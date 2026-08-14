"""Integrity tests for the frozen Expert Golden 100 taskset."""

from __future__ import annotations

import csv
from collections import Counter
import importlib.util
from pathlib import Path


ROOT = Path("docs/annotation/gpt_expert_v1_1")


def _validate_taskset():
    path = Path("scripts/validate_expert_taskset.py")
    spec = importlib.util.spec_from_file_location("validate_expert_taskset", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_taskset()


def _build_taskset(output_root: Path):
    path = Path("scripts/build_expert_golden_taskset.py")
    spec = importlib.util.spec_from_file_location("build_expert_golden_taskset", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_taskset(output_root=output_root)


def _rows(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_taskset_has_fixed_indices_years_and_splits() -> None:
    rows = _rows("expert_golden_100_taskset.csv")
    assert [int(row["task_index"]) for row in rows] == list(range(1, 101))
    assert Counter(row["source_year"] for row in rows) == {
        "2020": 20, "2021": 20, "2022": 20, "2023": 20, "2024": 20,
    }
    assert Counter(row["dataset_split"] for row in rows) == {
        "development": 80,
        "validation": 19,
        "development_exception": 1,
    }


def test_taskset_validator_passes_and_selects_no_2025() -> None:
    result = _validate_taskset()
    assert result["cases"] == 100
    assert result["risk_inspections"] == 800
    assert result["selected_2025"] == 0
    assert result["all_packets_blank"] is True
    assert result["raw_pdf_count"] == 0


def test_taskset_and_source_manifest_have_identical_case_mapping() -> None:
    taskset = {row["case_id"]: row for row in _rows("expert_golden_100_taskset.csv")}
    manifest = {row["case_id"]: row for row in _rows("source_manifest.csv")}
    assert set(taskset) == set(manifest)
    for case_id, row in taskset.items():
        assert row["stock_code"] == manifest[case_id]["stock_code"]
        assert row["dataset_split"] == manifest[case_id]["dataset_split"]
        assert row["packet_path"] == manifest[case_id]["packet_path"]


def test_generator_resolves_all_frozen_stocks_from_catalog_metadata(tmp_path: Path) -> None:
    result = _build_taskset(tmp_path / "taskset")
    assert result == {
        "cases": 100,
        "risk_inspections": 800,
        "development": 80,
        "validation": 19,
        "development_exception": 1,
    }
