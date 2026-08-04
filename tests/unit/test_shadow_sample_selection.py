from __future__ import annotations

from pathlib import Path
import sys
from zipfile import ZipFile

import fitz
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.run_shadow_tests import ShadowCase, load_selection, run_batch, validate_selection


SELECTION_PATH = Path("data/catalog/shadow_sample_24.csv")


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
