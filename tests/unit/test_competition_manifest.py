from __future__ import annotations

import csv
from pathlib import Path
import sys

import fitz
from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.build_competition_manifest import (
    build,
    dataset_split_for,
    discover_prospectuses,
    normalize_stock_code,
    OFFICIAL_IPO_WORKBOOK_FILENAME,
)


def _write_pdf(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    document.save(path)
    document.close()


def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", encoding="gb18030", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def _write_official_workbook(path: Path) -> None:
    workbook = Workbook()
    master = workbook.active
    master.title = "Merged_Official_Data"
    master.append([
        "Symbol", "ListedDate", "InstitutionID", "SecurityID", "IPOPrice", "OfferPrice",
        "DelistedDate", "ListingBoardID", "ListMethod", "IndustryName2", "INDUSTRYNAME",
        "FundsRaised", "NetProceed",
    ])
    master.append(["00001", "2020-01-02", "inst-1", "sec-1", "10", "10", "", "MAIN", "IPO", "Finance", "", "100", "90"])
    master.append(["02410", "2024-08-20", "inst-2", "sec-2", "8", "8", "", "MAIN", "IPO", "Health", "", "200", "180"])
    matches = workbook.create_sheet("IPO_565_Match")
    matches.append([
        "CaseID", "MatchStatus", "MatchedSymbol", "MatchedListedDate", "MatchedInstitutionID",
        "MatchedSecurityID", "SelectedName", "HasIPOInformation", "HasInstitutionInfo",
        "HasDelistedInfo", "MatchMethod",
    ])
    matches.append(["ipo_2020_00001", "matched", "00001", "2020-01-02", "inst-1", "sec-1", "Test One", True, True, False, "symbol+source_year+ipo"])
    matches.append(["ipo_2024_02410", "matched", "02410", "2024-08-20", "inst-2", "sec-2", "Test Two", True, True, False, "symbol+source_year+ipo"])
    matches.append(["ipo_2025_00002", "manifest_only_placeholder", "", "", "", "", "", False, False, False, "not_found"])
    workbook.save(path)


def _make_tiny_data_root(root: Path) -> None:
    _write_pdf(root / "2020_1份" / "00001_01-01-2020_測試公司_全球發售.pdf", "cash and cash equivalents")
    _write_pdf(root / "2024_1份" / "02410_12-08-2024_同源康醫藥－Ｂ_全球發售.pdf", "現金及現金等價物")
    _write_pdf(root / "2025_1份" / "00002_01-01-2025_盲測公司_股份發售.pdf", "經營活動現金流")
    _write_csv(
        root / "hkcompanyinfo.csv",
        ["OBJECT_ID", "S_INFO_COMPCODE"],
        [["company-1", "code-1"]],
    )
    _write_csv(
        root / "hksharedescription.csv",
        ["OBJECT_ID", "S_INFO_WINDCODE", "S_INFO_LISTDATE"],
        [["security-1", "1.HK"]],
    )
    _write_csv(
        root / "hkshareeodprices.csv",
        ["OBJECT_ID", "S_INFO_WINDCODE", "TRADE_DT", "S_DQ_AMOUNT"],
        [
            ["eod-1", "0001.HK", "20200102", "100"],
            ["eod-2", "0001.HK", "20200103", "120"],
            ["eod-3", "2410.HK", "20240820", "200"],
        ],
    )
    _write_official_workbook(root / OFFICIAL_IPO_WORKBOOK_FILENAME)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_stock_code_normalization_is_explicit() -> None:
    assert normalize_stock_code("02410") == ("2410.HK", "filename_5digit_to_wind_hk_equity")
    assert normalize_stock_code("00001") == ("0001.HK", "filename_5digit_to_wind_hk_equity")
    assert normalize_stock_code("00084") == ("0084.HK", "filename_5digit_to_wind_hk_equity")
    assert normalize_stock_code("ABC01") == ("", "unmatched_invalid_filename_code")
    assert normalize_stock_code("00000") == ("", "unmatched_invalid_filename_code")


def test_frozen_chronological_split_and_exception() -> None:
    assert dataset_split_for(2020, "00001")[0] == "development"
    assert dataset_split_for(2024, "00001")[0] == "validation"
    assert dataset_split_for(2024, "02410")[0] == "development_exception"
    assert dataset_split_for(2025, "00001")[0] == "blind_test"


def test_discovery_preserves_relative_paths_and_chinese(tmp_path: Path) -> None:
    _make_tiny_data_root(tmp_path)

    sources = discover_prospectuses(tmp_path)

    assert len(sources) == 3
    real_case = next(source for source in sources if source.stock_code_raw == "02410")
    assert real_case.company_short_name == "同源康醫藥－Ｂ"
    assert real_case.relative_path == "2024_1份/02410_12-08-2024_同源康醫藥－Ｂ_全球發售.pdf"
    assert real_case.disclosure_date == "2024-08-12"


def test_tiny_build_writes_all_b1_deliverables(tmp_path: Path) -> None:
    data_root = tmp_path / "raw"
    catalog_dir = tmp_path / "catalog"
    docs_dir = tmp_path / "docs"
    data_root.mkdir()
    _make_tiny_data_root(data_root)

    summary = build(data_root, catalog_dir, docs_dir)

    assert summary == {
        "prospectuses": 3,
        "eod_available": 2,
        "eod_missing": 1,
        "official_matched": 2,
        "official_unmatched": 1,
        "quality_issues": 4,
    }
    manifest = _read_csv(catalog_dir / "ipo_prospectus_manifest.csv")
    coverage = _read_csv(catalog_dir / "eod_coverage_report.csv")
    splits = _read_csv(catalog_dir / "dataset_split.csv")
    official_bridge = _read_csv(catalog_dir / "ipo_official_master_bridge.csv")
    issues = _read_csv(catalog_dir / "data_quality_issues.csv")
    assert len(manifest) == len(coverage) == len(splits) == 3
    assert len(official_bridge) == 3
    assert sum(row["official_match_status"] == "matched" for row in official_bridge) == 2
    assert next(row for row in official_bridge if row["case_id"] == "ipo_2024_02410")["listed_date_eod_relation"] == "eod_starts_on_listed_date"
    assert {row["dataset_split"] for row in splits} == {
        "development",
        "development_exception",
        "blind_test",
    }
    assert sum(row["eod_available"] == "true" for row in coverage) == 2
    assert {row["issue_code"] for row in issues} == {
        "EOD_NOT_AVAILABLE",
        "SECURITY_MASTER_TRUNCATED",
        "EOD_AMOUNT_UNIT_UNCONFIRMED",
        "OFFICIAL_IPO_MASTER_MATCH_MISSING",
    }
    assert all(not Path(row["relative_path"]).is_absolute() for row in manifest)
    assert all(len(row["sha256"]) == 64 for row in manifest)
    assert "赛事数据概览" in (docs_dir / "COMPETITION_DATA_OVERVIEW.md").read_text(encoding="utf-8")
    assert "赛事数据质量报告" in (docs_dir / "DATA_QUALITY_REPORT.md").read_text(encoding="utf-8")
