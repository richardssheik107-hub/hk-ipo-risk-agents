"""Tests for the PR-F product-handoff CLI case-list parser."""

from __future__ import annotations

import json
from pathlib import Path
import runpy

import pytest


_MODULE = runpy.run_path("scripts/build_v04_pr_f_product_handoff.py")
_case_ids = _MODULE["_case_ids"]


def test_case_ids_accepts_the_governed_demo_case_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "cases.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_version": "test",
                "cases": [
                    {"case_id": "ipo_2024_02410", "company_name": "A"},
                    {"case_id": "ipo_2024_02460", "company_name": "B"},
                    {"case_id": "ipo_2024_01318", "company_name": "C"},
                ],
            }
        ),
        encoding="utf-8",
    )

    assert _case_ids([], manifest) == [
        "ipo_2024_02410",
        "ipo_2024_02460",
        "ipo_2024_01318",
    ]


def test_case_ids_preserves_order_and_deduplicates_across_sources(tmp_path: Path) -> None:
    case_list = tmp_path / "cases.json"
    case_list.write_text(
        json.dumps(
            [
                "ipo_2024_02410",
                {"case_id": "ipo_2024_02460"},
                "ipo_2024_02410",
            ]
        ),
        encoding="utf-8",
    )

    assert _case_ids(["ipo_2024_01318", "ipo_2024_02410"], case_list) == [
        "ipo_2024_01318",
        "ipo_2024_02410",
        "ipo_2024_02460",
    ]


def test_case_ids_rejects_a_json_object_without_cases(tmp_path: Path) -> None:
    case_list = tmp_path / "cases.json"
    case_list.write_text(json.dumps({"items": []}), encoding="utf-8")

    with pytest.raises(ValueError, match="cases array"):
        _case_ids([], case_list)


def test_case_ids_rejects_object_entries_without_case_id(tmp_path: Path) -> None:
    case_list = tmp_path / "cases.json"
    case_list.write_text(json.dumps([{"company_name": "missing"}]), encoding="utf-8")

    with pytest.raises(ValueError, match="contain case_id"):
        _case_ids([], case_list)
