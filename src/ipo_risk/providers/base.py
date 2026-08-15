from datetime import date
from typing import Protocol, TypeVar

from pydantic import BaseModel

from ipo_risk.schemas import Evidence, IPOProfile, LLMCallMetadata, MarketSnapshot
from ipo_risk.schemas.market import IPOMarketMetadata, MarketDailyBar

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
    """V04 market source while retaining the v0.3 snapshot compatibility call."""

    def get_snapshot(self, profile: IPOProfile) -> MarketSnapshot: ...

    def get_listing_metadata(self, stock_code: str) -> IPOMarketMetadata | None: ...

    def get_daily_bars(
        self,
        stock_code: str,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[MarketDailyBar]: ...
class IPODataProvider(Protocol):
    def get_profile(self, company_name: str, stock_code: str = "") -> IPOProfile: ...
