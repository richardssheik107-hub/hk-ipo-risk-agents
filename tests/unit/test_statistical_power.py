"""Guards for the AUC comparison power utility."""
from __future__ import annotations

import math

import pytest

from ipo_risk.modeling.statistical_power import (
    assess_comparison,
    minimum_detectable_auc_difference,
)


def test_threshold_shrinks_with_sample_size() -> None:
    small = minimum_detectable_auc_difference(3, 7)
    oracle_validation = minimum_detectable_auc_difference(7, 12)
    full_production = minimum_detectable_auc_difference(25, 45)
    development = minimum_detectable_auc_difference(110, 258)
    assert small > oracle_validation > full_production > development
    assert round(development, 2) == 0.09


def test_degenerate_cohorts_are_unresolvable_rather_than_zero() -> None:
    assert minimum_detectable_auc_difference(0, 10) == math.inf
    assert minimum_detectable_auc_difference(10, 0) == math.inf


def test_frozen_pr_e_gaps_fall_below_their_own_resolution_limit() -> None:
    """The two gaps PR-E reports on 2024, placed against their cohorts.

    PR-E measured M ROC-AUC 0.5671 with a PR-AUC near 0.36, so the class split is
    roughly 36% positive.  Both reported gaps land far inside the noise floor.
    """
    oracle = assess_comparison(-0.0571, 7, 12, assumed_auc=0.567)
    production = assess_comparison(-0.0157, 25, 45, assumed_auc=0.567)
    for result in (oracle, production):
        assert not result.resolvable
        assert result.fraction_of_threshold < 0.2
        assert "sign is not informative" in result.statement()
    assert round(oracle.minimum_detectable_difference, 2) == 0.39
    assert round(production.minimum_detectable_difference, 2) == 0.20


def test_a_large_gap_is_reported_as_resolvable() -> None:
    result = assess_comparison(0.25, 110, 258)
    assert result.resolvable
    assert result.fraction_of_threshold > 1
    assert "reaches the minimum detectable difference" in result.statement()


@pytest.mark.parametrize("assumed_auc", [0.55, 0.70, 0.85])
def test_statement_always_names_the_cohort(assumed_auc: float) -> None:
    statement = assess_comparison(0.01, 7, 12, assumed_auc=assumed_auc).statement()
    assert "7 positive / 12 negative" in statement
