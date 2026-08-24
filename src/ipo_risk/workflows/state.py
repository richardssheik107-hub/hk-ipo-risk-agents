"""Workflow state and explicit append reducers for LangGraph."""
from typing import Annotated, Any, TypedDict
from ipo_risk.schemas import AgentLog, AnalysisError, RiskItem

def append(left: list[Any], right: list[Any] | None) -> list[Any]: return [*left, *(right or [])]
def reduce_risks(left: list[RiskItem], right: list[RiskItem] | None) -> list[RiskItem]:
    return list({risk.risk_id: risk for risk in [*left, *(right or [])]}.values())
def merge_dicts(left: dict[str, Any], right: dict[str, Any] | None) -> dict[str, Any]:
    return {**left, **(right or {})}
class WorkflowState(TypedDict, total=False):
    request: Any; profile: Any; chunks: list[Any]; market: Any
    candidates: Annotated[list[RiskItem], reduce_risks]
    verified_risks: Annotated[list[RiskItem], reduce_risks]
    pending_risks: Annotated[list[RiskItem], reduce_risks]
    rejected_risks: Annotated[list[RiskItem], reduce_risks]
    # enhanced_v2 replacement snapshot; unlike candidate reducers this must allow
    # Supervisor deduplication to remove semantically duplicate risk IDs.
    supervised_verified_risks: list[RiskItem]
    agent_logs: Annotated[list[AgentLog], append]
    errors: Annotated[list[AnalysisError], append]
    prediction: Any; report_sections: list[Any]
    # PR-G replacement snapshots; the Final Supervisor composes them, so unlike
    # the risk lists these must overwrite rather than accumulate.
    supervision_result: Any; market_context_view: Any; model_prediction_view: Any; final_supervision: Any
    document_metadata: dict[str, Any]
    component_diagnostics: Annotated[dict[str, Any], merge_dicts]
