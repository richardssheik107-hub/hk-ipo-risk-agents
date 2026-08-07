import csv
from pathlib import Path

from ipo_risk.evaluation.v03_manifest import REQUIRED_COLUMNS, validate_manifest


FIXTURE = Path("tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv")


def test_v03_golden_manifest_matches_frozen_contract():
    assert len(REQUIRED_COLUMNS) == 14
    assert validate_manifest(FIXTURE) == []


def test_financial_draft_cases_cover_all_v03_financial_risks_without_blind_data():
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
    assert all(row["review_status"] == "draft" for row in financial_rows)
    assert all(not row["second_reviewer"] for row in financial_rows)
    assert all("standard_calculation=" in row["notes"] for row in financial_rows)
