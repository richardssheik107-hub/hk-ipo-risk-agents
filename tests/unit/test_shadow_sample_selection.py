from __future__ import annotations

import csv
from pathlib import Path
import sys
from zipfile import ZipFile

import fitz
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.run_shadow_tests import ShadowCase, load_selection, run_batch, validate_selection


SELECTION_PATH = Path("data/catalog/shadow_sample_24.csv")
MANUAL_REVIEW_PATH = Path("data/catalog/shadow_manual_review_12.csv")


def test_repository_shadow_selection_contract() -> None:
    cases = load_selection(SELECTION_PATH)

    assert len(cases) == 24
    assert {year: sum(case.source_year == year for case in cases) for year in range(2020, 2025)} == {
        2020: 5,
        2021: 5,
        2022: 5,
        2023: 4,
        2024: 5,
    }
    assert sum(case.manual_review for case in cases) == 12
    assert sum("low_text_density" in case.selection_tags for case in cases) >= 2
    assert all(case.source_year != 2025 for case in cases)
    assert all(case.stock_code_raw != "02410" for case in cases)


def test_selection_rejects_blind_test_case() -> None:
    cases = load_selection(SELECTION_PATH)
    invalid = ShadowCase(**{**cases[0].__dict__, "source_year": 2025})

    with pytest.raises(ValueError, match="2025 blind-test"):
        validate_selection([invalid, *cases[1:]])


def test_manual_review_records_gate_result() -> None:
    with MANUAL_REVIEW_PATH.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 12
    assert {row["case_id"] for row in rows} == {
        case.case_id for case in load_selection(SELECTION_PATH) if case.manual_review
    }

    cash_applicable = [row for row in rows if row["cash_applicable"] == "true"]
    operating_applicable = [
        row for row in rows if row["operating_cash_flow_applicable"] == "true"
    ]
    assert len(cash_applicable) == 11
    assert len(operating_applicable) == 11
    assert sum(row["cash_hit_top5"] == "true" for row in cash_applicable) == 4
    assert sum(
        row["operating_cash_flow_hit_top5"] == "true" for row in operating_applicable
    ) == 7
    assert all(row["evidence_text_is_source"] == "true" for row in rows)
    assert not any(row["serious_wrong_page"] == "true" for row in rows)

    prudential = next(row for row in rows if row["stock_code_wind"] == "2378.HK")
    assert prudential["cash_hit_top5"] == "n/a"
    assert prudential["operating_cash_flow_hit_top5"] == "n/a"


def test_batch_isolates_failure_and_retrieves_real_text(tmp_path: Path) -> None:
    valid = ShadowCase(
        case_id="shadow_valid",
        source_year=2020,
        archive_filename="2020_fixture.zip",
        source_filename="00001_fixture.pdf",
        stock_code_raw="00001",
        stock_code_wind="1.HK",
        company_short_name="測試公司",
        offering_type="全球發售",
        selection_tags="fixture",
        manual_review=False,
    )
    missing = ShadowCase(**{**valid.__dict__, "case_id": "shadow_missing", "source_filename": "missing.pdf"})
    pdf_path = tmp_path / "source.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "cash and cash equivalents 100 net cash used in operating activities (20)")
    document.save(pdf_path)
    document.close()
    with ZipFile(tmp_path / valid.archive_filename, "w") as archive:
        archive.write(pdf_path, valid.source_filename)

    rows = run_batch(tmp_path, [missing, valid])

    assert rows[0]["parser_status"] == "failed"
    assert rows[0]["failure_code"] == "P-01"
    assert rows[1]["parser_status"] == "completed"
    assert rows[1]["cash_result_count"] == 1
    assert rows[1]["operating_cash_flow_result_count"] == 1
