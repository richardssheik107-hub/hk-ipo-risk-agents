"""Guards for the market channel: availability by source, never by non-null fields."""
from __future__ import annotations

import json
from datetime import date

import pytest

from ipo_risk.agents.market_context import (
    GatePendingMarketContextProvider,
    SnapshotMarketContextProvider,
)
from ipo_risk.providers.mock import MockMarketDataProvider
from ipo_risk.schemas import IPOProfile, MarketSnapshot
from ipo_risk.schemas.final_supervision import ChannelStatus

PROVIDER = SnapshotMarketContextProvider()


def _profile() -> IPOProfile:
    return IPOProfile(company_name="Demo", stock_code="9999.HK", listing_date=date(2024, 6, 1))


def test_absent_snapshot_is_an_error_not_an_empty_success() -> None:
    view = PROVIDER.context(_profile(), None)
    assert view.status is ChannelStatus.UNAVAILABLE_ERROR
    assert view.observations == ()


def test_governed_provider_reason_is_passed_through_verbatim() -> None:
    """CompetitionCSVMarketDataProvider's own words, not a paraphrase."""
    reason = "legacy snapshot is not produced by the governed EOD adapter"
    view = PROVIDER.context(_profile(), MarketSnapshot(
        source="unavailable", metadata={"available": False, "reason": reason}))
    assert view.status is ChannelStatus.UNAVAILABLE_ERROR
    assert view.reason == reason
    assert view.observations == ()


def test_available_false_metadata_overrides_a_populated_snapshot() -> None:
    view = PROVIDER.context(_profile(), MarketSnapshot(
        source="somewhere", hsi_return_5d=0.01, metadata={"available": False, "reason": "stale"}))
    assert view.status is ChannelStatus.UNAVAILABLE_ERROR
    assert view.observations == ()


def test_mock_snapshot_is_disabled_and_leaks_no_fixture_number() -> None:
    """MockMarketDataProvider returns invented values; rendering them would fabricate data."""
    snapshot = MockMarketDataProvider().get_snapshot(_profile())
    assert snapshot.source == "mock"
    assert snapshot.sentiment_score is not None  # the fixture really is populated
    view = PROVIDER.context(_profile(), snapshot)
    assert view.status is ChannelStatus.DISABLED
    assert view.observations == ()
    serialized = json.dumps(view.model_dump(mode="json"))
    for fabricated in ("-0.04", "0.42", "0.31", "35"):
        assert fabricated not in serialized, fabricated


def test_governed_snapshot_explains_every_field_present_or_absent() -> None:
    snapshot = MarketSnapshot(
        source="governed_eod", observation_date=date(2024, 5, 30),
        hsi_return_5d=-0.012, market_volatility=0.21)
    view = PROVIDER.context(_profile(), snapshot)
    assert view.status is ChannelStatus.AVAILABLE
    by_name = {item.name: item for item in view.observations}
    assert by_name["hsi_return_5d"].availability == "available"
    assert by_name["hsi_return_5d"].value == pytest.approx(-0.012)
    assert by_name["hsi_return_5d"].derivation
    # An absent field names why it is absent instead of vanishing.
    assert by_name["industry_return_5d"].availability == "unavailable"
    assert by_name["industry_return_5d"].missing_reason == "missing_industry_series"
    assert by_name["industry_return_5d"].value is None
    assert view.provenance["observation_date"] == "2024-05-30"


def test_snapshot_view_never_claims_pr_b_lineage() -> None:
    """A legacy snapshot did not come from the PR-B Market-X pipeline."""
    view = PROVIDER.context(_profile(), MarketSnapshot(source="governed_eod", hsi_return_5d=0.0))
    assert view.feature_manifest_hash is None
    assert view.provenance["feature_pipeline"] == "legacy_market_snapshot_not_v04_market_x"


def test_gate_pending_provider_no_longer_claims_a_blocking_gate() -> None:
    """PR-B is COMPLETE / FROZEN; nothing gates this channel any more."""
    view = GatePendingMarketContextProvider().context(_profile(), None)
    assert view.status is ChannelStatus.DISABLED
    assert view.blocking_gate is None
    assert view.observations == ()
