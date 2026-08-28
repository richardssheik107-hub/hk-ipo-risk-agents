"""Create a compact, Gold-safe Financial conversion audit from Role-B artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


FINANCIAL_RISKS = (
    "cash_runway",
    "customer_concentration",
    "supplier_concentration",
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _truth(value: object) -> bool:
    return str(value).strip().lower() == "true"


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["case_id", "risk_code"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _retrieval_index(rows: list[dict[str, str]]) -> dict[tuple[str, str], list[dict[str, str]]]:
    result: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        result[(row["case_id"], row["risk_code"])].append(row)
    return result


def _earliest_stage(row: dict[str, str]) -> str:
    if not _truth(row.get("parser_anchor_available")):
        return "parser_text_missing"
    if not row.get("first_gold_rank"):
        return "retrieval_candidate_miss"
    if not _truth(row.get("agent_consumed")):
        return "agent_consumption_miss"
    if row.get("extraction_status") not in {"extracted", "risk_generated"}:
        return "extraction"
    if not _truth(row.get("builder_risk_present")):
        return "builder"
    if not _truth(row.get("final_present")):
        return "verifier_or_final"
    if not _truth(row.get("m1_correct")):
        return "evaluator_attribute_mismatch"
    return "complete"


def build_audit(
    lifecycle_rows: list[dict[str, str]], retrieval_rows: list[dict[str, str]]
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any], list[dict[str, Any]]]:
    indexed = _retrieval_index(retrieval_rows)
    grouped: dict[str, list[dict[str, Any]]] = {risk: [] for risk in FINANCIAL_RISKS}
    trace: list[dict[str, Any]] = []
    failure_counts: Counter[str] = Counter()
    for row in lifecycle_rows:
        risk = row.get("risk_code", "")
        if risk not in grouped:
            continue
        retrieval = indexed.get((row["case_id"], risk), [])
        page_hit = any(_truth(item.get("gold_page_in_top20")) for item in retrieval)
        anchor_hit = any(_truth(item.get("gold_anchor_in_top20")) for item in retrieval)
        consumed = any(_truth(item.get("agent_consumed_gold_anchor")) for item in retrieval)
        stage = _earliest_stage(row)
        failure_counts[stage] += stage != "complete"
        common: dict[str, Any] = {
            "case_id": row["case_id"],
            "risk_unit_id": row["risk_unit_id"],
            "risk_code": risk,
            "gold_risk_status": row.get("gold_status"),
            "gold_required_attributes": json.dumps(
                {
                    "level": row.get("gold_level"),
                    "calculation_key": row.get("gold_calculation_key"),
                },
                sort_keys=True,
            ),
            "gold_evidence_count": row.get("gold_evidence_count"),
            "retrieved_candidate_count": max(
                (int(item.get("candidate_count") or 0) for item in retrieval),
                default=int(row.get("candidate_evidence_count") or 0),
            ),
            "gold_page_hit": page_hit,
            "gold_anchor_hit": anchor_hit,
            "agent_consumed_gold": consumed,
            "extraction_status": row.get("extraction_status"),
            "builder_status": row.get("builder_status"),
            "risk_item_created": _truth(row.get("builder_risk_present")),
            "verifier_outcome": row.get("verifier_outcome"),
            "final_bucket": row.get("final_bucket"),
            "m1_status_match": _truth(row.get("status_match")),
            "m1_level_match": _truth(row.get("level_match")),
            "m1_calculation_match": _truth(row.get("calculation_match")),
            "m1_evidence_match": _truth(row.get("evidence_hit")),
            "m1_correct": _truth(row.get("m1_correct")),
            "earliest_failure_stage": stage,
            "issue_codes": row.get("secondary_observations", "[]"),
        }
        if risk == "cash_runway":
            common.update(
                {
                    "cash_extraction_status": row.get("extraction_status"),
                    "cash_value_raw": "NOT_PERSISTED_IN_FORENSIC_INPUT",
                    "cash_value_normalized": "NOT_PERSISTED_IN_FORENSIC_INPUT",
                    "cash_currency": "NOT_PERSISTED_IN_FORENSIC_INPUT",
                    "cash_unit": "NOT_PERSISTED_IN_FORENSIC_INPUT",
                    "cash_period_end": "NOT_PERSISTED_IN_FORENSIC_INPUT",
                    "cash_evidence_id": "NOT_PERSISTED_IN_FORENSIC_INPUT",
                    "ocf_extraction_status": row.get("extraction_status"),
                    "ocf_value_raw": "NOT_PERSISTED_IN_FORENSIC_INPUT",
                    "ocf_value_normalized": "NOT_PERSISTED_IN_FORENSIC_INPUT",
                    "ocf_currency": "NOT_PERSISTED_IN_FORENSIC_INPUT",
                    "ocf_unit": "NOT_PERSISTED_IN_FORENSIC_INPUT",
                    "ocf_period_end": "NOT_PERSISTED_IN_FORENSIC_INPUT",
                    "ocf_period_months": "NOT_PERSISTED_IN_FORENSIC_INPUT",
                    "ocf_evidence_id": "NOT_PERSISTED_IN_FORENSIC_INPUT",
                    "calculation_created": _truth(row.get("final_calculation_present")),
                    "runway_months_exact": row.get("predicted_calculation_value"),
                    "policy_level": row.get("final_level"),
                }
            )
        else:
            common.update(
                {
                    "retrieved_evidence_count": row.get("candidate_evidence_count"),
                    "largest_candidate_count": "NOT_PERSISTED_IN_FORENSIC_INPUT",
                    "top_five_candidate_count": "NOT_PERSISTED_IN_FORENSIC_INPUT",
                    "selected_period": "NOT_PERSISTED_IN_FORENSIC_INPUT",
                    "complete_candidate_count": "NOT_PERSISTED_IN_FORENSIC_INPUT",
                    "partial_candidate_count": "NOT_PERSISTED_IN_FORENSIC_INPUT",
                    "same_period_conflict_count": int(
                        "conflicting_values_for_same_period"
                        in row.get("secondary_observations", "")
                    ),
                    "normalization_issues": row.get("normalization_issue_codes", "[]"),
                    "reconciliation_issues": row.get("reconciliation_issue_codes", "[]"),
                    "risk_created": _truth(row.get("builder_risk_present")),
                    "risk_level": row.get("final_level"),
                }
            )
        grouped[risk].append(common)
        trace.append(
            {
                "case_id": row["case_id"],
                "risk_code": risk,
                "retrieval_count": common["retrieved_candidate_count"],
                "consumed_count": int(consumed),
                "extractor_invoked": bool(row.get("extraction_status")),
                "extractor_status": row.get("extraction_status"),
                "extractor_issue_codes": row.get("secondary_observations", "[]"),
                "builder_invoked": row.get("builder_status") != "UNAVAILABLE",
                "builder_status": row.get("builder_status"),
                "calculation_created": _truth(row.get("final_calculation_present")),
                "risk_created": _truth(row.get("builder_risk_present")),
                "verifier_outcome": row.get("verifier_outcome"),
                "final_bucket": row.get("final_bucket"),
                "earliest_failure_stage": stage,
            }
        )
    summary = {
        "report_version": "v046_financial_conversion_audit_v1",
        "risk_unit_count": sum(len(rows) for rows in grouped.values()),
        "per_risk": {
            risk: {
                "risk_units": len(rows),
                "anchor_hit": sum(bool(row["gold_anchor_hit"]) for row in rows),
                "consumed": sum(bool(row["agent_consumed_gold"]) for row in rows),
                "risk_created": sum(bool(row["risk_item_created"]) for row in rows),
                "m1_correct": sum(bool(row["m1_correct"]) for row in rows),
            }
            for risk, rows in grouped.items()
        },
        "earliest_failure_counts": dict(sorted(failure_counts.items())),
        "gold_used_at_runtime": False,
        "validation_opened": False,
        "blind_2025_accessed": False,
    }
    return grouped, summary, trace


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--forensic-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    lifecycle = _read_csv(args.forensic_dir / "05_candidate_lifecycle.csv")
    retrieval = _read_csv(args.forensic_dir / "03_retrieval_stage.csv")
    grouped, summary, trace = build_audit(lifecycle, retrieval)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(args.output_dir / "cash_conversion_units.csv", grouped["cash_runway"])
    _write_csv(
        args.output_dir / "customer_conversion_units.csv",
        grouped["customer_concentration"],
    )
    _write_csv(
        args.output_dir / "supplier_conversion_units.csv",
        grouped["supplier_concentration"],
    )
    (args.output_dir / "financial_conversion_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (args.output_dir / "financial_conversion_trace.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        for row in trace:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
