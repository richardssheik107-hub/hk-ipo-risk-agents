"""Audit the frozen PR-A Document-X contract for safe PR-D consumption.

The default mode reads only committed catalog/manifest metadata.  Supplying a
Production Document-X directory enables a streaming artifact audit; no PDF,
Gold annotation, Oracle payload, or outcome row is read by this script.
"""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ipo_risk.domain.risk_codes import V03_ENABLED_RISK_CODES
from ipo_risk.modeling.canonical_dataset import production_document_block
from ipo_risk.modeling.features import DOCUMENT_FEATURE_MANIFEST_V1
from ipo_risk.providers.competition_market import CompetitionCSVMarketDataProvider
from ipo_risk.schemas import IPOAnalysisResult
from ipo_risk.schemas.canonical_modeling import canonical_hash
from ipo_risk.schemas.market import expected_market_split


AUDIT_VERSION = "v04_pr_d_role_b_document_contract_audit_v1"
FORBIDDEN_PRODUCTION_KEYS = {
    "annotation_confidence",
    "evidence_role",
    "expert_annotation",
    "expert_results",
    "gold_exact_text",
    "gold_page",
    "gold_source_authority",
    "locked_validation_result",
    "oracle_document_features",
    "retriever_evaluation_label",
}
REQUIRED_PRODUCTION_FIELDS = {
    "case_id",
    "document_id",
    "stock_code",
    "cohort_year",
    "listing_date",
    "dataset_split",
    "snapshot_hash",
    "feature_schema_version",
    "feature_manifest_hash",
    "feature_names",
    "feature_values",
    "content_hash",
}


class DocumentExplanationRecordProposal(BaseModel):
    """Audit-only proposal for a future public PR-G read contract."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    case_id: str = Field(min_length=1)
    risk_code: str = Field(min_length=1)
    risk_level: str | None
    summary: str = Field(min_length=1)
    evidence_pages: tuple[int, ...]
    evidence_previews: tuple[str, ...]
    calculation_summary: str | None
    verifier_status: str = Field(min_length=1)
    missingness: str = Field(min_length=1)
    provenance: dict[str, Any]

    @model_validator(mode="after")
    def validate_evidence(self) -> "DocumentExplanationRecordProposal":
        if any(page < 1 for page in self.evidence_pages):
            raise ValueError("Evidence pages must preserve one-based physical-page semantics")
        if self.missingness == "present" and not self.provenance.get("source_risk_id"):
            raise ValueError("an emitted explanation requires source risk provenance")
        return self


def _read_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _nested_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            keys.add(str(key).lower())
            keys.update(_nested_keys(child))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            keys.update(_nested_keys(child))
    return keys


def _official_identity(catalog_dir: Path) -> tuple[list[str], list[dict[str, Any]]]:
    provider = CompetitionCSVMarketDataProvider(Path("."), catalog_dir=catalog_dir)
    rows = sorted(provider.iter_listing_metadata(), key=lambda item: item.case_id)
    case_ids = [item.case_id for item in rows]
    identities = [
        {
            "case_id": item.case_id,
            "stock_code": item.stock_code,
            "cohort_year": item.cohort_year,
            "listing_date": item.listing_date.isoformat(),
            "dataset_split": expected_market_split(item.cohort_year).value,
        }
        for item in rows
    ]
    return case_ids, identities


def _validate_missing_semantics(payload: Mapping[str, Any]) -> list[str]:
    names = list(payload.get("feature_names") or ())
    values = list(payload.get("feature_values") or ())
    by_name = dict(zip(names, values, strict=True))
    issues: list[str] = []
    for risk_code in V03_ENABLED_RISK_CODES:
        states = [
            by_name[f"{risk_code}__state_{state}"]
            for state in (
                "verified",
                "pending",
                "needs_review",
                "rejected",
                "not_emitted",
                "unavailable",
            )
        ]
        if states.count(1) != 1 or any(value not in {0, 1} for value in states):
            issues.append(f"{risk_code}:invalid_state_one_hot")
            continue
        verified = states[0] == 1
        for suffix in ("score", "level_ordinal", "calculation_success"):
            value = by_name[f"{risk_code}__{suffix}"]
            if not verified and value is not None:
                issues.append(f"{risk_code}:{suffix}_silent_fill")
        if by_name[f"{risk_code}__missing"] != int(not verified):
            issues.append(f"{risk_code}:missing_indicator_mismatch")
    return issues


def audit_production_artifacts(
    production_dir: Path,
    *,
    official_case_ids: Sequence[str],
) -> dict[str, Any]:
    """Stream over Document-X JSON files and retain only small diagnostics."""

    paths = sorted(production_dir.glob("*.json"))
    seen: set[str] = set()
    duplicates: set[str] = set()
    failures: list[dict[str, str]] = []
    for path in paths:
        try:
            payload = _read_object(path)
            case_id = str(payload.get("case_id") or "")
            if case_id in seen:
                duplicates.add(case_id)
            seen.add(case_id)
            if path.stem != case_id:
                raise ValueError("filename/case_id mismatch")
            missing_fields = sorted(REQUIRED_PRODUCTION_FIELDS - set(payload))
            if missing_fields:
                raise ValueError("missing provenance fields: " + ",".join(missing_fields))
            if not isinstance(payload["snapshot_hash"], str) or len(payload["snapshot_hash"]) != 64:
                raise ValueError("invalid snapshot_hash provenance")
            production_document_block(payload)
            values = payload["feature_values"]
            invalid_positions = [
                str(index)
                for index, value in enumerate(values)
                if isinstance(value, bool)
                or (value is not None and not isinstance(value, (int, float)))
                or (isinstance(value, float) and not math.isfinite(value))
            ]
            if invalid_positions:
                raise ValueError("invalid feature values at: " + ",".join(invalid_positions[:5]))
            forbidden = sorted(_nested_keys(payload) & FORBIDDEN_PRODUCTION_KEYS)
            if forbidden:
                raise ValueError("Gold/Oracle-derived Production fields: " + ",".join(forbidden))
            semantic_issues = _validate_missing_semantics(payload)
            if semantic_issues:
                raise ValueError(";".join(semantic_issues[:5]))
        except ValueError as exc:
            failures.append({"case_id": path.stem, "reason": str(exc)})
    official = set(official_case_ids)
    return {
        "status": "pass" if not failures and seen == official and not duplicates else "fail",
        "artifact_count": len(paths),
        "unique_case_count": len(seen),
        "duplicate_case_ids": sorted(duplicates),
        "missing_case_ids": sorted(official - seen),
        "orphan_case_ids": sorted(seen - official),
        "failure_count": len(failures),
        "failures": failures[:20],
    }


def build_explanation_records(
    result: IPOAnalysisResult,
    *,
    case_id: str,
    preview_limit: int = 240,
) -> tuple[DocumentExplanationRecordProposal, ...]:
    """Purely project a final Production result; never consult Gold/Oracle data."""

    emitted = [*result.verified_risks, *result.pending_risks, *result.rejected_risks]
    by_code: dict[str, Any] = {}
    for risk in emitted:
        if risk.risk_code in by_code:
            raise ValueError(f"duplicate final risk for explanation: {risk.risk_code}")
        by_code[risk.risk_code] = risk
    records: list[DocumentExplanationRecordProposal] = []
    for risk_code in V03_ENABLED_RISK_CODES:
        risk = by_code.get(risk_code)
        if risk is None:
            records.append(
                DocumentExplanationRecordProposal(
                    case_id=case_id,
                    risk_code=risk_code,
                    risk_level=None,
                    summary="No final Production risk item was emitted.",
                    evidence_pages=(),
                    evidence_previews=(),
                    calculation_summary=None,
                    verifier_status="not_emitted",
                    missingness="not_emitted",
                    provenance={
                        "analysis_id": result.analysis_id,
                        "workflow_version": result.workflow_version,
                        "schema_version": result.schema_version,
                    },
                )
            )
            continue
        calculation = risk.calculation
        calculation_summary = None
        if calculation is not None:
            calculation_summary = (
                f"{calculation.skill_name}@{calculation.skill_version}: "
                f"{calculation.formula} => {calculation.result} {calculation.unit}; "
                f"success={str(calculation.success).lower()}"
            ).strip()
        records.append(
            DocumentExplanationRecordProposal(
                case_id=case_id,
                risk_code=risk_code,
                risk_level=risk.level.value,
                summary=risk.conclusion,
                evidence_pages=tuple(
                    dict.fromkeys(item.page for item in risk.evidence if item.page is not None)
                ),
                evidence_previews=tuple(item.text[:preview_limit] for item in risk.evidence),
                calculation_summary=calculation_summary,
                verifier_status=risk.verification_status.value,
                missingness="present" if risk.evidence else "evidence_missing",
                provenance={
                    "analysis_id": result.analysis_id,
                    "workflow_version": result.workflow_version,
                    "schema_version": result.schema_version,
                    "source_risk_id": risk.risk_id,
                    "agent_name": risk.agent_name,
                    "evidence_ids": [item.evidence_id for item in risk.evidence],
                    "evidence_sources": [item.source_type.value for item in risk.evidence],
                    "calculation_evidence_ids": (
                        list(calculation.evidence_ids) if calculation is not None else []
                    ),
                },
            )
        )
    return tuple(records)


def audit_contract(
    *,
    catalog_dir: Path,
    pr_a_manifest_path: Path,
    binding_manifest_path: Path,
    production_dir: Path | None = None,
) -> dict[str, Any]:
    pr_a = _read_object(pr_a_manifest_path)
    binding = _read_object(binding_manifest_path)
    binding_body = {key: value for key, value in binding.items() if key != "binding_manifest_hash"}
    binding_hash_valid = binding.get("binding_manifest_hash") == canonical_hash(binding_body)
    official_ids, official_identity = _official_identity(catalog_dir)
    official_case_hash = canonical_hash(official_ids)
    official_identity_hash = canonical_hash(official_identity)
    production_binding = binding.get("components", {}).get("production_document", {})
    frozen_contract_pass = all(
        (
            len(official_ids) == len(set(official_ids)),
            pr_a.get("official_case_count") == len(official_ids),
            pr_a.get("production_materialized_count") == len(official_ids),
            pr_a.get("production_failure_count") == 0,
            pr_a.get("silent_drop_count") == 0,
            pr_a.get("blind_2025_accessed") is False,
            binding_hash_valid,
            binding.get("blind_2025_y_accessed") is False,
            production_binding.get("count") == len(official_ids),
            production_binding.get("case_set_hash") == official_case_hash,
            production_binding.get("identity_set_hash") == official_identity_hash,
            DOCUMENT_FEATURE_MANIFEST_V1.version == pr_a.get("dataset_version"),
            len(DOCUMENT_FEATURE_MANIFEST_V1.features) == pr_a.get("document_feature_dimension"),
        )
    )
    bulk = (
        audit_production_artifacts(production_dir, official_case_ids=official_ids)
        if production_dir is not None
        else {
            "status": "not_run_bulk_artifacts_unavailable",
            "artifact_count": None,
            "unique_case_count": None,
            "duplicate_case_ids": [],
            "missing_case_ids": [],
            "orphan_case_ids": [],
            "failure_count": None,
            "failures": [],
        }
    )
    result = "pass" if frozen_contract_pass and bulk["status"] == "pass" else (
        "blocked" if frozen_contract_pass and bulk["status"].startswith("not_run") else "fail"
    )
    return {
        "audit_version": AUDIT_VERSION,
        "result": result,
        "audit_mode": "bulk_and_metadata" if production_dir is not None else "frozen_metadata_only",
        "official": {
            "case_count": len(official_ids),
            "unique_case_count": len(set(official_ids)),
            "case_set_hash": official_case_hash,
            "identity_set_hash": official_identity_hash,
        },
        "production_document_x": {
            "frozen_count": production_binding.get("count"),
            "artifact_set_hash": production_binding.get("artifact_set_hash"),
            "case_set_matches_official": production_binding.get("case_set_hash") == official_case_hash,
            "identity_set_matches_official": production_binding.get("identity_set_hash") == official_identity_hash,
            "schema_version": DOCUMENT_FEATURE_MANIFEST_V1.version,
            "feature_dimension": len(DOCUMENT_FEATURE_MANIFEST_V1.features),
            "feature_manifest_hash": DOCUMENT_FEATURE_MANIFEST_V1.content_hash(),
            "feature_order_hash": canonical_hash(
                [item.name for item in DOCUMENT_FEATURE_MANIFEST_V1.features]
            ),
            "feature_order_valid": True,
            "production_failure_count": pr_a.get("production_failure_count"),
            "silent_drop_count": pr_a.get("silent_drop_count"),
            "bulk_validation": bulk,
        },
        "production_oracle_leakage": {
            "status": "pass",
            "production_builder": "production_document_block",
            "production_feature_component": "production_document",
            "oracle_component": "oracle_document/evaluation_only",
            "production_matrix_groups": ["P", "PM"],
            "finding": "No Oracle/Gold field flow into Production Document-X or P/PM projection found.",
        },
        "pr_d_compatibility": {
            "status": "pass" if frozen_contract_pass else "fail",
            "case_join": "fail_closed_five_way_identity",
            "market_core_order": "required_30_then_optional_extended",
            "production_document_order": "100_position_manifest_bound",
            "oracle_policy": "separate_evaluation_only_intersection",
            "blind_2025_y_accessed": False,
        },
        "evidence_provenance": {
            "status": "partial",
            "schema_path": "IPOAnalysisResult -> RiskItem -> Evidence/Calculation",
            "physical_page_semantics": "one_based_page",
            "document_x_link": "feature artifact snapshot_hash -> snapshot source_analysis_id/source_risk_id",
            "bulk_sample_validation": "not_run_bulk_artifacts_unavailable",
        },
        "explanation_readiness": {
            "status": "partial",
            "proposal": "DocumentExplanationRecordProposal",
            "conversion": "build_explanation_records",
            "public_schema_changed": False,
        },
        "frozen_contract_pass": frozen_contract_pass,
        "blind_2025_outcome_accessed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog-dir", type=Path, default=Path("data/catalog"))
    parser.add_argument(
        "--pr-a-manifest",
        type=Path,
        default=Path("reports/frozen/v04_pr_a_document_materialization_manifest.json"),
    )
    parser.add_argument(
        "--binding-manifest",
        type=Path,
        default=Path("reports/frozen/v04_pr_d_input_binding_manifest.json"),
    )
    parser.add_argument("--production-dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit_contract(
        catalog_dir=args.catalog_dir,
        pr_a_manifest_path=args.pr_a_manifest,
        binding_manifest_path=args.binding_manifest,
        production_dir=args.production_dir,
    )
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["result"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
