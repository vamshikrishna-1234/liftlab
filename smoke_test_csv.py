"""Smoke test for the CSV upload path.
Loads samples/liftlab_sample_population.csv and runs the full pipeline."""
from __future__ import annotations

import time

from liftlab.data import load_population_from_csv
from liftlab.splits import create_tvc_split, balance_report
from liftlab.simulation import simulate_campaign
from liftlab.analysis import compute_incrementality, segment_incrementality
from liftlab.analysis.engagement import engagement_summary, daily_engagement, ops_efficiency
from liftlab.insights import generate_executive_summary
from liftlab.report import build_excel_report


def main() -> None:
    t0 = time.time()
    print("[1] Loading sample CSV...")
    pop = load_population_from_csv("samples/liftlab_sample_population.csv")
    print(f"   loaded {len(pop):,} rows, "
          f"avg pre-period $/wk = {pop['pre_weekly_net_sales'].mean():.2f}")

    print("[2] TVC split...")
    split = create_tvc_split(pop, test_ratio=0.9, seed=420)
    print(f"   Test {(split['target_group']=='Test').sum():,} / "
          f"Control {(split['target_group']=='Control').sum():,}")

    print("[3] Simulating campaign...")
    eng, post, _ = simulate_campaign(split, seed=7)

    print("[4] Analyzing...")
    joined = split.merge(post, on="household_id", how="left").fillna(0)
    overall = compute_incrementality(joined)
    seg = {dim: segment_incrementality(joined, dim)
           for dim in ["my_needs_segment", "persona", "channel_mix"]}

    net = overall[(overall["metric"] == "Net Sales per HH") &
                  (overall["target_group"] == "Test")].iloc[0]
    print(f"   Net Sales/HH lift: {net['lift_pct']:+.2f}%, "
          f"incremental ${net['incrementality']:,.0f}, p = {net['p_value']:.4f}")

    print("[5] Executive summary + Excel...")
    summary = generate_executive_summary(
        df_overall=overall, df_segment=seg,
        df_engagement_summary=engagement_summary(eng),
        df_ops_efficiency=ops_efficiency(split, post),
        campaign_name="CSV Upload Smoke Test", use_llm=False,
    )
    xls = build_excel_report(
        campaign_name="CSV Upload Smoke Test",
        overall=overall, segment_breakdowns=seg,
        engagement_summary=engagement_summary(eng),
        daily_engagement=daily_engagement(eng),
        ops_efficiency=ops_efficiency(split, post),
        balance_report=balance_report(split),
        executive_summary_md=summary,
    )
    print(f"   Excel: {len(xls):,} bytes")
    print(f"Total time: {time.time()-t0:.2f}s")


if __name__ == "__main__":
    main()
