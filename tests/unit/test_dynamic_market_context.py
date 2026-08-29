"""Dynamic Market-X must generalize to new IPOs or degrade for a stated reason."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from ipo_risk.agents.dynamic_market_context import (
    MISSING_BLIND_COHORT_WITHHELD,
    DynamicPITMarketContextProvider,
)
from ipo_risk.agents.market_context import GovernedPRBMarketContextProvider
from ipo_risk.market.ipo_market_context_features import (
    IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
    IPO_MARKET_CONTEXT_MISSING_INDUSTRY,
    IPO_MARKET_CONTEXT_MISSING_LEFT_BOUNDARY,
    IPO_MARKET_CONTEXT_MISSING_OUTCOME_SOURCE,
    IPO_MARKET_CONTEXT_MISSING_RIGHT_BOUNDARY,
    IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER,
)
from ipo_risk.schemas import IPOProfile
from ipo_risk.schemas.final_supervision import ChannelStatus
from ..dynamic_market_fixture import (
    bridge_row,
    outcome_record,
    prior_ipo_rows,
    write_bridge,
    write_outcome_pack,
)
from ..v04_market_context_fixture import write_governed_pr_b_fixture

FIRST_LISTING = date(2020, 1, 6)
# 120 weekly listings run from 2020-01-06 into 2022, so a 2022 target sits well
# inside both universe boundaries.
TARGET = date(2022, 3, 1)


def _rows() -> list[dict[str, str]]:
    return prior_ipo_rows(first_listing=FIRST_LISTING, count=120)


def _provider(tmp_path, rows=None, *, outcome_pack=None):
    bridge = write_bridge(tmp_path, rows if rows is not None else _rows())
    return DynamicPITMarketContextProvider(
        official_bridge_path=bridge,
        outcome_pack_path=outcome_pack,
    ), bridge


def _by_name(view):
    return {item.name: item for item in view.observations}


def test_new_case_inside_coverage_gets_a_real_market_x_projection(tmp_path) -> None:
    provider, _ = _provider(tmp_path)
    view = provider.context(IPOProfile(
        company_name="Fresh Issuer",
        stock_code="9999.HK",
        listing_date=TARGET,
        industry="软件服务",
    ))
    assert view.status is ChannelStatus.AVAILABLE
    assert len(view.observations) == len(IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER)
    # The dynamic build reports the frozen schema, so the model lane can build a
    # frozen model input from a case that has no frozen artifact.
    assert view.feature_manifest_hash == IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH
    assert view.provenance["runtime_path"] == "dynamic_pit"
    assert view.provenance["identity_source"] == "caller_supplied_identity"
    assert view.provenance["pit_cutoff_date"] == TARGET.isoformat()
    assert view.provenance["target_post_listing_data_used"] is False
    by_name = _by_name(view)
    assert by_name["ipo_count_30d"].availability == "available"
    assert by_name["ipo_count_30d"].value == pytest.approx(5)
    assert by_name["same_industry_ipo_count_180d"].value == pytest.approx(26)


def test_missing_listing_date_never_borrows_the_clock_as_a_cutoff(tmp_path) -> None:
    provider, _ = _provider(tmp_path)
    view = provider.context(IPOProfile(company_name="Undated", stock_code="9999.HK"))
    assert view.status is ChannelStatus.UNAVAILABLE
    assert view.observations == ()
    assert view.provenance["reason_code"] == "new_case_identity_incomplete"
    assert view.provenance["missing_identity_fields"] == ["listing_date"]
    assert view.provenance["listing_date"] is None


def test_a_listing_on_the_target_date_is_outside_the_point_in_time_window(tmp_path) -> None:
    rows = _rows()
    rows.append(bridge_row(
        case_id="ipo_2022_09000", stock_code="9000.HK", listing_date=TARGET,
    ))
    provider, _ = _provider(tmp_path, rows)
    baseline, _ = _provider(tmp_path / "baseline", _rows())
    profile = IPOProfile(
        company_name="Fresh Issuer", stock_code="9999.HK",
        listing_date=TARGET, industry="软件服务",
    )
    assert (
        _by_name(provider.context(profile))["ipo_count_30d"].value
        == _by_name(baseline.context(profile))["ipo_count_30d"].value
    )


def test_listing_beyond_the_coverage_end_is_unavailable_not_short_counted(tmp_path) -> None:
    provider, _ = _provider(tmp_path)
    view = provider.context(IPOProfile(
        company_name="Future Issuer", stock_code="9999.HK",
        listing_date=date(2024, 6, 1), industry="软件服务",
    ))
    assert view.status is ChannelStatus.UNAVAILABLE
    by_name = _by_name(view)
    assert by_name["ipo_count_30d"].value is None
    assert (
        by_name["ipo_count_30d"].missing_reason
        == IPO_MARKET_CONTEXT_MISSING_RIGHT_BOUNDARY
    )


def test_a_lookback_before_the_first_governed_listing_is_missing(tmp_path) -> None:
    provider, _ = _provider(tmp_path)
    view = provider.context(IPOProfile(
        company_name="Early Issuer", stock_code="9999.HK",
        listing_date=FIRST_LISTING + timedelta(days=20), industry="软件服务",
    ))
    by_name = _by_name(view)
    assert (
        by_name["ipo_count_30d"].missing_reason
        == IPO_MARKET_CONTEXT_MISSING_LEFT_BOUNDARY
    )
    assert by_name["ipo_count_30d"].value is None


def test_identity_that_disagrees_with_the_governed_row_fails_closed(tmp_path) -> None:
    rows = _rows()
    provider, _ = _provider(tmp_path, rows)
    view = provider.context(IPOProfile(
        company_name="Mismatched",
        stock_code="9996.HK",
        listing_date=date.fromisoformat(rows[0]["official_listed_date"]),
        metadata={"case_id": rows[0]["case_id"]},
    ))
    assert view.status is ChannelStatus.UNAVAILABLE_ERROR
    assert view.observations == ()
    assert view.provenance["reason_code"] == "governed_history_invalid"


def test_unknown_case_id_is_an_error_rather_than_a_silent_new_case(tmp_path) -> None:
    provider, _ = _provider(tmp_path)
    view = provider.context(IPOProfile(
        company_name="Ghost", stock_code="9999.HK", listing_date=TARGET,
        metadata={"case_id": "ipo_2022_99999"},
    ))
    assert view.status is ChannelStatus.UNAVAILABLE_ERROR
    assert "not present in the governed universe" in view.reason


def test_missing_industry_marks_only_the_industry_family_missing(tmp_path) -> None:
    provider, _ = _provider(tmp_path)
    view = provider.context(IPOProfile(
        company_name="Unclassified", stock_code="9999.HK", listing_date=TARGET,
    ))
    assert view.status is ChannelStatus.AVAILABLE
    by_name = _by_name(view)
    assert by_name["ipo_count_30d"].availability == "available"
    for name in (
        "same_industry_ipo_count_180d",
        "same_industry_recent_break_rate",
    ):
        assert by_name[name].value is None
        assert by_name[name].missing_reason == IPO_MARKET_CONTEXT_MISSING_INDUSTRY


def test_no_missing_feature_is_ever_reported_as_zero(tmp_path) -> None:
    provider, _ = _provider(tmp_path)
    for listing_date in (TARGET, date(2024, 6, 1), FIRST_LISTING + timedelta(days=20)):
        view = provider.context(IPOProfile(
            company_name="Probe", stock_code="9999.HK", listing_date=listing_date,
        ))
        for item in view.observations:
            if item.availability != "available":
                assert item.value is None, item.name
                assert item.missing_reason, item.name


def test_the_target_is_excluded_from_its_own_prior_universe(tmp_path) -> None:
    rows = _rows()
    target_row = bridge_row(
        case_id="ipo_2022_09000", stock_code="9000.HK",
        listing_date=TARGET - timedelta(days=3),
    )
    rows.append(target_row)
    provider, _ = _provider(tmp_path, rows)
    baseline, _ = _provider(tmp_path / "baseline", _rows())
    view = provider.context(IPOProfile(
        company_name=target_row["case_id"], stock_code="9000.HK",
        listing_date=TARGET - timedelta(days=3), industry="软件服务",
        metadata={"case_id": target_row["case_id"]},
    ))
    reference = baseline.context(IPOProfile(
        company_name="Fresh", stock_code="9999.HK",
        listing_date=TARGET - timedelta(days=3), industry="软件服务",
    ))
    assert view.provenance["identity_source"] == "official_bridge_case_id"
    assert (
        _by_name(view)["ipo_count_30d"].value
        == _by_name(reference)["ipo_count_30d"].value
    )


def test_outcome_families_are_missing_when_no_outcome_pack_is_configured(tmp_path) -> None:
    provider, _ = _provider(tmp_path)
    by_name = _by_name(provider.context(IPOProfile(
        company_name="Fresh", stock_code="9999.HK",
        listing_date=TARGET, industry="软件服务",
    )))
    for name in ("recent_ipo_break_rate", "recent_ipo_1d_sample_count"):
        assert by_name[name].value is None
        assert (
            by_name[name].missing_reason
            == IPO_MARKET_CONTEXT_MISSING_OUTCOME_SOURCE
        )


def test_a_validated_outcome_pack_makes_the_outcome_families_available(tmp_path) -> None:
    rows = _rows()
    bridge = write_bridge(tmp_path, rows)
    pack = write_outcome_pack(
        tmp_path,
        bridge,
        [
            outcome_record(row, return_1d=-0.1 if index % 2 else 0.2, return_5d=0.05)
            for index, row in enumerate(rows)
        ],
    )
    provider = DynamicPITMarketContextProvider(
        official_bridge_path=bridge, outcome_pack_path=pack
    )
    view = provider.context(IPOProfile(
        company_name="Fresh", stock_code="9999.HK",
        listing_date=TARGET, industry="软件服务",
    ))
    by_name = _by_name(view)
    assert by_name["recent_ipo_break_rate"].availability == "available"
    assert by_name["recent_ipo_break_rate"].value == pytest.approx(0.5)
    assert by_name["recent_ipo_return_5d"].value == pytest.approx(0.05)
    assert view.provenance["outcome_history_available"] is True
    assert view.provenance["blind_outcomes_included"] is False


def test_blind_cohort_window_says_withheld_rather_than_empty_sample(tmp_path) -> None:
    # Priors run into 2025; the target lists in 2025 so its recent window holds
    # only blind-cohort issuers, whose outcomes the pack must never carry.
    rows = prior_ipo_rows(first_listing=date(2023, 1, 2), count=140)
    bridge = write_bridge(tmp_path, rows)
    pack = write_outcome_pack(
        tmp_path,
        bridge,
        [
            outcome_record(row, return_1d=0.1, return_5d=0.1)
            for row in rows
            if row["official_listed_date"][:4] != "2025"
        ],
    )
    provider = DynamicPITMarketContextProvider(
        official_bridge_path=bridge, outcome_pack_path=pack
    )
    view = provider.context(IPOProfile(
        company_name="Blind Era", stock_code="9999.HK",
        listing_date=date(2025, 6, 2), industry="软件服务",
    ))
    by_name = _by_name(view)
    assert by_name["recent_ipo_break_rate"].value is None
    assert by_name["recent_ipo_break_rate"].missing_reason == MISSING_BLIND_COHORT_WITHHELD


def test_frozen_provider_hands_a_non_frozen_case_to_the_dynamic_path(tmp_path) -> None:
    feature_dir, frozen_bridge = write_governed_pr_b_fixture(tmp_path / "frozen")
    dynamic, _ = _provider(tmp_path / "dynamic")
    provider = GovernedPRBMarketContextProvider(
        feature_dir=feature_dir,
        official_bridge_path=frozen_bridge,
        new_case_provider=dynamic,
    )
    frozen_view = provider.context(IPOProfile(
        company_name="同源康医药-B", stock_code="2410.HK", listing_date=date(2024, 8, 20)
    ))
    assert frozen_view.provenance["runtime_path"] == "frozen"

    dynamic_view = provider.context(IPOProfile(
        company_name="Fresh", stock_code="9999.HK",
        listing_date=TARGET, industry="软件服务",
    ))
    assert dynamic_view.status is ChannelStatus.AVAILABLE
    assert dynamic_view.provenance["runtime_path"] == "dynamic_pit"
    assert dynamic_view.provenance["frozen_artifact_read_attempted"] is False
