"""Governed prior-IPO history for the dynamic (non-frozen) Market-X path.

The frozen PR-B artifacts answer "what was the market context of one of the 438
already materialized cases".  A new prospectus needs the question answered from
the *inputs* instead, so this module exposes the same point-in-time prior-IPO
universe the PR-B builder consumed, in two explicitly separated tiers:

``offer facts``
    issuer identity, listing date, industry and funds raised, read from the
    committed official master bridge.  Public pre-listing facts, always present
    in a checkout, and the only tier the counting/fundraising families need.

``outcomes``
    prior-IPO 1D/5D returns, which are derived from licensed EOD prices and are
    therefore an optional, locally materialized pack.  When the pack is absent
    the outcome families are missing *because their source is not configured* —
    a different fact from an empty sample, and never a zero.

Both boundaries of the universe are carried with it.  A lookback that reaches
before the first governed listing, or a target that lists after the last one,
makes the affected family explicitly missing instead of silently short-counted.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from ipo_risk.market.ipo_market_context_features import content_hash

PRIOR_IPO_HISTORY_SCHEMA_VERSION = "v046_prior_ipo_history_v1"
PRIOR_IPO_OUTCOME_PACK_SCHEMA_VERSION = "v046_prior_ipo_outcome_pack_v1"

# 2025 is the blind cohort: its prospectuses may be analyzed, its *outcomes* may
# not be read back into any feature.  The pack loader fails closed on them.
OUTCOME_COHORT_YEARS = frozenset({2020, 2021, 2022, 2023, 2024})

_BRIDGE_REQUIRED_FIELDS = frozenset(
    {
        "case_id",
        "stock_code_wind",
        "official_listed_date",
    }
)
_OUTCOME_RECORD_FIELDS = (
    "case_id",
    "stock_code",
    "listing_date",
    "target_1d",
    "return_1d",
    "target_5d",
    "return_5d",
)


class PriorIPOHistoryError(ValueError):
    """The governed prior-IPO universe could not be loaded or validated."""


def csv_content_hashes(path: Path) -> frozenset[str]:
    """Return byte hashes that differ only by CSV newline representation.

    The official bridge was frozen from a Windows checkout while Git stores it
    with LF endings.  Both candidates hash the complete file content; no field,
    row or ordering difference is tolerated.
    """

    raw = path.read_bytes()
    lf = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    crlf = lf.replace(b"\n", b"\r\n")
    return frozenset(
        hashlib.sha256(candidate).hexdigest() for candidate in (raw, lf, crlf)
    )


@dataclass(frozen=True, slots=True)
class PriorIPORecord:
    """One prior IPO, with its offer facts and optional governed outcomes."""

    case_id: str
    stock_code: str
    listing_date: date
    industry: str | None = None
    funds_raised: Decimal | None = None
    target_1d: date | None = None
    return_1d: float | None = None
    target_5d: date | None = None
    return_5d: float | None = None

    def as_context_row(self) -> dict[str, Any]:
        """Project into the shape ``build_ipo_market_context`` consumes."""

        return {
            "case_id": self.case_id,
            "stock_code": self.stock_code,
            "listing_date": self.listing_date,
            "industry": self.industry,
            "funds_raised": self.funds_raised,
            "target_1d": self.target_1d,
            "return_1d": self.return_1d,
            "target_5d": self.target_5d,
            "return_5d": self.return_5d,
        }


@dataclass(frozen=True)
class PriorIPOHistory:
    """A complete, bounded prior-IPO universe plus the provenance to prove it."""

    records: tuple[PriorIPORecord, ...]
    history_start_date: date
    history_end_date: date
    outcome_history_available: bool
    outcome_cohort_years: tuple[int, ...]
    provenance: dict[str, Any]

    def rows_before(
        self,
        listing_date: date,
        *,
        exclude_case_ids: frozenset[str] = frozenset(),
        exclude_stock_codes: frozenset[str] = frozenset(),
    ) -> list[dict[str, Any]]:
        """Return strictly pre-listing rows, minus the target's own identity.

        Rows listed after the declared coverage end are dropped rather than
        counted: past that date the corpus is known to be incomplete, and a
        lookback that reaches into it is reported as missing by the builder.
        Keeping the partial tail would turn "we do not know" into a low count.
        """

        return [
            record.as_context_row()
            for record in self.records
            if record.listing_date < listing_date
            and record.listing_date <= self.history_end_date
            and record.case_id not in exclude_case_ids
            and record.stock_code not in exclude_stock_codes
        ]

    def outcome_cohort_covers(self, listing_date: date) -> bool:
        return listing_date.year in set(self.outcome_cohort_years)


def _parse_amount(raw: str | None) -> Decimal | None:
    text = (raw or "").replace(",", "").strip()
    if not text:
        return None
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


def load_official_prior_ipo_history(
    bridge_path: str | Path,
    *,
    outcome_pack_path: str | Path | None = None,
) -> PriorIPOHistory:
    """Load the governed prior-IPO universe from the committed official bridge.

    Only officially matched rows with a listing date participate: an unmatched
    row has no authoritative identity to join on, and guessing one would be
    exactly the fuzzy-name join the governance boundary forbids.
    """

    path = Path(bridge_path)
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = set(reader.fieldnames or ())
            missing = _BRIDGE_REQUIRED_FIELDS - fields
            if missing:
                raise PriorIPOHistoryError(
                    "official bridge missing fields: " + ", ".join(sorted(missing))
                )
            rows = list(reader)
    except OSError as exc:
        raise PriorIPOHistoryError(f"official bridge is unreadable: {exc}") from exc

    records: dict[str, PriorIPORecord] = {}
    source_years: set[int] = set()
    skipped_unmatched = 0
    for row in rows:
        # A bridge without the column is already a matched projection; an
        # unmatched row has no authoritative identity to join on.
        if (row.get("official_match_status") or "matched").strip() != "matched":
            skipped_unmatched += 1
            continue
        raw_listing = (row.get("official_listed_date") or "").strip()
        case_id = (row.get("case_id") or "").strip()
        stock_code = (row.get("stock_code_wind") or "").strip()
        if not raw_listing or not case_id or not stock_code:
            skipped_unmatched += 1
            continue
        try:
            listing_date = date.fromisoformat(raw_listing)
        except ValueError as exc:
            raise PriorIPOHistoryError(
                f"official bridge listing date is invalid for {case_id}"
            ) from exc
        if case_id in records:
            raise PriorIPOHistoryError(f"duplicate official bridge case: {case_id}")
        raw_source_year = (row.get("source_year") or "").strip()
        source_years.add(
            int(raw_source_year) if raw_source_year.isdigit() else listing_date.year
        )
        records[case_id] = PriorIPORecord(
            case_id=case_id,
            stock_code=stock_code,
            listing_date=listing_date,
            industry=(row.get("official_industry_name") or "").strip() or None,
            funds_raised=_parse_amount(row.get("official_funds_raised")),
        )

    if not records:
        raise PriorIPOHistoryError("official bridge contains no matched IPO identity")

    # The corpus is a prospectus universe indexed by source year, so it is
    # complete for listings up to the end of its last source year.  Later
    # listings do appear (a 2025 prospectus can list in 2026) but only for the
    # issuers that already filed, so that tail is explicitly out of coverage.
    history_end_date = date(max(source_years), 12, 31)
    beyond_coverage = sum(
        record.listing_date > history_end_date for record in records.values()
    )

    bridge_hashes = csv_content_hashes(path)
    provenance: dict[str, Any] = {
        "schema_version": PRIOR_IPO_HISTORY_SCHEMA_VERSION,
        "offer_facts_source": "competition_official_master_bridge",
        "offer_facts_source_filename": path.name,
        "official_bridge_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "matched_case_count": len(records),
        "skipped_unmatched_row_count": skipped_unmatched,
        "prior_ipo_history_scope": "official_matched_prospectus_corpus",
        "prior_ipo_history_source_years": sorted(source_years),
        "coverage_end_basis": "last_day_of_last_prospectus_source_year",
        "records_beyond_coverage_end": beyond_coverage,
        "outcome_source": "not_configured",
    }

    outcome_available = False
    if outcome_pack_path:
        outcomes, outcome_provenance = _load_outcome_pack(
            Path(outcome_pack_path),
            bridge_records=records,
            bridge_hashes=bridge_hashes,
        )
        for case_id, outcome in outcomes.items():
            records[case_id] = outcome
        provenance.update(outcome_provenance)
        outcome_available = True

    ordered = tuple(
        sorted(records.values(), key=lambda item: (item.listing_date, item.case_id))
    )
    history_start_date = ordered[0].listing_date
    if history_end_date < history_start_date:
        raise PriorIPOHistoryError(
            "declared coverage end precedes the first governed listing"
        )
    provenance["history_start_date"] = history_start_date.isoformat()
    provenance["history_end_date"] = history_end_date.isoformat()
    return PriorIPOHistory(
        records=ordered,
        history_start_date=history_start_date,
        history_end_date=history_end_date,
        outcome_history_available=outcome_available,
        outcome_cohort_years=tuple(sorted(OUTCOME_COHORT_YEARS)),
        provenance=provenance,
    )


def _load_outcome_pack(
    path: Path,
    *,
    bridge_records: dict[str, PriorIPORecord],
    bridge_hashes: frozenset[str],
) -> tuple[dict[str, PriorIPORecord], dict[str, Any]]:
    """Validate and join a locally materialized prior-IPO outcome pack.

    Every failure here is fail-closed: an outcome pack that cannot prove its
    identity, its bridge lineage or its cohort boundary is not partially used.
    """

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PriorIPOHistoryError(
            f"prior-IPO outcome pack is unreadable: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise PriorIPOHistoryError("prior-IPO outcome pack is not an object")
    if payload.get("schema_version") != PRIOR_IPO_OUTCOME_PACK_SCHEMA_VERSION:
        raise PriorIPOHistoryError("prior-IPO outcome pack schema version mismatch")

    stored_hash = payload.get("content_hash")
    body = {key: value for key, value in payload.items() if key != "content_hash"}
    if stored_hash != content_hash(body):
        raise PriorIPOHistoryError("prior-IPO outcome pack content_hash does not match")
    if payload.get("official_bridge_sha256") not in bridge_hashes:
        raise PriorIPOHistoryError(
            "prior-IPO outcome pack was not derived from this official bridge"
        )

    declared_years = payload.get("outcome_cohort_years")
    if not isinstance(declared_years, list) or set(declared_years) - OUTCOME_COHORT_YEARS:
        raise PriorIPOHistoryError(
            "prior-IPO outcome pack declares a cohort outside the allowed years"
        )

    raw_records = payload.get("records")
    if not isinstance(raw_records, list) or not raw_records:
        raise PriorIPOHistoryError("prior-IPO outcome pack carries no records")

    merged: dict[str, PriorIPORecord] = {}
    for item in raw_records:
        if not isinstance(item, dict) or set(item) != set(_OUTCOME_RECORD_FIELDS):
            raise PriorIPOHistoryError(
                "prior-IPO outcome record does not match the pack schema"
            )
        case_id = str(item["case_id"])
        base = bridge_records.get(case_id)
        if base is None:
            raise PriorIPOHistoryError(
                f"prior-IPO outcome record has no official bridge identity: {case_id}"
            )
        if item["stock_code"] != base.stock_code:
            raise PriorIPOHistoryError(f"outcome stock code mismatch for {case_id}")
        if item["listing_date"] != base.listing_date.isoformat():
            raise PriorIPOHistoryError(f"outcome listing date mismatch for {case_id}")
        if base.listing_date.year not in OUTCOME_COHORT_YEARS:
            raise PriorIPOHistoryError(
                f"outcome record is outside the allowed cohort years: {case_id}"
            )
        target_1d = _parse_optional_date(item["target_1d"], case_id)
        target_5d = _parse_optional_date(item["target_5d"], case_id)
        for target in (target_1d, target_5d):
            if target is not None and target < base.listing_date:
                raise PriorIPOHistoryError(
                    f"outcome target session precedes the listing date: {case_id}"
                )
        merged[case_id] = PriorIPORecord(
            case_id=base.case_id,
            stock_code=base.stock_code,
            listing_date=base.listing_date,
            industry=base.industry,
            funds_raised=base.funds_raised,
            target_1d=target_1d,
            return_1d=_parse_optional_float(item["return_1d"], case_id),
            target_5d=target_5d,
            return_5d=_parse_optional_float(item["return_5d"], case_id),
        )

    provenance = {
        "outcome_source": payload.get("outcome_source") or "governed_ipo_eod_derived",
        "outcome_pack_filename": path.name,
        "outcome_pack_schema_version": PRIOR_IPO_OUTCOME_PACK_SCHEMA_VERSION,
        "outcome_pack_content_hash": stored_hash,
        "outcome_pack_record_count": len(merged),
        "outcome_cohort_years": sorted(declared_years),
        "ipo_eod_sha256": payload.get("ipo_eod_sha256"),
        "blind_outcomes_included": False,
    }
    return merged, provenance


def _parse_optional_date(value: Any, case_id: str) -> date | None:
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise PriorIPOHistoryError(
            f"outcome target session date is invalid for {case_id}"
        ) from exc


def _parse_optional_float(value: Any, case_id: str) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise PriorIPOHistoryError(
            f"outcome return is not numeric for {case_id}"
        ) from exc
