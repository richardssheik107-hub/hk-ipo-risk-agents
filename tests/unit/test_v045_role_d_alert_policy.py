from __future__ import annotations

import numpy as np
import pytest

from ipo_risk.modeling.alert_policy import (
    alert_budget_predictions,
    evaluate_alert_budget,
    select_development_alert_budget,
)


def test_alert_budget_is_ranked_and_ties_are_deterministic() -> None:
    predicted = alert_budget_predictions(
        ["case_c", "case_b", "case_a", "case_d"],
        [0.9, 0.5, 0.5, 0.1],
        0.5,
    )
    assert predicted.tolist() == [True, False, True, False]


def test_development_selection_uses_f2_and_prefers_smaller_tied_budget() -> None:
    case_ids = [f"case_{index}" for index in range(6)]
    labels = [1, 1, 0, 0, 0, 0]
    scores = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4]
    selected = select_development_alert_budget(
        case_ids,
        labels,
        scores,
        candidate_fractions=(1 / 3, 0.5),
    )
    assert selected.fraction == pytest.approx(1 / 3)
    assert selected.precision == 1.0
    assert selected.recall == 1.0
    assert selected.f2 == 1.0


def test_evaluation_reports_realized_budget_and_metrics() -> None:
    predicted, metrics = evaluate_alert_budget(
        ["a", "b", "c", "d"],
        [1, 0, 1, 0],
        [0.9, 0.8, 0.7, 0.6],
        0.5,
    )
    assert np.array_equal(predicted, np.asarray([True, True, False, False]))
    assert metrics["alert_count"] == 2
    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5


@pytest.mark.parametrize("fraction", [0.0, -0.1, 1.1])
def test_alert_budget_rejects_invalid_fraction(fraction: float) -> None:
    with pytest.raises(ValueError, match="fraction"):
        alert_budget_predictions(["a"], [0.5], fraction)
