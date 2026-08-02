from datetime import datetime, timezone
from langgraph.graph import END, START, StateGraph
from ipo_risk.schemas import AgentLog, AnalysisError, DocumentParseRequest, IPOProfile, LogStatus, ReportContext, TaskStatus, VerificationStatus
from ipo_risk.workflows.state import WorkflowState

class MVPWorkflow:
    def __init__(self, parser, retriever, agents, verifier, supervisor, predictor, reporter, market_provider, ipo_provider):
        self.parser, self.retriever, self.agents, self.verifier = parser, retriever, agents, verifier
        self.supervisor, self.predictor, self.reporter = supervisor, predictor, reporter
        self.market_provider, self.ipo_provider = market_provider, ipo_provider
        graph = StateGraph(WorkflowState)
        nodes = [("load_ipo_profile", self.load_profile), ("load_market_snapshot", self.load_market), ("document", self.document), *[(agent.name, self.agent_node(agent)) for agent in agents], ("verifier", self.verify), ("supervisor", self.supervise), ("predictor", self.predict), ("report", self.report)]
        for name, node in nodes: graph.add_node(name, node)
        graph.add_edge(START, "load_ipo_profile"); previous = "load_ipo_profile"
        for name, _ in nodes[1:]: graph.add_edge(previous, name); previous = name
        graph.add_edge(previous, END); self.graph = graph.compile()
    def _log(self, state, name, action, status=LogStatus.SUCCESS, text="", error=None):
        return AgentLog(task_id=state["request"].request_id, step=len(state.get("agent_logs", [])) + 1, agent_name=name, action=action, status=status, output_summary=text, error=error, finished_at=datetime.now(timezone.utc))
    def _error(self, component, exc): return AnalysisError(stage=component, component=component, code="component_failure", message=str(exc))
    def _safe(self, state, component, action, operation, fallback):
        try:
            outcome = operation()
            return {**outcome, "agent_logs": [self._log(state, component, action, text=outcome.get("_summary", ""))]}
        except Exception as exc:
            error = self._error(component, exc)
            return {**fallback, "errors": [error], "agent_logs": [self._log(state, component, action, LogStatus.FAILED, str(exc), error)]}
    def load_profile(self, state):
        request = state["request"]
        return self._safe(state, "ipo_data_provider", "load_ipo_profile", lambda: {"profile": self.ipo_provider.get_profile(request.company_name, request.stock_code).model_copy(update={"listing_date": request.listing_date}), "_summary": "IPO profile loaded"}, {"profile": IPOProfile(company_name=request.company_name, stock_code=request.stock_code, listing_date=request.listing_date)})
    def load_market(self, state):
        return self._safe(state, "market_data_provider", "load_market_snapshot", lambda: {"market": state["request"].market_snapshot or self.market_provider.get_snapshot(state["profile"]), "_summary": "market snapshot loaded"}, {"market": None})
    def document(self, state):
        return self._safe(state, "document_parser", "parse", lambda: {"chunks": self.parser.parse(DocumentParseRequest(document_id=state["request"].request_id, prospectus_path=state["request"].prospectus_path)), "_summary": "document parsed"}, {"chunks": []})
    def agent_node(self, agent):
        return lambda state: self._safe(state, agent.name, "analyze", lambda: {"candidates": agent.analyze(state["profile"], state.get("chunks", []), state.get("market")), "_summary": "agent completed"}, {"candidates": []})
    def _pending(self, risks):
        return [risk.model_copy(update={"evidence": [], "verification_status": VerificationStatus.PENDING, "verification_notes": "Verification unavailable; human review required."}) for risk in risks]
    def verify(self, state):
        risks = state.get("candidates", [])
        try:
            evidence = {risk.risk_code: ([] if risk.risk_code == "precommercial_product" else self.retriever.retrieve(state.get("chunks", []), risk.risk_type)) for risk in risks}
        except Exception as exc:
            error = self._error("document_retriever", exc)
            return {"pending_risks": self._pending(risks), "errors": [error], "agent_logs": [self._log(state, "document_retriever", "retrieve", LogStatus.FAILED, str(exc), error)]}
        def operation():
            result = self.verifier.verify(risks, evidence)
            return {"verified_risks": result.verified_risks, "pending_risks": result.pending_risks, "rejected_risks": result.rejected_risks}
        return self._safe(state, "verifier", "verify", operation, {"pending_risks": self._pending(risks), "verified_risks": [], "rejected_risks": []})
    def supervise(self, state):
        return self._safe(state, "supervisor", "supervise", lambda: {"verified_risks": self.supervisor.supervise(state.get("verified_risks", [])).verified_risks}, {"verified_risks": []})
    def predict(self, state):
        return self._safe(state, "predictor", "predict", lambda: {"prediction": self.predictor.predict(state.get("verified_risks", []) + state.get("pending_risks", []), state.get("market"))}, {"prediction": None})
    def report(self, state):
        context = ReportContext(analysis_id=state["request"].request_id, profile=state["profile"], verified_risks=state.get("verified_risks", []), pending_risks=state.get("pending_risks", []), rejected_risks=state.get("rejected_risks", []), prediction=state.get("prediction"), log_summary=f"{len(state.get('agent_logs', []))} workflow events")
        return self._safe(state, "report_generator", "generate", lambda: {"report_sections": self.reporter.generate(context)}, {"report_sections": []})
    def invoke(self, state): return self.graph.invoke(state)
