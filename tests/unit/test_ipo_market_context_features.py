from datetime import date

import pytest

from ipo_risk.market.ipo_market_context_features import (
    IPO_MARKET_CONTEXT_FEATURE_MANIFEST,
    IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
    IPO_MARKET_CONTEXT_MISSING_OUTCOME_SAMPLE,
    IPO_MARKET_CONTEXT_MISSING_OUTCOME_SOURCE,
    IPO_MARKET_CONTEXT_MISSING_RIGHT_BOUNDARY,
    IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER,
    build_ipo_market_context,
    build_ipo_market_context_with_reasons,
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


def test_missing_target_industry_marks_whole_industry_family_missing() -> None:
    got = build_ipo_market_context(
        listing_date=date(2022, 3, 1),
        industry=None,
        prior_ipos=[
            {
                "listing_date": date(2022, 2, 1),
                "industry": "A",
                "funds_raised": 10,
                "target_1d": date(2022, 2, 2),
                "return_1d": -0.1,
                "target_5d": date(2022, 2, 8),
                "return_5d": -0.2,
            }
        ],
    )
    assert got["same_industry_ipo_count_180d"] is None
    assert got["same_industry_recent_break_rate"] is None
    assert got["same_industry_recent_return_5d"] is None
    assert got["same_industry_recent_1d_sample_count"] is None
    assert got["same_industry_recent_5d_sample_count"] is None


def test_left_boundary_marks_incomplete_lookbacks_missing() -> None:
    target = date(2020, 3, 1)
    got = build_ipo_market_context(
        listing_date=target,
        industry="A",
        history_start_date=date(2020, 1, 15),
        prior_ipos=[
            {
                "listing_date": date(2020, 2, 15),
                "industry": "A",
                "funds_raised": 10,
                "target_1d": date(2020, 2, 16),
                "return_1d": -0.1,
                "target_5d": date(2020, 2, 21),
                "return_5d": -0.2,
            }
        ],
    )

    # 30D reaches 2020-01-31 and is fully inside the declared source history.
    assert got["ipo_count_30d"] == 1
    assert got["prior_ipo_funds_raised_30d_sample_count"] == 1
    # 60D/180D extend before the source universe and must not become partial zeros.
    assert got["ipo_count_60d"] is None
    assert got["recent_ipo_1d_sample_count"] is None
    assert got["recent_ipo_break_rate"] is None
    assert got["same_industry_ipo_count_180d"] is None


def test_context_rejects_row_before_declared_history_start() -> None:
    with pytest.raises(ValueError, match="predates declared history_start_date"):
        build_ipo_market_context(
            listing_date=date(2020, 3, 1),
            industry="A",
            history_start_date=date(2020, 1, 15),
            prior_ipos=[
                {
                    "listing_date": date(2020, 1, 1),
                    "industry": "A",
                }
            ],
        )


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

    recent_missing_index = names.index("recent_ipo_break_rate")
    assert vector[recent_missing_index] is None
    assert vector[recent_missing_index + 1] == 1

    industry_missing_index = names.index("same_industry_ipo_count_180d")
    assert vector[industry_missing_index] is None
    assert vector[industry_missing_index + 1] == 1


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


def test_right_boundary_marks_a_stale_universe_missing_not_short_counted() -> None:
    """A universe that stops before the target cannot report a low count."""

    rows = [
        {"listing_date": date(2022, 1, 5), "industry": "A", "funds_raised": 10},
        {"listing_date": date(2022, 1, 20), "industry": "A", "funds_raised": 10},
    ]
    values, reasons = build_ipo_market_context_with_reasons(
        listing_date=date(2022, 6, 1),
        industry="A",
        prior_ipos=rows,
        history_start_date=date(2020, 1, 1),
        history_end_date=date(2022, 1, 31),
    )
    assert values["ipo_count_30d"] is None
    assert reasons["ipo_count_30d"] == IPO_MARKET_CONTEXT_MISSING_RIGHT_BOUNDARY
    assert reasons["same_industry_ipo_count_180d"] == IPO_MARKET_CONTEXT_MISSING_RIGHT_BOUNDARY


def test_a_universe_complete_to_the_prior_session_keeps_the_window() -> None:
    values, reasons = build_ipo_market_context_with_reasons(
        listing_date=date(2022, 6, 1),
        industry="A",
        prior_ipos=[{"listing_date": date(2022, 5, 20), "industry": "A", "funds_raised": 10}],
        history_start_date=date(2020, 1, 1),
        history_end_date=date(2022, 5, 31),
    )
    assert values["ipo_count_30d"] == 1
    assert "ipo_count_30d" not in reasons


def test_a_row_after_the_declared_coverage_end_fails_closed() -> None:
    with pytest.raises(ValueError, match="postdates declared history_end_date"):
        build_ipo_market_context_with_reasons(
            listing_date=date(2022, 6, 1),
            industry="A",
            prior_ipos=[{"listing_date": date(2022, 5, 20), "industry": "A"}],
            history_start_date=date(2020, 1, 1),
            history_end_date=date(2022, 1, 31),
        )


def test_an_absent_outcome_source_is_not_an_empty_sample() -> None:
    rows = [
        {
            "listing_date": date(2022, 2, 15),
            "industry": "A",
            "funds_raised": 10,
            "target_1d": date(2022, 2, 16),
            "return_1d": -0.1,
        }
    ]
    values, reasons = build_ipo_market_context_with_reasons(
        listing_date=date(2022, 3, 1),
        industry="A",
        prior_ipos=rows,
        outcome_history_available=False,
    )
    assert values["ipo_count_30d"] == 1
    for name in ("recent_ipo_break_rate", "recent_ipo_1d_sample_count"):
        assert values[name] is None
        assert reasons[name] == IPO_MARKET_CONTEXT_MISSING_OUTCOME_SOURCE
    assert reasons["recent_ipo_break_rate"] != IPO_MARKET_CONTEXT_MISSING_OUTCOME_SAMPLE


def test_every_missing_value_carries_a_reason() -> None:
    values, reasons = build_ipo_market_context_with_reasons(
        listing_date=date(2022, 3, 1),
        industry=None,
        prior_ipos=[],
        history_start_date=date(2022, 2, 20),
        history_end_date=date(2022, 2, 28),
    )
    for name in IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER:
        if values[name] is None:
            assert reasons[name], name
