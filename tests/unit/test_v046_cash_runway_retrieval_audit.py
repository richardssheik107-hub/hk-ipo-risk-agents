from __future__ import annotations

from types import SimpleNamespace

from scripts.audit_v046_cash_runway_retrieval import rank_units, summarize


def test_rank_units_reports_page_and_anchor_without_persisting_text() -> None:
    units = [
        {
            "evidence_unit_id": "unit-1",
            "exact_text_hash": "a" * 64,
            "exact_text": "cash and cash equivalents were 100 million",
            "page": 9,
        }
    ]
    candidates = [
        SimpleNamespace(page=2, text="other content"),
        SimpleNamespace(page=9, text="Cash and cash equivalents were 100 million."),
    ]

    rows = rank_units(case_id="ipo_2020_00001", units=units, candidates=candidates)

    assert rows == [
        {
            "case_id": "ipo_2020_00001",
            "evidence_unit_id": "unit-1",
            "exact_text_hash": "a" * 64,
            "expected_page": 9,
            "candidate_count": 2,
            "first_gold_page_rank": 2,
            "first_gold_anchor_rank": 2,
            "page_hit_at_20": True,
            "anchor_hit_at_20": True,
        }
    ]
    assert "exact_text" not in rows[0]


def test_summarize_keeps_page_and_anchor_recall_distinct() -> None:
    rows = [
        {
            "case_id": "case-a",
            "page_hit_at_20": True,
            "anchor_hit_at_20": False,
        },
        {
            "case_id": "case-b",
            "page_hit_at_20": True,
            "anchor_hit_at_20": True,
        },
    ]

    assert summarize(rows) == {
        "evidence_unit_count": 2,
        "case_count": 2,
        "page_hit_at_20_count": 2,
        "page_recall_at_20": 1.0,
        "anchor_hit_at_20_count": 1,
        "anchor_recall_at_20": 0.5,
    }
