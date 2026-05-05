"""Engagement and ops-efficiency aggregation."""
from __future__ import annotations

import numpy as np
import pandas as pd


def engagement_summary(df_engagement: pd.DataFrame) -> pd.DataFrame:
    """Per-channel/target_group send/open/click/unsub aggregation."""
    if df_engagement.empty:
        return pd.DataFrame()
    g = df_engagement.groupby(["channel", "target_group"]).agg(
        sent=("sent", "sum"),
        opened=("opened", "sum"),
        clicked=("clicked", "sum"),
        unsubscribed=("unsubscribed", "sum"),
        unique_hhs=("household_id", "nunique"),
    ).reset_index()
    g["open_rate_%"] = np.where(g["sent"] > 0, 100 * g["opened"] / g["sent"], np.nan)
    g["click_rate_%"] = np.where(g["sent"] > 0, 100 * g["clicked"] / g["sent"], np.nan)
    g["unsub_rate_%"] = np.where(g["sent"] > 0, 100 * g["unsubscribed"] / g["sent"], np.nan)
    return g


def daily_engagement(df_engagement: pd.DataFrame) -> pd.DataFrame:
    if df_engagement.empty:
        return pd.DataFrame()
    g = df_engagement.groupby(["send_date", "channel"]).agg(
        sent=("sent", "sum"),
        opened=("opened", "sum"),
        clicked=("clicked", "sum"),
    ).reset_index()
    g["click_rate_%"] = np.where(g["sent"] > 0, 100 * g["clicked"] / g["sent"], np.nan)
    return g


def ops_efficiency(
    df_split: pd.DataFrame,
    df_post: pd.DataFrame,
) -> pd.DataFrame:
    """Validate that test got the comm and control didn't.

    Categories:
      1. Same Communication: HH received and was supposed to (Test + received_any)
      2. Other Communication: HH was Control but received any (contamination)
      3. No Communication: HH didn't receive anything
    """
    df = df_split.merge(
        df_post[["household_id", "received_any"]], on="household_id", how="left"
    )
    cond_same = (df["target_group"] == "Test") & (df["received_any"] == 1)
    cond_other = (df["target_group"] == "Control") & (df["received_any"] == 1)
    cond_none = df["received_any"] == 0
    df["channel_ops"] = np.select(
        [cond_same, cond_other, cond_none],
        ["1. Same Communication", "2. Other Communication", "3. No Communication"],
        default="3. No Communication",
    )
    out = df.groupby(["target_group", "channel_ops"]).agg(
        households=("household_id", "count"),
    ).reset_index()
    totals = out.groupby("target_group")["households"].transform("sum")
    out["pct_within_group"] = 100 * out["households"] / totals
    return out
