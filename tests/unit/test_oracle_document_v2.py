from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import pytest

from ipo_risk.modeling.oracle_document import (
    ORACLE_DOCUMENT_FEATURE_MANIFEST_HASH,
    ORACLE_DOCUMENT_FEATURE_POLICY_VERSION,
    ORACLE_DOCUMENT_FEATURE_SCHEMA_VERSION,
)
from ipo_risk.modeling.oracle_document_v2 import (
    ORACLE_V2_FEATURE_MANIFEST_HASH,
    ORACLE_V2_POLICY_VERSION,
    ORACLE_V2_SCHEMA_VERSION,
    annotation_inventory,
    build_oracle_v2_artifact,
    materialize_oracle_v2,
    validate_oracle_v2_artifact,
)
from ipo_risk.schemas.canonical_modeling import canonical_hash


ROOT = Path(__file__).resolve().parents[2]


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _official(case_id: str) -> dict:
    bridge = ROOT / "data/catalog/ipo_official_master_bridge.csv"
    with bridge.open(encoding="utf-8-sig", newline="") as handle:
        row = next(item for item in csv.DictReader(handle) if item["case_id"] == case_id)
    annotation = _read(
        ROOT / "expert_results" / case_id / "pass1/expert_annotation_v1.json"
    )
    listed_date = row["official_listed_date"]
    return {
        "case_id": case_id,
        "document_id": annotation["document_id"],
        "stock_code": row["stock_code_wind"],
        "cohort_year": int(listed_date[:4]),
        "listing_date": listed_date,
        "dataset_split": row["dataset_split"],
    }


def _entry(case_id: str) -> dict:
    return next(
        item
        for item in annotation_inventory(ROOT)["entries"]
        if item["case_id"] == case_id and item["status"] == "valid"
    )


def _artifact(case_id: str = "ipo_2020_00368") -> dict:
    return build_oracle_v2_artifact(ROOT, case_id, _official(case_id), _entry(case_id))


def _write_inputs(
    root: Path,
    case_ids: tuple[str, ...],
    unavailable: dict[str, str] | None = None,
) -> tuple[Path, Path]:
    production, targets = root / "production", root / "targets"
    production.mkdir(parents=True)
    targets.mkdir(parents=True)
    unavailable = unavailable or {}
    for case_id in case_ids:
        (production / f"{case_id}.json").write_text(
            json.dumps(_official(case_id), ensure_ascii=False), encoding="utf-8"
        )
        target = {
            "case_id": case_id,
            "availability": "unavailable" if case_id in unavailable else "available",
            "missing_reason": unavailable.get(case_id),
        }
        (targets / f"{case_id}.json").write_text(
            json.dumps(target, ensure_ascii=False), encoding="utf-8"
        )
    return production, targets


def _verified_test_binding(case_count: int) -> dict:
    return {
        "upstream_binding_verified": True,
        "upstream_binding_hash": "test-upstream-binding",
        "binding_manifest_hash": "test-binding-manifest",
        "pr_d_freeze_manifest_hash": "test-pr-d-freeze",
        "pr_a_manifest_identity": {"filename": "pr_a.json", "sha256": "test"},
        "pr_c_manifest_identity": {"filename": "pr_c.json", "sha256": "test"},
        "pr_c_freeze_manifest_hash": "test-pr-c-freeze",
        "official_case_count": case_count,
        "production_artifact_set_hash": "test-production",
        "outcome_artifact_set_hash": "test-outcome",
        "pr_c_target_set_hash": "test-target-set",
        "pr_c_policy_hash": "test-policy",
        "pr_c_threshold_hash": "test-threshold",
    }


def test_oracle_v1_contract_is_unchanged() -> None:
    assert ORACLE_DOCUMENT_FEATURE_SCHEMA_VERSION == "expert_oracle_document_features_v1"
    assert ORACLE_DOCUMENT_FEATURE_POLICY_VERSION == "oracle_gold_policy_v1"
    assert ORACLE_DOCUMENT_FEATURE_MANIFEST_HASH == (
        "f5f5ebfa3f23c457e6302c65af564b0ec2b586c5952875df0daa9e105fd166ff"
    )


def test_inventory_is_deterministic_and_cross_platform() -> None:
    first = annotation_inventory(ROOT)
    assert first == annotation_inventory(ROOT)
    assert first["count"] == 101
    assert first["valid_count"] == 100
    assert first["invalid_count"] == 1
    assert first["audit_count"] == 87
    assert first["stale_audit_count"] == 17
    assert _entry("ipo_2020_00368")["audit_status"] == "fresh"


@pytest.mark.parametrize(
    "case_id",
    [
        "ipo_2020_08489",
        "ipo_2020_09600",
        "ipo_2022_02450",
        "ipo_2023_02503",
        "ipo_2024_02410",
    ],
)
def test_official_identity_reconciles_annotation_metadata(case_id: str) -> None:
    identity = _official(case_id)
    artifact = build_oracle_v2_artifact(ROOT, case_id, identity, _entry(case_id))
    assert artifact["official_identity"] == identity
    assert artifact["listing_date"] == identity["listing_date"]
    assert artifact["dataset_split"] == identity["dataset_split"]
    assert artifact["reconciliation_status"] == "annotation_identity_rebound_to_official"


def test_non_official_and_outcome_unavailable_are_explicit(tmp_path: Path) -> None:
    case_ids = ("ipo_2020_00368", "ipo_2020_02599", "ipo_2020_06688")
    production, targets = _write_inputs(
        tmp_path,
        case_ids,
        {"ipo_2020_02599": "missing_base_price", "ipo_2020_06688": "no_eligible_session"},
    )
    result = materialize_oracle_v2(
        root=ROOT,
        production_dir=production,
        target_dir=targets,
        output_dir=tmp_path / "output",
        resume=False,
        upstream_binding=_verified_test_binding(len(case_ids)),
    )
    statuses = {item["case_id"]: item for item in result["statuses"] if item["case_id"] != "ipo_2024_02410"}
    assert statuses["ipo_2024_00805"]["reason"] == "non_official_case"
    assert statuses["ipo_2024_02613"]["reason"] == "non_official_case"
    assert statuses["ipo_2020_02599"]["status"] == "materialized"
    assert statuses["ipo_2020_02599"]["outcome_eligible"] is False
    assert statuses["ipo_2020_06688"]["outcome_eligible"] is False


def test_unresolved_and_blind_identity_fail_closed() -> None:
    identity = _official("ipo_2020_00368")
    identity["case_id"] = "wrong_case"
    with pytest.raises(ValueError, match="identity_unresolved"):
        build_oracle_v2_artifact(ROOT, "ipo_2020_00368", identity, _entry("ipo_2020_00368"))
    identity = _official("ipo_2020_00368")
    identity["cohort_year"] = 2025
    identity["dataset_split"] = "blind"
    with pytest.raises(ValueError, match="blind_2025"):
        build_oracle_v2_artifact(ROOT, "ipo_2020_00368", identity, _entry("ipo_2020_00368"))


def test_duplicate_and_invalid_annotation_fail(tmp_path: Path) -> None:
    source = ROOT / "expert_results/ipo_2020_00368/pass1/expert_annotation_v1.json"
    duplicate = tmp_path / "expert_results/ipo_2020_99999/pass1/expert_annotation_v1.json"
    duplicate.parent.mkdir(parents=True)
    shutil.copyfile(source, duplicate)
    with pytest.raises(ValueError, match="directory_identity"):
        annotation_inventory(tmp_path)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("content_hash", "0" * 64, "content_hash"),
        ("oracle_feature_schema_version", "drift", "schema_drift"),
        ("oracle_feature_policy_version", "drift", "policy_drift"),
        ("oracle_manifest_hash", "drift", "manifest_drift"),
        ("feature_names", ["drift"], "feature_order_drift"),
        ("evaluation_only", False, "isolation_violation"),
        ("production_consumable", True, "isolation_violation"),
    ],
)
def test_artifact_corruption_fails(field: str, value: object, message: str) -> None:
    payload = _artifact()
    payload[field] = value
    if field != "content_hash":
        payload["content_hash"] = canonical_hash(
            {key: item for key, item in payload.items() if key != "content_hash"}
        )
    with pytest.raises(ValueError, match=message):
        validate_oracle_v2_artifact(payload)


def test_versioned_schema_policy_and_production_isolation() -> None:
    payload = _artifact()
    validate_oracle_v2_artifact(payload)
    assert payload["oracle_feature_schema_version"] == ORACLE_V2_SCHEMA_VERSION
    assert payload["oracle_feature_policy_version"] == ORACLE_V2_POLICY_VERSION
    assert payload["oracle_manifest_hash"] == ORACLE_V2_FEATURE_MANIFEST_HASH
    assert payload["evaluation_only"] is True
    assert payload["production_consumable"] is False


def test_stale_audit_is_explicit_and_not_applied() -> None:
    case_id = "ipo_2024_00300"
    entry = _entry(case_id)
    assert entry["audit_status"] == "stale_not_applied"
    artifact = build_oracle_v2_artifact(ROOT, case_id, _official(case_id), entry)
    assert artifact["source_annotation_kind"] == "pass1_stale_audit_not_applied"


def test_inventory_mutation_changes_hash(tmp_path: Path) -> None:
    source = ROOT / "expert_results/ipo_2020_00368/pass1/expert_annotation_v1.json"
    target = tmp_path / "expert_results/ipo_2020_00368/pass1/expert_annotation_v1.json"
    target.parent.mkdir(parents=True)
    shutil.copyfile(source, target)
    meta_source = ROOT / "docs/annotation/gpt_expert_v1_1/case_packets/ipo_2020_00368/case_metadata.json"
    meta = tmp_path / "docs/annotation/gpt_expert_v1_1/case_packets/ipo_2020_00368/case_metadata.json"
    meta.parent.mkdir(parents=True)
    shutil.copyfile(meta_source, meta)
    before = annotation_inventory(tmp_path)["inventory_hash"]
    payload = _read(target)
    payload["company_name"] += " mutation"
    target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    assert annotation_inventory(tmp_path)["inventory_hash"] != before


def test_resume_same_passes_and_conflict_fails(tmp_path: Path) -> None:
    production, targets = _write_inputs(tmp_path, ("ipo_2020_00368",))
    output = tmp_path / "output"
    first = materialize_oracle_v2(
        root=ROOT, production_dir=production, target_dir=targets, output_dir=output, resume=False,
        upstream_binding=_verified_test_binding(1),
    )
    second = materialize_oracle_v2(
        root=ROOT, production_dir=production, target_dir=targets, output_dir=output, resume=True,
        upstream_binding=_verified_test_binding(1),
    )
    assert first == second
    path = output / "features/ipo_2020_00368.json"
    payload = _read(path)
    payload["content_hash"] = "0" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="resume_provenance_conflict"):
        materialize_oracle_v2(
            root=ROOT, production_dir=production, target_dir=targets, output_dir=output, resume=True,
            upstream_binding=_verified_test_binding(1),
        )


def test_artifact_set_is_deterministic(tmp_path: Path) -> None:
    production, targets = _write_inputs(tmp_path, ("ipo_2020_00368", "ipo_2020_01942"))
    one = materialize_oracle_v2(
        root=ROOT, production_dir=production, target_dir=targets, output_dir=tmp_path / "one", resume=False,
        upstream_binding=_verified_test_binding(2),
    )
    two = materialize_oracle_v2(
        root=ROOT, production_dir=production, target_dir=targets, output_dir=tmp_path / "two", resume=False,
        upstream_binding=_verified_test_binding(2),
    )
    assert one["artifact_set_hash"] == two["artifact_set_hash"]
    assert one["status_set_hash"] == two["status_set_hash"]
