"""Phase-2 deterministic correction and triage for expert annotations.

Phase 2 consumes the Phase-1 audit, writes deterministic corrections only under
Case ``audit/`` directories, and splits unresolved policy/input work into review
queues. Source ``pass1/expert_annotation_v1.json`` files are immutable.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .annotation_audit import (
    STATUS_HARD,
    STATUS_INSUFFICIENT,
    STATUS_POLICY,
    audit_case,
    discover_annotation_files,
    sha256_file,
)

PHASE2_VERSION = "expert_annotation_phase2_audit_v1"
CORRECTION_VERSION = "expert_annotation_deterministic_corrections_v1"
CORRECTION_FILENAME = "deterministic_corrections_v1.json"


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _evidence_rows(bundle: Mapping[str, Any], risk_code: str) -> list[Mapping[str, Any]]:
    return [
        row for row in bundle.get("evidence", [])
        if isinstance(row, Mapping) and row.get("risk_code") == risk_code
    ]


def _bound(inputs: Mapping[str, Any], names: Sequence[str]) -> tuple[float, bool, str] | None:
    """Return (upper bound, strict, source field) for the first usable field."""
    for name in names:
        value = _num(inputs.get(name))
        if value is None:
            continue
        lowered = name.lower()
        strict = (
            str(inputs.get("bound_operator") or "").strip() == "<"
            and ("bound" in lowered or "upper" in lowered)
        )
        return value, strict, name
    return None


def _below(bound: tuple[float, bool, str] | None, threshold: float) -> bool:
    if bound is None:
        return False
    value, strict, _ = bound
    return value < threshold or (strict and value <= threshold)


def resolve_concentration_bound(inputs: Mapping[str, Any], kind: str) -> dict[str, Any]:
    """Resolve a formal concentration upper-bound proof when it excludes medium."""
    plural = "customers" if kind == "customer" else "suppliers"
    largest = _bound(
        inputs,
        (
            f"largest_{kind}_upper_bound_pct",
            f"largest_{kind}_bound_pct",
            f"single_{kind}_upper_bound_pct",
            f"largest_{kind}_max_pct",
            f"largest_{kind}_pct",
        ),
    )
    top_five = _bound(
        inputs,
        (
            f"top_five_{kind}_upper_bound_pct",
            f"top_five_{kind}_bound_pct",
            f"top_five_{kind}_max_pct",
            f"top_five_{kind}_pct",
        ),
    )

    # Domain-specific but compatible names, e.g. top_five_patient_revenue_bound_pct.
    if top_five is None:
        for key, raw in inputs.items():
            lowered = str(key).lower()
            if "top_five" in lowered and "pct" in lowered and "threshold" not in lowered:
                value = _num(raw)
                if value is not None:
                    strict = str(inputs.get("bound_operator") or "").strip() == "<" and "bound" in lowered
                    top_five = (value, strict, str(key))
                    break

    # top-five always upper-bounds the largest counterparty.
    if top_five is not None and (largest is None or top_five[0] < largest[0]):
        largest = (top_five[0], top_five[1], f"largest<=({top_five[2]})")

    # If every one of at most N counterparties is formally bounded, aggregate it.
    single = _bound(inputs, (f"single_{kind}_upper_bound_pct",))
    maximum = _num(inputs.get(f"maximum_{plural}_considered"))
    if single is not None and maximum is not None and maximum > 0:
        aggregate = (single[0] * maximum, single[1], f"{single[2]}*maximum_{plural}_considered")
        if top_five is None or aggregate[0] < top_five[0]:
            top_five = aggregate
        if largest is None or single[0] < largest[0]:
            largest = single

    # Some legacy rows store an explicit max rather than an upper-bound key.
    if top_five is None:
        hit = _bound(inputs, (f"top_five_{kind}_max_pct",))
        if hit is not None:
            top_five = hit
            if largest is None or hit[0] < largest[0]:
                largest = (hit[0], False, f"largest<=({hit[2]})")

    details = {
        "largest_upper_bound": None if largest is None else {"value": largest[0], "strict": largest[1], "source": largest[2]},
        "top_five_upper_bound": None if top_five is None else {"value": top_five[0], "strict": top_five[1], "source": top_five[2]},
    }
    if _below(largest, 30) and _below(top_five, 60):
        return {
            "policy_bucket": "BOUND_PROOF_DETERMINISTICALLY_RESOLVED",
            "resolution_status": "resolved",
            "resolution_code": "DETERMINISTIC_BOUND_EXCLUDES_MEDIUM",
            "resolved_level": "not_applicable",
            "requires_human_review": False,
            "details": details,
        }
    return {
        "policy_bucket": "BOUND_PROOF_THRESHOLD_REVIEW",
        "resolution_status": "review_required",
        "resolution_code": "BOUND_DOES_NOT_EXCLUDE_FROZEN_THRESHOLD",
        "resolved_level": None,
        "requires_human_review": True,
        "details": details,
    }


def classify_policy(finding: Mapping[str, Any]) -> dict[str, Any]:
    code = str(finding.get("finding_code") or "")
    risk_code = str(finding.get("risk_code") or "")
    details = finding.get("details") or {}
    if code == "CONCENTRATION_BOUND_PROOF_REQUIRES_REVIEW":
        inputs = details.get("calculation_inputs") if isinstance(details, Mapping) else None
        kind = "customer" if risk_code.startswith("customer_") else "supplier"
        return resolve_concentration_bound(inputs if isinstance(inputs, Mapping) else {}, kind)
    if code == "COMPARABILITY_AMBIGUITY_CONTINUOUS_LOSS":
        return {
            "policy_bucket": "CONTINUOUS_LOSS_COMPARABILITY_REVIEW",
            "resolution_status": "review_required",
            "resolution_code": "COMPARABILITY_POLICY_NOT_FROZEN",
            "resolved_level": None,
            "requires_human_review": True,
            "details": details,
        }
    if code == "POLICY_AMBIGUITY_CONCENTRATION_PERIOD":
        return {
            "policy_bucket": "CONCENTRATION_PERIOD_SELECTION_REVIEW",
            "resolution_status": "review_required",
            "resolution_code": "LATEST_VS_ANY_PERIOD_POLICY_NOT_FROZEN",
            "resolved_level": None,
            "requires_human_review": True,
            "details": details,
        }
    return {
        "policy_bucket": "OTHER_POLICY_REVIEW",
        "resolution_status": "review_required",
        "resolution_code": "UNCLASSIFIED_POLICY_AMBIGUITY",
        "resolved_level": None,
        "requires_human_review": True,
        "details": details,
    }


def classify_insufficient(finding: Mapping[str, Any], bundle: Mapping[str, Any]) -> dict[str, Any]:
    risk_code = str(finding.get("risk_code") or "")
    code = str(finding.get("finding_code") or "")
    if risk_code == "cash_runway":
        bucket = "CASH_INPUT_BACKFILL"
        default_missing = ["cash", "monthly_cash_burn"]
    elif risk_code == "continuous_loss":
        bucket = "LOSS_PERIOD_FACT_BACKFILL"
        default_missing = ["loss_periods"]
    elif risk_code == "revenue_growth":
        bucket = "REVENUE_COMPARABLE_VALUE_BACKFILL"
        default_missing = ["previous_revenue", "current_revenue"]
    elif risk_code == "customer_concentration":
        bucket = "CUSTOMER_RATIO_BACKFILL"
        default_missing = ["largest_pct", "top_five_pct"]
    elif risk_code == "supplier_concentration":
        bucket = "SUPPLIER_RATIO_BACKFILL"
        default_missing = ["largest_pct", "top_five_pct"]
    else:
        bucket = "OTHER_STRUCTURED_INPUT_BACKFILL"
        default_missing = []

    evidence = _evidence_rows(bundle, risk_code)
    raw_details = finding.get("details") or {}
    missing = []
    if isinstance(raw_details, Mapping):
        missing = sorted(str(key) for key, value in raw_details.items() if value is None)
    if not missing:
        missing = default_missing
    priority = (
        "P0_POSITIVE_OR_NEEDS_REVIEW"
        if finding.get("current_applicable") is True or finding.get("current_status") == "needs_review"
        else "P1_REJECTED_LABEL_BACKFILL"
    )
    return {
        "backfill_type": bucket,
        "evidence_state": "EXISTING_EVIDENCE_BACKFILL" if evidence else "SOURCE_REINVESTIGATION_REQUIRED",
        "priority": priority,
        "evidence_count": len(evidence),
        "primary_evidence_count": sum(1 for row in evidence if row.get("evidence_role") == "primary"),
        "missing_fields": missing,
        "finding_code": code,
    }


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run_phase2(root: Path, output_dir: Path | None = None, *, write_corrections: bool = True) -> dict[str, Any]:
    files = discover_annotation_files(root)
    before = {path: sha256_file(path) for path in files}
    hard_rows: list[dict[str, Any]] = []
    policy_rows: list[dict[str, Any]] = []
    input_rows: list[dict[str, Any]] = []
    corrections: dict[str, list[dict[str, Any]]] = defaultdict(list)
    source_sha: dict[str, str] = {}

    for path in files:
        bundle = json.loads(path.read_text(encoding="utf-8"))
        case = audit_case(path)
        case_id = str(case["case_id"])
        source_sha[case_id] = str(case["sha256"])
        for finding in case.get("findings", []):
            status = finding.get("audit_status")
            if status == STATUS_HARD:
                patch = {
                    "risk_code": finding.get("risk_code"),
                    "finding_code": finding.get("finding_code"),
                    "original": {
                        "applicable": finding.get("current_applicable"),
                        "expected_status": finding.get("current_status"),
                        "expected_level": finding.get("current_level"),
                    },
                    "replacement": {
                        "applicable": finding.get("recomputed_applicable"),
                        "expected_status": finding.get("recomputed_status"),
                        "expected_level": finding.get("recomputed_level"),
                    },
                    "audit_message": finding.get("message"),
                    "deterministic_details": finding.get("details") or {},
                }
                corrections[case_id].append(patch)
                hard_rows.append({
                    "case_id": case_id,
                    "risk_code": patch["risk_code"],
                    "finding_code": patch["finding_code"],
                    "source_pass1_sha256": source_sha[case_id],
                    "original_json": _json(patch["original"]),
                    "replacement_json": _json(patch["replacement"]),
                    "details_json": _json(patch["deterministic_details"]),
                })
            elif status == STATUS_POLICY:
                resolution = classify_policy(finding)
                policy_rows.append({
                    "case_id": case_id,
                    "risk_code": finding.get("risk_code"),
                    "finding_code": finding.get("finding_code"),
                    "policy_bucket": resolution["policy_bucket"],
                    "resolution_status": resolution["resolution_status"],
                    "resolution_code": resolution["resolution_code"],
                    "resolved_level": resolution["resolved_level"],
                    "requires_human_review": resolution["requires_human_review"],
                    "current_status": finding.get("current_status"),
                    "current_level": finding.get("current_level"),
                    "details_json": _json(resolution.get("details") or {}),
                })
            elif status == STATUS_INSUFFICIENT:
                split = classify_insufficient(finding, bundle)
                input_rows.append({
                    "case_id": case_id,
                    "risk_code": finding.get("risk_code"),
                    "finding_code": finding.get("finding_code"),
                    "backfill_type": split["backfill_type"],
                    "evidence_state": split["evidence_state"],
                    "priority": split["priority"],
                    "current_status": finding.get("current_status"),
                    "current_level": finding.get("current_level"),
                    "evidence_count": split["evidence_count"],
                    "primary_evidence_count": split["primary_evidence_count"],
                    "missing_fields_json": _json(split["missing_fields"]),
                })

    if write_corrections:
        for case_id, patches in sorted(corrections.items()):
            target = root / "expert_results" / case_id / "audit" / CORRECTION_FILENAME
            target.parent.mkdir(parents=True, exist_ok=True)
            artifact = {
                "artifact_version": CORRECTION_VERSION,
                "phase2_version": PHASE2_VERSION,
                "case_id": case_id,
                "source_pass1": f"expert_results/{case_id}/pass1/expert_annotation_v1.json",
                "source_pass1_sha256": source_sha[case_id],
                "review_outcome": "deterministic_audit_correction",
                "promoted_to_final": False,
                "correction_count": len(patches),
                "corrections": patches,
                "safety": {
                    "pass1_overwritten": False,
                    "evidence_text_modified": False,
                    "reasoning_text_modified": False,
                },
            }
            target.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    summary = {
        "phase2_version": PHASE2_VERSION,
        "cases_scanned": len(files),
        "hard_deterministic_corrections": len(hard_rows),
        "correction_case_count": len(corrections),
        "policy_ambiguities_total": len(policy_rows),
        "policy_deterministically_resolved": sum(row["resolution_status"] == "resolved" for row in policy_rows),
        "policy_review_remaining": sum(row["resolution_status"] != "resolved" for row in policy_rows),
        "policy_buckets": dict(sorted(Counter(row["policy_bucket"] for row in policy_rows).items())),
        "insufficient_input_total": len(input_rows),
        "insufficient_backfill_buckets": dict(sorted(Counter(row["backfill_type"] for row in input_rows).items())),
        "insufficient_priority_counts": dict(sorted(Counter(row["priority"] for row in input_rows).items())),
        "insufficient_evidence_state_counts": dict(sorted(Counter(row["evidence_state"] for row in input_rows).items())),
        "pass1_unchanged": True,
        "pass1_file_count": len(files),
    }

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "phase2_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        _write_csv(output_dir / "correction_manifest.csv", hard_rows, (
            "case_id", "risk_code", "finding_code", "source_pass1_sha256", "original_json", "replacement_json", "details_json",
        ))
        _write_csv(output_dir / "policy_resolution_queue.csv", policy_rows, (
            "case_id", "risk_code", "finding_code", "policy_bucket", "resolution_status", "resolution_code", "resolved_level",
            "requires_human_review", "current_status", "current_level", "details_json",
        ))
        _write_csv(output_dir / "insufficient_input_backfill_queue.csv", input_rows, (
            "case_id", "risk_code", "finding_code", "backfill_type", "evidence_state", "priority", "current_status", "current_level",
            "evidence_count", "primary_evidence_count", "missing_fields_json",
        ))

    after = {path: sha256_file(path) for path in files}
    changed = [path.as_posix() for path in files if before[path] != after[path]]
    if changed:
        raise RuntimeError(f"Phase-2 processing modified pass1 artifacts: {changed}")
    return summary
