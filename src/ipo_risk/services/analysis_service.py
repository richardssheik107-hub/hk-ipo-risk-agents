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
    def _failure(self, request, exc):
        error = AnalysisError(stage="service", component="IPOAnalysisService", code="unrecoverable_workflow_failure", message=str(exc), recoverable=False)
        return IPOAnalysisResult(request_id=request.request_id, company_name=request.company_name, stock_code=request.stock_code, workflow_version=request.workflow_version, status=TaskStatus.FAILED, errors=[error], agent_logs=[AgentLog(task_id=request.request_id, step=1, agent_name="service", action="execute_workflow", status=LogStatus.FAILED, error=error, finished_at=datetime.now(timezone.utc))], finished_at=datetime.now(timezone.utc))
    def analyze(self, request: IPOAnalysisRequest) -> IPOAnalysisResult:
        try:
            state = self.workflow.invoke({"request": request, "candidates": [], "verified_risks": [], "pending_risks": [], "rejected_risks": [], "agent_logs": [], "errors": []})
            result = IPOAnalysisResult(request_id=request.request_id, company_name=request.company_name, stock_code=request.stock_code, workflow_version=request.workflow_version, verified_risks=state.get("verified_risks", []), pending_risks=state.get("pending_risks", []), rejected_risks=state.get("rejected_risks", []), prediction=state.get("prediction"), agent_logs=state.get("agent_logs", []), report_sections=state.get("report_sections", []), errors=state.get("errors", []), status=TaskStatus.PARTIAL if state.get("errors") else TaskStatus.COMPLETED, finished_at=datetime.now(timezone.utc))
        except Exception as exc: result = self._failure(request, exc)
        try: self.repository.save(result)
        except Exception as exc:
            error = AnalysisError(stage="repository", component="analysis_repository", code="save_failure", message=str(exc))
            log = AgentLog(task_id=request.request_id, step=len(result.agent_logs) + 1, agent_name="analysis_repository", action="save", status=LogStatus.FAILED, error=error, finished_at=datetime.now(timezone.utc))
            result = result.model_copy(update={"status": TaskStatus.PARTIAL, "errors": [*result.errors, error], "agent_logs": [*result.agent_logs, log]})
        return result
