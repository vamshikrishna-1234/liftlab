"""Incrementality math: lift %, incremental units/sales, statistical significance."""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from .stats import welch_t_test


def _stats_one_metric(
    df: pd.DataFrame, group_col: str, metric_col: str,
    control_label: str = "Control",
) -> pd.DataFrame:
    """Compute mean / std / count / lift / incrementality / p-value
    for a single metric across one grouping column."""
    agg = (
        df.groupby(group_col)[metric_col]
        .agg(mean="mean", std="std", count="count")
        .reset_index()
    )
    if control_label not in agg[group_col].values:
        return agg.assign(lift_pct=np.nan, incrementality=np.nan, p_value=np.nan)

    ctrl = agg[agg[group_col] == control_label].iloc[0]
    out_rows = []
    for _, row in agg.iterrows():
        if row[group_col] == control_label:
            out_rows.append({**row.to_dict(), "lift_pct": 0.0, "incrementality": 0.0, "p_value": np.nan})
            continue
        lift = 100.0 * (row["mean"] - ctrl["mean"]) / ctrl["mean"] if ctrl["mean"] else np.nan
        incr = (row["mean"] - ctrl["mean"]) * row["count"]
        t = welch_t_test(row["mean"], row["std"], int(row["count"]),
                         ctrl["mean"], ctrl["std"], int(ctrl["count"]))
        out_rows.append({**row.to_dict(), "lift_pct": lift, "incrementality": incr, "p_value": t.p_value})
    return pd.DataFrame(out_rows)


def compute_incrementality(
    df_post_with_groups: pd.DataFrame,
    metrics: Iterable[str] = (
        "post_net_sales",
        "post_gross_sales",
        "post_units",
        "post_visits",
        "post_ecom_net_sales",
        "post_non_ecom_net_sales",
    ),
    group_col: str = "target_group",
    control_label: str = "Control",
) -> pd.DataFrame:
    """Per-HH lift / incrementality / p-value for each metric."""
    out = []
    for m in metrics:
        per_hh_metric = m + "_per_hh"
        df = df_post_with_groups.rename(columns={m: per_hh_metric}) if m != per_hh_metric else df_post_with_groups
        s = _stats_one_metric(df, group_col, per_hh_metric, control_label=control_label)
        s.insert(0, "metric", _pretty_metric(m))
        s = s.rename(columns={group_col: "target_group"})
        out.append(s)
    return pd.concat(out, ignore_index=True)


def segment_incrementality(
    df_post_with_groups: pd.DataFrame,
    dimension: str,
    metric: str = "post_net_sales",
    group_col: str = "target_group",
    control_label: str = "Control",
) -> pd.DataFrame:
    """Incrementality for one metric, broken out by a customer dimension."""
    rows = []
    for value, sub in df_post_with_groups.groupby(dimension):
        s = _stats_one_metric(sub, group_col, metric, control_label=control_label)
        s.insert(0, dimension, value)
        rows.append(s)
    if not rows:
        return pd.DataFrame()
    out = pd.concat(rows, ignore_index=True)
    out = out.rename(columns={group_col: "target_group", "mean": f"{metric}_per_hh_mean"})
    return out


def _pretty_metric(m: str) -> str:
    mapping = {
        "post_net_sales": "Net Sales per HH",
        "post_gross_sales": "Gross Sales per HH",
        "post_units": "Units per HH",
        "post_visits": "Visits per HH",
        "post_ecom_net_sales": "eCom Net Sales per HH",
        "post_non_ecom_net_sales": "Non-eCom Net Sales per HH",
    }
    return mapping.get(m, m)
