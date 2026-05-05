"""Statistical tests for incrementality reports."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass
class TestResult:
    statistic: float
    p_value: float
    test_type: str

    def is_significant(self, alpha: float = 0.05) -> bool:
        return self.p_value < alpha


def welch_t_test(
    test_mean: float, test_std: float, test_n: int,
    control_mean: float, control_std: float, control_n: int,
) -> TestResult:
    """Welch's two-sample t-test on aggregated stats (no raw arrays needed)."""
    if test_n < 2 or control_n < 2:
        return TestResult(np.nan, np.nan, "welch_t")
    se = np.sqrt(test_std ** 2 / test_n + control_std ** 2 / control_n)
    if se == 0 or np.isnan(se):
        return TestResult(np.nan, np.nan, "welch_t")
    t_stat = (test_mean - control_mean) / se
    num = (test_std ** 2 / test_n + control_std ** 2 / control_n) ** 2
    denom = (
        (test_std ** 2 / test_n) ** 2 / (test_n - 1)
        + (control_std ** 2 / control_n) ** 2 / (control_n - 1)
    )
    df = num / denom if denom > 0 else max(test_n + control_n - 2, 1)
    p = 2 * (1 - stats.t.cdf(abs(t_stat), df))
    return TestResult(float(t_stat), float(p), "welch_t")


def two_proportion_z_test(
    test_successes: int, test_n: int,
    control_successes: int, control_n: int,
) -> TestResult:
    """Two-proportion z-test (chi-squared equivalent for 2x2)."""
    if test_n == 0 or control_n == 0:
        return TestResult(np.nan, np.nan, "two_prop_z")
    p1 = test_successes / test_n
    p2 = control_successes / control_n
    p_pool = (test_successes + control_successes) / (test_n + control_n)
    se = np.sqrt(p_pool * (1 - p_pool) * (1 / test_n + 1 / control_n))
    if se == 0:
        return TestResult(np.nan, np.nan, "two_prop_z")
    z = (p1 - p2) / se
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    return TestResult(float(z), float(p), "two_prop_z")
