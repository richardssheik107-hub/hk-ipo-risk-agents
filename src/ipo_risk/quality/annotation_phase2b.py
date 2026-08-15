"""Phase-2b P0 structured-input backfill orchestration.

Phase 2b targets only Phase-2 P0 records whose cited Evidence exists but whose
legacy calculation fields were not understood by the Phase-1 auditor. Backfills
are written under per-Case audit directories; pass1 remains byte-for-byte
immutable.
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
from .annotation_phase2 import classify_insufficient
from .annotation_backfill_normalizers import (
    BACKFILL_FILENAME,
    BACKFILL_VERSION,
    PHASE2B_VERSION,
    P0,
    canonicalize_record,
)


def _evidence_refs(bundle: Mapping[str, Any], risk_code: str) -> list[dict[str, Any]]:
    refs = []
    for row in bundle.get("evidence", []):
        if not isinstance(row, Mapping) or row.get("risk_code") != risk_code:
            continue
        refs.append({
            "page": row.get("page"),
            "evidence_role": row.get("evidence_role"),
            "requirement": row.get("requirement"),
            "source_authority": row.get("source_authority"),
        })
    return refs


def _p0_findings(path: Path, bundle: Mapping[str, Any]) -> list[dict[str, Any]]:
    phase1 = audit_case(path)
    rows = []
    for finding in phase1.get("findings", []):
        if finding.get("audit_status") != STATUS_INSUFFICIENT:
            continue
        classified = classify_insufficient(finding, bundle)
        if classified.get("priority") == P0:
            rows.append(dict(finding))
    return rows


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "case_id", "risk_code", "re_audit_status", "finding_code",
        "current_status", "current_level", "recomputed_level",
        "backfill_method", "evidence_count", "source_fields_json",
        "canonical_inputs_json", "message",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run_phase2b(root: Path, output_dir: Path | None = None, *, write_backfills: bool = True) -> dict[str, Any]:
    files = discover_annotation_files(root)
    before = {path: sha256_file(path) for path in files}
    rows: list[dict[str, Any]] = []
    case_artifacts: dict[str, dict[str, Any]] = {}

    for path in files:
        bundle = json.loads(path.read_text(encoding="utf-8"))
        case_id = str(bundle.get("case_id") or path.parents[1].name)
        records = {
            str(row.get("risk_code")): row
            for row in bundle.get("risks", [])
            if isinstance(row, Mapping)
        }
        p0 = _p0_findings(path, bundle)
        if not p0:
            continue
        entries = []
        for finding in p0:
            risk_code = str(finding["risk_code"])
            record = records[risk_code]
            outcome = canonicalize_record(record)
            evidence_refs = _evidence_refs(bundle, risk_code)
            entry = {
                "risk_code": risk_code,
                "source_pass1_finding_code": finding.get("finding_code"),
                "current_state": {
                    "applicable": record.get("applicable"),
                    "expected_status": record.get("expected_status"),
                    "expected_level": record.get("expected_level"),
                },
                "backfill_method": "legacy_structured_fact_normalization",
                "evidence_refs": evidence_refs,
                **outcome,
            }
            entries.append(entry)
            rows.append({
                "case_id": case_id,
                "risk_code": risk_code,
                "re_audit_status": outcome["re_audit_status"],
                "finding_code": outcome["finding_code"],
                "current_status": record.get("expected_status"),
                "current_level": record.get("expected_level"),
                "recomputed_level": outcome.get("recomputed_level"),
                "backfill_method": entry["backfill_method"],
                "evidence_count": len(evidence_refs),
                "source_fields_json": json.dumps(outcome.get("source_fields") or [], ensure_ascii=False, sort_keys=True),
                "canonical_inputs_json": json.dumps(outcome.get("canonical_calculation_inputs") or {}, ensure_ascii=False, sort_keys=True),
                "message": outcome.get("message") or "",
            })
        artifact = {
            "artifact_version": BACKFILL_VERSION,
            "phase2b_version": PHASE2B_VERSION,
            "case_id": case_id,
            "source_pass1": path.relative_to(root).as_posix(),
            "source_pass1_sha256": before[path],
            "priority": P0,
            "entry_count": len(entries),
            "entries": entries,
            "safety": {
                "pass1_overwritten": False,
                "evidence_text_modified": False,
                "reasoning_text_modified": False,
                "promoted_to_final": False,
            },
        }
        case_artifacts[case_id] = artifact
        if write_backfills:
            dest = root / "expert_results" / case_id / "audit" / BACKFILL_FILENAME
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    status_counts = Counter(row["re_audit_status"] for row in rows)
    risk_counts = defaultdict(Counter)
    for row in rows:
        risk_counts[row["risk_code"]][row["re_audit_status"]] += 1
    summary = {
        "phase2b_version": PHASE2B_VERSION,
        "cases_scanned": len(files),
        "p0_records_targeted": len(rows),
        "backfill_case_count": len(case_artifacts),
        "re_audit_status_counts": dict(sorted(status_counts.items())),
        "by_risk_code": {risk: dict(sorted(counts.items())) for risk, counts in sorted(risk_counts.items())},
        "pass1_unchanged": True,
        "pass1_file_count": len(files),
    }

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "phase2b_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        _write_csv(output_dir / "phase2b_backfill_results.csv", rows)
        _write_csv(
            output_dir / "phase2b_unresolved.csv",
            [row for row in rows if row["re_audit_status"] in {STATUS_POLICY, STATUS_INSUFFICIENT}],
        )
        _write_csv(
            output_dir / "phase2b_reaudit_conflicts.csv",
            [row for row in rows if row["re_audit_status"] == STATUS_HARD],
        )

    after = {path: sha256_file(path) for path in files}
    changed = [path.as_posix() for path in files if before[path] != after[path]]
    if changed:
        raise RuntimeError(f"Phase 2b modified pass1 artifacts: {changed}")
    return summary
