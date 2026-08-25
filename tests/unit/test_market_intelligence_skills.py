from __future__ import annotations

import csv
from datetime import date

import pytest

from ipo_risk.agents.final_supervisor import V04FinalSupervisor
from ipo_risk.agents.market_intelligence import (
    GovernedExtendedReadinessMarketContextProvider,
    MARKET_INTERPRETATION_PROMPT_VERSION,
    MARKET_INTERPRETATION_TASK,
    MarketIntelligenceAgent,
    MarketInterpretation,
    MarketInterpretationStatus,
)
from ipo_risk.market.skills import IPOHeat, IPOHeatSkill, MarketRegime, MarketRegimeSkill
from ipo_risk.market.skills.models import LiquidityCondition, VolatilityCondition
from ipo_risk.providers.llm import UnavailableLLMProvider
from ipo_risk.providers.mock import MockLLMProvider
from ipo_risk.providers.prompt_registry import resolve_domain_instruction
from ipo_risk.schemas import IPOProfile
from ipo_risk.schemas.final_supervision import (
    ChannelStatus,
    FinalSupervisionInput,
    MarketContextView,
    MarketObservation,
)


def _available(name: str, value: float) -> MarketObservation:
    return MarketObservation(
        name=name, value=value, unit="ratio", availability="available",
        derivation="strictly pre-listing test fact", source="governed_test",
    )


def _missing(name: str, reason: str = "source_unavailable") -> MarketObservation:
    return MarketObservation(
        name=name, availability="unavailable", missing_reason=reason,
        source="governed_test",
    )


def _heat_observations(
    *, break_rate=0.30, recent_return=0.02, count_1d=8, count_5d=7,
) -> tuple[MarketObservation, ...]:
    values = {
        "recent_ipo_break_rate": break_rate,
        "recent_ipo_return_5d": recent_return,
        "recent_ipo_1d_sample_count": count_1d,
        "recent_ipo_5d_sample_count": count_5d,
    }
    return tuple(
        _missing(name, "no_recent_ipo_sample") if value is None else _available(name, value)
        for name, value in values.items()
    )


def _regime_observations(
    *, short=0.02, medium=0.04, volatility=0.012, turnover=100.0,
    industry_reason="INDUSTRY_MAPPING_PIT_BLOCKED",
) -> tuple[MarketObservation, ...]:
    values = {
        "hsi_return_5d": short,
        "hsi_return_20d": medium,
        "market_volatility_20d": volatility,
        "market_turnover_20d_mean": turnover,
    }
    rows = [
        _missing(name) if value is None else _available(name, value)
        for name, value in values.items()
    ]
    rows.extend((
        _missing("industry_return_5d", industry_reason),
        _missing("industry_return_20d", industry_reason),
    ))
    return tuple(rows)


def _context() -> MarketContextView:
    return MarketContextView(
        status=ChannelStatus.AVAILABLE,
        reason="governed fixture",
        observations=(*_heat_observations(), *_regime_observations()),
        provenance={
            "case_id": "ipo_2024_02410",
            "stock_code": "2410.HK",
            "listing_date": "2024-08-20",
            "pit_cutoff_date": "2024-08-20",
            "cutoff_semantics": "market_date_strictly_before_listing_date",
            "source_version": "fixture_v1",
        },
    )


def _interpretation_payload(source_feature="hsi_return_20d") -> dict:
    return {
        "summary": "The governed signals indicate a constructive but qualified environment.",
        "market_regime_interpretation": "The broad market trend is supportive.",
        "ipo_heat_interpretation": "Recent issuance conditions are supportive.",
        "liquidity_interpretation": "Turnover is observed without a comparable historical baseline.",
        "key_drivers": [{
            "statement": "The medium-term index trend supports risk appetite.",
            "source_feature_ids": [source_feature],
        }],
        "uncertainties": ["Industry benchmarking is unavailable under the PIT constraint."],
    }


def test_market_interpretation_v2_prompt_requires_qualitative_prose() -> None:
    assert MARKET_INTERPRETATION_PROMPT_VERSION == "v04_market_interpretation_v2"
    instruction = resolve_domain_instruction(
        MARKET_INTERPRETATION_TASK,
        MARKET_INTERPRETATION_PROMPT_VERSION,
    )
    assert instruction is not None
    assert "summary" in instruction
    assert "driver.statement" in instruction
    assert "no digits" in instruction
    assert "1D, 5D, or 20D" in instruction
    assert "source_feature_ids" in instruction


class CapturingLLMProvider(MockLLMProvider):
    def generate_structured(self, **kwargs):
        self.supplied_evidence = kwargs["evidence"]
        return super().generate_structured(**kwargs)


def test_ipo_heat_normal_positive_and_high_break_rate_states() -> None:
    skill = IPOHeatSkill()
    assert skill.evaluate(_heat_observations()).ipo_heat is IPOHeat.HOT
    assert skill.evaluate(_heat_observations(break_rate=0.75)).ipo_heat is IPOHeat.COLD
    assert skill.evaluate(_heat_observations(recent_return=-0.08)).ipo_heat is IPOHeat.COLD
    assert skill.evaluate(_heat_observations(break_rate=0.45, recent_return=-0.01)).ipo_heat is IPOHeat.NEUTRAL


def test_ipo_heat_missing_is_not_neutral_or_zero_filled() -> None:
    result = IPOHeatSkill().evaluate(_heat_observations(
        break_rate=None, recent_return=None, count_1d=0, count_5d=0,
    ))
    assert result.ipo_heat is IPOHeat.INSUFFICIENT_DATA
    assert result.missingness["recent_ipo_break_rate"] == "no_recent_ipo_sample"
    assert result.drivers == ()


def test_ipo_heat_count_available_but_return_unavailable_and_deterministic() -> None:
    observations = _heat_observations(recent_return=None, count_1d=4, count_5d=0)
    skill = IPOHeatSkill()
    first = skill.evaluate(observations)
    assert first.recent_return_condition == "UNAVAILABLE"
    assert first.ipo_heat is IPOHeat.NEUTRAL
    assert first.model_dump_json() == skill.evaluate(observations).model_dump_json()


@pytest.mark.parametrize(
    ("short", "medium", "volatility", "expected"),
    [
        (0.02, 0.04, 0.012, MarketRegime.RISK_ON),
        (-0.02, -0.04, 0.012, MarketRegime.RISK_OFF),
        (0.02, -0.04, 0.012, MarketRegime.MIXED),
        (0.0, 0.0, 0.025, MarketRegime.MIXED),
    ],
)
def test_market_regime_trend_volatility_and_mixed(short, medium, volatility, expected) -> None:
    result = MarketRegimeSkill().evaluate(_regime_observations(
        short=short, medium=medium, volatility=volatility,
    ))
    assert result.market_regime is expected


def test_market_regime_turnover_is_never_absolute_high_or_low() -> None:
    low = MarketRegimeSkill().evaluate(_regime_observations(turnover=1.0))
    high = MarketRegimeSkill().evaluate(_regime_observations(turnover=1e15))
    assert low.liquidity_condition is LiquidityCondition.OBSERVED_UNBENCHMARKED
    assert high.liquidity_condition is LiquidityCondition.OBSERVED_UNBENCHMARKED
    assert low.market_regime == high.market_regime


def test_market_regime_missing_and_industry_pit_block_survive() -> None:
    result = MarketRegimeSkill().evaluate(_regime_observations(
        short=None, medium=None, volatility=None, turnover=None,
    ))
    assert result.market_regime is MarketRegime.INSUFFICIENT_DATA
    assert result.volatility_condition is VolatilityCondition.UNAVAILABLE
    assert any("INDUSTRY_MAPPING_PIT_BLOCKED" in item for item in result.uncertainties)
    assert result.model_dump_json() == MarketRegimeSkill().evaluate(_regime_observations(
        short=None, medium=None, volatility=None, turnover=None,
    )).model_dump_json()


def test_context_preserves_features_provenance_missingness_and_stable_serialization() -> None:
    first = MarketIntelligenceAgent().analyze(_context(), run_id="run-a")
    second = MarketIntelligenceAgent().analyze(_context(), run_id="run-b")
    assert first.market_context.observations == _context().observations
    intelligence = first.market_context.provenance["market_intelligence"]
    assert "hsi_return_20d" in intelligence["source_feature_ids"]
    assert "industry_return_5d" in intelligence["source_feature_ids"]
    assert intelligence["missing_reasons"]["industry_return_5d"] == "INDUSTRY_MAPPING_PIT_BLOCKED"
    assert first.market_context.provenance["pit_cutoff_date"] == "2024-08-20"
    assert intelligence["missing_reasons"] == second.market_context.provenance["market_intelligence"]["missing_reasons"]
    assert intelligence == second.market_context.provenance["market_intelligence"]
    assert first.interpretation_status is MarketInterpretationStatus.UNAVAILABLE


def test_llm_input_is_bounded_structured_and_cannot_mutate_facts() -> None:
    provider = CapturingLLMProvider({MARKET_INTERPRETATION_TASK: _interpretation_payload()})
    original = _context()
    bundle = MarketIntelligenceAgent(provider).analyze(original, run_id="run-llm")
    assert bundle.interpretation_status is MarketInterpretationStatus.AVAILABLE
    assert bundle.market_context.observations == original.observations
    assert provider.last_call_metadata is not None
    assert len(provider.supplied_evidence) == len(original.observations) + 1
    assert {item.evidence_id for item in provider.supplied_evidence if item.evidence_id.startswith("market_feature:")} == {
        f"market_feature:{item.name}" for item in original.observations
    }
    assert all(item.page is None and item.document_id is None for item in provider.supplied_evidence)
    llm_trace = bundle.trace_events[-1]
    assert llm_trace.provider_name == "mock"
    assert llm_trace.details["structured_output"] == bundle.interpretation.model_dump(mode="json")
    assert all(event.latency_ms is not None for event in bundle.trace_events)


def test_llm_unavailable_invalid_numeric_and_fake_industry_all_fall_back() -> None:
    unavailable = MarketIntelligenceAgent(UnavailableLLMProvider()).analyze(_context(), run_id="u")
    assert unavailable.interpretation is None
    assert unavailable.market_context.provenance["market_intelligence"]["market_regime"] == "RISK_ON"

    numeric = _interpretation_payload()
    numeric["summary"] = "The index rose by 99 percent."
    invalid = MarketIntelligenceAgent(MockLLMProvider({MARKET_INTERPRETATION_TASK: numeric})).analyze(
        _context(), run_id="i"
    )
    assert invalid.interpretation_status is MarketInterpretationStatus.UNAVAILABLE

    fake_industry = MarketIntelligenceAgent(MockLLMProvider({
        MARKET_INTERPRETATION_TASK: _interpretation_payload("industry_return_5d")
    })).analyze(_context(), run_id="f")
    assert fake_industry.interpretation_status is MarketInterpretationStatus.UNAVAILABLE
    assert next(
        item for item in fake_industry.market_context.observations
        if item.name == "industry_return_5d"
    ).value is None


def test_c_to_e_handoff_accepts_context_and_preserves_industry_missingness() -> None:
    bundle = MarketIntelligenceAgent().analyze(_context(), run_id="handoff")
    result = V04FinalSupervisor().finalize(FinalSupervisionInput(
        market_context=bundle.market_context,
    ))
    assert result.market_context == bundle.market_context
    industry = next(item for item in result.market_context.observations if item.name == "industry_return_5d")
    assert industry.value is None
    assert industry.missing_reason == "INDUSTRY_MAPPING_PIT_BLOCKED"
    serialized = result.model_dump_json()
    assert '"industry_return_5d"' in serialized
    assert "INDUSTRY_MAPPING_PIT_BLOCKED" in serialized


def test_extended_provider_rejects_listing_day_or_future_benchmark_row(tmp_path) -> None:
    path = tmp_path / "readiness.csv"
    row = {
        "case_id": "ipo_2024_02410", "stock_code": "2410.HK",
        "listing_date": "2024-08-20", "dataset_split": "validation",
        "benchmark_observation_date": "2024-08-20",
    }
    for name in (
        "hsi_return_5d", "hsi_return_20d", "industry_return_5d", "industry_return_20d",
        "recent_ipo_break_rate", "recent_ipo_return_5d", "recent_ipo_1d_sample_count",
        "recent_ipo_5d_sample_count", "market_turnover_20d_mean", "market_volatility_20d",
    ):
        available = not name.startswith("industry_return_")
        row[name] = "0.1" if available else ""
        row[f"{name}__available"] = str(available)
        row[f"{name}__missing"] = str(not available)
        row[f"{name}__missing_reason"] = "" if available else "INDUSTRY_MAPPING_PIT_BLOCKED"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(row))
        writer.writeheader()
        writer.writerow(row)
    view = GovernedExtendedReadinessMarketContextProvider(path).context(IPOProfile(
        company_name="同源康医药-B", stock_code="2410.HK", listing_date=date(2024, 8, 20),
    ))
    assert view.status is ChannelStatus.UNAVAILABLE_ERROR
    assert view.observations == ()
    assert "strictly before listing date" in view.reason


@pytest.mark.parametrize("numeric_uncertainty", [
    "The 5D industry benchmark is unavailable.",
    "The industry benchmark coverage is below 50%.",
])
def test_interpretation_schema_forbids_numeric_uncertainty(numeric_uncertainty: str) -> None:
    with pytest.raises(ValueError, match="numeric market facts"):
        MarketInterpretation.model_validate({
            **_interpretation_payload(),
            "uncertainties": [numeric_uncertainty],
        })


def test_interpretation_schema_accepts_compliant_qualitative_prose() -> None:
    result = MarketInterpretation.model_validate(_interpretation_payload())
    assert result.uncertainties == (
        "Industry benchmarking is unavailable under the PIT constraint.",
    )


def test_interpretation_schema_forbids_numeric_fact_and_extra_fields() -> None:
    with pytest.raises(ValueError, match="numeric market facts"):
        MarketInterpretation.model_validate({**_interpretation_payload(), "summary": "Turnover was 123."})
    with pytest.raises(ValueError):
        MarketInterpretation.model_validate({**_interpretation_payload(), "market_regime": "RISK_OFF"})
