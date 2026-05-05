"""Stratified test/control population creation.

Mirrors the production approach used by retail CRM teams: stratify on a
configurable list of customer attributes, fall back to random allocation
for tiny strata, and verify post-hoc balance on a measurement variable.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split


def create_tvc_split(
    df: pd.DataFrame,
    balance_variables: Iterable[str] = (
        "division_id",
        "my_needs_segment",
        "persona",
        "facts_seg",
        "ecom_ind",
        "rewards_engaged",
        "channel_mix",
    ),
    test_ratio: float = 0.9,
    min_stratum_size: int = 50,
    seed: int = 420,
) -> pd.DataFrame:
    """Create a stratified test/control split.

    Parameters
    ----------
    df : household-level population.
    balance_variables : columns to stratify on.
    test_ratio : fraction of households assigned to Test (typical 0.9 = 90/10).
    min_stratum_size : strata smaller than this are split randomly to avoid
        sklearn errors on rare combinations.
    seed : random seed for reproducibility.
    """
    bv = list(balance_variables)
    df = df.sort_values("household_id").copy()
    df["_stratum_size"] = df.groupby(bv, dropna=False)["household_id"].transform("size")

    big = df[df["_stratum_size"] >= min_stratum_size]
    small = df[df["_stratum_size"] < min_stratum_size]

    if len(big) > 0:
        control_big, test_big = train_test_split(
            big,
            test_size=test_ratio,
            stratify=big[bv],
            random_state=seed,
        )
    else:
        control_big = test_big = big

    if len(small) > 0:
        control_small, test_small = train_test_split(
            small,
            test_size=test_ratio,
            random_state=seed,
        )
    else:
        control_small = test_small = small

    control = pd.concat([control_big, control_small])
    test = pd.concat([test_big, test_small])

    control = control.assign(target_group="Control")
    test = test.assign(target_group="Test")

    out = pd.concat([control, test]).drop(columns=["_stratum_size"]).reset_index(drop=True)
    return out


def balance_report(
    df_split: pd.DataFrame,
    measure_variable: str = "pre_weekly_net_sales",
    dimension_variables: Iterable[str] = (
        "division_id",
        "my_needs_segment",
        "persona",
        "facts_seg",
        "channel_mix",
    ),
) -> pd.DataFrame:
    """Verify post-hoc balance: counts and pre-period mean by group/dimension."""
    rows = []
    overall = df_split.groupby("target_group").agg(
        households=("household_id", "count"),
        pre_period_mean=(measure_variable, "mean"),
    ).reset_index()
    overall.insert(0, "dimension", "overall")
    overall.insert(1, "value", "all")
    rows.append(overall)

    for dim in dimension_variables:
        chunk = df_split.groupby([dim, "target_group"]).agg(
            households=("household_id", "count"),
            pre_period_mean=(measure_variable, "mean"),
        ).reset_index()
        chunk.insert(0, "dimension", dim)
        chunk = chunk.rename(columns={dim: "value"})
        rows.append(chunk)

    return pd.concat(rows, ignore_index=True)
