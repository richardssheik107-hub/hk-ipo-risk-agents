"""Submission-oriented Role-B Risk/Evidence benchmark.

The evaluator reuses the frozen v0.3 Golden metric implementation.  Its main
addition is availability semantics: absent governed analysis results remain
``NOT AVAILABLE`` instead of being presented as measured zero performance.
"""

from __future__ import annotations

import csv
import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from ipo_risk.evaluation.golden_eval import evaluate, load_golden, load_results
from ipo_risk.evaluation.v03_manifest import is_formally_eligible


ROLE_B_RISK_CODES = (
    "redemption_rights",
    "material_litigation_compliance",
    "precommercial_product",
)
NOT_AVAILABLE = "NOT AVAILABLE"
_CASE_YEAR = re.compile(r"^ipo_(\d{4})_")


def _split(case_id: str, notes: str) -> str:
    match = _CASE_YEAR.match(case_id)
    if match and int(match.group(1)) == 2025:
        raise ValueError("2025 Blind cases are barred from the Role-B benchmark")
    note_match = re.search(r"dataset_split=(development|validation)", notes)
    if note_match:
        return note_match.group(1)
    if not match:
        return "development_exception"
    year = int(match.group(1))
    return "validation" if year == 2024 else "development"


def _load_role_b_golden(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    rows, fields = load_golden(path)
    selected = [
        row
        for row in rows
        if row.get("risk_code") in ROLE_B_RISK_CODES
        and not row.get("case_id", "").startswith("synthetic-")
        and is_formally_eligible(row)
    ]
    for row in selected:
        row["benchmark_split"] = _split(row["case_id"], row.get("notes", ""))
    return selected, fields


def _load_safe_results(path: Path | None) -> tuple[list[dict[str, Any]], str]:
    if path is None or not path.is_file():
        return [], "MISSING"
    results = load_results(path)
    for result in results:
        case_id = str((result.get("metadata") or {}).get("case_id") or "")
        if _CASE_YEAR.match(case_id) and case_id.startswith("ipo_2025_"):
            raise ValueError("2025 Blind results are barred from the Role-B benchmark")
    return results, "AVAILABLE"


def _available_metrics(raw: dict[str, Any]) -> dict[str, Any]:
    if raw["cases"]["evaluated"] == 0:
        return {
            "status": NOT_AVAILABLE,
            "reason": "no governed analysis result overlaps the formal Human Golden",
            "precision": None,
            "recall": None,
            "f1": None,
        }
    return {"status": "AVAILABLE", **raw["risk"]}


def _retriever_reference(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {"status": NOT_AVAILABLE}
    payload = json.loads(path.read_text(encoding="utf-8"))
    metrics = payload.get("metrics", {}).get("LTR-C", {})
    return {
        "status": "AVAILABLE",
        "classification": "frozen_retriever_locked_validation_reference_only",
        "validation_consumed": bool(payload.get("LOCKED_VALIDATION_CONSUMED")),
        "recall_at_5": metrics.get("r5"),
        "recall_at_10": metrics.get("r10"),
        "recall_at_20": metrics.get("r20"),
        "per_risk": payload.get("per_risk", {}),
    }


def build_benchmark(
    *,
    golden_path: Path,
    results_path: Path | None = None,
    retriever_summary_path: Path | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    rows, fields = _load_role_b_golden(golden_path)
    results, result_input_status = _load_safe_results(results_path)
    overall_raw = evaluate(results, rows, fields)
    per_risk: list[dict[str, Any]] = []
    available_for_macro: list[dict[str, Any]] = []
    for risk_code in ROLE_B_RISK_CODES:
        risk_rows = [row for row in rows if row["risk_code"] == risk_code]
        raw = evaluate(results, risk_rows, fields)
        measured = _available_metrics(raw)
        record = {
            "risk_code": risk_code,
            "gold_rows": len(risk_rows),
            "gold_cases": len({row["case_id"] for row in risk_rows}),
            **measured,
        }
        per_risk.append(record)
        if measured["status"] == "AVAILABLE":
            available_for_macro.append(measured)

    macro = (
        {
            "status": "AVAILABLE",
            "precision": sum(item["precision"] for item in available_for_macro)
            / len(available_for_macro),
            "recall": sum(item["recall"] for item in available_for_macro)
            / len(available_for_macro),
            "f1": sum(item["f1"] for item in available_for_macro)
            / len(available_for_macro),
        }
        if available_for_macro
        else {"status": NOT_AVAILABLE, "precision": None, "recall": None, "f1": None}
    )
    retriever = _retriever_reference(retriever_summary_path)
    evidence_rows = []
    for risk_code in ROLE_B_RISK_CODES:
        frozen = retriever.get("per_risk", {}).get(risk_code, {})
        evidence_rows.append(
            {
                "risk_code": risk_code,
                "metric_scope": "frozen_retriever_reference",
                "recall_at_5": frozen.get("ltr_r5"),
                "recall_at_20": frozen.get("ltr_r20"),
                "precision_at_5": None,
                "physical_page_correctness": None,
                "status": "AVAILABLE" if frozen else NOT_AVAILABLE,
            }
        )

    splits = {name: set() for name in ("development", "validation", "development_exception")}
    for row in rows:
        splits[row["benchmark_split"]].add(row["case_id"])
    risk_metrics = _available_metrics(overall_raw)
    summary = {
        "benchmark_version": "v045_role_b_document_benchmark_v1",
        "result": "PARTIAL" if rows else "BLOCKED",
        "blocker": "BLOCKED_EXTERNAL_LLM_NOT_AUTHORIZED",
        "analysis_results_input": result_input_status,
        "development_cases": len(splits["development"]),
        "validation_cases": len(splits["validation"]),
        "development_exception_cases": len(splits["development_exception"]),
        "real_llm_cases": 0,
        "stub_only_cases": 0,
        "formal_golden_rows": len(rows),
        "risk_micro": risk_metrics,
        "risk_macro": macro,
        "risk_per_code": per_risk,
        "evidence_end_to_end": {
            "status": NOT_AVAILABLE,
            "recall_at_1": None,
            "recall_at_3": None,
            "recall_at_5": None,
            "precision_at_5": None,
            "physical_page_correctness": None,
            "reason": "governed Agent analysis results and exhaustive Evidence judgments are absent",
        },
        "frozen_retriever_reference": retriever,
        "evidence_scope_validity": {"status": NOT_AVAILABLE},
        "schema_valid_structured_output_ratio": {"status": NOT_AVAILABLE},
        "verifier_ratios": {"status": NOT_AVAILABLE},
        "extraction_failure_ratio": {"status": NOT_AVAILABLE},
        "failure_matrix": {
            "parser/input issue": len(overall_raw["cases"]["missing_from_results"]),
            "LLM provider unavailable": len({row["case_id"] for row in rows}),
            "invalid structured response": 0,
            "Evidence out of scope": 0,
            "semantic conflict": 0,
            "Builder insufficient facts": 0,
            "Verifier rejected": 0,
            "Gold/schema mismatch": 0,
            "retrieval miss": 0,
            "unknown": 0,
        },
        "missing_or_not_evaluable_cases": overall_raw["cases"]["missing_from_results"],
        "external_llm_called": False,
        "validation_consumed_by_this_run": False,
        "blind_2025_outcome_accessed": False,
    }
    return summary, per_risk, evidence_rows


def write_benchmark(
    output_dir: Path,
    summary: dict[str, Any],
    risk_rows: Sequence[dict[str, Any]],
    evidence_rows: Sequence[dict[str, Any]],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "document_benchmark_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for name, rows in (("risk_benchmark.csv", risk_rows), ("evidence_benchmark.csv", evidence_rows)):
        path = output_dir / name
        fieldnames = list(rows[0]) if rows else []
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
