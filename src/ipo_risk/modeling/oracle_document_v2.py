"""Versioned, evaluation-only Oracle v2 materialization and governance."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ipo_risk.domain.risk_codes import V03_ENABLED_RISK_CODES
from ipo_risk.evaluation.expert_annotation import validate_expert_annotation_payload
from ipo_risk.modeling.oracle_document import load_risk_gold, oracle_feature_names
from ipo_risk.schemas.canonical_modeling import canonical_hash


ORACLE_V2_SCHEMA_VERSION = "expert_oracle_document_features_v2"
ORACLE_V2_POLICY_VERSION = "oracle_gold_policy_v2"
ORACLE_V2_FEATURE_MANIFEST = {
    "schema_version": ORACLE_V2_SCHEMA_VERSION,
    "policy_version": ORACLE_V2_POLICY_VERSION,
    "feature_names": list(oracle_feature_names()),
    "evaluation_only": True,
    "missing_semantics": "unknown is explicit and is never converted to zero-risk",
}
ORACLE_V2_FEATURE_MANIFEST_HASH = canonical_hash(ORACLE_V2_FEATURE_MANIFEST)


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid_json:{path.name}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"expected_object:{path.name}")
    return value


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact_hash(payload: dict[str, Any]) -> str:
    return canonical_hash({k: v for k, v in payload.items() if k != "content_hash"})


def _feature_values(bundle: Any) -> tuple[Any, ...]:
    evidence = bundle.evidence
    values: dict[str, int | float] = {}
    confidences: list[float] = []
    for risk in bundle.risks:
        code = risk.risk_code
        rows = [item for item in evidence if item.risk_code == code]
        status = risk.expected_status.value
        level = getattr(risk.expected_level, "value", None)
        fields = {
            "applicable": int(risk.applicable),
            "status_verified": int(status == "verified"),
            "status_needs_review": int(status == "needs_review"),
            "status_rejected": int(status == "rejected"),
            "level_low": int(level == "low"),
            "level_medium": int(level == "medium"),
            "level_high": int(level == "high"),
            "level_critical": int(level == "critical"),
            "level_not_applicable": int(level == "not_applicable"),
            "confidence": risk.confidence,
            "evidence_count": len(rows),
            "required_evidence_count": sum(
                item.requirement.value == "required" for item in rows
            ),
            "primary_evidence_count": sum(
                item.evidence_role.value == "primary" for item in rows
            ),
            "calculation_required": int(risk.calculation_required),
            "calculation_result_available": int(risk.calculation_result is not None),
            "missing": 0,
        }
        values.update({f"{code}__{name}": value for name, value in fields.items()})
        confidences.append(risk.confidence)

    def count(suffix: str) -> int:
        return sum(int(values[f"{risk}__{suffix}"]) for risk in V03_ENABLED_RISK_CODES)

    values.update(
        {
            "applicable_risk_count": count("applicable"),
            "verified_risk_count": count("status_verified"),
            "needs_review_count": count("status_needs_review"),
            "rejected_count": count("status_rejected"),
            "high_risk_count": count("level_high"),
            "critical_risk_count": count("level_critical"),
            "high_or_critical_count": count("level_high") + count("level_critical"),
            "mean_confidence": sum(confidences) / len(confidences),
            "min_confidence": min(confidences),
            "calculation_required_count": count("calculation_required"),
            "calculation_available_count": count("calculation_result_available"),
            "total_evidence_count": count("evidence_count"),
            "required_evidence_count": count("required_evidence_count"),
            "primary_evidence_count": count("primary_evidence_count"),
        }
    )
    return tuple(values[name] for name in oracle_feature_names())


def load_official_identities(production_dir: Path) -> dict[str, dict[str, Any]]:
    identities: dict[str, dict[str, Any]] = {}
    for path in sorted(production_dir.glob("*.json")):
        payload = _read(path)
        case_id = str(payload.get("case_id") or "")
        if path.stem != case_id or case_id in identities:
            raise ValueError(f"official_identity_conflict:{path.name}")
        identities[case_id] = {
            "case_id": case_id,
            "document_id": payload.get("document_id"),
            "stock_code": payload.get("stock_code"),
            "cohort_year": payload.get("cohort_year"),
            "listing_date": payload.get("listing_date"),
            "dataset_split": payload.get("dataset_split"),
        }
    if not identities:
        raise ValueError("official_identity_source_empty")
    return identities


def annotation_inventory(root: Path) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in sorted((root / "expert_results").glob("*/pass1/expert_annotation_v1.json")):
        payload = _read(path)
        case_id = str(payload.get("case_id") or "")
        directory_case = path.parents[1].name
        meta_path = (
            root
            / "docs/annotation/gpt_expert_v1_1/case_packets"
            / case_id
            / "case_metadata.json"
        )
        status = "valid"
        reason = ""
        if not directory_case.startswith("ipo_"):
            status, reason = "invalid", "noncanonical_legacy_path"
        elif directory_case != case_id:
            raise ValueError(f"duplicate_or_directory_identity:{directory_case}:{case_id}")
        elif case_id in seen:
            raise ValueError(f"duplicate_annotation:{case_id}")
        elif not meta_path.is_file():
            status, reason = "invalid", "missing_metadata"
        seen.add(case_id)
        audit_path = path.parents[1] / "audit/financial_resolution_v1.json"
        audit_hash = _file_hash(audit_path) if audit_path.is_file() else None
        stale = False
        if audit_path.is_file():
            audit = _read(audit_path)
            stale = audit.get("source_pass1_sha256") != _file_hash(path)
        annotation_version = payload.get("annotation_version")
        entry = {
            "case_id": case_id,
            "source_directory": directory_case,
            "annotation_version": annotation_version,
            "base_pass_hash": _file_hash(path),
            "audit_hash": audit_hash,
            "audit_status": "stale_not_applied" if stale else ("fresh" if audit_hash else "none"),
            "status": status,
            "reason": reason,
        }
        entry["effective_annotation_hash"] = canonical_hash(
            {
                "base_pass_hash": entry["base_pass_hash"],
                "audit_hash": audit_hash if not stale else None,
                "audit_status": entry["audit_status"],
            }
        )
        entries.append(entry)
    entries.sort(key=lambda item: (item["case_id"], item["source_directory"]))
    return {
        "count": len(entries),
        "valid_count": sum(item["status"] == "valid" for item in entries),
        "invalid_count": sum(item["status"] != "valid" for item in entries),
        "audit_count": sum(item["audit_hash"] is not None for item in entries),
        "stale_audit_count": sum(item["audit_status"] == "stale_not_applied" for item in entries),
        "entries": entries,
        "inventory_hash": canonical_hash(entries),
    }


def build_oracle_v2_artifact(
    root: Path,
    case_id: str,
    official: dict[str, Any],
    inventory_entry: dict[str, Any],
) -> dict[str, Any]:
    path = root / "expert_results" / case_id / "pass1/expert_annotation_v1.json"
    meta_path = root / "docs/annotation/gpt_expert_v1_1/case_packets" / case_id / "case_metadata.json"
    payload, metadata = _read(path), _read(meta_path)
    if official.get("case_id") != case_id:
        raise ValueError(f"annotation_identity_unresolved:{case_id}")
    bundle, issues = validate_expert_annotation_payload(payload, page_count=int(metadata["page_count"]))
    if bundle is None or issues:
        raise ValueError("invalid_annotation:" + ",".join(issue.code for issue in issues))
    if bundle.case_id != case_id:
        raise ValueError(f"annotation_identity_unresolved:{case_id}")
    source_kind = "pass1_only"
    effective_annotation_hash = inventory_entry["effective_annotation_hash"]
    if inventory_entry["audit_status"] == "fresh":
        gold = load_risk_gold(root, case_id)
        bundle = gold.bundle
        source_kind = gold.source_kind
        effective_annotation_hash = gold.effective_annotation_hash
    elif inventory_entry["audit_status"] == "stale_not_applied":
        source_kind = "pass1_stale_audit_not_applied"
    if int(official["cohort_year"]) >= 2025 or official["dataset_split"] == "blind":
        raise ValueError("blind_2025_oracle_materialization_prohibited")
    declared = {
        "case_id": bundle.case_id,
        "document_id": bundle.document_id,
        "stock_code": bundle.stock_code,
        "cohort_year": metadata.get("source_year"),
        "listing_date": metadata.get("listing_date"),
        "dataset_split": metadata.get("dataset_split"),
    }
    rebound = any(
        declared.get(key) != official.get(key)
        for key in ("stock_code", "cohort_year", "listing_date", "dataset_split")
    )
    artifact = {
        **official,
        "company_name": bundle.company_name,
        "source_annotation_version": bundle.annotation_version,
        "source_annotation_kind": source_kind,
        "base_pass_hash": inventory_entry["base_pass_hash"],
        "audit_hash": inventory_entry["audit_hash"],
        "audit_status": inventory_entry["audit_status"],
        "effective_annotation_hash": effective_annotation_hash,
        "annotation_declared_identity": declared,
        "official_identity": official,
        "reconciliation_status": "annotation_identity_rebound_to_official" if rebound else "identity_already_official",
        "evaluation_only": True,
        "production_consumable": False,
        "oracle_feature_schema_version": ORACLE_V2_SCHEMA_VERSION,
        "oracle_feature_policy_version": ORACLE_V2_POLICY_VERSION,
        "oracle_manifest_hash": ORACLE_V2_FEATURE_MANIFEST_HASH,
        "feature_names": oracle_feature_names(),
        "feature_values": _feature_values(bundle),
    }
    artifact["content_hash"] = _artifact_hash(artifact)
    return artifact


def validate_oracle_v2_artifact(payload: dict[str, Any]) -> None:
    if payload.get("content_hash") != _artifact_hash(payload):
        raise ValueError("oracle_v2_content_hash_mismatch")
    if payload.get("evaluation_only") is not True or payload.get("production_consumable") is not False:
        raise ValueError("oracle_v2_production_isolation_violation")
    if payload.get("oracle_feature_schema_version") != ORACLE_V2_SCHEMA_VERSION:
        raise ValueError("oracle_v2_schema_drift")
    if payload.get("oracle_feature_policy_version") != ORACLE_V2_POLICY_VERSION:
        raise ValueError("oracle_v2_policy_drift")
    if payload.get("oracle_manifest_hash") != ORACLE_V2_FEATURE_MANIFEST_HASH:
        raise ValueError("oracle_v2_manifest_drift")
    if tuple(payload.get("feature_names") or ()) != oracle_feature_names():
        raise ValueError("oracle_v2_feature_order_drift")


def materialize_oracle_v2(
    *, root: Path, production_dir: Path, target_dir: Path, output_dir: Path, resume: bool
) -> dict[str, Any]:
    inventory = annotation_inventory(root)
    official = load_official_identities(production_dir)
    targets = {path.stem: _read(path) for path in sorted(target_dir.glob("*.json"))}
    statuses: list[dict[str, Any]] = []
    artifact_entries: list[dict[str, Any]] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    valid_entries = [item for item in inventory["entries"] if item["status"] == "valid"]
    for item in valid_entries:
        case_id = item["case_id"]
        if case_id not in official:
            statuses.append({"case_id": case_id, "status": "excluded", "reason": "non_official_case"})
            continue
        try:
            artifact = build_oracle_v2_artifact(root, case_id, official[case_id], item)
            validate_oracle_v2_artifact(artifact)
            path = output_dir / "features" / f"{case_id}.json"
            if path.exists():
                existing = _read(path)
                if not resume:
                    raise ValueError("existing_artifact_requires_resume")
                if existing != json.loads(json.dumps(artifact, ensure_ascii=False)):
                    raise ValueError("resume_provenance_conflict")
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            target = targets.get(case_id)
            eligible = bool(target and target.get("availability") == "available")
            reason = "" if eligible else (f"outcome_unavailable:{target.get('missing_reason')}" if target else "outcome_missing")
            statuses.append({"case_id": case_id, "status": "materialized", "outcome_eligible": eligible, "reason": reason, "dataset_split": official[case_id]["dataset_split"], "reconciliation_status": artifact["reconciliation_status"]})
            artifact_entries.append({"case_id": case_id, "content_hash": artifact["content_hash"], "schema_version": ORACLE_V2_SCHEMA_VERSION, "policy_version": ORACLE_V2_POLICY_VERSION, "official_identity": official[case_id], "effective_annotation_hash": artifact["effective_annotation_hash"]})
        except ValueError as exc:
            if "resume_provenance_conflict" in str(exc):
                raise
            statuses.append({"case_id": case_id, "status": "failed", "reason": str(exc)})
    for item in inventory["entries"]:
        if item["status"] != "valid":
            statuses.append({"case_id": item["case_id"], "status": "excluded", "reason": item["reason"]})
    statuses.sort(key=lambda item: (item["case_id"], item["status"]))
    artifact_entries.sort(key=lambda item: item["case_id"])
    strict = [item for item in statuses if item.get("status") == "materialized" and item.get("outcome_eligible")]
    body = {
        "run_version": "v04_oracle_v2_materialization_v1",
        "schema_version": ORACLE_V2_SCHEMA_VERSION,
        "policy_version": ORACLE_V2_POLICY_VERSION,
        "feature_manifest_hash": ORACLE_V2_FEATURE_MANIFEST_HASH,
        "source_annotation_inventory_count": inventory["count"],
        "valid_annotation_count": inventory["valid_count"],
        "invalid_annotation_count": inventory["invalid_count"],
        "audit_overlay_count": inventory["audit_count"],
        "stale_audit_count": inventory["stale_audit_count"],
        "source_annotation_inventory_hash": inventory["inventory_hash"],
        "official_identity_set_hash": canonical_hash([official[key] for key in sorted(official)]),
        "materialized_count": len(artifact_entries),
        "strict_usable_count": len(strict),
        "development_usable_count": sum(item.get("dataset_split") == "development" for item in strict),
        "validation_usable_count": sum(item.get("dataset_split") == "validation" for item in strict),
        "outcome_unavailable_count": sum(item.get("status") == "materialized" and not item.get("outcome_eligible") for item in statuses),
        "identity_reconciled_count": sum(item.get("reconciliation_status") == "annotation_identity_rebound_to_official" for item in statuses),
        "identity_unresolved_count": sum("identity_unresolved" in item.get("reason", "") for item in statuses),
        "case_set_hash": canonical_hash([item["case_id"] for item in artifact_entries]),
        "strict_usable_case_set_hash": canonical_hash([item["case_id"] for item in strict]),
        "artifact_set_hash": canonical_hash(artifact_entries),
        "status_set_hash": canonical_hash(statuses),
        "evaluation_only": True,
        "production_consumable": False,
        "blind_2025_y_accessed": False,
        "oracle_v1_modified": False,
        "statuses": statuses,
    }
    body["run_manifest_hash"] = canonical_hash(body)
    manifest_path = output_dir / "run_manifest.json"
    if manifest_path.exists() and resume and _read(manifest_path) != body:
        raise ValueError("resume_manifest_conflict")
    manifest_path.write_text(json.dumps(body, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return body
