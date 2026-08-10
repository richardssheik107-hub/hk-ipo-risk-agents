from datetime import date
from hashlib import sha256
from time import perf_counter
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from ipo_risk.providers.llm import LLMFailureKind, LLMProviderError
from ipo_risk.providers.prompt_registry import (
    PromptResolutionError,
    resolve_domain_instruction,
)
from ipo_risk.schemas import Evidence, IPOProfile, LLMCallMetadata, MarketSnapshot

class MockLLMProvider:
    name = "mock"

    def __init__(self, responses: dict[str, dict[str, Any]] | None = None) -> None:
        self.responses = responses or {}
        self.last_call_metadata: LLMCallMetadata | None = None

    def complete(self, prompt: str) -> str:
        started = perf_counter()
        raw = "mock response"
        self.last_call_metadata = LLMCallMetadata(
            provider_name=self.name,
            model_name="mock-complete",
            prompt_version="legacy_complete",
            latency_ms=max(0, int((perf_counter() - started) * 1000)),
            token_usage={},
            request_id=str(uuid4()),
            raw_response_hash=sha256(raw.encode("utf-8")).hexdigest(),
        )
        return raw

    def generate_structured(
        self,
        *,
        task_name: str,
        prompt_version: str,
        evidence: list[Evidence],
        response_model: type[BaseModel],
    ) -> BaseModel:
        started = perf_counter()
        try:
            resolve_domain_instruction(task_name, prompt_version)
        except PromptResolutionError:
            raise LLMProviderError(
                LLMFailureKind.REQUEST,
                "LLM prompt identity is not registered",
                recoverable=False,
                attempts=0,
            ) from None
        payload = self.responses.get(task_name, {})
        result = response_model.model_validate(payload)
        raw = result.model_dump_json()
        self.last_call_metadata = LLMCallMetadata(
            provider_name=self.name,
            model_name="mock-structured",
            prompt_version=prompt_version,
            latency_ms=max(0, int((perf_counter() - started) * 1000)),
            token_usage={},
            request_id=str(uuid4()),
            raw_response_hash=sha256(raw.encode("utf-8")).hexdigest(),
        )
        return result
class MockMarketDataProvider:
    def get_snapshot(self, profile: IPOProfile) -> MarketSnapshot:
        return MarketSnapshot(observation_date=profile.listing_date or date.today(), hsi_return_5d=-.04, recent_ipo_break_rate=.42, market_volatility=.31, sentiment_score=35, source="mock")
class MockIPODataProvider:
    def get_profile(self, company_name: str, stock_code: str = "") -> IPOProfile: return IPOProfile(company_name=company_name, stock_code=stock_code, industry="mock")
