"""Statistical power for AUC comparisons between two evaluation arms.

PR-E reports `PM - M`, `OM - M` and `OM - PM` as point estimates.  On cohorts of
this size those differences can be far smaller than what the sample can resolve,
in which case the sign carries no information.  This module makes that limit
explicit so an underpowered comparison is never read as a null finding.

It computes nothing about any particular run; callers supply the class counts.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

DEFAULT_ASSUMED_AUC = 0.70
Z_95 = 1.96


@dataclass(frozen=True)
class ComparisonPower:
    """An observed arm-to-arm gap placed against what the cohort can resolve."""

    observed_difference: float
    minimum_detectable_difference: float
    positive_count: int
    negative_count: int
    assumed_auc: float

    @property
    def resolvable(self) -> bool:
        return abs(self.observed_difference) >= self.minimum_detectable_difference

    @property
    def fraction_of_threshold(self) -> float:
        if self.minimum_detectable_difference == 0:
            return math.inf
        return abs(self.observed_difference) / self.minimum_detectable_difference

    def statement(self) -> str:
        """One sentence safe to paste into a report."""
        if self.resolvable:
            return (
                f"observed gap {self.observed_difference:+.4f} reaches the minimum detectable "
                f"difference of {self.minimum_detectable_difference:.3f} for this cohort "
                f"({self.positive_count} positive / {self.negative_count} negative)"
            )
        return (
            f"observed gap {self.observed_difference:+.4f} is {self.fraction_of_threshold:.0%} of the "
            f"minimum detectable difference of {self.minimum_detectable_difference:.3f} for this cohort "
            f"({self.positive_count} positive / {self.negative_count} negative); "
            "its sign is not informative at this sample size"
        )


def minimum_detectable_auc_difference(
    positive_count: int,
    negative_count: int,
    *,
    assumed_auc: float = DEFAULT_ASSUMED_AUC,
) -> float:
    """Smallest AUC gap two arms of this size could distinguish at 95% confidence.

    Hanley-McNeil standard error for one AUC, widened by sqrt(2) for a two-arm
    comparison.  Treating the arms as independent is conservative for paired arms
    evaluated on the same cases, so the real threshold is somewhat lower -- but not
    by the order of magnitude that would change any conclusion drawn from it.
    """
    if positive_count < 1 or negative_count < 1:
        return math.inf
    q1 = assumed_auc / (2 - assumed_auc)
    q2 = 2 * assumed_auc**2 / (1 + assumed_auc)
    variance = (
        assumed_auc * (1 - assumed_auc)
        + (positive_count - 1) * (q1 - assumed_auc**2)
        + (negative_count - 1) * (q2 - assumed_auc**2)
    ) / (positive_count * negative_count)
    return Z_95 * math.sqrt(2 * variance)


def assess_comparison(
    observed_difference: float,
    positive_count: int,
    negative_count: int,
    *,
    assumed_auc: float = DEFAULT_ASSUMED_AUC,
) -> ComparisonPower:
    """Place an observed arm-to-arm gap against this cohort's resolution limit."""
    return ComparisonPower(
        observed_difference=float(observed_difference),
        minimum_detectable_difference=minimum_detectable_auc_difference(
            positive_count, negative_count, assumed_auc=assumed_auc
        ),
        positive_count=int(positive_count),
        negative_count=int(negative_count),
        assumed_auc=float(assumed_auc),
    )
