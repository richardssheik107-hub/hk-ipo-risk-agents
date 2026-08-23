"""Governed loader/provider for a normalized CSMAR Hang Seng Index series.

The licensed CSMAR workbook is never a runtime API.  A local preparation step
copies the HSI rows into an ignored, deterministic normalized CSV while this
module validates that cache and exposes only ``MarketReferenceBar`` records.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ipo_risk.schemas.market import MarketDataProvenance
from ipo_risk.schemas.market_features import MarketReferenceBar


CSMAR_HSI_REFERENCE_ID = "HSI"
CSMAR_HSI_SOURCE_ID = "CSMAR"
CSMAR_HSI_DATASET_NAME = "国际指数日行情文件"
CSMAR_HSI_NORMALIZED_SCHEMA_VERSION = "csmar_hsi_daily_close_v1"
CSMAR_HSI_REQUIRED_COLUMNS = (
    "reference_id",
    "trading_date",
    "open",
    "high",
    "low",
    "close",
    "constituent_volume",
    "index_return",
    "source_record_id",
    "source_id",
    "source_version",
    "project_generated_identity",
)


class CSMARHSIError(ValueError):
    """Raised when a normalized CSMAR HSI asset fails governance checks."""


class CSMARHSISourceManifest(BaseModel):
    """License-safe metadata for one accepted CSMAR HSI source workbook."""

    model_config = ConfigDict(frozen=True)

    manifest_version: str = "csmar_hsi_source_manifest_v1"
    source_name: str = CSMAR_HSI_SOURCE_ID
    dataset_name: str = CSMAR_HSI_DATASET_NAME
    reference_id: str = CSMAR_HSI_REFERENCE_ID
    series_name: str = "恒生指数"
    frequency: str = "daily"
    series_type: str
    series_type_status: str
    source_file_name: str
    source_archive_name: str
    source_archive_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    normalized_schema_version: str = CSMAR_HSI_NORMALIZED_SCHEMA_VERSION
    normalized_file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    row_count: int = Field(gt=0)
    coverage_start: date
    coverage_end: date
    duplicate_count: int = Field(ge=0)
    null_close_count: int = Field(ge=0)
    invalid_close_count: int = Field(ge=0)
    parse_error_count: int = Field(ge=0)
    retrieval_metadata: dict[str, Any] = Field(default_factory=dict)
    license_notice: str
    project_generated_identity: bool = True

    @model_validator(mode="after")
    def validate_accepted_source(self) -> "CSMARHSISourceManifest":
        if self.manifest_version != "csmar_hsi_source_manifest_v1":
            raise ValueError("unsupported CSMAR HSI manifest version")
        if self.reference_id != CSMAR_HSI_REFERENCE_ID:
            raise ValueError("CSMAR HSI manifest must identify HSI")
        if self.source_name != CSMAR_HSI_SOURCE_ID:
            raise ValueError("CSMAR HSI source must be CSMAR")
        if self.normalized_schema_version != CSMAR_HSI_NORMALIZED_SCHEMA_VERSION:
            raise ValueError("unsupported CSMAR HSI normalized schema")
        if self.coverage_end < self.coverage_start:
            raise ValueError("CSMAR HSI coverage is reversed")
        if any(
            (
                self.duplicate_count,
                self.null_close_count,
                self.invalid_close_count,
                self.parse_error_count,
            )
        ):
            raise ValueError("accepted CSMAR HSI manifest contains invalid rows")
        if not self.project_generated_identity:
            raise ValueError("normalized source record IDs must be declared project-generated")
        return self

    @classmethod
    def from_path(cls, path: Path) -> "CSMARHSISourceManifest":
        return cls.model_validate_json(path.read_text(encoding="utf-8"))

    def source_version(self) -> str:
        return (
            f"{CSMAR_HSI_NORMALIZED_SCHEMA_VERSION}:"
            f"{self.source_archive_sha256[:12]}:{self.source_file_sha256[:12]}"
        )


def sha256_file(path: Path) -> str:
    """Return the lowercase SHA-256 of a local file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_positive_decimal(raw: str, *, row_number: int) -> Decimal:
    value = raw.strip().replace(",", "")
    if not value:
        raise CSMARHSIError(f"missing close at normalized row {row_number}")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise CSMARHSIError(
            f"invalid close at normalized row {row_number}: {raw!r}"
        ) from exc
    if not parsed.is_finite() or parsed <= 0:
        raise CSMARHSIError(
            f"close must be finite and positive at normalized row {row_number}"
        )
    return parsed


def load_csmar_hsi_bars(
    normalized_csv: Path,
    manifest: CSMARHSISourceManifest,
) -> tuple[MarketReferenceBar, ...]:
    """Validate a normalized cache and return deterministically ordered HSI bars."""

    if not normalized_csv.is_file():
        raise FileNotFoundError(normalized_csv)
    actual_sha = sha256_file(normalized_csv)
    if actual_sha != manifest.normalized_file_sha256:
        raise CSMARHSIError(
            "normalized CSMAR HSI hash mismatch: "
            f"expected {manifest.normalized_file_sha256}, found {actual_sha}"
        )

    with normalized_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != CSMAR_HSI_REQUIRED_COLUMNS:
            raise CSMARHSIError(
                "normalized CSMAR HSI columns differ from the governed schema"
            )
        rows = list(reader)

    if len(rows) != manifest.row_count:
        raise CSMARHSIError(
            f"normalized CSMAR HSI row count mismatch: {len(rows)} != {manifest.row_count}"
        )

    bars: list[MarketReferenceBar] = []
    seen_dates: set[date] = set()
    expected_source_version = manifest.source_version()
    for row_number, row in enumerate(rows, start=2):
        reference_id = (row.get("reference_id") or "").strip()
        if reference_id != CSMAR_HSI_REFERENCE_ID:
            raise CSMARHSIError(
                f"unexpected reference_id at normalized row {row_number}: {reference_id!r}"
            )
        if (row.get("source_id") or "").strip() != CSMAR_HSI_SOURCE_ID:
            raise CSMARHSIError(f"unexpected source_id at normalized row {row_number}")
        if (row.get("source_version") or "").strip() != expected_source_version:
            raise CSMARHSIError(f"source_version mismatch at normalized row {row_number}")
        if (row.get("project_generated_identity") or "").strip().lower() != "true":
            raise CSMARHSIError(
                f"project-generated identity flag missing at normalized row {row_number}"
            )
        try:
            trading_date = date.fromisoformat((row.get("trading_date") or "").strip())
        except ValueError as exc:
            raise CSMARHSIError(
                f"invalid trading date at normalized row {row_number}"
            ) from exc
        if trading_date in seen_dates:
            raise CSMARHSIError(f"duplicate HSI trading date: {trading_date}")
        seen_dates.add(trading_date)
        close = _parse_positive_decimal(row.get("close") or "", row_number=row_number)
        source_record_id = (row.get("source_record_id") or "").strip()
        if not source_record_id:
            raise CSMARHSIError(
                f"source_record_id missing at normalized row {row_number}"
            )
        bars.append(
            MarketReferenceBar(
                reference_id=CSMAR_HSI_REFERENCE_ID,
                trading_date=trading_date,
                close=close,
                provenance=MarketDataProvenance(
                    source=CSMAR_HSI_SOURCE_ID,
                    dataset_version=expected_source_version,
                    source_record_id=source_record_id,
                    metadata={
                        "dataset_name": CSMAR_HSI_DATASET_NAME,
                        "source_archive_name": manifest.source_archive_name,
                        "source_archive_sha256": manifest.source_archive_sha256,
                        "source_file_name": manifest.source_file_name,
                        "source_file_sha256": manifest.source_file_sha256,
                        "project_generated_identity": True,
                    },
                ),
            )
        )

    bars.sort(key=lambda item: item.trading_date)
    if bars[0].trading_date != manifest.coverage_start:
        raise CSMARHSIError("normalized HSI coverage start differs from manifest")
    if bars[-1].trading_date != manifest.coverage_end:
        raise CSMARHSIError("normalized HSI coverage end differs from manifest")
    return tuple(bars)


class CSMARHSIProvider:
    """Point-in-time provider over one accepted normalized CSMAR HSI cache."""

    def __init__(
        self,
        normalized_csv: Path,
        manifest: CSMARHSISourceManifest | Path,
    ) -> None:
        self.manifest = (
            CSMARHSISourceManifest.from_path(manifest)
            if isinstance(manifest, Path)
            else manifest
        )
        self._bars = load_csmar_hsi_bars(normalized_csv, self.manifest)

    def get_benchmark_bars(
        self,
        reference_id: str,
        *,
        end_date_exclusive: date,
    ) -> tuple[MarketReferenceBar, ...]:
        """Return observed HSI sessions strictly before the requested cutoff."""

        if reference_id != CSMAR_HSI_REFERENCE_ID:
            raise CSMARHSIError(
                f"CSMAR HSI provider cannot serve reference_id={reference_id!r}"
            )
        return tuple(
            bar for bar in self._bars if bar.trading_date < end_date_exclusive
        )

    def iter_all_bars(self) -> Iterable[MarketReferenceBar]:
        """Yield all governed rows in deterministic trading-date order."""

        return iter(self._bars)
