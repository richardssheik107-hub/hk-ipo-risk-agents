"""Versioned source inventory and identifier-audit contracts for V04 data."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Any, Iterable, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


V04_SOURCE_MANIFEST_VERSION = "v04_source_manifest_v1"


class SourceAvailability(StrEnum):
    AVAILABLE = "available"
    MISSING = "missing"
    BLOCKED = "blocked"
    NOT_REQUIRED = "not_required"


class V04SourceManifestEntry(BaseModel):
    """One logical source without machine-local path leakage."""

    model_config = ConfigDict(frozen=True)

    source_name: str = Field(min_length=1)
    logical_id: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    relative_path: str | None = None
    coverage: dict[str, Any] = Field(default_factory=dict)
    availability: SourceAvailability
    provenance: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source_name", "logical_id", "dataset_version")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("relative_path")
    @classmethod
    def require_portable_relative_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().replace("\\", "/")
        path = PurePosixPath(normalized)
        if not normalized or path.is_absolute() or ":" in normalized or ".." in path.parts:
            raise ValueError("source manifest paths must be portable relative paths")
        return normalized

    @model_validator(mode="after")
    def validate_availability_payload(self) -> "V04SourceManifestEntry":
        if self.availability is SourceAvailability.AVAILABLE and self.sha256 is None:
            raise ValueError("available sources require a SHA-256")
        if self.availability is SourceAvailability.MISSING:
            if self.sha256 is not None or self.relative_path is not None:
                raise ValueError("missing sources cannot claim a file or checksum")
        return self


class V04SourceManifest(BaseModel):
    """Deterministic inventory of every source required by V04 materialization."""

    model_config = ConfigDict(frozen=True)

    manifest_version: str = V04_SOURCE_MANIFEST_VERSION
    entries: tuple[V04SourceManifestEntry, ...]

    @model_validator(mode="after")
    def validate_manifest(self) -> "V04SourceManifest":
        if self.manifest_version != V04_SOURCE_MANIFEST_VERSION:
            raise ValueError("unsupported V04 source manifest version")
        logical_ids = [entry.logical_id for entry in self.entries]
        if len(logical_ids) != len(set(logical_ids)):
            raise ValueError("source manifest logical IDs must be unique")
        if logical_ids != sorted(logical_ids):
            raise ValueError("source manifest entries must use stable logical-ID order")
        return self

    def canonical_json(self) -> str:
        return json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def content_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


class SecurityIdentifierAudit(BaseModel):
    """Read-only audit explaining whether a security-master join is authoritative."""

    model_config = ConfigDict(frozen=True)

    ipo_total: int = Field(ge=0)
    security_master_total: int = Field(ge=0)
    exact_wind_matches: int = Field(ge=0)
    normalized_code_matches: int = Field(ge=0)
    security_id_matches: int = Field(ge=0)
    institution_id_matches: int = Field(ge=0)
    matched_case_ids: tuple[str, ...]
    unmatched_case_ids: tuple[str, ...]

    @property
    def matched(self) -> int:
        return len(self.matched_case_ids)


def normalize_hk_security_identifier(value: str) -> str:
    """Normalize competition/Wind HK stock identifiers without inferring type."""

    token = value.strip().upper()
    if not token:
        raise ValueError("security identifier is required")
    if "." in token:
        code, suffix = token.rsplit(".", 1)
        if suffix != "HK":
            raise ValueError("only HK security identifiers are supported")
        token = code
    if not token.isdigit() or len(token) > 5:
        raise ValueError("HK security identifier must contain at most five digits")
    numeric = int(token)
    width = 4 if numeric <= 9999 else 5
    return f"{numeric:0{width}d}.HK"


def audit_security_identifiers(
    ipo_rows: Iterable[Mapping[str, str]],
    security_rows: Iterable[Mapping[str, str]],
) -> SecurityIdentifierAudit:
    """Try every supplied authoritative identifier before declaring a source gap."""

    ipos = list(ipo_rows)
    securities = list(security_rows)

    def values(rows: Iterable[Mapping[str, str]], key: str) -> set[str]:
        return {
            str(row.get(key) or "").strip().upper()
            for row in rows
            if str(row.get(key) or "").strip()
        }

    security_wind = values(securities, "S_INFO_WINDCODE")
    security_ids = values(securities, "OBJECT_ID")
    company_ids = values(securities, "S_INFO_COMPCODE")
    normalized_security_codes: set[str] = set()
    for value in values(securities, "S_INFO_CODE") | security_wind:
        try:
            normalized_security_codes.add(normalize_hk_security_identifier(value))
        except ValueError:
            # A malformed or non-HK source identifier must not abort the audit or
            # become an inferred match through lossy normalization.
            continue

    exact_wind_matches = 0
    normalized_code_matches = 0
    security_id_matches = 0
    institution_id_matches = 0
    matched: list[str] = []
    unmatched: list[str] = []
    for row in ipos:
        case_id = str(row.get("case_id") or "").strip()
        wind = str(row.get("stock_code_wind") or "").strip().upper()
        raw = str(row.get("stock_code_raw") or "").strip()
        security_id = str(row.get("security_id") or "").strip().upper()
        institution_id = str(row.get("institution_id") or "").strip().upper()
        exact = bool(wind and wind in security_wind)
        normalized = False
        for candidate in (wind, raw):
            if candidate:
                try:
                    normalized = (
                        normalize_hk_security_identifier(candidate)
                        in normalized_security_codes
                    )
                except ValueError:
                    normalized = False
                if normalized:
                    break
        by_security_id = bool(security_id and security_id in security_ids)
        by_institution_id = bool(institution_id and institution_id in company_ids)
        exact_wind_matches += int(exact)
        normalized_code_matches += int(normalized)
        security_id_matches += int(by_security_id)
        institution_id_matches += int(by_institution_id)
        (matched if any((exact, normalized, by_security_id, by_institution_id)) else unmatched).append(
            case_id
        )

    return SecurityIdentifierAudit(
        ipo_total=len(ipos),
        security_master_total=len(securities),
        exact_wind_matches=exact_wind_matches,
        normalized_code_matches=normalized_code_matches,
        security_id_matches=security_id_matches,
        institution_id_matches=institution_id_matches,
        matched_case_ids=tuple(sorted(matched)),
        unmatched_case_ids=tuple(sorted(unmatched)),
    )
