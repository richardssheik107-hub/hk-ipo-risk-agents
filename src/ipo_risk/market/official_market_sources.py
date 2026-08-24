"""Governed loaders for official HSCI and HKEX total-market sources.

The normalized CSV assets are local, ignored staging files.  This module
validates their versioned manifest and SHA-256 before exposing the existing
``MarketReferenceBar`` and ``MarketActivityObservation`` contracts.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ipo_risk.schemas.market import MarketDataProvenance
from ipo_risk.schemas.market_features import (
    MarketActivityObservation,
    MarketReferenceBar,
)


EXTERNAL_MARKET_MANIFEST_VERSION = "v04_c_external_market_source_manifest_v1"
HSCI_DATASET_VERSION = "hsci_industry_daily_close_official_public_5y_v1"
HKEX_TURNOVER_DATASET_VERSION = "hkex_total_market_daily_turnover_2019_2025_v1"
HSCI_EXPECTED_IDS = frozenset(
    {
        "HSCIE",
        "HSCIM",
        "HSCIIG",
        "HSCICD",
        "HSCICS",
        "HSCIH",
        "HSCIT",
        "HSCIU",
        "HSCIF",
        "HSCIPC",
        "HSCIIT",
        "HSCIC",
    }
)
HSCI_COLUMNS = (
    "benchmark_id",
    "trading_date",
    "close",
    "series_type",
    "source_owner",
)
HKEX_TURNOVER_COLUMNS = (
    "trading_date",
    "total_market_turnover",
    "currency",
    "unit",
    "market_scope",
    "main_board_turnover_hkd",
    "gem_turnover_hkd",
)


class OfficialMarketSourceError(ValueError):
    """Raised when an official normalized source fails closed."""


class HSCISeriesManifest(BaseModel):
    """Versioned public metadata for one accepted HSCI series."""

    model_config = ConfigDict(frozen=True)

    benchmark_id: str
    benchmark_name: str
    internal_index_code: str
    source_url: str
    dataset: str
    series_type: str = "price_index"
    frequency: str = "daily"
    coverage_start: date
    coverage_end: date
    row_count: int = Field(gt=0)
    raw_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    download_timestamp_utc: str


class HSCISourceManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    authority: str
    authoritative_level: str
    target_series_count: int
    found_series_count: int
    accepted_series_count: int
    row_count: int
    rows_per_series: int
    coverage_start: date
    coverage_end: date
    frequency: str
    fields: tuple[str, ...]
    series_type: str
    pit_safe: bool
    normalized_relative_path: str
    normalized_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    series: tuple[HSCISeriesManifest, ...]

    @model_validator(mode="after")
    def validate_universe(self) -> "HSCISourceManifest":
        ids = [item.benchmark_id for item in self.series]
        if (
            self.status != "ACCEPT_PARTIAL_COVERAGE"
            or self.authority != "Hang Seng Indexes Company Limited"
            or self.authoritative_level != "PRIMARY_OFFICIAL"
            or not self.pit_safe
        ):
            raise ValueError("HSCI manifest is not an accepted official source")
        if set(ids) != HSCI_EXPECTED_IDS or len(ids) != len(HSCI_EXPECTED_IDS):
            raise ValueError("HSCI manifest must contain the exact 12-series universe")
        if self.target_series_count != 12 or self.accepted_series_count != 12:
            raise ValueError("HSCI manifest acceptance count must be 12/12")
        if self.found_series_count != 12:
            raise ValueError("HSCI manifest found count must be 12/12")
        if self.fields != ("benchmark_id", "trading_date", "close"):
            raise ValueError("HSCI manifest fields differ from the governed schema")
        if self.row_count != self.rows_per_series * 12:
            raise ValueError("HSCI manifest aggregate row count is inconsistent")
        if any(
            item.row_count != self.rows_per_series
            or item.coverage_start != self.coverage_start
            or item.coverage_end != self.coverage_end
            or item.series_type != "price_index"
            or item.frequency != "daily"
            for item in self.series
        ):
            raise ValueError("HSCI series metadata differs from the accepted universe")
        return self


class HKEXSourceFileManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    market: str
    coverage_block: str
    source_url: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    download_timestamp_utc: str


class HKEXTurnoverSourceManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    authority: str
    authoritative_level: str
    row_count: int = Field(gt=0)
    coverage_start: date
    coverage_end: date
    frequency: str
    currency: str
    unit: str
    market_scope: str
    measure: str
    aggregation_method: str
    series_type: str
    pit_safe: bool
    calendar_mismatch_count: int = Field(ge=0)
    normalized_relative_path: str
    normalized_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_files: tuple[HKEXSourceFileManifest, ...]

    @model_validator(mode="after")
    def validate_definition(self) -> "HKEXTurnoverSourceManifest":
        if (
            self.status != "ACCEPT"
            or self.authority != "Hong Kong Exchanges and Clearing Limited"
            or self.authoritative_level != "PRIMARY_OFFICIAL"
            or self.frequency != "daily"
            or self.currency != "HKD"
            or self.unit != "HKD"
            or self.market_scope != "Main Board + GEM; all securities in HKEX archive"
            or self.measure != "daily trading value / turnover"
            or self.aggregation_method != "main_board_turnover_hkd + gem_turnover_hkd"
            or self.calendar_mismatch_count != 0
            or not self.pit_safe
        ):
            raise ValueError("HKEX turnover manifest definition is not accepted")
        if len(self.source_files) not in {0, 5}:
            raise ValueError("HKEX turnover manifest must identify all five source files")
        return self


class ExternalMarketSourceManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    manifest_version: str
    industry_taxonomy: dict[str, Any]
    hsci_industry_daily_close: HSCISourceManifest
    hkex_total_market_daily_turnover: HKEXTurnoverSourceManifest

    @model_validator(mode="after")
    def validate_version(self) -> "ExternalMarketSourceManifest":
        if self.manifest_version != EXTERNAL_MARKET_MANIFEST_VERSION:
            raise ValueError("unsupported external market source manifest version")
        return self

    @classmethod
    def from_path(cls, path: Path) -> "ExternalMarketSourceManifest":
        return cls.model_validate_json(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _positive_decimal(raw: str, *, row_number: int, field: str) -> Decimal:
    try:
        value = Decimal(raw.strip().replace(",", ""))
    except InvalidOperation as exc:
        raise OfficialMarketSourceError(
            f"invalid {field} at normalized row {row_number}"
        ) from exc
    if not value.is_finite() or value <= 0:
        raise OfficialMarketSourceError(
            f"{field} must be finite and positive at normalized row {row_number}"
        )
    return value


def _read_governed_rows(
    path: Path,
    *,
    expected_sha256: str,
    expected_columns: tuple[str, ...],
) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    actual_sha256 = sha256_file(path)
    if actual_sha256 != expected_sha256:
        raise OfficialMarketSourceError(
            f"normalized source hash mismatch: expected {expected_sha256}, "
            f"found {actual_sha256}"
        )
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != expected_columns:
            raise OfficialMarketSourceError("normalized source columns differ from manifest")
        return list(reader)


def load_hsci_bars(
    normalized_csv: Path,
    manifest: HSCISourceManifest,
) -> tuple[MarketReferenceBar, ...]:
    """Validate and load the exact 12 official HSCI price-index series."""

    rows = _read_governed_rows(
        normalized_csv,
        expected_sha256=manifest.normalized_sha256,
        expected_columns=HSCI_COLUMNS,
    )
    if len(rows) != manifest.row_count:
        raise OfficialMarketSourceError("HSCI normalized row count differs from manifest")
    series_metadata = {item.benchmark_id: item for item in manifest.series}
    seen: set[tuple[str, date]] = set()
    bars: list[MarketReferenceBar] = []
    for row_number, row in enumerate(rows, start=2):
        benchmark_id = row["benchmark_id"].strip()
        if benchmark_id not in HSCI_EXPECTED_IDS:
            raise OfficialMarketSourceError(
                f"unexpected HSCI benchmark ID at normalized row {row_number}"
            )
        try:
            trading_date = date.fromisoformat(row["trading_date"].strip())
        except ValueError as exc:
            raise OfficialMarketSourceError(
                f"invalid HSCI date at normalized row {row_number}"
            ) from exc
        key = (benchmark_id, trading_date)
        if key in seen:
            raise OfficialMarketSourceError(
                f"duplicate HSCI date for {benchmark_id}: {trading_date}"
            )
        seen.add(key)
        if row["series_type"].strip() != "price_index":
            raise OfficialMarketSourceError("HSCI row is not a price index")
        if row["source_owner"].strip() != manifest.authority:
            raise OfficialMarketSourceError("HSCI row authority differs from manifest")
        close = _positive_decimal(row["close"], row_number=row_number, field="close")
        metadata = series_metadata[benchmark_id]
        bars.append(
            MarketReferenceBar(
                reference_id=benchmark_id,
                trading_date=trading_date,
                close=close,
                provenance=MarketDataProvenance(
                    source=manifest.authority,
                    dataset_version=(
                        f"{HSCI_DATASET_VERSION}:sha256:{manifest.normalized_sha256}"
                    ),
                    source_record_id=f"{benchmark_id}:{trading_date.isoformat()}",
                    metadata={
                        "benchmark_name": metadata.benchmark_name,
                        "internal_index_code": metadata.internal_index_code,
                        "source_url": metadata.source_url,
                        "series_type": metadata.series_type,
                        "frequency": metadata.frequency,
                        "raw_sha256": metadata.raw_sha256,
                        "download_timestamp_utc": metadata.download_timestamp_utc,
                    },
                ),
            )
        )
    bars.sort(key=lambda item: (item.reference_id, item.trading_date))
    counts = Counter(item.reference_id for item in bars)
    if set(counts) != HSCI_EXPECTED_IDS or any(
        count != manifest.rows_per_series for count in counts.values()
    ):
        raise OfficialMarketSourceError("HSCI normalized series coverage is incomplete")
    for benchmark_id in HSCI_EXPECTED_IDS:
        dates = [item.trading_date for item in bars if item.reference_id == benchmark_id]
        if dates[0] != manifest.coverage_start or dates[-1] != manifest.coverage_end:
            raise OfficialMarketSourceError(
                f"HSCI coverage differs from manifest for {benchmark_id}"
            )
    return tuple(bars)


def load_hkex_turnover(
    normalized_csv: Path,
    manifest: HKEXTurnoverSourceManifest,
) -> tuple[MarketActivityObservation, ...]:
    """Validate Main Board + GEM aggregation and load daily HKD turnover."""

    rows = _read_governed_rows(
        normalized_csv,
        expected_sha256=manifest.normalized_sha256,
        expected_columns=HKEX_TURNOVER_COLUMNS,
    )
    if len(rows) != manifest.row_count:
        raise OfficialMarketSourceError("HKEX turnover row count differs from manifest")
    seen_dates: set[date] = set()
    observations: list[MarketActivityObservation] = []
    dataset_version = f"{HKEX_TURNOVER_DATASET_VERSION}:sha256:{manifest.normalized_sha256}"
    for row_number, row in enumerate(rows, start=2):
        try:
            trading_date = date.fromisoformat(row["trading_date"].strip())
        except ValueError as exc:
            raise OfficialMarketSourceError(
                f"invalid HKEX date at normalized row {row_number}"
            ) from exc
        if trading_date in seen_dates:
            raise OfficialMarketSourceError(f"duplicate HKEX turnover date: {trading_date}")
        seen_dates.add(trading_date)
        if (
            row["currency"].strip() != manifest.currency
            or row["unit"].strip() != manifest.unit
            or row["market_scope"].strip() != manifest.market_scope
        ):
            raise OfficialMarketSourceError(
                f"HKEX unit/currency/scope mismatch at normalized row {row_number}"
            )
        total = _positive_decimal(
            row["total_market_turnover"], row_number=row_number, field="total turnover"
        )
        main = _positive_decimal(
            row["main_board_turnover_hkd"], row_number=row_number, field="Main Board turnover"
        )
        gem = _positive_decimal(
            row["gem_turnover_hkd"], row_number=row_number, field="GEM turnover"
        )
        if total != main + gem:
            raise OfficialMarketSourceError(
                f"HKEX Main Board + GEM aggregation mismatch at row {row_number}"
            )
        observations.append(
            MarketActivityObservation(
                trading_date=trading_date,
                turnover=total,
                provenance=MarketDataProvenance(
                    source=manifest.authority,
                    dataset_version=dataset_version,
                    source_record_id=trading_date.isoformat(),
                    metadata={
                        "market_scope": manifest.market_scope,
                        "measure": manifest.measure,
                        "currency": manifest.currency,
                        "unit": manifest.unit,
                        "aggregation_method": manifest.aggregation_method,
                        "main_board_turnover_hkd": str(main),
                        "gem_turnover_hkd": str(gem),
                    },
                ),
            )
        )
    observations.sort(key=lambda item: item.trading_date)
    if observations[0].trading_date != manifest.coverage_start:
        raise OfficialMarketSourceError("HKEX turnover coverage start differs from manifest")
    if observations[-1].trading_date != manifest.coverage_end:
        raise OfficialMarketSourceError("HKEX turnover coverage end differs from manifest")
    return tuple(observations)


class OfficialHSCIProvider:
    """Read-only strict-before provider for the governed 12-series HSCI cache."""

    name = "official_hsci"

    def __init__(self, normalized_csv: Path, manifest: ExternalMarketSourceManifest | Path):
        self.manifest = (
            ExternalMarketSourceManifest.from_path(manifest)
            if isinstance(manifest, Path)
            else manifest
        )
        self._bars = load_hsci_bars(
            normalized_csv, self.manifest.hsci_industry_daily_close
        )
        self._by_id = {
            benchmark_id: tuple(
                item for item in self._bars if item.reference_id == benchmark_id
            )
            for benchmark_id in sorted(HSCI_EXPECTED_IDS)
        }

    def get_industry_bars(
        self, reference_id: str, *, end_date_exclusive: date
    ) -> tuple[MarketReferenceBar, ...]:
        if reference_id not in HSCI_EXPECTED_IDS:
            raise OfficialMarketSourceError(
                f"official HSCI provider cannot serve {reference_id!r}"
            )
        return tuple(
            item
            for item in self._by_id[reference_id]
            if item.trading_date < end_date_exclusive
        )

    def iter_all_bars(self) -> Iterable[MarketReferenceBar]:
        return iter(self._bars)


class OfficialHKEXTurnoverProvider:
    """Read-only strict-before provider for HKEX total-market turnover."""

    name = "official_hkex_total_market_turnover"

    def __init__(self, normalized_csv: Path, manifest: ExternalMarketSourceManifest | Path):
        self.manifest = (
            ExternalMarketSourceManifest.from_path(manifest)
            if isinstance(manifest, Path)
            else manifest
        )
        self._observations = load_hkex_turnover(
            normalized_csv, self.manifest.hkex_total_market_daily_turnover
        )

    def get_market_activity(
        self, *, end_date_exclusive: date
    ) -> tuple[MarketActivityObservation, ...]:
        return tuple(
            item
            for item in self._observations
            if item.trading_date < end_date_exclusive
        )

    def iter_all_observations(self) -> Iterable[MarketActivityObservation]:
        return iter(self._observations)
