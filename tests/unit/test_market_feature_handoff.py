"""The model lane consumes one handoff shape from both Market-X runtime paths."""

from __future__ import annotations

from datetime import date

import pytest

from ipo_risk.agents.dynamic_market_context import DynamicPITMarketContextProvider
from ipo_risk.agents.market_context import (
    GovernedPRBMarketContextProvider,
    SnapshotMarketContextProvider,
)
from ipo_risk.market.handoff import (
    MARKET_FEATURE_HANDOFF_SCHEMA_VERSION,
    MarketFeatureHandoffError,
    build_market_feature_handoff,
)
from ipo_risk.market.ipo_market_context_features import (
    IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
    IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER,
)
from ipo_risk.schemas import IPOProfile, MarketSnapshot
from ..dynamic_market_fixture import prior_ipo_rows, write_bridge
from ..v04_market_context_fixture import write_governed_pr_b_fixture


def _dynamic_handoff(tmp_path) -> dict:
    bridge = write_bridge(tmp_path, prior_ipo_rows(first_listing=date(2020, 1, 6), count=120))
    view = DynamicPITMarketContextProvider(official_bridge_path=bridge).context(
        IPOProfile(
            company_name="Fresh", stock_code="9999.HK",
            listing_date=date(2022, 3, 1), industry="软件服务",
        )
    )
    return build_market_feature_handoff(view)


def test_frozen_and_dynamic_handoffs_share_one_feature_identity(tmp_path) -> None:
    feature_dir, bridge_path = write_governed_pr_b_fixture(tmp_path / "frozen")
    frozen = build_market_feature_handoff(
        GovernedPRBMarketContextProvider(
            feature_dir=feature_dir, official_bridge_path=bridge_path
        ).context(IPOProfile(
            company_name="同源康医药-B", stock_code="2410.HK",
            listing_date=date(2024, 8, 20),
        ))
    )
    dynamic = _dynamic_handoff(tmp_path / "dynamic")

    assert frozen["schema_version"] == MARKET_FEATURE_HANDOFF_SCHEMA_VERSION
    assert frozen["feature_names"] == dynamic["feature_names"]
    assert len(frozen["feature_names"]) == 2 * len(IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER)
    assert (
        frozen["core_feature_manifest_hash"]
        == dynamic["core_feature_manifest_hash"]
        == IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH
    )
    assert frozen["market_runtime_path"] == "frozen"
    assert dynamic["market_runtime_path"] == "dynamic_pit"


def test_the_handoff_mask_separates_unknown_from_zero(tmp_path) -> None:
    handoff = _dynamic_handoff(tmp_path)
    mask = handoff["missing_mask"]
    for name in handoff["missing_features"]:
        assert mask[name] == 1
        assert handoff["missing_reasons"][name]
        index = handoff["feature_names"].index(name)
        assert handoff["feature_values"][index] is None
        assert handoff["feature_values"][index + 1] == 1
    for name in handoff["available_features"]:
        assert mask[name] == 0
        assert handoff["feature_values"][handoff["feature_names"].index(name) + 1] == 0


def test_the_handoff_is_content_hashed_and_carries_the_pit_cutoff(tmp_path) -> None:
    handoff = _dynamic_handoff(tmp_path)
    assert handoff["pit_cutoff_date"] == "2022-03-01"
    assert handoff["cutoff_semantics"] == "market_data_strictly_before_listing_date"
    assert len(handoff["content_hash"]) == 64
    assert build_market_feature_handoff(
        DynamicPITMarketContextProvider(
            official_bridge_path=tmp_path / "ipo_official_master_bridge.csv"
        ).context(IPOProfile(
            company_name="Fresh", stock_code="9999.HK",
            listing_date=date(2022, 3, 1), industry="软件服务",
        ))
    )["content_hash"] == handoff["content_hash"]


def test_an_unavailable_channel_cannot_be_handed_to_the_model(tmp_path) -> None:
    bridge = write_bridge(tmp_path, prior_ipo_rows(first_listing=date(2020, 1, 6), count=20))
    view = DynamicPITMarketContextProvider(official_bridge_path=bridge).context(
        IPOProfile(company_name="Undated", stock_code="9999.HK")
    )
    with pytest.raises(MarketFeatureHandoffError, match="not available"):
        build_market_feature_handoff(view)


def test_a_legacy_snapshot_view_is_not_a_market_x_handoff() -> None:
    view = SnapshotMarketContextProvider().context(
        IPOProfile(company_name="Demo", stock_code="9999.HK", listing_date=date(2024, 6, 1)),
        MarketSnapshot(source="governed_eod", hsi_return_5d=0.01),
    )
    with pytest.raises(MarketFeatureHandoffError, match="frozen Market-X Core manifest"):
        build_market_feature_handoff(view)
