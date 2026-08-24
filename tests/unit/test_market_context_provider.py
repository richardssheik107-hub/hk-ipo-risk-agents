"""Guards for the market channel: availability by source, never by non-null fields."""
from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

import pytest

from ipo_risk.agents.market_context import (
    GatePendingMarketContextProvider,
    GovernedPRBMarketContextProvider,
    SnapshotMarketContextProvider,
)
from ipo_risk.providers.mock import MockMarketDataProvider
from ipo_risk.schemas import IPOProfile, MarketSnapshot
from ipo_risk.schemas.final_supervision import ChannelStatus
from ..v04_market_context_fixture import (
    write_governed_extended_fixture,
    write_governed_pr_b_fixture,
)

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


def test_governed_pr_b_projection_is_available_and_hash_bound(tmp_path) -> None:
    feature_dir, bridge_path = write_governed_pr_b_fixture(tmp_path)
    provider = GovernedPRBMarketContextProvider(
        feature_dir=feature_dir,
        official_bridge_path=bridge_path,
    )
    view = provider.context(IPOProfile(
        company_name="同源康医药-B",
        stock_code="2410.HK",
        listing_date=date(2024, 8, 20),
    ))
    assert view.status is ChannelStatus.AVAILABLE
    assert len(view.observations) == 15
    assert view.feature_manifest_hash == "c2f4a1699e2bf9149f24cb35ea32dbc4851c017001ec509a0eaccd93720d729d"
    assert view.provenance["case_id"] == "ipo_2024_02410"
    assert view.provenance["cutoff_semantics"] == "strictly_before_target_listing_date"
    assert all(item.source == "pr_b_market_x_core" for item in view.observations)


def test_governed_pr_b_projection_fails_closed_for_unmatched_profile(tmp_path) -> None:
    feature_dir, bridge_path = write_governed_pr_b_fixture(tmp_path)
    provider = GovernedPRBMarketContextProvider(
        feature_dir=feature_dir,
        official_bridge_path=bridge_path,
    )
    view = provider.context(_profile())
    assert view.status is ChannelStatus.UNAVAILABLE_ERROR
    assert view.observations == ()
    assert "exactly one official IPO case" in view.reason


def test_governed_pr_b_projection_preserves_missing_values_without_zero_fill(tmp_path) -> None:
    feature_dir, bridge_path = write_governed_pr_b_fixture(tmp_path)
    provider = GovernedPRBMarketContextProvider(
        feature_dir=feature_dir,
        official_bridge_path=bridge_path,
    )
    view = provider.context(IPOProfile(
        company_name="德合集团", stock_code="0368.HK", listing_date=date(2020, 7, 17)))
    by_name = {item.name: item for item in view.observations}
    missing = by_name["same_industry_recent_return_5d"]
    assert missing.availability == "unavailable"
    assert missing.value is None
    assert missing.missing_reason == "insufficient_governed_prelisting_history"


def test_governed_pr_b_projection_rejects_tampered_artifact(tmp_path) -> None:
    source_dir, bridge_path = write_governed_pr_b_fixture(tmp_path / "source")
    source = source_dir / "ipo_2024_02410.json"
    feature_dir = tmp_path / "tampered"
    feature_dir.mkdir()
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["raw_values"]["recent_ipo_break_rate"] = 0.99
    (feature_dir / source.name).write_text(json.dumps(payload), encoding="utf-8")
    provider = GovernedPRBMarketContextProvider(
        feature_dir=feature_dir,
        official_bridge_path=bridge_path,
    )
    view = provider.context(IPOProfile(
        company_name="同源康医药-B", stock_code="2410.HK", listing_date=date(2024, 8, 20)))
    assert view.status is ChannelStatus.UNAVAILABLE_ERROR
    assert "content_hash" in view.reason


def test_governed_extended_projection_preserves_pit_blocked_industry_missingness(tmp_path) -> None:
    feature_dir, bridge_path = write_governed_pr_b_fixture(tmp_path)
    extended_path = write_governed_extended_fixture(tmp_path)
    provider = GovernedPRBMarketContextProvider(
        feature_dir=feature_dir,
        official_bridge_path=bridge_path,
        extended_readiness_path=extended_path,
    )
    view = provider.context(IPOProfile(
        company_name="同源康医药-B", stock_code="2410.HK", listing_date=date(2024, 8, 20)))
    assert view.status is ChannelStatus.AVAILABLE
    assert len(view.observations) == 21
    assert len({item.name for item in view.observations}) == 21
    by_name = {item.name: item for item in view.observations}
    for name in ("industry_return_5d", "industry_return_20d"):
        assert by_name[name].availability == "unavailable"
        assert by_name[name].value is None
        assert by_name[name].missing_reason == "INDUSTRY_MAPPING_PIT_BLOCKED"
    assert by_name["market_turnover_20d_mean"].value == pytest.approx(1_000_000)
    assert view.provenance["extended_readiness_sha256"]


def test_governed_extended_projection_rejects_zero_filled_missing_industry(tmp_path) -> None:
    feature_dir, bridge_path = write_governed_pr_b_fixture(tmp_path)
    extended_path = write_governed_extended_fixture(tmp_path)
    rows = list(csv.DictReader(extended_path.open(encoding="utf-8", newline="")))
    rows[1]["industry_return_5d"] = "0"
    with extended_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    provider = GovernedPRBMarketContextProvider(
        feature_dir=feature_dir,
        official_bridge_path=bridge_path,
        extended_readiness_path=extended_path,
    )
    view = provider.context(IPOProfile(
        company_name="同源康医药-B", stock_code="2410.HK", listing_date=date(2024, 8, 20)))
    assert view.status is ChannelStatus.UNAVAILABLE_ERROR
    assert view.observations == ()
    assert "must remain null" in view.reason
