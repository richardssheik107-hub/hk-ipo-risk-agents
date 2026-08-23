from __future__ import annotations

import argparse
import csv
from datetime import date, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from ipo_risk.market.csmar_hsi import (
    CSMAR_HSI_NORMALIZED_SCHEMA_VERSION,
    CSMAR_HSI_REQUIRED_COLUMNS,
    CSMARHSIError,
    CSMARHSIProvider,
    CSMARHSISourceManifest,
    load_csmar_hsi_bars,
    sha256_file,
)
from scripts.run_v04_c_hsi import run


ARCHIVE_SHA = "a" * 64
SOURCE_SHA = "b" * 64
SOURCE_VERSION = (
    f"{CSMAR_HSI_NORMALIZED_SCHEMA_VERSION}:"
    f"{ARCHIVE_SHA[:12]}:{SOURCE_SHA[:12]}"
)


def normalized_row(trading_date: str, close: str) -> dict[str, str]:
    return {
        "reference_id": "HSI",
        "trading_date": trading_date,
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "constituent_volume": "123",
        "index_return": "0.01",
        "source_record_id": f"project:CSMAR:IDX_Gidxtrd.xls:HSI:{trading_date}",
        "source_id": "CSMAR",
        "source_version": SOURCE_VERSION,
        "project_generated_identity": "true",
    }


def write_normalized(
    path: Path,
    rows: list[dict[str, str]],
    *,
    fieldnames: tuple[str, ...] = CSMAR_HSI_REQUIRED_COLUMNS,
    bom: bool = False,
) -> None:
    encoding = "utf-8-sig" if bom else "utf-8"
    with path.open("w", encoding=encoding, newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def manifest_for(path: Path, rows: list[dict[str, str]]) -> CSMARHSISourceManifest:
    dates = sorted(date.fromisoformat(row["trading_date"]) for row in rows)
    return CSMARHSISourceManifest(
        series_type="unspecified_by_delivered_metadata",
        series_type_status="SERIES_TYPE_REQUIRES_METADATA_CONFIRMATION",
        source_file_name="IDX_Gidxtrd.xls",
        source_archive_name="国际指数日行情文件.zip",
        source_archive_sha256=ARCHIVE_SHA,
        source_file_sha256=SOURCE_SHA,
        normalized_file_sha256=sha256_file(path),
        row_count=len(rows),
        coverage_start=dates[0],
        coverage_end=dates[-1],
        duplicate_count=0,
        null_close_count=0,
        invalid_close_count=0,
        parse_error_count=0,
        retrieval_metadata={"workbook_open_mode": "read_only"},
        license_notice="仅供西安交通大学使用",
    )


def test_loader_accepts_utf8_bom_and_sorts_deterministically(tmp_path: Path) -> None:
    path = tmp_path / "hsi.csv"
    rows = [
        normalized_row("2020-01-03", "28500.5"),
        normalized_row("2020-01-02", "28200.1"),
    ]
    write_normalized(path, rows, bom=True)
    manifest = manifest_for(path, rows)
    first = load_csmar_hsi_bars(path, manifest)
    second = load_csmar_hsi_bars(path, manifest)
    assert first == second
    assert [bar.trading_date for bar in first] == [
        date(2020, 1, 2),
        date(2020, 1, 3),
    ]
    assert first[0].reference_id == "HSI"
    assert first[0].provenance.source == "CSMAR"
    assert first[0].provenance.metadata["project_generated_identity"] is True


def test_provider_enforces_hsi_and_exclusive_listing_cutoff(tmp_path: Path) -> None:
    path = tmp_path / "hsi.csv"
    rows = [
        normalized_row("2020-01-02", "28200.1"),
        normalized_row("2020-01-03", "28500.5"),
    ]
    write_normalized(path, rows)
    provider = CSMARHSIProvider(path, manifest_for(path, rows))
    bars = provider.get_benchmark_bars(
        "HSI",
        end_date_exclusive=date(2020, 1, 3),
    )
    assert [bar.trading_date for bar in bars] == [date(2020, 1, 2)]
    with pytest.raises(CSMARHSIError, match="cannot serve"):
        provider.get_benchmark_bars("HSC", end_date_exclusive=date(2020, 1, 3))


@pytest.mark.parametrize("bad_close", ["", "0", "-1", "NaN", "Infinity", "bad"])
def test_loader_rejects_missing_invalid_or_nonpositive_close(
    tmp_path: Path,
    bad_close: str,
) -> None:
    path = tmp_path / "hsi.csv"
    rows = [normalized_row("2020-01-02", bad_close)]
    write_normalized(path, rows)
    with pytest.raises(CSMARHSIError, match="close"):
        load_csmar_hsi_bars(path, manifest_for(path, rows))


def test_loader_rejects_duplicate_dates(tmp_path: Path) -> None:
    path = tmp_path / "hsi.csv"
    rows = [
        normalized_row("2020-01-02", "28200"),
        normalized_row("2020-01-02", "28201"),
    ]
    write_normalized(path, rows)
    with pytest.raises(CSMARHSIError, match="duplicate HSI trading date"):
        load_csmar_hsi_bars(path, manifest_for(path, rows))


def test_loader_rejects_hash_column_and_reference_mismatches(tmp_path: Path) -> None:
    path = tmp_path / "hsi.csv"
    rows = [normalized_row("2020-01-02", "28200")]
    write_normalized(path, rows)
    manifest = manifest_for(path, rows)
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(CSMARHSIError, match="hash mismatch"):
        load_csmar_hsi_bars(path, manifest)

    wrong_columns_path = tmp_path / "wrong-columns.csv"
    write_normalized(
        wrong_columns_path,
        rows,
        fieldnames=tuple(name for name in CSMAR_HSI_REQUIRED_COLUMNS if name != "open"),
    )
    with pytest.raises(CSMARHSIError, match="columns"):
        load_csmar_hsi_bars(
            wrong_columns_path,
            manifest_for(wrong_columns_path, rows),
        )

    wrong_reference_path = tmp_path / "wrong-reference.csv"
    wrong_rows = [{**rows[0], "reference_id": "HSC"}]
    write_normalized(wrong_reference_path, wrong_rows)
    with pytest.raises(CSMARHSIError, match="unexpected reference_id"):
        load_csmar_hsi_bars(
            wrong_reference_path,
            manifest_for(wrong_reference_path, wrong_rows),
        )


def test_manifest_rejects_invalid_accepted_source_counts(tmp_path: Path) -> None:
    path = tmp_path / "hsi.csv"
    rows = [normalized_row("2020-01-02", "28200")]
    write_normalized(path, rows)
    payload = manifest_for(path, rows).model_dump()
    payload["duplicate_count"] = 1
    with pytest.raises(ValidationError, match="invalid rows"):
        CSMARHSISourceManifest.model_validate(payload)


def test_committed_license_safe_source_manifest_validates() -> None:
    manifest = CSMARHSISourceManifest.from_path(
        Path("data/catalog/csmar_hsi_source_manifest.json")
    )
    assert manifest.reference_id == "HSI"
    assert manifest.row_count == 943
    assert manifest.coverage_start == date(2020, 1, 2)
    assert manifest.coverage_end == date(2026, 8, 21)
    assert manifest.series_type_status == "SERIES_TYPE_REQUIRES_METADATA_CONFIRMATION"
    assert "西安交通大学" in manifest.license_notice


def test_readiness_orchestration_preserves_every_case_and_is_deterministic(
    tmp_path: Path,
) -> None:
    normalized_path = tmp_path / "hsi.csv"
    start = date(2020, 1, 2)
    rows = [
        normalized_row((start + timedelta(days=index)).isoformat(), str(28000 + index))
        for index in range(35)
    ]
    write_normalized(normalized_path, rows)
    source_manifest = manifest_for(normalized_path, rows)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        source_manifest.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    catalog_path = tmp_path / "catalog.csv"
    with catalog_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "case_id",
                "stock_code_wind",
                "dataset_split",
                "official_match_status",
                "official_listed_date",
            ),
        )
        writer.writeheader()
        writer.writerows(
            [
                {
                    "case_id": "case-b",
                    "stock_code_wind": "0002.HK",
                    "dataset_split": "development_exception",
                    "official_match_status": "matched",
                    "official_listed_date": "2020-02-10",
                },
                {
                    "case_id": "case-a",
                    "stock_code_wind": "0001.HK",
                    "dataset_split": "development",
                    "official_match_status": "matched",
                    "official_listed_date": "2020-02-11",
                },
                {
                    "case_id": "blind-forbidden",
                    "stock_code_wind": "9999.HK",
                    "dataset_split": "blind",
                    "official_match_status": "matched",
                    "official_listed_date": "2025-01-02",
                },
            ]
        )
    output_dir = tmp_path / "output"
    args = argparse.Namespace(
        normalized_csv=normalized_path,
        source_manifest=manifest_path,
        catalog=catalog_path,
        output_dir=output_dir,
        expected_cases=2,
    )
    first = run(args)
    second = run(args)
    assert first == second
    assert first["official_cases"] == 2
    assert first["hsi_5d_available"] == 2
    assert first["hsi_20d_available"] == 2
    assert first["hsi_volatility_available"] == 2
    assert first["future_row_poisoning"] == "PASS"
    assert first["determinism"] == "PASS"
    assert first["blind_2025_y_accessed"] is False
    with (output_dir / "hsi_readiness_438.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        readiness = list(csv.DictReader(handle))
    assert [row["case_id"] for row in readiness] == ["case-a", "case-b"]
