from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ipo_risk.market.exceptions import DuplicateMarketBarError
from ipo_risk.providers.competition_market import CompetitionCSVMarketDataProvider
from ipo_risk.schemas.data_readiness import (
    SourceAvailability,
    V04SourceManifest,
    V04SourceManifestEntry,
    audit_security_identifiers,
    normalize_hk_security_identifier,
)
from ipo_risk.schemas.market import (
    MarketSecurityEligibility,
    MarketSecurityType,
)


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _provider_fixture(tmp_path: Path, *, duplicate: bool = False):
    catalog = tmp_path / "catalog"
    data = tmp_path / "competition"
    _write_csv(
        catalog / "ipo_official_master_bridge.csv",
        [
            "case_id",
            "stock_code_wind",
            "official_listed_date",
            "official_ipo_price",
            "official_match_status",
        ],
        [
            {
                "case_id": "ipo_2023_00368",
                "stock_code_wind": "0368.HK",
                "official_listed_date": "2023-01-03",
                "official_ipo_price": "1.25",
                "official_match_status": "matched",
            },
            {
                "case_id": "ipo_2025_00700",
                "stock_code_wind": "0700.HK",
                "official_listed_date": "2025-01-02",
                "official_ipo_price": "99",
                "official_match_status": "matched",
            },
        ],
    )
    _write_csv(
        catalog / "ipo_prospectus_manifest.csv",
        ["case_id", "sha256"],
        [
            {"case_id": "ipo_2023_00368", "sha256": "a" * 64},
            {"case_id": "ipo_2025_00700", "sha256": "b" * 64},
        ],
    )
    eod_fields = [
        "OBJECT_ID",
        "S_INFO_WINDCODE",
        "TRADE_DT",
        "S_DQ_OPEN",
        "S_DQ_HIGH",
        "S_DQ_LOW",
        "S_DQ_CLOSE",
        "S_DQ_VOLUME",
    ]
    rows = [
        {
            "OBJECT_ID": "bar-2",
            "S_INFO_WINDCODE": "0368.HK",
            "TRADE_DT": "20230104",
            "S_DQ_OPEN": "1.10",
            "S_DQ_HIGH": "1.40",
            "S_DQ_LOW": "1.00",
            "S_DQ_CLOSE": "1.30",
            "S_DQ_VOLUME": "120",
        },
        {
            "OBJECT_ID": "bar-1",
            "S_INFO_WINDCODE": "0368.HK",
            "TRADE_DT": "20230103",
            "S_DQ_OPEN": "1.20",
            "S_DQ_HIGH": "1.30",
            "S_DQ_LOW": "1.00",
            "S_DQ_CLOSE": "1.10",
            "S_DQ_VOLUME": "100",
        },
        {
            "OBJECT_ID": "bad-price",
            "S_INFO_WINDCODE": "0368.HK",
            "TRADE_DT": "20230105",
            "S_DQ_OPEN": "1.20",
            "S_DQ_HIGH": "1.10",
            "S_DQ_LOW": "1.00",
            "S_DQ_CLOSE": "1.15",
            "S_DQ_VOLUME": "100",
        },
        {
            "OBJECT_ID": "blind-poison",
            "S_INFO_WINDCODE": "0700.HK",
            "TRADE_DT": "20250103",
            "S_DQ_OPEN": "must-not-parse",
            "S_DQ_HIGH": "must-not-parse",
            "S_DQ_LOW": "must-not-parse",
            "S_DQ_CLOSE": "must-not-parse",
            "S_DQ_VOLUME": "must-not-parse",
        },
    ]
    if duplicate:
        rows.append({**rows[0], "OBJECT_ID": "duplicate"})
    _write_csv(data / "hkshareeodprices.csv", eod_fields, rows)
    return CompetitionCSVMarketDataProvider(data, catalog_dir=catalog)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("00368", "0368.HK"),
        ("0368.HK", "0368.HK"),
        ("368", "0368.HK"),
        ("02410", "2410.HK"),
    ],
)
def test_hk_identifier_normalization(raw: str, expected: str) -> None:
    assert normalize_hk_security_identifier(raw) == expected


@pytest.mark.parametrize("raw", ["", "0700.US", "HK0001", "123456"])
def test_hk_identifier_normalization_rejects_unsupported_values(raw: str) -> None:
    with pytest.raises(ValueError):
        normalize_hk_security_identifier(raw)


def test_security_join_audits_all_authoritative_identifiers() -> None:
    ipo_rows = [
        {
            "case_id": "case-code",
            "stock_code_raw": "00368",
            "stock_code_wind": "0368.HK",
        },
        {"case_id": "case-id", "security_id": "SEC-2"},
        {"case_id": "case-company", "institution_id": "COMP-3"},
        {"case_id": "case-missing", "stock_code_raw": "9999"},
    ]
    security_rows = [
        {"S_INFO_CODE": "368", "S_INFO_WINDCODE": "0368.HK"},
        {"OBJECT_ID": "SEC-2"},
        {"S_INFO_COMPCODE": "COMP-3", "S_INFO_CODE": "bad-value"},
    ]
    audit = audit_security_identifiers(ipo_rows, security_rows)
    assert audit.matched == 3
    assert audit.exact_wind_matches == 1
    assert audit.normalized_code_matches == 1
    assert audit.security_id_matches == 1
    assert audit.institution_id_matches == 1
    assert audit.unmatched_case_ids == ("case-missing",)


def test_source_manifest_is_portable_versioned_and_deterministic() -> None:
    entries = (
        V04SourceManifestEntry(
            source_name="HSI",
            logical_id="hsi",
            dataset_version="not_supplied",
            availability=SourceAvailability.MISSING,
            coverage={"cases": 0},
        ),
        V04SourceManifestEntry(
            source_name="Official IPO metadata",
            logical_id="ipo_metadata",
            dataset_version="sha256:fixture",
            sha256="a" * 64,
            relative_path="HK_Official_Merged_565_First_with_IPO.xlsx",
            availability=SourceAvailability.AVAILABLE,
            coverage={"cases": 438},
        ),
    )
    first = V04SourceManifest(entries=entries)
    second = V04SourceManifest.model_validate_json(first.canonical_json())
    assert first.content_hash() == second.content_hash()
    assert "C:\\" not in first.canonical_json()
    with pytest.raises(ValidationError, match="relative"):
        V04SourceManifestEntry(
            source_name="bad",
            logical_id="bad",
            dataset_version="v1",
            sha256="b" * 64,
            relative_path="C:/local/source.csv",
            availability=SourceAvailability.AVAILABLE,
        )
    with pytest.raises(ValidationError, match="cannot claim"):
        V04SourceManifestEntry(
            source_name="missing",
            logical_id="missing",
            dataset_version="not_supplied",
            sha256="c" * 64,
            availability=SourceAvailability.MISSING,
        )


def test_committed_v04_source_manifest_validates() -> None:
    path = Path("data/catalog/v04_source_manifest.json")
    manifest = V04SourceManifest.model_validate_json(path.read_text(encoding="utf-8"))
    assert tuple(entry.logical_id for entry in manifest.entries) == (
        "document_result_pipeline",
        "hsi",
        "industry_index",
        "industry_mapping",
        "ipo_eod",
        "ipo_metadata",
        "market_turnover",
        "security_master",
    )
    assert len(manifest.content_hash()) == 64
    serialized = manifest.canonical_json()
    assert "C:\\" not in serialized
    assert "D:\\" not in serialized


def test_competition_eod_adapter_is_deterministic_and_blind_safe(tmp_path: Path) -> None:
    provider = _provider_fixture(tmp_path)
    metadata = provider.get_listing_metadata("368")
    bars = provider.get_daily_bars("00368")
    report = provider.readiness_report()

    assert metadata.security_type is MarketSecurityType.UNKNOWN
    assert metadata.modeling_eligibility is MarketSecurityEligibility.INELIGIBLE
    assert [bar.trading_date.isoformat() for bar in bars] == ["2023-01-03", "2023-01-04"]
    assert all(bar.provenance.metadata["source_sha256"] == report.source_sha256 for bar in bars)
    assert all("\\" not in json.dumps(bar.provenance.model_dump()) for bar in bars)
    assert report.ipo_total == 1
    assert report.ohlcv_matched == 1
    assert report.invalid_price_rows == 1
    assert report.horizon_coverage == {"1D": 1, "5D": 0, "20D": 0, "60D": 0}
    assert "0700.HK" not in provider._bar_offsets


def test_competition_eod_adapter_fails_closed_on_duplicates_every_time(
    tmp_path: Path,
) -> None:
    provider = _provider_fixture(tmp_path, duplicate=True)
    with pytest.raises(DuplicateMarketBarError):
        provider.readiness_report()
    with pytest.raises(DuplicateMarketBarError):
        provider.get_daily_bars("0368.HK")
