"""The competition workflow: composition, conflict, one re-check, then synthesis.

This is the E lane's integration point.  It keeps every upstream node exactly as
the frozen workflow defines it and replaces only the final supervision step with
the governed sequence the competition asks for:

```text
composed channels
-> deterministic conflict detection
-> one targeted re-check per conflict (bounded budget)
-> LLM Final Supervisor synthesis
-> Agent / Tool / Evidence trace sidecar
```

Every stage degrades on its own.  A failing detector, re-check or provider leaves
the deterministic PR-G composition intact and says so in the diagnostics; none of
them can erase a channel, invent a risk or upgrade an unavailable signal.
"""

from __future__ import annotations

from typing import Any

from ipo_risk.agents.conflict_detection import CONFLICT_POLICY_VERSION, ConflictDetector
from ipo_risk.agents.final_supervision_llm import LLMFinalSupervisor, SynthesisOutcome
from ipo_risk.agents.targeted_recheck import RECHECK_POLICY_VERSION, TargetedRecheckRunner
from ipo_risk.runtime.competition_trace import (
    CompetitionTraceAssembler,
    TRACE_SCHEMA_VERSION,
    traceability_report,
)
from ipo_risk.schemas import ComponentDiagnostic
from ipo_risk.schemas.competition_runtime import CompetitionRuntimeIdentity
from ipo_risk.schemas.final_supervision import FinalSupervisionInput
from ipo_risk.workflows.v04_ai import V04AIWorkflow


class V04CompetitionWorkflow(V04AIWorkflow):
    """v0.4 AI workflow plus conflict, targeted re-check and trace assembly."""

    name = "v04_competition"

    def __init__(self, *args, conflict_detector=None, recheck_runner=None, trace_assembler=None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.conflict_detector = conflict_detector or ConflictDetector()
        self.recheck_runner = recheck_runner or TargetedRecheckRunner(
            retriever=self.retriever, verifier=self.verifier
        )
        self.trace_assembler = trace_assembler or CompetitionTraceAssembler()
        # Node-local hand-off from ``finalize`` to ``report``.  It deliberately
        # does not enter WorkflowState: that contract is a protected interface and
        # the trace is observability, not workflow input.
        self.last_runtime: dict[str, Any] | None = None

    # ------------------------------------------------------------------ identity
    @staticmethod
    def _case_id(state) -> str:
        view = state.get("market_context_view")
        if view is not None and view.provenance.get("case_id"):
            return str(view.provenance["case_id"])
        profile = state.get("profile")
        if profile is not None:
            metadata = getattr(profile, "metadata", {}) or {}
            if metadata.get("case_id"):
                return str(metadata["case_id"])
            if profile.stock_code:
                return str(profile.stock_code)
        return str(state["request"].stock_code or "unknown_case")

    def _identity(self, state) -> CompetitionRuntimeIdentity:
        profile = state.get("profile")
        view = state.get("market_context_view")
        model_view = state.get("model_prediction_view")
        return CompetitionRuntimeIdentity(
            case_id=self._case_id(state),
            stock_code=getattr(profile, "stock_code", "") or state["request"].stock_code,
            listing_date=getattr(profile, "listing_date", None),
            run_id=state["request"].request_id,
            provider_name=getattr(getattr(self, "llm_provider", None), "name", None)
            or self._provider_name(),
            model_name=getattr(model_view, "model_name", None),
            prompt_version=getattr(self.final_supervisor, "prompt_version", None),
            provenance={
                "workflow": self.name,
                "trace_schema_version": TRACE_SCHEMA_VERSION,
                "conflict_policy_version": CONFLICT_POLICY_VERSION,
                "recheck_policy_version": RECHECK_POLICY_VERSION,
                "market_feature_manifest_hash": getattr(view, "feature_manifest_hash", None),
                "trace_scope": "parse_through_final_supervision",
            },
        )

    def _provider_name(self) -> str | None:
        provider = getattr(self.final_supervisor, "llm_provider", None)
        return getattr(provider, "name", None)

    def _agent_diagnostics(self) -> list[tuple[str, ComponentDiagnostic]]:
        """Typed per-agent diagnostics from this run.

        The workflow's generic diagnostic serialiser stringifies a list, which is
        lossy.  The agent objects still hold the structured records from their own
        node in this same invocation, so the conflict detector reads those instead
        of parsing a repr.
        """

        collected: list[tuple[str, ComponentDiagnostic]] = []
        for agent in self.agents:
            diagnostics = getattr(agent, "last_diagnostics", None)
            if not isinstance(diagnostics, (list, tuple)):
                continue
            for diagnostic in diagnostics:
                if isinstance(diagnostic, ComponentDiagnostic):
                    collected.append((agent.name, diagnostic))
        return collected

    @staticmethod
    def _diagnostic_evidence_by_agent(
        agent_diagnostics: list[tuple[str, ComponentDiagnostic]]
    ) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {}
        for agent_name, diagnostic in agent_diagnostics:
            bucket = grouped.setdefault(agent_name, [])
            for evidence_id in diagnostic.evidence_ids:
                if evidence_id not in bucket:
                    bucket.append(evidence_id)
        return grouped

    # ------------------------------------------------------------------ finalize
    def finalize(self, state):
        """Detect conflicts, run one bounded re-check, then synthesise."""

        self.last_runtime = None

        def operation() -> dict[str, Any]:
            identity = self._identity(state)
            supervision = state.get("supervision_result")
            unsettled = list(state.get("pending_risks", []))
            verified = list(supervision.verified_risks) if supervision else []

            agent_diagnostics = self._agent_diagnostics()
            conflicts = self.conflict_detector.detect(
                case_id=identity.case_id,
                run_id=identity.run_id,
                document_supervision=supervision,
                unsettled_risks=unsettled,
                agent_diagnostics=agent_diagnostics,
                market_context=state.get("market_context_view"),
                model_prediction=state.get("model_prediction_view"),
                rule_prediction=state.get("prediction"),
            )
            conflicts, outcomes = self.recheck_runner.run(
                conflicts,
                case_id=identity.case_id,
                run_id=identity.run_id,
                chunks=state.get("chunks", []),
                risks=[*verified, *unsettled],
            )

            inputs = FinalSupervisionInput(
                document_supervision=supervision,
                market_context=state.get("market_context_view"),
                model_prediction=state.get("model_prediction_view"),
                rule_prediction=state.get("prediction"),
            )
            supervise = getattr(self.final_supervisor, "supervise", None)
            if callable(supervise):
                bundle = supervise(
                    inputs,
                    case_id=identity.case_id,
                    run_id=identity.run_id,
                    conflicts=conflicts,
                    unsettled_risks=unsettled,
                    rejected_risks=state.get("rejected_risks", []),
                )
                result = bundle.result
                supervision_diagnostics = {
                    "status": bundle.status.value,
                    # Why the run ended where it did, kept apart from the status:
                    # the acceptance evidence has to distinguish an absent
                    # provider from a response the scope guard refused.
                    "outcome": bundle.outcome.value,
                    "reason": bundle.reason,
                    "fail_closed": bundle.outcome is SynthesisOutcome.REJECTED_OUT_OF_SCOPE,
                    "scope_check": bundle.scope_check,
                    "call": bundle.call,
                    "deterministic_severity_floor": bundle.deterministic_severity_floor,
                    "judgement": bundle.judgement.model_dump(mode="json") if bundle.judgement else None,
                    "agent_result": bundle.agent_result.model_dump(mode="json"),
                }
                extra_events = list(bundle.trace_events)
                agent_results = [bundle.agent_result]
            else:
                # A plain PR-G supervisor stays valid; only the synthesis is absent.
                result = self.final_supervisor.finalize(inputs)
                supervision_diagnostics = {
                    "status": "unavailable",
                    "outcome": SynthesisOutcome.SUPERVISOR_WITHOUT_SYNTHESIS.value,
                    "reason": "the configured Final Supervisor does not implement LLM synthesis",
                    "fail_closed": False,
                    "scope_check": {
                        "status": "not_applicable",
                        "reason": "this Final Supervisor performs no LLM synthesis to check",
                    },
                    "call": {},
                    "deterministic_severity_floor": None,
                    "judgement": None,
                }
                extra_events, agent_results = [], []

            recheck_payload = [
                {
                    "conflict_id": outcome.conflict_id,
                    "recheck_id": outcome.request.recheck_id,
                    "status": outcome.status.value,
                    "resolution_note": outcome.resolution_note,
                    "targets": list(outcome.request.targets),
                    "new_evidence_ids": list(outcome.new_evidence_ids),
                    "revised_risk_ids": list(outcome.revised_risk_ids),
                }
                for outcome in outcomes
            ]
            self.last_runtime = {
                "identity": identity,
                "conflicts": conflicts,
                "outcomes": outcomes,
                "extra_events": extra_events,
                "agent_results": agent_results,
                # Evidence the agents actually retrieved but could not turn into a
                # risk; it belongs to the run's Evidence universe for traceability.
                "diagnostic_evidence_ids": sorted(
                    {
                        evidence_id
                        for _, diagnostic in agent_diagnostics
                        for evidence_id in diagnostic.evidence_ids
                    }
                    | {
                        evidence_id
                        for outcome in outcomes
                        for evidence_id in outcome.new_evidence_ids
                    }
                ),
                "diagnostic_evidence_by_agent": self._diagnostic_evidence_by_agent(agent_diagnostics),
            }
            return {
                "final_supervision": result,
                "component_diagnostics": {
                    "final_supervisor": result.model_dump(mode="json"),
                    "final_supervision_llm": supervision_diagnostics,
                    "conflict_detection": {
                        "policy_version": CONFLICT_POLICY_VERSION,
                        "conflict_count": len(conflicts),
                        "conflicts": [conflict.model_dump(mode="json") for conflict in conflicts],
                    },
                    "targeted_recheck": {
                        "policy_version": RECHECK_POLICY_VERSION,
                        "attempted": len(outcomes),
                        "outcomes": recheck_payload,
                    },
                },
                "_summary": "final supervision composed with conflict and targeted re-check",
                "_log_metadata": {
                    "channel_states": {
                        item.channel.value: item.status.value for item in result.channel_states
                    },
                    "conflict_count": len(conflicts),
                    "recheck_attempted": len(outcomes),
                    "llm_synthesis_status": supervision_diagnostics["status"],
                },
            }

        return self._safe(
            state, "final_supervisor", "finalize", operation, {"final_supervision": None}
        )

    # -------------------------------------------------------------------- report
    def report(self, state):
        """Assemble the trace sidecar, then generate the report unchanged."""

        runtime = self.last_runtime
        trace_diagnostics: dict[str, Any]
        try:
            if runtime is None:
                identity = self._identity(state)
                conflicts, outcomes, extra_events, agent_results = (), (), (), ()
                diagnostic_evidence_ids: list[str] = []
                diagnostic_evidence_by_agent: dict[str, list[str]] = {}
            else:
                identity = runtime["identity"]
                conflicts = runtime["conflicts"]
                outcomes = runtime["outcomes"]
                extra_events = runtime["extra_events"]
                agent_results = runtime["agent_results"]
                diagnostic_evidence_ids = runtime["diagnostic_evidence_ids"]
                diagnostic_evidence_by_agent = runtime["diagnostic_evidence_by_agent"]
            risks = [
                *state.get("supervised_verified_risks", state.get("verified_risks", [])),
                *state.get("pending_risks", []),
                *state.get("rejected_risks", []),
            ]
            sidecar = self.trace_assembler.assemble(
                identity=identity,
                agent_logs=state.get("agent_logs", []),
                component_diagnostics=state.get("component_diagnostics", {}),
                risks=risks,
                conflicts=conflicts,
                recheck_outcomes=outcomes,
                extra_trace_events=extra_events,
                agent_results=agent_results,
                diagnostic_evidence_by_agent=diagnostic_evidence_by_agent,
            )
            report = traceability_report(sidecar, risks, diagnostic_evidence_ids)
            trace_diagnostics = {
                "status": "completed",
                "sidecar": sidecar.model_dump(mode="json"),
                "traceability": report.model_dump(mode="json"),
            }
        except Exception as exc:  # the trace is observability; it never blocks a run
            trace_diagnostics = {
                "status": "failed",
                "reason": f"{type(exc).__name__}: {exc}",
                "sidecar": None,
                "traceability": None,
            }
        generated = super().report(state)
        diagnostics = dict(generated.get("component_diagnostics", {}))
        diagnostics["competition_runtime"] = trace_diagnostics
        return {**generated, "component_diagnostics": diagnostics}
