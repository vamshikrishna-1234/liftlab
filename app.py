"""Liftlab demo app: AI marketing analyst for retail campaign incrementality.

Single-page Streamlit app with a guided 5-step flow:
    1. Define the campaign + audience
    2. Generate population & build a stratified TVC split
    3. Simulate the campaign (with a known ground-truth lift)
    4. Run the incrementality analysis
    5. Auto-narrate insights + export the executive Excel report

Built on entirely synthetic data. No real customer information.
"""
from __future__ import annotations

import time
from datetime import date

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from liftlab.data import (
    generate_population,
    load_population_from_csv,
    CSVValidationError,
    REQUIRED_COLUMNS,
    OPTIONAL_DEFAULTS,
)
from liftlab.splits import create_tvc_split, balance_report
from liftlab.simulation import simulate_campaign
from liftlab.simulation.campaign import ChannelConfig
from liftlab.analysis import compute_incrementality, segment_incrementality
from liftlab.analysis.engagement import engagement_summary, daily_engagement, ops_efficiency
from liftlab.insights import generate_executive_summary
from liftlab.report import build_excel_report


st.set_page_config(
    page_title="Liftlab — AI Marketing Analyst",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ===========================================================================
# Header
# ===========================================================================
st.markdown(
    """
    <div style="display:flex;align-items:center;gap:14px;margin-bottom:8px">
        <div style="font-size:32px">📈</div>
        <div>
            <div style="font-size:28px;font-weight:700;color:#F5F7FA">Liftlab</div>
            <div style="color:#9AA3B2;margin-top:-2px">
                AI marketing analyst for retail &amp; CPG incrementality testing.
                <i>All data shown is synthetic.</i>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.divider()


# ===========================================================================
# Sidebar: campaign config
# ===========================================================================
with st.sidebar:
    st.subheader("Campaign configuration")
    campaign_name = st.text_input("Campaign name", "Spring Grocery Push 2026")
    n_households = st.select_slider(
        "Population size (households)",
        options=[10_000, 50_000, 100_000, 250_000, 500_000],
        value=100_000,
    )
    test_ratio = st.slider("Test allocation %", 50, 95, 90) / 100.0

    st.markdown("**Channels enabled**")
    email_on = st.checkbox("Email", value=True)
    push_on = st.checkbox("Push", value=True)
    sms_on = st.checkbox("SMS", value=True)

    start_date = st.date_input("Campaign start", date(2026, 4, 6))
    end_date = st.date_input("Campaign end", date(2026, 4, 19))
    post_weeks = st.number_input("Post-period observation (weeks)", 1, 12, 4)

    seed = st.number_input("Random seed", value=42, step=1)
    use_llm = st.checkbox(
        "Use real LLM for narrative (requires API key)",
        value=False,
        help="If unchecked, uses the deterministic template narrator. The "
             "narrator falls back to template automatically if no API key is found.",
    )


# ===========================================================================
# Session state
# ===========================================================================
state = st.session_state
state.setdefault("step", 0)
state.setdefault("population", None)
state.setdefault("split", None)
state.setdefault("eng", None)
state.setdefault("post", None)
state.setdefault("results", None)
state.setdefault("excel_bytes", None)


def _bump(step: int) -> None:
    state["step"] = max(state["step"], step)


# ===========================================================================
# Step 1: Load population (synthetic OR uploaded CSV)
# ===========================================================================
st.subheader("1. Bring your customer population")

mode = st.radio(
    "Data source",
    ["Generate synthetic", "Upload my own CSV"],
    horizontal=True,
    label_visibility="collapsed",
    key="data_source",
)

if mode == "Generate synthetic":
    c1, c2 = st.columns([1, 3])
    with c1:
        if st.button("Generate population", type="primary", use_container_width=True):
            with st.spinner(f"Generating {n_households:,} synthetic households…"):
                t0 = time.time()
                df = generate_population(n_households=n_households, seed=int(seed))
                state["population"] = df
                state["population_source"] = "synthetic"
                state["gen_time"] = time.time() - t0
            _bump(1)

else:
    c1, c2 = st.columns([1, 3])
    with c1:
        with st.expander("Required CSV schema", expanded=False):
            st.markdown(
                f"""
                **Required columns:**
                - `household_id` (integer, unique)
                - `email_flag`, `push_flag`, `sms_flag` (each 0 or 1)
                - `pre_weekly_net_sales` (float, $/week)

                **Optional columns** (auto-filled if missing):
                - `division_id`, `my_needs_segment`, `persona`, `facts_seg`
                - `ecom_ind`, `rewards_engaged`
                """
            )

        sample_df = generate_population(n_households=50_000, seed=42)
        st.download_button(
            "Download sample CSV (50K HHs)",
            data=sample_df.to_csv(index=False).encode("utf-8"),
            file_name="liftlab_sample_population.csv",
            mime="text/csv",
            use_container_width=True,
        )
        uploaded = st.file_uploader(
            "Upload population CSV", type=["csv"], label_visibility="collapsed"
        )
        if uploaded is not None and st.button(
            "Load uploaded data", type="primary", use_container_width=True
        ):
            try:
                with st.spinner("Parsing and validating CSV…"):
                    t0 = time.time()
                    df = load_population_from_csv(uploaded)
                    state["population"] = df
                    state["population_source"] = f"uploaded ({uploaded.name})"
                    state["gen_time"] = time.time() - t0
                _bump(1)
            except CSVValidationError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Unexpected error reading CSV: {e}")

if state["population"] is not None:
    df = state["population"]
    with c2:
        a, b, c, d = st.columns(4)
        a.metric("Reachable HHs", f"{len(df):,}")
        b.metric("Avg pre-period weekly $", f"${df['pre_weekly_net_sales'].mean():.2f}")
        c.metric("eCom indexed HHs", f"{(df['ecom_ind']==1).sum():,}")
        d.metric("Load time", f"{state['gen_time']:.2f}s")
        st.caption(f"Source: **{state.get('population_source', 'synthetic')}**")
    with st.expander("Peek at the population"):
        st.dataframe(df.head(20), use_container_width=True)
        if "my_needs_segment" in df.columns:
            seg_chart = (df.groupby("my_needs_segment").size().reset_index(name="hhs"))
            st.plotly_chart(
                px.bar(seg_chart, x="my_needs_segment", y="hhs",
                       title="Household distribution by my-needs segment"),
                use_container_width=True,
            )

st.divider()


# ===========================================================================
# Step 2: Stratified TVC split
# ===========================================================================
st.subheader(f"2. Build a stratified test/control split ({int(test_ratio*100)}/{int((1-test_ratio)*100)})")
disabled = state["population"] is None
c1, c2 = st.columns([1, 3])
with c1:
    if st.button("Create TVC split", type="primary", use_container_width=True, disabled=disabled):
        with st.spinner("Stratifying across segment, persona, channel mix, division…"):
            t0 = time.time()
            split = create_tvc_split(state["population"], test_ratio=test_ratio, seed=int(seed))
            state["split"] = split
            state["balance"] = balance_report(split)
            state["split_time"] = time.time() - t0
        _bump(2)

if state["split"] is not None:
    split = state["split"]
    with c2:
        a, b, c, d = st.columns(4)
        a.metric("Test HHs", f"{(split['target_group']=='Test').sum():,}")
        b.metric("Control HHs", f"{(split['target_group']=='Control').sum():,}")
        actual_ratio = (split['target_group'] == 'Test').mean() * 100
        c.metric("Actual test %", f"{actual_ratio:.2f}%")
        d.metric("Split time", f"{state['split_time']:.2f}s")

    bal = state["balance"]
    with st.expander("Pre-period balance check (should be near-identical across groups)"):
        seg_bal = bal[bal["dimension"] == "my_needs_segment"]
        pivoted = seg_bal.pivot(index="value", columns="target_group",
                                values="pre_period_mean").reset_index()
        if "Test" in pivoted.columns and "Control" in pivoted.columns:
            pivoted["delta_%"] = 100 * (pivoted["Test"] - pivoted["Control"]) / pivoted["Control"]
        st.dataframe(pivoted, use_container_width=True)
        st.caption("Pre-campaign weekly net sales per HH, by my-needs segment.")

st.divider()


# ===========================================================================
# Step 3: Simulate campaign
# ===========================================================================
st.subheader("3. Simulate the campaign")
st.caption(
    "We inject a known ground-truth lift on engaged test households so the "
    "analysis layer can recover it. In production this step is replaced by "
    "the actual campaign delivery + transaction data from your warehouse."
)
disabled = state["split"] is None
c1, c2 = st.columns([1, 3])

channels = {
    "email": ChannelConfig(email_on, 0.95, 0.235, 0.052, 0.004, 0.260, 0.060, 0.018),
    "push":  ChannelConfig(push_on,  0.90, 0.110, 0.026, 0.002, 0.205, 0.045, 0.012),
    "sms":   ChannelConfig(sms_on,   0.93, np.nan, 0.062, 0.006, 0.225, 0.000, 0.018),
}

with c1:
    if st.button("Run campaign simulation", type="primary",
                 use_container_width=True, disabled=disabled):
        with st.spinner("Simulating sends, opens, clicks, and 4-week post-period sales…"):
            t0 = time.time()
            eng, post, truth = simulate_campaign(
                state["split"],
                campaign_dates=(str(start_date), str(end_date)),
                post_period_weeks=int(post_weeks),
                channels=channels,
                seed=int(seed),
            )
            state["eng"] = eng
            state["post"] = post
            state["truth"] = truth
            state["sim_time"] = time.time() - t0
        _bump(3)

if state["eng"] is not None:
    eng = state["eng"]
    post = state["post"]
    with c2:
        a, b, c, d = st.columns(4)
        a.metric("Total sends", f"{int(eng['sent'].sum()):,}")
        a.caption(f"Email + Push + SMS combined")
        b.metric("Total opens", f"{int(eng['opened'].sum()):,}")
        c.metric("Total clicks", f"{int(eng['clicked'].sum()):,}")
        d.metric("Sim time", f"{state['sim_time']:.2f}s")
    with st.expander("Daily send volume by channel"):
        daily = daily_engagement(eng)
        st.plotly_chart(
            px.bar(daily, x="send_date", y="sent", color="channel",
                   title="Daily sends by channel"),
            use_container_width=True,
        )

st.divider()


# ===========================================================================
# Step 4: Run incrementality analysis
# ===========================================================================
st.subheader("4. Run the incrementality analysis")
disabled = state["post"] is None or state["split"] is None
c1, c2 = st.columns([1, 3])

with c1:
    if st.button("Analyze campaign", type="primary",
                 use_container_width=True, disabled=disabled):
        with st.spinner("Computing lift, incrementality, and p-values…"):
            t0 = time.time()
            joined = state["split"].merge(state["post"], on="household_id", how="left").fillna(0)
            overall = compute_incrementality(joined)
            seg_dims = ["my_needs_segment", "persona", "facts_seg",
                        "channel_mix", "division_id", "ecom_ind", "rewards_engaged"]
            seg_results = {dim: segment_incrementality(joined, dim) for dim in seg_dims}
            eng_summary = engagement_summary(state["eng"])
            ops = ops_efficiency(state["split"], state["post"])
            state["results"] = {
                "overall": overall,
                "segments": seg_results,
                "engagement": eng_summary,
                "ops": ops,
                "joined": joined,
            }
            state["analysis_time"] = time.time() - t0
        _bump(4)

if state["results"] is not None:
    r = state["results"]
    overall = r["overall"]

    with c2:
        net = overall[(overall["metric"] == "Net Sales per HH") &
                      (overall["target_group"] == "Test")]
        units = overall[(overall["metric"] == "Units per HH") &
                        (overall["target_group"] == "Test")]
        if len(net):
            net = net.iloc[0]
            a, b, c, d = st.columns(4)
            a.metric("Lift in Net Sales/HH", f"{net['lift_pct']:+.2f}%")
            b.metric("Incremental Net Sales", f"${net['incrementality']:,.0f}")
            c.metric("p-value (Net Sales)", f"{net['p_value']:.4f}",
                     "significant" if net["p_value"] < 0.05 else "not sig.")
            d.metric("Analysis time", f"{state['analysis_time']:.2f}s")
        if len(units):
            u = units.iloc[0]
            st.caption(
                f"Units/HH lift {u['lift_pct']:+.2f}%  •  "
                f"~{u['incrementality']:,.0f} incremental units  •  "
                f"p = {u['p_value']:.4f}"
            )

    tabs = st.tabs(["Overall", "By segment", "Engagement", "Ops efficiency"])
    with tabs[0]:
        st.dataframe(overall, use_container_width=True, hide_index=True)
    with tabs[1]:
        dim_pick = st.selectbox("Dimension", list(r["segments"].keys()))
        sdf = r["segments"][dim_pick]
        st.dataframe(sdf, use_container_width=True, hide_index=True)
        if not sdf.empty:
            chart_df = sdf[sdf["target_group"] == "Test"].copy()
            chart_df["sig"] = np.where(chart_df["p_value"] < 0.05, "p<0.05", "p≥0.05")
            st.plotly_chart(
                px.bar(chart_df, x=dim_pick, y="lift_pct", color="sig",
                       title=f"Net sales lift % by {dim_pick}",
                       color_discrete_map={"p<0.05": "#22C55E", "p≥0.05": "#9AA3B2"}),
                use_container_width=True,
            )
    with tabs[2]:
        st.dataframe(r["engagement"], use_container_width=True, hide_index=True)
        if not r["engagement"].empty:
            ch = r["engagement"][r["engagement"]["target_group"] == "Test"]
            st.plotly_chart(
                px.bar(ch, x="channel", y=["open_rate_%", "click_rate_%"],
                       barmode="group", title="Open & click rates by channel (test side)"),
                use_container_width=True,
            )
    with tabs[3]:
        st.dataframe(r["ops"], use_container_width=True, hide_index=True)

st.divider()


# ===========================================================================
# Step 5: AI executive summary
# ===========================================================================
st.subheader("5. Auto-narrated executive summary + export")
disabled = state["results"] is None
c1, c2 = st.columns([1, 3])

with c1:
    if st.button("Generate AI summary", type="primary",
                 use_container_width=True, disabled=disabled):
        r = state["results"]
        with st.spinner("Writing narrative + assembling Excel…"):
            t0 = time.time()
            summary = generate_executive_summary(
                df_overall=r["overall"],
                df_segment=r["segments"],
                df_engagement_summary=r["engagement"],
                df_ops_efficiency=r["ops"],
                campaign_name=campaign_name,
                use_llm=use_llm,
            )
            xls = build_excel_report(
                campaign_name=campaign_name,
                overall=r["overall"],
                segment_breakdowns=r["segments"],
                engagement_summary=r["engagement"],
                daily_engagement=daily_engagement(state["eng"]),
                ops_efficiency=r["ops"],
                balance_report=state["balance"],
                executive_summary_md=summary,
            )
            state["summary"] = summary
            state["excel_bytes"] = xls
            state["report_time"] = time.time() - t0
        _bump(5)

if state.get("summary"):
    with c2:
        st.markdown(state["summary"])
    st.download_button(
        "Download full Excel report",
        data=state["excel_bytes"],
        file_name=f"{campaign_name.replace(' ', '_')}_liftlab_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )
    if "report_time" in state:
        total = state.get("gen_time", 0) + state.get("split_time", 0) + \
                state.get("sim_time", 0) + state.get("analysis_time", 0) + state["report_time"]
        st.caption(
            f"End-to-end pipeline ran in **{total:.2f} seconds**. "
            "In a real deployment, steps 1 and 3 are replaced by direct warehouse "
            "queries against your customer + delivery + transaction tables."
        )

st.divider()
st.caption(
    "Liftlab demo · Built end-to-end in <a href='https://cursor.com'>Cursor</a> · "
    "All numbers shown are from a synthetic data generator. "
    "Production deployment runs inside the customer's BigQuery / Snowflake / Redshift.",
    unsafe_allow_html=True,
)
