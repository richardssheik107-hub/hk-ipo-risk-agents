from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from ipo_risk.modeling.lightgbm_modeling import (
    train_lightgbm_development_cv,
    train_lightgbm_holdout,
)
from ipo_risk.schemas.canonical_modeling import (
    V04CanonicalCohort,
    V04CanonicalModelMatrix,
    V04ModelFeatureGroup,
)
from ipo_risk.schemas.market import MarketDatasetSplit
from scripts.run_v04_pr_f import run_pr_f


def _matrix(group, split, cohort, *, count=40):
    names = (
        "market_core__signal",
        "market_core__signal__missing",
        (
            "oracle_document__risk"
            if group in {V04ModelFeatureGroup.O, V04ModelFeatureGroup.OM}
            else "production_document__risk"
        ),
    )
    values = []
    binary = []
    raw = []
    for index in range(count):
        target = index % 2 == 0
        binary.append(target)
        raw.append(Decimal("-0.20") if target else Decimal("0.10"))
        values.append((float(target), 0, float(target)))
    prefix = "dev" if split is MarketDatasetSplit.DEVELOPMENT else "val"
    return V04CanonicalModelMatrix(
        cohort=cohort,
        dataset_split=split,
        feature_group=group,
        source_dataset_hash=("a" if prefix == "dev" else "b") * 64,
        feature_manifest_hash="c" * 64,
        target_policy_hash="d" * 64,
        target_threshold_hash="e" * 64,
        case_ids=tuple(f"{prefix}_{index:03d}" for index in range(count)),
        feature_names=names,
        feature_values=tuple(values),
        raw_return_5d=tuple(raw),
        poor_performer_5d=tuple(binary),
    )


def test_lightgbm_holdout_is_deterministic_and_explainable() -> None:
    development = _matrix(
        V04ModelFeatureGroup.PM,
        MarketDatasetSplit.DEVELOPMENT,
        V04CanonicalCohort.FULL_PRODUCTION,
    )
    validation = _matrix(
        V04ModelFeatureGroup.PM,
        MarketDatasetSplit.VALIDATION,
        V04CanonicalCohort.FULL_PRODUCTION,
        count=20,
    )
    first = train_lightgbm_holdout(development, validation)
    second = train_lightgbm_holdout(development, validation)
    assert first.artifact == second.artifact
    assert first.classifier_model_text == second.classifier_model_text
    assert first.artifact["classification_metrics"]["roc_auc"] == 1.0
    explain = first.artifact["explainability"]
    assert explain["contribution_method"] == "lightgbm_native_pred_contrib_shap"
    assert len(explain["single_ipo_drivers"]) == 20
    assert set(explain["feature_group_mean_abs_shap"]) == {
        "market_core",
        "production_document",
    }


def test_lightgbm_oracle_cv_is_not_validation() -> None:
    development = _matrix(
        V04ModelFeatureGroup.OM,
        MarketDatasetSplit.DEVELOPMENT,
        V04CanonicalCohort.ORACLE_INTERSECTION,
    )
    result = train_lightgbm_development_cv(development)
    assert result.artifact["evaluation_protocol"] == "development_stratified_5fold_oof"
    assert result.artifact["blind_2025_y_accessed"] is False
    validation = development.model_copy(update={"dataset_split": MarketDatasetSplit.VALIDATION})
    with pytest.raises(ValueError, match="Development only"):
        train_lightgbm_development_cv(validation)


def test_pr_f_orchestration_writes_models_and_explanations(tmp_path: Path) -> None:
    matrix_dir = tmp_path / "matrices"
    matrix_dir.mkdir()
    for group in (V04ModelFeatureGroup.M, V04ModelFeatureGroup.P, V04ModelFeatureGroup.PM):
        for split, count in (
            (MarketDatasetSplit.DEVELOPMENT, 40),
            (MarketDatasetSplit.VALIDATION, 20),
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
        )
        (matrix_dir / f"oracle_intersection_{group.value}_development.json").write_text(
            matrix.model_dump_json(), encoding="utf-8"
        )
    output = tmp_path / "out"
    first = run_pr_f(matrix_dir, output)
    second = run_pr_f(matrix_dir, output, resume=True)
    assert first == second
    assert first["manifest"]["result_count"] == 8
    assert first["manifest"]["explainability_method"] == "lightgbm_native_pred_contrib_shap"
    assert (output / "models" / "full_production_PM_classifier.txt").is_file()
    assert (output / "models" / "oracle_intersection_OM_regressor.txt").is_file()
    assert first["comparison"]["oracle_development_cv"]["not_2024_validation"] is True

