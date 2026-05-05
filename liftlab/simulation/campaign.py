"""Synthetic campaign simulator with injected ground-truth lift.

Simulates: deliveries → opens/clicks → purchase behavior in the
post-campaign window, with a known true lift applied only to engaged
test households. Lets the analysis layer "recover" the truth and
proves the pipeline is correct.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class ChannelConfig:
    enabled: bool
    send_rate: float        # fraction of opted-in test HHs that receive
    open_rate: float        # opens / sends (sms uses click_rate; opens=NaN)
    click_rate: float       # clicks / sends
    unsub_rate: float       # unsubs / sends
    lift_on_clickers: float  # multiplicative lift to post-period sales for clickers
    lift_on_openers_only: float  # smaller lift for openers who didn't click
    lift_on_received_only: float  # tiny lift for receive-only (brand awareness)


def _default_channels() -> dict[str, ChannelConfig]:
    """Defaults tuned to produce a demoable, statistically-significant lift
    that mirrors a well-targeted promotional campaign at a major retailer.
    Real-world per-channel parameters vary widely; tweak per use case."""
    return {
        "email": ChannelConfig(True, 0.95, 0.235, 0.052, 0.004, 0.260, 0.060, 0.018),
        "push":  ChannelConfig(True, 0.90, 0.110, 0.026, 0.002, 0.205, 0.045, 0.012),
        "sms":   ChannelConfig(True, 0.93, np.nan, 0.062, 0.006, 0.225, 0.000, 0.018),
    }


def simulate_campaign(
    df_split: pd.DataFrame,
    campaign_dates: tuple[str, str] = ("2025-09-01", "2025-09-14"),
    post_period_weeks: int = 4,
    channels: dict[str, ChannelConfig] | None = None,
    contamination_rate: float = 0.015,
    seed: int = 7,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Simulate one full campaign.

    Returns
    -------
    df_engagement : long-form per-(hh, channel, date) engagement events.
    df_post : household-level post-period transaction summary
              (net_sales, gross_sales, units, visits, ecom flags).
    truth : dict with the injected ground-truth lift parameters.
    """
    rng = np.random.default_rng(seed)
    channels = channels or _default_channels()

    n = len(df_split)
    df = df_split.copy().reset_index(drop=True)

    days = pd.date_range(campaign_dates[0], campaign_dates[1], freq="D")
    n_days = len(days)
    is_test = (df["target_group"] == "Test").values

    rec_records = []
    eng_records = []

    hh_received_any = np.zeros(n, dtype=bool)
    hh_opened_any = np.zeros(n, dtype=bool)
    hh_clicked_any = np.zeros(n, dtype=bool)

    for ch_name, ch in channels.items():
        if not ch.enabled:
            continue

        opt_in = (df[f"{ch_name}_flag"] == 1).values
        # Test side: real campaign sends
        eligible_test = is_test & opt_in
        # Control side: small accidental contamination (real-world ops drift)
        eligible_ctrl = (~is_test) & opt_in

        send_mask = np.zeros(n, dtype=bool)
        send_mask[eligible_test] = rng.random(eligible_test.sum()) < ch.send_rate
        send_mask[eligible_ctrl] = rng.random(eligible_ctrl.sum()) < contamination_rate

        sent_idx = np.where(send_mask)[0]

        # Spread sends across days uniformly for the demo.
        send_days = rng.choice(n_days, size=len(sent_idx))

        # Opens (skip for SMS)
        if not np.isnan(ch.open_rate):
            open_mask_local = rng.random(len(sent_idx)) < ch.open_rate
        else:
            open_mask_local = np.zeros(len(sent_idx), dtype=bool)

        click_mask_local = rng.random(len(sent_idx)) < ch.click_rate
        # If not opened, click is much rarer (consistent with real funnels)
        if not np.isnan(ch.open_rate):
            click_mask_local &= open_mask_local | (rng.random(len(sent_idx)) < 0.08)

        unsub_mask_local = rng.random(len(sent_idx)) < ch.unsub_rate

        eng_records.append(pd.DataFrame({
            "household_id": df["household_id"].values[sent_idx],
            "target_group": df["target_group"].values[sent_idx],
            "channel": ch_name,
            "send_date": days[send_days],
            "sent": 1,
            "opened": open_mask_local.astype(int),
            "clicked": click_mask_local.astype(int),
            "unsubscribed": unsub_mask_local.astype(int),
        }))

        hh_received_any[sent_idx] = True
        hh_opened_any[sent_idx[open_mask_local]] = True
        hh_clicked_any[sent_idx[click_mask_local]] = True

        # Pre-aggregate which lift bucket each sent HH falls into for this channel
        rec_records.append(pd.DataFrame({
            "hh_idx": sent_idx,
            "channel": ch_name,
            "received": 1,
            "opened_only": (open_mask_local & ~click_mask_local).astype(int),
            "clicked": click_mask_local.astype(int),
        }))

    df_engagement = pd.concat(eng_records, ignore_index=True) if eng_records else pd.DataFrame()
    df_recv = pd.concat(rec_records, ignore_index=True) if rec_records else pd.DataFrame()

    # ----- Post-period transactions -----
    weeks = post_period_weeks
    base_post = (df["pre_weekly_net_sales"].values * weeks
                 * rng.normal(1.0, 0.18, size=n).clip(0.05, 5.0))

    multiplier = np.ones(n, dtype=float)
    # Apply lift bucket-by-bucket; collapse multi-channel by taking the max lift
    if not df_recv.empty:
        per_hh = (
            df_recv.groupby("hh_idx").agg(
                received=("received", "max"),
                opened_only=("opened_only", "max"),
                clicked=("clicked", "max"),
            )
        )
        for hh_idx, row in per_hh.iterrows():
            ch_lifts = []
            for ch_name, ch in channels.items():
                if not ch.enabled:
                    continue
                if row["clicked"]:
                    ch_lifts.append(ch.lift_on_clickers)
                elif row["opened_only"]:
                    ch_lifts.append(ch.lift_on_openers_only)
                elif row["received"]:
                    ch_lifts.append(ch.lift_on_received_only)
            if ch_lifts:
                multiplier[hh_idx] = 1.0 + max(ch_lifts)

    # Treatment effect only takes hold for genuinely-test households who
    # received at least one send.  Control "contamination" sends do NOT add lift
    # (since the underlying intent attribution wouldn't apply to them in real
    # life — they got the message by mistake but weren't the targeted cohort).
    multiplier = np.where(is_test, multiplier, 1.0)

    post_net_sales = np.round(base_post * multiplier, 2)

    # Visits & units track the lift but with their own noise (real campaigns
    # tend to lift basket size *and* visit frequency, not just one of them).
    visit_multiplier = 1.0 + (multiplier - 1.0) * rng.uniform(0.55, 0.85, size=n)
    base_visits = rng.normal(weeks * 1.4, 1.2, size=n) * visit_multiplier
    visits = np.maximum(0, np.round(base_visits)).astype(int)
    visits[post_net_sales == 0] = 0

    unit_multiplier = 1.0 + (multiplier - 1.0) * rng.uniform(0.40, 0.80, size=n)
    base_units = np.where(visits > 0,
                          rng.normal(visits * 6.5, 2.0) * unit_multiplier,
                          0)
    units = np.maximum(0, np.round(base_units)).astype(int)

    gross_sales = np.round(post_net_sales * rng.normal(1.18, 0.04, size=n).clip(1.05, 1.40), 2)

    ecom_share = np.where(df["ecom_ind"].values == 1,
                          rng.beta(3, 4, size=n),
                          rng.beta(1, 9, size=n))
    ecom_net_sales = np.round(post_net_sales * ecom_share, 2)
    non_ecom_net_sales = np.round(post_net_sales - ecom_net_sales, 2)

    df_post = pd.DataFrame({
        "household_id": df["household_id"].values,
        "post_net_sales": post_net_sales,
        "post_gross_sales": gross_sales,
        "post_units": units,
        "post_visits": visits,
        "post_ecom_net_sales": ecom_net_sales,
        "post_non_ecom_net_sales": non_ecom_net_sales,
        "received_any": hh_received_any.astype(int),
        "opened_any": hh_opened_any.astype(int),
        "clicked_any": hh_clicked_any.astype(int),
    })

    truth = {
        "campaign_dates": campaign_dates,
        "post_period_weeks": post_period_weeks,
        "channels": {k: v.__dict__ for k, v in channels.items() if v.enabled},
        "contamination_rate": contamination_rate,
    }

    return df_engagement, df_post, truth
