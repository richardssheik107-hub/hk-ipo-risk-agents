from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pytest

from ipo_risk.modeling.lightgbm_modeling import train_lightgbm_holdout
from ipo_risk.schemas.canonical_modeling import (
    V04CanonicalCohort,
    V04CanonicalModelMatrix,
    V04ModelFeatureGroup,
    canonical_hash,
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
    case_ids = []
    for index in range(count):
        target = index % 2 == 0
        binary.append(target)
        raw.append(Decimal("-0.20") if target else Decimal("0.10"))
        values.append((float(target), 0, float(target)))
        year = 2024 if split is MarketDatasetSplit.VALIDATION else 2020 + index * 4 // count
        case_ids.append(f"ipo_{year}_{index:05d}")
    return V04CanonicalModelMatrix(
        cohort=cohort,
        dataset_split=split,
        feature_group=group,
        source_dataset_hash=("a" if split is MarketDatasetSplit.DEVELOPMENT else "b") * 64,
        feature_manifest_hash="c" * 64,
        target_policy_hash="d" * 64,
        target_threshold_hash="e" * 64,
        case_ids=tuple(case_ids),
        feature_names=names,
        feature_values=tuple(values),
        raw_return_5d=tuple(raw),
        poor_performer_5d=tuple(binary),
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_matrix_set(
    matrix_dir: Path,
    cohort: V04CanonicalCohort,
    groups: tuple[V04ModelFeatureGroup, ...],
    *,
    development_count: int,
    validation_count: int,
) -> dict[str, str]:
    matrix_dir.mkdir(parents=True)
    hashes: dict[str, str] = {}
    for group in groups:
        for split, count in (
            (MarketDatasetSplit.DEVELOPMENT, development_count),
            (MarketDatasetSplit.VALIDATION, validation_count),
        ):
            matrix = _matrix(group, split, cohort, count=count)
            filename = f"{cohort.value}_{group.value}_{split.value}.json"
            path = matrix_dir / filename
            path.write_text(matrix.model_dump_json(), encoding="utf-8")
            hashes[filename] = _sha256(path)
    return hashes


def _write_pr_e_manifest(
    path: Path,
    production_hashes: dict[str, str],
    oracle_hashes: dict[str, str],
    *,
    formal_gate_passed: bool = True,
) -> None:
    results: list[object] = []
    diagnostic: dict[str, object] = {}
    (path.parent / "baseline_results.json").write_text(
        json.dumps(results), encoding="utf-8"
    )
    (path.parent / "value_diagnostic.json").write_text(
        json.dumps(diagnostic), encoding="utf-8"
    )
    path.write_text(
        json.dumps(
            {
                "pr_e_version": "v04_pr_e_baseline_diagnostic_v1",
                "status": (
                    "complete_frozen_inputs"
                    if formal_gate_passed
                    else "production_readiness_only"
                ),
                "formal_gate_passed": formal_gate_passed,
                "blind_2025_y_accessed": False,
                "full_production_groups": ["M", "P", "PM"],
                "oracle_groups": ["M", "P", "O", "PM", "OM"],
                "results_hash": canonical_hash(results),
                "diagnostic_hash": canonical_hash(diagnostic),
                "production_matrix_hashes": production_hashes,
                "oracle_matrix_hashes": oracle_hashes,
            }
        ),
        encoding="utf-8",
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
    assert first.artifact["development_years"] == [2020, 2021, 2022, 2023]
    assert first.artifact["evaluation_years"] == [2024]
    assert len(first.artifact["case_predictions"]) == 20
    explain = first.artifact["explainability"]
    assert explain["contribution_method"] == "lightgbm_native_pred_contrib_shap"
    assert len(explain["single_ipo_drivers"]) == 20
    assert set(explain["feature_group_mean_abs_shap"]) == {
        "market_core",
        "production_document",
    }


def test_lightgbm_holdout_rejects_non_temporal_validation() -> None:
    development = _matrix(
        V04ModelFeatureGroup.M,
        MarketDatasetSplit.DEVELOPMENT,
        V04CanonicalCohort.FULL_PRODUCTION,
    )
    validation = _matrix(
        V04ModelFeatureGroup.M,
        MarketDatasetSplit.VALIDATION,
        V04CanonicalCohort.FULL_PRODUCTION,
        count=20,
    ).model_copy(
        update={"case_ids": tuple(f"ipo_2023_{index:05d}" for index in range(20))}
    )
    with pytest.raises(ValueError, match="2024 only"):
        train_lightgbm_holdout(development, validation)


def test_pr_f_orchestration_requires_pr_e_and_writes_models(tmp_path: Path) -> None:
    production_dir = tmp_path / "pr_d" / "matrices"
    production_hashes = _write_matrix_set(
        production_dir,
        V04CanonicalCohort.FULL_PRODUCTION,
        (
            V04ModelFeatureGroup.M,
            V04ModelFeatureGroup.P,
            V04ModelFeatureGroup.PM,
        ),
        development_count=40,
        validation_count=20,
    )
    oracle_dir = tmp_path / "oracle" / "matrices"
    oracle_hashes = _write_matrix_set(
        oracle_dir,
        V04CanonicalCohort.ORACLE_INTERSECTION,
        tuple(V04ModelFeatureGroup),
        development_count=40,
        validation_count=20,
    )
    pr_e_manifest = tmp_path / "pr_e_manifest.json"
    _write_pr_e_manifest(pr_e_manifest, production_hashes, oracle_hashes)
    output = tmp_path / "out"
    first = run_pr_f(
        production_dir,
        oracle_dir,
        output,
        pr_e_manifest_path=pr_e_manifest,
    )
    second = run_pr_f(
        production_dir,
        oracle_dir,
        output,
        pr_e_manifest_path=pr_e_manifest,
        resume=True,
    )
    assert first == second
    assert first["manifest"]["result_count"] == 8
    assert first["manifest"]["formal_gate_passed"] is True
    assert first["manifest"]["explainability_method"] == "lightgbm_native_pred_contrib_shap"
    assert (output / "models" / "full_production_PM_classifier.txt").is_file()
    assert (output / "models" / "oracle_intersection_OM_regressor.txt").is_file()
    assert first["comparison"]["oracle_intersection"][
        "classification_om_minus_m"
    ]["roc_auc_gain"] == 0


def test_pr_f_rejects_incomplete_pr_e_gate(tmp_path: Path) -> None:
    manifest = tmp_path / "pr_e.json"
    _write_pr_e_manifest(manifest, {}, {}, formal_gate_passed=False)
    with pytest.raises(ValueError, match="complete_frozen_inputs"):
        run_pr_f(
            tmp_path / "pr_d",
            tmp_path / "oracle",
            tmp_path / "out",
            pr_e_manifest_path=manifest,
        )
