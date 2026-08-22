from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from ipo_risk.market.eod_store import OUTPUT_COLUMNS, build_store, sha256_file
from ipo_risk.market.exceptions import DuplicateMarketBarError, UnsupportedStockError
from ipo_risk.market.labels import MarketLabelGenerator
from ipo_risk.providers.competition_market import CompetitionCSVMarketDataProvider
from ipo_risk.providers.filtered_eod_v2 import FilteredEODV2MarketDataProvider
from ipo_risk.schemas.market import MarketLabelHorizon, MarketLabelMissingReason


def _write_csv(
    path: Path,
    fieldnames: list[str] | tuple[str, ...],
    rows: list[dict[str, str]],
    *,
    encoding: str = "utf-8",
) -> None:
    with path.open("w", encoding=encoding, newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _eod_row(code: str, day: str, index: int, *, close: str | None = None):
    close_value = close or str(10 + index)
    return {
        "OBJECT_ID": f"{code}-{day}",
        "S_INFO_WINDCODE": code,
        "TRADE_DT": day,
        "S_DQ_OPEN": "10",
        "S_DQ_HIGH": str(max(12, int(float(close_value)) + 1)),
        "S_DQ_LOW": "9",
        "S_DQ_CLOSE": close_value,
        "S_DQ_VOLUME": "1000",
        "S_DQ_AMOUNT": "10000",
        "S_DQ_PRECLOSE": "10",
        "S_DQ_ADJCLOSE": close_value,
    }


def _fixture(tmp_path: Path, *, duplicate: bool = False):
    catalog = tmp_path / "catalog"
    raw_root = tmp_path / "raw"
    cache = tmp_path / "cache"
    catalog.mkdir()
    raw_root.mkdir()
    bridge_rows = [
        {
            "case_id": "ipo_2020_0001",
            "stock_code_wind": "0001.HK",
            "official_listed_date": "2020-01-02",
            "official_ipo_price": "10",
            "official_match_status": "matched",
        },
        {
            "case_id": "ipo_2021_0002",
            "stock_code_wind": "0002.HK",
            "official_listed_date": "2021-01-04",
            "official_ipo_price": "10",
            "official_match_status": "matched",
        },
        {
            "case_id": "ipo_2022_0003",
            "stock_code_wind": "0003.HK",
            "official_listed_date": "2022-01-03",
            "official_ipo_price": "",
            "official_match_status": "matched",
        },
        {
            "case_id": "ipo_2024_0004",
            "stock_code_wind": "0004.HK",
            "official_listed_date": "2024-01-02",
            "official_ipo_price": "20",
            "official_match_status": "matched",
        },
    ]
    _write_csv(
        catalog / "ipo_official_master_bridge.csv",
        list(bridge_rows[0]),
        bridge_rows,
    )
    _write_csv(
        catalog / "ipo_prospectus_manifest.csv",
        ["case_id", "sha256"],
        [
            {"case_id": row["case_id"], "sha256": str(index) * 64}
            for index, row in enumerate(bridge_rows, start=1)
        ],
    )
    rows: list[dict[str, str]] = []
    gap_days = ["20200102", "20200103", "20200110", "20200113", "20200114"]
    for index, day in enumerate(gap_days, start=1):
        rows.append(_eod_row("0001.HK", day, index))
    rows.append(_eod_row("0001.HK", "20200106", 1, close="0"))
    for code, days in (
        ("0003.HK", ["20220103", "20220104", "20220105", "20220106", "20220107"]),
        ("0004.HK", ["20240102", "20240103", "20240104", "20240105", "20240108"]),
    ):
        for index, day in enumerate(days, start=1):
            rows.append(_eod_row(code, day, index))
    if duplicate:
        rows.append(dict(rows[0], OBJECT_ID="duplicate-record"))
    raw_path = raw_root / "hkshareeodprices.csv"
    _write_csv(raw_path, OUTPUT_COLUMNS, rows, encoding="gb18030")
    (catalog / "v04_source_manifest.json").write_text(
        json.dumps(
            {
                "manifest_version": "v04_source_manifest_v1",
                "entries": [
                    {"logical_id": "ipo_eod", "sha256": sha256_file(raw_path)}
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    build_store(
        data_root=raw_root,
        catalog_dir=catalog,
        cache_dir=cache,
        expected_case_count=4,
    )
    return catalog, raw_root, cache


def _filtered(catalog: Path, cache: Path, **kwargs):
    return FilteredEODV2MarketDataProvider(
        store_path=cache / "v04_ipo_eod.csv",
        manifest_path=cache / "v04_ipo_eod.manifest.json",
        catalog_dir=catalog,
        expected_case_count=4,
        **kwargs,
    )


def _bar_semantics(bar):
    return (
        bar.stock_code,
        bar.trading_date,
        bar.open,
        bar.high,
        bar.low,
        bar.close,
        bar.volume,
        bar.source,
        bar.provenance.source,
        bar.provenance.dataset_version,
        bar.provenance.source_record_id,
    )


def test_filtered_provider_validates_v2_and_preserves_object_id(tmp_path: Path) -> None:
    catalog, _, cache = _fixture(tmp_path)
    provider = _filtered(catalog, cache)

    first = provider.get_daily_bars("0001.HK")
    second = provider.get_daily_bars("0001.HK")
    assert first == second
    assert len(first) == 5
    assert first[0].provenance.source_record_id == "0001.HK-20200102"
    assert first[0].provenance.metadata["filter_schema_version"] == (
        "v04_ipo_eod_filter_v2"
    )
    assert len(provider.provider_identity["filtered_store_sha256"]) == 64
    assert provider.readiness_report().invalid_price_rows == 1
    with pytest.raises(UnsupportedStockError):
        provider.get_daily_bars("9999.HK")


def test_filtered_provider_does_not_access_raw_eod(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    catalog, _, cache = _fixture(tmp_path)

    def forbidden_raw_scan(*args, **kwargs):
        raise AssertionError("raw EOD scan was attempted")

    monkeypatch.setattr(
        CompetitionCSVMarketDataProvider,
        "_ensure_index",
        forbidden_raw_scan,
    )
    provider = _filtered(catalog, cache)
    assert len(provider.get_daily_bars("0001.HK")) == 5


def test_raw_and_filtered_bars_and_labels_have_semantic_parity(tmp_path: Path) -> None:
    catalog, raw_root, cache = _fixture(tmp_path)
    raw = CompetitionCSVMarketDataProvider(raw_root, catalog_dir=catalog)
    filtered = _filtered(catalog, cache)
    generator = MarketLabelGenerator()

    for metadata in raw.iter_listing_metadata():
        filtered_metadata = filtered.get_listing_metadata(metadata.stock_code)
        assert filtered_metadata == metadata
        raw_bars = raw.get_daily_bars(metadata.stock_code)
        filtered_bars = filtered.get_daily_bars(metadata.stock_code)
        assert [_bar_semantics(item) for item in filtered_bars] == [
            _bar_semantics(item) for item in raw_bars
        ]
        raw_labels = generator.generate(metadata, raw_bars)
        filtered_labels = generator.generate(filtered_metadata, filtered_bars)
        assert filtered_labels == raw_labels

    missing_eod = generator.generate(
        raw.get_listing_metadata("0002.HK"), raw.get_daily_bars("0002.HK")
    )
    assert {item.missing_reason for item in missing_eod} == {
        MarketLabelMissingReason.NO_ELIGIBLE_SESSION
    }
    missing_price = generator.generate(
        raw.get_listing_metadata("0003.HK"), raw.get_daily_bars("0003.HK")
    )
    assert {item.missing_reason for item in missing_price} == {
        MarketLabelMissingReason.MISSING_BASE_PRICE
    }
    normal = {
        item.horizon: item
        for item in generator.generate(
            raw.get_listing_metadata("0001.HK"), raw.get_daily_bars("0001.HK")
        )
    }
    assert normal[MarketLabelHorizon.ONE_DAY].target_trading_date.isoformat() == (
        "2020-01-02"
    )
    assert normal[MarketLabelHorizon.FIVE_DAYS].target_trading_date.isoformat() == (
        "2020-01-14"
    )


def test_filtered_provider_rejects_duplicate_stock_date(tmp_path: Path) -> None:
    catalog, _, cache = _fixture(tmp_path, duplicate=True)
    provider = _filtered(catalog, cache)
    with pytest.raises(DuplicateMarketBarError):
        provider.get_daily_bars("0001.HK")


def test_filtered_provider_rejects_manifest_and_store_drift(tmp_path: Path) -> None:
    catalog, _, cache = _fixture(tmp_path)
    store = cache / "v04_ipo_eod.csv"
    with pytest.raises(ValueError, match="store SHA-256 mismatch"):
        _filtered(catalog, cache, expected_store_sha256="0" * 64).provider_identity

    manifest_path = cache / "v04_ipo_eod.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["row_count"] += 1
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="manifest/store mismatch"):
        _filtered(catalog, cache).provider_identity

    assert store.is_file()


def test_filtered_provider_rejects_expected_cohort_drift(tmp_path: Path) -> None:
    catalog, _, cache = _fixture(tmp_path)
    manifest_path = cache / "v04_ipo_eod.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["expected_official_case_count"] += 1
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="expected official case count mismatch"):
        _filtered(catalog, cache)


def test_filtered_provider_rejects_required_column_drift(tmp_path: Path) -> None:
    catalog, _, cache = _fixture(tmp_path)
    store = cache / "v04_ipo_eod.csv"
    rows = list(csv.DictReader(store.open("r", encoding="utf-8", newline="")))
    shortened = [
        {name: row[name] for name in OUTPUT_COLUMNS[:-1]} for row in rows
    ]
    _write_csv(store, OUTPUT_COLUMNS[:-1], shortened)
    with pytest.raises(ValueError, match="store schema mismatch"):
        _filtered(catalog, cache).provider_identity
