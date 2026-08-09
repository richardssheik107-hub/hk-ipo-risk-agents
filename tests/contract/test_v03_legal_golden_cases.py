from __future__ import annotations

import csv
from pathlib import Path

from ipo_risk.evaluation.v03_manifest import validate_manifest


ROOT = Path(__file__).resolve().parents[2]
LEGAL_GOLDEN = ROOT / "tests" / "fixtures" / "v03_golden_cases" / "v03_legal_golden_case_manifest.csv"
PROSPECTUS_MANIFEST = ROOT / "data" / "catalog" / "ipo_prospectus_manifest.csv"


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def _gold_case(row: dict[str, str]) -> str:
    for item in row["notes"].split(";"):
        key, _, value = item.strip().partition("=")
        if key == "gold_case":
            return value
    raise AssertionError(f"missing gold_case tag for {row['case_id']}")


def test_legal_golden_manifest_matches_frozen_annotation_contract() -> None:
    assert validate_manifest(LEGAL_GOLDEN) == []


def test_legal_golden_manifest_covers_pre_rule_cases_a_through_h() -> None:
    rows = _rows(LEGAL_GOLDEN)
    by_case = {_gold_case(row): row for row in rows}

    assert set(by_case) == set("ABCDEFGH")
    assert len(rows) == 8
    assert all(row["gold_page"] and row["exact_text"] for row in rows)
    assert {by_case[key]["risk_code"] for key in "ABCD"} == {"redemption_rights"}
    assert {by_case[key]["risk_code"] for key in "EFGH"} == {"material_litigation_compliance"}


def test_legal_golden_expected_outcomes_preserve_key_legal_distinctions() -> None:
    by_case = {_gold_case(row): row for row in _rows(LEGAL_GOLDEN)}

    assert (by_case["A"]["applicable"], by_case["A"]["expected_status"]) == ("true", "verified")
    assert (by_case["B"]["applicable"], by_case["B"]["expected_status"]) == ("false", "rejected")
    assert by_case["C"]["expected_status"] == "needs_review"
    assert by_case["D"]["expected_status"] == "needs_review"
    assert (by_case["E"]["applicable"], by_case["E"]["expected_status"]) == ("true", "verified")
    assert all(by_case[key]["expected_status"] == "rejected" for key in "FGH")
    assert all(by_case[key]["expected_level"] == "not_applicable" for key in "BFGH")


def test_legal_golden_cases_are_development_only_and_not_claimed_double_reviewed() -> None:
    golden_rows = _rows(LEGAL_GOLDEN)
    source_rows = {row["case_id"]: row for row in _rows(PROSPECTUS_MANIFEST)}

    assert all(source_rows[row["case_id"]]["dataset_split"] == "development" for row in golden_rows)
    assert all(int(source_rows[row["case_id"]]["source_year"]) <= 2023 for row in golden_rows)
    assert all(row["review_status"] == "draft" for row in golden_rows)
    assert all(not row["second_reviewer"].strip() for row in golden_rows)
    assert all(row["document_id"] == row["case_id"] for row in golden_rows)
