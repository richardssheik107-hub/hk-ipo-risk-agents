from datetime import date

import pytest

from ipo_risk.market.ipo_market_context_features import (
    IPO_MARKET_CONTEXT_FEATURE_MANIFEST,
    IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
    IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER,
    build_ipo_market_context,
    content_hash,
    vectorize_ipo_market_context,
)


def test_context_excludes_future_ipo_and_not_yet_known_outcome() -> None:
    target = date(2022, 3, 1)
    rows = [
        {
            "listing_date": date(2022, 2, 15),
            "industry": "A",
            "funds_raised": 10,
            "target_1d": date(2022, 2, 16),
            "return_1d": -0.1,
            # A result whose target session is the target IPO listing date is
            # not known strictly before that listing date and must be excluded.
            "target_5d": target,
            "return_5d": -0.2,
        },
        {
            "listing_date": target,
            "industry": "A",
            "funds_raised": 100,
            "target_1d": date(2022, 3, 2),
            "return_1d": -0.9,
            "target_5d": date(2022, 3, 8),
            "return_5d": -0.9,
        },
    ]
    got = build_ipo_market_context(
        listing_date=target,
        industry="A",
        prior_ipos=rows,
    )
    assert got["ipo_count_30d"] == 1
    assert got["recent_ipo_break_rate"] == 1
    assert got["recent_ipo_return_5d"] is None
    assert got["same_industry_recent_5d_sample_count"] == 0


def test_context_zero_sample_keeps_null_rate() -> None:
    got = build_ipo_market_context(
        listing_date=date(2022, 1, 1),
        industry="A",
        prior_ipos=[],
    )
    assert got["same_industry_ipo_count_180d"] == 0
    assert got["same_industry_recent_break_rate"] is None


def test_context_vector_uses_adjacent_missing_indicators() -> None:
    values = build_ipo_market_context(
        listing_date=date(2022, 1, 1),
        industry=None,
        prior_ipos=[],
    )
    names, vector = vectorize_ipo_market_context(values)

    assert len(names) == len(IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER) * 2
    assert len(vector) == len(names)
    assert names[:4] == (
        "ipo_count_30d",
        "ipo_count_30d__missing",
        "ipo_count_60d",
        "ipo_count_60d__missing",
    )
    assert vector[0:4] == (0, 0, 0, 0)

    missing_index = names.index("recent_ipo_break_rate")
    assert vector[missing_index] is None
    assert vector[missing_index + 1] == 1


def test_context_manifest_hash_is_deterministic() -> None:
    assert IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH == content_hash(
        IPO_MARKET_CONTEXT_FEATURE_MANIFEST
    )
    feature_names = tuple(
        item["name"] for item in IPO_MARKET_CONTEXT_FEATURE_MANIFEST["features"]
    )
    expected_names = tuple(
        name
        for raw_name in IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER
        for name in (raw_name, f"{raw_name}__missing")
    )
    assert feature_names == expected_names


def test_context_vector_rejects_manifest_key_drift() -> None:
    values = build_ipo_market_context(
        listing_date=date(2022, 1, 1),
        industry="A",
        prior_ipos=[],
    )
    values.pop("ipo_count_30d")
    values["unexpected"] = 1

    with pytest.raises(ValueError, match="frozen manifest"):
        vectorize_ipo_market_context(values)
