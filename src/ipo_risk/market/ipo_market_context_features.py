"""Point-in-time IPO market-context features for the PR-B Market-X Core.

This module deliberately uses only information that can be known before the
*target* IPO listing date: prior IPO identities/offer facts and prior IPO
outcomes whose target trading session has already occurred. It does not use or
proxy HSI, industry-index history, or total-market turnover; those belong to the
separate Extended Market-X contract.

A bounded prior-IPO source universe must also expose both of its boundaries.
When a 30/60/180-day lookback extends earlier than the source's left boundary,
or when the source stops before the day preceding the target listing date, the
affected feature family is returned as missing rather than a misleading
zero/partial history value.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import date, timedelta
from typing import Any

IPO_MARKET_CONTEXT_FEATURE_SCHEMA_VERSION = "v04_ipo_market_context_features_v1"
IPO_MARKET_CONTEXT_FEATURE_POLICY_VERSION = "ipo_market_context_policy_v1"

IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER = (
    "ipo_count_30d",
    "ipo_count_60d",
    "log_prior_ipo_funds_raised_30d",
    "log_prior_ipo_funds_raised_60d",
    "prior_ipo_funds_raised_30d_sample_count",
    "prior_ipo_funds_raised_60d_sample_count",
    "recent_ipo_break_rate",
    "recent_ipo_return_5d",
    "recent_ipo_1d_sample_count",
    "recent_ipo_5d_sample_count",
    "same_industry_ipo_count_180d",
    "same_industry_recent_break_rate",
    "same_industry_recent_return_5d",
    "same_industry_recent_1d_sample_count",
    "same_industry_recent_5d_sample_count",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def content_hash(value: Any) -> str:
    """Return a deterministic SHA-256 for a JSON-compatible payload."""

    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _build_manifest() -> dict[str, Any]:
    features: list[dict[str, Any]] = []
    for index, name in enumerate(IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER):
        features.append(
            {
                "index": index * 2,
                "name": name,
                "dtype": "float64",
            }
        )
        features.append(
            {
                "index": index * 2 + 1,
                "name": f"{name}__missing",
                "dtype": "int8",
            }
        )
    return {
        "version": IPO_MARKET_CONTEXT_FEATURE_SCHEMA_VERSION,
        "policy_version": IPO_MARKET_CONTEXT_FEATURE_POLICY_VERSION,
        "features": features,
    }


IPO_MARKET_CONTEXT_FEATURE_MANIFEST = _build_manifest()
IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH = content_hash(
    IPO_MARKET_CONTEXT_FEATURE_MANIFEST
)


# Stable units for the frozen raw feature order.  Every projection of these
# features -- frozen artifact or dynamic build -- must report the same unit.
IPO_MARKET_CONTEXT_FEATURE_UNITS: dict[str, str] = {
    "ipo_count_30d": "count",
    "ipo_count_60d": "count",
    "log_prior_ipo_funds_raised_30d": "log_currency",
    "log_prior_ipo_funds_raised_60d": "log_currency",
    "prior_ipo_funds_raised_30d_sample_count": "count",
    "prior_ipo_funds_raised_60d_sample_count": "count",
    "recent_ipo_break_rate": "ratio",
    "recent_ipo_return_5d": "ratio",
    "recent_ipo_1d_sample_count": "count",
    "recent_ipo_5d_sample_count": "count",
    "same_industry_ipo_count_180d": "count",
    "same_industry_recent_break_rate": "ratio",
    "same_industry_recent_return_5d": "ratio",
    "same_industry_recent_1d_sample_count": "count",
    "same_industry_recent_5d_sample_count": "count",
}
if set(IPO_MARKET_CONTEXT_FEATURE_UNITS) != set(IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER):
    raise RuntimeError("market-context feature units drifted from the frozen manifest")


IPO_MARKET_CONTEXT_MISSING_LEFT_BOUNDARY = (
    "prior_ipo_universe_left_boundary_incomplete"
)
IPO_MARKET_CONTEXT_MISSING_RIGHT_BOUNDARY = (
    "prior_ipo_universe_right_boundary_incomplete"
)
IPO_MARKET_CONTEXT_MISSING_INDUSTRY = "missing_industry_classification"
IPO_MARKET_CONTEXT_MISSING_OUTCOME_SOURCE = (
    "prior_ipo_outcome_source_not_configured"
)
IPO_MARKET_CONTEXT_MISSING_FUNDS_SAMPLE = "no_prior_ipo_offer_amount_sample"
IPO_MARKET_CONTEXT_MISSING_OUTCOME_SAMPLE = "no_recent_ipo_outcome_sample"
IPO_MARKET_CONTEXT_MISSING_SAME_INDUSTRY_OUTCOME_SAMPLE = (
    "no_same_industry_recent_outcome_sample"
)

def build_ipo_market_context_with_reasons(
    *,
    listing_date: date,
    industry: str | None,
    prior_ipos: list[dict[str, Any]],
    history_start_date: date | None = None,
    history_end_date: date | None = None,
    outcome_history_available: bool = True,
) -> tuple[dict[str, float | int | None], dict[str, str]]:
    """Build PIT context values plus an explicit reason for every absent value.

    ``history_start_date`` and ``history_end_date`` declare the closed interval
    over which the supplied prior-IPO universe is complete. They are provenance,
    not features. A lookback window that reaches outside that interval makes the
    affected feature family explicitly missing instead of silently short-counted
    against a truncated universe.

    ``outcome_history_available`` states whether prior-IPO 1D/5D outcomes could
    be supplied at all. "The outcome source is not configured" and "the window
    contained no completed prior outcome" are different facts, and a caller that
    has to explain missingness needs to be able to tell them apart.
    """

    if history_start_date is not None and history_start_date > listing_date:
        raise ValueError("history_start_date cannot be after target listing_date")
    if (
        history_start_date is not None
        and history_end_date is not None
        and history_end_date < history_start_date
    ):
        raise ValueError("history_end_date cannot precede history_start_date")

    normalized_industry = industry.strip() if industry and industry.strip() else None
    prior = sorted(
        (
            item
            for item in prior_ipos
            if item.get("listing_date") and item["listing_date"] < listing_date
        ),
        key=lambda item: item["listing_date"],
    )
    if history_start_date is not None and any(
        item["listing_date"] < history_start_date for item in prior
    ):
        raise ValueError("prior IPO row predates declared history_start_date")
    if history_end_date is not None and any(
        item["listing_date"] > history_end_date for item in prior
    ):
        raise ValueError("prior IPO row postdates declared history_end_date")

    # The universe must cover every day of the lookback window, which ends on
    # the session before the target listing date.
    right_complete = (
        history_end_date is None
        or history_end_date >= listing_date - timedelta(days=1)
    )

    def boundary_reason(days: int) -> str | None:
        if history_start_date is not None and history_start_date > listing_date - timedelta(days=days):
            return IPO_MARKET_CONTEXT_MISSING_LEFT_BOUNDARY
        if not right_complete:
            return IPO_MARKET_CONTEXT_MISSING_RIGHT_BOUNDARY
        return None

    def window(days: int) -> list[dict[str, Any]]:
        start = listing_date - timedelta(days=days)
        return [item for item in prior if item["listing_date"] >= start]

    def outcomes(
        rows: list[dict[str, Any]],
    ) -> tuple[float | None, float | None, int, int]:
        one_day = [
            float(item["return_1d"])
            for item in rows
            if item.get("target_1d")
            and item["target_1d"] < listing_date
            and item.get("return_1d") is not None
        ]
        five_day = [
            float(item["return_5d"])
            for item in rows
            if item.get("target_5d")
            and item["target_5d"] < listing_date
            and item.get("return_5d") is not None
        ]
        return (
            sum(value < 0 for value in one_day) / len(one_day)
            if one_day
            else None,
            sum(five_day) / len(five_day) if five_day else None,
            len(one_day),
            len(five_day),
        )

    computed: dict[str, float | int | None] = {}
    reasons: dict[str, str] = {}

    def record(name: str, value: float | int | None, reason: str) -> None:
        computed[name] = value
        if value is None:
            reasons[name] = reason

    reason_30d = boundary_reason(30)
    reason_60d = boundary_reason(60)
    reason_180d = boundary_reason(180)

    for days, reason in ((30, reason_30d), (60, reason_60d)):
        prefix = f"{days}d"
        rows = window(days) if reason is None else []
        record(f"ipo_count_{prefix}", None if reason else len(rows), reason or "")
        amounts = [
            float(item["funds_raised"])
            for item in rows
            if item.get("funds_raised") is not None
        ]
        record(
            f"log_prior_ipo_funds_raised_{prefix}",
            None
            if reason
            else (math.log1p(sum(amounts)) if amounts else None),
            reason or IPO_MARKET_CONTEXT_MISSING_FUNDS_SAMPLE,
        )
        record(
            f"prior_ipo_funds_raised_{prefix}_sample_count",
            None if reason else len(amounts),
            reason or "",
        )

    outcome_reason = (
        reason_60d
        if reason_60d
        else None
        if outcome_history_available
        else IPO_MARKET_CONTEXT_MISSING_OUTCOME_SOURCE
    )
    if outcome_reason is None:
        break_rate, return_5d, sample_1d, sample_5d = outcomes(window(60)[-20:])
    else:
        break_rate = return_5d = None
        sample_1d = sample_5d = None
    record("recent_ipo_break_rate", break_rate, outcome_reason or IPO_MARKET_CONTEXT_MISSING_OUTCOME_SAMPLE)
    record("recent_ipo_return_5d", return_5d, outcome_reason or IPO_MARKET_CONTEXT_MISSING_OUTCOME_SAMPLE)
    record("recent_ipo_1d_sample_count", sample_1d, outcome_reason or "")
    record("recent_ipo_5d_sample_count", sample_5d, outcome_reason or "")

    industry_reason = (
        reason_180d
        if reason_180d
        else IPO_MARKET_CONTEXT_MISSING_INDUSTRY
        if normalized_industry is None
        else None
    )
    if industry_reason is None:
        same_industry = [
            item
            for item in window(180)
            if (item.get("industry") or "").strip() == normalized_industry
        ]
    else:
        same_industry = []
    record(
        "same_industry_ipo_count_180d",
        None if industry_reason else len(same_industry),
        industry_reason or "",
    )
    same_outcome_reason = (
        industry_reason
        if industry_reason
        else None
        if outcome_history_available
        else IPO_MARKET_CONTEXT_MISSING_OUTCOME_SOURCE
    )
    if same_outcome_reason is None:
        (
            same_break_rate,
            same_return_5d,
            same_sample_1d,
            same_sample_5d,
        ) = outcomes(same_industry)
    else:
        same_break_rate = same_return_5d = None
        same_sample_1d = same_sample_5d = None
    fallback = IPO_MARKET_CONTEXT_MISSING_SAME_INDUSTRY_OUTCOME_SAMPLE
    record("same_industry_recent_break_rate", same_break_rate, same_outcome_reason or fallback)
    record("same_industry_recent_return_5d", same_return_5d, same_outcome_reason or fallback)
    record("same_industry_recent_1d_sample_count", same_sample_1d, same_outcome_reason or "")
    record("same_industry_recent_5d_sample_count", same_sample_5d, same_outcome_reason or "")

    if set(computed) != set(IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER):
        raise RuntimeError("IPO market-context feature order drifted")
    if any(not reason for reason in reasons.values()):
        raise RuntimeError("a missing market-context feature has no stated reason")
    values = {
        name: computed[name] for name in IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER
    }
    return values, reasons


def build_ipo_market_context(
    *,
    listing_date: date,
    industry: str | None,
    prior_ipos: list[dict[str, Any]],
    history_start_date: date | None = None,
    history_end_date: date | None = None,
    outcome_history_available: bool = True,
) -> dict[str, float | int | None]:
    """Build deterministic context using only complete, pre-listing history.

    ``history_start_date`` is the earliest date for which the supplied prior-IPO
    universe is considered complete. It is provenance, not a feature. If a
    requested lookback begins before it, that feature family is explicitly
    missing.
    """

    values, _ = build_ipo_market_context_with_reasons(
        listing_date=listing_date,
        industry=industry,
        prior_ipos=prior_ipos,
        history_start_date=history_start_date,
        history_end_date=history_end_date,
        outcome_history_available=outcome_history_available,
    )
    return values


def vectorize_ipo_market_context(
    values: dict[str, float | int | None],
) -> tuple[tuple[str, ...], tuple[float | int | None, ...]]:
    """Vectorize raw context values with an adjacent explicit missing indicator."""

    unexpected = set(values) - set(IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER)
    missing = set(IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER) - set(values)
    if unexpected or missing:
        raise ValueError(
            "market-context feature keys do not match frozen manifest: "
            f"missing={sorted(missing)}, unexpected={sorted(unexpected)}"
        )

    names: list[str] = []
    vector: list[float | int | None] = []
    for raw_name in IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER:
        raw_value = values[raw_name]
        names.extend((raw_name, f"{raw_name}__missing"))
        vector.extend((raw_value, int(raw_value is None)))
    return tuple(names), tuple(vector)
