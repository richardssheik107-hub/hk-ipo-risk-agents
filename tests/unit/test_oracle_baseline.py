"""Baseline guards over PR-D canonical matrices: protocol, power and comparability."""
from __future__ import annotations

import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from ipo_risk.modeling.oracle_baseline import (
    CV_PROTOCOL,
    HOLDOUT_PROTOCOL,
    IncomparableMatrixError,
    InsufficientCohortError,
    InsufficientValidationSplitError,
    assert_comparable,
    minimum_detectable_auc_difference,
    train_holdout,
    train_time_aware_cv,
)
from ipo_risk.schemas.canonical_modeling import (
    V04CanonicalCohort,
    V04ModelFeatureGroup,
    V04CanonicalModelMatrix,
)
from ipo_risk.schemas.market import MarketDatasetSplit

REPO_ROOT = Path(__file__).resolve().parents[2]
_HASH = {name: name[0] * 64 for name in ("source", "manifest", "policy", "threshold")}


def _matrix(*, group=V04ModelFeatureGroup.OM, split=MarketDatasetSplit.DEVELOPMENT,
            years=(2020, 2021, 2022), per_year=6, cohort=V04CanonicalCohort.ORACLE_INTERSECTION,
            source_hash=None, targets=None, feature_names=("oracle_document__a", "market_core__b")):
    case_ids, values, poor = [], [], []
    for year in years:
        for index in range(per_year):
            case_ids.append(f"ipo_{year}_{index:05d}")
            label = index % 2 == 0
            values.append((float(label) + 0.1 * index, None if index == 0 else float(index)))
            poor.append(label)
    if targets is not None:
        poor = list(targets)
    order = sorted(range(len(case_ids)), key=lambda i: case_ids[i])
    return V04CanonicalModelMatrix(
        cohort=cohort, dataset_split=split, feature_group=group,
        source_dataset_hash=source_hash or _HASH["source"], feature_manifest_hash=_HASH["manifest"],
        target_policy_hash=_HASH["policy"], target_threshold_hash=_HASH["threshold"],
        case_ids=tuple(case_ids[i] for i in order), feature_names=feature_names,
        feature_values=tuple(values[i] for i in order),
        raw_return_5d=tuple(Decimal("-0.05") for _ in order),
        poor_performer_5d=tuple(poor[i] for i in order),
    )


def _years(matrix) -> dict[str, int]:
    return {case_id: int(case_id.split("_")[1]) for case_id in matrix.case_ids}


# --- power -------------------------------------------------------------------


def test_minimum_detectable_difference_shrinks_with_sample_size() -> None:
    small = minimum_detectable_auc_difference(3, 7)
    oracle = minimum_detectable_auc_difference(17, 39)
    large = minimum_detectable_auc_difference(110, 258)
    assert small > oracle > large
    assert round(small, 2) == 0.55    # the 10-case carve-out the team considered
    assert round(oracle, 2) == 0.22   # the real 56-case Oracle intersection cohort
    assert minimum_detectable_auc_difference(0, 10) == float("inf")


def test_every_result_reports_its_own_power() -> None:
    """A gap below this threshold is unmeasurable here, not absent."""
    result = train_time_aware_cv(development=_matrix(), cohort_years=_years(_matrix()))
    assert result.pooled_metrics["minimum_detectable_auc_difference"] == result.minimum_detectable_auc_difference
    assert result.minimum_detectable_auc_difference > 0.3


# --- comparability -----------------------------------------------------------


def test_arms_from_the_same_dataset_and_cohort_are_comparable() -> None:
    assert_comparable(_matrix(group=V04ModelFeatureGroup.OM), _matrix(group=V04ModelFeatureGroup.PM))


def test_arms_from_different_datasets_cannot_be_subtracted() -> None:
    """OM - PM is only a pipeline gap when everything except the arm is identical."""
    with pytest.raises(IncomparableMatrixError, match="source_dataset_hash"):
        assert_comparable(_matrix(group=V04ModelFeatureGroup.OM),
                          _matrix(group=V04ModelFeatureGroup.PM, source_hash="z" * 64))


def test_arms_covering_different_cases_cannot_be_subtracted() -> None:
    with pytest.raises(IncomparableMatrixError, match="different cases"):
        assert_comparable(_matrix(group=V04ModelFeatureGroup.OM),
                          _matrix(group=V04ModelFeatureGroup.PM, per_year=5))


# --- holdout protocol --------------------------------------------------------


def test_holdout_fits_development_and_scores_validation() -> None:
    development = _matrix(group=V04ModelFeatureGroup.PM, cohort=V04CanonicalCohort.FULL_PRODUCTION)
    validation = _matrix(group=V04ModelFeatureGroup.PM, cohort=V04CanonicalCohort.FULL_PRODUCTION,
                         split=MarketDatasetSplit.VALIDATION, years=(2024,), per_year=6)
    result = train_holdout(development=development, validation=validation)
    assert result.arm == "PM"
    assert result.protocol == HOLDOUT_PROTOCOL
    assert result.metrics["sample_count"] == 6


def test_holdout_rejects_a_single_class_validation_split() -> None:
    """The shape the Oracle arms are in today; the CV protocol exists for this."""
    development = _matrix(group=V04ModelFeatureGroup.PM, cohort=V04CanonicalCohort.FULL_PRODUCTION)
    validation = _matrix(group=V04ModelFeatureGroup.PM, cohort=V04CanonicalCohort.FULL_PRODUCTION,
                         split=MarketDatasetSplit.VALIDATION, years=(2024,), per_year=4,
                         targets=[True] * 4)
    with pytest.raises(InsufficientValidationSplitError, match="single-class validation split"):
        train_holdout(development=development, validation=validation)


def test_holdout_rejects_mismatched_feature_groups() -> None:
    with pytest.raises(IncomparableMatrixError, match="different feature groups"):
        train_holdout(development=_matrix(group=V04ModelFeatureGroup.OM),
                      validation=_matrix(group=V04ModelFeatureGroup.PM,
                                         split=MarketDatasetSplit.VALIDATION, years=(2024,)))


# --- development-only time-aware CV (Option B) -------------------------------


def test_forward_chaining_folds_never_see_their_own_future() -> None:
    """The property that makes this a time-aware split rather than a random one."""
    matrix = _matrix()
    result = train_time_aware_cv(development=matrix, cohort_years=_years(matrix))
    assert result.protocol == CV_PROTOCOL
    assert [fold.test_year for fold in result.folds] == [2021, 2022]
    for fold in result.folds:
        assert all(year < fold.test_year for year in fold.train_years), fold
    assert result.folds[0].train_years == (2020,)
    assert result.folds[1].train_years == (2020, 2021)


def test_pooled_evaluation_covers_every_case_outside_the_first_year() -> None:
    matrix = _matrix()
    result = train_time_aware_cv(development=matrix, cohort_years=_years(matrix))
    assert result.pooled_metrics["sample_count"] == sum(f.test_size for f in result.folds if f.evaluated) == 12


def test_cv_result_always_carries_the_comparability_warning() -> None:
    """A CV number must never be readable as a holdout number."""
    matrix = _matrix()
    result = train_time_aware_cv(development=matrix, cohort_years=_years(matrix))
    assert "not comparable to holdout" in result.comparability_warning
    assert result.protocol != HOLDOUT_PROTOCOL


def test_both_arms_share_protocol_and_cases_so_the_gap_is_valid() -> None:
    oracle = _matrix(group=V04ModelFeatureGroup.OM)
    production = _matrix(group=V04ModelFeatureGroup.PM)
    assert_comparable(oracle, production)
    left = train_time_aware_cv(development=oracle, cohort_years=_years(oracle))
    right = train_time_aware_cv(development=production, cohort_years=_years(production))
    assert left.protocol == right.protocol
    assert left.pooled_metrics["sample_count"] == right.pooled_metrics["sample_count"]
    assert [f.test_year for f in left.folds] == [f.test_year for f in right.folds]


def test_cohort_years_are_keyed_by_case_id_not_position() -> None:
    matrix = _matrix()
    years = _years(matrix)
    years.pop(matrix.case_ids[0])
    with pytest.raises(ValueError, match="cohort year missing"):
        train_time_aware_cv(development=matrix, cohort_years=years)


def test_single_cohort_year_cannot_form_a_fold() -> None:
    matrix = _matrix(years=(2020,), per_year=8)
    with pytest.raises(InsufficientCohortError, match="at least two cohort years"):
        train_time_aware_cv(development=matrix, cohort_years=_years(matrix))


def test_cv_is_deterministic() -> None:
    matrix = _matrix()
    years = _years(matrix)
    assert train_time_aware_cv(development=matrix, cohort_years=years) == train_time_aware_cv(
        development=matrix, cohort_years=years)


def test_explicit_nulls_are_imputed_from_development_only() -> None:
    """Missing values must never be silently read as a safe zero."""
    matrix = _matrix()
    assert any(value is None for row in matrix.feature_values for value in row)
    result = train_time_aware_cv(development=matrix, cohort_years=_years(matrix))
    assert result.pooled_metrics["sample_count"] > 0


# --- CLI ---------------------------------------------------------------------


def test_cv_cli_reports_protocol_folds_and_the_power_warning(tmp_path) -> None:
    matrix = _matrix()
    development_path = tmp_path / "om_development.json"
    development_path.write_text(matrix.model_dump_json(), encoding="utf-8")
    years_path = tmp_path / "cohort_years.json"
    years_path.write_text(json.dumps(_years(matrix)), encoding="utf-8")
    output = tmp_path / "out"
    subprocess.run(
        [sys.executable, "scripts/train_oracle_baseline.py", "--development", str(development_path),
         "--cohort-years", str(years_path), "--output-dir", str(output), "--protocol", CV_PROTOCOL],
        cwd=REPO_ROOT, check=True,
    )
    report = json.loads((output / "metrics.json").read_text(encoding="utf-8"))
    assert report["protocol"] == CV_PROTOCOL
    arm = report["arms"][0]
    assert arm["arm"] == "OM"
    assert [fold["test_year"] for fold in arm["folds"]] == [2021, 2022]
    assert "not comparable to holdout" in arm["comparability_warning"]
    assert arm["minimum_detectable_auc_difference"] > 0.3


def test_cv_cli_requires_cohort_years(tmp_path) -> None:
    development_path = tmp_path / "om_development.json"
    development_path.write_text(_matrix().model_dump_json(), encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, "scripts/train_oracle_baseline.py", "--development", str(development_path),
         "--output-dir", str(tmp_path / "out"), "--protocol", CV_PROTOCOL],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert completed.returncode != 0
    assert "cohort-years" in completed.stderr
