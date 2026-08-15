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
        modes = {
            "parser": "real" if settings.parser in {"pymupdf", "pymupdf_table"} else "mock",
            "retriever": "real" if settings.retriever == "keyword" else "mock",
            "financial_agent": "real" if settings.financial_agent in {"cash_runway", "v03"} else "mock",
            "legal_agent": "real" if settings.legal_agent == "v03" else ("unavailable" if settings.legal_agent == "disabled" else "mock"),
            "business_agent": "real" if settings.business_agent == "v03" else ("unavailable" if settings.business_agent == "disabled" else "mock"),
            "market_agent": "unavailable" if settings.market_agent == "disabled" else "mock",
            "verifier": "deterministic" if settings.verifier in {"rule", "specialized_v03"} else settings.verifier,
            "predictor": "deterministic_rule" if settings.predictor == "rule_based" else settings.predictor,
            "market_data_provider": "unavailable" if settings.market_data_provider == "unavailable" else "mock",
            "ipo_data_provider": settings.ipo_data_provider if settings.ipo_data_provider in {"request", "catalog"} else "mock",
            "report_generator": "mock" if settings.report_generator == "mock" else settings.report_generator,
        }
        if settings.workflow_version == "enhanced_v2":
            llm_status = (
                "offline_unavailable"
                if settings.llm_provider == "unavailable"
                else "available"
                if settings.llm_provider == "openai_compatible"
                and all((settings.llm_api_key, settings.llm_base_url, settings.llm_model))
                else "credentials_unavailable"
                if settings.llm_provider == "openai_compatible"
                else settings.llm_provider
            )
            modes.update(
                {
                    "workflow": "enhanced_v2",
                    "supervisor": settings.supervisor,
                    "llm_provider": settings.llm_provider,
                    "llm_status": llm_status,
                }
            )
        return modes
    def _result_metadata(self, state):
        diagnostics = state.get("component_diagnostics", {})
        financial = diagnostics.get("financial", {})
        final_verified = state.get(
            "supervised_verified_risks", state.get("verified_risks", [])
        )
        prediction = state.get("prediction")
        prediction_metadata = prediction.metadata if prediction is not None else {}
        metadata = {
            "component_modes": self._component_modes(),
            "ipo_profile": (
                state["profile"].model_dump(mode="json")
                if state.get("profile") is not None
                else {}
            ),
            "document": state.get("document_metadata", {}),
            "real_slice": {
                "cash_runway_attempted": self.settings.financial_agent == "cash_runway",
                "cash_runway_built": financial.get("status") == "built",
                "cash_runway_verified": any(
                    risk.risk_code == "cash_runway"
                    for risk in final_verified
                ),
                "degraded_mode": prediction_metadata.get("degraded_mode", False),
                "degradation_reasons": prediction_metadata.get("degradation_reasons", []),
            },
            "configuration": {
                "workflow_version": self.settings.workflow_version,
                "use_mock": self.settings.use_mock,
                "config_name": (
                    "mock"
                    if self.settings.use_mock
                    else (
                        "v03_ai"
                        if self.settings.runtime_mode == "ai_enhanced"
                        else "v03_offline"
                        if self.settings.workflow_version == "enhanced_v2"
                        else "real_pdf"
                    )
                ),
                "runtime_mode": self.settings.runtime_mode,
            },
            "component_diagnostics": diagnostics,
        }
        if self.settings.workflow_version == "enhanced_v2":
            metadata["supervision"] = diagnostics.get("supervisor", {})
            metadata["governance"] = {
                "financial_second_review": "deferred_owner_waiver",
                "business_second_review": "deferred_owner_waiver",
                "legal_review": "completed",
                "formal_reviewed_golden_metrics": False,
            }
        return metadata
    def _failure(self, request, exc):
        error = AnalysisError(stage="service", component="IPOAnalysisService", code="unrecoverable_workflow_failure", message=str(exc), recoverable=False)
        return IPOAnalysisResult(request_id=request.request_id, company_name=request.company_name, stock_code=request.stock_code, workflow_version=request.workflow_version, status=TaskStatus.FAILED, errors=[error], agent_logs=[AgentLog(task_id=request.request_id, step=1, agent_name="service", action="execute_workflow", status=LogStatus.FAILED, error=error, finished_at=datetime.now(timezone.utc))], finished_at=datetime.now(timezone.utc))
    def analyze(self, request: IPOAnalysisRequest) -> IPOAnalysisResult:
        try:
            state = self.workflow.invoke({"request": request, "candidates": [], "verified_risks": [], "pending_risks": [], "rejected_risks": [], "agent_logs": [], "errors": []})
            result = IPOAnalysisResult(request_id=request.request_id, company_name=request.company_name, stock_code=request.stock_code, workflow_version=self.settings.workflow_version, verified_risks=state.get("supervised_verified_risks", state.get("verified_risks", [])), pending_risks=state.get("pending_risks", []), rejected_risks=state.get("rejected_risks", []), prediction=state.get("prediction"), agent_logs=state.get("agent_logs", []), report_sections=state.get("report_sections", []), errors=state.get("errors", []), status=TaskStatus.PARTIAL if state.get("errors") else TaskStatus.COMPLETED, finished_at=datetime.now(timezone.utc), metadata=self._result_metadata(state))
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
