"""Governed, local-only adapter for the competition IPO and EOD CSV sources."""

from __future__ import annotations

import csv
import hashlib
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import BinaryIO

from pydantic import BaseModel, ConfigDict, Field

from ipo_risk.market.exceptions import (
    DuplicateMarketBarError,
    UnsupportedStockError,
)
from ipo_risk.schemas import IPOProfile, MarketSnapshot
from ipo_risk.schemas.data_readiness import normalize_hk_security_identifier
from ipo_risk.schemas.market import (
    IPOMarketMetadata,
    MarketDailyBar,
    MarketDataProvenance,
    MarketExchange,
    MarketSecurityEligibility,
    MarketSecurityEligibilityReason,
)


DEFAULT_COMPETITION_DATA_ROOT = Path("data/competition")
DEFAULT_CATALOG_DIR = Path("data/catalog")
BRIDGE_FILENAME = "ipo_official_master_bridge.csv"
PROSPECTUS_MANIFEST_FILENAME = "ipo_prospectus_manifest.csv"
EOD_FILENAME = "hkshareeodprices.csv"
EOD_SOURCE_NAME = "competition_hkshareeodprices"
EOD_SOURCE_VERSION = "competition_hkshareeodprices_v1"
ALLOWED_OUTCOME_COHORT_YEARS = frozenset({2020, 2021, 2022, 2023, 2024})

_BRIDGE_REQUIRED_FIELDS = {
    "case_id",
    "stock_code_wind",
    "official_listed_date",
    "official_ipo_price",
    "official_match_status",
}
_EOD_REQUIRED_FIELDS = {
    "OBJECT_ID",
    "S_INFO_WINDCODE",
    "TRADE_DT",
    "S_DQ_OPEN",
    "S_DQ_HIGH",
    "S_DQ_LOW",
    "S_DQ_CLOSE",
    "S_DQ_VOLUME",
}


class CompetitionEODReadinessReport(BaseModel):
    """Deterministic audit summary produced by the real CSV scan."""

    model_config = ConfigDict(frozen=True)

    ipo_total: int = Field(ge=0)
    eligible_ipo_total: int = Field(ge=0)
    ohlcv_matched: int = Field(ge=0)
    ohlcv_missing: int = Field(ge=0)
    eligible_but_outcome_unavailable: int = Field(ge=0)
    duplicate_rows: int = Field(ge=0)
    invalid_price_rows: int = Field(ge=0)
    first_valid_trade_date: date | None = None
    last_valid_trade_date: date | None = None
    horizon_coverage: dict[str, int]
    missing_case_ids: tuple[str, ...]
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class CompetitionCSVMarketDataProvider:
    """Read official IPO metadata and indexed raw EOD rows without networking.

    The EOD file is scanned once. Only offsets for 2020-2024 catalog securities
    are retained, so 2025 blind securities never have price fields parsed or
    exposed. Invalid OHLC rows are excluded as non-eligible observations and
    counted in the readiness report; duplicate stock/date keys fail closed.
    """

    name = "competition_csv"

    def __init__(
        self,
        data_root: str | Path = DEFAULT_COMPETITION_DATA_ROOT,
        *,
        catalog_dir: str | Path = DEFAULT_CATALOG_DIR,
        source_version: str = EOD_SOURCE_VERSION,
    ) -> None:
        self.data_root = Path(data_root)
        self.catalog_dir = Path(catalog_dir)
        self.bridge_path = self.catalog_dir / BRIDGE_FILENAME
        self.prospectus_manifest_path = (
            self.catalog_dir / PROSPECTUS_MANIFEST_FILENAME
        )
        self.eod_path = self.data_root / EOD_FILENAME
        self.source_version = source_version.strip()
        if not self.source_version:
            raise ValueError("EOD source version is required")

        self._metadata = self._load_metadata()
        self._bar_offsets: dict[str, list[tuple[date, int]]] = defaultdict(list)
        self._eod_header: tuple[str, ...] | None = None
        self._eod_sha256: str | None = None
        self._duplicate_rows = 0
        self._invalid_price_rows = 0
        self._first_valid_trade_date: date | None = None
        self._last_valid_trade_date: date | None = None
        self._indexed = False

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _read_csv(path: Path) -> list[dict[str, str]]:
        if not path.is_file():
            raise FileNotFoundError(f"required catalog file not found: {path.name}")
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    def _load_metadata(self) -> dict[str, IPOMarketMetadata]:
        bridge_rows = self._read_csv(self.bridge_path)
        if bridge_rows and not _BRIDGE_REQUIRED_FIELDS.issubset(bridge_rows[0]):
            missing = sorted(_BRIDGE_REQUIRED_FIELDS - set(bridge_rows[0]))
            raise ValueError(f"official bridge missing fields: {', '.join(missing)}")
        document_ids = {
            row["case_id"]: (row.get("sha256") or "").strip()
            for row in self._read_csv(self.prospectus_manifest_path)
        }
        bridge_sha256 = self._sha256(self.bridge_path)
        metadata: dict[str, IPOMarketMetadata] = {}
        for row in bridge_rows:
            if (row.get("official_match_status") or "").strip() != "matched":
                continue
            raw_listing_date = (row.get("official_listed_date") or "").strip()
            if not raw_listing_date:
                continue
            listing_date = date.fromisoformat(raw_listing_date)
            if listing_date.year not in ALLOWED_OUTCOME_COHORT_YEARS:
                continue
            stock_code = normalize_hk_security_identifier(row["stock_code_wind"])
            if stock_code in metadata:
                raise ValueError(f"duplicate official IPO metadata: {stock_code}")
            raw_price = (row.get("official_ipo_price") or "").replace(",", "").strip()
            listing_price = Decimal(raw_price) if raw_price else None
            case_id = row["case_id"].strip()
            metadata[stock_code] = IPOMarketMetadata(
                case_id=case_id,
                document_id=document_ids.get(case_id) or None,
                stock_code=stock_code,
                cohort_year=listing_date.year,
                listing_date=listing_date,
                listing_price=listing_price,
                currency="HKD",
                exchange=MarketExchange.HKEX,
                official_ipo_universe_member=True,
                modeling_eligibility=MarketSecurityEligibility.ELIGIBLE,
                eligibility_reason=(
                    MarketSecurityEligibilityReason.OFFICIAL_IPO_UNIVERSE_MEMBER
                ),
                source="competition_official_master_bridge",
                provenance=MarketDataProvenance(
                    source="competition_official_master_bridge",
                    dataset_version=f"sha256:{bridge_sha256}",
                    source_record_id=case_id,
                    metadata={
                        "source_filename": BRIDGE_FILENAME,
                        "source_sha256": bridge_sha256,
                    },
                ),
            )
        return metadata

    def iter_listing_metadata(self) -> tuple[IPOMarketMetadata, ...]:
        """Return the frozen official universe in deterministic case order."""

        return tuple(sorted(self._metadata.values(), key=lambda item: item.case_id))

    @staticmethod
    def _decode_csv_line(line: bytes) -> list[str]:
        return next(csv.reader([line.decode("utf-8").rstrip("\r\n")]))

    @staticmethod
    def _parse_trade_date(raw: str) -> date:
        return datetime.strptime(raw, "%Y%m%d").date()

    @staticmethod
    def _valid_ohlc(row: dict[str, str]) -> bool:
        try:
            open_price, high, low, close = (
                Decimal(row[field])
                for field in ("S_DQ_OPEN", "S_DQ_HIGH", "S_DQ_LOW", "S_DQ_CLOSE")
            )
            raw_volume = (row.get("S_DQ_VOLUME") or "").strip()
            volume = Decimal(raw_volume) if raw_volume else None
        except (InvalidOperation, KeyError):
            return False
        return (
            all(value.is_finite() and value > 0 for value in (open_price, high, low, close))
            and high >= max(open_price, low, close)
            and low <= min(open_price, high, close)
            and (volume is None or (volume.is_finite() and volume >= 0))
        )

    def _ensure_index(self) -> None:
        if self._indexed:
            if self._duplicate_rows:
                raise DuplicateMarketBarError(
                    f"EOD source contains {self._duplicate_rows} duplicate stock/date rows"
                )
            return
        if not self.eod_path.is_file():
            raise FileNotFoundError(f"required EOD file not found: {EOD_FILENAME}")

        digest = hashlib.sha256()
        seen: set[tuple[str, date]] = set()
        with self.eod_path.open("rb") as handle:
            header_line = handle.readline()
            digest.update(header_line)
            header = tuple(self._decode_csv_line(header_line.lstrip(b"\xef\xbb\xbf")))
            if not _EOD_REQUIRED_FIELDS.issubset(header):
                missing = sorted(_EOD_REQUIRED_FIELDS - set(header))
                raise ValueError(f"EOD source missing fields: {', '.join(missing)}")
            self._eod_header = header

            while True:
                offset = handle.tell()
                line = handle.readline()
                if not line:
                    break
                digest.update(line)
                if not line.strip():
                    continue
                values = self._decode_csv_line(line)
                if len(values) != len(header):
                    continue
                row = dict(zip(header, values))
                raw_code = row.get("S_INFO_WINDCODE", "")
                try:
                    stock_code = normalize_hk_security_identifier(raw_code)
                except ValueError:
                    continue
                if stock_code not in self._metadata:
                    # Blind-cohort and unrelated rows are not price-parsed.
                    continue
                try:
                    trading_date = self._parse_trade_date(row["TRADE_DT"])
                except (KeyError, ValueError):
                    self._invalid_price_rows += 1
                    continue
                key = (stock_code, trading_date)
                if key in seen:
                    self._duplicate_rows += 1
                    continue
                seen.add(key)
                if not self._valid_ohlc(row):
                    self._invalid_price_rows += 1
                    continue
                self._bar_offsets[stock_code].append((trading_date, offset))
                self._first_valid_trade_date = min(
                    self._first_valid_trade_date or trading_date, trading_date
                )
                self._last_valid_trade_date = max(
                    self._last_valid_trade_date or trading_date, trading_date
                )

        for offsets in self._bar_offsets.values():
            offsets.sort(key=lambda item: item[0])
        self._eod_sha256 = digest.hexdigest()
        self._indexed = True
        if self._duplicate_rows:
            raise DuplicateMarketBarError(
                f"EOD source contains {self._duplicate_rows} duplicate stock/date rows"
            )

    def _row_at_offset(self, handle: BinaryIO, offset: int) -> dict[str, str]:
        if self._eod_header is None:
            raise RuntimeError("EOD index has not been initialized")
        handle.seek(offset)
        values = self._decode_csv_line(handle.readline())
        return dict(zip(self._eod_header, values))

    def get_listing_metadata(self, stock_code: str) -> IPOMarketMetadata:
        normalized = normalize_hk_security_identifier(stock_code)
        try:
            return self._metadata[normalized]
        except KeyError as exc:
            raise UnsupportedStockError(f"unsupported stock code: {normalized}") from exc

    def get_daily_bars(
        self,
        stock_code: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[MarketDailyBar]:
        normalized = normalize_hk_security_identifier(stock_code)
        if normalized not in self._metadata:
            raise UnsupportedStockError(f"unsupported stock code: {normalized}")
        self._ensure_index()
        assert self._eod_sha256 is not None
        bars: list[MarketDailyBar] = []
        with self.eod_path.open("rb") as handle:
            for trading_date, offset in self._bar_offsets.get(normalized, []):
                if start_date is not None and trading_date < start_date:
                    continue
                if end_date is not None and trading_date > end_date:
                    continue
                row = self._row_at_offset(handle, offset)
                raw_volume = (row.get("S_DQ_VOLUME") or "").strip()
                bars.append(
                    MarketDailyBar(
                        stock_code=normalized,
                        trading_date=trading_date,
                        open=Decimal(row["S_DQ_OPEN"]),
                        high=Decimal(row["S_DQ_HIGH"]),
                        low=Decimal(row["S_DQ_LOW"]),
                        close=Decimal(row["S_DQ_CLOSE"]),
                        volume=Decimal(raw_volume) if raw_volume else None,
                        source=EOD_SOURCE_NAME,
                        provenance=MarketDataProvenance(
                            source=EOD_SOURCE_NAME,
                            dataset_version=self.source_version,
                            source_record_id=(row.get("OBJECT_ID") or "").strip() or None,
                            metadata={
                                "source_filename": EOD_FILENAME,
                                "source_sha256": self._eod_sha256,
                            },
                        ),
                    )
                )
        return bars

    def readiness_report(self) -> CompetitionEODReadinessReport:
        self._ensure_index()
        assert self._eod_sha256 is not None
        missing: list[str] = []
        horizon_coverage = {"1D": 0, "5D": 0, "20D": 0, "60D": 0}
        for stock_code, metadata in self._metadata.items():
            eligible_dates = [
                trading_date
                for trading_date, _ in self._bar_offsets.get(stock_code, [])
                if metadata.listing_date is not None
                and trading_date >= metadata.listing_date
            ]
            if not eligible_dates:
                missing.append(metadata.case_id)
            for label, sessions in (("1D", 1), ("5D", 5), ("20D", 20), ("60D", 60)):
                horizon_coverage[label] += int(len(eligible_dates) >= sessions)
        missing_case_ids = frozenset(missing)
        return CompetitionEODReadinessReport(
            ipo_total=len(self._metadata),
            eligible_ipo_total=sum(
                item.modeling_eligibility is MarketSecurityEligibility.ELIGIBLE
                for item in self._metadata.values()
            ),
            ohlcv_matched=len(self._metadata) - len(missing),
            ohlcv_missing=len(missing),
            eligible_but_outcome_unavailable=sum(
                item.case_id in missing_case_ids
                and item.modeling_eligibility is MarketSecurityEligibility.ELIGIBLE
                for item in self._metadata.values()
            ),
            duplicate_rows=self._duplicate_rows,
            invalid_price_rows=self._invalid_price_rows,
            first_valid_trade_date=self._first_valid_trade_date,
            last_valid_trade_date=self._last_valid_trade_date,
            horizon_coverage=horizon_coverage,
            missing_case_ids=tuple(sorted(missing)),
            source_sha256=self._eod_sha256,
        )

    def get_snapshot(self, profile: IPOProfile) -> MarketSnapshot:
        return MarketSnapshot(
            source="unavailable",
            metadata={
                "available": False,
                "reason": "legacy snapshot is not produced by the governed EOD adapter",
            },
        )
