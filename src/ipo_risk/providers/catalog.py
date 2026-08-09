"""Catalog-backed IPO data provider for the v0.3 multi-agent slice.

Turns the frozen ``data/catalog/ipo_official_master_bridge.csv`` master bridge
into stable :class:`~ipo_risk.schemas.IPOProfile` objects. The 562 officially
matched cases load with full identity and offering facts; the three unmatched
placeholder securities degrade honestly (identity only, no fabricated financials)
and carry explicit special-securities governance in ``IPOProfile.metadata``.

The provider only reads committed catalog CSVs and never guesses a missing
value. It implements the ``IPODataProvider`` protocol (``get_profile``) and adds
``get_by_case_id`` / ``get_by_stock_code`` / ``get_by_stock_code_and_year`` for
batch and evaluation callers. Special-securities governance lives in metadata so
the public Schema stays unchanged (see V03_DEVELOPMENT_CONTRACT §7).
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from ipo_risk.schemas import IPOProfile

DEFAULT_CATALOG_DIR = Path("data/catalog")
BRIDGE_FILENAME = "ipo_official_master_bridge.csv"
PROSPECTUS_MANIFEST_FILENAME = "ipo_prospectus_manifest.csv"

MATCHED_STATUS = "matched"
PLACEHOLDER_STATUS = "manifest_only_placeholder"


@dataclass(frozen=True)
class SpecialSecurity:
    """Governance record for a non-ordinary-equity IPO line.

    ``ordinary_equity_eligible`` gates whether the line belongs to the ordinary
    post-listing equity risk/label universe; ``market_label_eligible`` gates
    whether the line itself can carry v0.4 post-listing market labels (a REIT
    trades on its own line, a SPAC warrant is analysed through its A-share).
    """

    stock_code: str
    security_category: str
    canonical_stock_code: str
    related_warrant_code: str | None
    ordinary_equity_eligible: bool
    market_label_eligible: bool
    special_case_reason: str


# Source of truth for the three governed special securities. Keyed by Wind code.
# Mirrors the v0.3 five-person plan's special-securities table (member #2 task).
SPECIAL_SECURITIES: dict[str, SpecialSecurity] = {
    "2191.HK": SpecialSecurity(
        stock_code="2191.HK",
        security_category="reit_units",
        canonical_stock_code="2191.HK",
        related_warrant_code=None,
        ordinary_equity_eligible=False,
        market_label_eligible=True,
        special_case_reason=(
            "REIT fund units (順豐房託): retain code 2191.HK and flag as REIT; "
            "exclude from the ordinary-equity risk universe but keep it eligible "
            "for its own post-listing market labels."
        ),
    ),
    "4801.HK": SpecialSecurity(
        stock_code="4801.HK",
        security_category="spac_warrant",
        canonical_stock_code="7801.HK",
        related_warrant_code="4801.HK",
        ordinary_equity_eligible=False,
        market_label_eligible=False,
        special_case_reason=(
            "SPAC listing warrant: analyse through the paired SPAC A-shares "
            "7801.HK (Interra Acquisition); the warrant line itself is not "
            "ordinary equity and does not carry standalone market labels."
        ),
    ),
    "4841.HK": SpecialSecurity(
        stock_code="4841.HK",
        security_category="spac_warrant",
        canonical_stock_code="7841.HK",
        related_warrant_code="4841.HK",
        ordinary_equity_eligible=False,
        market_label_eligible=False,
        special_case_reason=(
            "SPAC listing warrant: analyse through the paired SPAC A-shares "
            "7841.HK (匯德收購); the warrant line itself is not ordinary equity "
            "and does not carry standalone market labels."
        ),
    ),
}


def governance_table() -> list[dict[str, object]]:
    """Return the special-securities governance table as plain dict rows."""
    return [asdict(record) for record in SPECIAL_SECURITIES.values()]


def _canonical_code_key(code: str) -> str:
    """Collapse ``02410`` / ``2410`` / ``2410.HK`` to one comparable key."""
    token = code.strip().upper()
    if not token:
        return ""
    token = token.removesuffix(".HK")
    if token.isdigit():
        return str(int(token))
    return token


def _parse_amount(raw: str) -> float | None:
    """Parse a thousands-separated amount such as ``"126,000,000"``."""
    token = (raw or "").replace(",", "").strip()
    if not token:
        return None
    try:
        return float(token)
    except ValueError:
        return None


def _parse_date(raw: str) -> date | None:
    token = (raw or "").strip()
    if not token:
        return None
    try:
        return date.fromisoformat(token)
    except ValueError:
        return None


class CatalogIPODataProvider:
    """Read committed catalog CSVs and emit stable IPOProfiles.

    Parameters mirror the frozen v0.2 data governance layout so tests can point
    the provider at a tiny fixture catalog.
    """

    name = "catalog"

    def __init__(
        self,
        catalog_dir: str | Path = DEFAULT_CATALOG_DIR,
        *,
        bridge_path: str | Path | None = None,
        prospectus_manifest_path: str | Path | None = None,
    ) -> None:
        catalog_dir = Path(catalog_dir)
        self.bridge_path = Path(bridge_path or catalog_dir / BRIDGE_FILENAME)
        self.prospectus_manifest_path = Path(
            prospectus_manifest_path or catalog_dir / PROSPECTUS_MANIFEST_FILENAME
        )
        self._rows: list[dict[str, str]] = self._read_csv(self.bridge_path)
        self._manifest: dict[str, dict[str, str]] = {
            row["case_id"]: row
            for row in self._read_csv(self.prospectus_manifest_path)
        }
        self._by_case_id: dict[str, dict[str, str]] = {}
        self._by_code_key: dict[str, dict[str, str]] = {}
        self._by_code_year: dict[tuple[str, str], dict[str, str]] = {}
        self._by_name: dict[str, dict[str, str]] = {}
        for row in self._rows:
            self._index_row(row)

    # -- loading & indexing ------------------------------------------------

    @staticmethod
    def _read_csv(path: Path) -> list[dict[str, str]]:
        if not path.is_file():
            raise FileNotFoundError(f"catalog file not found: {path}")
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    def _index_row(self, row: dict[str, str]) -> None:
        case_id = row["case_id"]
        self._by_case_id[case_id] = row
        for code in (row.get("stock_code_wind", ""), row.get("stock_code_raw", "")):
            key = _canonical_code_key(code)
            if key:
                self._by_code_key.setdefault(key, row)
                self._by_code_year.setdefault((key, row.get("source_year", "")), row)
        name = self._company_name_for(row)
        if name:
            self._by_name.setdefault(name, row)

    def _company_name_for(self, row: dict[str, str]) -> str:
        """Official name when matched, else the disclosed prospectus short name."""
        official = (row.get("selected_name") or "").strip()
        if official:
            return official
        manifest_row = self._manifest.get(row["case_id"], {})
        return (manifest_row.get("company_short_name") or "").strip()

    # -- row -> profile ----------------------------------------------------

    def _row_to_profile(self, row: dict[str, str]) -> IPOProfile:
        status = row.get("official_match_status", "")
        matched = status == MATCHED_STATUS
        wind_code = (row.get("stock_code_wind") or "").strip()
        manifest_row = self._manifest.get(row["case_id"], {})

        metadata: dict[str, object] = {
            "source": "catalog",
            "case_id": row["case_id"],
            "source_year": row.get("source_year", ""),
            "stock_code_raw": row.get("stock_code_raw", ""),
            "dataset_split": row.get("dataset_split", ""),
            "official_match_status": status,
            "official_match_method": row.get("official_match_method", ""),
            "data_complete": matched,
            "eod_available": (row.get("eod_available", "").strip().lower() == "true"),
        }
        if not matched:
            metadata["degradation_reason"] = (
                row.get("notes") or "official master match unavailable"
            )

        # Offering facts are only trustworthy for officially matched rows.
        if matched:
            metadata["offer_price"] = _parse_amount(row.get("official_offer_price", ""))
            metadata["net_proceed"] = _parse_amount(row.get("official_net_proceed", ""))
            metadata["listing_board_id"] = (row.get("official_listing_board_id") or "").strip()
            metadata["list_method"] = (row.get("official_list_method") or "").strip()

        # Prospectus manifest cross-reference (locates the PDF for batch runs).
        if manifest_row:
            metadata["prospectus_relative_path"] = manifest_row.get("relative_path", "")
            metadata["prospectus_sha256"] = manifest_row.get("sha256", "")
            metadata["pdf_page_count"] = manifest_row.get("pdf_page_count", "")

        # Special-securities governance (member #2 task) — metadata only.
        special = SPECIAL_SECURITIES.get(wind_code)
        if special is not None:
            metadata["special_security"] = {
                "security_category": special.security_category,
                "canonical_stock_code": special.canonical_stock_code,
                "related_warrant_code": special.related_warrant_code,
                "ordinary_equity_eligible": special.ordinary_equity_eligible,
                "market_label_eligible": special.market_label_eligible,
                "special_case_reason": special.special_case_reason,
            }

        return IPOProfile(
            company_name=self._company_name_for(row),
            stock_code=wind_code,
            listing_date=_parse_date(row.get("official_listed_date", "")) if matched else None,
            industry=(row.get("official_industry_name") or "").strip() if matched else "",
            issue_price=_parse_amount(row.get("official_ipo_price", "")) if matched else None,
            issue_size=_parse_amount(row.get("official_funds_raised", "")) if matched else None,
            metadata=metadata,
        )

    # -- public query API --------------------------------------------------

    def get_by_case_id(self, case_id: str) -> IPOProfile:
        """Look up a case by its frozen ``ipo_<year>_<code>`` id."""
        try:
            row = self._by_case_id[case_id]
        except KeyError as exc:
            raise KeyError(f"unknown case_id: {case_id!r}") from exc
        return self._row_to_profile(row)

    def get_by_stock_code(self, stock_code: str) -> IPOProfile:
        """Look up by Wind or raw code (``2410.HK`` / ``02410`` / ``2410``)."""
        key = _canonical_code_key(stock_code)
        try:
            row = self._by_code_key[key]
        except KeyError as exc:
            raise KeyError(f"unknown stock_code: {stock_code!r}") from exc
        return self._row_to_profile(row)

    def get_by_stock_code_and_year(self, stock_code: str, year: int | str) -> IPOProfile:
        """Disambiguate a reused code by source year."""
        key = (_canonical_code_key(stock_code), str(year))
        try:
            row = self._by_code_year[key]
        except KeyError as exc:
            raise KeyError(
                f"unknown stock_code/year: {stock_code!r}/{year}"
            ) from exc
        return self._row_to_profile(row)

    def get_profile(self, company_name: str, stock_code: str = "") -> IPOProfile:
        """IPODataProvider protocol entry point with honest degradation.

        Resolves by stock code first, then company name. A genuinely unknown
        identity returns an identity-only profile flagged ``not_in_catalog``
        rather than fabricating offering facts.
        """
        row: dict[str, str] | None = None
        if stock_code:
            row = self._by_code_key.get(_canonical_code_key(stock_code))
        if row is None and company_name:
            row = self._by_name.get(company_name.strip())
        if row is not None:
            return self._row_to_profile(row)
        return IPOProfile(
            company_name=company_name,
            stock_code=stock_code,
            metadata={
                "source": "catalog",
                "official_match_status": "not_in_catalog",
                "data_complete": False,
                "degradation_reason": "no catalog row for requested identity",
            },
        )

    # -- iteration helpers -------------------------------------------------

    def case_ids(self) -> list[str]:
        return [row["case_id"] for row in self._rows]

    def iter_profiles(self):
        for row in self._rows:
            yield self._row_to_profile(row)

    def __len__(self) -> int:
        return len(self._rows)
