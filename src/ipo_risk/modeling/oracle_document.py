"""Evaluation-only Oracle document features built from reviewed expert annotations.

This module deliberately has no imports from retrievers, agents, verifiers, or
production document-feature materialisation.  It is an upper-bound research
input, never a production ``RiskItem`` or V04 document feature vector.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ipo_risk.domain.risk_codes import V03_ENABLED_RISK_CODES
from ipo_risk.evaluation.expert_annotation import ExpertAnnotationBundle, validate_expert_annotation_payload
from ipo_risk.schemas.market import MarketDatasetSplit, MarketLabelAvailability, MarketLabelHorizon, MarketOutcomeLabel

ORACLE_DOCUMENT_FEATURE_SCHEMA_VERSION = "expert_oracle_document_features_v1"
ORACLE_DOCUMENT_FEATURE_POLICY_VERSION = "oracle_gold_policy_v1"
SOURCE_KIND = "audited_pass1"

_RISK_FIELDS = (
    "applicable", "status_verified", "status_needs_review", "status_rejected",
    "level_low", "level_medium", "level_high", "level_critical", "level_not_applicable",
    "confidence", "evidence_count", "required_evidence_count", "primary_evidence_count",
    "calculation_required", "calculation_result_available", "missing",
)
_AGGREGATES = (
    "applicable_risk_count", "verified_risk_count", "needs_review_count", "rejected_count",
    "high_risk_count", "critical_risk_count", "high_or_critical_count", "mean_confidence",
    "min_confidence", "calculation_required_count", "calculation_available_count",
    "total_evidence_count", "required_evidence_count", "primary_evidence_count",
)

def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()

def oracle_feature_names() -> tuple[str, ...]:
    return tuple(
        f"{risk}__{field}"
        for risk in sorted(V03_ENABLED_RISK_CODES)
        for field in _RISK_FIELDS
    ) + _AGGREGATES

ORACLE_DOCUMENT_FEATURE_MANIFEST = {
    "schema_version": ORACLE_DOCUMENT_FEATURE_SCHEMA_VERSION,
    "policy_version": ORACLE_DOCUMENT_FEATURE_POLICY_VERSION,
    "features": [{"index": i, "name": name, "dtype": "float64" if name.endswith("confidence") else "int8"}
                 for i, name in enumerate(oracle_feature_names())],
    "missing_semantics": "missing is explicit; null/unknown is never converted to zero-risk",
}
ORACLE_DOCUMENT_FEATURE_MANIFEST_HASH = _sha(ORACLE_DOCUMENT_FEATURE_MANIFEST)

@dataclass(frozen=True)
class EffectiveRiskGoldView:
    bundle: ExpertAnnotationBundle
    base_pass_hash: str
    source_path: str
    source_kind: str
    audit_hash: str | None
    audit_source_pass_hash: str | None
    audit_status: str
    audit_applied_risks: tuple[str, ...]
    effective_annotation_hash: str

def _case_metadata(root: Path, case_id: str) -> dict[str, Any]:
    path = root / "docs" / "annotation" / "gpt_expert_v1_1" / "case_packets" / case_id / "case_metadata.json"
    if not path.is_file():
        raise ValueError(f"missing case metadata: {case_id}")
    return json.loads(path.read_text(encoding="utf-8"))

def load_risk_gold(root: Path, case_id: str, *, allow_provisional: bool = False) -> EffectiveRiskGoldView:
    if not allow_provisional and "provisional" in case_id.lower():
        raise ValueError("provisional annotations are disabled by default")
    path = root / "expert_results" / case_id / "pass1" / "expert_annotation_v1.json"
    if not path.is_file():
        raise ValueError(f"missing expert annotation: {case_id}")
    metadata = _case_metadata(root, case_id)
    payload = json.loads(path.read_text(encoding="utf-8"))
    bundle, issues = validate_expert_annotation_payload(payload, page_count=int(metadata["page_count"]))
    if bundle is None or issues:
        raise ValueError("invalid gold annotation: " + "; ".join(issue.code for issue in issues))
    if bundle.case_id != case_id or bundle.document_id != metadata["document_id"]:
        raise ValueError("annotation/case metadata identity mismatch")
    base_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    audit = root / "expert_results" / case_id / "audit" / "financial_resolution_v1.json"
    overlay: dict[str, Any] = {}
    audit_hash = None
    audit_source_hash = None
    states: dict[str, dict[str, Any]] = {}
    if audit.is_file():
        raw_audit = audit.read_bytes()
        overlay = json.loads(raw_audit)
        audit_hash = hashlib.sha256(raw_audit).hexdigest()
        audit_source_hash = overlay.get("source_pass1_sha256")
        # An entry is authoritative only when it self-identifies a canonical risk
        # and contains a complete, schema-valid resolved state.  Nothing else in
        # the old pass is ever restored into the current pass1 base.
        for item in overlay.get("entries", []):
            if not isinstance(item, dict) or item.get("risk_code") not in V03_ENABLED_RISK_CODES:
                continue
            state = item.get("resolved_state")
            if isinstance(state, dict) and {"applicable", "expected_status", "expected_level"} <= set(state):
                states[item["risk_code"]] = state
    risks = []
    for risk in bundle.risks:
        if risk.risk_code in states:
            risks.append(type(risk).model_validate({**risk.model_dump(mode="json"), **states[risk.risk_code]}))
        else:
            risks.append(risk)
    final_bundle = bundle.model_copy(update={"risks": risks})
    applied = tuple(sorted(states))
    effective_hash = _sha({"base_pass_hash": base_hash, "audit_hash": audit_hash, "applied_risks": applied,
                           "effective_risks": [risk.model_dump(mode="json") for risk in final_bundle.risks]})
    return EffectiveRiskGoldView(final_bundle, base_hash, path.relative_to(root).as_posix(),
        SOURCE_KIND if applied else "pass1_only", audit_hash, audit_source_hash,
        "applied_stale_audit" if audit_hash and audit_source_hash != base_hash else ("applied" if applied else "no_audit"),
        applied, effective_hash)

def build_oracle_document_features(root: Path, case_id: str) -> dict[str, Any]:
    gold = load_risk_gold(root, case_id)
    meta = _case_metadata(root, case_id)
    evidence = gold.bundle.evidence
    values: dict[str, int | float] = {}
    confidences: list[float] = []
    for risk in gold.bundle.risks:
        code = risk.risk_code
        rows = [item for item in evidence if item.risk_code == code]
        status, level = risk.expected_status.value, getattr(risk.expected_level, "value", None)
        field_values = {
            "applicable": int(risk.applicable), "status_verified": int(status == "verified"),
            "status_needs_review": int(status == "needs_review"), "status_rejected": int(status == "rejected"),
            "level_low": int(level == "low"), "level_medium": int(level == "medium"),
            "level_high": int(level == "high"), "level_critical": int(level == "critical"),
            "level_not_applicable": int(level == "not_applicable"), "confidence": risk.confidence,
            "evidence_count": len(rows), "required_evidence_count": sum(r.requirement.value == "required" for r in rows),
            "primary_evidence_count": sum(r.evidence_role.value == "primary" for r in rows),
            "calculation_required": int(risk.calculation_required),
            "calculation_result_available": int(risk.calculation_result is not None), "missing": 0,
        }
        values.update({f"{code}__{key}": value for key, value in field_values.items()})
        confidences.append(risk.confidence)
    def count(suffix: str) -> int: return sum(values[f"{r}__{suffix}"] for r in V03_ENABLED_RISK_CODES)
    values.update({"applicable_risk_count": count("applicable"), "verified_risk_count": count("status_verified"),
                   "needs_review_count": count("status_needs_review"), "rejected_count": count("status_rejected"),
                   "high_risk_count": count("level_high"), "critical_risk_count": count("level_critical"),
                   "high_or_critical_count": count("level_high") + count("level_critical"),
                   "mean_confidence": sum(confidences)/len(confidences), "min_confidence": min(confidences),
                   "calculation_required_count": count("calculation_required"), "calculation_available_count": count("calculation_result_available"),
                   "total_evidence_count": count("evidence_count"), "required_evidence_count": count("required_evidence_count"),
                   "primary_evidence_count": count("primary_evidence_count")})
    names = oracle_feature_names()
    artifact = {"case_id": case_id, "document_id": gold.bundle.document_id, "stock_code": gold.bundle.stock_code,
        "company_name": gold.bundle.company_name, "cohort_year": int(meta["source_year"]), "listing_date": None,
        "dataset_split": meta["dataset_split"], "source_annotation_version": gold.bundle.annotation_version,
        "source_annotation_kind": gold.source_kind, "base_pass_hash": gold.base_pass_hash,
        "audit_hash": gold.audit_hash, "audit_source_pass_hash": gold.audit_source_pass_hash,
        "audit_status": gold.audit_status, "audit_applied_risks": gold.audit_applied_risks,
        "effective_annotation_hash": gold.effective_annotation_hash, "evaluation_only": True,
        "oracle_feature_schema_version": ORACLE_DOCUMENT_FEATURE_SCHEMA_VERSION,
        "oracle_feature_policy_version": ORACLE_DOCUMENT_FEATURE_POLICY_VERSION,
        "oracle_manifest_hash": ORACLE_DOCUMENT_FEATURE_MANIFEST_HASH, "feature_names": names,
        "feature_values": tuple(values[name] for name in names)}
    artifact["content_hash"] = _sha(artifact)
    return artifact


def join_oracle_outcome(feature: dict[str, Any], label: MarketOutcomeLabel) -> dict[str, Any]:
    """Strict research-only join; 2025 and unavailable labels are never coerced."""
    for key in ("case_id", "stock_code", "cohort_year", "dataset_split"):
        left = feature.get(key)
        right = getattr(label, key)
        right = right.value if hasattr(right, "value") else right
        if left != right:
            raise ValueError(f"oracle/outcome identity mismatch: {key}")
    if label.dataset_split is MarketDatasetSplit.BLIND:
        raise ValueError("2025 blind features cannot join an outcome label")
    if label.horizon is not MarketLabelHorizon.FIVE_DAYS:
        raise ValueError("Oracle baseline accepts only the raw 5D outcome")
    if label.availability is not MarketLabelAvailability.AVAILABLE:
        raise ValueError("unavailable market outcome cannot enter a modeling dataset")
    return {"feature": feature, "raw_return_5d": float(label.raw_return),
            "outcome_provenance": label.model_dump(mode="json"), "dataset_split": feature["dataset_split"]}
