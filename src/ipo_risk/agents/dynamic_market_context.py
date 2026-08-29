"""Dynamic point-in-time Market-X for IPOs outside the frozen PR-B universe.

``GovernedPRBMarketContextProvider`` answers the question for the 438 already
materialized cases by *reading* a frozen artifact.  A new prospectus has no
artifact to read, so this provider recomputes the same 15-name Market-X Core
contract from the governed prior-IPO universe, under the same strictly
pre-listing cutoff.

Three properties make the result usable rather than decorative:

* it never invents a cutoff.  Without a target listing date there is no
  point-in-time boundary, and using today's date instead would silently
  contaminate the window, so the channel is unavailable and says so;
* it reports the same frozen feature schema, order and manifest hash, so the
  model lane can build a frozen model input from a dynamic case;
* every absent feature carries the reason it is absent -- an incomplete
  universe boundary, an unconfigured outcome source, withheld blind-cohort
  outcomes, a missing industry, or a genuinely empty sample.  None of them is
  ever a zero.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from ipo_risk.agents.market_context import (
    FAILURE_IDENTITY_MISMATCH,
    FAILURE_OTHER,
)
from ipo_risk.market.dynamic_extended import (
    DynamicExtendedMarketError,
    DynamicExtendedMarketSource,
)
from ipo_risk.market.ipo_market_context_features import (
    IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
    IPO_MARKET_CONTEXT_FEATURE_POLICY_VERSION,
    IPO_MARKET_CONTEXT_FEATURE_SCHEMA_VERSION,
    IPO_MARKET_CONTEXT_FEATURE_UNITS,
    IPO_MARKET_CONTEXT_MISSING_OUTCOME_SAMPLE,
    IPO_MARKET_CONTEXT_MISSING_SAME_INDUSTRY_OUTCOME_SAMPLE,
    IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER,
    build_ipo_market_context_with_reasons,
    content_hash,
    vectorize_ipo_market_context,
)
from ipo_risk.market.prior_ipo_history import (
    PriorIPOHistory,
    PriorIPOHistoryError,
    load_official_prior_ipo_history,
)
from ipo_risk.schemas import IPOProfile, MarketSnapshot
from ipo_risk.schemas.final_supervision import (
    ChannelStatus,
    MarketContextView,
    MarketObservation,
)
from ipo_risk.schemas.market import expected_market_split

DYNAMIC_MARKET_X_SOURCE = "dynamic_market_x_core"
DYNAMIC_MARKET_X_DERIVATION = "dynamic point-in-time Market-X Core feature"
CUTOFF_SEMANTICS = "market_data_strictly_before_listing_date"

# Prior IPOs exist in the window, but they belong to the blind cohort whose
# outcomes policy forbids reading back.  That is a governance fact, not an
# empty sample, and the two must not be reported with the same words.
MISSING_BLIND_COHORT_WITHHELD = "prior_ipo_outcomes_withheld_blind_cohort"

_RECENT_OUTCOME_FEATURES = (
    "recent_ipo_break_rate",
    "recent_ipo_return_5d",
    "recent_ipo_1d_sample_count",
    "recent_ipo_5d_sample_count",
)
_SAME_INDUSTRY_OUTCOME_FEATURES = (
    "same_industry_recent_break_rate",
    "same_industry_recent_return_5d",
    "same_industry_recent_1d_sample_count",
    "same_industry_recent_5d_sample_count",
)
_IDENTITY_FAILURE = re.compile(
    "|".join(
        (
            "resolves to",
            "lists on",
            "not present in the governed universe",
            "disagrees with the governed identity",
            "duplicate official bridge case",
        )
    )
)
_EMPTY_SAMPLE_REASONS = frozenset(
    {
        IPO_MARKET_CONTEXT_MISSING_OUTCOME_SAMPLE,
        IPO_MARKET_CONTEXT_MISSING_SAME_INDUSTRY_OUTCOME_SAMPLE,
    }
)


class DynamicPITMarketContextProvider:
    """Recompute Market-X Core for any identified IPO with a listing date."""

    name = "dynamic_pit_market_x"

    def __init__(
        self,
        *,
        official_bridge_path: str | Path,
        outcome_pack_path: str | Path | None = None,
        extended_source: DynamicExtendedMarketSource | None = None,
    ) -> None:
        self.official_bridge_path = Path(official_bridge_path)
        self.outcome_pack_path = (
            Path(outcome_pack_path) if outcome_pack_path else None
        )
        # Optional: governed HSI / turnover context for the same cutoff. Absent,
        # the six Extended names do not appear at all, which is not the same
        # claim as reporting them unavailable from a source never consulted.
        self.extended_source = extended_source
        self._history: PriorIPOHistory | None = None

    def history(self) -> PriorIPOHistory:
        """Load the governed universe once; a load failure is not cached."""

        if self._history is None:
            self._history = load_official_prior_ipo_history(
                self.official_bridge_path,
                outcome_pack_path=self.outcome_pack_path,
            )
        return self._history

    def context(
        self,
        profile: IPOProfile,
        market: MarketSnapshot | None = None,
    ) -> MarketContextView:
        del market
        if profile.listing_date is None:
            return self._identity_incomplete(profile)
        try:
            history = self.history()
            resolved = self._resolve_identity(profile, history)
            view = self._build(profile, history, resolved)
        except PriorIPOHistoryError as exc:
            return MarketContextView(
                status=ChannelStatus.UNAVAILABLE_ERROR,
                reason=f"dynamic Market-X governed history failed validation: {exc}",
                provenance={
                    "feature_pipeline": self.name,
                    "runtime_path": "dynamic_pit",
                    "reason_code": "governed_history_invalid",
                    "frozen_artifact_read_attempted": False,
                    "failure_code": (
                        FAILURE_IDENTITY_MISMATCH
                        if _IDENTITY_FAILURE.search(str(exc))
                        else FAILURE_OTHER
                    ),
                },
            )
        return view

    # -- identity ----------------------------------------------------------

    def _identity_incomplete(self, profile: IPOProfile) -> MarketContextView:
        """No listing date means no cutoff; today's date is not a substitute."""

        return MarketContextView(
            status=ChannelStatus.UNAVAILABLE,
            reason=(
                "dynamic Market-X requires the target listing date as its "
                "point-in-time cutoff; no cutoff is inferred from the clock"
            ),
            provenance={
                "feature_pipeline": self.name,
                "runtime_path": "dynamic_pit",
                "reason_code": "new_case_identity_incomplete",
                "missing_identity_fields": ["listing_date"],
                "frozen_artifact_read_attempted": False,
                "stock_code": profile.stock_code or None,
                "listing_date": None,
                "cutoff_semantics": CUTOFF_SEMANTICS,
            },
        )

    @staticmethod
    def _resolve_identity(
        profile: IPOProfile,
        history: PriorIPOHistory,
    ) -> dict[str, Any]:
        """Join the target onto governed identity, or accept it as truly new.

        The join is on ``case_id`` or on ``stock_code`` + ``listing_date`` --
        never on company name.  A governed row that disagrees with the supplied
        identity fails closed rather than resolving to the nearest match.
        """

        assert profile.listing_date is not None
        case_id = str(profile.metadata.get("case_id") or "").strip()
        by_case = {record.case_id: record for record in history.records}
        match = by_case.get(case_id) if case_id else None
        if match is not None:
            if profile.stock_code and match.stock_code != profile.stock_code:
                raise PriorIPOHistoryError(
                    f"case {case_id} resolves to {match.stock_code}, "
                    f"not {profile.stock_code}"
                )
            if match.listing_date != profile.listing_date:
                raise PriorIPOHistoryError(
                    f"case {case_id} lists on {match.listing_date.isoformat()}, "
                    f"not {profile.listing_date.isoformat()}"
                )
            return {"record": match, "identity_source": "official_bridge_case_id"}

        if profile.stock_code:
            candidates = [
                record
                for record in history.records
                if record.stock_code == profile.stock_code
                and record.listing_date == profile.listing_date
            ]
            if len(candidates) > 1:
                raise PriorIPOHistoryError(
                    "supplied identity resolves to multiple governed IPO cases"
                )
            if candidates:
                if case_id and candidates[0].case_id != case_id:
                    raise PriorIPOHistoryError(
                        "supplied case_id disagrees with the governed identity join"
                    )
                return {
                    "record": candidates[0],
                    "identity_source": "official_bridge_code_and_date",
                }
        if case_id:
            raise PriorIPOHistoryError(
                f"case_id is not present in the governed universe: {case_id}"
            )
        return {"record": None, "identity_source": "caller_supplied_identity"}

    # -- projection --------------------------------------------------------

    def _build(
        self,
        profile: IPOProfile,
        history: PriorIPOHistory,
        resolved: dict[str, Any],
    ) -> MarketContextView:
        assert profile.listing_date is not None
        listing_date = profile.listing_date
        record = resolved["record"]
        industry = (profile.industry or "").strip() or (
            record.industry if record is not None else None
        )
        exclude_case_ids = frozenset({record.case_id} if record is not None else ())
        exclude_stock_codes = frozenset(
            {profile.stock_code} if profile.stock_code else ()
        )
        prior_rows = history.rows_before(
            listing_date,
            exclude_case_ids=exclude_case_ids,
            exclude_stock_codes=exclude_stock_codes,
        )
        values, reasons = build_ipo_market_context_with_reasons(
            listing_date=listing_date,
            industry=industry,
            prior_ipos=prior_rows,
            history_start_date=history.history_start_date,
            history_end_date=history.history_end_date,
            outcome_history_available=history.outcome_history_available,
        )
        reasons = self._refine_blind_cohort_reasons(
            reasons,
            history=history,
            listing_date=listing_date,
            prior_rows=prior_rows,
            industry=industry,
        )
        observations = self._observations(values, reasons)
        core_available = sum(
            item.availability == "available" for item in observations
        )
        provenance = self._provenance(
            profile=profile,
            history=history,
            resolved=resolved,
            industry=industry,
            values=values,
            reasons=reasons,
            prior_row_count=len(prior_rows),
            available_count=core_available,
        )
        extended, extended_provenance = self._extended(
            listing_date=listing_date,
            case_id=record.case_id if record is not None else None,
            stock_code=profile.stock_code or None,
        )
        observations += extended
        provenance.update(extended_provenance)
        available = sum(item.availability == "available" for item in observations)
        if available == 0:
            return MarketContextView(
                status=ChannelStatus.UNAVAILABLE,
                reason=(
                    "dynamic Market-X produced no governed observation for this "
                    "listing date: " + self._dominant_reason(reasons)
                ),
                observations=observations,
                feature_manifest_hash=IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
                provenance=provenance,
            )
        return MarketContextView(
            status=ChannelStatus.AVAILABLE,
            reason=(
                "recomputed point-in-time Market-X Core from the governed "
                f"prior-IPO universe ({core_available}/"
                f"{len(IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER)} Core features "
                "available)"
                + (
                    f", plus governed Extended context "
                    f"({available - core_available} available)"
                    if extended
                    else ""
                )
            ),
            observations=observations,
            feature_manifest_hash=IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
            provenance=provenance,
        )

    def _extended(
        self,
        *,
        listing_date: date,
        case_id: str | None,
        stock_code: str | None,
    ) -> tuple[tuple[MarketObservation, ...], dict[str, Any]]:
        """Attach governed Extended context, or say why it could not be read.

        An Extended cache that fails to load must not take the Core projection
        down with it: Core is complete on its own, and the failure is reported
        as a capability statement rather than swallowed.
        """

        if self.extended_source is None:
            return (), {"extended_status": "not_configured"}
        try:
            result = self.extended_source.context(
                listing_date=listing_date,
                case_id=case_id,
                stock_code=stock_code,
            )
        except DynamicExtendedMarketError as exc:
            return (), {
                "extended_status": "source_error",
                "extended_error": str(exc),
            }
        provenance = dict(result.provenance)
        provenance["extended_status"] = "available"
        return result.observations, provenance

    @staticmethod
    def _refine_blind_cohort_reasons(
        reasons: dict[str, str],
        *,
        history: PriorIPOHistory,
        listing_date: date,
        prior_rows: list[dict[str, Any]],
        industry: str | None,
    ) -> dict[str, str]:
        """Separate "withheld by blind policy" from "the sample was empty"."""

        if not history.outcome_history_available:
            return reasons
        refined = dict(reasons)
        window = [
            row
            for row in prior_rows
            if row["listing_date"] >= listing_date - timedelta(days=60)
        ][-20:]
        if window and not any(
            history.outcome_cohort_covers(row["listing_date"]) for row in window
        ):
            for name in _RECENT_OUTCOME_FEATURES:
                if refined.get(name) in _EMPTY_SAMPLE_REASONS:
                    refined[name] = MISSING_BLIND_COHORT_WITHHELD
        normalized = (industry or "").strip()
        same_industry = [
            row
            for row in prior_rows
            if row["listing_date"] >= listing_date - timedelta(days=180)
            and normalized
            and (row.get("industry") or "").strip() == normalized
        ]
        if same_industry and not any(
            history.outcome_cohort_covers(row["listing_date"]) for row in same_industry
        ):
            for name in _SAME_INDUSTRY_OUTCOME_FEATURES:
                if refined.get(name) in _EMPTY_SAMPLE_REASONS:
                    refined[name] = MISSING_BLIND_COHORT_WITHHELD
        return refined

    @staticmethod
    def _observations(
        values: dict[str, float | int | None],
        reasons: dict[str, str],
    ) -> tuple[MarketObservation, ...]:
        rows: list[MarketObservation] = []
        for name in IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER:
            value = values[name]
            if value is None:
                rows.append(
                    MarketObservation(
                        name=name,
                        availability="unavailable",
                        missing_reason=reasons[name],
                        source=DYNAMIC_MARKET_X_SOURCE,
                    )
                )
                continue
            rows.append(
                MarketObservation(
                    name=name,
                    value=float(value),
                    unit=IPO_MARKET_CONTEXT_FEATURE_UNITS[name],
                    availability="available",
                    derivation=DYNAMIC_MARKET_X_DERIVATION,
                    source=DYNAMIC_MARKET_X_SOURCE,
                )
            )
        return tuple(rows)

    @staticmethod
    def _dominant_reason(reasons: dict[str, str]) -> str:
        counts: dict[str, int] = {}
        for reason in reasons.values():
            counts[reason] = counts.get(reason, 0) + 1
        return max(sorted(counts), key=lambda reason: counts[reason])

    def _provenance(
        self,
        *,
        profile: IPOProfile,
        history: PriorIPOHistory,
        resolved: dict[str, Any],
        industry: str | None,
        values: dict[str, float | int | None],
        reasons: dict[str, str],
        prior_row_count: int,
        available_count: int,
    ) -> dict[str, Any]:
        assert profile.listing_date is not None
        record = resolved["record"]
        names, vector = vectorize_ipo_market_context(values)
        body = {
            "case_id": record.case_id if record is not None else None,
            "stock_code": profile.stock_code or (
                record.stock_code if record is not None else None
            ),
            "listing_date": profile.listing_date.isoformat(),
            "core_feature_schema_version": IPO_MARKET_CONTEXT_FEATURE_SCHEMA_VERSION,
            "core_feature_policy_version": IPO_MARKET_CONTEXT_FEATURE_POLICY_VERSION,
            "core_feature_manifest_hash": IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
            "feature_names": list(names),
            "feature_values": list(vector),
            "missing_reasons": dict(sorted(reasons.items())),
            "source_provenance": dict(sorted(history.provenance.items())),
        }
        return {
            "feature_pipeline": self.name,
            "runtime_path": "dynamic_pit",
            "reason_code": (
                "dynamic_market_x_available"
                if available_count
                else "dynamic_market_x_unavailable"
            ),
            "frozen_artifact_read_attempted": False,
            "case_id": body["case_id"],
            "stock_code": body["stock_code"],
            "listing_date": body["listing_date"],
            "industry": industry,
            "identity_source": resolved["identity_source"],
            "dataset_split": self._dataset_split(profile.listing_date),
            "pit_cutoff_date": profile.listing_date.isoformat(),
            "cutoff_semantics": CUTOFF_SEMANTICS,
            "prior_ipo_universe_size": prior_row_count,
            "prior_ipo_history_start_date": history.history_start_date.isoformat(),
            "prior_ipo_history_end_date": history.history_end_date.isoformat(),
            "outcome_history_available": history.outcome_history_available,
            "outcome_cohort_years": list(history.outcome_cohort_years),
            "blind_outcomes_included": False,
            "target_post_listing_data_used": False,
            "available_observation_count": available_count,
            "missing_observation_count": (
                len(IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER) - available_count
            ),
            "missing_reasons": body["missing_reasons"],
            "source_provenance": body["source_provenance"],
            "artifact_content_hash": content_hash(body),
        }

    @staticmethod
    def _dataset_split(listing_date: date) -> str:
        try:
            return expected_market_split(listing_date.year).value
        except ValueError:
            return "outside_frozen_split"
