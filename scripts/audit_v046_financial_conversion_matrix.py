"""Build a Development-only Role-B financial conversion matrix from a finished run."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping


FINANCIAL_RISKS = frozenset(
    {"cash_runway", "customer_concentration", "supplier_concentration"}
)
RUNTIME_UNAVAILABLE_RISKS = frozenset({"redemption_rights"})
DIAGNOSTIC_START = "ComponentDiagnostic(risk_code='{risk_code}'"
EVIDENCE_IDS = re.compile(r"evidence_ids=\[(?P<ids>[^\]]*)\]")
QUOTED_ID = re.compile(r"'([^']+)'")
DIAGNOSTIC_CODE = re.compile(r"code=<DiagnosticCode\.(?P<code>[^:>]+)")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: json.dumps(value, ensure_ascii=False, sort_keys=True)
                    if isinstance(value, (list, dict))
                    else value
                    for key, value in row.items()
                }
            )


def _diagnostic_segment(payload: Mapping[str, Any], risk_code: str) -> str:
    components = payload.get("metadata", {}).get("component_diagnostics", {})
    financial = components.get("financial", {}) if isinstance(components, Mapping) else {}
    value = financial.get("value", "") if isinstance(financial, Mapping) else ""
    if not isinstance(value, str):
        return ""
    start = value.find(DIAGNOSTIC_START.format(risk_code=risk_code))
    if start < 0:
        return ""
    end = value.find("), ComponentDiagnostic", start)
    return value[start : end if end >= 0 else len(value)]


def _diagnostic_evidence_ids(segment: str) -> list[str]:
    match = EVIDENCE_IDS.search(segment)
    return QUOTED_ID.findall(match.group("ids")) if match else []


def _diagnostic_code(segment: str) -> str | None:
    match = DIAGNOSTIC_CODE.search(segment)
    return match.group("code").casefold() if match else None


def _all_risks(payload: Mapping[str, Any]) -> list[tuple[str, Mapping[str, Any]]]:
    result: list[tuple[str, Mapping[str, Any]]] = []
    for bucket in ("verified_risks", "pending_risks", "rejected_risks"):
        values = payload.get(bucket, [])
        if isinstance(values, list):
            result.extend(
                (bucket.removesuffix("_risks"), item)
                for item in values
                if isinstance(item, Mapping)
            )
    return result


def _predicted_positive(analysis: Mapping[str, Any], risk_code: str) -> bool:
    return any(
        item.get("risk_code") == risk_code and bucket in {"verified", "pending"}
        for bucket, item in _all_risks(analysis)
    )


def _load_analysis_universe(mode_root: Path) -> dict[str, Mapping[str, Any]]:
    """Load every completed case, including cases with no positive Gold unit."""

    analyses: dict[str, Mapping[str, Any]] = {}
    run_root = mode_root / "run"
    if not run_root.is_dir():
        return analyses
    for case_root in sorted(path for path in run_root.iterdir() if path.is_dir()):
        result_path = case_root / "analysis_result.json"
        if not result_path.is_file():
            continue
        payload = _load_json(result_path)
        if isinstance(payload, Mapping):
            analyses[case_root.name] = payload
    return analyses


def _family_summary(
    rows: list[dict[str, Any]],
    *,
    manifest: Mapping[str, Any] | None,
    analyses: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    summaries: dict[str, Any] = {}
    for risk_code in sorted(FINANCIAL_RISKS):
        selected = [row for row in rows if row["risk_family"] == risk_code]
        first_failures = Counter(row["final_failure_root"] for row in selected)
        positive_pairs = {(row["case_id"], risk_code) for row in selected}
        predicted_positive_pairs = {
            (case_id, risk_code)
            for case_id, analysis in analyses.items()
            if _predicted_positive(analysis, risk_code)
        }
        explicit_negative_pairs: set[tuple[str, str]] = set()
        if manifest is not None:
            explicit_negative_pairs = {
                (str(item["case_id"]), risk_code)
                for item in manifest.get("risk_units", [])
                if isinstance(item, Mapping)
                and item.get("split") == "development"
                and item.get("source_risk_code") == risk_code
                and item.get("primary_scope") is True
                and item.get("explicit_gold_judgment") is True
                and item.get("applicable") is False
                and str(item.get("case_id")) in analyses
            }
        true_positive_pairs = predicted_positive_pairs & positive_pairs
        false_positive_pairs = predicted_positive_pairs & explicit_negative_pairs
        summaries[risk_code] = {
            "positive_unit_count": len(selected),
            "observed_stage_counts": {
                "candidate_top20_hit": sum(row["top20_hit"] for row in selected),
                "agent_consumed": sum(row["agent_consumed"] for row in selected),
                "structured_fact_created": sum(
                    row["structured_fact_created"] for row in selected
                ),
                "risk_candidate_created": sum(
                    row["risk_candidate_created"] for row in selected
                ),
                "status_matched": sum(
                    row["final_risk_created"]
                    and row["status"] == row["gold_status"]
                    for row in selected
                ),
                "evidence_retained_exact": sum(
                    row["exact_page_match"] and row["exact_anchor_match"]
                    for row in selected
                ),
                "m1_correct": sum(
                    row["final_failure_root"] == "correct" for row in selected
                ),
            },
            "first_failure_counts": dict(sorted(first_failures.items())),
            "negative_control": {
                "status": (
                    "AVAILABLE_FROM_EXPLICIT_EXISTING_GOLD"
                    if manifest is not None
                    else "NOT_AVAILABLE_MANIFEST_NOT_PROVIDED"
                ),
                "explicit_negative_count": len(explicit_negative_pairs),
                "false_positive_count": len(false_positive_pairs),
                "valid_negative_count": len(explicit_negative_pairs - false_positive_pairs),
                "new_valid_risk_count": len(true_positive_pairs),
                "new_invalid_risk_count": len(false_positive_pairs),
                "true_positive_case_ids": sorted(case_id for case_id, _ in true_positive_pairs),
                "false_positive_case_ids": sorted(case_id for case_id, _ in false_positive_pairs),
                "unjudged_treated_as_negative": False,
            },
        }
    return summaries


def _classify(
    *,
    risk_code: str,
    correct: bool,
    top20_hit: bool,
    final_present: bool,
    status_match: bool,
    level_match: bool,
    evidence_match: bool,
    deterministic_fact_created: bool,
    diagnostic: str,
) -> tuple[str, str]:
    if risk_code in RUNTIME_UNAVAILABLE_RISKS:
        return "J", "unavailable_by_runtime_mode"
    if correct:
        return "I", "correct"
    if not top20_hit:
        return "A", "candidate_missing"
    if not final_present:
        if "conflicting_values" in diagnostic or "CONFLICTING_VALUES" in diagnostic:
            return "H", "true_conflict_fail_closed"
        if deterministic_fact_created:
            return "C", "fact_but_no_risk"
        return "B", "consumed_but_no_fact"
    if not status_match:
        return "D", "risk_but_wrong_status"
    if not level_match:
        return "E", "risk_but_wrong_level"
    if not evidence_match:
        return "F", "risk_correct_but_evidence_lost"
    return "G", "verifier_or_reconciliation_drop"


def build_matrix(
    run_root: Path, *, manifest_path: Path | None = None
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    summary = _load_json(run_root / "ablation_summary.json")
    if summary.get("validation_opened") is not False:
        raise ValueError("validation_scope_not_closed")
    if summary.get("blind_2025_outcome_accessed") is not False:
        raise ValueError("blind_scope_not_closed")
    mode_root = run_root / "offline"
    risk_rows = _read_csv(mode_root / "evaluation" / "risk_benchmark.csv")
    evidence_rows = _read_csv(mode_root / "evaluation" / "evidence_benchmark.csv")
    retrieval = _load_json(mode_root / "retrieval_waterfall.json").get("units", [])
    risk_waterfall = _load_json(mode_root / "risk_pipeline_waterfall.json").get("units", [])

    evidence_by_key: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    retrieval_by_key: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    risk_trace_by_id = {
        item["gold_unit_id"]: item for item in risk_waterfall if isinstance(item, Mapping)
    }
    for row in evidence_rows:
        evidence_by_key[(row["case_id"], row["source_risk_code"])].append(row)
    for item in retrieval:
        if isinstance(item, Mapping):
            retrieval_by_key[(str(item["case_id"]), str(item["risk_code"]))].append(item)

    cache = _load_analysis_universe(mode_root)
    rows: list[dict[str, Any]] = []
    for gold in risk_rows:
        risk_code = gold["source_risk_code"]
        if risk_code not in FINANCIAL_RISKS | RUNTIME_UNAVAILABLE_RISKS:
            continue
        case_id = gold["case_id"]
        analysis = cache[case_id]
        key = (case_id, risk_code)
        evidence_units = evidence_by_key[key]
        retrieval_units = retrieval_by_key[key]
        trace = risk_trace_by_id.get(gold["risk_unit_id"], {})
        matching = [
            (bucket, item)
            for bucket, item in _all_risks(analysis)
            if item.get("risk_code") == risk_code
        ]
        bucket, final = matching[0] if matching else ("", {})
        diagnostic = _diagnostic_segment(analysis, risk_code)
        diagnostic_code = _diagnostic_code(diagnostic)
        calculation = final.get("calculation") if isinstance(final, Mapping) else None
        conversion_values = diagnostic.count("'value':") >= 2
        deterministic_fact_created = bool(calculation) or (
            risk_code == "cash_runway"
            and "financial_conversion" in diagnostic
            and conversion_values
        ) or (
            risk_code in {"customer_concentration", "supplier_concentration"}
            and diagnostic_code in {"not_applicable", "risk_generated"}
        )
        top20_hit = any(bool(item.get("gold_evidence_in_top20")) for item in retrieval_units)
        consumed = any(bool(item.get("agent_consumed")) for item in retrieval_units)
        status_match = gold.get("status_match", "").casefold() == "true"
        level_match = gold.get("level_match", "").casefold() == "true"
        evidence_match = gold.get("evidence_hit", "").casefold() == "true"
        correct = gold.get("correct", "").casefold() == "true"
        category, root = _classify(
            risk_code=risk_code,
            correct=correct,
            top20_hit=top20_hit,
            final_present=bool(matching),
            status_match=status_match,
            level_match=level_match,
            evidence_match=evidence_match,
            deterministic_fact_created=deterministic_fact_created,
            diagnostic=diagnostic,
        )
        final_evidence = final.get("evidence", []) if isinstance(final, Mapping) else []
        rows.append(
            {
                "risk_unit_id": gold["risk_unit_id"],
                "case_id": case_id,
                "risk_family": risk_code,
                "expected_positive_unit": True,
                "gold_status": gold["gold_status"],
                "gold_level": gold["gold_level"],
                "gold_supporting_pages": sorted({int(row["page"]) for row in evidence_units}),
                "gold_evidence_unit_count": len(evidence_units),
                "top20_hit": top20_hit,
                "candidate_rank": min(
                    (int(item["first_gold_rank"]) for item in retrieval_units if item.get("first_gold_rank") is not None),
                    default=None,
                ),
                "agent_consumed": consumed,
                "structured_fact_created": bool(matching) or deterministic_fact_created,
                "deterministic_fact_created": deterministic_fact_created,
                "risk_candidate_created": bool(matching),
                "final_risk_created": bool(matching),
                "status": final.get("verification_status") if isinstance(final, Mapping) else None,
                "level": final.get("level") if isinstance(final, Mapping) else None,
                "verifier_state": bucket or "not_reached",
                "evidence_ids_consumed": _diagnostic_evidence_ids(diagnostic),
                "evidence_ids_retained": [
                    item.get("evidence_id") for item in final_evidence if isinstance(item, Mapping)
                ],
                "exact_page_match": evidence_match,
                "exact_anchor_match": evidence_match,
                "final_failure_category": category,
                "final_failure_root": root,
                "recoverable_m1_units": 0 if correct or category == "J" else 1,
                "recoverable_m2_units": sum(
                    row.get("covered", "").casefold() != "true" for row in evidence_units
                ),
                "risk_waterfall_stage": trace.get("first_failure_stage"),
                "component_diagnostic_code": diagnostic_code,
            }
        )

    manifest = _load_json(manifest_path) if manifest_path is not None else None

    root_summary: dict[str, dict[str, int]] = defaultdict(
        lambda: {"risk_units": 0, "recoverable_m1_units": 0, "recoverable_m2_units": 0}
    )
    for row in rows:
        item = root_summary[row["final_failure_root"]]
        item["risk_units"] += 1
        item["recoverable_m1_units"] += row["recoverable_m1_units"]
        item["recoverable_m2_units"] += row["recoverable_m2_units"]
    summary_payload = {
        "report_version": "v046_financial_conversion_matrix_v1",
        "source_run_id": run_root.name,
        "source_run_sha256": sha256(
            (run_root / "ablation_summary.json").read_bytes()
        ).hexdigest(),
        "row_count": len(rows),
        "financial_row_count": sum(row["risk_family"] in FINANCIAL_RISKS for row in rows),
        "runtime_unavailable_row_count": sum(
            row["risk_family"] in RUNTIME_UNAVAILABLE_RISKS for row in rows
        ),
        "category_counts": dict(Counter(row["final_failure_category"] for row in rows)),
        "root_summary": dict(root_summary),
        "family_summary": _family_summary(rows, manifest=manifest, analyses=cache),
        "validation_opened": False,
        "blind_2025_outcome_accessed": False,
        "gold_modified": False,
    }
    return rows, summary_payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    rows, summary = build_matrix(
        args.run_root.resolve(),
        manifest_path=args.manifest.resolve() if args.manifest else None,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(args.output_dir / "financial_conversion_matrix.csv", rows)
    _write_json(args.output_dir / "financial_conversion_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
