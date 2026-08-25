"""Traceability is measured, not asserted.

The assembler must turn every workflow step into a typed trace event carrying an
actor, a tool and either Evidence or a stated reason for having none.  The report
must then count what actually resolves, so a real gap lowers the number instead
of being hidden by a hard-coded 100%.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from ipo_risk.agents.targeted_recheck import RecheckOutcome
from ipo_risk.runtime.competition_trace import (
    TRACE_SCHEMA_VERSION,
    CompetitionTraceAssembler,
    traceability_report,
)
from ipo_risk.schemas import AgentLog, Evidence, LogStatus, RiskCategory, RiskItem, RiskLevel
from ipo_risk.schemas.competition_runtime import (
    CompetitionConflict,
    CompetitionRuntimeIdentity,
    ConflictStatus,
    HumanReview,
    HumanReviewDecision,
    RecheckRequest,
    RecheckStatus,
    TraceEvent,
    TraceEventType,
)

BASE = datetime(2026, 8, 25, 9, 0, tzinfo=timezone.utc)


def _identity() -> CompetitionRuntimeIdentity:
    return CompetitionRuntimeIdentity(
        case_id="ipo_2024_02410", stock_code="2410.HK", listing_date=date(2024, 8, 20), run_id="run-1"
    )


def _log(step: int, name: str, action: str, **kwargs) -> AgentLog:
    return AgentLog(
        task_id="run-1", step=step, agent_name=name, action=action,
        status=LogStatus.SUCCESS, started_at=BASE + timedelta(seconds=step), **kwargs
    )


def _risk() -> RiskItem:
    return RiskItem(
        risk_id="r1", risk_code="cash_runway", category=RiskCategory.FINANCIAL, risk_type="cash_runway",
        level=RiskLevel.CRITICAL, score=90, conclusion="short runway", agent_name="financial",
        evidence=[Evidence(evidence_id="e1", text="cash", page=5)],
    )


def _assemble(**kwargs):
    return CompetitionTraceAssembler().assemble(identity=_identity(), **kwargs)


def test_each_workflow_log_becomes_one_typed_trace_event() -> None:
    sidecar = _assemble(
        agent_logs=[_log(1, "document_parser", "parse"), _log(2, "financial", "analyze")]
    )
    types = [event.event_type for event in sidecar.trace_events]
    assert types == [TraceEventType.PARSER, TraceEventType.AGENT]
    assert all(event.run_id == "run-1" and event.case_id == "ipo_2024_02410" for event in sidecar.trace_events)


def test_an_agent_step_inherits_the_evidence_of_the_risks_it_produced() -> None:
    sidecar = _assemble(agent_logs=[_log(1, "financial", "analyze")], risks=[_risk()])
    assert sidecar.trace_events[0].evidence_ids == ["e1"]


def test_an_agent_with_no_risk_still_reports_the_evidence_its_diagnostics_held() -> None:
    sidecar = _assemble(
        agent_logs=[_log(1, "legal", "analyze")],
        diagnostic_evidence_by_agent={"legal": ["e_diag"]},
    )
    assert sidecar.trace_events[0].evidence_ids == ["e_diag"]


def test_a_step_with_no_evidence_states_why_instead_of_leaving_a_gap() -> None:
    sidecar = _assemble(agent_logs=[_log(1, "ipo_data_provider", "load_ipo_profile")])
    assert sidecar.trace_events[0].details["no_evidence_reason"]


def test_events_are_ordered_chronologically_and_stably() -> None:
    sidecar = _assemble(agent_logs=[_log(3, "verifier", "verify"), _log(1, "document_parser", "parse")])
    assert [event.details["step"] for event in sidecar.trace_events] == [1, 3]


def test_the_c_lane_market_trace_is_re_emitted_verbatim() -> None:
    event = TraceEvent(
        case_id="ipo_2024_02410", run_id="run-1", event_type=TraceEventType.SKILL,
        status="completed", agent_name="market_intelligence", action="deterministic_market_classification",
        tool_or_skill="IPOHeatSkill", details={"structured_output": {"ipo_heat": "hot"}},
    )
    sidecar = _assemble(
        component_diagnostics={"market_intelligence": {"trace_events": [event.model_dump(mode="json")]}}
    )
    assert len(sidecar.trace_events) == 1
    assert sidecar.trace_events[0].tool_or_skill == "IPOHeatSkill"
    assert sidecar.trace_events[0].details["structured_output"] == {"ipo_heat": "hot"}


def _conflict() -> CompetitionConflict:
    return CompetitionConflict(
        conflict_id="conflict:run-1:agent_verifier_disagreement:financial:cash_runway",
        case_id="ipo_2024_02410", run_id="run-1", involved_agents=["financial", "verifier"],
        risk_ids=["r1"], summary="disagreement", evidence_ids=["e1"],
        status=ConflictStatus.PARTIALLY_RESOLVED, created_at=BASE,
    )


def _outcome() -> RecheckOutcome:
    request = RecheckRequest(
        recheck_id="recheck:conflict-1", conflict_id=_conflict().conflict_id, case_id="ipo_2024_02410",
        run_id="run-1", requested_by="final_supervisor", targets=["cash_runway"], reason="disagreement",
        status=RecheckStatus.COMPLETED,
    )
    return RecheckOutcome(
        request=request, conflict_id=request.conflict_id, status=ConflictStatus.PARTIALLY_RESOLVED,
        resolution_note="new evidence found", new_evidence_ids=("e2",),
        trace_events=(TraceEvent(
            event_id="trace:recheck:1", case_id="ipo_2024_02410", run_id="run-1",
            event_type=TraceEventType.RETRIEVER, status="completed", agent_name="targeted_recheck",
            action="targeted_re_retrieval", tool_or_skill="keyword", evidence_ids=["e2"],
            occurred_at=BASE + timedelta(seconds=10),
        ),),
    )


def test_conflicts_and_rechecks_reach_the_public_sidecar() -> None:
    sidecar = _assemble(conflicts=[_conflict()], recheck_outcomes=[_outcome()])
    assert [item.status for item in sidecar.conflicts] == [ConflictStatus.PARTIALLY_RESOLVED]
    assert [item.recheck_id for item in sidecar.rechecks] == ["recheck:conflict-1"]
    kinds = {event.event_type for event in sidecar.trace_events}
    assert {TraceEventType.CONFLICT, TraceEventType.RETRIEVER} <= kinds


def test_a_human_review_becomes_its_own_trace_event() -> None:
    review = HumanReview(
        case_id="ipo_2024_02410", run_id="run-1", target_id="r1", original_machine_status="verified",
        decision=HumanReviewDecision.NEEDS_FOLLOW_UP, post_review_status="human_follow_up_required",
        reviewer_id="analyst_e", reviewer_note="check page 5", evidence_id="e1",
    )
    sidecar = _assemble(human_reviews=[review])
    event = sidecar.trace_events[0]
    assert event.event_type is TraceEventType.HUMAN_REVIEW
    assert event.agent_name == "reviewer:analyst_e"
    assert event.evidence_ids == ["e1"]


def test_a_complete_trace_measures_one_hundred_percent() -> None:
    sidecar = _assemble(
        agent_logs=[_log(1, "financial", "analyze"), _log(2, "verifier", "verify")],
        risks=[_risk()], conflicts=[_conflict()], recheck_outcomes=[_outcome()],
    )
    report = traceability_report(sidecar, [_risk()], ["e2"])
    assert report.schema_version == TRACE_SCHEMA_VERSION
    assert report.agent_traceability == 1.0
    assert report.tool_traceability == 1.0
    assert report.evidence_traceability == 1.0
    assert report.overall_traceability == 1.0
    assert report.unresolved_evidence_ids == ()


def test_an_unaccounted_step_lowers_the_measured_traceability() -> None:
    """A hand-built event with no actor and no reason must not read as traceable."""
    sidecar = _assemble(
        agent_logs=[_log(1, "financial", "analyze")],
        risks=[_risk()],
        extra_trace_events=[TraceEvent(
            event_id="trace:opaque", case_id="ipo_2024_02410", run_id="run-1",
            event_type=TraceEventType.AGENT, status="completed", tool_or_skill="",
            occurred_at=BASE + timedelta(seconds=20),
        )],
    )
    report = traceability_report(sidecar, [_risk()])
    assert report.event_count == 2
    assert report.agent_traceability == 0.5
    assert report.tool_traceability == 0.5
    assert report.evidence_traceability == 0.5
    assert report.overall_traceability == 0.5


def test_a_dangling_evidence_reference_is_reported_not_absorbed() -> None:
    sidecar = _assemble(
        agent_logs=[_log(1, "financial", "analyze", evidence_ids=["e_missing"])], risks=[_risk()]
    )
    report = traceability_report(sidecar, [_risk()])
    assert report.unresolved_evidence_ids == ("e_missing",)
    assert report.overall_traceability < 1.0


def test_a_namespaced_channel_reference_is_not_treated_as_a_document_evidence_id() -> None:
    """Market features carry their own namespace and resolve against their channel."""
    sidecar = _assemble(
        agent_logs=[_log(1, "market_intelligence", "interpret", evidence_ids=["market_feature:hsi_return_5d"])]
    )
    report = traceability_report(sidecar)
    assert report.referenced_evidence_count == 0
    assert report.overall_traceability == 1.0
