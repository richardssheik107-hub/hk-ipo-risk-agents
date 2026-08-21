from __future__ import annotations

import csv
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

from scripts import run_v04_pr_a as pr_a


def test_committed_official_cohort_matches_frozen_pr_a_universe() -> None:
    metadata = pr_a.load_official_metadata(Path("data/catalog"))
    assert len(metadata) == pr_a.EXPECTED_FULL_COHORT_SIZE == 438
    assert Counter(item.cohort_year for item in metadata) == {
        2020: 125,
        2021: 97,
        2022: 78,
        2023: 68,
        2024: 70,
    }
    assert all(item.cohort_year < 2025 for item in metadata)
    assert len({item.case_id for item in metadata}) == len(metadata)
    assert all(item.official_ipo_universe_member for item in metadata)


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


def test_oracle_manifest_hash_is_stable_across_hash_seeds() -> None:
    command = (
        "from ipo_risk.modeling.oracle_document import "
        "ORACLE_DOCUMENT_FEATURE_MANIFEST_HASH; "
        "print(ORACLE_DOCUMENT_FEATURE_MANIFEST_HASH)"
    )
    hashes = {
        subprocess.check_output(
            [sys.executable, "-c", command],
            env={**os.environ, "PYTHONHASHSEED": seed},
            text=True,
        ).strip()
        for seed in ("1", "2", "3")
    }
    assert len(hashes) == 1


def test_conflict_safe_json_reuses_tuple_payload_after_roundtrip(
    tmp_path: Path,
) -> None:
    target = tmp_path / "artifact.json"
    payload = {"feature_names": ("a", "b"), "feature_values": (1, 2)}

    assert pr_a._write_json_conflict_safe(target, payload, resume=False) == "created"
    assert pr_a._write_json_conflict_safe(target, payload, resume=True) == "reused"
