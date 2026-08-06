from typing import Protocol, TypeVar

from pydantic import BaseModel

from ipo_risk.schemas import Evidence, IPOProfile, LLMCallMetadata, MarketSnapshot

StructuredModel = TypeVar("StructuredModel", bound=BaseModel)

class LLMProvider(Protocol):
    name: str
    last_call_metadata: LLMCallMetadata | None

    def complete(self, prompt: str) -> str: ...

    def generate_structured(
        self,
        *,
        task_name: str,
        prompt_version: str,
        evidence: list[Evidence],
        response_model: type[StructuredModel],
    ) -> StructuredModel: ...
class MarketDataProvider(Protocol):
    def get_snapshot(self, profile: IPOProfile) -> MarketSnapshot: ...
class IPODataProvider(Protocol):
    def get_profile(self, company_name: str, stock_code: str = "") -> IPOProfile: ...
