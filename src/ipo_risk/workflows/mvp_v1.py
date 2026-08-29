"""LangGraph workflow for both mock and v0.2 real-document modes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langgraph.graph import END, START, StateGraph

from ipo_risk.schemas import (
    AgentLog,
    AnalysisError,
    DocumentParseRequest,
    IPOProfile,
    LogStatus,
    ReportContext,
    VerificationStatus,
)
from ipo_risk.schemas.final_supervision import FinalSupervisionInput
from ipo_risk.workflows.state import WorkflowState


class MVPWorkflow:
    def __init__(
        self,
        parser,
        retriever,
        agents,
        verifier,
        supervisor,
        predictor,
        reporter,
        market_provider,
        ipo_provider,
        *,
        market_context=None,
        model_prediction_provider=None,
        final_supervisor=None,
    ):
        self.parser, self.retriever, self.agents, self.verifier = (
            parser,
            retriever,
            agents,
            verifier,
        )
        self.supervisor, self.predictor, self.reporter = supervisor, predictor, reporter
        self.market_provider, self.ipo_provider = market_provider, ipo_provider
        self.market_context = market_context
        self.model_prediction_provider = model_prediction_provider
        self.final_supervisor = final_supervisor
        graph = StateGraph(WorkflowState)
        nodes = [
            ("load_ipo_profile", self.load_profile),
            ("load_market_snapshot", self.load_market),
            # Explains the snapshot just loaded; isolated by _safe and logged in
            # its own right, so an explanation failure never breaks the analysis.
            *([("market_context", self.explain_market)] if self.market_context else []),
            ("document", self.document),
            *[(agent.name, self.agent_node(agent)) for agent in agents],
            ("verifier", self.verify),
            ("supervisor", self.supervise),
            ("predictor", self.predict),
            *([("model_prediction", self.load_model_prediction)] if self.model_prediction_provider else []),
            # Must follow the predictor: the rule prediction is one of its inputs.
            *([("final_supervisor", self.finalize)] if self.final_supervisor else []),
            ("report", self.report),
        ]
        for name, node in nodes:
            graph.add_node(name, node)
        graph.add_edge(START, "load_ipo_profile")
        previous = "load_ipo_profile"
        for name, _ in nodes[1:]:
            graph.add_edge(previous, name)
            previous = name
        graph.add_edge(previous, END)
        self.graph = graph.compile()

    def _log(
        self,
        state,
        name,
        action,
        status=LogStatus.SUCCESS,
        text="",
        error=None,
        metadata: dict[str, Any] | None = None,
    ):
        return AgentLog(
            task_id=state["request"].request_id,
            step=len(state.get("agent_logs", [])) + 1,
            agent_name=name,
            action=action,
            status=status,
            output_summary=text,
            error=error,
            metadata=metadata or {},
            finished_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _safe_error(error: AnalysisError) -> AnalysisError:
        context = {
            key: value
            for key, value in error.context.items()
            if key not in {"path", "prospectus_path"}
        }
        return error.model_copy(update={"context": context})

    def _error(self, component, exc):
        embedded = getattr(exc, "error", None)
        if isinstance(embedded, AnalysisError):
            return self._safe_error(embedded)
        return AnalysisError(
            stage=component,
            component=component,
            code="component_failure",
            message=str(exc),
        )

    def _safe(self, state, component, action, operation, fallback):
        try:
            outcome = operation()
            summary = outcome.pop("_summary", "")
            metadata = outcome.pop("_log_metadata", {})
            return {
                **outcome,
                "agent_logs": [
                    self._log(state, component, action, text=summary, metadata=metadata)
                ],
            }
        except Exception as exc:
            error = self._error(component, exc)
            return {
                **fallback,
                "errors": [error],
                "agent_logs": [
                    self._log(
                        state,
                        component,
                        action,
                        LogStatus.FAILED,
                        str(exc),
                        error,
                    )
                ],
            }

    def load_profile(self, state):
        request = state["request"]

        def operation():
            profile = self.ipo_provider.get_profile(
                request.company_name, request.stock_code
            ).model_copy(update={"listing_date": request.listing_date})
            return {
                "profile": profile,
                "_summary": "IPO profile loaded",
                "_log_metadata": {"source": profile.metadata.get("source", "mock")},
            }

        return self._safe(
            state,
            "ipo_data_provider",
            "load_ipo_profile",
            operation,
            {
                "profile": IPOProfile(
                    company_name=request.company_name,
                    stock_code=request.stock_code,
                    listing_date=request.listing_date,
                )
            },
        )

    def load_market(self, state):
        def operation():
            market = state["request"].market_snapshot or self.market_provider.get_snapshot(
                state["profile"]
            )
            return {
                "market": market,
                "_summary": "market snapshot loaded",
                "_log_metadata": {
                    "source": market.source,
                    "available": market.metadata.get(
                        "available", market.sentiment_score is not None
                    ),
                    "reason": market.metadata.get("reason"),
                },
            }

        return self._safe(
            state,
            "market_data_provider",
            "load_market_snapshot",
            operation,
            {"market": None},
        )

    def document(self, state):
        def operation():
            chunks = self.parser.parse(
                DocumentParseRequest(
                    document_id=state["request"].request_id,
                    prospectus_path=state["request"].prospectus_path,
                )
            )
            parser_errors = [
                self._safe_error(error)
                for error in getattr(self.parser, "last_errors", [])
            ]
            serialized_errors = [
                error.model_dump(mode="json") for error in parser_errors
            ]
            metadata = {
                "parser_name": getattr(self.parser, "name", type(self.parser).__name__),
                "parsed_chunk_count": len(chunks),
                "parser_error_count": len(parser_errors),
                "parser_errors": serialized_errors,
            }
            cache_metrics = getattr(self.parser, "last_cache_metrics", None)
            if isinstance(cache_metrics, dict) and cache_metrics:
                metadata["cache_metrics"] = cache_metrics
            return {
                "chunks": chunks,
                "document_metadata": metadata,
                "errors": parser_errors,
                "_summary": f"document parsed into {len(chunks)} chunks",
                "_log_metadata": metadata,
            }

        return self._safe(
            state,
            "document_parser",
            "parse",
            operation,
            {
                "chunks": [],
                "document_metadata": {
                    "parser_name": getattr(
                        self.parser, "name", type(self.parser).__name__
                    ),
                    "parsed_chunk_count": 0,
                    "parser_error_count": 1,
                    "parser_errors": [],
                },
            },
        )

    @staticmethod
    def _diagnostics(agent) -> dict[str, Any]:
        diagnostics = getattr(agent, "last_diagnostics", None)
        if diagnostics is None:
            return {}
        if hasattr(diagnostics, "model_dump"):
            return diagnostics.model_dump(mode="json")
        return dict(diagnostics) if isinstance(diagnostics, dict) else {"value": str(diagnostics)}

    def _document_with_retrieval_cache(self, state) -> dict[str, Any]:
        document = dict(state.get("document_metadata") or {})
        observed = getattr(self.retriever, "last_cache_metrics", None)
        if not isinstance(observed, dict) or not observed:
            return document
        combined = dict(document.get("cache_metrics") or {})
        for key in ("retrieval_cache_hits", "retrieval_cache_misses"):
            combined[key] = int(observed.get(key) or 0)
        timings = dict(combined.get("stage_wall_clock_ms") or {})
        timings.update(observed.get("stage_wall_clock_ms") or {})
        combined["stage_wall_clock_ms"] = timings
        for key in ("retrieval_fingerprint", "retrieval_input_hash"):
            if observed.get(key):
                combined[key] = observed[key]
        document["cache_metrics"] = combined
        return document

    def agent_node(self, agent):
        def node(state):
            try:
                candidates = agent.analyze(
                    state["profile"], state.get("chunks", []), state.get("market")
                )
                diagnostics = self._diagnostics(agent)
                return {
                    "candidates": candidates,
                    "document_metadata": self._document_with_retrieval_cache(state),
                    "component_diagnostics": {agent.name: diagnostics},
                    "agent_logs": [
                        self._log(
                            state,
                            agent.name,
                            "analyze",
                            text=f"agent completed with {len(candidates)} risk(s)",
                            metadata=diagnostics,
                        )
                    ],
                }
            except Exception as exc:
                error = self._error(agent.name, exc)
                diagnostics = self._diagnostics(agent)
                return {
                    "candidates": [],
                    "component_diagnostics": {agent.name: diagnostics},
                    "errors": [error],
                    "agent_logs": [
                        self._log(
                            state,
                            agent.name,
                            "analyze",
                            LogStatus.FAILED,
                            str(exc),
                            error,
                            diagnostics,
                        )
                    ],
                }

        return node

    @staticmethod
    def _pending(risks):
        return [
            risk.model_copy(
                update={
                    "verification_status": VerificationStatus.PENDING,
                    "verification_notes": (
                        "Verification unavailable; original Evidence and Calculation "
                        "were preserved for human review."
                    ),
                }
            )
            for risk in risks
        ]

    def verify(self, state):
        risks = state.get("candidates", [])
        evidence: dict[str, list] = {}
        retrieval_errors: list[AnalysisError] = []
        retrieval_logs: list[AgentLog] = []
        retrieval_failed_risk_ids: set[str] = set()
        for risk in risks:
            if risk.risk_code in {"cash_runway", "precommercial_product"}:
                evidence[risk.risk_code] = []
                continue
            try:
                evidence[risk.risk_code] = self.retriever.retrieve(
                    state.get("chunks", []), risk.risk_type
                )
            except Exception as exc:
                error = self._error("document_retriever", exc).model_copy(
                    update={
                        "context": {
                            "risk_id": risk.risk_id,
                            "risk_code": risk.risk_code,
                        }
                    }
                )
                retrieval_errors.append(error)
                retrieval_failed_risk_ids.add(risk.risk_id)
                retrieval_logs.append(
                    self._log(
                        state,
                        "document_retriever",
                        "retrieve",
                        LogStatus.FAILED,
                        str(exc),
                        error,
                        {"risk_id": risk.risk_id, "risk_code": risk.risk_code},
                    )
                )
                evidence[risk.risk_code] = []

        try:
            result = self.verifier.verify(risks, evidence)
            verified = [
                risk
                for risk in result.verified_risks
                if risk.risk_id not in retrieval_failed_risk_ids
            ]
            rejected = [
                risk
                for risk in result.rejected_risks
                if risk.risk_id not in retrieval_failed_risk_ids
            ]
            pending = [
                risk
                for risk in result.pending_risks
                if risk.risk_id not in retrieval_failed_risk_ids
            ]
            pending.extend(
                risk.model_copy(
                    update={
                        "verification_status": VerificationStatus.PENDING,
                        "verification_notes": (
                            "Evidence retrieval failed for this risk; original Evidence and "
                            "Calculation were preserved for human review."
                        ),
                    }
                )
                for risk in risks
                if risk.risk_id in retrieval_failed_risk_ids
            )
            return {
                "verified_risks": verified,
                "pending_risks": pending,
                "rejected_risks": rejected,
                "errors": retrieval_errors,
                "agent_logs": [
                    *retrieval_logs,
                    self._log(
                        state,
                        "verifier",
                        "verify",
                        text=f"verified {len(verified)} risk(s)",
                    ),
                ],
            }
        except Exception as exc:
            error = self._error("verifier", exc)
            return {
                "pending_risks": self._pending(risks),
                "verified_risks": [],
                "rejected_risks": [],
                "errors": [*retrieval_errors, error],
                "agent_logs": [
                    *retrieval_logs,
                    self._log(
                        state,
                        "verifier",
                        "verify",
                        LogStatus.FAILED,
                        str(exc),
                        error,
                    ),
                ],
            }

    def supervise(self, state):
        return self._safe(
            state,
            "supervisor",
            "supervise",
            lambda: {
                "verified_risks": self.supervisor.supervise(
                    state.get("verified_risks", [])
                ).verified_risks
            },
            {"verified_risks": state.get("verified_risks", [])},
        )

    def predict(self, state):
        return self._safe(
            state,
            "predictor",
            "predict",
            lambda: {
                "prediction": self.predictor.predict(
                    state.get("verified_risks", [])
                    + state.get("pending_risks", []),
                    state.get("market"),
                )
            },
            {"prediction": None},
        )

    def explain_market(self, state):
        """Turn the loaded snapshot into an explanation, or into a named absence."""
        def operation():
            view = self.market_context.context(state["profile"], state.get("market"))
            return {
                "market_context_view": view,
                "component_diagnostics": {"market_context": view.model_dump(mode="json")},
                "_summary": f"market context {view.status.value}",
                "_log_metadata": {"status": view.status.value, "observation_count": len(view.observations)},
            }
        return self._safe(state, "market_context", "context", operation, {"market_context_view": None})

    def finalize(self, state):
        """Compose the document, market, model and rule channels."""
        def operation():
            inputs = FinalSupervisionInput(
                document_supervision=state.get("supervision_result"),
                market_context=state.get("market_context_view"),
                model_prediction=state.get("model_prediction_view"),
                rule_prediction=state.get("prediction"),
            )
            result = self.final_supervisor.finalize(inputs)
            return {
                "final_supervision": result,
                "component_diagnostics": {"final_supervisor": result.model_dump(mode="json")},
                "_summary": "final supervision composed",
                "_log_metadata": {
                    "channel_states": {
                        state_.channel.value: state_.status.value for state_ in result.channel_states
                    },
                    "unresolved_conflict_count": result.metadata.get("unresolved_conflict_count", 0),
                },
            }
        return self._safe(state, "final_supervisor", "finalize", operation, {"final_supervision": None})

    def load_model_prediction(self, state):
        """Load a frozen per-case model projection; never score or train here."""
        def operation():
            view = self.model_prediction_provider.prediction(state["profile"])
            return {
                "model_prediction_view": view,
                "component_diagnostics": {"model_prediction": view.model_dump(mode="json")},
                "_summary": f"model prediction {view.status.value}",
                "_log_metadata": {"status": view.status.value, "driver_count": len(view.drivers)},
            }

        return self._safe(
            state,
            "model_prediction",
            "load_frozen_projection",
            operation,
            {"model_prediction_view": None},
        )

    def report(self, state):
        context = ReportContext(
            analysis_id=state["request"].request_id,
            profile=state["profile"],
            verified_risks=state.get("verified_risks", []),
            pending_risks=state.get("pending_risks", []),
            rejected_risks=state.get("rejected_risks", []),
            prediction=state.get("prediction"),
            log_summary=f"{len(state.get('agent_logs', []))} workflow events",
        )
        return self._safe(
            state,
            "report_generator",
            "generate",
            lambda: {"report_sections": self.reporter.generate(context)},
            {"report_sections": []},
        )

    def invoke(self, state):
        return self.graph.invoke(state)
