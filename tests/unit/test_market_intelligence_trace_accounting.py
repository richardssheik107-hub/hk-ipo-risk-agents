from __future__ import annotations

from ipo_risk.agents.market_intelligence import MarketIntelligenceAgent
from ipo_risk.providers.llm import UnavailableLLMProvider
from ipo_risk.schemas.final_supervision import ChannelStatus, MarketContextView, MarketObservation


def _available(name: str, value: float, unit: str = "ratio") -> MarketObservation:
    return MarketObservation(
        name=name,
        value=value,
        unit=unit,
        availability="available",
        derivation="governed test fact",
        source="governed_test",
    )


def _context() -> MarketContextView:
    return MarketContextView(
        status=ChannelStatus.AVAILABLE,
        reason="governed fixture",
        observations=(
            _available("recent_ipo_break_rate", 0.30),
            _available("recent_ipo_return_5d", 0.02),
            _available("recent_ipo_1d_sample_count", 8, "count"),
            _available("recent_ipo_5d_sample_count", 7, "count"),
            _available("hsi_return_5d", 0.02),
            _available("hsi_return_20d", 0.04),
            _available("market_volatility_20d", 0.012),
            _available("market_turnover_20d_mean", 100.0, "currency"),
        ),
        provenance={
            "case_id": "ipo_2024_02410",
            "stock_code": "2410.HK",
            "listing_date": "2024-08-20",
            "pit_cutoff_date": "2024-08-20",
        },
    )


def test_every_market_intelligence_trace_event_accounts_for_its_governed_inputs() -> None:
    bundle = MarketIntelligenceAgent(UnavailableLLMProvider("offline test")).analyze(
        _context(), run_id="trace-test"
    )

    assert len(bundle.trace_events) == 3
    assert all(
        event.evidence_ids
        or event.calculation_ids
        or str(event.details.get("no_evidence_reason") or "")
        for event in bundle.trace_events
    )
    assert all(
        evidence_id.startswith("market_feature:")
        for event in bundle.trace_events[:2]
        for evidence_id in event.evidence_ids
    )
    assert "market_skill:deterministic_context" in bundle.trace_events[-1].evidence_ids
