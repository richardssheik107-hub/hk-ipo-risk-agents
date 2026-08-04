"""Application boundary: configure, assemble, execute, persist, return."""
from datetime import datetime, timezone
from ipo_risk.core.config import Settings, load_settings
from ipo_risk.core.container import DependencyContainer, default_registry
from ipo_risk.schemas import AgentLog, AnalysisError, IPOAnalysisRequest, IPOAnalysisResult, LogStatus, TaskStatus

class IPOAnalysisService:
    def __init__(self, settings: Settings | None = None, container: DependencyContainer | None = None, repository=None):
        if settings is not None and not isinstance(settings, Settings):
            repository, settings = settings, None
        self.settings = settings or load_settings()
        self.container = container or DependencyContainer(self.settings, default_registry())
        self.workflow = self.container.create_workflow()
        self.repository = repository or self.container.create_repository()
    def _component_modes(self):
        settings = self.settings
        return {
            "parser": "real" if settings.parser == "pymupdf" else "mock",
            "retriever": "real" if settings.retriever == "keyword" else "mock",
            "financial_agent": "real" if settings.financial_agent == "cash_runway" else "mock",
            "legal_agent": "unavailable" if settings.legal_agent == "disabled" else "mock",
            "business_agent": "unavailable" if settings.business_agent == "disabled" else "mock",
            "market_agent": "unavailable" if settings.market_agent == "disabled" else "mock",
            "verifier": "deterministic" if settings.verifier == "rule" else settings.verifier,
            "predictor": "deterministic_rule" if settings.predictor == "rule_based" else settings.predictor,
            "market_data_provider": "unavailable" if settings.market_data_provider == "unavailable" else "mock",
            "ipo_data_provider": "request" if settings.ipo_data_provider == "request" else "mock",
            "report_generator": "mock" if settings.report_generator == "mock" else settings.report_generator,
        }
    def _result_metadata(self, state):
        diagnostics = state.get("component_diagnostics", {})
        financial = diagnostics.get("financial", {})
        prediction = state.get("prediction")
        prediction_metadata = prediction.metadata if prediction is not None else {}
        return {
            "component_modes": self._component_modes(),
            "document": state.get("document_metadata", {}),
            "real_slice": {
                "cash_runway_attempted": self.settings.financial_agent == "cash_runway",
                "cash_runway_built": financial.get("status") == "built",
                "cash_runway_verified": any(
                    risk.risk_code == "cash_runway"
                    for risk in state.get("verified_risks", [])
                ),
                "degraded_mode": prediction_metadata.get("degraded_mode", False),
                "degradation_reasons": prediction_metadata.get("degradation_reasons", []),
            },
            "configuration": {
                "workflow_version": self.settings.workflow_version,
                "use_mock": self.settings.use_mock,
                "config_name": "mock" if self.settings.use_mock else "real_pdf",
            },
            "component_diagnostics": diagnostics,
        }
    def _failure(self, request, exc):
        error = AnalysisError(stage="service", component="IPOAnalysisService", code="unrecoverable_workflow_failure", message=str(exc), recoverable=False)
        return IPOAnalysisResult(request_id=request.request_id, company_name=request.company_name, stock_code=request.stock_code, workflow_version=request.workflow_version, status=TaskStatus.FAILED, errors=[error], agent_logs=[AgentLog(task_id=request.request_id, step=1, agent_name="service", action="execute_workflow", status=LogStatus.FAILED, error=error, finished_at=datetime.now(timezone.utc))], finished_at=datetime.now(timezone.utc))
    def analyze(self, request: IPOAnalysisRequest) -> IPOAnalysisResult:
        try:
            state = self.workflow.invoke({"request": request, "candidates": [], "verified_risks": [], "pending_risks": [], "rejected_risks": [], "agent_logs": [], "errors": []})
            result = IPOAnalysisResult(request_id=request.request_id, company_name=request.company_name, stock_code=request.stock_code, workflow_version=self.settings.workflow_version, verified_risks=state.get("verified_risks", []), pending_risks=state.get("pending_risks", []), rejected_risks=state.get("rejected_risks", []), prediction=state.get("prediction"), agent_logs=state.get("agent_logs", []), report_sections=state.get("report_sections", []), errors=state.get("errors", []), status=TaskStatus.PARTIAL if state.get("errors") else TaskStatus.COMPLETED, finished_at=datetime.now(timezone.utc), metadata=self._result_metadata(state))
        except Exception as exc: result = self._failure(request, exc)
        try:
            save_log = AgentLog(task_id=request.request_id, step=len(result.agent_logs) + 1, agent_name="analysis_repository", action="save", status=LogStatus.SUCCESS, output_summary="analysis result persisted and read back", metadata={"round_trip_verified": True}, finished_at=datetime.now(timezone.utc))
            result = result.model_copy(update={"agent_logs": [*result.agent_logs, save_log]})
            self.repository.save(result)
            persisted = self.repository.get(result.analysis_id)
            if persisted is None or persisted.model_dump() != result.model_dump():
                raise RuntimeError("Persisted analysis result failed round-trip verification")
        except Exception as exc:
            error = AnalysisError(stage="repository", component="analysis_repository", code="save_failure", message=str(exc))
            log = AgentLog(task_id=request.request_id, step=len(result.agent_logs) + 1, agent_name="analysis_repository", action="save", status=LogStatus.FAILED, error=error, finished_at=datetime.now(timezone.utc))
            retained_logs = [item for item in result.agent_logs if not (item.agent_name == "analysis_repository" and item.action == "save" and item.status == LogStatus.SUCCESS)]
            result = result.model_copy(update={"status": TaskStatus.PARTIAL, "errors": [*result.errors, error], "agent_logs": [*retained_logs, log]})
        return result
