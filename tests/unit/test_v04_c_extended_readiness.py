from __future__ import annotations

import json
from pathlib import Path

from scripts.run_v04_c_extended_readiness import (
    MAPPING_PIT_BLOCKED,
    _conditional_reason,
    load_mapping,
)


def test_mapping_draft_is_deterministic_and_production_blocked() -> None:
    path = Path("data/catalog/v04_c_hsics_benchmark_mapping_draft.csv")
    first = load_mapping(path)
    second = load_mapping(path)
    assert first == second
    assert len(first) == 12
    assert first["00"]["benchmark_id"] == "HSCIE"
    assert first["80"]["benchmark_id"] == "HSCIC"
    assert "99" not in first
    assert {row["pit_status"] for row in first.values()} == {"PIT_BLOCKED"}


def test_conditional_industry_missing_reasons_are_specific() -> None:
    assert (
        _conditional_reason(
            industry_code="", benchmark_id="", observation_count=0, sessions=5
        )
        == "MISSING_INDUSTRY_CLASSIFICATION"
    )
    assert (
        _conditional_reason(
            industry_code="99", benchmark_id="", observation_count=0, sessions=5
        )
        == "MISSING_INDUSTRY_MAPPING"
    )
    assert (
        _conditional_reason(
            industry_code="00", benchmark_id="HSCIE", observation_count=0, sessions=5
        )
        == "BENCHMARK_HISTORY_NOT_YET_STARTED"
    )
    assert (
        _conditional_reason(
            industry_code="00", benchmark_id="HSCIE", observation_count=5, sessions=5
        )
        == "INSUFFICIENT_5D_HISTORY"
    )
    assert (
        _conditional_reason(
            industry_code="00", benchmark_id="HSCIE", observation_count=20, sessions=20
        )
        == "INSUFFICIENT_20D_HISTORY"
    )
    assert not _conditional_reason(
        industry_code="00", benchmark_id="HSCIE", observation_count=21, sessions=20
    )


def test_real_438_aggregate_preserves_contract_and_blind_gate() -> None:
    summary = json.loads(
        Path("data/catalog/v04_c_extended_readiness_summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["official_cases"] == 438
    assert summary["silent_drops"] == 0
    assert summary["industry_mapping_pit_status"] == MAPPING_PIT_BLOCKED
    assert summary["hsci_series_accepted"] == 12
    assert summary["hsci_production_5d_available"] == 0
    assert summary["hsci_production_20d_available"] == 0
    assert summary["conditional_static_mapping_5d_available"] == 243
    assert summary["conditional_static_mapping_20d_available"] == 242
    assert summary["turnover_20d_available"] == 438
    assert summary["extended_raw_feature_count"] == 10
    assert summary["extended_position_count"] == 20
    assert summary["full_10_raw_available"] == 0
    assert summary["partial_available"] == 438
    assert summary["future_row_poisoning"] == "PASS"
    assert summary["determinism"] == "PASS"
    assert summary["blind_2025_y_accessed"] is False
    decision = summary["hsci_history_backfill_decision"]
    assert decision["affected_cases"] == 190
    assert decision["affected_years"] == [2020, 2021]
    assert decision["validation_set_impact"] == 0
    assert decision["purchase_recommended"] == "NO"
