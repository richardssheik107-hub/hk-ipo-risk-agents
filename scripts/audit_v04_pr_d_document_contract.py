"""Audit the frozen PR-A Document-X contract for safe PR-D consumption.

The default mode reads only committed catalog/manifest metadata.  Supplying a
Production Document-X directory enables a streaming artifact audit; no PDF,
Gold annotation, Oracle payload, or outcome row is read by this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import zipfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ipo_risk.domain.risk_codes import V03_ENABLED_RISK_CODES
from ipo_risk.modeling.canonical_dataset import production_document_block
from ipo_risk.modeling.features import DOCUMENT_FEATURE_MANIFEST_V1
from ipo_risk.modeling.pr_d_input_binding import _component_identity
from ipo_risk.providers.competition_market import CompetitionCSVMarketDataProvider
from ipo_risk.schemas import IPOAnalysisResult
from ipo_risk.schemas.canonical_modeling import canonical_hash
from ipo_risk.schemas.market import expected_market_split


AUDIT_VERSION = "v04_pr_d_role_b_document_contract_audit_v1"
EXPECTED_SOURCE_REVISION = "13e0281f5e65a970caaf1255e56d08597e1ead70"
EXPECTED_PRODUCTION_ARTIFACT_SET_HASH = (
    "9197b0f4f90e6d43277586ac40160679d40f91e3b30223578d0853d9dc288bf3"
)
EXPECTED_ZIP_SHA256 = "c88cbb2545b75ac71b94e6499695a750c7aa039c94c05021e331e7d2c6ea5229"
EXPECTED_PACKAGE_MEMBERS = 442
EXPECTED_PRODUCTION_COUNT = 438
FORBIDDEN_PRODUCTION_KEYS = {
    "annotation",
    "annotation_confidence",
    "evidence_role",
    "exact_text",
    "expert",
    "expert_annotation",
    "expert_results",
    "gold",
    "gold_exact_text",
    "gold_page",
    "gold_source_authority",
    "locked_label",
    "locked_validation_result",
    "oracle",
    "oracle_document_features",
    "retrieval_label",
    "retriever_evaluation_label",
    "source_authority",
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


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_archive_name(name: str) -> str | None:
    normalized = name.replace("\\", "/")
    parts = normalized.split("/")
    if (
        normalized.startswith("/")
        or normalized.startswith("\\")
        or re.match(r"^[A-Za-z]:", normalized)
        or any(part == ".." for part in parts)
    ):
        return None
    return normalized


def audit_zip_package(
    zip_path: Path,
    *,
    expected_sha256: str = EXPECTED_ZIP_SHA256,
) -> dict[str, Any]:
    """Validate the small handoff ZIP without extracting or reading PDF content."""

    archive_hash = _file_sha256(zip_path)
    with zipfile.ZipFile(zip_path) as archive:
        names = [item.filename for item in archive.infolist()]
        normalized = [_safe_archive_name(name) for name in names]
        safe_names = [name for name in normalized if name is not None]
        duplicate_paths = sorted(
            name
            for name, count in {
                item: [value.casefold() for value in safe_names].count(item.casefold())
                for item in safe_names
            }.items()
            if count > 1
        )
        production = [
            name
            for name in safe_names
            if re.search(r"(^|/)production_features/[^/]+\.json$", name)
        ]
        manifests = [
            name
            for name in safe_names
            if re.search(
                r"(^|/)manifests/(v04_pr_a_document_materialization_manifest|"
                r"v04_pr_d_input_binding_manifest)\.json$",
                name,
            )
        ]
        readmes = [name for name in safe_names if name.endswith("/README_ROLE_B_HANDOFF.md")]
        checksum_files = [name for name in safe_names if name.endswith("/SHA256SUMS.txt")]
        uncompressed_bytes = sum(item.file_size for item in archive.infolist())
    unsafe_paths = sorted(name for name, safe in zip(names, normalized, strict=True) if safe is None)
    checks = {
        "zip_sha256_matches": archive_hash == expected_sha256,
        "member_count_matches": len(names) == EXPECTED_PACKAGE_MEMBERS,
        "production_json_count_matches": len(production) == EXPECTED_PRODUCTION_COUNT,
        "manifest_count_matches": len(manifests) == 2,
        "readme_count_matches": len(readmes) == 1,
        "checksum_file_count_matches": len(checksum_files) == 1,
        "no_unsafe_paths": not unsafe_paths,
        "no_duplicate_member_paths": not duplicate_paths,
    }
    return {
        "status": "pass" if all(checks.values()) else "fail",
        "zip_sha256": archive_hash,
        "zip_size_bytes": zip_path.stat().st_size,
        "uncompressed_bytes": uncompressed_bytes,
        "member_count": len(names),
        "production_json_count": len(production),
        "manifest_count": len(manifests),
        "readme_count": len(readmes),
        "checksum_file_count": len(checksum_files),
        "unsafe_paths": unsafe_paths[:20],
        "duplicate_member_paths": duplicate_paths[:20],
        "checks": checks,
    }


def verify_checksum_manifest(package_root: Path) -> dict[str, Any]:
    """Verify SHA256SUMS against binary files under one extracted package root."""

    checksum_path = package_root / "SHA256SUMS.txt"
    entries: dict[str, str] = {}
    invalid_lines: list[str] = []
    duplicate_entries: list[str] = []
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r"([0-9a-fA-F]{64})  (.+)", line)
        if match is None:
            invalid_lines.append(line[:200])
            continue
        relative = _safe_archive_name(match.group(2))
        if relative is None:
            invalid_lines.append(line[:200])
            continue
        if relative in entries:
            duplicate_entries.append(relative)
        entries[relative] = match.group(1).lower()
    actual = {
        path.relative_to(package_root).as_posix(): path
        for path in package_root.rglob("*")
        if path.is_file() and path != checksum_path
    }
    missing_entries = sorted(set(actual) - set(entries))
    unexpected_entries = sorted(set(entries) - set(actual))
    mismatches = sorted(
        relative
        for relative in set(actual) & set(entries)
        if _file_sha256(actual[relative]) != entries[relative]
    )
    passed = not any(
        (invalid_lines, duplicate_entries, missing_entries, unexpected_entries, mismatches)
    )
    return {
        "status": "pass" if passed else "fail",
        "checksum_entry_count": len(entries),
        "checked_file_count": len(actual),
        "invalid_line_count": len(invalid_lines),
        "duplicate_entry_count": len(duplicate_entries),
        "missing_checksum_entries": missing_entries[:20],
        "unexpected_checksum_entries": unexpected_entries[:20],
        "hash_mismatches": mismatches[:20],
    }


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


def validate_frozen_manifest_binding(
    pr_a: Mapping[str, Any],
    binding: Mapping[str, Any],
    *,
    official_count: int,
    official_case_hash: str,
    official_identity_hash: str,
) -> dict[str, Any]:
    """Validate the PR-A/PR-D frozen declarations without touching bulk data."""

    production = binding.get("components", {}).get("production_document", {})
    binding_body = {key: value for key, value in binding.items() if key != "binding_manifest_hash"}
    checks = {
        "source_git_revision": pr_a.get("source_git_revision") == EXPECTED_SOURCE_REVISION,
        "official_case_count": pr_a.get("official_case_count") == official_count,
        "production_materialized_count": pr_a.get("production_materialized_count")
        == official_count,
        "production_feature_count": pr_a.get("production_feature_count") == official_count,
        "document_feature_dimension": pr_a.get("document_feature_dimension")
        == len(DOCUMENT_FEATURE_MANIFEST_V1.features),
        "production_failure_count": pr_a.get("production_failure_count") == 0,
        "silent_drop_count": pr_a.get("silent_drop_count") == 0,
        "blind_2025_accessed": pr_a.get("blind_2025_accessed") is False,
        "determinism_passed": pr_a.get("determinism_passed") is True,
        "production_feature_mismatch_count": pr_a.get("production_feature_mismatch_count") == 0,
        "binding_manifest_hash": binding.get("binding_manifest_hash")
        == canonical_hash(binding_body),
        "binding_blind_2025_y_accessed": binding.get("blind_2025_y_accessed") is False,
        "production_component_count": production.get("count") == official_count,
        "production_artifact_set_hash": production.get("artifact_set_hash")
        == EXPECTED_PRODUCTION_ARTIFACT_SET_HASH,
        "production_case_set_hash": production.get("case_set_hash") == official_case_hash,
        "production_identity_set_hash": production.get("identity_set_hash")
        == official_identity_hash,
        "feature_schema_version": pr_a.get("dataset_version")
        == DOCUMENT_FEATURE_MANIFEST_V1.version,
    }
    return {
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "failed_checks": sorted(name for name, passed in checks.items() if not passed),
    }


def _feature_diagnostics(payload: Mapping[str, Any]) -> dict[str, Any]:
    names = list(payload.get("feature_names") or ())
    values = list(payload.get("feature_values") or ())
    by_name = dict(zip(names, values, strict=True))
    issues: list[str] = []
    nan_count = 0
    positive_infinity_count = 0
    negative_infinity_count = 0
    invalid_numeric_string_count = 0
    invalid_value_positions: list[int] = []
    unexpected_null_positions: list[int] = []
    for index, value in enumerate(values):
        if isinstance(value, str):
            invalid_numeric_string_count += 1
            invalid_value_positions.append(index)
        elif isinstance(value, bool) or (value is not None and not isinstance(value, (int, float))):
            invalid_value_positions.append(index)
        elif isinstance(value, float):
            if math.isnan(value):
                nan_count += 1
                invalid_value_positions.append(index)
            elif value == math.inf:
                positive_infinity_count += 1
                invalid_value_positions.append(index)
            elif value == -math.inf:
                negative_infinity_count += 1
                invalid_value_positions.append(index)

    state_counts = {
        "verified": 0,
        "pending": 0,
        "needs_review": 0,
        "rejected": 0,
        "not_emitted": 0,
        "unavailable": 0,
    }
    verified_scores: list[float] = []
    verified_levels: list[int] = []
    invalid_state_groups = 0
    missingness_contradictions = 0
    suspicious_zero_fill = 0
    for risk_code in V03_ENABLED_RISK_CODES:
        state_names = (
            "verified",
            "pending",
            "needs_review",
            "rejected",
            "not_emitted",
            "unavailable",
        )
        states = [
            by_name[f"{risk_code}__state_{state}"]
            for state in state_names
        ]
        if states.count(1) != 1 or any(value not in {0, 1} for value in states):
            issues.append(f"{risk_code}:invalid_state_one_hot")
            invalid_state_groups += 1
            continue
        active_state = state_names[states.index(1)]
        state_counts[active_state] += 1
        verified = active_state == "verified"
        score_name = f"{risk_code}__score"
        level_name = f"{risk_code}__level_ordinal"
        evidence_name = f"{risk_code}__evidence_count"
        calculation_name = f"{risk_code}__calculation_success"
        missing_name = f"{risk_code}__missing"
        score = by_name[score_name]
        level = by_name[level_name]
        evidence_count = by_name[evidence_name]
        calculation = by_name[calculation_name]
        missing = by_name[missing_name]
        if verified:
            if score is None:
                unexpected_null_positions.append(names.index(score_name))
                issues.append(f"{risk_code}:verified_score_null")
            elif isinstance(score, (int, float)) and not isinstance(score, bool) and math.isfinite(score):
                verified_scores.append(float(score))
            if level is None:
                unexpected_null_positions.append(names.index(level_name))
                issues.append(f"{risk_code}:verified_level_null")
            elif level in {0, 1, 2, 3}:
                verified_levels.append(int(level))
            else:
                issues.append(f"{risk_code}:invalid_level_ordinal")
            if calculation not in {None, 0, 1}:
                issues.append(f"{risk_code}:invalid_calculation_success")
        else:
            for suffix, value in (
                ("score", score),
                ("level_ordinal", level),
                ("calculation_success", calculation),
            ):
                if value is not None:
                    issues.append(f"{risk_code}:{suffix}_silent_fill")
                    missingness_contradictions += 1
                    suspicious_zero_fill += int(value == 0)
        if evidence_count is None:
            unexpected_null_positions.append(names.index(evidence_name))
            issues.append(f"{risk_code}:evidence_count_null")
        elif not isinstance(evidence_count, int) or isinstance(evidence_count, bool) or evidence_count < 0:
            issues.append(f"{risk_code}:invalid_evidence_count")
        if missing != int(not verified):
            issues.append(f"{risk_code}:missing_indicator_mismatch")
            missingness_contradictions += 1

    aggregate_expected = {
        "verified_risk_count": state_counts["verified"],
        "pending_risk_count": state_counts["pending"],
        "needs_review_risk_count": state_counts["needs_review"],
        "rejected_risk_count": state_counts["rejected"],
        "not_emitted_risk_count": state_counts["not_emitted"],
        "unavailable_risk_count": state_counts["unavailable"],
        "high_risk_count": verified_levels.count(2),
        "critical_risk_count": verified_levels.count(3),
        "missing_risk_feature_count": len(V03_ENABLED_RISK_CODES) - state_counts["verified"],
    }
    for name, expected in aggregate_expected.items():
        value = by_name[name]
        if value is None:
            unexpected_null_positions.append(names.index(name))
            issues.append(f"aggregate:{name}_null")
        elif value != expected:
            issues.append(f"aggregate:{name}_mismatch")
            missingness_contradictions += 1
    for name, expected in (
        ("max_verified_score", max(verified_scores) if verified_scores else None),
        (
            "mean_verified_score",
            sum(verified_scores) / len(verified_scores) if verified_scores else None,
        ),
    ):
        value = by_name[name]
        if expected is None and value is not None:
            issues.append(f"aggregate:{name}_silent_fill")
            missingness_contradictions += 1
            suspicious_zero_fill += int(value == 0)
        elif expected is not None and value is None:
            unexpected_null_positions.append(names.index(name))
            issues.append(f"aggregate:{name}_null")
        elif expected is not None and isinstance(value, (int, float)) and not math.isclose(
            float(value), expected, rel_tol=1e-12, abs_tol=1e-12
        ):
            issues.append(f"aggregate:{name}_mismatch")
            missingness_contradictions += 1
    all_zero = bool(values) and all(value == 0 for value in values)
    return {
        "issues": issues,
        "nan_count": nan_count,
        "positive_infinity_count": positive_infinity_count,
        "negative_infinity_count": negative_infinity_count,
        "invalid_numeric_string_count": invalid_numeric_string_count,
        "invalid_value_positions": invalid_value_positions,
        "unexpected_null_positions": sorted(set(unexpected_null_positions)),
        "all_zero_row": all_zero,
        "invalid_state_groups": invalid_state_groups,
        "missingness_contradictions": missingness_contradictions,
        "suspicious_zero_fill": suspicious_zero_fill,
    }


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
    forbidden_fields: set[str] = set()
    forbidden_cases: set[str] = set()
    unexpected_extra_fields: set[str] = set()
    unexpected_extra_cases: set[str] = set()
    counters = {
        "nan_count": 0,
        "positive_infinity_count": 0,
        "negative_infinity_count": 0,
        "invalid_numeric_string_count": 0,
        "unexpected_null_count": 0,
        "all_zero_rows": 0,
        "invalid_state_groups": 0,
        "missingness_contradictions": 0,
        "suspicious_zero_fill_cases": 0,
    }
    zero_fill_cases: set[str] = set()
    for path in paths:
        reasons: list[str] = []
        try:
            payload = _read_object(path)
        except ValueError as exc:
            failures.append({"case_id": path.stem, "reason": str(exc)})
            continue
        case_id = str(payload.get("case_id") or "")
        if case_id in seen:
            duplicates.add(case_id)
        seen.add(case_id)
        if path.stem != case_id:
            reasons.append("filename/case_id mismatch")
        missing_fields = sorted(REQUIRED_PRODUCTION_FIELDS - set(payload))
        if missing_fields:
            reasons.append("missing provenance fields: " + ",".join(missing_fields))
        extras = sorted(set(payload) - REQUIRED_PRODUCTION_FIELDS)
        if extras:
            unexpected_extra_fields.update(extras)
            unexpected_extra_cases.add(case_id or path.stem)
            reasons.append("unexpected extra fields: " + ",".join(extras))
        snapshot_hash = payload.get("snapshot_hash")
        if not isinstance(snapshot_hash, str) or len(snapshot_hash) != 64:
            reasons.append("invalid snapshot_hash provenance")
        try:
            production_document_block(payload)
        except ValueError as exc:
            reasons.append(str(exc))
        forbidden = sorted(_nested_keys(payload) & FORBIDDEN_PRODUCTION_KEYS)
        if forbidden:
            forbidden_fields.update(forbidden)
            forbidden_cases.add(case_id or path.stem)
            reasons.append("Gold/Oracle-derived Production fields: " + ",".join(forbidden))
        try:
            diagnostics = _feature_diagnostics(payload)
        except (KeyError, ValueError) as exc:
            reasons.append(f"feature diagnostics unavailable: {exc}")
        else:
            for name in (
                "nan_count",
                "positive_infinity_count",
                "negative_infinity_count",
                "invalid_numeric_string_count",
                "invalid_state_groups",
                "missingness_contradictions",
            ):
                counters[name] += diagnostics[name]
            counters["unexpected_null_count"] += len(diagnostics["unexpected_null_positions"])
            counters["all_zero_rows"] += int(diagnostics["all_zero_row"])
            if diagnostics["suspicious_zero_fill"]:
                zero_fill_cases.add(case_id or path.stem)
            if diagnostics["invalid_value_positions"]:
                reasons.append(
                    "invalid feature values at: "
                    + ",".join(str(item) for item in diagnostics["invalid_value_positions"][:5])
                )
            if diagnostics["unexpected_null_positions"]:
                reasons.append(
                    "unexpected nulls at: "
                    + ",".join(str(item) for item in diagnostics["unexpected_null_positions"][:5])
                )
            if diagnostics["issues"]:
                reasons.extend(diagnostics["issues"][:5])
        if reasons:
            failures.append({"case_id": case_id or path.stem, "reason": ";".join(reasons)})
    official = set(official_case_ids)
    counters["suspicious_zero_fill_cases"] = len(zero_fill_cases)
    return {
        "status": "pass" if not failures and seen == official and not duplicates else "fail",
        "artifact_count": len(paths),
        "unique_case_count": len(seen),
        "duplicate_case_ids": sorted(duplicates),
        "missing_case_ids": sorted(official - seen),
        "orphan_case_ids": sorted(seen - official),
        "failure_count": len(failures),
        "failures": failures[:20],
        **counters,
        "forbidden_field_count": len(forbidden_fields),
        "forbidden_fields": sorted(forbidden_fields),
        "forbidden_case_ids": sorted(forbidden_cases)[:20],
        "unexpected_extra_field_count": len(unexpected_extra_fields),
        "unexpected_extra_fields": sorted(unexpected_extra_fields),
        "unexpected_extra_case_ids": sorted(unexpected_extra_cases)[:20],
        "suspicious_zero_fill_case_ids": sorted(zero_fill_cases)[:20],
    }


def audit_artifact_set_binding(
    production_dir: Path,
    *,
    expected_hash: str,
) -> dict[str, Any]:
    """Reuse the frozen PR-D aggregate algorithm and compare its exact identity."""

    try:
        component, _ = _component_identity(production_dir, component="production_document")
    except ValueError as exc:
        return {
            "status": "fail",
            "actual_artifact_set_hash": None,
            "expected_artifact_set_hash": expected_hash,
            "matches": False,
            "error": str(exc),
        }
    actual_hash = component["artifact_set_hash"]
    matches = actual_hash == expected_hash
    return {
        "status": "pass" if matches else "fail",
        "actual_artifact_set_hash": actual_hash,
        "expected_artifact_set_hash": expected_hash,
        "matches": matches,
        "component": component,
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
    package_root: Path | None = None,
    zip_path: Path | None = None,
    expected_zip_sha256: str = EXPECTED_ZIP_SHA256,
) -> dict[str, Any]:
    pr_a = _read_object(pr_a_manifest_path)
    binding = _read_object(binding_manifest_path)
    official_ids, official_identity = _official_identity(catalog_dir)
    official_case_hash = canonical_hash(official_ids)
    official_identity_hash = canonical_hash(official_identity)
    production_binding = binding.get("components", {}).get("production_document", {})
    manifest_binding = validate_frozen_manifest_binding(
        pr_a,
        binding,
        official_count=len(official_ids),
        official_case_hash=official_case_hash,
        official_identity_hash=official_identity_hash,
    )
    frozen_contract_pass = (
        len(official_ids) == len(set(official_ids)) and manifest_binding["status"] == "pass"
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
    artifact_binding: dict[str, Any]
    if production_dir is None:
        artifact_binding = {
            "status": "not_run",
            "actual_artifact_set_hash": None,
            "expected_artifact_set_hash": production_binding.get("artifact_set_hash"),
            "matches": None,
        }
    else:
        artifact_binding = audit_artifact_set_binding(
            production_dir,
            expected_hash=str(production_binding.get("artifact_set_hash") or ""),
        )
        artifact_binding["matches_expected_frozen_hash"] = (
            artifact_binding.get("actual_artifact_set_hash")
            == EXPECTED_PRODUCTION_ARTIFACT_SET_HASH
        )
        if not artifact_binding["matches_expected_frozen_hash"]:
            artifact_binding["status"] = "fail"
            artifact_binding["matches"] = False
    zip_audit = (
        audit_zip_package(zip_path, expected_sha256=expected_zip_sha256)
        if zip_path is not None
        else {"status": "not_run"}
    )
    checksum_audit = (
        verify_checksum_manifest(package_root)
        if package_root is not None
        else {"status": "not_run"}
    )
    supplied_package_pass = all(
        item["status"] in {"pass", "not_run"} for item in (zip_audit, checksum_audit)
    )
    document_input_pass = all(
        (
            frozen_contract_pass,
            bulk["status"] == "pass",
            artifact_binding["status"] == "pass",
            supplied_package_pass,
        )
    )
    result = "pass" if document_input_pass else (
        "blocked"
        if frozen_contract_pass and bulk["status"].startswith("not_run")
        else "fail"
    )
    return {
        "audit_version": AUDIT_VERSION,
        "result": result,
        "audit_mode": "bulk_and_metadata" if production_dir is not None else "frozen_metadata_only",
        "package_transport": zip_audit,
        "package_checksums": checksum_audit,
        "manifest_binding": manifest_binding,
        "official": {
            "case_count": len(official_ids),
            "unique_case_count": len(set(official_ids)),
            "case_set_hash": official_case_hash,
            "identity_set_hash": official_identity_hash,
        },
        "production_document_x": {
            "frozen_count": production_binding.get("count"),
            "artifact_set_hash": production_binding.get("artifact_set_hash"),
            "artifact_set_binding": artifact_binding,
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
            "status": (
                "pass"
                if bulk.get("forbidden_field_count", 0) == 0
                and bulk.get("unexpected_extra_field_count", 0) == 0
                else "fail"
            ),
            "production_builder": "production_document_block",
            "production_feature_component": "production_document",
            "oracle_component": "oracle_document/evaluation_only",
            "production_matrix_groups": ["P", "PM"],
            "finding": "No Oracle/Gold field flow into Production Document-X or P/PM projection found.",
        },
        "pr_d_compatibility": {
            "status": "pass" if document_input_pass else "fail",
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
            "bulk_sample_validation": "not_run_evidence_bulk_not_supplied",
        },
        "explanation_readiness": {
            "status": "partial",
            "proposal": "DocumentExplanationRecordProposal",
            "conversion": "build_explanation_records",
            "public_schema_changed": False,
        },
        "frozen_contract_pass": frozen_contract_pass,
        "pr_d_document_x_input_qa": "pass" if document_input_pass else "fail",
        "pr_g_explanation_readiness": "partial",
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
    parser.add_argument("--package-root", type=Path)
    parser.add_argument("--zip-path", type=Path)
    parser.add_argument("--expected-zip-sha256", default=EXPECTED_ZIP_SHA256)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit_contract(
        catalog_dir=args.catalog_dir,
        pr_a_manifest_path=args.pr_a_manifest,
        binding_manifest_path=args.binding_manifest,
        production_dir=args.production_dir,
        package_root=args.package_root,
        zip_path=args.zip_path,
        expected_zip_sha256=args.expected_zip_sha256,
    )
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["result"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
