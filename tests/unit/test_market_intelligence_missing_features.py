from __future__ import annotations

from ipo_risk.agents.market_intelligence import (
    MarketIntelligenceAgent,
    MarketInterpretationStatus,
)
from ipo_risk.market.skills import IPOHeat, IPOHeatSkill, MarketRegime, MarketRegimeSkill
from ipo_risk.schemas.final_supervision import ChannelStatus, MarketContextView, MarketObservation


def _available(name: str, value: float, *, unit: str = "ratio") -> MarketObservation:
    return MarketObservation(
        name=name,
        value=value,
        unit=unit,
        availability="available",
        derivation="strictly pre-listing governed test fact",
        source="governed_core_test",
    )


def _core_only_context() -> MarketContextView:
    # Mirrors the important integration boundary from PR-B Core: recent-IPO
    # features can be present while HSI/volatility/turnover Extended features are
    # absent entirely.  Absence is governed missingness, not a component error.
    observations = (
        _available("recent_ipo_break_rate", 0.30),
        _available("recent_ipo_return_5d", 0.02),
        _available("recent_ipo_1d_sample_count", 8.0, unit="count"),
        _available("recent_ipo_5d_sample_count", 7.0, unit="count"),
    )
    return MarketContextView(
        status=ChannelStatus.AVAILABLE,
        reason="validated frozen PR-B Market-X Core projection",
        observations=observations,
        provenance={
            "case_id": "ipo_2024_02410",
            "stock_code": "2410.HK",
            "listing_date": "2024-08-20",
            "feature_pipeline": "governed_pr_b_core",
        },
    )


def test_ipo_heat_absent_source_features_are_explicit_missingness() -> None:
    result = IPOHeatSkill().evaluate(())

    assert result.ipo_heat is IPOHeat.INSUFFICIENT_DATA
    assert result.drivers == ()
    assert result.missingness == {
        "recent_ipo_break_rate": "source_unavailable",
        "recent_ipo_return_5d": "source_unavailable",
        "recent_ipo_1d_sample_count": "source_unavailable",
        "recent_ipo_5d_sample_count": "source_unavailable",
    }


def test_market_regime_absent_extended_features_are_explicit_missingness() -> None:
    result = MarketRegimeSkill().evaluate(_core_only_context().observations)

    assert result.market_regime is MarketRegime.INSUFFICIENT_DATA
    assert result.drivers == ()
    assert result.missingness == {
        "hsi_return_5d": "source_unavailable",
        "hsi_return_20d": "source_unavailable",
        "market_volatility_20d": "source_unavailable",
        "market_turnover_20d_mean": "source_unavailable",
    }


def test_market_intelligence_core_only_context_degrades_without_crashing() -> None:
    context = _core_only_context()

    bundle = MarketIntelligenceAgent().analyze(context, run_id="core-only-run")

    assert bundle.market_context.observations == context.observations
    assert bundle.ipo_heat.ipo_heat is IPOHeat.HOT
    assert bundle.market_regime.market_regime is MarketRegime.INSUFFICIENT_DATA
    assert bundle.market_regime.missingness["hsi_return_5d"] == "source_unavailable"
    assert bundle.market_regime.missingness["market_turnover_20d_mean"] == "source_unavailable"
    assert bundle.interpretation_status is MarketInterpretationStatus.UNAVAILABLE
    assert bundle.agent_result.status == "partial"
    assert bundle.market_context.provenance["market_intelligence"]["market_regime"] == "INSUFFICIENT_DATA"
