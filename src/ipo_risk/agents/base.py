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
from ipo_risk.schemas.final_supervision import (
    FinalSupervisionInput,
    FinalSupervisionResult,
    MarketContextView,
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


class MarketContextProvider(Protocol):
    """Explanatory market channel, never a risk producer.

    Takes the snapshot the workflow already loaded rather than fetching its own:
    two different snapshots inside one analysis would be a provenance hazard.
    """

    name: str
    def context(self, profile: IPOProfile, market: MarketSnapshot | None = None) -> MarketContextView: ...


class FinalSupervisor(Protocol):
    """Composes existing channels; creates no new signal."""

    name: str
    def finalize(self, inputs: FinalSupervisionInput) -> FinalSupervisionResult: ...
