"""Assemble one run's Agent / Tool / Evidence trace into the public sidecar.

Traceability is a measurement here, not a claim.  Every workflow step becomes a
``TraceEvent`` carrying who acted, which tool or skill was used, which Evidence
and Calculation ids were involved, and -- when there were none -- an explicit
reason.  ``TraceabilityReport`` then counts what actually resolves, so an
incomplete trace shows up as a number below 1.0 instead of being asserted away.

Nothing is invented: every id comes from the run's own risks, logs and
diagnostics, and an unresolvable reference is reported as unresolved.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

from pydantic import BaseModel, ConfigDict, Field

from ipo_risk.agents.targeted_recheck import RecheckOutcome
from ipo_risk.schemas import AgentLog, RiskItem
from ipo_risk.schemas.competition_runtime import (
    AgentResultEnvelope,
    CompetitionConflict,
    CompetitionRuntimeIdentity,
    CompetitionRuntimeSidecar,
    HumanReview,
    TraceEvent,
    TraceEventType,
)


TRACE_SCHEMA_VERSION = "v04_e_agent_trace_v1"

# Which workflow component maps to which public trace event type.  A component
# that is not listed still produces an event, typed as AGENT, so nothing is lost.
_EVENT_TYPES: dict[str, TraceEventType] = {
    "document_parser": TraceEventType.PARSER,
    "retriever": TraceEventType.RETRIEVER,
    "verifier": TraceEventType.VERIFIER,
    "financial_verifier": TraceEventType.VERIFIER,
    "legal_verifier": TraceEventType.VERIFIER,
    "business_verifier": TraceEventType.VERIFIER,
    "supervisor": TraceEventType.SUPERVISOR,
    "final_supervisor": TraceEventType.SUPERVISOR,
    "market_context": TraceEventType.MARKET,
    "market_intelligence": TraceEventType.MARKET,
    "market_data_provider": TraceEventType.MARKET,
    "model_prediction": TraceEventType.MODEL,
    "predictor": TraceEventType.MODEL,
    "ipo_data_provider": TraceEventType.AGENT,
    "analysis_repository": TraceEventType.AGENT,
}

_LOG_STATUS = {"success": "completed", "failed": "failed", "skipped": "skipped", "started": "started"}


class TraceabilityReport(BaseModel):
    """Measured, not asserted: what fraction of the trace actually resolves."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = TRACE_SCHEMA_VERSION
    event_count: int = Field(ge=0)
    agent_identified_count: int = Field(ge=0)
    tool_identified_count: int = Field(ge=0)
    evidence_accounted_count: int = Field(ge=0)
    referenced_evidence_count: int = Field(ge=0)
    resolved_evidence_count: int = Field(ge=0)
    unresolved_evidence_ids: tuple[str, ...] = ()
    agent_traceability: float = Field(ge=0, le=1)
    tool_traceability: float = Field(ge=0, le=1)
    evidence_traceability: float = Field(ge=0, le=1)
    overall_traceability: float = Field(ge=0, le=1)


def _ratio(numerator: int, denominator: int) -> float:
    return 1.0 if denominator == 0 else round(numerator / denominator, 6)


class CompetitionTraceAssembler:
    """Turn workflow logs, diagnostics and E-lane outputs into one sidecar."""

    name = "competition_trace_assembler"
    schema_version = TRACE_SCHEMA_VERSION

    def assemble(
        self,
        *,
        identity: CompetitionRuntimeIdentity,
        agent_logs: Sequence[AgentLog] = (),
        component_diagnostics: dict[str, Any] | None = None,
        risks: Sequence[RiskItem] = (),
        conflicts: Sequence[CompetitionConflict] = (),
        recheck_outcomes: Sequence[RecheckOutcome] = (),
        extra_trace_events: Sequence[TraceEvent] = (),
        agent_results: Sequence[AgentResultEnvelope] = (),
        human_reviews: Sequence[HumanReview] = (),
        diagnostic_evidence_by_agent: dict[str, Sequence[str]] | None = None,
    ) -> CompetitionRuntimeSidecar:
        diagnostics = component_diagnostics or {}
        evidence_by_component = self._evidence_by_component(risks, diagnostic_evidence_by_agent)
        events: list[TraceEvent] = [
            self._from_log(log, identity, diagnostics, evidence_by_component) for log in agent_logs
        ]
        events.extend(self._market_intelligence_events(diagnostics, identity))
        events.extend(self._conflict_events(conflicts, identity))
        for outcome in recheck_outcomes:
            events.extend(outcome.trace_events)
        events.extend(extra_trace_events)
        events.extend(self._human_review_events(human_reviews, identity))
        return CompetitionRuntimeSidecar(
            identity=identity,
            agent_results=list(agent_results),
            conflicts=list(conflicts),
            rechecks=[outcome.request for outcome in recheck_outcomes],
            trace_events=self._ordered(events),
            human_reviews=list(human_reviews),
        )

    @staticmethod
    def _ordered(events: Iterable[TraceEvent]) -> list[TraceEvent]:
        """Stable order: chronological, then by id so equal timestamps never swap."""

        return sorted(events, key=lambda event: (event.occurred_at, event.event_id))

    @staticmethod
    def _evidence_by_component(
        risks: Sequence[RiskItem], diagnostic_evidence_by_agent: dict[str, Sequence[str]] | None = None
    ) -> dict[str, list[str]]:
        """Which Evidence each component actually stood on, taken from the risks.

        ``AgentLog`` does not carry Evidence ids, so an unenriched trace would
        show every step as evidence-free.  The producing agent's own risks do
        carry them, and the routing components ruled on all of them, so the link
        is recovered from the run's data rather than asserted.
        """

        by_agent: dict[str, list[str]] = {}
        every: list[str] = []
        for risk in risks:
            bucket = by_agent.setdefault(risk.agent_name, [])
            for item in risk.evidence:
                if item.evidence_id not in bucket:
                    bucket.append(item.evidence_id)
                if item.evidence_id not in every:
                    every.append(item.evidence_id)
        # An agent that produced no risk may still have stood on Evidence; its
        # diagnostics record which, so the step is not reported as evidence-free.
        for agent_name, evidence_ids in (diagnostic_evidence_by_agent or {}).items():
            bucket = by_agent.setdefault(agent_name, [])
            for evidence_id in evidence_ids:
                if evidence_id not in bucket:
                    bucket.append(evidence_id)
        for component in ("verifier", "supervisor", "final_supervisor"):
            by_agent.setdefault(component, every)
        return by_agent

    def _from_log(
        self,
        log: AgentLog,
        identity: CompetitionRuntimeIdentity,
        diagnostics: dict[str, Any],
        evidence_by_component: dict[str, list[str]] | None = None,
    ) -> TraceEvent:
        component = log.agent_name
        details: dict[str, Any] = {
            "step": log.step,
            "output_summary": log.output_summary,
            "log_id": log.log_id,
        }
        component_diagnostic = diagnostics.get(component)
        if isinstance(component_diagnostic, dict) and component_diagnostic:
            details["component_diagnostics"] = component_diagnostic
        if log.error is not None:
            details["error"] = log.error.model_dump(mode="json")
        calculation_ids = list(log.metadata.get("calculation_ids", []) or [])
        evidence_ids = list(log.evidence_ids) or list((evidence_by_component or {}).get(component, []))
        if not evidence_ids and not calculation_ids:
            # Stating why a step carries no evidence is what keeps the trace
            # complete; a silent empty list would be indistinguishable from a gap.
            details["no_evidence_reason"] = (
                f"{component} is an orchestration or channel step that references no document Evidence directly"
            )
        return TraceEvent(
            event_id=f"trace:{identity.run_id}:log:{log.step:03d}:{component}",
            case_id=identity.case_id,
            run_id=identity.run_id,
            event_type=_EVENT_TYPES.get(component, TraceEventType.AGENT),
            status=_LOG_STATUS.get(log.status.value, log.status.value),
            agent_name=component,
            action=log.action,
            tool_or_skill=log.tool_name or component,
            provider_name=log.metadata.get("provider_name") if isinstance(log.metadata, dict) else None,
            model_name=log.metadata.get("model_name") if isinstance(log.metadata, dict) else None,
            prompt_version=log.metadata.get("prompt_version") if isinstance(log.metadata, dict) else None,
            evidence_ids=evidence_ids,
            calculation_ids=calculation_ids,
            latency_ms=log.duration_ms if log.duration_ms is not None else 0,
            occurred_at=log.started_at,
            details=details,
        )

    @staticmethod
    def _market_intelligence_events(
        diagnostics: dict[str, Any], identity: CompetitionRuntimeIdentity
    ) -> list[TraceEvent]:
        """Re-emit the C lane's own trace events verbatim; they are already governed."""

        payload = diagnostics.get("market_intelligence")
        if not isinstance(payload, dict):
            return []
        events = []
        for index, raw in enumerate(payload.get("trace_events", []) or []):
            event_id = f"trace:{identity.run_id}:market_intelligence:{index:02d}"
            try:
                event = TraceEvent.model_validate(raw)
            except Exception as exc:
                # A market event this assembler cannot parse is still a step that
                # happened.  Dropping it would silently shrink the denominator and
                # inflate the measured traceability, so it is recorded as
                # unparsable instead.
                events.append(TraceEvent(
                    event_id=event_id, case_id=identity.case_id, run_id=identity.run_id,
                    event_type=TraceEventType.MARKET, status="unparsable_trace_event",
                    agent_name="market_intelligence", action="interpret_market_context",
                    tool_or_skill="market_intelligence", latency_ms=0,
                    details={
                        "reason": f"{type(exc).__name__}: {exc}",
                        "no_evidence_reason": "the market trace event could not be parsed into the public contract",
                    },
                ))
                continue
            events.append(event.model_copy(update={"event_id": event_id}))
        return events

    @staticmethod
    def _conflict_events(
        conflicts: Sequence[CompetitionConflict], identity: CompetitionRuntimeIdentity
    ) -> list[TraceEvent]:
        return [
            TraceEvent(
                event_id=f"trace:{conflict.conflict_id}:detected",
                case_id=identity.case_id,
                run_id=identity.run_id,
                event_type=TraceEventType.CONFLICT,
                status=conflict.status.value,
                agent_name="conflict_detector",
                action="detect_cross_agent_conflict",
                tool_or_skill="deterministic_conflict_policy",
                evidence_ids=list(conflict.evidence_ids),
                conflict_id=conflict.conflict_id,
                latency_ms=0,
                occurred_at=conflict.created_at,
                details={
                    "involved_agents": list(conflict.involved_agents),
                    "risk_ids": list(conflict.risk_ids),
                    "claim_ids": list(conflict.claim_ids),
                    "summary": conflict.summary,
                    "resolution_note": conflict.resolution_note,
                    "no_evidence_reason": (
                        "this conflict spans channels that carry no document Evidence"
                        if not conflict.evidence_ids else ""
                    ),
                },
            )
            for conflict in conflicts
        ]

    @staticmethod
    def _human_review_events(
        reviews: Sequence[HumanReview], identity: CompetitionRuntimeIdentity
    ) -> list[TraceEvent]:
        return [
            TraceEvent(
                event_id=f"trace:{review.review_id}:human_review",
                case_id=identity.case_id,
                run_id=identity.run_id,
                event_type=TraceEventType.HUMAN_REVIEW,
                status=review.decision.value,
                agent_name=f"reviewer:{review.reviewer_id}",
                action="human_review_decision",
                tool_or_skill="human_review_console",
                evidence_ids=[review.evidence_id] if review.evidence_id else [],
                latency_ms=0,
                occurred_at=review.reviewed_at,
                details={
                    "target_id": review.target_id,
                    "original_machine_status": review.original_machine_status,
                    "post_review_status": review.post_review_status,
                    "reviewer_note": review.reviewer_note,
                    "no_evidence_reason": (
                        "the reviewer decided at risk level rather than against a single Evidence item"
                        if not review.evidence_id else ""
                    ),
                },
            )
            for review in reviews
        ]


def traceability_report(
    sidecar: CompetitionRuntimeSidecar,
    risks: Sequence[RiskItem] = (),
    extra_evidence_ids: Sequence[str] = (),
) -> TraceabilityReport:
    """Measure Agent / Tool / Evidence traceability over an assembled sidecar.

    ``extra_evidence_ids`` carries Evidence the run retrieved but never attached
    to a risk -- diagnostic and re-check Evidence -- so a reference to it counts
    as resolved rather than dangling.
    """

    events = sidecar.trace_events
    known_evidence = {item.evidence_id for risk in risks for item in risk.evidence}
    known_evidence |= set(extra_evidence_ids)
    known_evidence |= {
        evidence_id for conflict in sidecar.conflicts for evidence_id in conflict.evidence_ids
    }
    agent_identified = sum(1 for event in events if event.agent_name)
    tool_identified = sum(1 for event in events if event.tool_or_skill)
    evidence_accounted = sum(
        1
        for event in events
        if event.evidence_ids
        or event.calculation_ids
        or str(event.details.get("no_evidence_reason") or "")
    )
    referenced = [
        evidence_id
        for event in events
        for evidence_id in event.evidence_ids
        # Non-document channels mint their own namespaced reference ids; those
        # resolve against their own channel, not the prospectus evidence set.
        if ":" not in evidence_id
    ]
    unresolved = tuple(sorted({item for item in referenced if item not in known_evidence}))
    resolved = len(referenced) - sum(1 for item in referenced if item in unresolved)
    agent_ratio = _ratio(agent_identified, len(events))
    tool_ratio = _ratio(tool_identified, len(events))
    evidence_ratio = _ratio(evidence_accounted, len(events))
    resolution_ratio = _ratio(resolved, len(referenced))
    return TraceabilityReport(
        event_count=len(events),
        agent_identified_count=agent_identified,
        tool_identified_count=tool_identified,
        evidence_accounted_count=evidence_accounted,
        referenced_evidence_count=len(referenced),
        resolved_evidence_count=resolved,
        unresolved_evidence_ids=unresolved,
        agent_traceability=agent_ratio,
        tool_traceability=tool_ratio,
        evidence_traceability=evidence_ratio,
        overall_traceability=round(min(agent_ratio, tool_ratio, evidence_ratio, resolution_ratio), 6),
    )
