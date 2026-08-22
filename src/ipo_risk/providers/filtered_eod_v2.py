"""Read-only consumer for the frozen v04 IPO EOD filtered store."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, BinaryIO

from ipo_risk.market.eod_store import (
    EXPECTED_OFFICIAL_CASE_COUNT,
    FILTER_SCHEMA_VERSION,
    OFFICIAL_LISTING_YEARS,
    OUTPUT_COLUMNS,
    sha256_file,
)
from ipo_risk.market.exceptions import DuplicateMarketBarError, UnsupportedStockError
from ipo_risk.providers.competition_market import (
    BRIDGE_FILENAME,
    EOD_FILENAME,
    EOD_SOURCE_NAME,
    EOD_SOURCE_VERSION,
    CompetitionCSVMarketDataProvider,
    CompetitionEODReadinessReport,
)
from ipo_risk.schemas import IPOProfile, MarketSnapshot
from ipo_risk.schemas.data_readiness import normalize_hk_security_identifier
from ipo_risk.schemas.market import (
    IPOMarketMetadata,
    MarketDailyBar,
    MarketDataProvenance,
    MarketSecurityEligibility,
)


FILTERED_EOD_FILENAME = "v04_ipo_eod.csv"
FILTERED_EOD_MANIFEST_FILENAME = "v04_ipo_eod.manifest.json"
SOURCE_MANIFEST_FILENAME = "v04_source_manifest.json"
SELECTION_POLICY = (
    "official_match_status=matched + official_listed_date.year in 2020-2024"
)
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_MANIFEST_FIELDS = {
    "filter_schema_version",
    "selection_policy",
    "official_listing_years",
    "expected_official_case_count",
    "target_case_count",
    "target_case_ids_sha256",
    "raw_eod_sha256",
    "bridge_sha256",
    "row_count",
    "distinct_target_securities",
    "target_security_count",
    "min_trading_date",
    "max_trading_date",
    "source_record_id_column",
    "s_dq_amount_semantics",
}


class FilteredEODV2MarketDataProvider:
    """Serve official metadata and valid bars from the immutable v2 store.

    The provider validates the store, its frozen builder manifest, the current
    official bridge, and the cataloged raw-source identity. It never opens the
    original ``hkshareeodprices.csv`` file.
    """

    name = "governed_filtered_eod_v2"

    def __init__(
        self,
        *,
        store_path: str | Path,
        manifest_path: str | Path,
        catalog_dir: str | Path = Path("data/catalog"),
        expected_case_count: int | None = EXPECTED_OFFICIAL_CASE_COUNT,
        expected_store_sha256: str | None = None,
        source_version: str = EOD_SOURCE_VERSION,
    ) -> None:
        self.store_path = Path(store_path)
        self.manifest_path = Path(manifest_path)
        self.catalog_dir = Path(catalog_dir)
        self.expected_case_count = expected_case_count
        self.expected_store_sha256 = expected_store_sha256
        self.source_version = source_version.strip()
        if not self.source_version:
            raise ValueError("EOD source version is required")
        if expected_store_sha256 is not None and not _SHA256_PATTERN.fullmatch(
            expected_store_sha256
        ):
            raise ValueError("expected filtered-store SHA-256 is invalid")
        if not self.store_path.is_file():
            raise FileNotFoundError(self.store_path)
        if not self.manifest_path.is_file():
            raise FileNotFoundError(self.manifest_path)

        self.manifest = self._read_manifest()
        # Metadata loading is deliberately reused without calling the raw EOD
        # provider's lazy index. The placeholder root is never opened.
        metadata_provider = CompetitionCSVMarketDataProvider(
            self.store_path.parent / "__raw_eod_not_used__",
            catalog_dir=self.catalog_dir,
            source_version=self.source_version,
        )
        self._metadata = {
            item.stock_code: item for item in metadata_provider.iter_listing_metadata()
        }
        self._validate_manifest_identity()

        self._bar_offsets: dict[str, list[tuple[date, int]]] = defaultdict(list)
        self._header: tuple[str, ...] | None = None
        self._store_sha256: str | None = None
        self._manifest_sha256 = sha256_file(self.manifest_path)
        self._invalid_price_rows = 0
        self._duplicate_rows = 0
        self._first_valid_trade_date: date | None = None
        self._last_valid_trade_date: date | None = None
        self._indexed = False

    def _read_manifest(self) -> dict[str, Any]:
        payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("filtered EOD manifest must be a JSON object")
        missing = sorted(_REQUIRED_MANIFEST_FIELDS - set(payload))
        if missing:
            raise ValueError(
                "filtered EOD manifest missing fields: " + ", ".join(missing)
            )
        return payload

    def _cataloged_raw_eod_sha256(self) -> str:
        path = self.catalog_dir / SOURCE_MANIFEST_FILENAME
        if not path.is_file():
            raise FileNotFoundError(path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries = payload.get("entries") if isinstance(payload, dict) else None
        if not isinstance(entries, list):
            raise ValueError("v04 source manifest entries are unavailable")
        matches = [
            item
            for item in entries
            if isinstance(item, dict) and item.get("logical_id") == "ipo_eod"
        ]
        if len(matches) != 1:
            raise ValueError("v04 source manifest must contain exactly one ipo_eod entry")
        checksum = matches[0].get("sha256")
        if not isinstance(checksum, str) or not _SHA256_PATTERN.fullmatch(checksum):
            raise ValueError("cataloged raw EOD SHA-256 is invalid")
        return checksum

    def _validate_manifest_identity(self) -> None:
        if self.manifest["filter_schema_version"] != FILTER_SCHEMA_VERSION:
            raise ValueError("unsupported filtered EOD schema version")
        if self.manifest["selection_policy"] != SELECTION_POLICY:
            raise ValueError("filtered EOD selection policy mismatch")
        if self.manifest["official_listing_years"] != sorted(OFFICIAL_LISTING_YEARS):
            raise ValueError("filtered EOD official listing years mismatch")

        case_ids = sorted(item.case_id for item in self._metadata.values())
        case_ids_hash = hashlib.sha256(
            json.dumps(case_ids, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        expected_count = self.expected_case_count
        if expected_count is not None and len(case_ids) != expected_count:
            raise ValueError(
                f"official cohort drift: expected {expected_count}, found {len(case_ids)}"
            )
        if self.manifest["expected_official_case_count"] != len(case_ids):
            raise ValueError("filtered EOD expected official case count mismatch")
        if self.manifest["target_case_count"] != len(case_ids):
            raise ValueError("filtered EOD target case count mismatch")
        if self.manifest["target_case_ids_sha256"] != case_ids_hash:
            raise ValueError("filtered EOD target case identity mismatch")
        if self.manifest["target_security_count"] != len(self._metadata):
            raise ValueError("filtered EOD target security count mismatch")

        bridge_path = self.catalog_dir / BRIDGE_FILENAME
        if self.manifest["bridge_sha256"] != sha256_file(bridge_path):
            raise ValueError("filtered EOD bridge SHA-256 mismatch")
        raw_hash = self.manifest["raw_eod_sha256"]
        if not isinstance(raw_hash, str) or not _SHA256_PATTERN.fullmatch(raw_hash):
            raise ValueError("filtered EOD raw-source SHA-256 is invalid")
        if raw_hash != self._cataloged_raw_eod_sha256():
            raise ValueError("filtered EOD raw-source identity conflicts with catalog")
        if self.manifest["source_record_id_column"] != "OBJECT_ID":
            raise ValueError("filtered EOD source-record identity is not OBJECT_ID")
        if self.manifest["s_dq_amount_semantics"] != (
            "retained as per-security source column only; never total-market turnover"
        ):
            raise ValueError("filtered EOD S_DQ_AMOUNT semantics mismatch")

    @staticmethod
    def _decode_csv_line(line: bytes) -> list[str]:
        return next(csv.reader([line.decode("utf-8").rstrip("\r\n")]))

    @staticmethod
    def _parse_trade_date(raw: str) -> date:
        return datetime.strptime(raw, "%Y%m%d").date()

    def _validate_scanned_manifest(
        self,
        *,
        row_count: int,
        seen_codes: set[str],
        min_trade_date: str | None,
        max_trade_date: str | None,
    ) -> None:
        checks = {
            "row_count": row_count,
            "distinct_target_securities": len(seen_codes),
            "min_trading_date": min_trade_date,
            "max_trading_date": max_trade_date,
        }
        mismatches = [
            name for name, actual in checks.items() if self.manifest.get(name) != actual
        ]
        if mismatches:
            raise ValueError(
                "filtered EOD manifest/store mismatch: " + ", ".join(mismatches)
            )

    def _ensure_index(self) -> None:
        if self._indexed:
            if self._duplicate_rows:
                raise DuplicateMarketBarError(
                    f"filtered EOD store contains {self._duplicate_rows} duplicate stock/date rows"
                )
            return

        digest = hashlib.sha256()
        seen_keys: set[tuple[str, date]] = set()
        seen_codes: set[str] = set()
        row_count = 0
        min_trade_date: str | None = None
        max_trade_date: str | None = None
        with self.store_path.open("rb") as handle:
            header_line = handle.readline()
            digest.update(header_line)
            header = tuple(self._decode_csv_line(header_line.lstrip(b"\xef\xbb\xbf")))
            if header != OUTPUT_COLUMNS:
                missing = sorted(set(OUTPUT_COLUMNS) - set(header))
                detail = f"; missing={missing}" if missing else ""
                raise ValueError("filtered EOD store schema mismatch" + detail)
            self._header = header

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
                    raise ValueError("filtered EOD row does not match the frozen schema")
                row = dict(zip(header, values))
                row_count += 1
                raw_code = (row.get("S_INFO_WINDCODE") or "").strip()
                try:
                    stock_code = normalize_hk_security_identifier(raw_code)
                except ValueError as exc:
                    raise ValueError("filtered EOD row has invalid stock identity") from exc
                if stock_code not in self._metadata:
                    raise ValueError(
                        f"filtered EOD row is outside the official cohort: {stock_code}"
                    )
                seen_codes.add(stock_code)
                raw_date = (row.get("TRADE_DT") or "").strip()
                if raw_date:
                    min_trade_date = (
                        raw_date
                        if min_trade_date is None
                        else min(min_trade_date, raw_date)
                    )
                    max_trade_date = (
                        raw_date
                        if max_trade_date is None
                        else max(max_trade_date, raw_date)
                    )
                try:
                    trading_date = self._parse_trade_date(raw_date)
                except ValueError:
                    self._invalid_price_rows += 1
                    continue
                key = (stock_code, trading_date)
                if key in seen_keys:
                    self._duplicate_rows += 1
                    continue
                seen_keys.add(key)
                if not CompetitionCSVMarketDataProvider._valid_ohlc(row):
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
        self._store_sha256 = digest.hexdigest()
        if (
            self.expected_store_sha256 is not None
            and self._store_sha256 != self.expected_store_sha256
        ):
            raise ValueError("filtered EOD store SHA-256 mismatch")
        self._validate_scanned_manifest(
            row_count=row_count,
            seen_codes=seen_codes,
            min_trade_date=min_trade_date,
            max_trade_date=max_trade_date,
        )
        self._indexed = True
        if self._duplicate_rows:
            raise DuplicateMarketBarError(
                f"filtered EOD store contains {self._duplicate_rows} duplicate stock/date rows"
            )

    def _row_at_offset(self, handle: BinaryIO, offset: int) -> dict[str, str]:
        if self._header is None:
            raise RuntimeError("filtered EOD index has not been initialized")
        handle.seek(offset)
        values = self._decode_csv_line(handle.readline())
        return dict(zip(self._header, values))

    @property
    def provider_identity(self) -> dict[str, Any]:
        """Return portable provenance for readiness artifacts."""

        self._ensure_index()
        assert self._store_sha256 is not None
        return {
            "provider": self.name,
            "filter_schema_version": FILTER_SCHEMA_VERSION,
            "raw_eod_sha256": self.manifest["raw_eod_sha256"],
            "official_bridge_sha256": self.manifest["bridge_sha256"],
            "filtered_store_sha256": self._store_sha256,
            "filtered_store_manifest_sha256": self._manifest_sha256,
            "filtered_store_row_count": self.manifest["row_count"],
            "filtered_store_filename": self.store_path.name,
            "filtered_store_manifest_filename": self.manifest_path.name,
        }

    def iter_listing_metadata(self) -> tuple[IPOMarketMetadata, ...]:
        return tuple(sorted(self._metadata.values(), key=lambda item: item.case_id))

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
        assert self._store_sha256 is not None
        bars: list[MarketDailyBar] = []
        with self.store_path.open("rb") as handle:
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
                            source_record_id=(row.get("OBJECT_ID") or "").strip()
                            or None,
                            metadata={
                                "source_filename": EOD_FILENAME,
                                "source_sha256": self.manifest["raw_eod_sha256"],
                                "filtered_store_filename": self.store_path.name,
                                "filtered_store_sha256": self._store_sha256,
                                "filtered_store_manifest_sha256": (
                                    self._manifest_sha256
                                ),
                                "filter_schema_version": FILTER_SCHEMA_VERSION,
                            },
                        ),
                    )
                )
        return bars

    def has_daily_bars(self, stock_code: str) -> bool:
        return bool(self.get_daily_bars(stock_code))

    def readiness_report(self) -> CompetitionEODReadinessReport:
        self._ensure_index()
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
            for horizon, sessions in (
                ("1D", 1),
                ("5D", 5),
                ("20D", 20),
                ("60D", 60),
            ):
                horizon_coverage[horizon] += int(len(eligible_dates) >= sessions)
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
            source_sha256=str(self.manifest["raw_eod_sha256"]),
        )

    def get_snapshot(self, profile: IPOProfile) -> MarketSnapshot:
        return MarketSnapshot(
            source="unavailable",
            metadata={
                "available": False,
                "reason": "legacy snapshot is not produced by the filtered EOD adapter",
            },
        )
