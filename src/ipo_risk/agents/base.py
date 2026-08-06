from typing import Protocol

from ipo_risk.schemas import (
    ComponentDiagnostic,
    DocumentChunk,
    Evidence,
    IPOProfile,
    MarketSnapshot,
    RiskItem,
    SupervisionResult,
    VerificationResult,
)

class RiskAgent(Protocol):
    name: str
    def analyze(self, profile: IPOProfile, chunks: list[DocumentChunk], market: MarketSnapshot | None = None) -> list[RiskItem]: ...


class DiagnosticSource(Protocol):
    """Optional v0.3 diagnostic channel; RiskAgent return type stays unchanged."""

    @property
    def last_diagnostics(self) -> list[ComponentDiagnostic]: ...


class RiskVerifier(Protocol):
    name: str
    def verify(self, risks: list[RiskItem], evidence_by_code: dict[str, list[Evidence]]) -> VerificationResult: ...


class RiskSupervisor(Protocol):
    name: str
    def supervise(self, risks: list[RiskItem]) -> SupervisionResult: ...
