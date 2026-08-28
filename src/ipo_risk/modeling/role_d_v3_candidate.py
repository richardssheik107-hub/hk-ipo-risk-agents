"""Bounded Development-only refinement of the Role-D v2 research candidate."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from ipo_risk.modeling.alert_policy import (
    evaluate_alert_budget,
    select_development_alert_budget,
)
from ipo_risk.modeling.lightgbm_modeling import build_pr_f_classifier
from ipo_risk.modeling.role_d_v2_candidate import ROLE_D_V2_CORE_REGIME_FEATURES


ROLE_D_V3_MODEL_POLICY_VERSION = "v045_role_d_bounded_backward_pruning_v1"
ROLE_D_V3_SELECTION_METRIC = "macro_forward_year_pr_auc"
ROLE_D_V3_MIN_FEATURE_COUNT = 4


@dataclass(frozen=True)
class V3CandidateStudy:
    summary: dict[str, Any]
    prediction_rows: list[dict[str, Any]]
    model_text: str


def role_d_v3_seed_positions(feature_names: Sequence[str]) -> tuple[int, ...]:
    """Return the governed seven-feature v2 seed contract."""

    names = tuple(feature_names)
    if len(names) != len(set(names)) or not names:
        raise ValueError("Role-D v3 feature names must be non-empty and unique")
    index = {name: position for position, name in enumerate(names)}
    missing = [name for name in ROLE_D_V2_CORE_REGIME_FEATURES if name not in index]
    if missing:
        raise ValueError("Role-D v3 is missing seed features: " + ", ".join(missing))
    return tuple(index[name] for name in ROLE_D_V2_CORE_REGIME_FEATURES)


def _forward_oof(
    x: np.ndarray,
    labels: np.ndarray,
    years: np.ndarray,
    positions: tuple[int, ...],
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    scores = np.full(len(labels), np.nan, dtype=float)
    folds: list[dict[str, Any]] = []
    for evaluation_year in (2021, 2022, 2023):
        train = years < evaluation_year
        evaluate = years == evaluation_year
        model = build_pr_f_classifier()
        model.fit(x[train][:, positions], labels[train])
        fold_scores = np.asarray(
            model.booster_.predict(x[evaluate][:, positions]), dtype=float
        )
        scores[evaluate] = fold_scores
        fold_labels = labels[evaluate]
        folds.append(
            {
                "train_years": sorted(set(int(value) for value in years[train])),
                "evaluation_year": evaluation_year,
                "train_count": int(train.sum()),
                "evaluation_count": int(evaluate.sum()),
                "pr_auc": float(average_precision_score(fold_labels, fold_scores)),
                "roc_auc": float(roc_auc_score(fold_labels, fold_scores)),
            }
        )
    return scores, folds


def _candidate_metrics(
    labels: np.ndarray,
    scores: np.ndarray,
    folds: list[dict[str, Any]],
) -> dict[str, Any]:
    available = np.isfinite(scores)
    return {
        "oof_count": int(available.sum()),
        "pooled_pr_auc": float(
            average_precision_score(labels[available], scores[available])
        ),
        "pooled_roc_auc": float(roc_auc_score(labels[available], scores[available])),
        "pooled_brier_score": float(
            brier_score_loss(labels[available], scores[available])
        ),
        "macro_forward_year_pr_auc": float(
            np.mean([fold["pr_auc"] for fold in folds])
        ),
        "minimum_forward_year_pr_auc": float(
            min(fold["pr_auc"] for fold in folds)
        ),
        "macro_forward_year_roc_auc": float(
            np.mean([fold["roc_auc"] for fold in folds])
        ),
        "folds": folds,
    }


def _selection_key(candidate: dict[str, Any]) -> tuple[Any, ...]:
    return (
        candidate[ROLE_D_V3_SELECTION_METRIC],
        candidate["minimum_forward_year_pr_auc"],
        candidate["pooled_pr_auc"],
        candidate["macro_forward_year_roc_auc"],
        -candidate["feature_count"],
        tuple(candidate["feature_names"]),
    )


def _evaluate_positions(
    *,
    x: np.ndarray,
    labels: np.ndarray,
    years: np.ndarray,
    feature_names: Sequence[str],
    positions: tuple[int, ...],
) -> tuple[dict[str, Any], np.ndarray]:
    scores, folds = _forward_oof(x, labels, years, positions)
    return (
        {
            "feature_count": len(positions),
            "feature_names": [feature_names[position] for position in positions],
            **_candidate_metrics(labels, scores, folds),
        },
        scores,
    )


def select_role_d_v3_features(
    *,
    feature_names: Sequence[str],
    feature_values: np.ndarray,
    labels: np.ndarray,
    years: np.ndarray,
) -> tuple[tuple[int, ...], np.ndarray, list[dict[str, Any]]]:
    """Greedily prune only the seven v2 features on Development forward folds."""

    if tuple(sorted(set(int(value) for value in years))) != (2020, 2021, 2022, 2023):
        raise ValueError("Role-D v3 selection accepts Development years 2020-2023 only")
    current_positions = role_d_v3_seed_positions(feature_names)
    current, current_scores = _evaluate_positions(
        x=feature_values,
        labels=labels,
        years=years,
        feature_names=feature_names,
        positions=current_positions,
    )
    rounds: list[dict[str, Any]] = [
        {"round": 0, "accepted": True, "selected": current, "candidates": [current]}
    ]
    round_number = 1
    while len(current_positions) > ROLE_D_V3_MIN_FEATURE_COUNT:
        evaluated: list[tuple[dict[str, Any], np.ndarray, tuple[int, ...]]] = []
        for removed_position in current_positions:
            candidate_positions = tuple(
                position
                for position in current_positions
                if position != removed_position
            )
            candidate, scores = _evaluate_positions(
                x=feature_values,
                labels=labels,
                years=years,
                feature_names=feature_names,
                positions=candidate_positions,
            )
            candidate["removed_feature"] = feature_names[removed_position]
            evaluated.append((candidate, scores, candidate_positions))
        best, best_scores, best_positions = max(
            evaluated, key=lambda item: _selection_key(item[0])
        )
        accepted = (
            best[ROLE_D_V3_SELECTION_METRIC]
            > current[ROLE_D_V3_SELECTION_METRIC] + 1e-12
        )
        rounds.append(
            {
                "round": round_number,
                "accepted": accepted,
                "selected": best if accepted else current,
                "candidates": sorted(
                    (item[0] for item in evaluated),
                    key=lambda row: tuple(row["feature_names"]),
                ),
            }
        )
        if not accepted:
            break
        current = best
        current_scores = best_scores
        current_positions = best_positions
        round_number += 1
    return current_positions, current_scores, rounds


def _fixed_threshold_metrics(
    labels: np.ndarray,
    scores: np.ndarray,
    threshold: float = 0.5,
) -> dict[str, Any]:
    predicted = scores >= threshold
    return {
        "classification_threshold": threshold,
        "alert_count": int(predicted.sum()),
        "precision": float(precision_score(labels, predicted, zero_division=0)),
        "recall": float(recall_score(labels, predicted, zero_division=0)),
        "f1": float(f1_score(labels, predicted, zero_division=0)),
    }


def run_role_d_v3_candidate(
    *,
    case_ids: Sequence[str],
    years: Sequence[int],
    feature_names: Sequence[str],
    feature_values: Sequence[Sequence[float]],
    labels: Sequence[bool | int],
    raw_returns: Sequence[float],
    frozen_pr_f_metrics: dict[str, Any],
) -> V3CandidateStudy:
    """Select on Development only, then evaluate the frozen v3 candidate once."""

    if not (
        len(case_ids)
        == len(years)
        == len(feature_values)
        == len(labels)
        == len(raw_returns)
    ):
        raise ValueError("Role-D v3 input row counts disagree")
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("Role-D v3 case IDs must be unique")
    year_array = np.asarray(years, dtype=int)
    if np.any(year_array >= 2025):
        raise ValueError("Role-D v3 refuses 2025 Blind y")
    x = np.asarray(feature_values, dtype=float)
    y = np.asarray(labels, dtype=int)
    returns = np.asarray(raw_returns, dtype=float)
    development = year_array <= 2023
    validation = year_array == 2024
    if int(development.sum()) != 354 or int(validation.sum()) != 70:
        raise ValueError("Role-D v3 governed cohort coverage drift")

    selected_positions, selected_oof, rounds = select_role_d_v3_features(
        feature_names=feature_names,
        feature_values=x[development],
        labels=y[development],
        years=year_array[development],
    )
    oof_available = np.isfinite(selected_oof)
    development_indices = np.flatnonzero(development)
    oof_case_ids = [
        case_ids[development_indices[index]]
        for index in np.flatnonzero(oof_available)
    ]
    alert_selection = select_development_alert_budget(
        oof_case_ids,
        y[development][oof_available],
        selected_oof[oof_available],
    )

    model = build_pr_f_classifier()
    model.fit(x[development][:, selected_positions], y[development])
    validation_scores = np.asarray(
        model.booster_.predict(x[validation][:, selected_positions]), dtype=float
    )
    validation_indices = np.flatnonzero(validation)
    validation_ids = [case_ids[index] for index in validation_indices]
    validation_predicted, alert_metrics = evaluate_alert_budget(
        validation_ids,
        y[validation],
        validation_scores,
        alert_selection.fraction,
    )
    ranking_metrics = {
        "roc_auc": float(roc_auc_score(y[validation], validation_scores)),
        "pr_auc": float(average_precision_score(y[validation], validation_scores)),
        "brier_score": float(brier_score_loss(y[validation], validation_scores)),
    }
    model_text = model.booster_.model_to_string()
    gain = model.booster_.feature_importance(importance_type="gain")
    split = model.booster_.feature_importance(importance_type="split")
    importance = sorted(
        (
            {
                "feature": feature_names[position],
                "gain": float(gain[index]),
                "split": int(split[index]),
            }
            for index, position in enumerate(selected_positions)
        ),
        key=lambda row: (-row["gain"], row["feature"]),
    )
    prediction_rows = [
        {
            "case_id": case_ids[row_index],
            "cohort_year": 2024,
            "actual_significant_drop_5d": bool(y[row_index]),
            "actual_return_5d": float(returns[row_index]),
            "v3_score": float(validation_scores[local_index]),
            "v3_fixed_threshold_prediction": bool(
                validation_scores[local_index] >= 0.5
            ),
            "v3_alert_budget_prediction": bool(validation_predicted[local_index]),
        }
        for local_index, row_index in enumerate(validation_indices)
    ]
    selected = rounds[-1]["selected"]
    baseline_ranking = {
        "roc_auc": float(frozen_pr_f_metrics["roc_auc"]),
        "pr_auc": float(frozen_pr_f_metrics["pr_auc"]),
        "brier_score": float(frozen_pr_f_metrics["brier_score"]),
    }
    summary = {
        "policy_version": ROLE_D_V3_MODEL_POLICY_VERSION,
        "status": "complete_research_candidate_pending_a_decision",
        "model_family": "lightgbm_binary_frozen_pr_f_parameters",
        "selection_protocol": {
            "split": "2021_2023_expanding_year_forward_oof",
            "method": "bounded_backward_elimination_from_v2_core_regime",
            "primary_metric": ROLE_D_V3_SELECTION_METRIC,
            "minimum_feature_count": ROLE_D_V3_MIN_FEATURE_COUNT,
            "validation_labels_used_for_selection": False,
            "selected_feature_count": len(selected_positions),
            "selected_feature_names": [
                feature_names[position] for position in selected_positions
            ],
            "selected_development_metrics": selected,
            "rounds": rounds,
        },
        "development_alert_policy": {
            "objective": "F2",
            "selected_fraction": alert_selection.fraction,
            "oof_alert_count": alert_selection.alert_count,
            "oof_precision": alert_selection.precision,
            "oof_recall": alert_selection.recall,
            "oof_f1": alert_selection.f1,
            "oof_f2": alert_selection.f2,
        },
        "validation": {
            "sample_count": int(validation.sum()),
            "ranking_metrics": ranking_metrics,
            "fixed_threshold_metrics": _fixed_threshold_metrics(
                y[validation], validation_scores
            ),
            "development_selected_alert_metrics": alert_metrics,
        },
        "frozen_pr_f_baseline": baseline_ranking,
        "ranking_metric_deltas": {
            key: ranking_metrics[key] - baseline_ranking[key]
            for key in ("roc_auc", "pr_auc")
        }
        | {
            "brier_reduction": baseline_ranking["brier_score"]
            - ranking_metrics["brier_score"]
        },
        "global_feature_importance": importance,
        "classifier_model_sha256": hashlib.sha256(
            model_text.encode("utf-8")
        ).hexdigest(),
        "promotion": {
            "decision_owner": "A",
            "status": "pending_a_governance_decision",
            "replaces_frozen_pr_f": False,
            "fresh_unseen_holdout_available": False,
            "reason": (
                "2024 Validation was previously observed for v2; v3 cannot be "
                "declared a new unbiased frozen replacement without A review."
            ),
        },
        "frozen_pr_f_unchanged": True,
        "blind_2025_y_accessed": False,
    }
    return V3CandidateStudy(summary, prediction_rows, model_text)
