"""Build governed Oracle-v2 fair-comparison matrices for PR-E and PR-F."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from ipo_risk.modeling.oracle_document import oracle_feature_names
from ipo_risk.modeling.oracle_document_v2 import (
    ORACLE_V2_FEATURE_MANIFEST_HASH,
    ORACLE_V2_POLICY_VERSION,
    ORACLE_V2_SCHEMA_VERSION,
    validate_oracle_v2_artifact,
)
from ipo_risk.schemas.canonical_modeling import (
    V04CanonicalCohort,
    V04CanonicalModelMatrix,
    V04ModelFeatureGroup,
    canonical_hash,
)


ORACLE_V2_FREEZE_MANIFEST_VERSION = "v04_oracle_v2_freeze_manifest_v1"
ORACLE_V2_MATRIX_MANIFEST_VERSION = "v04_oracle_v2_matrix_manifest_v1"
ORACLE_V2_MATRIX_POLICY_VERSION = "v04_oracle_v2_matrix_policy_v1"
PR_D_FREEZE_MANIFEST_VERSION = "v04_pr_d_freeze_manifest_v1"


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise ValueError(f"missing Oracle-v2 matrix input: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid Oracle-v2 matrix JSON: {path}") from exc


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any, *, resume: bool) -> None:
    normalized = json.loads(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    if path.exists():
        if not resume:
            raise ValueError(f"Oracle-v2 matrix output exists; use --resume: {path}")
        if _read_json(path) != normalized:
            raise ValueError(f"Oracle-v2 matrix output conflict: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def validate_pr_d_freeze(manifest: dict[str, Any]) -> None:
    """Validate the exact PR-D freeze contract consumed downstream."""

    if manifest.get("manifest_version") != PR_D_FREEZE_MANIFEST_VERSION:
        raise ValueError("Oracle-v2 matrices require the frozen PR-D manifest version")
    if manifest.get("status") != "complete_frozen":
        raise ValueError("Oracle-v2 matrices require PR-D complete_frozen")
    if manifest.get("blind_2025_y_accessed") is not False:
        raise ValueError("Oracle-v2 matrices reject PR-D that accessed 2025 Blind y")
    if (
        manifest.get("model_ready_count"),
        manifest.get("development_model_ready_count"),
        manifest.get("validation_model_ready_count"),
    ) != (424, 354, 70):
        raise ValueError("Oracle-v2 matrices require the frozen PR-D 424/354/70 cohort")


def validate_oracle_v2_freeze(manifest: dict[str, Any]) -> None:
    """Validate the exact Oracle-v2 freeze contract merged through PR #97."""

    if manifest.get("manifest_version") != ORACLE_V2_FREEZE_MANIFEST_VERSION:
        raise ValueError("formal modeling requires Oracle v2 freeze manifest v1")
    if manifest.get("status") != "complete_frozen":
        raise ValueError("formal modeling requires Oracle v2 complete_frozen")
    if manifest.get("a_final_sign_off") != "passed":
        raise ValueError("formal modeling requires Oracle v2 A final sign-off")
    if manifest.get("evaluation_only") is not True:
        raise ValueError("Oracle v2 must remain evaluation_only")
    if manifest.get("production_consumable") is not False:
        raise ValueError("Oracle v2 cannot become production-consumable")
    if manifest.get("blind_2025_y_accessed") is not False:
        raise ValueError("formal modeling rejects Oracle v2 that accessed 2025 Blind y")
    if manifest.get("schema_version") != ORACLE_V2_SCHEMA_VERSION:
        raise ValueError("Oracle v2 schema drift")
    if manifest.get("policy_version") != ORACLE_V2_POLICY_VERSION:
        raise ValueError("Oracle v2 policy drift")
    if manifest.get("feature_manifest_hash") != ORACLE_V2_FEATURE_MANIFEST_HASH:
        raise ValueError("Oracle v2 feature manifest drift")
    if (
        manifest.get("materialized_count"),
        manifest.get("strict_usable_count"),
        manifest.get("development_usable_count"),
        manifest.get("validation_usable_count"),
    ) != (98, 96, 77, 19):
        raise ValueError("Oracle v2 freeze row counts do not match 98/96/77/19")
    for field in (
        "artifact_set_hash",
        "case_set_hash",
        "strict_usable_case_set_hash",
        "source_annotation_inventory_hash",
        "pr_d_freeze_manifest_hash",
    ):
        if not isinstance(manifest.get(field), str) or len(manifest[field]) != 64:
            raise ValueError(f"Oracle v2 freeze is missing {field}")


def _verify_pr_d_matrices(
    matrix_dir: Path,
    manifest: dict[str, Any],
) -> dict[tuple[str, str], V04CanonicalModelMatrix]:
    runtime_files = manifest.get("runtime_files")
    if not isinstance(runtime_files, dict):
        raise ValueError("PR-D freeze manifest is missing runtime_files")
    matrices: dict[tuple[str, str], V04CanonicalModelMatrix] = {}
    for group in ("M", "P", "PM"):
        for split in ("development", "validation"):
            filename = f"full_production_{group}_{split}.json"
            path = matrix_dir / filename
            if not path.is_file():
                raise ValueError(f"missing frozen PR-D matrix: {path}")
            expected = runtime_files.get(f"matrices/{filename}")
            if not isinstance(expected, dict) or not expected.get("sha256"):
                raise ValueError(f"PR-D freeze does not bind matrices/{filename}")
            if _sha256_file(path) != expected["sha256"]:
                raise ValueError(f"PR-D matrix checksum mismatch: {filename}")
            matrices[(group, split)] = V04CanonicalModelMatrix.model_validate(
                _read_json(path)
            )
    return matrices


def _artifact_entry(payload: dict[str, Any]) -> dict[str, Any]:
    validate_oracle_v2_artifact(payload)
    if int(payload.get("cohort_year") or 0) >= 2025:
        raise ValueError("Oracle-v2 matrix builder rejects 2025 features")
    if payload.get("dataset_split") not in {"development", "validation"}:
        raise ValueError("Oracle-v2 feature has an ineligible dataset split")
    return {
        "case_id": payload["case_id"],
        "content_hash": payload["content_hash"],
        "schema_version": ORACLE_V2_SCHEMA_VERSION,
        "policy_version": ORACLE_V2_POLICY_VERSION,
        "official_identity": payload["official_identity"],
        "effective_annotation_hash": payload["effective_annotation_hash"],
    }


def _load_oracle_features(
    feature_dir: Path,
    manifest: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    features: dict[str, dict[str, Any]] = {}
    entries: list[dict[str, Any]] = []
    for path in sorted(feature_dir.glob("*.json")):
        payload = _read_json(path)
        case_id = str(payload.get("case_id") or "")
        if path.stem != case_id or case_id in features:
            raise ValueError(f"Oracle-v2 feature identity conflict: {path.name}")
        entries.append(_artifact_entry(payload))
        features[case_id] = payload
    if len(features) != manifest["materialized_count"]:
        raise ValueError("Oracle-v2 feature count does not match its freeze")
    if canonical_hash(entries) != manifest["artifact_set_hash"]:
        raise ValueError("Oracle-v2 artifact-set hash mismatch")
    if canonical_hash(sorted(features)) != manifest["case_set_hash"]:
        raise ValueError("Oracle-v2 case-set hash mismatch")
    return features


def _validate_full_matrix_fairness(
    matrices: dict[tuple[str, str], V04CanonicalModelMatrix],
) -> None:
    for split in ("development", "validation"):
        reference = matrices[("M", split)]
        for group in ("P", "PM"):
            current = matrices[(group, split)]
            for field in (
                "case_ids",
                "raw_return_5d",
                "poor_performer_5d",
                "target_policy_hash",
                "target_threshold_hash",
                "source_dataset_hash",
            ):
                if getattr(reference, field) != getattr(current, field):
                    raise ValueError(f"unfair PR-D {split} M/{group} matrix: {field}")


def _subset_matrix(
    source: V04CanonicalModelMatrix,
    indexes: tuple[int, ...],
    *,
    source_dataset_hash: str,
) -> V04CanonicalModelMatrix:
    return V04CanonicalModelMatrix(
        cohort=V04CanonicalCohort.ORACLE_INTERSECTION,
        dataset_split=source.dataset_split,
        feature_group=source.feature_group,
        source_dataset_hash=source_dataset_hash,
        feature_manifest_hash=source.feature_manifest_hash,
        target_policy_hash=source.target_policy_hash,
        target_threshold_hash=source.target_threshold_hash,
        case_ids=tuple(source.case_ids[index] for index in indexes),
        feature_names=source.feature_names,
        feature_values=tuple(source.feature_values[index] for index in indexes),
        raw_return_5d=tuple(source.raw_return_5d[index] for index in indexes),
        poor_performer_5d=tuple(
            source.poor_performer_5d[index] for index in indexes
        ),
    )


def _oracle_matrix(
    reference: V04CanonicalModelMatrix,
    features: dict[str, dict[str, Any]],
    *,
    source_dataset_hash: str,
) -> V04CanonicalModelMatrix:
    names = tuple(f"oracle_document__{name}" for name in oracle_feature_names())
    return V04CanonicalModelMatrix(
        cohort=V04CanonicalCohort.ORACLE_INTERSECTION,
        dataset_split=reference.dataset_split,
        feature_group=V04ModelFeatureGroup.O,
        source_dataset_hash=source_dataset_hash,
        feature_manifest_hash=canonical_hash(
            {
                "component": "oracle_document",
                "schema_version": ORACLE_V2_SCHEMA_VERSION,
                "policy_version": ORACLE_V2_POLICY_VERSION,
                "manifest_hash": ORACLE_V2_FEATURE_MANIFEST_HASH,
                "feature_names": list(oracle_feature_names()),
            }
        ),
        target_policy_hash=reference.target_policy_hash,
        target_threshold_hash=reference.target_threshold_hash,
        case_ids=reference.case_ids,
        feature_names=names,
        feature_values=tuple(tuple(features[case_id]["feature_values"]) for case_id in reference.case_ids),
        raw_return_5d=reference.raw_return_5d,
        poor_performer_5d=reference.poor_performer_5d,
    )


def _combined_oracle_matrix(
    market: V04CanonicalModelMatrix,
    oracle: V04CanonicalModelMatrix,
) -> V04CanonicalModelMatrix:
    if market.case_ids != oracle.case_ids:
        raise ValueError("Oracle-v2 OM case set drift")
    return V04CanonicalModelMatrix(
        cohort=V04CanonicalCohort.ORACLE_INTERSECTION,
        dataset_split=market.dataset_split,
        feature_group=V04ModelFeatureGroup.OM,
        source_dataset_hash=market.source_dataset_hash,
        feature_manifest_hash=canonical_hash(
            {
                "market_manifest_hash": market.feature_manifest_hash,
                "oracle_manifest_hash": oracle.feature_manifest_hash,
                "feature_names": list(market.feature_names + oracle.feature_names),
            }
        ),
        target_policy_hash=market.target_policy_hash,
        target_threshold_hash=market.target_threshold_hash,
        case_ids=market.case_ids,
        feature_names=market.feature_names + oracle.feature_names,
        feature_values=tuple(
            market_row + oracle_row
            for market_row, oracle_row in zip(
                market.feature_values, oracle.feature_values, strict=True
            )
        ),
        raw_return_5d=market.raw_return_5d,
        poor_performer_5d=market.poor_performer_5d,
    )


def _runtime_file_manifest(paths: Iterable[Path]) -> dict[str, dict[str, Any]]:
    return {
        f"matrices/{path.name}": {
            "sha256": _sha256_file(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(paths)
    }


def build_oracle_v2_matrices(
    *,
    production_matrix_dir: Path,
    oracle_feature_dir: Path,
    pr_d_freeze_manifest_path: Path,
    oracle_v2_freeze_manifest_path: Path,
    output_dir: Path,
    resume: bool = False,
) -> dict[str, Any]:
    """Build M/P/O/PM/OM matrices on the exact Oracle-v2 eligible cohort."""

    pr_d_manifest = _read_json(pr_d_freeze_manifest_path)
    oracle_manifest = _read_json(oracle_v2_freeze_manifest_path)
    validate_pr_d_freeze(pr_d_manifest)
    validate_oracle_v2_freeze(oracle_manifest)
    if oracle_manifest["pr_d_freeze_manifest_hash"] != pr_d_manifest.get(
        "freeze_manifest_hash"
    ):
        raise ValueError("Oracle v2 is not bound to the supplied PR-D freeze")
    full = _verify_pr_d_matrices(production_matrix_dir, pr_d_manifest)
    _validate_full_matrix_fairness(full)
    features = _load_oracle_features(oracle_feature_dir, oracle_manifest)

    all_model_case_ids = {
        case_id
        for split in ("development", "validation")
        for case_id in full[("M", split)].case_ids
    }
    strict_case_ids = tuple(sorted(set(features) & all_model_case_ids))
    if len(strict_case_ids) != oracle_manifest["strict_usable_count"]:
        raise ValueError("Oracle-v2 strict usable count does not match PR-D intersection")
    if canonical_hash(list(strict_case_ids)) != oracle_manifest[
        "strict_usable_case_set_hash"
    ]:
        raise ValueError("Oracle-v2 strict usable case-set hash mismatch")

    matrices: dict[tuple[str, str], V04CanonicalModelMatrix] = {}
    strict_set = set(strict_case_ids)
    for split, expected_count in (
        ("development", oracle_manifest["development_usable_count"]),
        ("validation", oracle_manifest["validation_usable_count"]),
    ):
        source_m = full[("M", split)]
        indexes = tuple(
            index for index, case_id in enumerate(source_m.case_ids) if case_id in strict_set
        )
        if len(indexes) != expected_count:
            raise ValueError(f"Oracle-v2 {split} count does not match its freeze")
        split_case_ids = tuple(source_m.case_ids[index] for index in indexes)
        source_dataset_hash = canonical_hash(
            {
                "matrix_policy_version": ORACLE_V2_MATRIX_POLICY_VERSION,
                "pr_d_freeze_manifest_hash": pr_d_manifest["freeze_manifest_hash"],
                "oracle_v2_freeze_manifest_hash": oracle_manifest[
                    "freeze_manifest_hash"
                ],
                "dataset_split": split,
                "case_ids": split_case_ids,
                "target_policy_hash": source_m.target_policy_hash,
                "target_threshold_hash": source_m.target_threshold_hash,
            }
        )
        for group in ("M", "P", "PM"):
            matrices[(group, split)] = _subset_matrix(
                full[(group, split)], indexes, source_dataset_hash=source_dataset_hash
            )
        oracle = _oracle_matrix(
            matrices[("M", split)], features, source_dataset_hash=source_dataset_hash
        )
        matrices[("O", split)] = oracle
        matrices[("OM", split)] = _combined_oracle_matrix(
            matrices[("M", split)], oracle
        )

    matrix_paths: list[Path] = []
    for (group, split), matrix in sorted(matrices.items()):
        path = output_dir / "matrices" / f"oracle_intersection_{group}_{split}.json"
        _write_json(path, matrix.model_dump(mode="json"), resume=resume)
        matrix_paths.append(path)
    runtime_files = _runtime_file_manifest(matrix_paths)
    manifest = {
        "manifest_version": ORACLE_V2_MATRIX_MANIFEST_VERSION,
        "policy_version": ORACLE_V2_MATRIX_POLICY_VERSION,
        "status": "complete_frozen_inputs",
        "evaluation_only": True,
        "production_consumable": False,
        "blind_2025_y_accessed": False,
        "pr_d_freeze_manifest_sha256": _sha256_file(pr_d_freeze_manifest_path),
        "pr_d_freeze_manifest_hash": pr_d_manifest["freeze_manifest_hash"],
        "oracle_v2_freeze_manifest_sha256": _sha256_file(
            oracle_v2_freeze_manifest_path
        ),
        "oracle_v2_freeze_manifest_hash": oracle_manifest["freeze_manifest_hash"],
        "oracle_v2_artifact_set_hash": oracle_manifest["artifact_set_hash"],
        "strict_usable_case_set_hash": oracle_manifest[
            "strict_usable_case_set_hash"
        ],
        "development_model_ready_count": oracle_manifest[
            "development_usable_count"
        ],
        "validation_model_ready_count": oracle_manifest[
            "validation_usable_count"
        ],
        "feature_groups": ["M", "P", "O", "PM", "OM"],
        "runtime_files": runtime_files,
        "matrix_set_hash": canonical_hash(runtime_files),
    }
    manifest["manifest_hash"] = canonical_hash(manifest)
    _write_json(output_dir / "run_manifest.json", manifest, resume=resume)
    return manifest
