"""Point-in-time IPO market-context features for the PR-B Market-X Core.

This module deliberately uses only information that can be known before the
*target* IPO listing date: prior IPO identities/offer facts and prior IPO
outcomes whose target trading session has already occurred. It does not use or
proxy HSI, industry-index history, or total-market turnover; those belong to the
separate Extended Market-X contract.
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


def build_ipo_market_context(
    *,
    listing_date: date,
    industry: str | None,
    prior_ipos: list[dict[str, Any]],
) -> dict[str, float | int | None]:
    """Build deterministic context using only facts known before listing date."""

    normalized_industry = industry.strip() if industry and industry.strip() else None
    prior = sorted(
        (
            item
            for item in prior_ipos
            if item.get("listing_date") and item["listing_date"] < listing_date
        ),
        key=lambda item: item["listing_date"],
    )

    def window(days: int) -> list[dict[str, Any]]:
        start = listing_date - timedelta(days=days)
        return [item for item in prior if item["listing_date"] >= start]

    def aggregate(
        rows: list[dict[str, Any]], prefix: str
    ) -> dict[str, float | int | None]:
        amounts = [
            float(item["funds_raised"])
            for item in rows
            if item.get("funds_raised") is not None
        ]
        return {
            f"log_prior_ipo_funds_raised_{prefix}": (
                math.log1p(sum(amounts)) if amounts else None
            ),
            f"prior_ipo_funds_raised_{prefix}_sample_count": len(amounts),
        }

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

    rows_30d = window(30)
    rows_60d = window(60)
    recent = rows_60d[-20:]
    break_rate, return_5d, sample_1d, sample_5d = outcomes(recent)

    if normalized_industry is None:
        same_industry_values: dict[str, float | int | None] = {
            "same_industry_ipo_count_180d": None,
            "same_industry_recent_break_rate": None,
            "same_industry_recent_return_5d": None,
            "same_industry_recent_1d_sample_count": None,
            "same_industry_recent_5d_sample_count": None,
        }
    else:
        same_industry = [
            item
            for item in window(180)
            if (item.get("industry") or "").strip() == normalized_industry
        ]
        (
            same_break_rate,
            same_return_5d,
            same_sample_1d,
            same_sample_5d,
        ) = outcomes(same_industry)
        same_industry_values = {
            "same_industry_ipo_count_180d": len(same_industry),
            "same_industry_recent_break_rate": same_break_rate,
            "same_industry_recent_return_5d": same_return_5d,
            "same_industry_recent_1d_sample_count": same_sample_1d,
            "same_industry_recent_5d_sample_count": same_sample_5d,
        }

    values: dict[str, float | int | None] = {
        "ipo_count_30d": len(rows_30d),
        "ipo_count_60d": len(rows_60d),
        **aggregate(rows_30d, "30d"),
        **aggregate(rows_60d, "60d"),
        "recent_ipo_break_rate": break_rate,
        "recent_ipo_return_5d": return_5d,
        "recent_ipo_1d_sample_count": sample_1d,
        "recent_ipo_5d_sample_count": sample_5d,
        **same_industry_values,
    }
    if tuple(values) != IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER:
        raise RuntimeError("IPO market-context feature order drifted")
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
