from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from ipo_risk.evaluation.document_intelligence_benchmark import (
    NOT_AVAILABLE,
    build_benchmark,
    write_benchmark,
)


FIELDS = [
    "case_id",
    "stock_code",
    "company_name",
    "document_id",
    "risk_code",
    "applicable",
    "gold_page",
    "exact_text",
    "expected_status",
    "expected_level",
    "reviewer",
    "second_reviewer",
    "review_status",
    "notes",
]


def _row(case_id: str, risk_code: str, *, applicable: bool = True) -> dict[str, str]:
    return {
        "case_id": case_id,
        "stock_code": "1234.HK",
        "company_name": "Governed case",
        "document_id": case_id,
        "risk_code": risk_code,
        "applicable": str(applicable).lower(),
        "gold_page": "8" if applicable else "",
        "exact_text": "bounded text" if applicable else "",
        "expected_status": "verified" if applicable else "rejected",
        "expected_level": "medium" if applicable else "not_applicable",
        "reviewer": "reviewer-a",
        "second_reviewer": "reviewer-b",
        "review_status": "double_reviewed",
        "notes": "dataset_split=development",
    }


def _golden(path: Path, rows: list[dict[str, str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _result(case_id: str, risk_code: str, *, page: int = 8) -> dict:
    risk = {
        "risk_code": risk_code,
        "evidence": [{"page": page, "relevance_score": 1.0}],
    }
    return {
        "stock_code": "1234.HK",
        "verified_risks": [risk],
        "pending_risks": [],
        "rejected_risks": [],
        "status": "completed",
        "metadata": {"case_id": case_id},
        "agent_logs": [],
    }


def test_missing_analysis_is_not_reported_as_zero_performance(tmp_path: Path) -> None:
    golden = _golden(
        tmp_path / "gold.csv",
        [_row("ipo_2023_01234", "redemption_rights")],
    )
    summary, risks, _ = build_benchmark(golden_path=golden)
    assert summary["risk_micro"]["status"] == NOT_AVAILABLE
    assert summary["risk_micro"]["precision"] is None
    assert summary["missing_or_not_evaluable_cases"] == ["ipo_2023_01234"]
    assert risks[0]["status"] == NOT_AVAILABLE


def test_risk_metrics_reuse_frozen_golden_semantics(tmp_path: Path) -> None:
    golden = _golden(
        tmp_path / "gold.csv",
        [
            _row("ipo_2023_01234", "redemption_rights"),
            _row("ipo_2023_05678", "redemption_rights", applicable=False),
        ],
    )
    results = tmp_path / "results.jsonl"
    results.write_text(
        json.dumps(_result("ipo_2023_01234", "redemption_rights")) + "\n",
        encoding="utf-8",
    )
    summary, risks, _ = build_benchmark(golden_path=golden, results_path=results)
    assert summary["risk_micro"]["precision"] == 1.0
    assert summary["risk_micro"]["recall"] == 1.0
    redemption = next(row for row in risks if row["risk_code"] == "redemption_rights")
    assert redemption["f1"] == 1.0


def test_non_gold_prediction_remains_unjudged(tmp_path: Path) -> None:
    golden = _golden(
        tmp_path / "gold.csv",
        [_row("ipo_2023_01234", "redemption_rights")],
    )
    results = tmp_path / "results.jsonl"
    payloads = [
        _result("ipo_2023_01234", "redemption_rights"),
        _result("ipo_2023_09999", "redemption_rights"),
    ]
    results.write_text("\n".join(json.dumps(item) for item in payloads) + "\n", encoding="utf-8")
    summary, _, _ = build_benchmark(golden_path=golden, results_path=results)
    assert summary["risk_micro"]["precision"] == 1.0


def test_2025_blind_golden_is_rejected_before_evaluation(tmp_path: Path) -> None:
    golden = _golden(
        tmp_path / "gold.csv",
        [_row("ipo_2025_01234", "redemption_rights")],
    )
    with pytest.raises(ValueError, match="2025 Blind"):
        build_benchmark(golden_path=golden)


def test_retriever_metrics_are_labeled_reference_only(tmp_path: Path) -> None:
    golden = _golden(
        tmp_path / "gold.csv",
        [_row("ipo_2023_01234", "precommercial_product")],
    )
    retriever = tmp_path / "retriever.json"
    retriever.write_text(
        json.dumps(
            {
                "LOCKED_VALIDATION_CONSUMED": True,
                "metrics": {"LTR-C": {"r5": 0.7, "r10": 0.8, "r20": 0.9}},
                "per_risk": {"precommercial_product": {"ltr_r5": 0.6, "ltr_r20": 0.8}},
            }
        ),
        encoding="utf-8",
    )
    summary, _, evidence = build_benchmark(
        golden_path=golden,
        retriever_summary_path=retriever,
    )
    assert summary["frozen_retriever_reference"]["classification"].endswith(
        "reference_only"
    )
    business = next(row for row in evidence if row["risk_code"] == "precommercial_product")
    assert business["recall_at_5"] == 0.6
    assert business["precision_at_5"] is None


def test_outputs_are_deterministic_and_small(tmp_path: Path) -> None:
    golden = _golden(
        tmp_path / "gold.csv",
        [_row("ipo_2023_01234", "material_litigation_compliance")],
    )
    summary, risks, evidence = build_benchmark(golden_path=golden)
    first = tmp_path / "first"
    second = tmp_path / "second"
    write_benchmark(first, summary, risks, evidence)
    write_benchmark(second, summary, risks, evidence)
    for name in ("document_benchmark_summary.json", "risk_benchmark.csv", "evidence_benchmark.csv"):
        assert (first / name).read_bytes() == (second / name).read_bytes()
    assert sum(path.stat().st_size for path in first.iterdir()) < 100_000
