"""Unavailable professional agents for the honest v0.2 real mode."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ipo_risk.schemas import DocumentChunk, IPOProfile, MarketSnapshot, RiskItem


class DisabledAgentDiagnostics(BaseModel):
    status: str = "component_not_implemented"
    available: bool = False
    reason: str = "professional_module_not_implemented_in_v0.2"
    metadata: dict[str, Any] = Field(default_factory=dict)


class _DisabledAgent:
    name = "disabled"

    def __init__(self) -> None:
        self.last_diagnostics = DisabledAgentDiagnostics(
            metadata={"component": self.name}
        )

    def analyze(
        self,
        profile: IPOProfile,
        chunks: list[DocumentChunk],
        market: MarketSnapshot | None = None,
    ) -> list[RiskItem]:
        """Return no risks because this component is unavailable, not risk-free."""

        return []


class DisabledLegalAgent(_DisabledAgent):
    name = "legal"


class DisabledBusinessAgent(_DisabledAgent):
    name = "business"


class DisabledMarketAgent(_DisabledAgent):
    name = "market"
