"""Role-A final competition readiness, audit, indexing, and packaging helpers.

This module is deliberately read-only with respect to B/C/D/E outputs. It never
fills a missing metric, market fact, model score, Evidence item, or LLM result.
Instead it converts the final hand-offs into an auditable PASS/FAIL decision and
produces the A-owned CH-6 evidence needed for submission.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Iterable
from uuid import NAMESPACE_URL, uuid5
import zipfile


READINESS_SCHEMA_VERSION = "v045_submission_readiness_v1"
ARTIFACT_INDEX_SCHEMA_VERSION = "v045_submission_artifact_index_v1"
BLIND_AUDIT_SCHEMA_VERSION = "v045_blind_audit_v1"
PROVENANCE_AUDIT_SCHEMA_VERSION = "v045_provenance_audit_v1"
DETERMINISM_AUDIT_SCHEMA_VERSION = "v045_determinism_audit_v1"
PACKAGE_SCHEMA_VERSION = "v045_submission_package_v1"

ROLE_B_REQUIRED = (
    "document_benchmark_summary.json",
    "risk_benchmark.csv",
    "evidence_benchmark.csv",
)
ROLE_D_REQUIRED = (
    "test_predictions.csv",
    "multi_horizon_results.csv",
    "evaluation_summary.json",
)
ROLE_E_CASE_REQUIRED = (
    "analysis_result.json",
    "final_supervision.json",
    "conflicts.json",
    "rechecks.json",
    "trace_sidecar.json",
    "traceability.json",
    "prospectus_verification.json",
    "agent_reasoning_log.json",
    "agent_reasoning_log.md",
    "case_report.md",
    "gate_e1_evidence.json",
)
REQUIRED_HORIZONS = ("return_1d", "return_5d", "return_20d", "return_60d")
REQUIRED_CALL_TRACE_FIELDS = (
    "provider_name",
    "model_name",
    "prompt_version",
    "request_id",
    "raw_response_hash",
    "latency_ms",
)

# Package source allowlist: repository code/config/docs only. Licensed PDFs and
# local competition data are intentionally not reachable from this list.
SOURCE_ROOT_FILES = (
    "README.md",
    "CHANGELOG.md",
    "AGENTS.md",
    "pyproject.toml",
    "environment.yml",
    ".env.example",
)
SOURCE_ROOT_DIRS = ("src", "app", "configs", "scripts")
SUBMISSION_DOCS = (
    "docs/SUBMISSION_RUNBOOK.md",
    "docs/V0.4_RELEASE_ACCEPTANCE.md",
    "docs/COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md",
    "docs/V04_FIVE_PERSON_EXECUTION_PLAN.md",
)

_FORBIDDEN_PACKAGE_SUFFIXES = {".pdf", ".pem", ".key", ".p12", ".pfx"}
_FORBIDDEN_PACKAGE_NAMES = {".env", "id_rsa", "id_ed25519"}
_PRIVATE_KEY_RE = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
_TOKEN_RE = re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")
_WINDOWS_ABS_RE = re.compile(r"\b[A-Za-z]:\\(?:Users|Documents and Settings|home|mnt)\\", re.I)
_UNIX_LOCAL_ABS_RE = re.compile(r"(?<![A-Za-z0-9_])/(?:Users|home|mnt|private|var/folders)/[^\s\"']+")


@dataclass(frozen=True)
class GateResult:
    name: str
    owner: str
    passed: bool
    details: dict[str, Any]
    blockers: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "owner": self.owner,
            "passed": self.passed,
            "blockers": list(self.blockers),
            "details": self.details,
        }


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _sha(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _csv_header_and_rows(path: Path) -> tuple[list[str], int]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return list(reader.fieldnames or []), len(rows)


def _bool_is_false(payload: dict[str, Any], *keys: str) -> bool:
    for key in keys:
        if key in payload:
            return payload[key] is False
    return False


def _traceability_value(case: dict[str, Any]) -> float | None:
    value = case.get("traceability")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, dict):
        for key in ("overall_traceability", "traceability", "ratio", "value"):
            candidate = value.get(key)
            if isinstance(candidate, (int, float)) and not isinstance(candidate, bool):
                return float(candidate)
    return None


def _result_status(value: Any) -> str:
    return str(value or "").strip().casefold()


def audit_role_b(role_b_dir: Path) -> GateResult:
    missing = [name for name in ROLE_B_REQUIRED if not (role_b_dir / name).is_file()]
    if missing:
        return GateResult(
            "B1_real_llm_document_benchmark",
            "B",
            False,
            {"artifact_dir": _record_path(role_b_dir), "missing_files": missing},
            tuple(f"missing Role-B artifact: {name}" for name in missing),
        )

    summary = _read_json(role_b_dir / "document_benchmark_summary.json")
    risk_header, risk_rows = _csv_header_and_rows(role_b_dir / "risk_benchmark.csv")
    evidence_header, evidence_rows = _csv_header_and_rows(role_b_dir / "evidence_benchmark.csv")
    risk_target = summary.get("risk_target_at_least_80_percent") is True
    evidence_target = summary.get("evidence_target_at_least_85_percent") is True
    real_llm_cases = int(summary.get("real_llm_cases") or 0)
    external_called = summary.get("external_llm_called") is True
    blind_safe = summary.get("blind_2025_outcome_accessed") is False
    passed = all(
        (
            real_llm_cases > 0,
            external_called,
            risk_target,
            evidence_target,
            blind_safe,
            risk_rows > 0,
            evidence_rows > 0,
        )
    )
    blockers: list[str] = []
    if real_llm_cases <= 0 or not external_called:
        blockers.append("fixed Development benchmark has no real external LLM case")
    if not risk_target:
        blockers.append("Risk extraction >=80% is not demonstrated by the governed evaluator")
    if not evidence_target:
        blockers.append("Key Evidence Recall >=85% is not demonstrated by the governed evaluator")
    if not blind_safe:
        blockers.append("Role-B benchmark does not explicitly attest 2025 Blind protection")
    if risk_rows == 0 or evidence_rows == 0:
        blockers.append("Role-B benchmark CSVs are empty")
    return GateResult(
        "B1_real_llm_document_benchmark",
        "B",
        passed,
        {
            "artifact_dir": _record_path(role_b_dir),
            "benchmark_version": summary.get("benchmark_version"),
            "result": summary.get("result"),
            "real_llm_cases": real_llm_cases,
            "external_llm_called": external_called,
            "risk_target_at_least_80_percent": risk_target,
            "evidence_target_at_least_85_percent": evidence_target,
            "risk_rows": risk_rows,
            "risk_columns": risk_header,
            "evidence_rows": evidence_rows,
            "evidence_columns": evidence_header,
            "blind_2025_outcome_accessed": summary.get("blind_2025_outcome_accessed"),
        },
        tuple(blockers),
    )


def audit_role_d(role_d_dir: Path) -> GateResult:
    missing = [name for name in ROLE_D_REQUIRED if not (role_d_dir / name).is_file()]
    if missing:
        return GateResult(
            "D1_multi_horizon_evaluation",
            "D",
            False,
            {"artifact_dir": _record_path(role_d_dir), "missing_files": missing},
            tuple(f"missing Role-D artifact: {name}" for name in missing),
        )

    pred_header, pred_rows = _csv_header_and_rows(role_d_dir / "test_predictions.csv")
    horizon_header, horizon_rows = _csv_header_and_rows(role_d_dir / "multi_horizon_results.csv")
    summary = _read_json(role_d_dir / "evaluation_summary.json")
    missing_horizons = [name for name in REQUIRED_HORIZONS if name not in horizon_header]
    blind_explicit = _bool_is_false(
        summary,
        "blind_2025_y_accessed",
        "blind_2025_outcome_accessed",
        "blind_2025_accessed",
    )
    passed = not missing_horizons and pred_rows > 0 and horizon_rows > 0 and blind_explicit
    blockers: list[str] = []
    if missing_horizons:
        blockers.append("multi_horizon_results.csv missing: " + ", ".join(missing_horizons))
    if pred_rows <= 0:
        blockers.append("test_predictions.csv has no rows")
    if horizon_rows <= 0:
        blockers.append("multi_horizon_results.csv has no rows")
    if not blind_explicit:
        blockers.append("evaluation_summary.json lacks an explicit false 2025 Blind access flag")
    return GateResult(
        "D1_multi_horizon_evaluation",
        "D",
        passed,
        {
            "artifact_dir": _record_path(role_d_dir),
            "prediction_rows": pred_rows,
            "prediction_columns": pred_header,
            "multi_horizon_rows": horizon_rows,
            "multi_horizon_columns": horizon_header,
            "missing_required_horizons": missing_horizons,
            "blind_2025_explicitly_protected": blind_explicit,
            "evaluation_summary_keys": sorted(summary),
        },
        tuple(blockers),
    )


def _case_dir(role_e_dir: Path, case: dict[str, Any]) -> Path:
    return role_e_dir / str(case.get("case_id") or "")


def audit_market_from_final_matrix(role_e_dir: Path, summary: dict[str, Any] | None = None) -> GateResult:
    if summary is None:
        summary_path = role_e_dir / "summary.json"
        if not summary_path.is_file():
            return GateResult(
                "C1_final_matrix_market_validation",
                "C",
                False,
                {"artifact_dir": _record_path(role_e_dir)},
                ("Role-E final matrix summary is missing",),
            )
        summary = _read_json(summary_path)

    cases = [case for case in summary.get("cases", []) if isinstance(case, dict)]
    checked: list[dict[str, Any]] = []
    blockers: list[str] = []
    for case in cases:
        case_id = str(case.get("case_id") or "")
        market_state = (case.get("channel_states") or {}).get("market")
        trace_path = _case_dir(role_e_dir, case) / "trace_sidecar.json"
        market_trace_accounted = False
        market_event_count = 0
        if trace_path.is_file():
            sidecar = _read_json(trace_path)
            events = sidecar.get("trace_events", []) or []
            market_events = [
                event
                for event in events
                if isinstance(event, dict)
                and (
                    str(event.get("event_type") or "").casefold() == "market"
                    or "market" in str(event.get("agent_name") or "").casefold()
                    or "market" in str(event.get("tool_or_skill") or "").casefold()
                )
            ]
            market_event_count = len(market_events)
            if market_events:
                market_trace_accounted = all(
                    bool(
                        event.get("evidence_ids")
                        or event.get("calculation_ids")
                        or (event.get("details") or {}).get("no_evidence_reason")
                    )
                    for event in market_events
                )
        explicit_state = bool(market_state)
        case_passed = explicit_state and market_event_count > 0 and market_trace_accounted
        if not case_passed:
            blockers.append(f"{case_id}: market state/trace is not fully accounted")
        checked.append(
            {
                "case_id": case_id,
                "market_channel_state": market_state,
                "market_event_count": market_event_count,
                "market_trace_accounted": market_trace_accounted,
                "passed": case_passed,
            }
        )
    passed = len(checked) >= 3 and all(item["passed"] for item in checked)
    if len(checked) < 3:
        blockers.append("fewer than 3 final cases were available for Market validation")
    return GateResult(
        "C1_final_matrix_market_validation",
        "C",
        passed,
        {"artifact_dir": _record_path(role_e_dir), "cases": checked},
        tuple(blockers),
    )


def audit_role_e(role_e_dir: Path) -> GateResult:
    summary_path = role_e_dir / "summary.json"
    if not summary_path.is_file():
        return GateResult(
            "E1_real_provider_final_supervisor",
            "E",
            False,
            {"artifact_dir": _record_path(role_e_dir)},
            ("Role-E final matrix summary.json is missing",),
        )
    summary = _read_json(summary_path)
    cases = [case for case in summary.get("cases", []) if isinstance(case, dict)]
    declared = int(summary.get("declared_case_count") or len(cases))
    executed = int(summary.get("executed_case_count") or 0)
    gate = summary.get("gate_e1") or {}
    gate_satisfied = gate.get("satisfied") is True
    all_integrity = summary.get("all_prospectus_sha256_verified") is True
    blind_safe = summary.get("blind_2025_y_accessed") is False
    outcome_safe = summary.get("outcome_labels_accessed") is False

    case_checks: list[dict[str, Any]] = []
    blockers: list[str] = []
    for case in cases:
        case_id = str(case.get("case_id") or "")
        root = _case_dir(role_e_dir, case)
        missing_files = [name for name in ROLE_E_CASE_REQUIRED if not (root / name).is_file()]
        traceability = _traceability_value(case)
        case_gate = case.get("gate_e1") or {}
        case_gate_satisfied = case_gate.get("satisfied") is True
        passed = not missing_files and traceability == 1.0 and case_gate_satisfied
        if missing_files:
            blockers.append(f"{case_id}: missing submission artifacts: {', '.join(missing_files)}")
        if traceability != 1.0:
            blockers.append(f"{case_id}: measured traceability is not 1.0")
        if not case_gate_satisfied:
            blockers.append(f"{case_id}: real-provider Final Supervisor Gate E1 is not satisfied")
        case_checks.append(
            {
                "case_id": case_id,
                "status": case.get("status"),
                "traceability": traceability,
                "gate_e1_satisfied": case_gate_satisfied,
                "missing_files": missing_files,
                "passed": passed,
            }
        )

    if declared < 3 or executed < 3:
        blockers.append("final matrix has fewer than three executed declared cases")
    if not all_integrity:
        blockers.append("not every executed prospectus passed frozen SHA-256 integrity")
    if not gate_satisfied:
        blockers.append("matrix-level Gate E1 is not satisfied")
    if not blind_safe or not outcome_safe:
        blockers.append("Role-E final matrix does not attest pre-listing/Blind isolation")
    passed = all(
        (
            declared >= 3,
            executed >= 3,
            all_integrity,
            gate_satisfied,
            blind_safe,
            outcome_safe,
            len(case_checks) >= 3,
            all(item["passed"] for item in case_checks),
        )
    )
    return GateResult(
        "E1_real_provider_final_supervisor",
        "E",
        passed,
        {
            "artifact_dir": _record_path(role_e_dir),
            "declared_case_count": declared,
            "executed_case_count": executed,
            "all_prospectus_sha256_verified": all_integrity,
            "matrix_gate_e1_satisfied": gate_satisfied,
            "blind_2025_y_accessed": summary.get("blind_2025_y_accessed"),
            "outcome_labels_accessed": summary.get("outcome_labels_accessed"),
            "cases": case_checks,
        },
        tuple(blockers),
    )


def build_blind_audit(role_b_dir: Path, role_d_dir: Path, role_e_dir: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    b_path = role_b_dir / "document_benchmark_summary.json"
    if b_path.is_file():
        payload = _read_json(b_path)
        checks.append(
            {
                "source": _record_path(b_path),
                "assertion": "blind_2025_outcome_accessed is false",
                "passed": payload.get("blind_2025_outcome_accessed") is False,
                "value": payload.get("blind_2025_outcome_accessed"),
            }
        )
    else:
        checks.append({"source": _record_path(b_path), "assertion": "Role-B blind attestation exists", "passed": False})

    d_path = role_d_dir / "evaluation_summary.json"
    if d_path.is_file():
        payload = _read_json(d_path)
        value = next(
            (
                payload[key]
                for key in ("blind_2025_y_accessed", "blind_2025_outcome_accessed", "blind_2025_accessed")
                if key in payload
            ),
            None,
        )
        checks.append(
            {
                "source": _record_path(d_path),
                "assertion": "Role-D explicitly records no 2025 Blind y access",
                "passed": value is False,
                "value": value,
            }
        )
    else:
        checks.append({"source": _record_path(d_path), "assertion": "Role-D blind attestation exists", "passed": False})

    e_path = role_e_dir / "summary.json"
    if e_path.is_file():
        payload = _read_json(e_path)
        checks.extend(
            [
                {
                    "source": _record_path(e_path),
                    "assertion": "blind_2025_y_accessed is false",
                    "passed": payload.get("blind_2025_y_accessed") is False,
                    "value": payload.get("blind_2025_y_accessed"),
                },
                {
                    "source": _record_path(e_path),
                    "assertion": "Role-E demo did not open outcome labels",
                    "passed": payload.get("outcome_labels_accessed") is False,
                    "value": payload.get("outcome_labels_accessed"),
                },
            ]
        )
    else:
        checks.append({"source": _record_path(e_path), "assertion": "Role-E blind attestation exists", "passed": False})

    passed = bool(checks) and all(check.get("passed") is True for check in checks)
    return {
        "schema_version": BLIND_AUDIT_SCHEMA_VERSION,
        "passed": passed,
        "checks": checks,
        "statement": (
            "All governed final artifacts explicitly preserve the 2025 Blind boundary."
            if passed
            else "Blind audit is incomplete or contains a failing attestation; submission must remain blocked."
        ),
    }


def build_provenance_audit(role_e_dir: Path) -> dict[str, Any]:
    summary_path = role_e_dir / "summary.json"
    if not summary_path.is_file():
        return {
            "schema_version": PROVENANCE_AUDIT_SCHEMA_VERSION,
            "passed": False,
            "cases": [],
            "blockers": ["Role-E final summary is missing"],
        }
    summary = _read_json(summary_path)
    cases: list[dict[str, Any]] = []
    blockers: list[str] = []
    for case in [item for item in summary.get("cases", []) if isinstance(item, dict)]:
        case_id = str(case.get("case_id") or "")
        root = _case_dir(role_e_dir, case)
        verification_path = root / "prospectus_verification.json"
        sidecar_path = root / "trace_sidecar.json"
        gate_path = root / "gate_e1_evidence.json"
        verification = _read_json(verification_path) if verification_path.is_file() else {}
        sidecar = _read_json(sidecar_path) if sidecar_path.is_file() else {}
        gate = _read_json(gate_path) if gate_path.is_file() else {}
        identity = sidecar.get("identity") or {}
        provenance = identity.get("provenance") or {}
        call = (gate.get("call") or gate.get("provider_call") or {})
        if not call:
            # Gate-E evidence nests the exact call in different revisions; fall
            # back to final supervision evidence if present.
            final_path = root / "final_supervision.json"
            if final_path.is_file():
                final = _read_json(final_path)
                call = ((final.get("llm_synthesis") or {}).get("call") or {})
        accepted = gate.get("satisfied") is True
        call_complete = all(call.get(field) is not None for field in REQUIRED_CALL_TRACE_FIELDS) if accepted else True
        case_passed = all(
            (
                verification.get("sha256_matches_frozen_catalog") is True,
                verification.get("size_matches_frozen_catalog") is True,
                verification.get("page_count_matches_frozen_catalog") is True,
                verification.get("path_recorded") is False,
                bool(identity.get("run_id")),
                bool(provenance.get("workflow")),
                bool(provenance.get("trace_schema_version")),
                bool(provenance.get("conflict_policy_version")),
                bool(provenance.get("recheck_policy_version")),
                call_complete,
            )
        )
        if not case_passed:
            blockers.append(f"{case_id}: incomplete prospectus/runtime/provider provenance")
        cases.append(
            {
                "case_id": case_id,
                "passed": case_passed,
                "prospectus_sha256": verification.get("sha256"),
                "sha256_matches_frozen_catalog": verification.get("sha256_matches_frozen_catalog"),
                "size_matches_frozen_catalog": verification.get("size_matches_frozen_catalog"),
                "page_count_matches_frozen_catalog": verification.get("page_count_matches_frozen_catalog"),
                "path_recorded": verification.get("path_recorded"),
                "run_id": identity.get("run_id"),
                "workflow": provenance.get("workflow"),
                "trace_schema_version": provenance.get("trace_schema_version"),
                "conflict_policy_version": provenance.get("conflict_policy_version"),
                "recheck_policy_version": provenance.get("recheck_policy_version"),
                "gate_e1_satisfied": accepted,
                "provider_call_trace_complete_if_accepted": call_complete,
            }
        )
    passed = len(cases) >= 3 and all(case["passed"] for case in cases)
    if len(cases) < 3:
        blockers.append("fewer than three final cases were available for provenance audit")
    return {
        "schema_version": PROVENANCE_AUDIT_SCHEMA_VERSION,
        "passed": passed,
        "cases": cases,
        "blockers": blockers,
    }


def _expected_request_id(case: dict[str, Any]) -> str | None:
    verification = case.get("prospectus_verification") or {}
    digest = verification.get("sha256")
    stock_code = case.get("stock_code")
    listing_date = case.get("listing_date")
    if not all((digest, stock_code, listing_date)):
        return None
    return str(uuid5(NAMESPACE_URL, f"v04-real-e2e:{stock_code}:{listing_date}:{digest}"))


def build_determinism_audit(role_e_dir: Path, baseline_role_e_dir: Path | None = None) -> dict[str, Any]:
    summary_path = role_e_dir / "summary.json"
    if not summary_path.is_file():
        return {
            "schema_version": DETERMINISM_AUDIT_SCHEMA_VERSION,
            "passed": False,
            "cases": [],
            "pairwise_repeatability": "NOT_EVALUATED",
            "blockers": ["Role-E final summary is missing"],
        }
    summary = _read_json(summary_path)
    current_cases = {
        str(case.get("case_id")): case
        for case in summary.get("cases", [])
        if isinstance(case, dict) and case.get("case_id")
    }
    cases: list[dict[str, Any]] = []
    blockers: list[str] = []
    for case_id, case in current_cases.items():
        expected = _expected_request_id(case)
        actual = case.get("deterministic_request_id")
        identity_pass = bool(expected) and actual == expected
        if not identity_pass:
            blockers.append(f"{case_id}: deterministic request identity does not reproduce from governed inputs")
        cases.append(
            {
                "case_id": case_id,
                "expected_request_id": expected,
                "actual_request_id": actual,
                "identity_reproducible": identity_pass,
                "prospectus_sha256": (case.get("prospectus_verification") or {}).get("sha256"),
                "final_supervision_content_hash": case.get("final_supervision_content_hash"),
            }
        )

    pairwise = "NOT_EVALUATED"
    pairwise_checks: list[dict[str, Any]] = []
    if baseline_role_e_dir is not None:
        baseline_path = baseline_role_e_dir / "summary.json"
        if not baseline_path.is_file():
            blockers.append("baseline Role-E summary requested for pairwise determinism but missing")
            pairwise = "FAIL"
        else:
            baseline = _read_json(baseline_path)
            baseline_cases = {
                str(case.get("case_id")): case
                for case in baseline.get("cases", [])
                if isinstance(case, dict) and case.get("case_id")
            }
            pairwise = "PASS"
            for case_id, current in current_cases.items():
                prior = baseline_cases.get(case_id)
                same = bool(prior) and all(
                    (
                        current.get("deterministic_request_id") == prior.get("deterministic_request_id"),
                        (current.get("prospectus_verification") or {}).get("sha256")
                        == (prior.get("prospectus_verification") or {}).get("sha256"),
                        current.get("parsed_chunk_count") == prior.get("parsed_chunk_count"),
                    )
                )
                pairwise_checks.append({"case_id": case_id, "deterministic_facets_match": same})
                if not same:
                    pairwise = "FAIL"
                    blockers.append(f"{case_id}: deterministic facets differ from the supplied baseline run")

    # Remote LLM prose is not promised byte-for-byte deterministic. The audit
    # proves deterministic identities/facets and preserves provider response
    # hashes instead of making a false reproducibility claim.
    passed = len(cases) >= 3 and all(case["identity_reproducible"] for case in cases) and pairwise != "FAIL"
    if len(cases) < 3:
        blockers.append("fewer than three final cases were available for determinism audit")
    return {
        "schema_version": DETERMINISM_AUDIT_SCHEMA_VERSION,
        "passed": passed,
        "definition": (
            "Deterministic request identity and governed deterministic facets must reproduce; "
            "remote LLM text is audited by provider/model/prompt/request/response hash, not by byte-for-byte replay."
        ),
        "cases": cases,
        "pairwise_repeatability": pairwise,
        "pairwise_checks": pairwise_checks,
        "blockers": blockers,
    }


def _artifact_record(path: Path, *, logical_path: str, owner: str, required: bool) -> dict[str, Any]:
    return {
        "logical_path": logical_path,
        "owner": owner,
        "required": required,
        "size_bytes": path.stat().st_size,
        "sha256": _sha(path),
    }


def build_artifact_index(
    *,
    role_b_dir: Path,
    role_d_dir: Path,
    role_e_dir: Path,
    a_output_dir: Path,
    runbook_path: Path,
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []

    def add(path: Path, logical: str, owner: str, required: bool = True) -> None:
        if path.is_file():
            records.append(_artifact_record(path, logical_path=logical, owner=owner, required=required))

    for name in ROLE_B_REQUIRED:
        add(role_b_dir / name, f"role_b/{name}", "B")
    for candidate in (role_b_dir / "ai_vs_offline_report.json", role_d_dir / "ai_vs_offline_report.json"):
        if candidate.is_file():
            add(candidate, "evaluation/ai_vs_offline_report.json", "B/D")
            break
    for name in ROLE_D_REQUIRED:
        add(role_d_dir / name, f"role_d/{name}", "D")
    summary_path = role_e_dir / "summary.json"
    add(summary_path, "role_e/summary.json", "E")
    if summary_path.is_file():
        summary = _read_json(summary_path)
        for case in [item for item in summary.get("cases", []) if isinstance(item, dict)]:
            case_id = str(case.get("case_id") or "")
            for name in ROLE_E_CASE_REQUIRED:
                add(_case_dir(role_e_dir, case) / name, f"role_e/{case_id}/{name}", "E")
    for name in (
        "submission_readiness.json",
        "blind_audit.json",
        "provenance_audit.json",
        "determinism_audit.json",
    ):
        add(a_output_dir / name, f"role_a/{name}", "A")
    add(runbook_path, "docs/SUBMISSION_RUNBOOK.md", "A")
    records.sort(key=lambda item: item["logical_path"])
    return {
        "schema_version": ARTIFACT_INDEX_SCHEMA_VERSION,
        "artifact_count": len(records),
        "artifacts": records,
    }


def _record_path(path: Path) -> str:
    """Render a path for an audit record without embedding a local absolute path.

    These audits are themselves packaged and shipped, and the packager refuses
    any artifact carrying a local absolute path -- so the audits must not create
    one, or the tooling refuses its own output.  A path inside the working tree
    is recorded relative to it; anything outside is reduced to its own name,
    which keeps the record readable without pinning it to the machine that
    produced it.  Relative inputs, which is what the CLI defaults pass, are kept
    verbatim.
    """

    if not path.is_absolute():
        return path.as_posix()
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return f"<external>/{path.name}"


def _scan_path_for_sensitive_material(path: Path) -> list[str]:
    issues: list[str] = []
    if path.name in _FORBIDDEN_PACKAGE_NAMES:
        issues.append(f"forbidden secret-bearing filename: {path.name}")
    if path.suffix.casefold() in _FORBIDDEN_PACKAGE_SUFFIXES:
        issues.append(f"forbidden licensed/secret file type: {path.suffix}")
    if path.stat().st_size > 5 * 1024 * 1024:
        return issues
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return issues
    if _PRIVATE_KEY_RE.search(text):
        issues.append("private-key material detected")
    if _TOKEN_RE.search(text):
        issues.append("token-like secret detected")
    if _WINDOWS_ABS_RE.search(text) or _UNIX_LOCAL_ABS_RE.search(text):
        issues.append("local absolute path detected")
    return issues


def _find_ai_vs_offline(role_b_dir: Path, role_d_dir: Path) -> Path | None:
    for candidate in (role_b_dir / "ai_vs_offline_report.json", role_d_dir / "ai_vs_offline_report.json"):
        if candidate.is_file():
            return candidate
    return None


def build_submission_readiness(
    *,
    repo_root: Path,
    role_b_dir: Path,
    role_d_dir: Path,
    role_e_dir: Path,
    a_output_dir: Path,
    baseline_role_e_dir: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    b = audit_role_b(role_b_dir)
    d = audit_role_d(role_d_dir)
    e = audit_role_e(role_e_dir)
    c = audit_market_from_final_matrix(role_e_dir)
    blind = build_blind_audit(role_b_dir, role_d_dir, role_e_dir)
    provenance = build_provenance_audit(role_e_dir)
    determinism = build_determinism_audit(role_e_dir, baseline_role_e_dir)
    ai_vs_offline = _find_ai_vs_offline(role_b_dir, role_d_dir)
    runbook = repo_root / "docs/SUBMISSION_RUNBOOK.md"

    a_blockers: list[str] = []
    if not blind["passed"]:
        a_blockers.append("blind audit is not PASS")
    if not provenance["passed"]:
        a_blockers.append("provenance audit is not PASS")
    if not determinism["passed"]:
        a_blockers.append("determinism audit is not PASS")
    if not runbook.is_file():
        a_blockers.append("docs/SUBMISSION_RUNBOOK.md is missing")
    if ai_vs_offline is None:
        a_blockers.append("ai_vs_offline_report.json is missing from B/D handoff")
    a = GateResult(
        "A1_final_integration_submission_freeze",
        "A",
        not a_blockers,
        {
            "blind_audit_passed": blind["passed"],
            "provenance_audit_passed": provenance["passed"],
            "determinism_audit_passed": determinism["passed"],
            "runbook_present": runbook.is_file(),
            "ai_vs_offline_report": _record_path(ai_vs_offline) if ai_vs_offline else None,
            "latest_main_ci": "EXTERNAL_CHECK_REQUIRED_AT_FREEZE",
        },
        tuple(a_blockers),
    )

    gates = [b, c, d, e, a]
    blockers = [blocker for gate in gates for blocker in gate.blockers]
    ready = all(gate.passed for gate in gates)
    readiness = {
        "schema_version": READINESS_SCHEMA_VERSION,
        "competition_ready": ready,
        "verdict": "COMPETITION_READY" if ready else "NOT_YET_COMPETITION_READY",
        "gates": [gate.as_dict() for gate in gates],
        "blockers": blockers,
        "rules": {
            "no_missing_gate_may_be_inferred_as_pass": True,
            "model_channel_may_be_explicitly_unavailable": True,
            "2025_blind_y_must_remain_unaccessed": True,
            "remote_llm_text_byte_determinism_claimed": False,
            "packaging_allowed_only_when_competition_ready": True,
        },
    }
    return readiness, blind, provenance, determinism


def write_submission_audits(
    *,
    output_dir: Path,
    readiness: dict[str, Any],
    blind: dict[str, Any],
    provenance: dict[str, Any],
    determinism: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in (
        ("submission_readiness.json", readiness),
        ("blind_audit.json", blind),
        ("provenance_audit.json", provenance),
        ("determinism_audit.json", determinism),
    ):
        (output_dir / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def write_artifact_index(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _iter_source_files(repo_root: Path) -> Iterable[tuple[Path, str]]:
    for name in SOURCE_ROOT_FILES:
        path = repo_root / name
        if path.is_file():
            yield path, f"source/{name}"
    for dirname in SOURCE_ROOT_DIRS:
        root = repo_root / dirname
        if not root.is_dir():
            continue
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
                continue
            relative = path.relative_to(repo_root).as_posix()
            yield path, f"source/{relative}"
    for name in SUBMISSION_DOCS:
        path = repo_root / name
        if path.is_file():
            yield path, f"source/{name}"


def _iter_submission_artifacts(
    *,
    role_b_dir: Path,
    role_d_dir: Path,
    role_e_dir: Path,
    a_output_dir: Path,
) -> Iterable[tuple[Path, str]]:
    for name in ROLE_B_REQUIRED:
        path = role_b_dir / name
        if path.is_file():
            yield path, f"artifacts/role_b/{name}"
    ai = _find_ai_vs_offline(role_b_dir, role_d_dir)
    if ai is not None:
        yield ai, "artifacts/evaluation/ai_vs_offline_report.json"
    for name in ROLE_D_REQUIRED:
        path = role_d_dir / name
        if path.is_file():
            yield path, f"artifacts/role_d/{name}"
    summary_path = role_e_dir / "summary.json"
    if summary_path.is_file():
        yield summary_path, "artifacts/role_e/summary.json"
        summary = _read_json(summary_path)
        for case in [item for item in summary.get("cases", []) if isinstance(item, dict)]:
            case_id = str(case.get("case_id") or "")
            for name in ROLE_E_CASE_REQUIRED:
                path = _case_dir(role_e_dir, case) / name
                if path.is_file():
                    yield path, f"artifacts/role_e/{case_id}/{name}"
    for name in (
        "submission_readiness.json",
        "blind_audit.json",
        "provenance_audit.json",
        "determinism_audit.json",
        "artifact_index.json",
    ):
        path = a_output_dir / name
        if path.is_file():
            yield path, f"artifacts/role_a/{name}"


def package_submission_bundle(
    *,
    repo_root: Path,
    role_b_dir: Path,
    role_d_dir: Path,
    role_e_dir: Path,
    a_output_dir: Path,
    output_zip: Path,
) -> dict[str, Any]:
    readiness_path = a_output_dir / "submission_readiness.json"
    if not readiness_path.is_file():
        raise RuntimeError("submission_readiness.json is missing; run the readiness audit first")
    readiness = _read_json(readiness_path)
    if readiness.get("competition_ready") is not True:
        raise RuntimeError("submission package refused: COMPETITION_READY is not true")

    selected: dict[str, Path] = {}
    for path, logical in _iter_source_files(repo_root):
        selected[logical] = path
    for path, logical in _iter_submission_artifacts(
        role_b_dir=role_b_dir,
        role_d_dir=role_d_dir,
        role_e_dir=role_e_dir,
        a_output_dir=a_output_dir,
    ):
        selected[logical] = path

    security_issues: list[dict[str, Any]] = []
    manifest_files: list[dict[str, Any]] = []
    for logical, path in sorted(selected.items()):
        issues = _scan_path_for_sensitive_material(path)
        if issues:
            security_issues.append({"logical_path": logical, "issues": issues})
        manifest_files.append(
            {
                "logical_path": logical,
                "size_bytes": path.stat().st_size,
                "sha256": _sha(path),
            }
        )
    if security_issues:
        raise RuntimeError(
            "submission package refused by secret/licensed/local-path audit: "
            + json.dumps(security_issues, ensure_ascii=False)
        )

    manifest = {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "competition_ready": True,
        "file_count": len(manifest_files),
        "files": manifest_files,
        "security": {
            "licensed_pdf_included": False,
            "secret_file_included": False,
            "local_absolute_path_detected": False,
        },
    }
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for logical, path in sorted(selected.items()):
            info = zipfile.ZipInfo(logical)
            info.date_time = (2026, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
        info = zipfile.ZipInfo("submission_manifest.json")
        info.date_time = (2026, 1, 1, 0, 0, 0)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        archive.writestr(
            info,
            (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )
    return {
        **manifest,
        "bundle_path": str(output_zip),
        "bundle_size_bytes": output_zip.stat().st_size,
        "bundle_sha256": _sha(output_zip),
    }
