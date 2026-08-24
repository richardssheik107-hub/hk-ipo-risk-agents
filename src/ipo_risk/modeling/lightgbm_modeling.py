"""Deterministic PR-F LightGBM models and native SHAP contributions."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from math import sqrt
from typing import Any

import lightgbm as lgb
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)

from ipo_risk.schemas.canonical_modeling import V04CanonicalModelMatrix


PR_F_MODEL_POLICY_VERSION = "v04_pr_f_lightgbm_policy_v1"
PR_F_RANDOM_SEED = 20260822
PR_F_CLASSIFICATION_THRESHOLD = 0.5
PR_F_CALIBRATION_BINS = 10


@dataclass(frozen=True)
class LightGBMRun:
    artifact: dict[str, Any]
    classifier_model_text: str
    regressor_model_text: str


def _classifier() -> lgb.LGBMClassifier:
    return lgb.LGBMClassifier(
        objective="binary",
        n_estimators=200,
        learning_rate=0.03,
        num_leaves=15,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        random_state=PR_F_RANDOM_SEED,
        deterministic=True,
        force_col_wise=True,
        n_jobs=1,
        verbosity=-1,
    )


def _regressor() -> lgb.LGBMRegressor:
    return lgb.LGBMRegressor(
        objective="regression_l2",
        n_estimators=200,
        learning_rate=0.03,
        num_leaves=15,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        random_state=PR_F_RANDOM_SEED,
        deterministic=True,
        force_col_wise=True,
        n_jobs=1,
        verbosity=-1,
    )


def _xy(matrix: V04CanonicalModelMatrix):
    return (
        np.asarray(matrix.feature_values, dtype=float),
        np.asarray(matrix.poor_performer_5d, dtype=int),
        np.asarray(matrix.raw_return_5d, dtype=float),
    )


def _case_years(
    matrix: V04CanonicalModelMatrix,
    cohort_year_by_case: Mapping[str, int],
) -> tuple[int, ...]:
    years: list[int] = []
    for case_id in matrix.case_ids:
        if case_id not in cohort_year_by_case:
            raise ValueError(f"missing governed cohort year for {case_id}")
        years.append(int(cohort_year_by_case[case_id]))
    return tuple(sorted(set(years)))


def _classification_metrics(y, probability):
    prediction = (probability >= PR_F_CLASSIFICATION_THRESHOLD).astype(int)
    both = len(np.unique(y)) == 2
    return {
        "sample_count": int(len(y)),
        "positive_rate": float(np.mean(y)),
        "classification_threshold": PR_F_CLASSIFICATION_THRESHOLD,
        "accuracy": float(accuracy_score(y, prediction)),
        "precision": float(precision_score(y, prediction, zero_division=0)),
        "recall": float(recall_score(y, prediction, zero_division=0)),
        "f1": float(f1_score(y, prediction, zero_division=0)),
        "brier_score": float(brier_score_loss(y, probability)),
        "roc_auc": float(roc_auc_score(y, probability)) if both else None,
        "pr_auc": float(average_precision_score(y, probability)) if both else None,
    }


def _regression_metrics(y, prediction):
    return {
        "sample_count": int(len(y)),
        "mae": float(mean_absolute_error(y, prediction)),
        "rmse": float(sqrt(mean_squared_error(y, prediction))),
        "r2": float(r2_score(y, prediction)) if len(y) >= 2 else None,
    }


def _calibration_assessment(y, probability) -> dict[str, Any]:
    """Describe fixed-bin reliability without fitting a calibrator on Validation."""

    bin_index = np.minimum(
        (np.asarray(probability, dtype=float) * PR_F_CALIBRATION_BINS).astype(int),
        PR_F_CALIBRATION_BINS - 1,
    )
    rows: list[dict[str, Any]] = []
    weighted_gap = 0.0
    max_gap = 0.0
    for index in range(PR_F_CALIBRATION_BINS):
        mask = bin_index == index
        if not np.any(mask):
            continue
        mean_score = float(np.mean(probability[mask]))
        observed_rate = float(np.mean(y[mask]))
        gap = abs(mean_score - observed_rate)
        count = int(np.sum(mask))
        weighted_gap += count * gap
        max_gap = max(max_gap, gap)
        rows.append(
            {
                "lower": index / PR_F_CALIBRATION_BINS,
                "upper": (index + 1) / PR_F_CALIBRATION_BINS,
                "count": count,
                "mean_score": mean_score,
                "observed_rate": observed_rate,
                "absolute_gap": gap,
            }
        )
    return {
        "status": "assessment_only_uncalibrated",
        "score_semantics": "uncalibrated_model_score",
        "method": "fixed_equal_width_reliability_bins",
        "requested_bin_count": PR_F_CALIBRATION_BINS,
        "nonempty_bin_count": len(rows),
        "expected_calibration_error": weighted_gap / len(y),
        "maximum_calibration_error": max_gap,
        "reliability_bins": rows,
    }


def _error_analysis(
    case_ids,
    binary_actual,
    probability,
    raw_actual,
    raw_prediction,
) -> dict[str, Any]:
    """Return deterministic holdout classification and return-error diagnostics."""

    predicted = (probability >= PR_F_CLASSIFICATION_THRESHOLD).astype(int)
    classification_rows = []
    for case_id, actual, score, predicted_value in zip(
        case_ids,
        binary_actual,
        probability,
        predicted,
        strict=True,
    ):
        if int(actual) == int(predicted_value):
            continue
        classification_rows.append(
            {
                "case_id": case_id,
                "actual": bool(actual),
                "predicted": bool(predicted_value),
                "score": float(score),
                "error_confidence": float(score if predicted_value else 1.0 - score),
            }
        )
    classification_rows.sort(
        key=lambda row: (-row["error_confidence"], row["case_id"])
    )
    regression_rows = [
        {
            "case_id": case_id,
            "actual_return_5d": float(actual),
            "predicted_return_5d": float(prediction),
            "signed_error": float(prediction - actual),
            "absolute_error": float(abs(prediction - actual)),
        }
        for case_id, actual, prediction in zip(
            case_ids, raw_actual, raw_prediction, strict=True
        )
    ]
    regression_rows.sort(key=lambda row: (-row["absolute_error"], row["case_id"]))
    return {
        "classification": {
            "false_positive_count": int(np.sum((predicted == 1) & (binary_actual == 0))),
            "false_negative_count": int(np.sum((predicted == 0) & (binary_actual == 1))),
            "top_misclassifications": classification_rows[:10],
        },
        "regression": {
            "mean_signed_error": float(np.mean(raw_prediction - raw_actual)),
            "top_absolute_errors": regression_rows[:10],
        },
    }


def _component(name: str) -> str:
    return name.split("__", 1)[0] if "__" in name else "unclassified"


def _explain(
    model: lgb.LGBMClassifier,
    matrix: V04CanonicalModelMatrix,
    x: np.ndarray,
) -> dict[str, Any]:
    names = matrix.feature_names
    booster = model.booster_
    gain = booster.feature_importance(importance_type="gain")
    split = booster.feature_importance(importance_type="split")
    contributions = np.asarray(booster.predict(x, pred_contrib=True), dtype=float)
    if contributions.shape[1] != len(names) + 1:
        raise RuntimeError("LightGBM contribution width does not match feature manifest")
    shap_values = contributions[:, :-1]
    global_rows = sorted(
        (
            {
                "feature": name,
                "component": _component(name),
                "gain": float(gain[index]),
                "split": int(split[index]),
                "mean_abs_shap": float(np.mean(np.abs(shap_values[:, index]))),
            }
            for index, name in enumerate(names)
        ),
        key=lambda row: (-row["mean_abs_shap"], row["feature"]),
    )
    group_totals: dict[str, float] = {}
    for row in global_rows:
        group_totals[row["component"]] = group_totals.get(row["component"], 0.0) + row[
            "mean_abs_shap"
        ]
    per_case = []
    for row_index, case_id in enumerate(matrix.case_ids):
        drivers = sorted(
            (
                {
                    "feature": name,
                    "component": _component(name),
                    "feature_value": (
                        None if np.isnan(x[row_index, index]) else float(x[row_index, index])
                    ),
                    "shap_value": float(shap_values[row_index, index]),
                }
                for index, name in enumerate(names)
            ),
            key=lambda row: (-abs(row["shap_value"]), row["feature"]),
        )[:10]
        per_case.append(
            {
                "case_id": case_id,
                "base_value": float(contributions[row_index, -1]),
                "top_drivers": drivers,
            }
        )
    return {
        "contribution_method": "lightgbm_native_pred_contrib_shap",
        "global_feature_importance": global_rows,
        "feature_group_mean_abs_shap": dict(sorted(group_totals.items())),
        "single_ipo_drivers": per_case,
    }


def _validate_holdout(development, validation, cohort_year_by_case):
    fields = (
        "feature_group",
        "cohort",
        "feature_manifest_hash",
        "feature_names",
        "target_policy_hash",
        "target_threshold_hash",
    )
    mismatches = [field for field in fields if getattr(development, field) != getattr(validation, field)]
    if mismatches:
        raise ValueError("LightGBM Development/Validation mismatch: " + ", ".join(mismatches))
    if development.dataset_split.value != "development" or validation.dataset_split.value != "validation":
        raise ValueError("LightGBM holdout requires Development then Validation")
    if _case_years(development, cohort_year_by_case) != (2020, 2021, 2022, 2023):
        raise ValueError("formal LightGBM Development must contain 2020-2023")
    if _case_years(validation, cohort_year_by_case) != (2024,):
        raise ValueError("formal LightGBM Validation must contain 2024 only")


def train_lightgbm_holdout(
    development: V04CanonicalModelMatrix,
    validation: V04CanonicalModelMatrix,
    *,
    cohort_year_by_case: Mapping[str, int],
) -> LightGBMRun:
    """Train fixed-policy models on Development and evaluate/explain 2024."""

    _validate_holdout(development, validation, cohort_year_by_case)
    train_x, train_y, train_raw = _xy(development)
    valid_x, valid_y, valid_raw = _xy(validation)
    if len(np.unique(train_y)) < 2:
        raise ValueError("Development classification target requires both classes")
    classifier = _classifier()
    classifier.fit(train_x, train_y)
    probability = np.asarray(classifier.booster_.predict(valid_x), dtype=float)
    regressor = _regressor()
    regressor.fit(train_x, train_raw)
    raw_prediction = np.asarray(regressor.booster_.predict(valid_x), dtype=float)
    classifier_text = classifier.booster_.model_to_string()
    regressor_text = regressor.booster_.model_to_string()
    artifact = {
        "policy_version": PR_F_MODEL_POLICY_VERSION,
        "evaluation_protocol": "development_fit_2024_validation",
        "feature_group": development.feature_group.value,
        "cohort": development.cohort.value,
        "development_count": len(train_y),
        "evaluation_count": len(valid_y),
        "development_years": [2020, 2021, 2022, 2023],
        "evaluation_years": [2024],
        "fold_audit": [
            {
                "train_years": [2020, 2021, 2022, 2023],
                "evaluation_years": [2024],
                "train_count": len(train_y),
                "evaluation_count": len(valid_y),
            }
        ],
        "feature_count": len(development.feature_names),
        "classification_metrics": _classification_metrics(valid_y, probability),
        "calibration_assessment": _calibration_assessment(valid_y, probability),
        "regression_metrics": _regression_metrics(valid_raw, raw_prediction),
        "classifier_model_sha256": hashlib.sha256(classifier_text.encode()).hexdigest(),
        "regressor_model_sha256": hashlib.sha256(regressor_text.encode()).hexdigest(),
        "explainability": _explain(classifier, validation, valid_x),
        "case_predictions": [
            {
                "case_id": case_id,
                "poor_performer_5d": bool(actual),
                "poor_performer_score": float(score),
                "raw_return_5d": float(raw_actual),
                "raw_return_5d_prediction": float(raw_score),
            }
            for case_id, actual, score, raw_actual, raw_score in zip(
                validation.case_ids,
                valid_y,
                probability,
                valid_raw,
                raw_prediction,
                strict=True,
            )
        ],
        "error_analysis": _error_analysis(
            validation.case_ids,
            valid_y,
            probability,
            valid_raw,
            raw_prediction,
        ),
        "blind_2025_y_accessed": False,
    }
    return LightGBMRun(artifact, classifier_text, regressor_text)
