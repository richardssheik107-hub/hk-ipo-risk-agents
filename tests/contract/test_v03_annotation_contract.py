import csv
from pathlib import Path

from ipo_risk.evaluation.v03_manifest import (
    REQUIRED_COLUMNS,
    formal_eligibility_reason,
    is_formally_eligible,
    validate_manifest,
)


FIXTURE = Path("tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv")


def test_v03_golden_manifest_matches_frozen_contract():
    assert len(REQUIRED_COLUMNS) == 14
    assert validate_manifest(FIXTURE) == []


def test_financial_single_human_review_covers_all_risks_without_blind_data():
    with FIXTURE.open("r", encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))

    financial_rows = [row for row in rows if row["reviewer"] == "member-3"]
    positive_codes = {
        row["risk_code"] for row in financial_rows if row["applicable"] == "true"
    }
    assert positive_codes == {
        "cash_runway",
        "continuous_loss",
        "revenue_growth",
        "customer_concentration",
        "supplier_concentration",
    }
    required_stock_codes = {
        "1167.HK",
        "1541.HK",
        "8489.HK",
        "2503.HK",
        "9633.HK",
        "2410.HK",
    }
    actual_stock_codes = {row["stock_code"] for row in financial_rows}
    assert required_stock_codes <= actual_stock_codes
    assert all(
        not row["case_id"].startswith("ipo_2025_") for row in financial_rows
    )
    assert all(
        not row["document_id"].startswith("ipo_2025_") for row in financial_rows
    )
    assert all(row["review_status"] == "first_reviewed" for row in financial_rows)
    assert all(not row["second_reviewer"] for row in financial_rows)
    assert all(is_formally_eligible(row) for row in financial_rows)
    assert all("standard_calculation=" in row["notes"] for row in financial_rows)


def _review_row(**updates):
    row = {
        "reviewer": "member-3",
        "second_reviewer": "",
        "review_status": "first_reviewed",
        "notes": "",
    }
    row.update(updates)
    return row


def test_single_named_human_review_is_formally_eligible() -> None:
    assert is_formally_eligible(_review_row())


def test_primary_only_draft_is_not_formally_eligible() -> None:
    row = _review_row(review_status="draft")
    assert not is_formally_eligible(row)
    assert formal_eligibility_reason(row) == "review_status_not_formal"


def test_double_review_requires_independent_named_humans() -> None:
    assert is_formally_eligible(
        _review_row(review_status="double_reviewed", second_reviewer="member-4")
    )
    assert not is_formally_eligible(
        _review_row(review_status="double_reviewed", second_reviewer="member-3")
    )
    assert not is_formally_eligible(
        _review_row(review_status="double_reviewed", second_reviewer="")
    )


def test_ai_or_placeholder_reviewer_is_never_formally_eligible() -> None:
    for reviewer in ("Codex", "ChatGPT", "AI", "LLM", "auto", "unknown"):
        assert not is_formally_eligible(_review_row(reviewer=reviewer))


def test_adjudication_requires_provenance() -> None:
    missing = _review_row(
        review_status="adjudicated", second_reviewer="member-4", notes="disagreement"
    )
    complete = _review_row(
        review_status="adjudicated",
        second_reviewer="member-4",
        notes="adjudicated_by=member-2",
    )
    assert not is_formally_eligible(missing)
    assert is_formally_eligible(complete)
