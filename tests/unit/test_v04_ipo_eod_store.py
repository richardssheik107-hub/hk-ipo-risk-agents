from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from scripts.build_v04_ipo_eod_store import (
    FILTER_SCHEMA_VERSION,
    OUTPUT_COLUMNS,
    _cache_is_compatible,
    build_store,
    load_official_target_codes,
)


def _write_bridge(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "case_id",
        "source_year",
        "stock_code_wind",
        "official_match_status",
        "official_listed_date",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_eod_store_uses_official_listing_year_not_source_year(tmp_path: Path) -> None:
    bridge = tmp_path / "bridge.csv"
    _write_bridge(
        bridge,
        [
            {
                "case_id": "case_in",
                "source_year": "2019",
                "stock_code_wind": "0001.HK",
                "official_match_status": "matched",
                "official_listed_date": "2020-01-02",
            },
            {
                "case_id": "case_out",
                "source_year": "2020",
                "stock_code_wind": "0002.HK",
                "official_match_status": "matched",
                "official_listed_date": "2019-12-31",
            },
        ],
    )

    codes, cases = load_official_target_codes(
        bridge,
        expected_case_count=None,
    )

    assert codes == {"0001.HK"}
    assert cases == ("case_in",)


def test_eod_store_rejects_invalid_official_listing_date(tmp_path: Path) -> None:
    bridge = tmp_path / "bridge.csv"
    _write_bridge(
        bridge,
        [
            {
                "case_id": "case_bad",
                "source_year": "2020",
                "stock_code_wind": "0001.HK",
                "official_match_status": "matched",
                "official_listed_date": "not-a-date",
            }
        ],
    )

    with pytest.raises(ValueError, match="invalid official_listed_date"):
        load_official_target_codes(bridge, expected_case_count=None)


def test_eod_store_rejects_official_cohort_drift(tmp_path: Path) -> None:
    bridge = tmp_path / "bridge.csv"
    _write_bridge(
        bridge,
        [
            {
                "case_id": "case_only",
                "source_year": "2020",
                "stock_code_wind": "0001.HK",
                "official_match_status": "matched",
                "official_listed_date": "2020-01-02",
            }
        ],
    )

    with pytest.raises(ValueError, match="official target cohort drift"):
        load_official_target_codes(bridge, expected_case_count=438)


def test_governed_store_filters_rows_and_retains_source_record_id(tmp_path: Path) -> None:
    catalog = tmp_path / "catalog"
    data_root = tmp_path / "data"
    cache = tmp_path / "cache"
    catalog.mkdir()
    data_root.mkdir()
    _write_bridge(
        catalog / "ipo_official_master_bridge.csv",
        [
            {
                "case_id": "case_target",
                "source_year": "2019",
                "stock_code_wind": "0001.HK",
                "official_match_status": "matched",
                "official_listed_date": "2020-01-02",
            }
        ],
    )

    rows = [
        {
            "OBJECT_ID": "row-target",
            "S_INFO_WINDCODE": "0001.HK",
            "TRADE_DT": "20200102",
            "S_DQ_OPEN": "1",
            "S_DQ_HIGH": "1.2",
            "S_DQ_LOW": "0.9",
            "S_DQ_CLOSE": "1.1",
            "S_DQ_VOLUME": "100",
            "S_DQ_AMOUNT": "1000",
            "S_DQ_PRECLOSE": "1",
            "S_DQ_ADJCLOSE": "1.1",
        },
        {
            "OBJECT_ID": "row-unrelated",
            "S_INFO_WINDCODE": "0002.HK",
            "TRADE_DT": "20200102",
            "S_DQ_OPEN": "2",
            "S_DQ_HIGH": "2.2",
            "S_DQ_LOW": "1.9",
            "S_DQ_CLOSE": "2.1",
            "S_DQ_VOLUME": "200",
            "S_DQ_AMOUNT": "2000",
            "S_DQ_PRECLOSE": "2",
            "S_DQ_ADJCLOSE": "2.1",
        },
    ]
    with (data_root / "hkshareeodprices.csv").open(
        "w", encoding="gb18030", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(OUTPUT_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)

    manifest = build_store(
        data_root=data_root,
        catalog_dir=catalog,
        cache_dir=cache,
        expected_case_count=1,
    )

    with (cache / "v04_ipo_eod.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        filtered = list(csv.DictReader(handle))
    assert len(filtered) == 1
    assert filtered[0]["OBJECT_ID"] == "row-target"
    assert filtered[0]["S_INFO_WINDCODE"] == "0001.HK"
    assert manifest["target_case_count"] == 1
    assert manifest["row_count"] == 1
    assert manifest["source_record_id_column"] == "OBJECT_ID"
    assert "never total-market turnover" in manifest["s_dq_amount_semantics"]


def test_cache_compatibility_includes_selection_policy() -> None:
    manifest = {
        "raw_eod_sha256": "a" * 64,
        "bridge_sha256": "b" * 64,
        "filter_schema_version": FILTER_SCHEMA_VERSION,
        "selection_policy": (
            "official_match_status=matched + "
            "official_listed_date.year in 2020-2024"
        ),
    }

    assert _cache_is_compatible(
        manifest,
        raw_hash="a" * 64,
        bridge_hash="b" * 64,
    )

    changed = json.loads(json.dumps(manifest))
    changed["selection_policy"] = "source_year"
    assert not _cache_is_compatible(
        changed,
        raw_hash="a" * 64,
        bridge_hash="b" * 64,
    )
