from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from ipo_risk.modeling.oracle_document import build_oracle_document_features
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
PRODUCTION = ROOT / "reports/v04_pr_a_full_13e0281/production_features"
TARGETS = ROOT / "reports/v04_pr_c/targets"


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _artifact(case_id: str = "ipo_2020_00368") -> dict:
    inventory = annotation_inventory(ROOT)
    entry = next(item for item in inventory["entries"] if item["case_id"] == case_id and item["status"] == "valid")
    official = _read(PRODUCTION / f"{case_id}.json")
    identity = {key: official[key] for key in ("case_id", "document_id", "stock_code", "cohort_year", "listing_date", "dataset_split")}
    return build_oracle_v2_artifact(ROOT, case_id, identity, entry)


def test_oracle_v1_regression_is_unchanged() -> None:
    assert build_oracle_document_features(ROOT, "ipo_2020_00368")["content_hash"] == (
        "5036f890a13a694e2b16a58a9cd01fcdb9ee8389bdaa1db1fc955a7433a43eca"
    )


def test_inventory_is_deterministic_and_audits_legacy_alias() -> None:
    first = annotation_inventory(ROOT)
    second = annotation_inventory(ROOT)
    assert first == second
    assert first["count"] == 101
    assert first["valid_count"] == 100
    assert first["invalid_count"] == 1
    assert first["audit_count"] == 87
    assert first["stale_audit_count"] == 74


@pytest.mark.parametrize("case_id", ["ipo_2020_08489", "ipo_2020_09600", "ipo_2022_02450", "ipo_2023_02503", "ipo_2024_02410"])
def test_official_identity_reconciles_annotation_metadata(case_id: str) -> None:
    inventory = annotation_inventory(ROOT)
    entry = next(item for item in inventory["entries"] if item["case_id"] == case_id and item["status"] == "valid")
    official = _read(PRODUCTION / f"{case_id}.json")
    identity = {key: official[key] for key in ("case_id", "document_id", "stock_code", "cohort_year", "listing_date", "dataset_split")}
    artifact = build_oracle_v2_artifact(ROOT, case_id, identity, entry)
    assert artifact["official_identity"] == identity
    assert artifact["listing_date"] == identity["listing_date"]
    assert artifact["dataset_split"] == identity["dataset_split"]
    assert artifact["reconciliation_status"] == "annotation_identity_rebound_to_official"


def test_non_official_and_outcome_unavailable_are_explicit(tmp_path: Path) -> None:
    result = materialize_oracle_v2(root=ROOT, production_dir=PRODUCTION, target_dir=TARGETS, output_dir=tmp_path, resume=False)
    statuses = {item["case_id"]: item for item in result["statuses"] if item["case_id"] != "ipo_2024_02410"}
    assert statuses["ipo_2024_00805"]["reason"] == "non_official_case"
    assert statuses["ipo_2024_02613"]["reason"] == "non_official_case"
    assert statuses["ipo_2020_02599"]["status"] == "materialized"
    assert statuses["ipo_2020_02599"]["outcome_eligible"] is False
    assert statuses["ipo_2020_06688"]["outcome_eligible"] is False


def test_unresolved_and_blind_identity_fail_closed() -> None:
    inventory = annotation_inventory(ROOT)
    entry = next(item for item in inventory["entries"] if item["case_id"] == "ipo_2020_00368" and item["status"] == "valid")
    official = _read(PRODUCTION / "ipo_2020_00368.json")
    identity = {key: official[key] for key in ("case_id", "document_id", "stock_code", "cohort_year", "listing_date", "dataset_split")}
    identity["case_id"] = "wrong_case"
    with pytest.raises(ValueError, match="identity_unresolved"):
        build_oracle_v2_artifact(ROOT, "ipo_2020_00368", identity, entry)
    identity["case_id"] = "ipo_2020_00368"
    identity["cohort_year"] = 2025
    identity["dataset_split"] = "blind"
    with pytest.raises(ValueError, match="blind_2025"):
        build_oracle_v2_artifact(ROOT, "ipo_2020_00368", identity, entry)


def test_duplicate_and_invalid_annotation_fail(tmp_path: Path) -> None:
    source = ROOT / "expert_results/ipo_2020_00368/pass1/expert_annotation_v1.json"
    metadata = ROOT / "docs/annotation/gpt_expert_v1_1/case_packets/ipo_2020_00368/case_metadata.json"
    duplicate = tmp_path / "expert_results/ipo_2020_99999/pass1/expert_annotation_v1.json"
    duplicate.parent.mkdir(parents=True)
    shutil.copyfile(source, duplicate)
    with pytest.raises(ValueError, match="directory_identity"):
        annotation_inventory(tmp_path)
    invalid_root = tmp_path / "invalid"
    valid = invalid_root / "expert_results/ipo_2020_00368/pass1/expert_annotation_v1.json"
    valid.parent.mkdir(parents=True)
    valid.write_text("{}", encoding="utf-8")
    meta = invalid_root / "docs/annotation/gpt_expert_v1_1/case_packets/ipo_2020_00368/case_metadata.json"
    meta.parent.mkdir(parents=True)
    shutil.copyfile(metadata, meta)
    with pytest.raises(ValueError, match="directory_identity"):
        annotation_inventory(invalid_root)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("content_hash", "0" * 64, "content_hash"),
        ("oracle_feature_schema_version", "drift", "schema_drift"),
        ("feature_names", ["drift"], "feature_order_drift"),
        ("evaluation_only", False, "isolation_violation"),
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
    inventory = annotation_inventory(ROOT)
    entry = next(item for item in inventory["entries"] if item["case_id"] == "ipo_2020_00368" and item["status"] == "valid")
    assert entry["audit_status"] == "stale_not_applied"
    official = _read(PRODUCTION / "ipo_2020_00368.json")
    identity = {key: official[key] for key in ("case_id", "document_id", "stock_code", "cohort_year", "listing_date", "dataset_split")}
    artifact = build_oracle_v2_artifact(ROOT, "ipo_2020_00368", identity, entry)
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
    target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert annotation_inventory(tmp_path)["inventory_hash"] != before


def test_resume_same_passes_and_conflict_fails(tmp_path: Path) -> None:
    first = materialize_oracle_v2(root=ROOT, production_dir=PRODUCTION, target_dir=TARGETS, output_dir=tmp_path, resume=False)
    second = materialize_oracle_v2(root=ROOT, production_dir=PRODUCTION, target_dir=TARGETS, output_dir=tmp_path, resume=True)
    assert first == second
    path = tmp_path / "features/ipo_2020_00368.json"
    payload = _read(path)
    payload["content_hash"] = "0" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="resume_provenance_conflict"):
        materialize_oracle_v2(root=ROOT, production_dir=PRODUCTION, target_dir=TARGETS, output_dir=tmp_path, resume=True)


def test_artifact_set_is_deterministic(tmp_path: Path) -> None:
    one = materialize_oracle_v2(root=ROOT, production_dir=PRODUCTION, target_dir=TARGETS, output_dir=tmp_path / "one", resume=False)
    two = materialize_oracle_v2(root=ROOT, production_dir=PRODUCTION, target_dir=TARGETS, output_dir=tmp_path / "two", resume=False)
    assert one["artifact_set_hash"] == two["artifact_set_hash"]
    assert one["status_set_hash"] == two["status_set_hash"]
