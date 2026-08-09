"""Integration tests for the v0.3 batch runner (member #2, V3-10)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ipo_risk.evaluation.batch import BLIND_TEST_TOKEN, run_batch

CATALOG_DIR = Path(__file__).resolve().parents[2] / "data" / "catalog"


def test_mock_batch_runs_and_writes_artifacts(tmp_path: Path) -> None:
    report = run_batch(
        catalog_dir=CATALOG_DIR,
        output_dir=tmp_path / "out",
        case_ids=["ipo_2020_00368", "ipo_2020_00589"],
    )
    counts = report.counts()
    assert counts.get("completed", 0) + counts.get("partial", 0) == 2

    out = tmp_path / "out"
    assert (out / "run_manifest.json").is_file()
    assert (out / "case_summary.csv").is_file()
    assert (out / "failure_report.csv").is_file()

    lines = (out / "analysis_results.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["company_name"] == "德合集团"

    manifest = json.loads((out / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["code_revision"]  # a SHA or "unknown", never empty
    assert manifest["selected_case_count"] == 2
    assert manifest["blind_test_included"] is False


def test_blind_test_is_protected_by_default(tmp_path: Path) -> None:
    # ipo_2025_* cases are in the blind_test split.
    blind_case = next(
        cid for cid in _case_ids_for_split("blind_test")
    )
    report = run_batch(
        catalog_dir=CATALOG_DIR,
        output_dir=tmp_path / "out",
        case_ids=[blind_case],
    )
    assert report.counts() == {"protected": 1}
    # Nothing was executed or persisted for the protected case.
    assert not (tmp_path / "out" / "cases" / f"{blind_case}.json").exists()


def test_blind_test_requires_exact_token(tmp_path: Path) -> None:
    blind_case = next(iter(_case_ids_for_split("blind_test")))
    with pytest.raises(PermissionError):
        run_batch(
            catalog_dir=CATALOG_DIR,
            output_dir=tmp_path / "out",
            case_ids=[blind_case],
            include_blind_test=True,
            blind_test_token="wrong-token",
        )


def test_unknown_case_is_isolated_not_fatal(tmp_path: Path) -> None:
    report = run_batch(
        catalog_dir=CATALOG_DIR,
        output_dir=tmp_path / "out",
        case_ids=["ipo_2020_00368", "ipo_9999_00000"],
    )
    counts = report.counts()
    assert counts.get("failed") == 1
    assert counts.get("completed", 0) + counts.get("partial", 0) == 1


def test_resume_skips_existing_then_overwrites(tmp_path: Path) -> None:
    out = tmp_path / "out"
    first = run_batch(catalog_dir=CATALOG_DIR, output_dir=out, case_ids=["ipo_2020_00368"])
    assert first.counts().get("completed", 0) + first.counts().get("partial", 0) == 1

    resumed = run_batch(catalog_dir=CATALOG_DIR, output_dir=out, case_ids=["ipo_2020_00368"])
    assert resumed.counts() == {"skipped": 1}

    overwritten = run_batch(
        catalog_dir=CATALOG_DIR, output_dir=out, case_ids=["ipo_2020_00368"], overwrite=True
    )
    assert overwritten.counts().get("skipped") is None


def _case_ids_for_split(split: str) -> list[str]:
    from ipo_risk.providers.catalog import CatalogIPODataProvider

    provider = CatalogIPODataProvider(CATALOG_DIR)
    return [
        row["case_id"] for row in provider._rows if row.get("dataset_split") == split
    ]
