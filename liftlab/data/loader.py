"""Load and validate a customer population from an uploaded CSV.

Lets users bring their own household-level data instead of using the
synthetic generator. Validates the schema and gives actionable error
messages so a non-technical user can fix their file and re-upload.
"""
from __future__ import annotations

from typing import IO, Union

import numpy as np
import pandas as pd

from .synthetic import channel_mix_label

REQUIRED_COLUMNS = [
    "household_id",
    "email_flag",
    "push_flag",
    "sms_flag",
    "pre_weekly_net_sales",
]

OPTIONAL_DEFAULTS: dict[str, object] = {
    "division_id": 1,
    "my_needs_segment": "Unknown",
    "persona": "Unknown",
    "facts_seg": "Unknown",
    "ecom_ind": 0,
    "rewards_engaged": 0,
}


class CSVValidationError(ValueError):
    """Raised when an uploaded CSV cannot be turned into a valid population."""


def load_population_from_csv(file_or_path: Union[str, IO]) -> pd.DataFrame:
    """Read, validate, type-coerce and channel-label an uploaded CSV.

    Returns a DataFrame in the exact same shape as `generate_population()`.
    """
    try:
        df = pd.read_csv(file_or_path)
    except Exception as e:
        raise CSVValidationError(
            f"Could not parse the file as CSV: {e}. "
            "Make sure it's a comma-separated values file with a header row."
        ) from e

    if df.empty:
        raise CSVValidationError("The uploaded CSV is empty.")

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise CSVValidationError(
            f"CSV is missing required columns: {missing}.\n\n"
            f"Required columns are: {REQUIRED_COLUMNS}.\n"
            f"Optional columns (filled with defaults if missing): "
            f"{list(OPTIONAL_DEFAULTS.keys())}."
        )

    if df["household_id"].duplicated().any():
        n_dupes = int(df["household_id"].duplicated().sum())
        raise CSVValidationError(
            f"Found {n_dupes:,} duplicate `household_id` values. "
            "Each household must appear exactly once."
        )

    for col, default in OPTIONAL_DEFAULTS.items():
        if col not in df.columns:
            df[col] = default

    try:
        df["household_id"] = pd.to_numeric(df["household_id"], errors="raise").astype(np.int64)
    except Exception as e:
        raise CSVValidationError(f"`household_id` must be integer: {e}") from e

    for c in ["email_flag", "push_flag", "sms_flag", "ecom_ind", "rewards_engaged"]:
        try:
            df[c] = pd.to_numeric(df[c], errors="raise").fillna(0).astype(np.int8)
        except Exception as e:
            raise CSVValidationError(f"`{c}` must be 0 or 1: {e}") from e
        bad = ~df[c].isin([0, 1])
        if bad.any():
            raise CSVValidationError(
                f"`{c}` contains values other than 0/1 ({int(bad.sum()):,} rows)."
            )

    try:
        df["division_id"] = pd.to_numeric(df["division_id"], errors="coerce").fillna(1).astype(np.int16)
    except Exception:
        df["division_id"] = 1
        df["division_id"] = df["division_id"].astype(np.int16)

    try:
        df["pre_weekly_net_sales"] = pd.to_numeric(df["pre_weekly_net_sales"], errors="raise").astype(float)
    except Exception as e:
        raise CSVValidationError(
            f"`pre_weekly_net_sales` must be numeric (dollars per week): {e}"
        ) from e
    if (df["pre_weekly_net_sales"] < 0).any():
        raise CSVValidationError(
            "`pre_weekly_net_sales` contains negative values. "
            "It should be the weekly $ spend baseline before the campaign."
        )

    for c in ["my_needs_segment", "persona", "facts_seg"]:
        df[c] = df[c].astype(str).fillna("Unknown")

    n_before = len(df)
    df = df[(df["email_flag"] + df["push_flag"] + df["sms_flag"]) > 0].reset_index(drop=True)
    n_after = len(df)
    if n_after == 0:
        raise CSVValidationError(
            "After filtering to reachable households (at least one of email/push/sms = 1), "
            "no rows remain."
        )

    df["channel_mix"] = channel_mix_label(df)
    df.attrs["rows_dropped_unreachable"] = n_before - n_after

    return df
