from __future__ import annotations

from types import SimpleNamespace

from ipo_risk.agents.market_intelligence import MarketIntelligenceAgent
from ipo_risk.core.config import Settings, load_settings
from ipo_risk.core.container import DependencyContainer, default_registry
from ipo_risk.providers.llm import UnavailableLLMProvider
from ipo_risk.schemas.final_supervision import ChannelStatus, MarketContextView, MarketObservation
from ipo_risk.workflows.v04_ai import V04AIWorkflow


class _ContextProvider:
    def __init__(self, view: MarketContextView) -> None:
        self.view = view

    def context(self, profile, market):
        del profile, market
        return self.view


def _observation(name: str, value: float, unit: str = "ratio") -> MarketObservation:
    return MarketObservation(
        name=name,
        value=value,
        unit=unit,
        availability="available",
        derivation="test governed PIT fact",
        source="test_market_x",
    )


def _available_view() -> MarketContextView:
    return MarketContextView(
        status=ChannelStatus.AVAILABLE,
        reason="test governed context",
        observations=(
            _observation("hsi_return_5d", 0.03),
            _observation("hsi_return_20d", 0.04),
            _observation("market_volatility_20d", 0.009),
            _observation("market_turnover_20d_mean", 100.0, "currency"),
            _observation("recent_ipo_break_rate", 0.20),
            _observation("recent_ipo_return_5d", 0.02),
            _observation("recent_ipo_1d_sample_count", 6.0, "count"),
            _observation("recent_ipo_5d_sample_count", 6.0, "count"),
            MarketObservation(
                name="industry_return_5d",
                availability="unavailable",
                missing_reason="INDUSTRY_MAPPING_PIT_BLOCKED",
                source="test_market_x",
            ),
            MarketObservation(
                name="industry_return_20d",
                availability="unavailable",
                missing_reason="INDUSTRY_MAPPING_PIT_BLOCKED",
                source="test_market_x",
            ),
        ),
        provenance={
            "case_id": "ipo_2024_02410",
            "stock_code": "2410.HK",
            "listing_date": "2024-08-20",
        },
    )


def _workflow(view: MarketContextView) -> V04AIWorkflow:
    workflow = V04AIWorkflow.__new__(V04AIWorkflow)
    workflow.market_context = _ContextProvider(view)
    workflow.market_intelligence_agent = MarketIntelligenceAgent(
        llm_provider=UnavailableLLMProvider("test provider unavailable")
    )
    return workflow


def _state():
    return {
        "request": SimpleNamespace(request_id="run-001"),
        "profile": SimpleNamespace(stock_code="2410.HK"),
        "market": None,
        "agent_logs": [],
        "errors": [],
    }


def test_v04_market_intelligence_enriches_governed_context_and_emits_trace():
    outcome = _workflow(_available_view()).explain_market(_state())

    enriched = outcome["market_context_view"]
    intelligence = enriched.provenance["market_intelligence"]
    assert intelligence["ipo_heat"] == "hot"
    assert intelligence["market_regime"] == "risk_on"
    assert intelligence["missing_reasons"]["industry_return_5d"] == "INDUSTRY_MAPPING_PIT_BLOCKED"

    diagnostics = outcome["component_diagnostics"]["market_intelligence"]
    assert diagnostics["status"] == "completed"
    assert diagnostics["interpretation_status"] == "unavailable"
    assert diagnostics["agent_result"]["run_id"] == "run-001"
    assert diagnostics["agent_result"]["case_id"] == "ipo_2024_02410"
    assert len(diagnostics["trace_events"]) == 3
    assert {event["event_type"] for event in diagnostics["trace_events"]} == {"skill", "llm"}
    assert outcome.get("errors", []) == []


def test_v04_market_intelligence_skips_cleanly_when_governed_context_is_unavailable():
    view = MarketContextView(
        status=ChannelStatus.UNAVAILABLE_ERROR,
        reason="test missing governed context",
        provenance={"case_id": "ipo_2024_02410"},
    )
    outcome = _workflow(view).explain_market(_state())

    assert outcome["market_context_view"] == view
    assert outcome["component_diagnostics"]["market_intelligence"] == {
        "status": "skipped_context_unavailable",
        "reason": "test missing governed context",
    }
    assert outcome.get("errors", []) == []


def test_container_keeps_market_intelligence_out_of_legacy_agent_loop():
    settings = Settings(
        workflow_version="enhanced_v2",
        market_agent="market_intelligence",
        market_context="gate_pending",
        llm_provider="unavailable",
    )
    workflow = DependencyContainer(settings, default_registry()).create_workflow()

    assert isinstance(workflow, V04AIWorkflow)
    assert workflow.market_intelligence_agent.name == "market_intelligence"
    assert all(agent.name != "market_intelligence" for agent in workflow.agents)


def test_only_ai_v04_configs_enable_market_intelligence():
    assert load_settings("configs/v04_ai.yaml").market_agent == "market_intelligence"
    assert load_settings("configs/v04_ai_table.yaml").market_agent == "market_intelligence"
    assert load_settings("configs/v04_offline.yaml").market_agent == "disabled"
    assert load_settings("configs/v04_offline_table.yaml").market_agent == "disabled"
