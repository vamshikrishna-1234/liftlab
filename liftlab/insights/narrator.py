"""Auto-generated executive narrative.

Two paths:
  1. If ANTHROPIC_API_KEY or OPENAI_API_KEY is set, calls a real LLM with
     a structured analyst-style prompt grounded in the actual numbers.
  2. Otherwise falls back to a rule-based template that produces an
     analyst-grade summary from the metrics. The template path is what
     makes the demo recordable offline / without API keys.
"""
from __future__ import annotations

import os
import textwrap

import numpy as np
import pandas as pd


def generate_executive_summary(
    df_overall: pd.DataFrame,
    df_segment: dict[str, pd.DataFrame],
    df_engagement_summary: pd.DataFrame,
    df_ops_efficiency: pd.DataFrame,
    campaign_name: str,
    use_llm: bool = False,
) -> str:
    """Build an executive summary from the analysis outputs.

    df_overall: output of compute_incrementality (overall, no dimension).
    df_segment: dict {dimension_name: segment_incrementality_df}
    """
    facts = _extract_facts(df_overall, df_segment, df_engagement_summary, df_ops_efficiency)
    template_summary = _render_template(facts, campaign_name)

    if use_llm:
        llm_text = _try_llm(facts, campaign_name, template_summary)
        if llm_text:
            return llm_text
    return template_summary


# ---------------------------------------------------------------------------
def _extract_facts(df_overall, df_segment, df_eng, df_ops) -> dict:
    facts = {}
    if not df_overall.empty:
        net = df_overall[df_overall["metric"] == "Net Sales per HH"]
        test_row = net[net["target_group"] == "Test"]
        ctrl_row = net[net["target_group"] == "Control"]
        if len(test_row) and len(ctrl_row):
            test_row = test_row.iloc[0]; ctrl_row = ctrl_row.iloc[0]
            facts["test_n"] = int(test_row["count"])
            facts["control_n"] = int(ctrl_row["count"])
            facts["lift_pct"] = float(test_row["lift_pct"])
            facts["p_value"] = float(test_row["p_value"])
            facts["incremental_net_sales"] = float(test_row["incrementality"])
            facts["test_mean"] = float(test_row["mean"])
            facts["control_mean"] = float(ctrl_row["mean"])

        units = df_overall[df_overall["metric"] == "Units per HH"]
        ut = units[units["target_group"] == "Test"]
        if len(ut):
            facts["units_lift_pct"] = float(ut.iloc[0]["lift_pct"])
            facts["incremental_units"] = float(ut.iloc[0]["incrementality"])
            facts["units_p_value"] = float(ut.iloc[0]["p_value"])

    # Best & worst segment
    best_seg = worst_seg = None
    best_val = -np.inf; worst_val = np.inf
    for dim, sdf in df_segment.items():
        if sdf.empty:
            continue
        test_only = sdf[sdf["target_group"] == "Test"]
        for _, row in test_only.iterrows():
            v = row.get("lift_pct", np.nan)
            if pd.isna(v):
                continue
            if v > best_val:
                best_val = v
                best_seg = (dim, str(row.get(dim, "?")), v, float(row.get("p_value", np.nan)),
                            int(row.get("count", 0)))
            if v < worst_val:
                worst_val = v
                worst_seg = (dim, str(row.get(dim, "?")), v, float(row.get("p_value", np.nan)),
                             int(row.get("count", 0)))
    facts["best_segment"] = best_seg
    facts["worst_segment"] = worst_seg

    # Engagement headline
    if df_eng is not None and not df_eng.empty:
        test_eng = df_eng[df_eng["target_group"] == "Test"]
        eng_lines = []
        for _, row in test_eng.iterrows():
            eng_lines.append({
                "channel": row["channel"],
                "sent": int(row["sent"]),
                "open_rate": float(row.get("open_rate_%", np.nan)),
                "click_rate": float(row.get("click_rate_%", np.nan)),
                "unsub_rate": float(row.get("unsub_rate_%", np.nan)),
            })
        facts["engagement"] = eng_lines

    # Ops efficiency headline
    if df_ops is not None and not df_ops.empty:
        ctrl_clean = df_ops[
            (df_ops["target_group"] == "Control")
            & (df_ops["channel_ops"] == "3. No Communication")
        ]
        test_match = df_ops[
            (df_ops["target_group"] == "Test")
            & (df_ops["channel_ops"] == "1. Same Communication")
        ]
        if len(ctrl_clean):
            facts["control_clean_pct"] = float(ctrl_clean.iloc[0]["pct_within_group"])
        if len(test_match):
            facts["test_match_pct"] = float(test_match.iloc[0]["pct_within_group"])

    return facts


# ---------------------------------------------------------------------------
def _render_template(f: dict, campaign_name: str) -> str:
    sig = (
        f"statistically significant (p = {f['p_value']:.4f})"
        if f.get("p_value") is not None and not np.isnan(f.get("p_value", np.nan)) and f["p_value"] < 0.05
        else f"NOT statistically significant (p = {f.get('p_value', float('nan')):.4f})"
    )

    lines = []
    lines.append(f"# Executive Summary — {campaign_name}\n")
    lines.append("## Headline")
    if "lift_pct" in f:
        lines.append(
            f"- The campaign delivered a **{f['lift_pct']:+.2f}% lift in net sales per household**, "
            f"which is {sig}."
        )
        lines.append(
            f"- Estimated **incremental net sales: ${f['incremental_net_sales']:,.0f}** "
            f"across {f['test_n']:,} test households (vs {f['control_n']:,} control)."
        )
    if "units_lift_pct" in f:
        lines.append(
            f"- Units-per-HH lift: **{f['units_lift_pct']:+.2f}%** "
            f"(~{f['incremental_units']:,.0f} incremental units, p = {f['units_p_value']:.4f})."
        )

    lines.append("\n## Engagement")
    for e in f.get("engagement", []):
        if np.isnan(e.get("open_rate", np.nan)):
            lines.append(
                f"- **{e['channel'].upper()}**: {e['sent']:,} sends, "
                f"CTR **{e['click_rate']:.2f}%**, unsub {e['unsub_rate']:.2f}%."
            )
        else:
            lines.append(
                f"- **{e['channel'].upper()}**: {e['sent']:,} sends, "
                f"open rate **{e['open_rate']:.2f}%**, CTR **{e['click_rate']:.2f}%**, "
                f"unsub {e['unsub_rate']:.2f}%."
            )

    lines.append("\n## Where it worked")
    if f.get("best_segment"):
        dim, val, lift, p, n = f["best_segment"]
        lines.append(
            f"- **Best segment:** `{dim} = {val}` — lift **{lift:+.2f}%** "
            f"across {n:,} HHs (p = {p:.4f})."
        )
    if f.get("worst_segment"):
        dim, val, lift, p, n = f["worst_segment"]
        lines.append(
            f"- **Weakest segment:** `{dim} = {val}` — lift **{lift:+.2f}%** "
            f"across {n:,} HHs (p = {p:.4f})."
        )

    lines.append("\n## Operational integrity")
    if "control_clean_pct" in f:
        verdict = "Healthy" if f["control_clean_pct"] >= 95 else "Investigate"
        lines.append(
            f"- Control hold-out cleanliness: **{f['control_clean_pct']:.2f}%** of control "
            f"received no communication. ({verdict}.)"
        )
    if "test_match_pct" in f:
        verdict = "Healthy" if f["test_match_pct"] >= 80 else "Investigate"
        lines.append(
            f"- Test send fidelity: **{f['test_match_pct']:.2f}%** of test households "
            f"received the comm they were assigned. ({verdict}.)"
        )

    lines.append("\n## What to test next")
    if f.get("worst_segment"):
        dim, val, lift, p, n = f["worst_segment"]
        lines.append(
            f"- Underperformance in `{dim} = {val}` warrants a creative or channel "
            f"variant test on this cohort isolated from the main blast."
        )
    if f.get("best_segment"):
        dim, val, lift, p, n = f["best_segment"]
        lines.append(
            f"- Double down on `{dim} = {val}` with a +offer / +cadence variant to "
            f"see if the lift compounds or saturates."
        )
    lines.append(
        "- Run a 2-week observation extension to estimate post-window decay and "
        "true campaign ROI."
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
def _try_llm(facts: dict, campaign_name: str, template_fallback: str) -> str | None:
    """Attempt to call an LLM if a key is present; otherwise return None."""
    prompt = textwrap.dedent(f"""
        You are a senior retail marketing analyst writing the executive summary of
        a post-campaign incrementality report. Write in clean markdown, ≤300 words,
        with sections: Headline, Engagement, Where it worked, Operational integrity,
        What to test next. Be specific, quote numbers, and call out anything unusual.

        Campaign name: {campaign_name}
        Facts (ground truth): {facts}
    """).strip()

    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            import anthropic  # type: ignore
            client = anthropic.Anthropic()
            resp = client.messages.create(
                model=os.getenv("LIFTLAB_LLM_MODEL", "claude-sonnet-4-5"),
                max_tokens=900,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text  # type: ignore
        except Exception:
            return None
    if os.getenv("OPENAI_API_KEY"):
        try:
            from openai import OpenAI  # type: ignore
            client = OpenAI()
            resp = client.chat.completions.create(
                model=os.getenv("LIFTLAB_LLM_MODEL", "gpt-5"),
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.choices[0].message.content
        except Exception:
            return None
    return None
