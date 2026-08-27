"""Development-only alert-budget policy for uncalibrated model scores.

The frozen PR-F score remains unchanged.  This module only converts a batch of
uncalibrated scores into a deterministic alert set after an alert fraction has
been selected on Development forward-OOF predictions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from sklearn.metrics import fbeta_score, precision_score, recall_score


ROLE_D_ALERT_POLICY_VERSION = "v045_role_d_development_alert_budget_v1"
ROLE_D_ALERT_BETA = 2.0
ROLE_D_ALERT_FRACTIONS = tuple(index / 40 for index in range(4, 21))


@dataclass(frozen=True)
class AlertBudgetSelection:
    """Frozen Development-only choice and its OOF evidence."""

    fraction: float
    alert_count: int
    precision: float
    recall: float
    f1: float
    f2: float


def alert_budget_predictions(
    case_ids: Sequence[str],
    scores: Sequence[float],
    fraction: float,
) -> np.ndarray:
    """Select the highest scores with deterministic case-ID tie breaking."""

    if len(case_ids) != len(scores):
        raise ValueError("alert-policy case IDs and scores have different lengths")
    if not case_ids:
        raise ValueError("alert-policy scores must be non-empty")
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("alert-policy case IDs must be unique")
    if not 0.0 < fraction <= 1.0:
        raise ValueError("alert-policy fraction must be in (0, 1]")
    score_array = np.asarray(scores, dtype=float)
    if not np.all(np.isfinite(score_array)):
        raise ValueError("alert-policy scores must be finite")

    count = max(1, int(np.ceil(len(case_ids) * fraction)))
    ranked = sorted(
        range(len(case_ids)),
        key=lambda index: (-score_array[index], case_ids[index]),
    )
    predicted = np.zeros(len(case_ids), dtype=bool)
    predicted[ranked[:count]] = True
    return predicted


def _metrics(labels: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    return {
        "precision": float(precision_score(labels, predicted, zero_division=0)),
        "recall": float(recall_score(labels, predicted, zero_division=0)),
        "f1": float(fbeta_score(labels, predicted, beta=1.0, zero_division=0)),
        "f2": float(
            fbeta_score(labels, predicted, beta=ROLE_D_ALERT_BETA, zero_division=0)
        ),
    }


def select_development_alert_budget(
    case_ids: Sequence[str],
    labels: Sequence[bool | int],
    scores: Sequence[float],
    *,
    candidate_fractions: Sequence[float] = ROLE_D_ALERT_FRACTIONS,
) -> AlertBudgetSelection:
    """Choose a high-recall alert fraction using Development OOF labels only.

    F2 is primary because Role D gives higher weight to significant-drop
    identification.  Ties prefer higher recall, then higher precision, then a
    smaller alert budget.
    """

    label_array = np.asarray(labels, dtype=int)
    if len(label_array) != len(case_ids):
        raise ValueError("alert-policy labels and case IDs have different lengths")
    if set(np.unique(label_array)) - {0, 1}:
        raise ValueError("alert-policy labels must be binary")
    if len(np.unique(label_array)) != 2:
        raise ValueError("alert-policy Development OOF labels require both classes")
    fractions = tuple(float(value) for value in candidate_fractions)
    if not fractions:
        raise ValueError("alert-policy candidate fractions must be non-empty")

    candidates: list[tuple[tuple[float, float, float, float], AlertBudgetSelection]] = []
    for fraction in fractions:
        predicted = alert_budget_predictions(case_ids, scores, fraction)
        metrics = _metrics(label_array, predicted)
        selection = AlertBudgetSelection(
            fraction=fraction,
            alert_count=int(predicted.sum()),
            precision=metrics["precision"],
            recall=metrics["recall"],
            f1=metrics["f1"],
            f2=metrics["f2"],
        )
        key = (
            selection.f2,
            selection.recall,
            selection.precision,
            -selection.fraction,
        )
        candidates.append((key, selection))
    return max(candidates, key=lambda item: item[0])[1]


def evaluate_alert_budget(
    case_ids: Sequence[str],
    labels: Sequence[bool | int],
    scores: Sequence[float],
    fraction: float,
) -> tuple[np.ndarray, dict[str, float | int]]:
    """Apply a frozen fraction and return classification metrics."""

    predicted = alert_budget_predictions(case_ids, scores, fraction)
    label_array = np.asarray(labels, dtype=int)
    metrics = _metrics(label_array, predicted)
    return predicted, {
        "sample_count": len(case_ids),
        "alert_count": int(predicted.sum()),
        "alert_fraction_realized": float(predicted.mean()),
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "f1": metrics["f1"],
        "f2": metrics["f2"],
    }
