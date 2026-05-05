"""Synthetic retail customer population generator.

Generates a realistic-looking household-level dataset with the same shape
real retailers work with: divisions, customer segments, persona, channel
opt-in flags, and pre-period transaction baselines. No real customer data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

MY_NEEDS_SEGMENTS = [
    "Easy_Eating",
    "Healthy_Foodies",
    "Chasing_Price",
    "Easy_Shopping",
    "Scratch_Foodies",
    "One_Stop_Low_Price",
]

PERSONAS = ["Convenience", "Value", "Premium", "Family", "Wellness"]

FACTS_SEGMENTS = ["Loyal", "Occasional", "Lapsing", "New"]

DIVISIONS = list(range(1, 9))


def generate_population(
    n_households: int = 100_000,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate a synthetic household-level retail customer population.

    Each row represents one household with marketing attributes and a
    pre-campaign transaction baseline drawn from a lognormal distribution
    that varies by segment (e.g. Healthy_Foodies and Premium spend more).
    """
    rng = np.random.default_rng(seed)

    division_id = rng.choice(DIVISIONS, size=n_households, p=_normalize([5, 4, 4, 3, 3, 2, 2, 1]))
    my_needs = rng.choice(MY_NEEDS_SEGMENTS, size=n_households, p=_normalize([3, 2, 2, 2, 1.5, 1.5]))
    persona = rng.choice(PERSONAS, size=n_households, p=_normalize([3, 3, 1, 2, 1.5]))
    facts_seg = rng.choice(FACTS_SEGMENTS, size=n_households, p=_normalize([4, 3, 1.5, 1.5]))

    ecom_ind = rng.binomial(1, 0.32, size=n_households)
    rewards_engaged = rng.binomial(1, 0.58, size=n_households)

    email_flag = rng.binomial(1, 0.78, size=n_households)
    push_flag = rng.binomial(1, 0.41, size=n_households)
    sms_flag = rng.binomial(1, 0.22, size=n_households)

    # Pre-period weekly net sales baseline ($).  Lognormal with multiplicative
    # boosts for higher-spend segments; gives realistic skewed distribution.
    base_mu = np.log(38.0)
    base_sigma = 0.85
    pre_weekly = rng.lognormal(base_mu, base_sigma, size=n_households)

    segment_multiplier = np.where(
        np.isin(my_needs, ["Healthy_Foodies", "Scratch_Foodies"]), 1.25,
        np.where(np.isin(my_needs, ["Chasing_Price", "One_Stop_Low_Price"]), 0.78, 1.0),
    )
    persona_multiplier = np.where(persona == "Premium", 1.45,
                          np.where(persona == "Family", 1.30,
                          np.where(persona == "Value", 0.85, 1.0)))
    rewards_multiplier = np.where(rewards_engaged == 1, 1.18, 1.0)
    ecom_multiplier = np.where(ecom_ind == 1, 1.12, 1.0)

    pre_weekly = pre_weekly * segment_multiplier * persona_multiplier * rewards_multiplier * ecom_multiplier

    df = pd.DataFrame({
        "household_id": np.arange(1_000_000, 1_000_000 + n_households, dtype=np.int64),
        "division_id": division_id.astype(np.int16),
        "my_needs_segment": my_needs,
        "persona": persona,
        "facts_seg": facts_seg,
        "ecom_ind": ecom_ind.astype(np.int8),
        "rewards_engaged": rewards_engaged.astype(np.int8),
        "email_flag": email_flag.astype(np.int8),
        "push_flag": push_flag.astype(np.int8),
        "sms_flag": sms_flag.astype(np.int8),
        "pre_weekly_net_sales": np.round(pre_weekly, 2),
    })

    # Filter to reachable households (at least one channel) — same business
    # rule retailers apply: don't include un-contactable HHs in TVC.
    df = df[(df["email_flag"] + df["push_flag"] + df["sms_flag"]) > 0].reset_index(drop=True)

    df["channel_mix"] = _channel_mix_label(df)

    return df


def _channel_mix_label(df: pd.DataFrame) -> pd.Series:
    e, p, s = df["email_flag"], df["push_flag"], df["sms_flag"]
    conds = [
        (e == 1) & (p == 0) & (s == 0),
        (e == 0) & (p == 1) & (s == 0),
        (e == 0) & (p == 0) & (s == 1),
        (e == 1) & (p == 1) & (s == 0),
        (e == 1) & (p == 0) & (s == 1),
        (e == 0) & (p == 1) & (s == 1),
        (e == 1) & (p == 1) & (s == 1),
    ]
    labels = [
        "1.Email-only",
        "2.Push-only",
        "3.SMS-only",
        "4.Email+Push",
        "5.Email+SMS",
        "6.Push+SMS",
        "7.Email+Push+SMS",
    ]
    return np.select(conds, labels, default="0.Unreachable")


def _normalize(weights):
    arr = np.asarray(weights, dtype=float)
    return arr / arr.sum()
