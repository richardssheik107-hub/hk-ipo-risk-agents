"""Governed Extended context must reach a new IPO, without unblocking industry."""

from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from ipo_risk.agents.dynamic_market_context import DynamicPITMarketContextProvider
from ipo_risk.market.csmar_hsi import CSMAR_HSI_REQUIRED_COLUMNS, sha256_file
from ipo_risk.market.dynamic_extended import (
    EXTENDED_ONLY_FEATURE_ORDER,
    INDUSTRY_MAPPING_PIT_BLOCKED,
    OUTSIDE_GOVERNED_SPLIT,
    DynamicExtendedMarketError,
    DynamicExtendedMarketSource,
)
from ipo_risk.market.official_market_sources import (
    HKEX_TURNOVER_COLUMNS,
    HSCI_EXPECTED_IDS,
)
from ipo_risk.schemas import IPOProfile
from ipo_risk.schemas.final_supervision import ChannelStatus
from ..dynamic_market_fixture import prior_ipo_rows, write_bridge

SESSION_COUNT = 40
FIRST_SESSION = date(2021, 12, 1)
# Sessions run daily from FIRST_SESSION, so the cutoff sits after all of them.
TARGET = FIRST_SESSION + timedelta(days=SESSION_COUNT + 5)
ARCHIVE_SHA = "a" * 64
SOURCE_SHA = "b" * 64


def _sessions() -> list[date]:
    return [FIRST_SESSION + timedelta(days=offset) for offset in range(SESSION_COUNT)]


def _write_hsi(root: Path) -> tuple[Path, Path]:
    csv_path = root / "hsi_normalized.csv"
    rows = []
    for index, session in enumerate(_sessions()):
        close = f"{20000 + index * 25}"
        rows.append({
            "reference_id": "HSI",
            "trading_date": session.isoformat(),
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "constituent_volume": "123",
            "index_return": "0.01",
            "source_record_id": f"project:CSMAR:IDX_Gidxtrd.xls:HSI:{session.isoformat()}",
            "source_id": "CSMAR",
            "source_version": "csmar_hsi_daily_close_v1:" + ARCHIVE_SHA[:12] + ":" + SOURCE_SHA[:12],
            "project_generated_identity": "true",
        })
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSMAR_HSI_REQUIRED_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    manifest_path = root / "csmar_hsi_source_manifest.json"
    manifest_path.write_text(json.dumps({
        "manifest_version": "csmar_hsi_source_manifest_v1",
        "source_name": "CSMAR",
        "dataset_name": "国际指数日行情文件",
        "reference_id": "HSI",
        "series_name": "恒生指数",
        "frequency": "daily",
        "series_type": "unspecified_by_delivered_metadata",
        "series_type_status": "SERIES_TYPE_REQUIRES_METADATA_CONFIRMATION",
        "source_file_name": "IDX_Gidxtrd.xls",
        "source_archive_name": "国际指数日行情文件.zip",
        "source_archive_sha256": ARCHIVE_SHA,
        "source_file_sha256": SOURCE_SHA,
        "normalized_schema_version": "csmar_hsi_daily_close_v1",
        "normalized_file_sha256": sha256_file(csv_path),
        "row_count": len(rows),
        "coverage_start": rows[0]["trading_date"],
        "coverage_end": rows[-1]["trading_date"],
        "duplicate_count": 0,
        "null_close_count": 0,
        "invalid_close_count": 0,
        "parse_error_count": 0,
        "retrieval_metadata": {"workbook_open_mode": "read_only"},
        "license_notice": "仅供西安交通大学使用",
        "project_generated_identity": True,
    }, ensure_ascii=False), encoding="utf-8")
    return csv_path, manifest_path


def _write_turnover(root: Path) -> tuple[Path, Path]:
    csv_path = root / "turnover_normalized.csv"
    sessions = _sessions()
    rows = [
        {
            "trading_date": session.isoformat(),
            "total_market_turnover": 1020 + index,
            "currency": "HKD",
            "unit": "HKD",
            "market_scope": "Main Board + GEM; all securities in HKEX archive",
            "main_board_turnover_hkd": 1000 + index,
            "gem_turnover_hkd": 20,
        }
        for index, session in enumerate(sessions)
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HKEX_TURNOVER_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    manifest_path = root / "v04_c_external_market_source_manifest.json"
    manifest_path.write_text(json.dumps({
        "manifest_version": "v04_c_external_market_source_manifest_v1",
        "industry_taxonomy": {"production_mapping_status": INDUSTRY_MAPPING_PIT_BLOCKED},
        # Declared so the manifest validates; the dynamic Extended source never
        # constructs an HSCI provider, because industry stays PIT-blocked.
        "hsci_industry_daily_close": {
            "status": "ACCEPT_PARTIAL_COVERAGE",
            "authority": "Hang Seng Indexes Company Limited",
            "authoritative_level": "PRIMARY_OFFICIAL",
            "target_series_count": 12,
            "found_series_count": 12,
            "accepted_series_count": 12,
            "row_count": 12 * len(rows),
            "rows_per_series": len(rows),
            "coverage_start": rows[0]["trading_date"],
            "coverage_end": rows[-1]["trading_date"],
            "frequency": "daily",
            "fields": ["benchmark_id", "trading_date", "close"],
            "series_type": "price_index",
            "pit_safe": True,
            "normalized_relative_path": "hsci_unused.csv",
            "normalized_sha256": "c" * 64,
            "series": [
                {
                    "benchmark_id": benchmark_id,
                    "benchmark_name": f"Official {benchmark_id}",
                    "internal_index_code": f"00011.{index:02d}",
                    "source_url": f"https://example.test/{benchmark_id}.json",
                    "dataset": "test official chart",
                    "coverage_start": rows[0]["trading_date"],
                    "coverage_end": rows[-1]["trading_date"],
                    "row_count": len(rows),
                    "raw_sha256": "d" * 64,
                    "download_timestamp_utc": "2026-08-23T00:00:00+00:00",
                }
                for index, benchmark_id in enumerate(sorted(HSCI_EXPECTED_IDS), start=1)
            ],
        },
        "hkex_total_market_daily_turnover": {
            "status": "ACCEPT",
            "authority": "Hong Kong Exchanges and Clearing Limited",
            "authoritative_level": "PRIMARY_OFFICIAL",
            "row_count": len(rows),
            "coverage_start": rows[0]["trading_date"],
            "coverage_end": rows[-1]["trading_date"],
            "frequency": "daily",
            "currency": "HKD",
            "unit": "HKD",
            "market_scope": "Main Board + GEM; all securities in HKEX archive",
            "measure": "daily trading value / turnover",
            "aggregation_method": "main_board_turnover_hkd + gem_turnover_hkd",
            "series_type": "total_trading_value",
            "pit_safe": True,
            "calendar_mismatch_count": 0,
            "normalized_relative_path": csv_path.name,
            "normalized_sha256": sha256_file(csv_path),
            "source_files": [],
        },
    }, ensure_ascii=False), encoding="utf-8")
    return csv_path, manifest_path


@pytest.fixture
def extended_source(tmp_path) -> DynamicExtendedMarketSource:
    root = tmp_path / "market_reference"
    root.mkdir(parents=True)
    hsi_csv, hsi_manifest = _write_hsi(root)
    turnover_csv, external_manifest = _write_turnover(root)
    return DynamicExtendedMarketSource(
        hsi_normalized_csv=hsi_csv,
        turnover_normalized_csv=turnover_csv,
        hsi_manifest=hsi_manifest,
        external_manifest=external_manifest,
    )


def test_a_new_listing_date_gets_governed_benchmark_and_turnover_context(
    extended_source: DynamicExtendedMarketSource,
) -> None:
    """No case_id is involved: the cutoff alone selects the history."""

    result = extended_source.context(listing_date=TARGET)
    by_name = {item.name: item for item in result.observations}
    assert set(by_name) == set(EXTENDED_ONLY_FEATURE_ORDER)
    for name in ("hsi_return_5d", "hsi_return_20d", "market_volatility_20d",
                 "market_turnover_20d_mean"):
        assert by_name[name].availability == "available", name
        assert by_name[name].value is not None
        assert by_name[name].source == "dynamic_market_x_extended"
    assert result.provenance["extended_pit_cutoff_date"] == TARGET.isoformat()
    assert result.provenance["extended_available_observation_count"] == 4


def test_industry_returns_stay_pit_blocked_and_are_never_computed(
    extended_source: DynamicExtendedMarketSource,
) -> None:
    """The delivered classification has no effective dates; nothing unblocks it."""

    by_name = {
        item.name: item
        for item in extended_source.context(listing_date=TARGET).observations
    }
    for name in ("industry_return_5d", "industry_return_20d"):
        assert by_name[name].availability == "unavailable"
        assert by_name[name].value is None
        assert by_name[name].missing_reason == INDUSTRY_MAPPING_PIT_BLOCKED


def test_benchmark_history_stops_strictly_before_the_listing_date(
    extended_source: DynamicExtendedMarketSource,
) -> None:
    sessions = _sessions()
    on_session = extended_source.context(listing_date=sessions[-1])
    assert on_session.provenance["extended_observation_date"] == sessions[-2].isoformat()


def test_a_listing_year_outside_the_frozen_split_is_explicit(
    extended_source: DynamicExtendedMarketSource,
) -> None:
    result = extended_source.context(listing_date=date(2026, 6, 1))
    by_name = {item.name: item for item in result.observations}
    assert by_name["hsi_return_5d"].missing_reason == OUTSIDE_GOVERNED_SPLIT
    assert by_name["hsi_return_5d"].value is None
    assert by_name["industry_return_5d"].missing_reason == INDUSTRY_MAPPING_PIT_BLOCKED


def test_a_missing_cache_is_an_error_not_a_silent_empty_series(tmp_path) -> None:
    source = DynamicExtendedMarketSource(
        hsi_normalized_csv=tmp_path / "absent.csv",
        turnover_normalized_csv=tmp_path / "absent2.csv",
        hsi_manifest=tmp_path / "absent3.json",
        external_manifest=tmp_path / "absent4.json",
    )
    with pytest.raises(DynamicExtendedMarketError):
        source.context(listing_date=TARGET)


def test_the_dynamic_channel_carries_core_and_extended_together(
    tmp_path, extended_source: DynamicExtendedMarketSource
) -> None:
    bridge = write_bridge(
        tmp_path / "catalog",
        prior_ipo_rows(first_listing=date(2020, 1, 6), count=140),
    )
    provider = DynamicPITMarketContextProvider(
        official_bridge_path=bridge, extended_source=extended_source
    )
    view = provider.context(IPOProfile(
        company_name="Fresh", stock_code="9999.HK",
        listing_date=TARGET, industry="软件服务",
    ))
    assert view.status is ChannelStatus.AVAILABLE
    assert len(view.observations) == 21
    assert len({item.name for item in view.observations}) == 21
    assert view.provenance["extended_status"] == "available"
    assert view.provenance["extended_pit_cutoff_date"] == TARGET.isoformat()
    # Core identity is untouched by the Extended attachment.
    assert view.provenance["runtime_path"] == "dynamic_pit"
    assert view.feature_manifest_hash


def test_an_unreadable_extended_cache_does_not_take_core_down(tmp_path) -> None:
    bridge = write_bridge(
        tmp_path / "catalog",
        prior_ipo_rows(first_listing=date(2020, 1, 6), count=140),
    )
    provider = DynamicPITMarketContextProvider(
        official_bridge_path=bridge,
        extended_source=DynamicExtendedMarketSource(
            hsi_normalized_csv=tmp_path / "absent.csv",
            turnover_normalized_csv=tmp_path / "absent2.csv",
            hsi_manifest=tmp_path / "absent3.json",
            external_manifest=tmp_path / "absent4.json",
        ),
    )
    view = provider.context(IPOProfile(
        company_name="Fresh", stock_code="9999.HK",
        listing_date=TARGET, industry="软件服务",
    ))
    assert view.status is ChannelStatus.AVAILABLE
    assert len(view.observations) == 15
    assert view.provenance["extended_status"] == "source_error"


def test_an_unconfigured_extended_source_adds_no_observation(tmp_path) -> None:
    """Absent is absent: no Extended name appears at all, not even as null."""

    bridge = write_bridge(
        tmp_path / "catalog",
        prior_ipo_rows(first_listing=date(2020, 1, 6), count=140),
    )
    view = DynamicPITMarketContextProvider(official_bridge_path=bridge).context(
        IPOProfile(
            company_name="Fresh", stock_code="9999.HK",
            listing_date=TARGET, industry="软件服务",
        )
    )
    assert len(view.observations) == 15
    assert view.provenance["extended_status"] == "not_configured"
    assert not {item.name for item in view.observations} & set(EXTENDED_ONLY_FEATURE_ORDER)
