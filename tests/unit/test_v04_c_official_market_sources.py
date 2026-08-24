from __future__ import annotations

import csv
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from ipo_risk.market.features import PreListingMarketFeatureEngine
from ipo_risk.market.official_market_sources import (
    HSCI_COLUMNS,
    HSCI_EXPECTED_IDS,
    HKEX_TURNOVER_COLUMNS,
    ExternalMarketSourceManifest,
    OfficialHSCIProvider,
    OfficialHKEXTurnoverProvider,
    OfficialMarketSourceError,
    sha256_file,
)
from ipo_risk.schemas.market import MarketDataProvenance, expected_market_split
from ipo_risk.schemas.market_features import (
    MarketFeatureAvailability,
    MarketReferenceBar,
    PreListingMarketFeatureContext,
)


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _source_manifest(
    hsci_path: Path,
    turnover_path: Path,
    *,
    rows_per_series: int,
) -> ExternalMarketSourceManifest:
    start = date(2021, 8, 19)
    end = start + timedelta(days=rows_per_series - 1)
    series = [
        {
            "benchmark_id": benchmark_id,
            "benchmark_name": f"Official {benchmark_id}",
            "internal_index_code": f"00011.{index:02d}",
            "source_url": f"https://example.test/{benchmark_id}.json",
            "dataset": "test official chart",
            "coverage_start": start,
            "coverage_end": end,
            "row_count": rows_per_series,
            "raw_sha256": "a" * 64,
            "download_timestamp_utc": "2026-08-23T00:00:00+00:00",
        }
        for index, benchmark_id in enumerate(sorted(HSCI_EXPECTED_IDS), start=1)
    ]
    return ExternalMarketSourceManifest.model_validate(
        {
            "manifest_version": "v04_c_external_market_source_manifest_v1",
            "industry_taxonomy": {"production_mapping_status": "INDUSTRY_MAPPING_PIT_BLOCKED"},
            "hsci_industry_daily_close": {
                "status": "ACCEPT_PARTIAL_COVERAGE",
                "authority": "Hang Seng Indexes Company Limited",
                "authoritative_level": "PRIMARY_OFFICIAL",
                "target_series_count": 12,
                "found_series_count": 12,
                "accepted_series_count": 12,
                "row_count": rows_per_series * 12,
                "rows_per_series": rows_per_series,
                "coverage_start": start,
                "coverage_end": end,
                "frequency": "daily",
                "fields": list(HSCI_COLUMNS[:3]),
                "series_type": "price_index",
                "pit_safe": True,
                "normalized_relative_path": hsci_path.name,
                "normalized_sha256": sha256_file(hsci_path),
                "series": series,
            },
            "hkex_total_market_daily_turnover": {
                "status": "ACCEPT",
                "authority": "Hong Kong Exchanges and Clearing Limited",
                "authoritative_level": "PRIMARY_OFFICIAL",
                "row_count": 21,
                "coverage_start": "2020-01-01",
                "coverage_end": "2020-01-21",
                "frequency": "daily",
                "currency": "HKD",
                "unit": "HKD",
                "market_scope": "Main Board + GEM; all securities in HKEX archive",
                "measure": "daily trading value / turnover",
                "aggregation_method": "main_board_turnover_hkd + gem_turnover_hkd",
                "series_type": "total_trading_value",
                "pit_safe": True,
                "calendar_mismatch_count": 0,
                "normalized_relative_path": turnover_path.name,
                "normalized_sha256": sha256_file(turnover_path),
                "source_files": [],
            },
        }
    )


@pytest.fixture
def governed_sources(tmp_path: Path) -> tuple[Path, Path, ExternalMarketSourceManifest]:
    hsci_path = tmp_path / "hsci.csv"
    hsci_rows: list[dict[str, object]] = []
    start = date(2021, 8, 19)
    for benchmark_id in sorted(HSCI_EXPECTED_IDS):
        for offset in range(21):
            hsci_rows.append(
                {
                    "benchmark_id": benchmark_id,
                    "trading_date": (start + timedelta(days=offset)).isoformat(),
                    "close": 100 + offset,
                    "series_type": "price_index",
                    "source_owner": "Hang Seng Indexes Company Limited",
                }
            )
    _write_csv(hsci_path, HSCI_COLUMNS, hsci_rows)

    turnover_path = tmp_path / "turnover.csv"
    turnover_rows = [
        {
            "trading_date": (date(2020, 1, 1) + timedelta(days=offset)).isoformat(),
            "total_market_turnover": 1020 + offset,
            "currency": "HKD",
            "unit": "HKD",
            "market_scope": "Main Board + GEM; all securities in HKEX archive",
            "main_board_turnover_hkd": 1000 + offset,
            "gem_turnover_hkd": 20,
        }
        for offset in range(21)
    ]
    _write_csv(turnover_path, HKEX_TURNOVER_COLUMNS, turnover_rows)
    return hsci_path, turnover_path, _source_manifest(
        hsci_path, turnover_path, rows_per_series=21
    )


def test_hsci_provider_accepts_exact_12_series_and_exclusive_cutoff(
    governed_sources: tuple[Path, Path, ExternalMarketSourceManifest],
) -> None:
    hsci_path, _, manifest = governed_sources
    provider = OfficialHSCIProvider(hsci_path, manifest)
    assert {item.reference_id for item in provider.iter_all_bars()} == HSCI_EXPECTED_IDS
    cutoff = date(2021, 8, 25)
    bars = provider.get_industry_bars("HSCIE", end_date_exclusive=cutoff)
    assert bars
    assert all(item.trading_date < cutoff for item in bars)
    with pytest.raises(OfficialMarketSourceError, match="cannot serve"):
        provider.get_industry_bars("HSC", end_date_exclusive=cutoff)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [("close", "0", "positive"), ("benchmark_id", "HSC", "unexpected HSCI")],
)
def test_hsci_loader_fails_closed_on_invalid_rows(
    governed_sources: tuple[Path, Path, ExternalMarketSourceManifest],
    field: str,
    value: str,
    message: str,
) -> None:
    hsci_path, _, manifest = governed_sources
    with hsci_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows[0][field] = value
    _write_csv(hsci_path, HSCI_COLUMNS, rows)
    manifest = manifest.model_copy(
        update={
            "hsci_industry_daily_close": manifest.hsci_industry_daily_close.model_copy(
                update={"normalized_sha256": sha256_file(hsci_path)}
            )
        }
    )
    with pytest.raises(OfficialMarketSourceError, match=message):
        OfficialHSCIProvider(hsci_path, manifest)


def test_hsci_loader_rejects_duplicate_and_hash_mismatch(
    governed_sources: tuple[Path, Path, ExternalMarketSourceManifest],
) -> None:
    hsci_path, _, manifest = governed_sources
    original = hsci_path.read_text(encoding="utf-8")
    hsci_path.write_text(original + original.splitlines()[1] + "\n", encoding="utf-8")
    duplicate_manifest = manifest.model_copy(
        update={
            "hsci_industry_daily_close": manifest.hsci_industry_daily_close.model_copy(
                update={
                    "normalized_sha256": sha256_file(hsci_path),
                    "row_count": manifest.hsci_industry_daily_close.row_count + 1,
                }
            )
        }
    )
    with pytest.raises(OfficialMarketSourceError, match="duplicate HSCI"):
        OfficialHSCIProvider(hsci_path, duplicate_manifest)
    with pytest.raises(OfficialMarketSourceError, match="hash mismatch"):
        OfficialHSCIProvider(hsci_path, manifest)


def test_hkex_provider_validates_aggregation_and_excludes_listing_day(
    governed_sources: tuple[Path, Path, ExternalMarketSourceManifest],
) -> None:
    _, turnover_path, manifest = governed_sources
    provider = OfficialHKEXTurnoverProvider(turnover_path, manifest)
    observations = provider.get_market_activity(end_date_exclusive=date(2020, 1, 21))
    assert len(observations) == 20
    assert all(item.trading_date < date(2020, 1, 21) for item in observations)
    assert observations[0].turnover == Decimal("1020")


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"currency": "USD"}, "unit/currency/scope"),
        ({"total_market_turnover": "999"}, "aggregation mismatch"),
        ({"trading_date": "2020-01-02"}, "duplicate HKEX"),
    ],
)
def test_hkex_provider_rejects_invalid_definition(
    governed_sources: tuple[Path, Path, ExternalMarketSourceManifest],
    mutation: dict[str, str],
    message: str,
) -> None:
    _, turnover_path, manifest = governed_sources
    with turnover_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows[0].update(mutation)
    _write_csv(turnover_path, HKEX_TURNOVER_COLUMNS, rows)
    manifest = manifest.model_copy(
        update={
            "hkex_total_market_daily_turnover": (
                manifest.hkex_total_market_daily_turnover.model_copy(
                    update={"normalized_sha256": sha256_file(turnover_path)}
                )
            )
        }
    )
    with pytest.raises(OfficialMarketSourceError, match=message):
        OfficialHKEXTurnoverProvider(turnover_path, manifest)


def test_turnover_feature_uses_20_sessions_and_future_poisoning_is_inert(
    governed_sources: tuple[Path, Path, ExternalMarketSourceManifest],
) -> None:
    _, turnover_path, manifest = governed_sources
    provider = OfficialHKEXTurnoverProvider(turnover_path, manifest)
    listing_date = date(2020, 1, 21)
    provenance = MarketDataProvenance(source="test", dataset_version="test-v1")
    benchmark = [
        MarketReferenceBar(
            reference_id="HSI",
            trading_date=date(2020, 1, 20),
            close=Decimal("100"),
            provenance=provenance,
        )
    ]
    context = PreListingMarketFeatureContext(
        case_id="ipo_2020_test",
        stock_code="00001.HK",
        cohort_year=2020,
        listing_date=listing_date,
        dataset_split=expected_market_split(2020),
        benchmark_reference_id="HSI",
        source="test",
        provenance=provenance,
    )
    engine = PreListingMarketFeatureEngine()
    legal = provider.get_market_activity(end_date_exclusive=listing_date)
    base = engine.build(
        context,
        benchmark_bars=benchmark,
        activity_observations=legal,
        prior_ipos=(),
    )
    poisoned = engine.build(
        context,
        benchmark_bars=benchmark,
        activity_observations=tuple(provider.iter_all_observations()),
        prior_ipos=(),
    )
    by_name = lambda snapshot: {item.name: item for item in snapshot.features}
    base_turnover = by_name(base)["market_turnover_20d_mean"]
    poisoned_turnover = by_name(poisoned)["market_turnover_20d_mean"]
    assert base_turnover.availability is MarketFeatureAvailability.AVAILABLE
    assert base_turnover.value == Decimal("1029.5")
    assert poisoned_turnover == base_turnover
