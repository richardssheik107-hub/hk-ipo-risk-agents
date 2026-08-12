"""Evaluate v0.3 batch analysis results against the golden manifest (member #2).

Consumes ``analysis_results.jsonl`` (from :mod:`ipo_risk.evaluation.batch`) and a
golden-case manifest, then writes the v0.3 evaluation bundle: per-risk and
per-evidence tables, a per-case summary, a failure report, and an aggregate
``evaluation_metrics.json``.

Metrics are computed honestly: numeric extraction accuracy is only reported when
the manifest carries gold numeric columns (``gold_amount`` / ``gold_unit`` /
``gold_period``); otherwise it is marked ``available: false`` rather than faked.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

EXTRACTION_COLUMNS = ("gold_amount", "gold_unit", "gold_period")


def load_results(path: Path) -> list[dict]:
    """Load one analysis result per JSONL line."""
    results: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    return results


def load_golden(path: Path) -> tuple[list[dict], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def _result_case_id(result: dict, stock_to_case: dict[str, str]) -> str:
    case_id = (result.get("metadata") or {}).get("case_id")
    if case_id:
        return case_id
    return stock_to_case.get(result.get("stock_code", ""), result.get("stock_code", ""))


def _predicted_risks(result: dict) -> tuple[list[dict], list[dict]]:
    return result.get("verified_risks", []), result.get("pending_risks", [])


def _evidence_pages(risks: list[dict], risk_code: str) -> list[int]:
    """Predicted evidence pages for a risk code, best-relevance first."""
    evidence: list[dict] = []
    for risk in risks:
        if risk.get("risk_code") == risk_code:
            evidence.extend(risk.get("evidence", []))
    evidence.sort(key=lambda item: item.get("relevance_score", 0.0), reverse=True)
    pages: list[int] = []
    for item in evidence:
        page = item.get("page")
        if isinstance(page, int) and page not in pages:
            pages.append(page)
    return pages


def evaluate(results: list[dict], golden_rows: list[dict], golden_fields: list[str]) -> dict:
    """Compute metrics and disclose whether their labels had formal human review."""
    formally_reviewed = [
        row
        for row in golden_rows
        if row.get("review_status") in {"double_reviewed", "adjudicated"}
        and bool(row.get("second_reviewer", "").strip())
    ]
    real_rows = [row for row in golden_rows if not row.get("case_id", "").startswith("synthetic-")]
    real_formally_reviewed = [
        row for row in formally_reviewed if not row.get("case_id", "").startswith("synthetic-")
    ]
    golden_by_case: dict[str, list[dict]] = defaultdict(list)
    stock_to_case: dict[str, str] = {}
    for row in golden_rows:
        case_id = row["case_id"].strip()
        golden_by_case[case_id].append(row)
        if row.get("stock_code"):
            stock_to_case.setdefault(row["stock_code"].strip(), case_id)

    results_by_case: dict[str, dict] = {}
    for result in results:
        results_by_case[_result_case_id(result, stock_to_case)] = result

    evaluable = sorted(set(golden_by_case) & set(results_by_case))
    missing = sorted(set(golden_by_case) - set(results_by_case))

    # -- risk precision / recall / verified precision ----------------------
    expected_verified: set[tuple[str, str]] = set()
    predicted_verified: set[tuple[str, str]] = set()
    predicted_verified_with_gold = 0
    correct_verified = 0
    for case_id in evaluable:
        rows = golden_by_case[case_id]
        gold_codes = {r["risk_code"] for r in rows if r["applicable"] == "true"}
        exp_verified = {
            r["risk_code"] for r in rows
            if r["applicable"] == "true" and r["expected_status"] == "verified"
        }
        expected_verified |= {(case_id, code) for code in exp_verified}
        verified_codes = {r.get("risk_code") for r in results_by_case[case_id].get("verified_risks", [])}
        predicted_verified |= {(case_id, code) for code in verified_codes}
        for code in verified_codes:
            if code in gold_codes:
                predicted_verified_with_gold += 1
                if code in exp_verified:
                    correct_verified += 1

    tp = len(expected_verified & predicted_verified)
    precision = tp / len(predicted_verified) if predicted_verified else 0.0
    recall = tp / len(expected_verified) if expected_verified else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    verified_precision = (
        correct_verified / predicted_verified_with_gold if predicted_verified_with_gold else 0.0
    )

    # -- evidence recall @k -------------------------------------------------
    applicable_gold = 0
    hits = {1: 0, 3: 0, 5: 0}
    for case_id in evaluable:
        verified, pending = _predicted_risks(results_by_case[case_id])
        predicted = verified + pending
        for row in golden_by_case[case_id]:
            if row["applicable"] != "true" or not row["gold_page"].strip():
                continue
            applicable_gold += 1
            gold_page = int(row["gold_page"])
            pages = _evidence_pages(predicted, row["risk_code"])
            for k in hits:
                if gold_page in pages[:k]:
                    hits[k] += 1
    evidence_recall = {
        f"recall_at_{k}": (hits[k] / applicable_gold if applicable_gold else 0.0) for k in (1, 3, 5)
    }

    # -- numeric extraction accuracy (only if gold columns exist) ----------
    has_extraction = all(column in golden_fields for column in EXTRACTION_COLUMNS)
    if has_extraction:
        extraction = _extraction_accuracy(evaluable, golden_by_case, results_by_case)
    else:
        extraction = {
            "available": False,
            "reason": "golden manifest has no gold_amount/gold_unit/gold_period columns",
        }

    # -- system health ------------------------------------------------------
    statuses = [r.get("status") for r in results]
    analyze_logs = [
        log for r in results for log in r.get("agent_logs", []) if log.get("action") == "analyze"
    ]
    per_agent: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "failed": 0})
    for log in analyze_logs:
        agent = log.get("agent_name", "unknown")
        per_agent[agent]["total"] += 1
        if log.get("status") == "failed":
            per_agent[agent]["failed"] += 1
    agent_failures = sum(bucket["failed"] for bucket in per_agent.values())

    return {
        "evaluation_provenance": {
            "classification": (
                "formal_reviewed_golden"
                if real_rows and len(real_formally_reviewed) == len(real_rows)
                else "development_or_mixed_review"
            ),
            "development_validation_only": len(real_formally_reviewed) != len(real_rows),
            "formal_reviewed_golden_metric": bool(real_rows)
            and len(real_formally_reviewed) == len(real_rows),
            "total_rows": len(golden_rows),
            "formally_reviewed_rows": len(formally_reviewed),
            "real_rows": len(real_rows),
            "real_formally_reviewed_rows": len(real_formally_reviewed),
            "owner_waiver": {
                "financial_second_review_deferred": True,
                "business_second_review_deferred": True,
            },
        },
        "cases": {
            "golden": len(golden_by_case),
            "evaluated": len(evaluable),
            "missing_from_results": missing,
            "completion_rate": len(evaluable) / len(golden_by_case) if golden_by_case else 0.0,
        },
        "risk": {
            "expected_verified": len(expected_verified),
            "predicted_verified": len(predicted_verified),
            "true_positives": tp,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "verified_precision": verified_precision,
        },
        "evidence": {"applicable_gold_rows": applicable_gold, **evidence_recall},
        "extraction": extraction,
        "system": {
            "results": len(results),
            "partial_ratio": statuses.count("partial") / len(statuses) if statuses else 0.0,
            "failed_ratio": statuses.count("failed") / len(statuses) if statuses else 0.0,
            "agent_failure_rate": agent_failures / len(analyze_logs) if analyze_logs else 0.0,
            "per_agent": {agent: dict(bucket) for agent, bucket in sorted(per_agent.items())},
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _extraction_accuracy(evaluable, golden_by_case, results_by_case) -> dict:
    """Compare gold numeric fields against predicted Calculation results."""
    total = correct_amount = correct_unit = 0
    for case_id in evaluable:
        verified = results_by_case[case_id].get("verified_risks", [])
        calc_by_code = {
            r.get("risk_code"): r.get("calculation")
            for r in verified
            if r.get("calculation")
        }
        for row in golden_by_case[case_id]:
            if row["applicable"] != "true" or not (row.get("gold_amount") or "").strip():
                continue
            total += 1
            calc = calc_by_code.get(row["risk_code"])
            if not calc:
                continue
            try:
                if abs(float(calc.get("result")) - float(row["gold_amount"])) <= 1e-6:
                    correct_amount += 1
            except (TypeError, ValueError):
                pass
            if (calc.get("unit") or "").strip() == (row.get("gold_unit") or "").strip():
                correct_unit += 1
    return {
        "available": True,
        "gold_numeric_rows": total,
        "amount_accuracy": correct_amount / total if total else 0.0,
        "unit_accuracy": correct_unit / total if total else 0.0,
    }


def write_tables(results: list[dict], golden_rows: list[dict], output_dir: Path) -> None:
    """Write risk_items.csv, evidence_results.csv, case_summary.csv, failure_report.csv."""
    output_dir.mkdir(parents=True, exist_ok=True)
    golden_by_case: dict[str, list[dict]] = defaultdict(list)
    stock_to_case: dict[str, str] = {}
    for row in golden_rows:
        golden_by_case[row["case_id"].strip()].append(row)
        if row.get("stock_code"):
            stock_to_case.setdefault(row["stock_code"].strip(), row["case_id"].strip())
    results_by_case = {_result_case_id(r, stock_to_case): r for r in results}

    _write_risk_items(results, stock_to_case, output_dir / "risk_items.csv")
    _write_evidence_results(golden_by_case, results_by_case, output_dir / "evidence_results.csv")
    _write_case_summary(golden_by_case, results_by_case, output_dir / "case_summary.csv")
    _write_failure_report(golden_by_case, results_by_case, output_dir / "failure_report.csv")

    # Self-contained bundle: passthrough copy of the analysed results.
    with (output_dir / "analysis_results.jsonl").open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")


def _write_risk_items(results, stock_to_case, path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "case_id", "bucket", "risk_code", "category", "level", "score",
            "verification_status", "agent_name", "evidence_count", "evidence_pages", "has_calculation",
        ])
        for result in results:
            case_id = _result_case_id(result, stock_to_case)
            for bucket in ("verified_risks", "pending_risks", "rejected_risks"):
                for risk in result.get(bucket, []):
                    pages = [e.get("page") for e in risk.get("evidence", []) if e.get("page") is not None]
                    writer.writerow([
                        case_id, bucket.removesuffix("_risks"), risk.get("risk_code"),
                        risk.get("category"), risk.get("level"), risk.get("score"),
                        risk.get("verification_status"), risk.get("agent_name"),
                        len(risk.get("evidence", [])), json.dumps(pages),
                        risk.get("calculation") is not None,
                    ])


def _write_evidence_results(golden_by_case, results_by_case, path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["case_id", "risk_code", "gold_page", "matched", "rank", "predicted_pages"])
        for case_id in sorted(golden_by_case):
            result = results_by_case.get(case_id)
            predicted = (result.get("verified_risks", []) + result.get("pending_risks", [])) if result else []
            for row in golden_by_case[case_id]:
                if row["applicable"] != "true" or not row["gold_page"].strip():
                    continue
                gold_page = int(row["gold_page"])
                pages = _evidence_pages(predicted, row["risk_code"])
                rank = pages.index(gold_page) + 1 if gold_page in pages else ""
                writer.writerow([
                    case_id, row["risk_code"], gold_page, gold_page in pages, rank, json.dumps(pages),
                ])


def _write_case_summary(golden_by_case, results_by_case, path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "case_id", "has_result", "status", "verified_risks", "pending_risks",
            "expected_verified", "predicted_verified", "agent_failures",
        ])
        for case_id in sorted(golden_by_case):
            result = results_by_case.get(case_id)
            rows = golden_by_case[case_id]
            expected_verified = sum(
                1 for r in rows if r["applicable"] == "true" and r["expected_status"] == "verified"
            )
            if result is None:
                writer.writerow([case_id, False, "missing", "", "", expected_verified, "", ""])
                continue
            analyze_logs = [log for log in result.get("agent_logs", []) if log.get("action") == "analyze"]
            writer.writerow([
                case_id, True, result.get("status"),
                len(result.get("verified_risks", [])), len(result.get("pending_risks", [])),
                expected_verified, len(result.get("verified_risks", [])),
                sum(1 for log in analyze_logs if log.get("status") == "failed"),
            ])


def _write_failure_report(golden_by_case, results_by_case, path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["case_id", "reason", "detail"])
        for case_id in sorted(golden_by_case):
            result = results_by_case.get(case_id)
            if result is None:
                writer.writerow([case_id, "missing_from_results", "golden case has no analysis result"])
                continue
            if result.get("status") == "failed":
                messages = "; ".join(e.get("message", "") for e in result.get("errors", []))
                writer.writerow([case_id, "analysis_failed", messages])


def run_evaluation(results_path: Path, golden_path: Path, output_dir: Path) -> dict:
    """End-to-end: load, evaluate, write all bundle files, return the metrics."""
    results = load_results(results_path)
    golden_rows, golden_fields = load_golden(golden_path)
    metrics = evaluate(results, golden_rows, golden_fields)
    write_tables(results, golden_rows, output_dir)
    (output_dir / "evaluation_metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return metrics
