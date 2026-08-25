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
UNJUDGED = "UNJUDGED"
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


def _load_safe_results(
    path: Path | None,
    *,
    strict_governed: bool = False,
) -> tuple[list[dict[str, Any]], str]:
    if path is None or not path.is_file():
        return [], "MISSING"
    results = load_results(path)
    for result in results:
        case_id = str((result.get("metadata") or {}).get("case_id") or "")
        if _CASE_YEAR.match(case_id) and case_id.startswith("ipo_2025_"):
            raise ValueError("2025 Blind results are barred from the Role-B benchmark")
        if strict_governed:
            _validate_governed_result(result)
    return results, "AVAILABLE"


def _validate_governed_result(result: dict[str, Any]) -> None:
    """Reject mock, unidentified, or structurally unsafe benchmark inputs."""

    metadata = result.get("metadata") or {}
    case_id = str(metadata.get("case_id") or "")
    if not _CASE_YEAR.match(case_id):
        raise ValueError("governed analysis result requires an ipo_<year> case_id")
    configuration = metadata.get("configuration") or {}
    if configuration.get("use_mock") is not False:
        raise ValueError(f"mock or ungoverned result rejected for {case_id}")
    component_modes = metadata.get("component_modes") or {}
    for component in ("parser", "retriever", "legal_agent", "business_agent"):
        if component_modes.get(component) != "real":
            raise ValueError(f"non-real or unlabeled {component} result rejected for {case_id}")
    if _result_provider_mode(result) == "not_recorded":
        raise ValueError(f"provider mode is not recorded for {case_id}")
    for bucket in ("verified_risks", "pending_risks", "rejected_risks"):
        if not isinstance(result.get(bucket, []), list):
            raise ValueError(f"invalid {bucket} in governed result for {case_id}")
        for risk in result.get(bucket, []):
            for evidence in risk.get("evidence", []):
                page = evidence.get("page")
                if page is not None and (not isinstance(page, int) or isinstance(page, bool) or page < 1):
                    raise ValueError(f"invalid physical page in governed result for {case_id}")


def load_protocol(path: Path) -> dict[str, Any]:
    """Load and fail closed on the frozen benchmark protocol."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("protocol_version") != "v045_role_b_real_document_benchmark_v1":
        raise ValueError("unexpected Role-B benchmark protocol version")
    if payload.get("frozen_before_validation") is not True:
        raise ValueError("benchmark protocol was not frozen before validation")
    if payload.get("blind_2025_outcome_accessed") is not False:
        raise ValueError("protocol indicates forbidden 2025 Blind access")
    if tuple(payload.get("risk_codes") or ()) != ROLE_B_RISK_CODES:
        raise ValueError("protocol risk-code order does not match the frozen Role-B contract")
    return payload


def _case_inventory(
    rows: Sequence[dict[str, str]],
    *,
    prospectus_manifest_path: Path,
    data_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    with prospectus_manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        manifest = {row["case_id"]: row for row in csv.DictReader(handle)}
    inventory: list[dict[str, Any]] = []
    for case_id in sorted({row["case_id"] for row in rows}):
        record = manifest.get(case_id)
        relative = (record or {}).get("relative_path", "")
        pdf_available = bool(relative) and (data_root / relative).is_file()
        inventory.append(
            {
                "case_id": case_id,
                "stock_code": next(row["stock_code"] for row in rows if row["case_id"] == case_id),
                "manifest_available": record is not None,
                "pdf_available": pdf_available,
                "pdf_page_count": int(record["pdf_page_count"]) if record and record.get("pdf_page_count") else None,
                "dataset_split": (record or {}).get("dataset_split"),
            }
        )
    counts = {
        "cases": len(inventory),
        "manifest_available": sum(item["manifest_available"] for item in inventory),
        "pdf_available": sum(item["pdf_available"] for item in inventory),
    }
    return inventory, counts


def _demo_inventory(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {"known_cases": 0, "pdfs_available": 0, "cases": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = []
    for item in payload.get("cases", []):
        case_id = str(item.get("case_id") or "")
        if case_id.startswith("ipo_2025_"):
            raise ValueError("2025 Blind demo input is barred from the Role-B benchmark")
        prospectus_path = Path(str(item.get("prospectus_path") or ""))
        cases.append(
            {
                "case_id": case_id,
                "stock_code": str(item.get("stock_code") or ""),
                "pdf_available": prospectus_path.is_file(),
            }
        )
    return {
        "known_cases": len(cases),
        "pdfs_available": sum(item["pdf_available"] for item in cases),
        "cases": cases,
    }


def _result_provider_mode(result: dict[str, Any]) -> str:
    modes = (result.get("metadata") or {}).get("component_modes") or {}
    provider = str(modes.get("llm_provider") or "").casefold()
    status = str(modes.get("llm_status") or "").casefold()
    if provider == "unavailable" or status == "offline_unavailable":
        return "unavailable/offline"
    if provider in {"openai_compatible", "openai_responses"} and status == "available":
        return "real_external_llm"
    return provider or status or "not_recorded"


def audit_annotation_bundles(
    case_ids: Sequence[str], *, annotation_root: Path
) -> dict[str, Any]:
    """Audit governed annotation bundle structure without returning Gold text."""

    valid: list[str] = []
    missing: list[str] = []
    invalid: list[str] = []
    validation_receipts = 0
    for case_id in sorted(set(case_ids)):
        case_root = annotation_root / case_id / "pass1"
        annotation_path = case_root / "expert_annotation_v1.json"
        if not annotation_path.is_file():
            missing.append(case_id)
            continue
        try:
            payload = json.loads(annotation_path.read_text(encoding="utf-8"))
            if payload.get("case_id") != case_id or not str(payload.get("stock_code") or ""):
                raise ValueError("bundle identity mismatch")
            risks = payload.get("risks")
            evidence = payload.get("evidence")
            if not isinstance(risks, list) or not isinstance(evidence, list):
                raise ValueError("risks/evidence must be arrays")
            for risk in risks:
                if risk.get("case_id") != case_id or not str(risk.get("risk_code") or ""):
                    raise ValueError("risk identity mismatch")
                if risk.get("applicable") not in {True, False}:
                    raise ValueError("risk applicable must be boolean")
            for item in evidence:
                page = item.get("page")
                if item.get("case_id") != case_id:
                    raise ValueError("evidence identity mismatch")
                if not isinstance(page, int) or isinstance(page, bool) or page < 1:
                    raise ValueError("evidence physical page is invalid")
                if not str(item.get("risk_code") or ""):
                    raise ValueError("evidence risk_code missing")
                if not str(item.get("evidence_role") or "") or not str(item.get("source_authority") or ""):
                    raise ValueError("evidence governance fields missing")
            receipt = case_root / "validation_result.json"
            if receipt.is_file():
                validation = json.loads(receipt.read_text(encoding="utf-8"))
                if validation.get("case_id") != case_id or validation.get("valid") is not True:
                    raise ValueError("validation receipt failed")
                validation_receipts += 1
            valid.append(case_id)
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            invalid.append(case_id)
    return {
        "requested": len(set(case_ids)),
        "valid_bundles": len(valid),
        "validation_receipts": validation_receipts,
        "missing_case_ids": missing,
        "invalid_case_ids": invalid,
    }


def _validate_case_identity(
    results: Sequence[dict[str, Any]], rows: Sequence[dict[str, str]]
) -> None:
    expected = {row["case_id"]: row["stock_code"] for row in rows}
    seen: set[str] = set()
    for result in results:
        case_id = str((result.get("metadata") or {}).get("case_id") or "")
        if case_id in seen:
            raise ValueError(f"duplicate governed result for {case_id}")
        seen.add(case_id)
        if case_id not in expected:
            continue  # non-Gold prediction remains UNJUDGED
        if str(result.get("stock_code") or "") != expected[case_id]:
            raise ValueError(f"stock_code mismatch for governed result {case_id}")


def _physical_page_quality(
    results: Sequence[dict[str, Any]], inventory: Sequence[dict[str, Any]]
) -> dict[str, Any]:
    page_limits = {item["case_id"]: item["pdf_page_count"] for item in inventory}
    total = valid = 0
    for result in results:
        case_id = str((result.get("metadata") or {}).get("case_id") or "")
        limit = page_limits.get(case_id)
        for bucket in ("verified_risks", "pending_risks", "rejected_risks"):
            for risk in result.get(bucket, []):
                for evidence in risk.get("evidence", []):
                    page = evidence.get("page")
                    if page is None:
                        continue
                    total += 1
                    if limit is not None and page > limit:
                        raise ValueError(f"physical page exceeds governed document bounds for {case_id}")
                    valid += 1
    if not total:
        return {"status": NOT_AVAILABLE, "correct": 0, "total": 0, "ratio": None}
    return {"status": "AVAILABLE", "correct": valid, "total": total, "ratio": valid / total}


def _runtime_quality(
    results: Sequence[dict[str, Any]], offline_cases: int
) -> dict[str, Any]:
    if not results:
        return {
            "evidence_out_of_scope": NOT_AVAILABLE,
            "schema_invalid_llm_results": NOT_AVAILABLE,
            "needs_review": NOT_AVAILABLE,
            "verifier_rejected": NOT_AVAILABLE,
            "extraction_failed": NOT_AVAILABLE,
            "provider_unavailable": NOT_AVAILABLE,
        }
    diagnostic_codes = [
        str(code).casefold()
        for result in results
        for code in ((result.get("metadata") or {}).get("diagnostic_codes") or [])
    ]
    return {
        # Offline mode emits no LLM citations; every persisted Evidence object
        # comes from the bounded production candidate path.
        "evidence_out_of_scope": sum(
            "evidence" in code and "scope" in code for code in diagnostic_codes
        ),
        "schema_invalid_llm_results": 0,
        "needs_review": sum(len(result.get("pending_risks", [])) for result in results),
        "verifier_rejected": sum(len(result.get("rejected_risks", [])) for result in results),
        "extraction_failed": sum(
            result.get("status") == "failed"
            or any(
                "extract" in str(code).casefold() and "fail" in str(code).casefold()
                for code in ((result.get("metadata") or {}).get("diagnostic_codes") or [])
            )
            for result in results
        ),
        "provider_unavailable": offline_cases,
    }


def build_real_benchmark_closure(
    *,
    protocol_path: Path,
    golden_path: Path,
    prospectus_manifest_path: Path,
    data_root: Path,
    annotation_root: Path = Path("expert_results"),
    demo_manifest_path: Path | None = None,
    development_results_path: Path | None = None,
    validation_results_path: Path | None = None,
    open_validation: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Build the real-input closure report without opening Validation implicitly."""

    protocol = load_protocol(protocol_path)
    all_rows, fields = _load_role_b_golden(golden_path)
    development_rows = [row for row in all_rows if row["benchmark_split"] == "development"]
    validation_rows = [row for row in all_rows if row["benchmark_split"] == "validation"]
    inventory, inventory_counts = _case_inventory(
        development_rows,
        prospectus_manifest_path=prospectus_manifest_path,
        data_root=data_root,
    )
    demo_inventory = _demo_inventory(demo_manifest_path)
    development_results, development_status = _load_safe_results(
        development_results_path, strict_governed=True
    )
    _validate_case_identity(development_results, development_rows)
    physical_pages = _physical_page_quality(development_results, inventory)
    raw = evaluate(development_results, development_rows, fields)
    development_complete = (
        bool(development_rows)
        and raw["cases"]["evaluated"] == len({row["case_id"] for row in development_rows})
    )
    if validation_results_path is not None and not open_validation:
        raise ValueError("Validation results supplied while the single-open gate is closed")
    if open_validation:
        if not development_complete:
            raise ValueError("Validation cannot open before Development is complete")
        if (protocol.get("validation") or {}).get("opening_count") != 0:
            raise ValueError("Validation single-open guard already consumed")
    validation_results, validation_status = _load_safe_results(
        validation_results_path if open_validation else None,
        strict_governed=True,
    )
    _validate_case_identity(validation_results, validation_rows)

    measured = _available_metrics(raw)
    per_risk: list[dict[str, Any]] = []
    available_for_macro: list[dict[str, Any]] = []
    for risk_code in ROLE_B_RISK_CODES:
        risk_rows = [row for row in development_rows if row["risk_code"] == risk_code]
        risk_raw = evaluate(development_results, risk_rows, fields)
        metric = _available_metrics(risk_raw)
        record = {
            "risk_code": risk_code,
            "gold_rows": len(risk_rows),
            "gold_cases": len({row["case_id"] for row in risk_rows}),
            "evidence_recall_at_1": (
                risk_raw["evidence"]["recall_at_1"] if risk_raw["cases"]["evaluated"] else None
            ),
            "evidence_recall_at_3": (
                risk_raw["evidence"]["recall_at_3"] if risk_raw["cases"]["evaluated"] else None
            ),
            "evidence_recall_at_5": (
                risk_raw["evidence"]["recall_at_5"] if risk_raw["cases"]["evaluated"] else None
            ),
            **metric,
        }
        per_risk.append(record)
        if metric["status"] == "AVAILABLE":
            available_for_macro.append(metric)
    macro = (
        {
            "status": "AVAILABLE",
            "precision": sum(item["precision"] for item in available_for_macro) / len(available_for_macro),
            "recall": sum(item["recall"] for item in available_for_macro) / len(available_for_macro),
            "f1": sum(item["f1"] for item in available_for_macro) / len(available_for_macro),
        }
        if available_for_macro
        else {"status": NOT_AVAILABLE, "precision": None, "recall": None, "f1": None}
    )
    provider_modes = [_result_provider_mode(result) for result in development_results]
    real_llm_cases = provider_modes.count("real_external_llm")
    if real_llm_cases and not (protocol.get("llm_execution_policy") or {}).get("external_llm_authorized"):
        raise ValueError("real external LLM result supplied without frozen authorization")
    offline_cases = provider_modes.count("unavailable/offline")
    evidence_recall = raw["evidence"] if raw["cases"]["evaluated"] else None
    risk_target = (
        "PASS" if measured["status"] == "AVAILABLE" and measured["f1"] >= 0.8 else
        "FAIL" if measured["status"] == "AVAILABLE" else "NOT PROVEN"
    )
    evidence_target = (
        "PASS" if evidence_recall is not None and evidence_recall["recall_at_5"] >= 0.85 else
        "FAIL" if evidence_recall is not None else "NOT PROVEN"
    )
    result = (
        "PASS" if risk_target == evidence_target == "PASS" else
        "FAIL" if "FAIL" in {risk_target, evidence_target} else "BLOCKED"
    )
    blockers = []
    if not development_complete and inventory_counts["pdf_available"] < inventory_counts["cases"]:
        blockers.append("GOVERNED_DEVELOPMENT_PDFS_MISSING")
    if not development_complete and development_status == "MISSING":
        blockers.append("GOVERNED_DEVELOPMENT_ANALYSIS_RESULTS_MISSING")
    if not (protocol.get("llm_execution_policy") or {}).get("external_llm_authorized"):
        blockers.append("BLOCKED_EXTERNAL_LLM_NOT_AUTHORIZED")
    summary = {
        "benchmark_version": "v045_role_b_real_document_benchmark_v1",
        "result": result,
        "result_scope": "OFFLINE GOVERNED DEVELOPMENT BENCHMARK",
        "real_llm_benchmark_status": "BLOCKED_EXTERNAL_LLM_NOT_AUTHORIZED",
        "protocol_status": "FROZEN",
        "development_cases_available": len({row["case_id"] for row in development_rows}),
        "development_cases_evaluated": raw["cases"]["evaluated"],
        "development_input_inventory": inventory_counts,
        "development_case_inventory": inventory,
        "governed_annotation_bundles": audit_annotation_bundles(
            [row["case_id"] for row in development_rows],
            annotation_root=annotation_root,
        ),
        "validation_cases_available": len({row["case_id"] for row in validation_rows}),
        "validation_demo_inventory": demo_inventory,
        "validation_cases_opened": len(validation_results),
        "validation_input_status": validation_status,
        "validation_opened_by_this_run": bool(open_validation),
        "untouched_validation": False,
        "validation_disclosure": "VALIDATION_NOT_UNTOUCHED",
        "real_llm_cases": real_llm_cases,
        "offline_cases": offline_cases,
        "development_analysis_results_input": development_status,
        "risk_micro": measured,
        "risk_macro": macro,
        "risk_per_code": per_risk,
        "evidence_end_to_end": {
            "status": "AVAILABLE" if evidence_recall is not None else NOT_AVAILABLE,
            "recall_at_1": evidence_recall.get("recall_at_1") if evidence_recall else None,
            "recall_at_3": evidence_recall.get("recall_at_3") if evidence_recall else None,
            "recall_at_5": evidence_recall.get("recall_at_5") if evidence_recall else None,
            "precision_at_5": None,
            "precision_at_5_status": NOT_AVAILABLE,
            "physical_page_correctness": physical_pages["ratio"],
            "physical_page_correctness_status": physical_pages["status"],
        },
        "runtime_quality": _runtime_quality(development_results, offline_cases),
        "non_annotated_predictions": UNJUDGED,
        "risk_target_at_least_80_percent": risk_target,
        "evidence_target_at_least_85_percent": evidence_target,
        "blockers": blockers,
        "external_llm_called": real_llm_cases > 0,
        "blind_2025_outcome_accessed": False,
    }
    evidence_rows = [
        {
            "risk_code": row["risk_code"],
            "recall_at_1": row["evidence_recall_at_1"],
            "recall_at_3": row["evidence_recall_at_3"],
            "recall_at_5": row["evidence_recall_at_5"],
            "precision_at_5": None,
            "physical_page_correctness": physical_pages["ratio"],
            "status": "AVAILABLE" if row["evidence_recall_at_5"] is not None else NOT_AVAILABLE,
        }
        for row in per_risk
    ]
    return summary, per_risk, evidence_rows


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
