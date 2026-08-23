"""Deterministic PR-E linear/logistic baselines for canonical matrices."""

from __future__ import annotations

import re
from dataclasses import dataclass
from math import sqrt
from typing import Any, Literal

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression, Ridge
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
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ipo_risk.schemas.canonical_modeling import V04CanonicalModelMatrix


PR_E_BASELINE_POLICY_VERSION = "v04_pr_e_baseline_policy_v1"
PR_E_CLASSIFICATION_THRESHOLD = 0.5
PR_E_RANDOM_SEED = 20260822


@dataclass(frozen=True)
class BaselineEvaluation:
    """Serializable metrics and audit metadata for one baseline family."""

    model_family: str
    evaluation_protocol: str
    feature_group: str
    cohort: str
    development_count: int
    evaluation_count: int
    feature_count: int
    all_missing_development_features: tuple[str, ...]
    development_years: tuple[int, ...]
    evaluation_years: tuple[int, ...]
    fold_audit: tuple[dict[str, Any], ...]
    metrics: dict[str, float | int | None]
    coefficients: tuple[tuple[str, float], ...]
    intercept: float
    policy_version: str = PR_E_BASELINE_POLICY_VERSION

    def as_dict(self) -> dict[str, Any]:
        return {
            "policy_version": self.policy_version,
            "model_family": self.model_family,
            "evaluation_protocol": self.evaluation_protocol,
            "feature_group": self.feature_group,
            "cohort": self.cohort,
            "development_count": self.development_count,
            "evaluation_count": self.evaluation_count,
            "feature_count": self.feature_count,
            "all_missing_development_features": self.all_missing_development_features,
            "development_years": self.development_years,
            "evaluation_years": self.evaluation_years,
            "fold_audit": self.fold_audit,
            "metrics": self.metrics,
            "coefficients": self.coefficients,
            "intercept": self.intercept,
        }


def _validate_pair(
    development: V04CanonicalModelMatrix,
    validation: V04CanonicalModelMatrix,
) -> None:
    pairs = {
        "feature_group": (development.feature_group, validation.feature_group),
        "cohort": (development.cohort, validation.cohort),
        "feature_manifest_hash": (
            development.feature_manifest_hash,
            validation.feature_manifest_hash,
        ),
        "feature_names": (development.feature_names, validation.feature_names),
        "target_policy_hash": (
            development.target_policy_hash,
            validation.target_policy_hash,
        ),
        "target_threshold_hash": (
            development.target_threshold_hash,
            validation.target_threshold_hash,
        ),
    }
    mismatches = [name for name, (left, right) in pairs.items() if left != right]
    if mismatches:
        raise ValueError("Development/Validation matrix mismatch: " + ", ".join(mismatches))
    if development.dataset_split.value != "development":
        raise ValueError("baseline fit input must be Development")
    if validation.dataset_split.value != "validation":
        raise ValueError("baseline evaluation input must be Validation")


def _xy(matrix: V04CanonicalModelMatrix, target: Literal["binary", "raw"]):
    x = np.asarray(matrix.feature_values, dtype=float)
    y = np.asarray(
        matrix.poor_performer_5d if target == "binary" else matrix.raw_return_5d,
        dtype=int if target == "binary" else float,
    )
    return x, y


_CASE_YEAR_PATTERN = re.compile(r"^ipo_(20\d{2})_")


def _case_years(matrix: V04CanonicalModelMatrix) -> np.ndarray:
    """Extract governed cohort years from canonical case IDs."""

    years: list[int] = []
    for case_id in matrix.case_ids:
        match = _CASE_YEAR_PATTERN.match(case_id)
        if match is None:
            raise ValueError(f"canonical case ID does not encode cohort year: {case_id}")
        years.append(int(match.group(1)))
    return np.asarray(years, dtype=int)


def _all_missing_names(x: np.ndarray, names: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(name for index, name in enumerate(names) if np.isnan(x[:, index]).all())


def _pipeline(model) -> Pipeline:
    # Missing indicators remain separate features. keep_empty_features preserves
    # width; a raw column missing for all Development rows carries no fitted signal.
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("scaler", StandardScaler()),
            ("model", model),
        ]
    )

def _classification_metrics(y_true, probability) -> dict[str, float | int | None]:
    prediction = (probability >= PR_E_CLASSIFICATION_THRESHOLD).astype(int)
    both = len(np.unique(y_true)) == 2
    return {
        "sample_count": int(len(y_true)),
        "positive_rate": float(np.mean(y_true)),
        "classification_threshold": PR_E_CLASSIFICATION_THRESHOLD,
        "accuracy": float(accuracy_score(y_true, prediction)),
        "precision": float(precision_score(y_true, prediction, zero_division=0)),
        "recall": float(recall_score(y_true, prediction, zero_division=0)),
        "f1": float(f1_score(y_true, prediction, zero_division=0)),
        "brier_score": float(brier_score_loss(y_true, probability)),
        "roc_auc": float(roc_auc_score(y_true, probability)) if both else None,
        "pr_auc": float(average_precision_score(y_true, probability)) if both else None,
    }


def _regression_metrics(y_true, prediction) -> dict[str, float | int | None]:
    return {
        "sample_count": int(len(y_true)),
        "mae": float(mean_absolute_error(y_true, prediction)),
        "rmse": float(sqrt(mean_squared_error(y_true, prediction))),
        "r2": float(r2_score(y_true, prediction)) if len(y_true) >= 2 else None,
    }


def _coefficients(pipe: Pipeline, names: tuple[str, ...]):
    model = pipe.named_steps["model"]
    raw = np.asarray(model.coef_).reshape(-1)
    return tuple((name, float(value)) for name, value in zip(names, raw, strict=True))


def evaluate_holdout_baselines(
    development: V04CanonicalModelMatrix,
    validation: V04CanonicalModelMatrix,
) -> tuple[BaselineEvaluation, ...]:
    """Fit every preprocessing/model step on Development and evaluate 2024 once."""

    _validate_pair(development, validation)
    development_years = tuple(sorted(set(_case_years(development).tolist())))
    validation_years = tuple(sorted(set(_case_years(validation).tolist())))
    if development_years != (2020, 2021, 2022, 2023):
        raise ValueError(
            "formal baseline Development must contain cohort years 2020-2023"
        )
    if validation_years != (2024,):
        raise ValueError("formal baseline Validation must contain cohort year 2024")
    train_x, train_y = _xy(development, "binary")
    valid_x, valid_y = _xy(validation, "binary")
    if len(np.unique(train_y)) < 2:
        raise ValueError("Development classification target requires both classes")
    missing = _all_missing_names(train_x, development.feature_names)
    logistic = _pipeline(
        LogisticRegression(
            C=1.0,
            max_iter=5000,
            random_state=PR_E_RANDOM_SEED,
            solver="liblinear",
        )
    )
    logistic.fit(train_x, train_y)
    probability = logistic.predict_proba(valid_x)[:, 1]
    results = [
        BaselineEvaluation(
            model_family="logistic_regression",
            evaluation_protocol="development_fit_2024_validation",
            feature_group=development.feature_group.value,
            cohort=development.cohort.value,
            development_count=len(train_y),
            evaluation_count=len(valid_y),
            feature_count=len(development.feature_names),
            all_missing_development_features=missing,
            development_years=development_years,
            evaluation_years=validation_years,
            fold_audit=(
                {
                    "train_years": development_years,
                    "evaluation_years": validation_years,
                    "train_count": len(train_y),
                    "evaluation_count": len(valid_y),
                },
            ),
            metrics=_classification_metrics(valid_y, probability),
            coefficients=_coefficients(logistic, development.feature_names),
            intercept=float(logistic.named_steps["model"].intercept_[0]),
        )
    ]
    raw_train_x, raw_train_y = _xy(development, "raw")
    raw_valid_x, raw_valid_y = _xy(validation, "raw")
    for family, model in (
        ("linear_regression", LinearRegression()),
        ("ridge_regression", Ridge(alpha=1.0)),
    ):
        pipe = _pipeline(model)
        pipe.fit(raw_train_x, raw_train_y)
        prediction = pipe.predict(raw_valid_x)
        results.append(
            BaselineEvaluation(
                model_family=family,
                evaluation_protocol="development_fit_2024_validation",
                feature_group=development.feature_group.value,
                cohort=development.cohort.value,
                development_count=len(raw_train_y),
                evaluation_count=len(raw_valid_y),
                feature_count=len(development.feature_names),
                all_missing_development_features=missing,
                development_years=development_years,
                evaluation_years=validation_years,
                fold_audit=(
                    {
                        "train_years": development_years,
                        "evaluation_years": validation_years,
                        "train_count": len(raw_train_y),
                        "evaluation_count": len(raw_valid_y),
                    },
                ),
                metrics=_regression_metrics(raw_valid_y, prediction),
                coefficients=_coefficients(pipe, development.feature_names),
                intercept=float(np.asarray(pipe.named_steps["model"].intercept_).reshape(-1)[0]),
            )
        )
    return tuple(results)


def evaluate_development_forward_chaining_baselines(
    development: V04CanonicalModelMatrix,
) -> tuple[BaselineEvaluation, ...]:
    """Evaluate Development with expanding-year, strictly forward folds."""

    if development.dataset_split.value != "development":
        raise ValueError("forward-chaining evaluation accepts Development only")
    x, y = _xy(development, "binary")
    years = _case_years(development)
    unique_years = tuple(sorted(set(years.tolist())))
    if unique_years != (2020, 2021, 2022, 2023):
        raise ValueError(
            "forward-chaining Development must contain cohort years 2020-2023"
        )
    probability = np.full(len(y), np.nan, dtype=float)
    raw_y = np.asarray(development.raw_return_5d, dtype=float)
    linear_prediction = np.full(len(y), np.nan, dtype=float)
    ridge_prediction = np.full(len(y), np.nan, dtype=float)
    fold_audit: list[dict[str, Any]] = []
    for evaluation_year in unique_years[1:]:
        train_index = np.flatnonzero(years < evaluation_year)
        test_index = np.flatnonzero(years == evaluation_year)
        if len(np.unique(y[train_index])) < 2:
            raise ValueError(
                f"forward fold before {evaluation_year} requires both target classes"
            )
        logistic = _pipeline(
            LogisticRegression(
                C=1.0,
                max_iter=5000,
                random_state=PR_E_RANDOM_SEED,
                solver="liblinear",
            )
        )
        logistic.fit(x[train_index], y[train_index])
        probability[test_index] = logistic.predict_proba(x[test_index])[:, 1]
        for target, model in (
            (linear_prediction, LinearRegression()),
            (ridge_prediction, Ridge(alpha=1.0)),
        ):
            pipe = _pipeline(model)
            pipe.fit(x[train_index], raw_y[train_index])
            target[test_index] = pipe.predict(x[test_index])

        fold_audit.append(
            {
                "train_years": tuple(sorted(set(years[train_index].tolist()))),
                "evaluation_years": (int(evaluation_year),),
                "train_count": int(len(train_index)),
                "evaluation_count": int(len(test_index)),
            }
        )

    evaluated = ~np.isnan(probability)
    if not evaluated.any():
        raise ValueError("forward-chaining produced no out-of-fold predictions")

    missing = _all_missing_names(x, development.feature_names)
    fitted_models = []
    for family, model in (
        (
            "logistic_regression",
            LogisticRegression(
                C=1.0,
                max_iter=5000,
                random_state=PR_E_RANDOM_SEED,
                solver="liblinear",
            ),
        ),
        ("linear_regression", LinearRegression()),
        ("ridge_regression", Ridge(alpha=1.0)),
    ):
        pipe = _pipeline(model)
        pipe.fit(x, y if family == "logistic_regression" else raw_y)
        fitted_models.append((family, pipe))
    metrics = {
        "logistic_regression": _classification_metrics(y[evaluated], probability[evaluated]),
        "linear_regression": _regression_metrics(
            raw_y[evaluated], linear_prediction[evaluated]
        ),
        "ridge_regression": _regression_metrics(
            raw_y[evaluated], ridge_prediction[evaluated]
        ),
    }
    return tuple(
        BaselineEvaluation(
            model_family=family,
            evaluation_protocol="development_expanding_year_forward_oof",
            feature_group=development.feature_group.value,
            cohort=development.cohort.value,
            development_count=len(y),
            evaluation_count=int(evaluated.sum()),
            feature_count=len(development.feature_names),
            all_missing_development_features=missing,
            development_years=unique_years,
            evaluation_years=tuple(year for year in unique_years[1:]),
            fold_audit=tuple(fold_audit),
            metrics=metrics[family],
            coefficients=_coefficients(pipe, development.feature_names),
            intercept=float(np.asarray(pipe.named_steps["model"].intercept_).reshape(-1)[0]),
        )
        for family, pipe in fitted_models
    )


def evaluate_development_cv_baselines(
    development: V04CanonicalModelMatrix,
    *,
    folds: int | None = None,
) -> tuple[BaselineEvaluation, ...]:
    """Compatibility alias for the governed forward-chaining evaluation."""

    if folds is not None:
        raise ValueError("random/stratified fold counts are not allowed by PR-E policy")
    return evaluate_development_forward_chaining_baselines(development)
