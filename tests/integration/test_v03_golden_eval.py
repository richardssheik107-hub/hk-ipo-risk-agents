"""Tests for the v0.3 golden-case evaluation harness (member #2, V3-10)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from ipo_risk.evaluation.batch import run_batch
from ipo_risk.evaluation.golden_eval import evaluate, run_evaluation

CATALOG_DIR = Path(__file__).resolve().parents[2] / "data" / "catalog"

_GOLDEN_FIELDS = [
    "case_id", "stock_code", "company_name", "document_id", "risk_code",
    "applicable", "gold_page", "exact_text", "expected_status",
    "expected_level", "reviewer", "second_reviewer", "review_status", "notes",
]


def _golden_row(case_id, code, *, applicable="true", page="", status="verified", level="high", extra=None):
    row = {
        "case_id": case_id, "stock_code": "0368.HK", "company_name": "德合集团",
        "document_id": case_id, "risk_code": code, "applicable": applicable,
        "gold_page": page, "exact_text": "原文" if applicable == "true" else "",
        "expected_status": status, "expected_level": level if applicable == "true" else "not_applicable",
        "reviewer": "r1", "second_reviewer": "r2", "review_status": "double_reviewed", "notes": "",
    }
    if extra:
        row.update(extra)
    return row


def _risk(code, *, page=None, score=1.0, calc=None):
    evidence = [{"page": page, "relevance_score": score, "text": "x"}] if page is not None else []
    return {
        "risk_code": code, "category": "financial", "risk_type": code, "level": "high",
        "score": 80.0, "verification_status": "verified", "agent_name": "financial",
        "evidence": evidence, "calculation": calc,
    }


def _result(case_id, *, verified=None, pending=None, status="completed", agent_logs=None):
    return {
        "analysis_id": f"a-{case_id}", "request_id": f"r-{case_id}",
        "company_name": "德合集团", "stock_code": "0368.HK", "workflow_version": "mvp_v1",
        "verified_risks": verified or [], "pending_risks": pending or [], "rejected_risks": [],
        "agent_logs": agent_logs or [], "errors": [], "status": status,
        "metadata": {"case_id": case_id},
    }


def _write_golden(path, rows, fields=None):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or _GOLDEN_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def test_metrics_precision_recall_and_evidence(tmp_path: Path) -> None:
    golden = [
        _golden_row("ipo_2020_00368", "continuous_loss", page="10"),
        _golden_row("ipo_2020_00368", "revenue_growth", page="20"),
        _golden_row("ipo_2020_00589", "precommercial_product", applicable="false", status="rejected"),
    ]
    results = [
        _result(
            "ipo_2020_00368",
            verified=[_risk("continuous_loss", page=10)],
            pending=[_risk("revenue_growth", page=99)],
        ),
        _result("ipo_2020_00589"),
    ]
    metrics = evaluate(results, golden, _GOLDEN_FIELDS)

    assert metrics["cases"] == {
        "golden": 2, "evaluated": 2, "missing_from_results": [], "completion_rate": 1.0,
    }
    risk = metrics["risk"]
    assert risk["expected_verified"] == 2
    assert risk["predicted_verified"] == 1
    assert risk["true_positives"] == 1
    assert risk["precision"] == 1.0
    assert risk["recall"] == 0.5
    assert risk["verified_precision"] == 1.0

    evidence = metrics["evidence"]
    assert evidence["applicable_gold_rows"] == 2
    assert evidence["recall_at_1"] == 0.5  # page 10 hit, page 20 missed
    assert evidence["recall_at_5"] == 0.5
    assert metrics["evaluation_provenance"]["formal_reviewed_golden_metric"] is True
    assert metrics["evaluation_provenance"]["development_validation_only"] is False

    assert metrics["extraction"]["available"] is False


def test_missing_case_lowers_completion_rate(tmp_path: Path) -> None:
    golden = [
        _golden_row("ipo_2020_00368", "continuous_loss", page="10"),
        _golden_row("ipo_2020_00589", "continuous_loss", page="12"),
    ]
    results = [_result("ipo_2020_00368", verified=[_risk("continuous_loss", page=10)])]
    metrics = evaluate(results, golden, _GOLDEN_FIELDS)
    assert metrics["cases"]["evaluated"] == 1
    assert metrics["cases"]["missing_from_results"] == ["ipo_2020_00589"]
    assert metrics["cases"]["completion_rate"] == 0.5


def test_formal_metrics_include_single_human_review_and_exclude_draft() -> None:
    first_reviewed = _golden_row(
        "ipo_2020_00368",
        "continuous_loss",
        page="10",
        extra={
            "reviewer": "member-3",
            "second_reviewer": "",
            "review_status": "first_reviewed",
        },
    )
    draft = _golden_row(
        "ipo_2020_00589",
        "continuous_loss",
        page="12",
        extra={
            "reviewer": "member-3",
            "second_reviewer": "",
            "review_status": "draft",
        },
    )
    results = [
        _result("ipo_2020_00368", verified=[_risk("continuous_loss", page=10)]),
        _result("ipo_2020_00589", verified=[_risk("continuous_loss", page=12)]),
    ]

    metrics = evaluate(results, [first_reviewed, draft], _GOLDEN_FIELDS)

    assert metrics["cases"]["golden"] == 1
    assert metrics["cases"]["evaluated"] == 1
    assert metrics["evaluation_provenance"]["real_formally_reviewed_rows"] == 1
    assert metrics["evaluation_provenance"]["formal_reviewed_golden_metric"] is False
    assert metrics["risk"]["expected_verified"] == 1


def test_run_evaluation_reports_formal_metrics_per_domain(tmp_path: Path) -> None:
    golden_path = tmp_path / "golden.csv"
    rows = [
        _golden_row(
            "ipo_2020_00368",
            "continuous_loss",
            page="10",
            extra={"review_status": "first_reviewed", "second_reviewer": ""},
        ),
        _golden_row("ipo_2020_00589", "redemption_rights", applicable="false", status="rejected"),
        _golden_row("ipo_2020_00999", "precommercial_product", applicable="false", status="rejected"),
    ]
    _write_golden(golden_path, rows)
    results_path = tmp_path / "analysis_results.jsonl"
    results_path.write_text(
        "\n".join(
            json.dumps(item)
            for item in (
                _result("ipo_2020_00368", verified=[_risk("continuous_loss", page=10)]),
                _result("ipo_2020_00589"),
                _result("ipo_2020_00999"),
            )
        )
        + "\n",
        encoding="utf-8",
    )

    metrics = run_evaluation(results_path, golden_path, tmp_path / "eval")

    assert set(metrics["domains"]) == {"financial", "legal", "business"}
    assert metrics["domains"]["financial"]["risk"]["recall"] == 1.0
    assert metrics["domains"]["legal"]["cases"]["evaluated"] == 1
    assert metrics["domains"]["business"]["cases"]["evaluated"] == 1


def test_extraction_accuracy_when_gold_numeric_present(tmp_path: Path) -> None:
    fields = _GOLDEN_FIELDS + ["gold_amount", "gold_unit", "gold_period"]
    golden = [
        _golden_row(
            "ipo_2020_00368", "cash_runway", page="10",
            extra={"gold_amount": "2.76", "gold_unit": "months", "gold_period": "2023"},
        ),
    ]
    calc = {"result": 2.76, "unit": "months"}
    results = [_result("ipo_2020_00368", verified=[_risk("cash_runway", page=10, calc=calc)])]
    metrics = evaluate(results, golden, fields)
    assert metrics["extraction"]["available"] is True
    assert metrics["extraction"]["gold_numeric_rows"] == 1
    assert metrics["extraction"]["amount_accuracy"] == 1.0
    assert metrics["extraction"]["unit_accuracy"] == 1.0


def test_run_evaluation_writes_full_bundle(tmp_path: Path) -> None:
    golden_path = tmp_path / "golden.csv"
    _write_golden(golden_path, [_golden_row("ipo_2020_00368", "continuous_loss", page="10")])
    results_path = tmp_path / "analysis_results.jsonl"
    results_path.write_text(
        json.dumps(_result("ipo_2020_00368", verified=[_risk("continuous_loss", page=10)])) + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "eval"
    metrics = run_evaluation(results_path, golden_path, out)

    for name in (
        "analysis_results.jsonl", "risk_items.csv", "evidence_results.csv",
        "case_summary.csv", "failure_report.csv", "evaluation_metrics.json",
    ):
        assert (out / name).is_file(), name
    assert metrics["risk"]["precision"] == 1.0

    with (out / "evidence_results.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["matched"] == "True"
    assert rows[0]["rank"] == "1"


def test_batch_then_eval_end_to_end(tmp_path: Path) -> None:
    batch_out = tmp_path / "batch"
    run_batch(catalog_dir=CATALOG_DIR, output_dir=batch_out, case_ids=["ipo_2020_00368", "ipo_2020_00589"])

    golden_path = tmp_path / "golden.csv"
    _write_golden(
        golden_path,
        [
            _golden_row("ipo_2020_00368", "continuous_loss", page="10"),
            _golden_row("ipo_2020_00589", "continuous_loss", page="12"),
        ],
    )
    metrics = run_evaluation(
        batch_out / "analysis_results.jsonl", golden_path, tmp_path / "eval"
    )
    # Both catalog cases were analysed and map back to their golden case_ids.
    assert metrics["cases"]["evaluated"] == 2
    assert metrics["cases"]["missing_from_results"] == []
