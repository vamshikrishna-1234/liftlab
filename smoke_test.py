"""Headless end-to-end smoke test for the Liftlab pipeline.

Runs the full flow without Streamlit and prints summary numbers so we can
confirm everything works before recording the demo.
"""
from __future__ import annotations

import time

from liftlab.data import generate_population
from liftlab.splits import create_tvc_split, balance_report
from liftlab.simulation import simulate_campaign
from liftlab.simulation.campaign import ChannelConfig
from liftlab.analysis import compute_incrementality, segment_incrementality
from liftlab.analysis.engagement import engagement_summary, daily_engagement, ops_efficiency
from liftlab.insights import generate_executive_summary
from liftlab.report import build_excel_report


def main() -> None:
    t0 = time.time()
    print("[1/5] Generating synthetic population…")
    pop = generate_population(n_households=100_000, seed=42)
    print(f"   reachable HHs: {len(pop):,}, "
          f"avg pre-period weekly $: {pop['pre_weekly_net_sales'].mean():.2f}")

    print("[2/5] Creating stratified TVC split…")
    split = create_tvc_split(pop, test_ratio=0.9, seed=420)
    print(f"   Test {(split['target_group']=='Test').sum():,} / "
          f"Control {(split['target_group']=='Control').sum():,}")

    print("[3/5] Simulating campaign with injected lift…")
    eng, post, truth = simulate_campaign(
        split,
        campaign_dates=("2026-04-06", "2026-04-19"),
        post_period_weeks=4,
        seed=7,
    )
    print(f"   sends: {int(eng['sent'].sum()):,} | "
          f"opens: {int(eng['opened'].sum()):,} | "
          f"clicks: {int(eng['clicked'].sum()):,}")

    print("[4/5] Computing incrementality + segment breakdowns…")
    joined = split.merge(post, on="household_id", how="left").fillna(0)
    overall = compute_incrementality(joined)
    seg = {dim: segment_incrementality(joined, dim)
           for dim in ["my_needs_segment", "persona", "channel_mix"]}
    eng_summary = engagement_summary(eng)
    ops = ops_efficiency(split, post)

    net = overall[(overall["metric"] == "Net Sales per HH") &
                  (overall["target_group"] == "Test")].iloc[0]
    print(f"   Net Sales/HH lift: {net['lift_pct']:+.2f}%, "
          f"incremental ${net['incrementality']:,.0f}, p = {net['p_value']:.4f}")

    print("[5/5] Generating executive summary + Excel report…")
    summary = generate_executive_summary(
        df_overall=overall,
        df_segment=seg,
        df_engagement_summary=eng_summary,
        df_ops_efficiency=ops,
        campaign_name="Smoke Test Spring Campaign",
        use_llm=False,
    )
    xls = build_excel_report(
        campaign_name="Smoke Test Spring Campaign",
        overall=overall,
        segment_breakdowns=seg,
        engagement_summary=eng_summary,
        daily_engagement=daily_engagement(eng),
        ops_efficiency=ops,
        balance_report=balance_report(split),
        executive_summary_md=summary,
    )

    out_path = "smoke_test_report.xlsx"
    with open(out_path, "wb") as f:
        f.write(xls)

    print()
    print("=" * 70)
    print("EXECUTIVE SUMMARY (template-generated)")
    print("=" * 70)
    print(summary)
    print()
    print(f"Excel report bytes: {len(xls):,}  ->  saved to {out_path}")
    print(f"Total pipeline time: {time.time()-t0:.2f}s")


if __name__ == "__main__":
    main()
