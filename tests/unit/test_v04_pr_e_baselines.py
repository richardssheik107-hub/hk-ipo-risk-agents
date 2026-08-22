from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from ipo_risk.modeling.baselines import (
    evaluate_development_cv_baselines,
    evaluate_holdout_baselines,
)
from ipo_risk.schemas.canonical_modeling import (
    V04CanonicalCohort,
    V04CanonicalModelMatrix,
    V04ModelFeatureGroup,
)
from ipo_risk.schemas.market import MarketDatasetSplit
from scripts.run_v04_pr_e import run_pr_e


def _matrix(
    group: V04ModelFeatureGroup,
    split: MarketDatasetSplit,
    cohort: V04CanonicalCohort,
    *,
    count: int,
) -> V04CanonicalModelMatrix:
    names = (f"{group.value}__signal", f"{group.value}__missing")
    values = []
    binary = []
    raw = []
    for index in range(count):
        target = index % 2 == 0
        binary.append(target)
        raw.append(Decimal("-0.2") if target else Decimal("0.15"))
        values.append((float(target), None if index % 3 == 0 else 0.0))
    prefix = "dev" if split is MarketDatasetSplit.DEVELOPMENT else "val"
    return V04CanonicalModelMatrix(
        cohort=cohort,
        dataset_split=split,
        feature_group=group,
        source_dataset_hash=("a" if split is MarketDatasetSplit.DEVELOPMENT else "b") * 64,
        feature_manifest_hash=(group.value.lower()[0] * 64),
        target_policy_hash="c" * 64,
        target_threshold_hash="d" * 64,
        case_ids=tuple(f"{prefix}_{index:03d}" for index in range(count)),
        feature_names=names,
        feature_values=tuple(values),
        raw_return_5d=tuple(raw),
        poor_performer_5d=tuple(binary),
    )


def test_holdout_baselines_are_deterministic_and_dev_fit_only() -> None:
    development = _matrix(
        V04ModelFeatureGroup.PM,
        MarketDatasetSplit.DEVELOPMENT,
        V04CanonicalCohort.FULL_PRODUCTION,
        count=20,
    )
    validation = _matrix(
        V04ModelFeatureGroup.PM,
        MarketDatasetSplit.VALIDATION,
        V04CanonicalCohort.FULL_PRODUCTION,
        count=8,
    )
    first = evaluate_holdout_baselines(development, validation)
    second = evaluate_holdout_baselines(development, validation)
    assert first == second
    assert {row.model_family for row in first} == {
        "logistic_regression",
        "linear_regression",
        "ridge_regression",
    }
    assert all(row.evaluation_protocol == "development_fit_2024_validation" for row in first)
    assert first[0].metrics["roc_auc"] == 1.0


def test_oracle_cv_is_explicitly_development_only() -> None:
    oracle = _matrix(
        V04ModelFeatureGroup.OM,
        MarketDatasetSplit.DEVELOPMENT,
        V04CanonicalCohort.ORACLE_INTERSECTION,
        count=20,
    )
    result = evaluate_development_cv_baselines(oracle)
    assert len(result) == 3
    assert all("development_stratified_5fold_oof" == row.evaluation_protocol for row in result)
    validation = oracle.model_copy(update={"dataset_split": MarketDatasetSplit.VALIDATION})
    with pytest.raises(ValueError, match="Development only"):
        evaluate_development_cv_baselines(validation)


def test_holdout_rejects_feature_manifest_drift() -> None:
    development = _matrix(
        V04ModelFeatureGroup.M,
        MarketDatasetSplit.DEVELOPMENT,
        V04CanonicalCohort.FULL_PRODUCTION,
        count=20,
    )
    validation = _matrix(
        V04ModelFeatureGroup.M,
        MarketDatasetSplit.VALIDATION,
        V04CanonicalCohort.FULL_PRODUCTION,
        count=8,
    ).model_copy(update={"feature_manifest_hash": "e" * 64})
    with pytest.raises(ValueError, match="feature_manifest_hash"):
        evaluate_holdout_baselines(development, validation)


def test_pr_e_orchestration_runs_full_and_oracle_tracks(tmp_path: Path) -> None:
    matrix_dir = tmp_path / "matrices"
    matrix_dir.mkdir()
    for group in (V04ModelFeatureGroup.M, V04ModelFeatureGroup.P, V04ModelFeatureGroup.PM):
        for split, count in (
            (MarketDatasetSplit.DEVELOPMENT, 20),
            (MarketDatasetSplit.VALIDATION, 8),
        ):
            matrix = _matrix(group, split, V04CanonicalCohort.FULL_PRODUCTION, count=count)
            (matrix_dir / f"full_production_{group.value}_{split.value}.json").write_text(
                matrix.model_dump_json(), encoding="utf-8"
            )
    for group in V04ModelFeatureGroup:
        matrix = _matrix(
            group,
            MarketDatasetSplit.DEVELOPMENT,
            V04CanonicalCohort.ORACLE_INTERSECTION,
            count=20,
        )
        (matrix_dir / f"oracle_intersection_{group.value}_development.json").write_text(
            matrix.model_dump_json(), encoding="utf-8"
        )
    output = tmp_path / "out"
    first = run_pr_e(matrix_dir, output)
    second = run_pr_e(matrix_dir, output, resume=True)
    assert first == second
    assert first["manifest"]["result_count"] == 24
    assert first["manifest"]["oracle_status"] == "development_cv_only"
    assert first["diagnostic"]["full_production_validation"]["pm_minus_m_roc_auc"] == 0
    assert first["diagnostic"]["oracle_validation_status"] == "unavailable_no_reviewed_gold"
    assert json.loads((output / "run_manifest.json").read_text())["blind_2025_y_accessed"] is False

