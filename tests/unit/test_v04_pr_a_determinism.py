from __future__ import annotations

import csv
from pathlib import Path

from scripts import run_v04_pr_a as pr_a


def test_coverage_hash_is_stable_after_csv_roundtrip(tmp_path: Path) -> None:
    rows = [
        {
            "case_id": "ipo_2023_00368",
            "official_listing_year": 2023,
            "production_document_available": "true",
            "oracle_document_available": "false",
        }
    ]
    normalized = pr_a._csv_string_rows(rows)
    target = tmp_path / "coverage.csv"
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(normalized[0]))
        writer.writeheader()
        writer.writerows(normalized)

    with target.open("r", encoding="utf-8", newline="") as handle:
        reread = list(csv.DictReader(handle))

    assert reread == normalized
    assert pr_a._content_hash(reread) == pr_a._content_hash(normalized)
