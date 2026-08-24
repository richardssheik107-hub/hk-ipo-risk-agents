from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pytest

from ipo_risk.modeling.oracle_document import oracle_feature_names
from ipo_risk.modeling.oracle_document_v2 import (
    ORACLE_V2_FEATURE_MANIFEST_HASH,
    ORACLE_V2_POLICY_VERSION,
    ORACLE_V2_SCHEMA_VERSION,
)
from ipo_risk.modeling.oracle_v2_matrices import (
    ORACLE_V2_FREEZE_MANIFEST_VERSION,
    build_oracle_v2_matrices,
)
from ipo_risk.schemas.canonical_modeling import (
    V04CanonicalCohort,
    V04CanonicalModelMatrix,
    V04ModelFeatureGroup,
    canonical_hash,
)
from ipo_risk.schemas.market import MarketDatasetSplit


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _case_ids(split: MarketDatasetSplit, count: int) -> tuple[str, ...]:
    if split is MarketDatasetSplit.VALIDATION:
        return tuple(f"ipo_2024_{index:05d}" for index in range(count))
    return tuple(
        f"ipo_{2020 + index * 4 // count}_{index:05d}" for index in range(count)
    )


def _matrix(
    group: V04ModelFeatureGroup,
    split: MarketDatasetSplit,
    count: int,
) -> V04CanonicalModelMatrix:
    case_ids = _case_ids(split, count)
    return V04CanonicalModelMatrix(
        cohort=V04CanonicalCohort.FULL_PRODUCTION,
        dataset_split=split,
        feature_group=group,
        source_dataset_hash=("a" if split is MarketDatasetSplit.DEVELOPMENT else "b") * 64,
        feature_manifest_hash=canonical_hash({"group": group.value}),
        target_policy_hash="c" * 64,
        target_threshold_hash="d" * 64,
        case_ids=case_ids,
        feature_names=(f"{group.value}__signal", f"{group.value}__missing"),
        feature_values=tuple((float(index % 2), 0.0) for index in range(count)),
        raw_return_5d=tuple(
            Decimal("-0.20") if index % 2 else Decimal("0.10")
            for index in range(count)
        ),
        poor_performer_5d=tuple(bool(index % 2) for index in range(count)),
    )


def _write_pr_d(tmp_path: Path) -> tuple[Path, Path, dict[str, object]]:
    matrix_dir = tmp_path / "pr_d" / "matrices"
    matrix_dir.mkdir(parents=True)
    runtime_files: dict[str, dict[str, object]] = {}
    for group in (
        V04ModelFeatureGroup.M,
        V04ModelFeatureGroup.P,
        V04ModelFeatureGroup.PM,
    ):
        for split, count in (
            (MarketDatasetSplit.DEVELOPMENT, 354),
            (MarketDatasetSplit.VALIDATION, 70),
        ):
            matrix = _matrix(group, split, count)
            filename = f"full_production_{group.value}_{split.value}.json"
            path = matrix_dir / filename
            path.write_text(matrix.model_dump_json(), encoding="utf-8")
            runtime_files[f"matrices/{filename}"] = {
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
    manifest: dict[str, object] = {
        "manifest_version": "v04_pr_d_freeze_manifest_v1",
        "status": "complete_frozen",
        "blind_2025_y_accessed": False,
        "model_ready_count": 424,
        "development_model_ready_count": 354,
        "validation_model_ready_count": 70,
        "freeze_manifest_hash": "e" * 64,
        "runtime_files": runtime_files,
    }
    manifest_path = tmp_path / "pr_d_freeze.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return matrix_dir, manifest_path, manifest


def _oracle_payload(case_id: str, split: str, year: int, index: int) -> dict[str, object]:
    official = {
        "case_id": case_id,
        "document_id": f"doc_{case_id}",
        "stock_code": f"{index:05d}.HK",
        "cohort_year": year,
        "listing_date": f"{year}-01-02",
        "dataset_split": split,
    }
    payload: dict[str, object] = {
        **official,
        "official_identity": official,
        "evaluation_only": True,
        "production_consumable": False,
        "oracle_feature_schema_version": ORACLE_V2_SCHEMA_VERSION,
        "oracle_feature_policy_version": ORACLE_V2_POLICY_VERSION,
        "oracle_manifest_hash": ORACLE_V2_FEATURE_MANIFEST_HASH,
        "feature_names": list(oracle_feature_names()),
        "feature_values": [float(index % 3)] * len(oracle_feature_names()),
        "effective_annotation_hash": canonical_hash({"case_id": case_id}),
    }
    payload["content_hash"] = canonical_hash(payload)
    return payload


def _write_oracle(
    tmp_path: Path,
    development_ids: tuple[str, ...],
    validation_ids: tuple[str, ...],
) -> tuple[Path, Path]:
    feature_dir = tmp_path / "oracle_v2" / "features"
    feature_dir.mkdir(parents=True)
    selected = [
        (case_id, "development", int(case_id[4:8]))
        for case_id in development_ids[:77]
    ]
    selected.extend(
        (case_id, "validation", 2024) for case_id in validation_ids[:19]
    )
    selected.extend(
        (
            ("ipo_2020_90000", "development", 2020),
            ("ipo_2020_90001", "development", 2020),
        )
    )
    entries = []
    for index, (case_id, split, year) in enumerate(selected):
        payload = _oracle_payload(case_id, split, year, index)
        (feature_dir / f"{case_id}.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )
        entries.append(
            {
                "case_id": case_id,
                "content_hash": payload["content_hash"],
                "schema_version": ORACLE_V2_SCHEMA_VERSION,
                "policy_version": ORACLE_V2_POLICY_VERSION,
                "official_identity": payload["official_identity"],
                "effective_annotation_hash": payload["effective_annotation_hash"],
            }
        )
    entries.sort(key=lambda row: row["case_id"])
    all_ids = sorted(row["case_id"] for row in entries)
    strict_ids = sorted(set(development_ids[:77]) | set(validation_ids[:19]))
    manifest = {
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
        "artifact_set_hash": canonical_hash(entries),
        "case_set_hash": canonical_hash(all_ids),
        "strict_usable_case_set_hash": canonical_hash(strict_ids),
        "source_annotation_inventory_hash": "a" * 64,
        "pr_d_freeze_manifest_hash": "e" * 64,
        "freeze_manifest_hash": "f" * 64,
    }
    manifest_path = tmp_path / "oracle_v2_freeze.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return feature_dir, manifest_path


def test_build_oracle_v2_matrices_is_fair_bound_and_resumable(tmp_path: Path) -> None:
    matrix_dir, pr_d_manifest_path, _ = _write_pr_d(tmp_path)
    development_ids = _case_ids(MarketDatasetSplit.DEVELOPMENT, 354)
    validation_ids = _case_ids(MarketDatasetSplit.VALIDATION, 70)
    feature_dir, oracle_manifest_path = _write_oracle(
        tmp_path, development_ids, validation_ids
    )
    output_dir = tmp_path / "out"
    first = build_oracle_v2_matrices(
        production_matrix_dir=matrix_dir,
        oracle_feature_dir=feature_dir,
        pr_d_freeze_manifest_path=pr_d_manifest_path,
        oracle_v2_freeze_manifest_path=oracle_manifest_path,
        output_dir=output_dir,
    )
    second = build_oracle_v2_matrices(
        production_matrix_dir=matrix_dir,
        oracle_feature_dir=feature_dir,
        pr_d_freeze_manifest_path=pr_d_manifest_path,
        oracle_v2_freeze_manifest_path=oracle_manifest_path,
        output_dir=output_dir,
        resume=True,
    )
    assert first == second
    assert first["development_model_ready_count"] == 77
    assert first["validation_model_ready_count"] == 19
    assert len(first["runtime_files"]) == 10
    matrices = [
        V04CanonicalModelMatrix.model_validate_json(path.read_text())
        for path in sorted((output_dir / "matrices").glob("*.json"))
    ]
    for split in MarketDatasetSplit.DEVELOPMENT, MarketDatasetSplit.VALIDATION:
        current = [matrix for matrix in matrices if matrix.dataset_split is split]
        assert len({matrix.case_ids for matrix in current}) == 1
        assert len({matrix.raw_return_5d for matrix in current}) == 1
        assert len({matrix.source_dataset_hash for matrix in current}) == 1


def test_build_oracle_v2_matrices_rejects_artifact_drift(tmp_path: Path) -> None:
    matrix_dir, pr_d_manifest_path, _ = _write_pr_d(tmp_path)
    feature_dir, oracle_manifest_path = _write_oracle(
        tmp_path,
        _case_ids(MarketDatasetSplit.DEVELOPMENT, 354),
        _case_ids(MarketDatasetSplit.VALIDATION, 70),
    )
    path = next(feature_dir.glob("*.json"))
    payload = json.loads(path.read_text())
    payload["feature_values"][0] = 99
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="content_hash_mismatch"):
        build_oracle_v2_matrices(
            production_matrix_dir=matrix_dir,
            oracle_feature_dir=feature_dir,
            pr_d_freeze_manifest_path=pr_d_manifest_path,
            oracle_v2_freeze_manifest_path=oracle_manifest_path,
            output_dir=tmp_path / "out",
        )
