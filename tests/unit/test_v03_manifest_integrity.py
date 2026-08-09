"""Tests for golden-case manifest integrity checks (member #2 data validation)."""

from __future__ import annotations

import csv
from pathlib import Path

from ipo_risk.evaluation.v03_manifest import (
    REQUIRED_COLUMNS,
    validate_manifest_integrity,
)

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "v03_golden_cases"
    / "v03_golden_case_manifest.csv"
)

_BASE_ROW = {
    "case_id": "ipo_2020_00368",
    "stock_code": "0368.HK",
    "company_name": "德合集团",
    "document_id": "ipo_2020_00368",
    "risk_code": "continuous_loss",
    "applicable": "true",
    "gold_page": "120",
    "exact_text": "本公司持续录得亏损",
    "expected_status": "needs_review",
    "expected_level": "medium",
    "reviewer": "r1",
    "second_reviewer": "r2",
    "review_status": "double_reviewed",
    "notes": "primary",
}


def _write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(REQUIRED_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_prospectus(path: Path, rows: list[dict[str, str]]) -> None:
    fields = ["case_id", "dataset_split", "sha256", "relative_path"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def test_synthetic_fixture_passes_integrity() -> None:
    assert validate_manifest_integrity(FIXTURE) == []


def test_detects_inconsistent_case_identity(tmp_path: Path) -> None:
    manifest = tmp_path / "m.csv"
    row_a = dict(_BASE_ROW)
    row_b = dict(_BASE_ROW, risk_code="revenue_growth", company_name="别的公司")
    _write_manifest(manifest, [row_a, row_b])
    errors = validate_manifest_integrity(manifest)
    assert any("inconsistent" in error for error in errors)


def test_detects_duplicate_judgement(tmp_path: Path) -> None:
    manifest = tmp_path / "m.csv"
    _write_manifest(manifest, [dict(_BASE_ROW), dict(_BASE_ROW)])
    errors = validate_manifest_integrity(manifest)
    assert any("duplicate judgement" in error for error in errors)


def test_bars_2025_blind_test_case(tmp_path: Path) -> None:
    manifest = tmp_path / "m.csv"
    blind = dict(_BASE_ROW, case_id="ipo_2025_00999", document_id="ipo_2025_00999")
    _write_manifest(manifest, [blind])
    errors = validate_manifest_integrity(manifest)
    assert any("2025 blind-test" in error for error in errors)


def test_cross_check_flags_bad_split_and_sha(tmp_path: Path) -> None:
    manifest = tmp_path / "m.csv"
    _write_manifest(manifest, [dict(_BASE_ROW)])
    prospectus = tmp_path / "p.csv"
    _write_prospectus(
        prospectus,
        [{
            "case_id": "ipo_2020_00368",
            "dataset_split": "blind_test",  # not allowed for golden cases
            "sha256": "tooshort",
            "relative_path": "2020/x.pdf",
        }],
    )
    errors = validate_manifest_integrity(
        manifest, prospectus_manifest_path=prospectus
    )
    assert any("not allowed for golden cases" in error for error in errors)
    assert any("SHA-256" in error for error in errors)


def test_cross_check_passes_for_valid_real_case(tmp_path: Path) -> None:
    manifest = tmp_path / "m.csv"
    _write_manifest(manifest, [dict(_BASE_ROW)])
    pdf = tmp_path / "2020" / "x.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4 test")
    prospectus = tmp_path / "p.csv"
    _write_prospectus(
        prospectus,
        [{
            "case_id": "ipo_2020_00368",
            "dataset_split": "development",
            "sha256": "a" * 64,
            "relative_path": "2020/x.pdf",
        }],
    )
    errors = validate_manifest_integrity(
        manifest, prospectus_manifest_path=prospectus, data_root=tmp_path
    )
    assert errors == []
