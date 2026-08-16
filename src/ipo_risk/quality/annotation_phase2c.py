"""Phase 2c closes all known deterministic financial annotation audit issues.

This phase is an audit-overlay layer. It never rewrites pass1. It consumes the
Phase-1 findings and the structured facts already stored in pass1, applies the
v1.1.2 policy addendum, and writes versioned per-Case resolution artifacts.

"Closed" does not mean "forced numeric answer": when authoritative evidence is
insufficient for a frozen threshold, the final resolved state is needs_review.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

from .annotation_audit import (
    STATUS_HARD,
    STATUS_INSUFFICIENT,
    STATUS_PASS,
    STATUS_POLICY,
    audit_case,
    discover_annotation_files,
    period_signature,
    sha256_file,
)
from .annotation_backfill_normalizers_v2 import canonicalize_record
from .annotation_phase2 import classify_insufficient, classify_policy

PHASE2C_VERSION = "expert_annotation_phase2c_policy_v1_1_2"
POLICY_VERSION = "gpt_expert_policy_addendum_v1.1.2"
RESOLUTION_VERSION = "expert_annotation_financial_resolution_v1"
RESOLUTION_FILENAME = "financial_resolution_v1.json"

_SEVERITY = {
    "not_applicable": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


def _current_state(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "applicable": record.get("applicable"),
        "expected_status": record.get("expected_status"),
        "expected_level": record.get("expected_level"),
    }


def _state_for_level(level: str) -> dict[str, Any]:
    if level == "not_applicable":
        return {"applicable": False, "expected_status": "rejected", "expected_level": "not_applicable"}
    return {"applicable": True, "expected_status": "verified", "expected_level": level}


def _review_state() -> dict[str, Any]:
    return {"applicable": True, "expected_status": "needs_review", "expected_level": None}


def _same_state(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return all(left.get(key) == right.get(key) for key in ("applicable", "expected_status", "expected_level"))


def _max_level(levels: Sequence[str | None]) -> str | None:
    usable = [level for level in levels if level in _SEVERITY]
    if not usable:
        return None
    return max(usable, key=lambda level: _SEVERITY[level])


def period_signature_v112(period: Any) -> str:
    """Recognize English and Chinese duration labels without pooling durations."""
    base = period_signature(period)
    if base != "UNKNOWN":
        return base
    text = str(period or "").strip().lower()
    chinese_patterns = (
        (r"止(?:十二|12)個?月|止(?:十二|12)个月|止年度|截至.*年度|財政年度|财政年度", "FY"),
        (r"止(?:六|6)個?月|止(?:六|6)个月|半年度", "H1"),
        (r"止(?:九|9)個?月|止(?:九|9)个月", "9M"),
        (r"止(?:八|8)個?月|止(?:八|8)个月", "8M"),
        (r"止(?:七|7)個?月|止(?:七|7)个月", "7M"),
        (r"止(?:五|5)個?月|止(?:五|5)个月", "5M"),
        (r"止(?:四|4)個?月|止(?:四|4)个月", "4M"),
        (r"止(?:三|3)個?月|止(?:三|3)个月", "3M"),
    )
    for pattern, label in chinese_patterns:
        if re.search(pattern, text):
            return label
    return "UNKNOWN"


def _iter_loss_rows(value: Any):
    if isinstance(value, Mapping):
        if "period" in value and "loss" in value:
            yield {"period": value.get("period"), "loss": value.get("loss")}
        for child in value.values():
            yield from _iter_loss_rows(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_loss_rows(child)


def _continuous_level_from_facts(facts: Any) -> tuple[str | None, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen = set()
    unknown = []
    for row in _iter_loss_rows(facts):
        try:
            loss = float(row.get("loss"))
        except (TypeError, ValueError):
            continue
        token = (str(row.get("period")), loss)
        if token in seen:
            continue
        seen.add(token)
        if loss >= 0:
            continue
        sig = period_signature_v112(row.get("period"))
        item = {"period": row.get("period"), "loss": loss, "signature": sig}
        if sig == "UNKNOWN":
            unknown.append(item)
        else:
            groups[sig].append(item)
    if unknown:
        return None, {"groups": dict(groups), "unknown": unknown}
    counts = {sig: len(rows) for sig, rows in groups.items()}
    max_count = max(counts.values(), default=0)
    if max_count >= 3:
        level = "high"
    elif max_count >= 2:
        level = "medium"
    else:
        level = "not_applicable"
    return level, {"groups": dict(groups), "counts": counts, "max_comparable_loss_count": max_count}


def _resolved_entry(
    record: Mapping[str, Any],
    *,
    resolved_state: Mapping[str, Any],
    policy_code: str,
    resolution_class: str,
    source_outcome: Mapping[str, Any] | None = None,
    message: str = "",
) -> dict[str, Any]:
    current = _current_state(record)
    state = dict(resolved_state)
    if _same_state(current, state):
        action = "CONFIRM_EXISTING"
    elif state.get("expected_status") == "needs_review":
        action = "SET_REVIEW_STATE"
    else:
        action = "APPLY_AUDIT_OVERLAY_RELABEL"
    return {
        "closure_status": "CLOSED",
        "resolution_class": resolution_class,
        "action": action,
        "policy_code": policy_code,
        "current_state": current,
        "resolved_state": state,
        "source_outcome": dict(source_outcome or {}),
        "message": message,
        "pass1_modified": False,
    }


def resolve_canonical_outcome(record: Mapping[str, Any], outcome: Mapping[str, Any]) -> dict[str, Any]:
    """Turn a Phase-2b canonicalization outcome into a final v1.1.2 audit state."""
    status = str(outcome.get("re_audit_status") or "")
    code = str(outcome.get("finding_code") or "")

    if status == STATUS_PASS:
        level = outcome.get("recomputed_level")
        state = _state_for_level(level) if level in _SEVERITY else _current_state(record)
        return _resolved_entry(record, resolved_state=state, policy_code="CANONICAL_INPUTS_CONFIRM_LABEL", resolution_class="DETERMINISTIC", source_outcome=outcome)

    if status == STATUS_HARD:
        replacement = outcome.get("proposed_replacement")
        if isinstance(replacement, Mapping):
            state = dict(replacement)
        else:
            level = outcome.get("recomputed_level")
            state = _state_for_level(level) if level in _SEVERITY else _review_state()
        return _resolved_entry(record, resolved_state=state, policy_code="CANONICAL_INPUTS_DETERMINISTIC_RELABEL", resolution_class="DETERMINISTIC", source_outcome=outcome)

    if status == STATUS_POLICY:
        facts = outcome.get("normalized_facts")
        if code in {"POLICY_AMBIGUITY_CONCENTRATION_PERIOD", "POLICY_AMBIGUITY_REVENUE_PERIOD_AGGREGATION", "POLICY_AMBIGUITY_CASH_PERIOD_SELECTION"}:
            rows = facts if isinstance(facts, list) else []
            level = _max_level([row.get("level") for row in rows if isinstance(row, Mapping)])
            if level is not None:
                return _resolved_entry(
                    record,
                    resolved_state=_state_for_level(level),
                    policy_code="MAX_SEVERITY_ACROSS_VALID_COMPARABLE_PERIODS",
                    resolution_class="POLICY_RESOLVED",
                    source_outcome=outcome,
                    message="v1.1.2 retains the most adverse valid comparable-period state; later improvement does not erase an observed trigger.",
                )
        if code == "COMPARABILITY_AMBIGUITY_CONTINUOUS_LOSS":
            level, detail = _continuous_level_from_facts(facts)
            if level is not None:
                enriched = dict(outcome)
                enriched["v112_continuous_loss_resolution"] = detail
                return _resolved_entry(
                    record,
                    resolved_state=_state_for_level(level),
                    policy_code="MAX_SEVERITY_WITHIN_HOMOGENEOUS_DURATION_GROUP",
                    resolution_class="POLICY_RESOLVED",
                    source_outcome=enriched,
                    message="v1.1.2 never pools unlike durations; it evaluates each homogeneous duration group and keeps the most severe group.",
                )
        if code in {"OPEN_01_ZERO_REVENUE_GROWTH", "OPEN_01_ZERO_REVENUE_CONCENTRATION"}:
            return _resolved_entry(
                record,
                resolved_state=_state_for_level("not_applicable"),
                policy_code="ZERO_REVENUE_DENOMINATOR_NOT_APPLICABLE",
                resolution_class="POLICY_RESOLVED",
                source_outcome=outcome,
                message="Exact zero revenue excludes a negative-growth/customer-concentration threshold test. Ratios remain null; no synthetic 0% ratio is created.",
            )
        if code == "REVENUE_GROWTH_DENOMINATOR_NONPOSITIVE":
            pairs = facts if isinstance(facts, list) else []
            if pairs:
                safe = True
                for pair in pairs:
                    if not isinstance(pair, Mapping):
                        safe = False
                        break
                    try:
                        previous = float(pair.get("previous_revenue"))
                        current = float(pair.get("current_revenue"))
                    except (TypeError, ValueError):
                        safe = False
                        break
                    if previous != 0 or current < 0:
                        safe = False
                        break
                if safe:
                    return _resolved_entry(
                        record,
                        resolved_state=_state_for_level("not_applicable"),
                        policy_code="ZERO_BASE_NONDECLINE_EXCLUDES_NEGATIVE_GROWTH",
                        resolution_class="POLICY_RESOLVED",
                        source_outcome=outcome,
                        message="With an exact zero base and non-negative current revenue, a negative-growth trigger cannot occur; no percentage is synthesized.",
                    )
        return _resolved_entry(
            record,
            resolved_state=_review_state(),
            policy_code="POLICY_EVIDENCE_LIMITED_FINAL_REVIEW_STATE",
            resolution_class="REVIEW_STATE",
            source_outcome=outcome,
            message="The policy cannot derive a unique numeric label without inventing facts; v1.1.2 closes the audit item as an explicit needs_review state.",
        )

    if status == STATUS_INSUFFICIENT:
        return _resolved_entry(
            record,
            resolved_state=_review_state(),
            policy_code="EVIDENCE_LIMITED_FINAL_REVIEW_STATE",
            resolution_class="REVIEW_STATE",
            source_outcome=outcome,
            message="Existing cited evidence does not support a frozen numeric threshold proof. The correct closed state is needs_review, not an invented number.",
        )

    return _resolved_entry(
        record,
        resolved_state=_review_state(),
        policy_code="UNRECOGNIZED_CANONICAL_OUTCOME_FINAL_REVIEW_STATE",
        resolution_class="REVIEW_STATE",
        source_outcome=outcome,
        message="Unexpected canonicalization outcome was conservatively closed as needs_review.",
    )


def _evidence_refs(bundle: Mapping[str, Any], risk_code: str) -> list[dict[str, Any]]:
    refs = []
    for row in bundle.get("evidence", []):
        if not isinstance(row, Mapping) or row.get("risk_code") != risk_code:
            continue
        refs.append({"page": row.get("page"), "evidence_role": row.get("evidence_role"), "requirement": row.get("requirement"), "source_authority": row.get("source_authority")})
    return refs


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    fields = [
        "case_id", "risk_code", "phase1_status", "phase1_finding_code", "priority",
        "closure_status", "resolution_class", "action", "policy_code",
        "current_state_json", "resolved_state_json", "evidence_count", "message",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run_phase2c(root: Path, output_dir: Path | None = None, *, write_artifacts: bool = True) -> dict[str, Any]:
    files = discover_annotation_files(root)
    before = {path: sha256_file(path) for path in files}
    rows: list[dict[str, Any]] = []
    per_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    phase1_policy = 0
    phase1_insufficient = 0
    priority_counts = Counter()

    for path in files:
        bundle = json.loads(path.read_text(encoding="utf-8"))
        case_id = str(bundle.get("case_id") or path.parents[1].name)
        records = {str(row.get("risk_code")): row for row in bundle.get("risks", []) if isinstance(row, Mapping)}
        phase1 = audit_case(path)
        for finding in phase1.get("findings", []):
            phase1_status = finding.get("audit_status")
            if phase1_status not in {STATUS_POLICY, STATUS_INSUFFICIENT}:
                continue
            risk_code = str(finding.get("risk_code") or "")
            record = records.get(risk_code)
            if not isinstance(record, Mapping):
                continue

            priority = ""
            if phase1_status == STATUS_INSUFFICIENT:
                phase1_insufficient += 1
                split = classify_insufficient(finding, bundle)
                priority = str(split.get("priority") or "")
                priority_counts[priority] += 1
                outcome = canonicalize_record(record)
                resolution = resolve_canonical_outcome(record, outcome)
            else:
                phase1_policy += 1
                if finding.get("finding_code") == "CONCENTRATION_BOUND_PROOF_REQUIRES_REVIEW":
                    bound = classify_policy(finding)
                    if bound.get("resolution_status") == "resolved" and bound.get("resolved_level") in _SEVERITY:
                        resolution = _resolved_entry(record, resolved_state=_state_for_level(str(bound["resolved_level"])), policy_code="FORMAL_BOUND_EXCLUDES_MEDIUM", resolution_class="DETERMINISTIC", source_outcome=bound)
                    else:
                        resolution = _resolved_entry(
                            record,
                            resolved_state=_review_state(),
                            policy_code="BOUND_INSUFFICIENT_FOR_UNIQUE_THRESHOLD_STATE",
                            resolution_class="REVIEW_STATE",
                            source_outcome=bound,
                            message="The formal bound does not uniquely prove a frozen threshold state; needs_review is final unless new numeric evidence is added.",
                        )
                else:
                    outcome = canonicalize_record(record)
                    resolution = resolve_canonical_outcome(record, outcome)

            entry = {
                "risk_code": risk_code,
                "source_phase1_status": phase1_status,
                "source_phase1_finding_code": finding.get("finding_code"),
                "priority": priority or None,
                "evidence_refs": _evidence_refs(bundle, risk_code),
                **resolution,
            }
            per_case[case_id].append(entry)
            rows.append({
                "case_id": case_id,
                "risk_code": risk_code,
                "phase1_status": phase1_status,
                "phase1_finding_code": finding.get("finding_code"),
                "priority": priority,
                "closure_status": resolution["closure_status"],
                "resolution_class": resolution["resolution_class"],
                "action": resolution["action"],
                "policy_code": resolution["policy_code"],
                "current_state_json": json.dumps(resolution["current_state"], ensure_ascii=False, sort_keys=True),
                "resolved_state_json": json.dumps(resolution["resolved_state"], ensure_ascii=False, sort_keys=True),
                "evidence_count": len(entry["evidence_refs"]),
                "message": resolution.get("message") or "",
            })

    if write_artifacts:
        for case_id, entries in sorted(per_case.items()):
            source = root / "expert_results" / case_id / "pass1" / "expert_annotation_v1.json"
            artifact = {
                "artifact_version": RESOLUTION_VERSION,
                "phase2c_version": PHASE2C_VERSION,
                "policy_version": POLICY_VERSION,
                "case_id": case_id,
                "source_pass1": source.relative_to(root).as_posix(),
                "source_pass1_sha256": before[source],
                "entry_count": len(entries),
                "entries": entries,
                "safety": {
                    "pass1_overwritten": False,
                    "evidence_text_modified": False,
                    "reasoning_text_modified": False,
                    "promoted_to_final": False,
                    "audit_overlay_only": True,
                },
            }
            target = root / "expert_results" / case_id / "audit" / RESOLUTION_FILENAME
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    action_counts = Counter(row["action"] for row in rows)
    class_counts = Counter(row["resolution_class"] for row in rows)
    policy_code_counts = Counter(row["policy_code"] for row in rows)
    closed = sum(row["closure_status"] == "CLOSED" for row in rows)
    summary = {
        "phase2c_version": PHASE2C_VERSION,
        "policy_version": POLICY_VERSION,
        "cases_scanned": len(files),
        "phase1_policy_records": phase1_policy,
        "phase1_insufficient_records": phase1_insufficient,
        "financial_issue_records_total": len(rows),
        "financial_issue_records_closed": closed,
        "remaining_unresolved": len(rows) - closed,
        "insufficient_priority_counts": dict(sorted(priority_counts.items())),
        "resolution_action_counts": dict(sorted(action_counts.items())),
        "resolution_class_counts": dict(sorted(class_counts.items())),
        "policy_code_counts": dict(sorted(policy_code_counts.items())),
        "resolution_case_count": len(per_case),
        "pass1_unchanged": True,
        "pass1_file_count": len(files),
    }

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "phase2c_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        _write_csv(output_dir / "phase2c_resolutions.csv", rows)
        _write_csv(output_dir / "phase2c_remaining_unresolved.csv", [r for r in rows if r["closure_status"] != "CLOSED"])

    after = {path: sha256_file(path) for path in files}
    changed = [path.as_posix() for path in files if before[path] != after[path]]
    if changed:
        raise RuntimeError(f"Phase 2c modified pass1 artifacts: {changed}")
    if summary["remaining_unresolved"] != 0:
        raise RuntimeError(f"Phase 2c left unresolved financial issues: {summary['remaining_unresolved']}")
    return summary
