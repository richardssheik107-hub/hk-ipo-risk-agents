"""Versioned Development-only Role-D feature/model candidate study."""

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


ROLE_D_V2_MODEL_POLICY_VERSION = "v045_role_d_temporal_feature_pruning_v1"
ROLE_D_V2_SELECTION_METRIC = "macro_forward_year_pr_auc"
ROLE_D_V2_CORE_REGIME_FEATURES = (
    "ipo_count_30d",
    "ipo_count_60d",
    "recent_ipo_break_rate",
    "recent_ipo_return_5d",
    "same_industry_ipo_count_180d",
    "same_industry_recent_break_rate",
    "same_industry_recent_return_5d",
)


@dataclass(frozen=True)
class CandidateStudy:
    summary: dict[str, Any]
    prediction_rows: list[dict[str, Any]]
    model_text: str


def role_d_v2_feature_groups(
    feature_names: Sequence[str],
) -> dict[str, tuple[int, ...]]:
    """Return the small, domain-defined feature-pruning candidate set."""

    names = tuple(feature_names)
    if len(names) != len(set(names)) or not names:
        raise ValueError("Role-D v2 feature names must be non-empty and unique")
    index = {name: position for position, name in enumerate(names)}
    missing_core = [name for name in ROLE_D_V2_CORE_REGIME_FEATURES if name not in index]
    if missing_core:
        raise ValueError(
            "Role-D v2 is missing core regime features: " + ", ".join(missing_core)
        )
    groups = {
        "all_30": tuple(range(len(names))),
        "raw_only": tuple(
            position
            for position, name in enumerate(names)
            if not name.endswith("__missing")
        ),
        "global_only": tuple(
            position
            for position, name in enumerate(names)
            if not name.startswith("same_industry")
        ),
        "sentiment_and_samples": tuple(
            position
            for position, name in enumerate(names)
            if not name.endswith("__missing")
            and any(
                token in name
                for token in ("break_rate", "return_5d", "sample_count")
            )
        ),
        "core_regime": tuple(index[name] for name in ROLE_D_V2_CORE_REGIME_FEATURES),
    }
    if any(not positions for positions in groups.values()):
        raise ValueError("Role-D v2 feature group cannot be empty")
    return groups


def _forward_oof(
    x: np.ndarray,
    labels: np.ndarray,
    years: np.ndarray,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    scores = np.full(len(labels), np.nan, dtype=float)
    folds: list[dict[str, Any]] = []
    for evaluation_year in (2021, 2022, 2023):
        train = years < evaluation_year
        evaluate = years == evaluation_year
        model = build_pr_f_classifier()
        model.fit(x[train], labels[train])
        fold_scores = np.asarray(
            model.booster_.predict(x[evaluate]), dtype=float
        )
        scores[evaluate] = fold_scores
        fold_labels = labels[evaluate]
        folds.append(
            {
                "train_years": sorted(set(int(value) for value in years[train])),
                "evaluation_year": evaluation_year,
                "train_count": int(train.sum()),
                "evaluation_count": int(evaluate.sum()),
                "pr_auc": float(
                    average_precision_score(fold_labels, fold_scores)
                ),
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
        "macro_forward_year_roc_auc": float(
            np.mean([fold["roc_auc"] for fold in folds])
        ),
        "folds": folds,
    }


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


def run_role_d_v2_candidate(
    *,
    case_ids: Sequence[str],
    years: Sequence[int],
    feature_names: Sequence[str],
    feature_values: Sequence[Sequence[float]],
    labels: Sequence[bool | int],
    raw_returns: Sequence[float],
    frozen_pr_f_metrics: dict[str, Any],
) -> CandidateStudy:
    """Select on Development only, then evaluate the frozen candidate on 2024."""

    if not (
        len(case_ids)
        == len(years)
        == len(feature_values)
        == len(labels)
        == len(raw_returns)
    ):
        raise ValueError("Role-D v2 input row counts disagree")
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("Role-D v2 case IDs must be unique")
    year_array = np.asarray(years, dtype=int)
    if np.any(year_array >= 2025):
        raise ValueError("Role-D v2 refuses 2025 Blind y")
    x = np.asarray(feature_values, dtype=float)
    y = np.asarray(labels, dtype=int)
    returns = np.asarray(raw_returns, dtype=float)
    groups = role_d_v2_feature_groups(feature_names)
    development = year_array <= 2023
    validation = year_array == 2024
    if int(development.sum()) != 354 or int(validation.sum()) != 70:
        raise ValueError("Role-D v2 governed cohort coverage drift")

    candidate_rows: list[dict[str, Any]] = []
    oof_by_group: dict[str, np.ndarray] = {}
    for group_name, positions in groups.items():
        scores, folds = _forward_oof(x[:, positions], y, year_array)
        metrics = _candidate_metrics(y, scores, folds)
        candidate_rows.append(
            {
                "feature_group": group_name,
                "feature_count": len(positions),
                "feature_names": [feature_names[position] for position in positions],
                **metrics,
            }
        )
        oof_by_group[group_name] = scores
    selected = max(
        candidate_rows,
        key=lambda row: (
            row[ROLE_D_V2_SELECTION_METRIC],
            row["pooled_pr_auc"],
            row["macro_forward_year_roc_auc"],
            -row["feature_count"],
            row["feature_group"],
        ),
    )
    selected_name = selected["feature_group"]
    selected_positions = groups[selected_name]
    selected_oof = oof_by_group[selected_name]
    oof_available = np.isfinite(selected_oof)
    oof_ids = [
        case_ids[index] for index in np.flatnonzero(oof_available)
    ]
    alert_selection = select_development_alert_budget(
        oof_ids,
        y[oof_available],
        selected_oof[oof_available],
    )

    model = build_pr_f_classifier()
    model.fit(x[development][:, selected_positions], y[development])
    validation_scores = np.asarray(
        model.booster_.predict(x[validation][:, selected_positions]), dtype=float
    )
    validation_ids = [case_ids[index] for index in np.flatnonzero(validation)]
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
    fixed_metrics = _fixed_threshold_metrics(y[validation], validation_scores)
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
    prediction_rows = []
    validation_indices = np.flatnonzero(validation)
    for local_index, row_index in enumerate(validation_indices):
        prediction_rows.append(
            {
                "case_id": case_ids[row_index],
                "cohort_year": 2024,
                "actual_significant_drop_5d": bool(y[row_index]),
                "actual_return_5d": float(returns[row_index]),
                "v2_score": float(validation_scores[local_index]),
                "v2_fixed_threshold_prediction": bool(
                    validation_scores[local_index] >= 0.5
                ),
                "v2_alert_budget_prediction": bool(
                    validation_predicted[local_index]
                ),
            }
        )

    baseline_ranking = {
        "roc_auc": float(frozen_pr_f_metrics["roc_auc"]),
        "pr_auc": float(frozen_pr_f_metrics["pr_auc"]),
        "brier_score": float(frozen_pr_f_metrics["brier_score"]),
    }
    summary = {
        "policy_version": ROLE_D_V2_MODEL_POLICY_VERSION,
        "status": "complete_development_selected_2024_evaluated",
        "model_family": "lightgbm_binary_frozen_pr_f_parameters",
        "selection_protocol": {
            "split": "2021_2023_expanding_year_forward_oof",
            "primary_metric": ROLE_D_V2_SELECTION_METRIC,
            "candidate_feature_group_count": len(candidate_rows),
            "validation_labels_used_for_selection": False,
            "selected_feature_group": selected_name,
            "selected_feature_count": len(selected_positions),
            "selected_feature_names": selected["feature_names"],
            "candidate_results": sorted(
                candidate_rows, key=lambda row: row["feature_group"]
            ),
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
            "fixed_threshold_metrics": fixed_metrics,
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
        "frozen_pr_f_unchanged": True,
        "blind_2025_y_accessed": False,
    }
    return CandidateStudy(summary, prediction_rows, model_text)
