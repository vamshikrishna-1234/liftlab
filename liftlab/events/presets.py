"""Retail seasonal event presets.

When a user picks an event (Easter, Super Bowl, etc.), the agent narrows the
population to households whose persona / segment / channel mix historically
over-index on that event, and explains the reasoning. The same filter logic
would be replaced in production by a category-affinity query against your
SKU/UPC purchase history.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class EventPreset:
    name: str
    short: str                                  # for the campaign name
    target_personas: list[str] = field(default_factory=list)
    target_segments: list[str] = field(default_factory=list)
    boost_ecom: bool = False
    rationale: str = ""
    expected_lift_profile: str = ""             # narrative paragraph


EVENT_PRESETS: dict[str, EventPreset] = {
    "None — full population": EventPreset(
        name="None — full population",
        short="General Campaign",
        rationale="No event filter applied. Targeting all reachable households.",
    ),
    "Super Bowl 2026": EventPreset(
        name="Super Bowl 2026",
        short="Super Bowl 2026",
        target_personas=["Family", "Convenience", "Value"],
        target_segments=["Easy_Eating", "One_Stop_Low_Price", "Chasing_Price"],
        rationale=(
            "Super Bowl is the largest single-day grocery event in the U.S. "
            "and over-indexes on snack, beverage, frozen-pizza, and party-platter "
            "categories. Families and value-driven shoppers historically drive "
            "60–70% of incremental basket on game-week. Wellness and Premium "
            "personas under-index, so we exclude them to avoid diluting the "
            "control hold-out with non-responders."
        ),
        expected_lift_profile=(
            "Expected lift profile: +5–9% net sales/HH on engaged customers, "
            "concentrated in the 7-day window leading up to game day. "
            "Push and SMS typically out-perform email by 1.4× for last-minute "
            "purchase intent."
        ),
    ),
    "Easter 2026": EventPreset(
        name="Easter 2026",
        short="Easter 2026",
        target_personas=["Family", "Premium", "Wellness"],
        target_segments=["Easy_Eating", "Healthy_Foodies", "Scratch_Foodies"],
        rationale=(
            "Easter campaigns over-index on Family and Premium personas "
            "(brunch / ham / lamb / chocolate), plus Wellness for premium-"
            "produce holiday baskets. Scratch_Foodies and Healthy_Foodies "
            "are the strongest segment responders historically. Value-only "
            "and Convenience shoppers under-index — they trade down rather "
            "than up for holiday meals — so we exclude them."
        ),
        expected_lift_profile=(
            "Expected lift profile: +4–7% net sales/HH, with significant "
            "premium-mix shift (gross sales lifts even higher). Email leads "
            "engagement; push assists for the 48-hour reminder window."
        ),
    ),
    "Valentine's Day 2026": EventPreset(
        name="Valentine's Day 2026",
        short="Valentine's Day 2026",
        target_personas=["Premium", "Wellness", "Convenience"],
        target_segments=["Easy_Eating", "Scratch_Foodies", "Healthy_Foodies"],
        boost_ecom=True,
        rationale=(
            "Valentine's Day skews to Premium and Wellness personas with "
            "strong eCom indexation (flowers, premium chocolates, prepared "
            "meals delivered). Family persona is included only at low weight "
            "since family-oriented purchases happen at lower frequency."
        ),
        expected_lift_profile=(
            "Expected lift profile: +3–6% net sales/HH, very narrow 5-day "
            "window. eCom lift typically 2× the in-store lift."
        ),
    ),
    "Back to School 2026": EventPreset(
        name="Back to School 2026",
        short="Back to School 2026",
        target_personas=["Family", "Value", "Convenience"],
        target_segments=["Easy_Eating", "Easy_Shopping", "One_Stop_Low_Price"],
        rationale=(
            "Back-to-School targets families with school-age children — Family "
            "and Value personas drive almost all of the incremental basket "
            "(lunch staples, snacks, beverages). Easy_Shopping and "
            "Easy_Eating segments historically convert at 1.6× the rate "
            "of Healthy_Foodies for this event."
        ),
        expected_lift_profile=(
            "Expected lift profile: +3–5% net sales/HH spread across a 4-week "
            "window. Frequency lift (visits/HH) typically larger than basket "
            "lift."
        ),
    ),
    "Thanksgiving 2026": EventPreset(
        name="Thanksgiving 2026",
        short="Thanksgiving 2026",
        target_personas=["Family", "Premium", "Wellness", "Convenience"],
        target_segments=["Easy_Eating", "Scratch_Foodies", "Healthy_Foodies",
                         "Easy_Shopping"],
        rationale=(
            "Thanksgiving is the highest-volume grocery week of the year. "
            "Almost all personas participate, but Family + Scratch_Foodies "
            "drive disproportionate incremental basket size. Value-only "
            "shoppers participate but with lower lift (they shop the "
            "holiday regardless of communication)."
        ),
        expected_lift_profile=(
            "Expected lift profile: +6–10% net sales/HH. Lift in units/HH "
            "typically tracks lift in net sales 1:1 (no premium-mix shift)."
        ),
    ),
    "Halloween 2026": EventPreset(
        name="Halloween 2026",
        short="Halloween 2026",
        target_personas=["Family", "Convenience", "Value"],
        target_segments=["Easy_Eating", "Easy_Shopping", "Chasing_Price"],
        rationale=(
            "Halloween is dominated by Family personas (candy + costume + "
            "party). Convenience and Value personas drive the second wave "
            "of last-minute purchases. Wellness and Premium personas "
            "under-index strongly and are excluded."
        ),
        expected_lift_profile=(
            "Expected lift profile: +4–7% net sales/HH. Push notifications "
            "in the final 72 hours typically drive the largest single-channel "
            "incremental contribution."
        ),
    ),
}


def list_events() -> list[str]:
    return list(EVENT_PRESETS.keys())


def apply_event_targeting(
    df: pd.DataFrame, event_name: str
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Filter the population to event-relevant households + return audit info.

    Returns
    -------
    df_filtered : the (possibly filtered) population.
    info : {
        "event": EventPreset,
        "n_before": int,
        "n_after": int,
        "drop_pct": float,
        "narrative_md": str,   # ready-to-render markdown narrative
    }
    """
    event = EVENT_PRESETS.get(event_name)
    if event is None:
        raise KeyError(f"Unknown event: {event_name}")

    n_before = len(df)
    if event_name.startswith("None"):
        df_filt = df.reset_index(drop=True)
    else:
        mask = pd.Series(False, index=df.index)
        if event.target_personas and "persona" in df.columns:
            mask = mask | df["persona"].isin(event.target_personas)
        if event.target_segments and "my_needs_segment" in df.columns:
            mask = mask | df["my_needs_segment"].isin(event.target_segments)
        # If neither column is present, fall back to keeping everyone.
        if mask.sum() == 0:
            mask = pd.Series(True, index=df.index)
        df_filt = df[mask].reset_index(drop=True)

    n_after = len(df_filt)
    drop_pct = 100.0 * (1 - n_after / n_before) if n_before else 0.0

    narrative = _render_event_narrative(event, n_before, n_after, drop_pct)

    return df_filt, {
        "event": event,
        "n_before": n_before,
        "n_after": n_after,
        "drop_pct": drop_pct,
        "narrative_md": narrative,
    }


def _render_event_narrative(
    event: EventPreset, n_before: int, n_after: int, drop_pct: float
) -> str:
    if event.name.startswith("None"):
        return (
            f"**Targeting:** No event filter applied — analyzing all "
            f"{n_before:,} reachable households."
        )

    bullets = []
    if event.target_personas:
        bullets.append(f"- **Target personas:** {', '.join(event.target_personas)}")
    if event.target_segments:
        bullets.append(f"- **Target segments:** {', '.join(event.target_segments)}")

    return (
        f"### Targeting reasoning · {event.name}\n\n"
        f"**Filtered to {n_after:,} of {n_before:,} reachable households "
        f"({100 - drop_pct:.1f}% retained).**\n\n"
        + "\n".join(bullets)
        + f"\n\n**Why these households:** {event.rationale}\n\n"
        f"**{event.expected_lift_profile}**"
    )
