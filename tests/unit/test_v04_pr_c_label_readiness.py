from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from ipo_risk.market.label_readiness import build_label_readiness
from ipo_risk.providers.filtered_eod_v2 import FilteredEODV2MarketDataProvider
from ipo_risk.schemas.market import (
    IPOMarketMetadata,
    MarketDataProvenance,
    MarketExchange,
)
from scripts.audit_v04_pr_c_label_readiness import write_readiness_outputs
from tests.unit.test_filtered_eod_v2_provider import _fixture


def _provider(tmp_path: Path) -> FilteredEODV2MarketDataProvider:
    catalog, _, cache = _fixture(tmp_path)
    return FilteredEODV2MarketDataProvider(
        store_path=cache / "v04_ipo_eod.csv",
        manifest_path=cache / "v04_ipo_eod.manifest.json",
        catalog_dir=catalog,
        expected_case_count=4,
    )


def test_label_readiness_keeps_every_case_and_separates_coverage(
    tmp_path: Path,
) -> None:
    provider = _provider(tmp_path)
    first = build_label_readiness(provider, expected_case_count=4)
    second = build_label_readiness(provider, expected_case_count=4)
    summary = first["summary"]

    assert len(first["records"]) == summary["official_case_count"] == 4
    assert summary["eod_ready_count"] == 3
    assert summary["eod_5d_session_ready_count"] == 3
    assert summary["base_price_ready_count"] == 3
    assert summary["one_day_label_available_count"] == 2
    assert summary["five_day_label_available_count"] == 2
    assert summary["missing_reason_counts"] == {
        "1d": {"missing_base_price": 1, "no_eligible_session": 1},
        "5d": {"missing_base_price": 1, "no_eligible_session": 1},
    }
    assert summary["eod_coverage_is_not_label_coverage"] is True
    assert summary["audit_failure_count"] == 0
    assert summary["blind_2025_y_accessed"] is False
    assert summary["coverage_content_hash"] == second["summary"][
        "coverage_content_hash"
    ]

    by_case = {row["case_id"]: row for row in first["records"]}
    assert by_case["ipo_2021_0002"]["5d_missing_reason"] == "no_eligible_session"
    assert by_case["ipo_2022_0003"]["5d_missing_reason"] == "missing_base_price"
    assert by_case["ipo_2020_0001"]["5d_target_trading_date"] == "2020-01-14"


def test_readiness_outputs_are_utf8_and_portable(tmp_path: Path) -> None:
    result = build_label_readiness(_provider(tmp_path), expected_case_count=4)
    output = tmp_path / "out"
    write_readiness_outputs(output, result)
    assert (output / "coverage.csv").read_text(encoding="utf-8").startswith(
        "case_id,stock_code"
    )
    summary_text = (output / "summary.json").read_text(encoding="utf-8")
    assert "filtered_store_filename" in summary_text
    assert str(tmp_path) not in summary_text


def test_readiness_rejects_2025_blind_metadata() -> None:
    blind = IPOMarketMetadata(
        case_id="ipo_2025_0001",
        stock_code="0001.HK",
        cohort_year=2025,
        listing_date=date(2025, 1, 2),
        listing_price=Decimal("10"),
        exchange=MarketExchange.HKEX,
        source="fixture",
        provenance=MarketDataProvenance(source="fixture", dataset_version="v1"),
    )

    class BlindProvider:
        def iter_listing_metadata(self):
            return (blind,)

    with pytest.raises(ValueError, match="2025 Blind"):
        build_label_readiness(BlindProvider(), expected_case_count=None)  # type: ignore[arg-type]
