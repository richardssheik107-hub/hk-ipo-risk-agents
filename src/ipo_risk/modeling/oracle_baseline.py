"""Deterministic Logistic Regression baselines over PR-D canonical model matrices.

Column selection is *not* done here.  ``project_model_matrix`` already produced one
matrix per M / P / O / PM / OM group with a frozen component order and prefixed
feature names, so this module only fits, evaluates and reports statistical power.

Two evaluation protocols:

``holdout``
    Fit on a development matrix, evaluate an untouched validation matrix.  This is
    the PR-E protocol for the M / P / PM arms.

``development_only_time_aware_cv``
    Forward-chaining folds inside development: train on all earlier cohort years,
    test on the next one, then pool the out-of-fold predictions.  The Oracle arms
    O and OM have no validation coverage at all, so this is the only protocol under
    which ``OM - PM`` can be measured.  Its numbers are NOT comparable to holdout
    numbers and every result carries that warning as a required field.
    See docs/V04_ORACLE_GOLD_COVERAGE_AUDIT.md section 4.
"""
from __future__ import annotations
import math
from collections.abc import Mapping
from dataclasses import dataclass
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, average_precision_score, brier_score_loss, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from ipo_risk.schemas.canonical_modeling import V04CanonicalModelMatrix

HOLDOUT_PROTOCOL = "holdout"
CV_PROTOCOL = "development_only_time_aware_cv"
CV_COMPARABILITY_WARNING = (
    "development-only out-of-fold estimate; not comparable to holdout validation numbers, "
    "and development exposure makes it optimistic for both arms"
)
DEFAULT_SEED = 20260816

class InsufficientValidationSplitError(ValueError):
    """Raised when an arm has no usable validation split.

    The Oracle arms O and OM currently cover 56 usable development cases and zero
    validation cases, so they cannot be evaluated under the fit-on-development /
    evaluate-on-validation protocol.  Use ``train_time_aware_cv`` instead and report
    its numbers separately.  See docs/V04_ORACLE_GOLD_COVERAGE_AUDIT.md.
    """

class InsufficientCohortError(ValueError):
    """Raised when the cohort cannot form a single usable forward-chaining fold."""

class IncomparableMatrixError(ValueError):
    """Raised when two arms cannot be subtracted because their setup differs."""

@dataclass(frozen=True)
class OracleBaselineResult:
    arm: str
    protocol: str
    cohort: str
    feature_names: tuple[str, ...]
    metrics: dict[str, float | int | list[list[int]] | None]

@dataclass(frozen=True)
class TimeAwareFold:
    train_years: tuple[int, ...]
    test_year: int
    train_size: int
    test_size: int
    evaluated: bool
    reason: str = ""

@dataclass(frozen=True)
class OracleCrossValidationResult:
    arm: str
    protocol: str
    cohort: str
    feature_names: tuple[str, ...]
    folds: tuple[TimeAwareFold, ...]
    pooled_metrics: dict[str, float | int | list[list[int]] | None]
    minimum_detectable_auc_difference: float
    comparability_warning: str = CV_COMPARABILITY_WARNING

def minimum_detectable_auc_difference(positive_count: int, negative_count: int, *, assumed_auc: float = 0.70) -> float:
    """Smallest AUC gap two arms of this size could distinguish at 95% confidence.

    Hanley-McNeil standard error, widened for a two-arm comparison.  Reporting this
    alongside every result keeps an underpowered comparison from reading as a null
    finding: a gap below this number is unmeasurable here, not absent.
    """
    if positive_count < 1 or negative_count < 1:
        return float("inf")
    q1 = assumed_auc / (2 - assumed_auc)
    q2 = 2 * assumed_auc**2 / (1 + assumed_auc)
    variance = (
        assumed_auc * (1 - assumed_auc)
        + (positive_count - 1) * (q1 - assumed_auc**2)
        + (negative_count - 1) * (q2 - assumed_auc**2)
    ) / (positive_count * negative_count)
    return 1.96 * math.sqrt(2 * variance)

def assert_comparable(left: V04CanonicalModelMatrix, right: V04CanonicalModelMatrix) -> None:
    """Guard the precondition that makes an arm-to-arm gap meaningful.

    ``OM - PM`` is only interpretable when both arms were built from the same
    dataset, the same cohort and the same target policy; only the feature group
    may differ.
    """
    for field in ("source_dataset_hash", "cohort", "dataset_split", "target_policy_hash", "target_threshold_hash"):
        if getattr(left, field) != getattr(right, field):
            raise IncomparableMatrixError(
                f"arms {left.feature_group.value} and {right.feature_group.value} differ in {field}; "
                "their difference would not be a pipeline gap"
            )
    if left.case_ids != right.case_ids:
        raise IncomparableMatrixError(
            f"arms {left.feature_group.value} and {right.feature_group.value} cover different cases"
        )

def _x(matrix: V04CanonicalModelMatrix) -> np.ndarray:
    """Dense float view; explicit nulls become NaN for the development-fit imputer."""
    return np.asarray([[np.nan if value is None else float(value) for value in row]
                       for row in matrix.feature_values], dtype=float)

def _y(matrix: V04CanonicalModelMatrix) -> np.ndarray:
    return np.asarray(matrix.poor_performer_5d, dtype=int)

def _metrics(y_true, probability) -> dict[str, float | int | list[list[int]] | None]:
    prediction = (probability >= 0.5).astype(int)
    both_classes = len(np.unique(y_true)) == 2
    positive_count = int(y_true.sum())
    return {
        "sample_count": int(len(y_true)), "positive_rate": float(y_true.mean()),
        "accuracy": float(accuracy_score(y_true, prediction)), "precision": float(precision_score(y_true, prediction, zero_division=0)),
        "recall": float(recall_score(y_true, prediction, zero_division=0)), "f1": float(f1_score(y_true, prediction, zero_division=0)),
        "brier_score": float(brier_score_loss(y_true, probability)), "confusion_matrix": confusion_matrix(y_true, prediction).tolist(),
        "roc_auc": float(roc_auc_score(y_true, probability)) if both_classes else None,
        "pr_auc": float(average_precision_score(y_true, probability)) if both_classes else None,
        "minimum_detectable_auc_difference": minimum_detectable_auc_difference(positive_count, len(y_true) - positive_count),
    }

def _fit_predict(train_x, y_train, test_x, seed: int):
    """Fit imputation and the model on training rows only, then score the test rows."""
    imputer = SimpleImputer(strategy="median")
    model = LogisticRegression(random_state=seed, max_iter=1000)
    model.fit(imputer.fit_transform(train_x), y_train)
    return model.predict_proba(imputer.transform(test_x))[:, 1]

def train_holdout(*, development: V04CanonicalModelMatrix, validation: V04CanonicalModelMatrix,
                  seed: int = DEFAULT_SEED) -> OracleBaselineResult:
    """Fit preprocessing on development only and evaluate untouched validation."""
    if development.feature_group is not validation.feature_group:
        raise IncomparableMatrixError("development and validation matrices are different feature groups")
    if development.feature_names != validation.feature_names:
        raise IncomparableMatrixError("development and validation feature manifests differ")
    y_train, y_valid = _y(development), _y(validation)
    if len(np.unique(y_train)) < 2:
        raise ValueError("development target needs both classes")
    arm = development.feature_group.value
    if len(y_valid) == 0:
        raise InsufficientValidationSplitError(f"arm {arm} has an empty validation split; see docs/V04_ORACLE_GOLD_COVERAGE_AUDIT.md")
    if len(np.unique(y_valid)) < 2:
        raise InsufficientValidationSplitError(f"arm {arm} has a single-class validation split; see docs/V04_ORACLE_GOLD_COVERAGE_AUDIT.md")
    probability = _fit_predict(_x(development), y_train, _x(validation), seed)
    return OracleBaselineResult(arm, HOLDOUT_PROTOCOL, development.cohort.value,
                                development.feature_names, _metrics(y_valid, probability))

def train_time_aware_cv(*, development: V04CanonicalModelMatrix, cohort_years: Mapping[str, int],
                        seed: int = DEFAULT_SEED) -> OracleCrossValidationResult:
    """Forward-chaining folds inside development, pooled over out-of-fold predictions.

    Fold k trains on every cohort year before ``year[k]`` and tests on ``year[k]``,
    so chronological order is preserved and no fold ever sees its own future.
    ``cohort_years`` is keyed by case id rather than positional, so a row can never
    silently receive another case's year.
    """
    arm = development.feature_group.value
    missing = [case_id for case_id in development.case_ids if case_id not in cohort_years]
    if missing:
        raise ValueError(f"cohort year missing for {len(missing)} case(s), first: {missing[0]}")
    years = np.asarray([cohort_years[case_id] for case_id in development.case_ids], dtype=int)
    x, y = _x(development), _y(development)
    ordered = sorted(set(years.tolist()))
    if len(ordered) < 2:
        raise InsufficientCohortError(f"arm {arm} needs at least two cohort years to form a forward-chaining fold")
    folds: list[TimeAwareFold] = []
    pooled_true: list[np.ndarray] = []
    pooled_probability: list[np.ndarray] = []
    for index, test_year in enumerate(ordered[1:], start=1):
        train_years = tuple(ordered[:index])
        train_mask = np.isin(years, train_years)
        test_mask = years == test_year
        y_train = y[train_mask]
        reason = ""
        if len(np.unique(y_train)) < 2:
            reason = "training years are single-class"
        elif not test_mask.any():
            reason = "no rows in the test year"
        folds.append(TimeAwareFold(train_years, int(test_year), int(train_mask.sum()), int(test_mask.sum()),
                                   evaluated=not reason, reason=reason))
        if reason:
            continue
        pooled_probability.append(_fit_predict(x[train_mask], y_train, x[test_mask], seed))
        pooled_true.append(y[test_mask])
    if not pooled_true:
        raise InsufficientCohortError(f"arm {arm} produced no evaluable forward-chaining fold")
    y_pooled = np.concatenate(pooled_true)
    metrics = _metrics(y_pooled, np.concatenate(pooled_probability))
    return OracleCrossValidationResult(
        arm, CV_PROTOCOL, development.cohort.value, development.feature_names,
        tuple(folds), metrics, float(metrics["minimum_detectable_auc_difference"]),
    )
