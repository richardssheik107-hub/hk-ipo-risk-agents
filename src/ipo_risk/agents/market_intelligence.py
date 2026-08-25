"""Governed Market facts -> deterministic skills -> bounded LLM interpretation."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from enum import StrEnum
from pathlib import Path
from time import perf_counter
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ipo_risk.market.skills import IPOHeat, IPOHeatSkill, MarketRegime, MarketRegimeSkill
from ipo_risk.market.skills.models import IPOHeatResult, MarketRegimeResult, SkillDriver
from ipo_risk.providers.base import LLMProvider
from ipo_risk.schemas import Evidence, EvidenceSourceType, IPOProfile
from ipo_risk.schemas.competition_runtime import AgentResultEnvelope, TraceEvent, TraceEventType
from ipo_risk.schemas.final_supervision import ChannelStatus, MarketContextView, MarketObservation


MARKET_INTELLIGENCE_SCHEMA_VERSION = "v04_market_intelligence_v1"
MARKET_INTERPRETATION_PROMPT_VERSION = "v04_market_interpretation_v2"
MARKET_INTERPRETATION_TASK = "market_context_interpretation"
EXTENDED_READINESS_SOURCE_VERSION = "v04_c_extended_readiness_v1"

_GOVERNED_FEATURES = (
    "hsi_return_5d",
    "hsi_return_20d",
    "industry_return_5d",
    "industry_return_20d",
    "recent_ipo_break_rate",
    "recent_ipo_return_5d",
    "recent_ipo_1d_sample_count",
    "recent_ipo_5d_sample_count",
    "market_turnover_20d_mean",
    "market_volatility_20d",
)
_UNITS = {
    "hsi_return_5d": "ratio",
    "hsi_return_20d": "ratio",
    "industry_return_5d": "ratio",
    "industry_return_20d": "ratio",
    "recent_ipo_break_rate": "ratio",
    "recent_ipo_return_5d": "ratio",
    "recent_ipo_1d_sample_count": "count",
    "recent_ipo_5d_sample_count": "count",
    "market_turnover_20d_mean": "currency",
    "market_volatility_20d": "ratio",
}
_NUMBER_IN_PROSE = re.compile(r"(?<![A-Za-z_])[-+]?\d+(?:\.\d+)?%?")


class MarketInterpretationStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class InterpretationDriver(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    statement: str = Field(min_length=1)
    source_feature_ids: tuple[str, ...] = Field(min_length=1)

    @field_validator("statement")
    @classmethod
    def _no_numeric_fact(cls, value: str) -> str:
        if _NUMBER_IN_PROSE.search(value):
            raise ValueError("LLM interpretation prose cannot introduce numeric market facts")
        return value


class MarketInterpretation(BaseModel):
    """Narrative-only schema: deterministic states and numeric facts cannot be returned."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: str = Field(min_length=1)
    market_regime_interpretation: str = Field(min_length=1)
    ipo_heat_interpretation: str = Field(min_length=1)
    liquidity_interpretation: str = Field(min_length=1)
    key_drivers: tuple[InterpretationDriver, ...]
    uncertainties: tuple[str, ...] = ()

    @field_validator(
        "summary",
        "market_regime_interpretation",
        "ipo_heat_interpretation",
        "liquidity_interpretation",
    )
    @classmethod
    def _no_numeric_fact(cls, value: str) -> str:
        if _NUMBER_IN_PROSE.search(value):
            raise ValueError("LLM interpretation prose cannot introduce numeric market facts")
        return value

    @field_validator("uncertainties")
    @classmethod
    def _uncertainties_have_no_numeric_fact(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(_NUMBER_IN_PROSE.search(value) for value in values):
            raise ValueError("LLM interpretation prose cannot introduce numeric market facts")
        return values


class MarketIntelligenceBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    market_context: MarketContextView
    ipo_heat: IPOHeatResult
    market_regime: MarketRegimeResult
    interpretation_status: MarketInterpretationStatus
    interpretation: MarketInterpretation | None = None
    interpretation_reason: str
    agent_result: AgentResultEnvelope
    trace_events: tuple[TraceEvent, ...]


class GovernedExtendedReadinessMarketContextProvider:
    """Read the already-materialized C readiness artifact without recalculating data."""

    name = "governed_v04_c_extended_readiness"

    def __init__(self, readiness_path: str | Path) -> None:
        self.readiness_path = Path(readiness_path)

    def context(self, profile: IPOProfile, market=None) -> MarketContextView:
        del market
        try:
            if not profile.stock_code or profile.listing_date is None:
                raise ValueError("stock_code and listing_date are required")
            with self.readiness_path.open(encoding="utf-8-sig", newline="") as handle:
                rows = [
                    row for row in csv.DictReader(handle)
                    if row.get("stock_code") == profile.stock_code
                    and row.get("listing_date") == profile.listing_date.isoformat()
                ]
            if len(rows) != 1:
                raise ValueError("profile does not resolve to exactly one readiness row")
            row = rows[0]
            benchmark_date = row.get("benchmark_observation_date", "")
            if benchmark_date and benchmark_date >= row["listing_date"]:
                raise ValueError("benchmark observation date must be strictly before listing date")
            observations = self._observations(row)
            split = "development" if profile.listing_date.year <= 2023 else "validation"
            if row.get("dataset_split") != split:
                raise ValueError("dataset split conflicts with listing year")
        except (OSError, ValueError, TypeError) as exc:
            return MarketContextView(
                status=ChannelStatus.UNAVAILABLE_ERROR,
                reason=f"governed Extended readiness projection failed validation: {exc}",
                provenance={"feature_pipeline": self.name},
            )
        return MarketContextView(
            status=ChannelStatus.AVAILABLE,
            reason="validated governed C Extended readiness projection",
            observations=observations,
            provenance={
                "feature_pipeline": self.name,
                "case_id": row["case_id"],
                "stock_code": row["stock_code"],
                "listing_date": row["listing_date"],
                "dataset_split": row["dataset_split"],
                "pit_cutoff_date": row["listing_date"],
                "cutoff_semantics": "market_date_strictly_before_listing_date",
                "source_provider": "governed_market_x_extended_readiness",
                "source_version": EXTENDED_READINESS_SOURCE_VERSION,
                "source_sha256": self._sha256(),
            },
        )

    def _sha256(self) -> str:
        digest = hashlib.sha256()
        with self.readiness_path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def _observations(row: dict[str, str]) -> tuple[MarketObservation, ...]:
        observations: list[MarketObservation] = []
        for name in _GOVERNED_FEATURES:
            available = row.get(f"{name}__available")
            missing = row.get(f"{name}__missing")
            if available not in {"True", "False"} or missing not in {"True", "False"}:
                raise ValueError(f"{name} availability flags are invalid")
            if (available == "True") == (missing == "True"):
                raise ValueError(f"{name} availability flags are not complementary")
            raw_value = row.get(name, "")
            missing_reason = row.get(f"{name}__missing_reason", "")
            if available == "True":
                if raw_value == "" or missing_reason:
                    raise ValueError(f"{name} available value is incomplete")
                value = float(raw_value)
                if not math.isfinite(value):
                    raise ValueError(f"{name} available value is not finite")
                observations.append(MarketObservation(
                    name=name,
                    value=value,
                    unit=_UNITS[name],
                    availability="available",
                    derivation="governed point-in-time Market-X Extended readiness feature",
                    source="v04_c_extended_readiness",
                ))
            else:
                if raw_value != "" or not missing_reason:
                    raise ValueError(f"{name} unavailable value must remain null with a reason")
                if name.startswith("industry_return_") and missing_reason not in {
                    "INDUSTRY_MAPPING_PIT_BLOCKED", "MISSING_INDUSTRY_CLASSIFICATION"
                }:
                    raise ValueError(f"{name} does not retain governed PIT-blocked semantics")
                observations.append(MarketObservation(
                    name=name,
                    availability="unavailable",
                    missing_reason=missing_reason,
                    source="v04_c_extended_readiness",
                ))
        return tuple(observations)


class MarketIntelligenceAgent:
    """Build a frozen MarketContextView projection plus traceable interpretation."""

    name = "market_intelligence"

    def __init__(self, llm_provider: LLMProvider | None = None) -> None:
        self.llm_provider = llm_provider
        self.ipo_heat_skill = IPOHeatSkill()
        self.market_regime_skill = MarketRegimeSkill()

    def analyze(self, context: MarketContextView, *, run_id: str) -> MarketIntelligenceBundle:
        if context.status is not ChannelStatus.AVAILABLE:
            raise ValueError("Market Intelligence requires an available governed MarketContextView")
        case_id = str(context.provenance.get("case_id") or "unknown_case")
        started = perf_counter()
        heat = self.ipo_heat_skill.evaluate(context.observations)
        regime = self.market_regime_skill.evaluate(context.observations)
        deterministic = self._deterministic_payload(heat, regime, context.observations)
        enriched = context.model_copy(update={
            "provenance": {
                **context.provenance,
                "market_intelligence_schema_version": MARKET_INTELLIGENCE_SCHEMA_VERSION,
                "market_intelligence": deterministic,
            }
        })
        trace = [
            self._skill_trace(case_id, run_id, self.ipo_heat_skill.name, heat.model_dump(mode="json")),
            self._skill_trace(case_id, run_id, self.market_regime_skill.name, regime.model_dump(mode="json")),
        ]
        interpretation, status, reason, llm_trace = self._interpret(enriched, run_id)
        trace.append(llm_trace)
        if interpretation is not None:
            enriched = enriched.model_copy(update={
                "provenance": {
                    **enriched.provenance,
                    "llm_market_interpretation": interpretation.model_dump(mode="json"),
                    "llm_market_interpretation_status": status.value,
                }
            })
        else:
            enriched = enriched.model_copy(update={
                "provenance": {
                    **enriched.provenance,
                    "llm_market_interpretation_status": status.value,
                    "llm_market_interpretation_reason": reason,
                }
            })
        metadata = getattr(self.llm_provider, "last_call_metadata", None)
        agent_result = AgentResultEnvelope(
            case_id=case_id,
            run_id=run_id,
            agent_name=self.name,
            status="completed" if status is MarketInterpretationStatus.AVAILABLE else "partial",
            provider_name=metadata.provider_name if metadata else getattr(self.llm_provider, "name", None),
            model_name=metadata.model_name if metadata else None,
            prompt_version=MARKET_INTERPRETATION_PROMPT_VERSION,
            warnings=[] if status is MarketInterpretationStatus.AVAILABLE else [reason],
            metadata={
                "task": "interpret governed pre-listing market context",
                "market_context_status": context.status.value,
                "source_feature_ids": deterministic["source_feature_ids"],
                "market_side_risk_only": True,
                "latency_ms": max(0, int((perf_counter() - started) * 1000)),
            },
        )
        return MarketIntelligenceBundle(
            market_context=enriched,
            ipo_heat=heat,
            market_regime=regime,
            interpretation_status=status,
            interpretation=interpretation,
            interpretation_reason=reason,
            agent_result=agent_result,
            trace_events=tuple(trace),
        )

    @staticmethod
    def _deterministic_payload(
        heat, regime, observations: tuple[MarketObservation, ...]
    ) -> dict[str, Any]:
        drivers: tuple[SkillDriver, ...] = (*regime.drivers, *heat.drivers)
        if regime.market_regime is MarketRegime.RISK_OFF and heat.ipo_heat is IPOHeat.COLD:
            risk_level = "high"
        elif regime.market_regime is MarketRegime.RISK_ON and heat.ipo_heat is IPOHeat.HOT:
            risk_level = "low"
        else:
            risk_level = "medium"
        source_ids = tuple(dict.fromkeys(item.name for item in observations))
        missing_reasons = {
            item.name: item.missing_reason
            for item in observations
            if item.availability == "unavailable" and item.missing_reason
        }
        return {
            "market_regime": regime.market_regime.value,
            "risk_level": risk_level,
            "risk_scope": "market_side_only",
            "ipo_heat": heat.ipo_heat.value,
            "liquidity_condition": regime.liquidity_condition.value,
            "key_drivers": [driver.model_dump(mode="json") for driver in drivers],
            "uncertainties": list(regime.uncertainties),
            "source_feature_ids": list(source_ids),
            "missing_reasons": missing_reasons,
            "ipo_heat_policy_version": heat.policy_version,
            "market_regime_policy_version": regime.policy_version,
        }

    def _interpret(self, context: MarketContextView, run_id: str):
        case_id = str(context.provenance.get("case_id") or "unknown_case")
        if self.llm_provider is None:
            reason = "LLM provider is not configured; deterministic MarketContext is retained"
            return None, MarketInterpretationStatus.UNAVAILABLE, reason, TraceEvent(
                case_id=case_id, run_id=run_id, event_type=TraceEventType.LLM,
                status="unavailable", agent_name=self.name, action=MARKET_INTERPRETATION_TASK,
                tool_or_skill="LLMProvider.generate_structured",
                prompt_version=MARKET_INTERPRETATION_PROMPT_VERSION,
                details={"reason": reason},
            )
        evidence = self._bounded_evidence(context)
        started = perf_counter()
        try:
            result = self.llm_provider.generate_structured(
                task_name=MARKET_INTERPRETATION_TASK,
                prompt_version=MARKET_INTERPRETATION_PROMPT_VERSION,
                evidence=evidence,
                response_model=MarketInterpretation,
            )
            if not isinstance(result, MarketInterpretation):
                result = MarketInterpretation.model_validate(result)
            allowed = {item.name for item in context.observations}
            referenced = {
                feature for driver in result.key_drivers for feature in driver.source_feature_ids
            }
            if not referenced <= allowed:
                raise ValueError("LLM interpretation references an out-of-scope market feature")
            unavailable_industry = {
                item.name for item in context.observations
                if item.name.startswith("industry_return_") and item.availability == "unavailable"
            }
            if referenced & unavailable_industry:
                raise ValueError("LLM interpretation treats unavailable industry facts as drivers")
        except Exception as exc:
            reason = f"LLM market interpretation unavailable: {type(exc).__name__}"
            return None, MarketInterpretationStatus.UNAVAILABLE, reason, TraceEvent(
                case_id=case_id, run_id=run_id, event_type=TraceEventType.LLM,
                status="unavailable", agent_name=self.name, action=MARKET_INTERPRETATION_TASK,
                tool_or_skill="LLMProvider.generate_structured",
                provider_name=getattr(self.llm_provider, "name", None),
                prompt_version=MARKET_INTERPRETATION_PROMPT_VERSION,
                latency_ms=max(0, int((perf_counter() - started) * 1000)),
                details={"reason": reason},
            )
        metadata = getattr(self.llm_provider, "last_call_metadata", None)
        return result, MarketInterpretationStatus.AVAILABLE, "structured grounded interpretation available", TraceEvent(
            case_id=case_id, run_id=run_id, event_type=TraceEventType.LLM,
            status="completed", agent_name=self.name, action=MARKET_INTERPRETATION_TASK,
            tool_or_skill="LLMProvider.generate_structured",
            provider_name=metadata.provider_name if metadata else getattr(self.llm_provider, "name", None),
            model_name=metadata.model_name if metadata else None,
            prompt_version=MARKET_INTERPRETATION_PROMPT_VERSION,
            latency_ms=metadata.latency_ms if metadata else max(0, int((perf_counter() - started) * 1000)),
            request_id=metadata.request_id if metadata else None,
            raw_response_hash=metadata.raw_response_hash if metadata else None,
            details={"structured_output": result.model_dump(mode="json")},
        )

    @staticmethod
    def _bounded_evidence(context: MarketContextView) -> list[Evidence]:
        evidence: list[Evidence] = []
        for item in context.observations:
            payload = {
                "feature_id": item.name,
                "value": item.value,
                "unit": item.unit,
                "availability": item.availability,
                "missing_reason": item.missing_reason,
            }
            evidence.append(Evidence(
                evidence_id=f"market_feature:{item.name}",
                text=json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                section="governed_market_context",
                source_type=EvidenceSourceType.MARKET_DATA,
                metadata={"feature_id": item.name},
            ))
        intelligence = context.provenance["market_intelligence"]
        evidence.append(Evidence(
            evidence_id="market_skill:deterministic_context",
            text=json.dumps(intelligence, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            section="deterministic_market_skills",
            source_type=EvidenceSourceType.CALCULATION,
        ))
        return evidence

    @staticmethod
    def _skill_trace(case_id: str, run_id: str, skill: str, output: dict[str, Any]) -> TraceEvent:
        return TraceEvent(
            case_id=case_id,
            run_id=run_id,
            event_type=TraceEventType.SKILL,
            status="completed",
            agent_name="market_intelligence",
            action="deterministic_market_classification",
            tool_or_skill=skill,
            latency_ms=0,
            details={
                "input_feature_ids": output["source_feature_ids"],
                "structured_output": output,
            },
        )
