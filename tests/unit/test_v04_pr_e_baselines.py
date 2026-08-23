from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pytest

from ipo_risk.modeling.baselines import (
    evaluate_development_cv_baselines,
    evaluate_development_forward_chaining_baselines,
    evaluate_holdout_baselines,
)
from ipo_risk.modeling.oracle_document_v2 import (
    ORACLE_V2_FEATURE_MANIFEST_HASH,
    ORACLE_V2_POLICY_VERSION,
    ORACLE_V2_SCHEMA_VERSION,
)
from ipo_risk.modeling.oracle_v2_matrices import (
    ORACLE_V2_FREEZE_MANIFEST_VERSION,
    ORACLE_V2_MATRIX_MANIFEST_VERSION,
    ORACLE_V2_MATRIX_POLICY_VERSION,
)
from ipo_risk.schemas.canonical_modeling import (
    V04CanonicalCohort,
    V04CanonicalModelMatrix,
    V04ModelFeatureGroup,
    canonical_hash,
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
    case_ids = []
    for index in range(count):
        target = index % 2 == 0
        binary.append(target)
        raw.append(Decimal("-0.2") if target else Decimal("0.15"))
        values.append((float(target), None if index % 3 == 0 else 0.0))
        year = 2024 if split is MarketDatasetSplit.VALIDATION else 2020 + index * 4 // count
        case_ids.append(f"ipo_{year}_{index:05d}")
    return V04CanonicalModelMatrix(
        cohort=cohort,
        dataset_split=split,
        feature_group=group,
        source_dataset_hash=("a" if split is MarketDatasetSplit.DEVELOPMENT else "b") * 64,
        feature_manifest_hash=(group.value.lower()[0] * 64),
        target_policy_hash="c" * 64,
        target_threshold_hash="d" * 64,
        case_ids=tuple(case_ids),
        feature_names=names,
        feature_values=tuple(values),
        raw_return_5d=tuple(raw),
        poor_performer_5d=tuple(binary),
    )


def _write_matrices(
    matrix_dir: Path,
    cohort: V04CanonicalCohort,
    groups: tuple[V04ModelFeatureGroup, ...],
    *,
    development_count: int,
    validation_count: int,
) -> None:
    matrix_dir.mkdir(parents=True, exist_ok=True)
    for group in groups:
        for split, count in (
            (MarketDatasetSplit.DEVELOPMENT, development_count),
            (MarketDatasetSplit.VALIDATION, validation_count),
        ):
            matrix = _matrix(group, split, cohort, count=count)
            (matrix_dir / f"{cohort.value}_{group.value}_{split.value}.json").write_text(
                matrix.model_dump_json(), encoding="utf-8"
            )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _runtime_files(matrix_dir: Path) -> dict[str, dict[str, str | int]]:
    return {
        f"matrices/{path.name}": {
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(matrix_dir.glob("*.json"))
    }


def _write_pr_d_manifest(path: Path, matrix_dir: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "manifest_version": "v04_pr_d_freeze_manifest_v1",
                "status": "complete_frozen",
                "blind_2025_y_accessed": False,
                "model_ready_count": 424,
                "development_model_ready_count": 354,
                "validation_model_ready_count": 70,
                "runtime_files": _runtime_files(matrix_dir),
            }
        ),
        encoding="utf-8",
    )


def _write_oracle_v2_manifest(
    path: Path,
) -> None:
    path.write_text(
        json.dumps(
            {
                "manifest_version": ORACLE_V2_FREEZE_MANIFEST_VERSION,
                "status": "complete_frozen",
                "a_final_sign_off": "passed",
                "evaluation_only": True,
                "production_consumable": False,
                "blind_2025_y_accessed": False,
                "schema_version": ORACLE_V2_SCHEMA_VERSION,
                "policy_version": ORACLE_V2_POLICY_VERSION,
                "feature_manifest_hash": ORACLE_V2_FEATURE_MANIFEST_HASH,
                "materialized_count": 98,
                "strict_usable_count": 96,
                "development_usable_count": 77,
                "validation_usable_count": 19,
                "artifact_set_hash": "a" * 64,
                "case_set_hash": "b" * 64,
                "strict_usable_case_set_hash": "c" * 64,
                "source_annotation_inventory_hash": "d" * 64,
                "pr_d_freeze_manifest_hash": "e" * 64,
                "freeze_manifest_hash": "f" * 64,
            }
        ),
        encoding="utf-8",
    )


def _write_oracle_v2_matrix_manifest(path: Path, matrix_dir: Path) -> None:
    body = {
        "manifest_version": ORACLE_V2_MATRIX_MANIFEST_VERSION,
        "policy_version": ORACLE_V2_MATRIX_POLICY_VERSION,
        "status": "complete_frozen_inputs",
        "evaluation_only": True,
        "production_consumable": False,
        "blind_2025_y_accessed": False,
        "oracle_v2_freeze_manifest_hash": "f" * 64,
        "oracle_v2_artifact_set_hash": "a" * 64,
        "development_model_ready_count": 77,
        "validation_model_ready_count": 19,
        "runtime_files": _runtime_files(matrix_dir),
    }
    body["manifest_hash"] = canonical_hash(body)
    path.write_text(json.dumps(body), encoding="utf-8")


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
    assert first[0].development_years == (2020, 2021, 2022, 2023)
    assert first[0].evaluation_years == (2024,)


def test_development_evaluation_is_strictly_forward_chaining() -> None:
    development = _matrix(
        V04ModelFeatureGroup.OM,
        MarketDatasetSplit.DEVELOPMENT,
        V04CanonicalCohort.ORACLE_INTERSECTION,
        count=20,
    )
    result = evaluate_development_forward_chaining_baselines(development)
    assert len(result) == 3
    assert all(
        row.evaluation_protocol == "development_expanding_year_forward_oof"
        for row in result
    )
    assert result[0].evaluation_count == 15
    assert result[0].fold_audit[0]["train_years"] == (2020,)
    assert result[0].fold_audit[-1]["evaluation_years"] == (2023,)
    assert all(
        max(fold["train_years"]) < min(fold["evaluation_years"])
        for fold in result[0].fold_audit
    )
    with pytest.raises(ValueError, match="random/stratified"):
        evaluate_development_cv_baselines(development, folds=5)


def test_forward_evaluation_rejects_validation_and_noncanonical_ids() -> None:
    development = _matrix(
        V04ModelFeatureGroup.OM,
        MarketDatasetSplit.DEVELOPMENT,
        V04CanonicalCohort.ORACLE_INTERSECTION,
        count=20,
    )
    validation = development.model_copy(
        update={"dataset_split": MarketDatasetSplit.VALIDATION}
    )
    with pytest.raises(ValueError, match="Development only"):
        evaluate_development_forward_chaining_baselines(validation)
    invalid = development.model_copy(
        update={"case_ids": tuple(f"case_{index:03d}" for index in range(20))}
    )
    with pytest.raises(ValueError, match="does not encode cohort year"):
        evaluate_development_forward_chaining_baselines(invalid)


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


def test_pr_e_orchestration_runs_frozen_production_and_oracle_v2(tmp_path: Path) -> None:
    production_matrix_dir = tmp_path / "pr_d" / "matrices"
    _write_matrices(
        production_matrix_dir,
        V04CanonicalCohort.FULL_PRODUCTION,
        (
            V04ModelFeatureGroup.M,
            V04ModelFeatureGroup.P,
            V04ModelFeatureGroup.PM,
        ),
        development_count=354,
        validation_count=70,
    )
    pr_d_manifest = tmp_path / "pr_d_freeze.json"
    _write_pr_d_manifest(pr_d_manifest, production_matrix_dir)

    oracle_matrix_dir = tmp_path / "oracle_v2" / "matrices"
    _write_matrices(
        oracle_matrix_dir,
        V04CanonicalCohort.ORACLE_INTERSECTION,
        tuple(V04ModelFeatureGroup),
        development_count=77,
        validation_count=19,
    )
    oracle_manifest = tmp_path / "oracle_v2_freeze.json"
    _write_oracle_v2_manifest(oracle_manifest)
    oracle_matrix_manifest = tmp_path / "oracle_v2_matrix_manifest.json"
    _write_oracle_v2_matrix_manifest(oracle_matrix_manifest, oracle_matrix_dir)

    output = tmp_path / "out"
    first = run_pr_e(
        production_matrix_dir,
        output,
        pr_d_freeze_manifest_path=pr_d_manifest,
        oracle_v2_matrix_dir=oracle_matrix_dir,
        oracle_v2_freeze_manifest_path=oracle_manifest,
        oracle_v2_matrix_manifest_path=oracle_matrix_manifest,
    )
    second = run_pr_e(
        production_matrix_dir,
        output,
        pr_d_freeze_manifest_path=pr_d_manifest,
        oracle_v2_matrix_dir=oracle_matrix_dir,
        oracle_v2_freeze_manifest_path=oracle_manifest,
        oracle_v2_matrix_manifest_path=oracle_matrix_manifest,
        resume=True,
    )
    assert first == second
    assert first["manifest"]["result_count"] == 48
    assert first["manifest"]["formal_gate_passed"] is True
    assert first["manifest"]["oracle_status"] == "frozen_v2_validation"
    assert (
        first["diagnostic"]["full_production_validation"][
            "classification"
        ]["production_increment_pm_minus_m_roc_auc"]
        == 0
    )
    assert first["diagnostic"]["oracle_validation"] is not None
    assert json.loads((output / "run_manifest.json").read_text())[
        "blind_2025_y_accessed"
    ] is False


def test_pr_e_formal_run_rejects_missing_oracle_v2(tmp_path: Path) -> None:
    matrix_dir = tmp_path / "pr_d" / "matrices"
    _write_matrices(
        matrix_dir,
        V04CanonicalCohort.FULL_PRODUCTION,
        (
            V04ModelFeatureGroup.M,
            V04ModelFeatureGroup.P,
            V04ModelFeatureGroup.PM,
        ),
        development_count=354,
        validation_count=70,
    )
    manifest = tmp_path / "pr_d_freeze.json"
    _write_pr_d_manifest(manifest, matrix_dir)
    with pytest.raises(ValueError, match="formal PR-E requires frozen Oracle v2"):
        run_pr_e(
            matrix_dir,
            tmp_path / "out",
            pr_d_freeze_manifest_path=manifest,
        )


def test_pr_e_rejects_matrix_checksum_drift(tmp_path: Path) -> None:
    matrix_dir = tmp_path / "pr_d" / "matrices"
    _write_matrices(
        matrix_dir,
        V04CanonicalCohort.FULL_PRODUCTION,
        (
            V04ModelFeatureGroup.M,
            V04ModelFeatureGroup.P,
            V04ModelFeatureGroup.PM,
        ),
        development_count=354,
        validation_count=70,
    )
    manifest = tmp_path / "pr_d_freeze.json"
    _write_pr_d_manifest(manifest, matrix_dir)
    target = matrix_dir / "full_production_M_development.json"
    target.write_text(target.read_text() + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum mismatch"):
        run_pr_e(
            matrix_dir,
            tmp_path / "out",
            pr_d_freeze_manifest_path=manifest,
            allow_production_only=True,
        )
