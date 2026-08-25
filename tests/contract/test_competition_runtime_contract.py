from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from ipo_risk.schemas.competition_runtime import (
    AgentResultEnvelope,
    CompetitionConflict,
    CompetitionRuntimeIdentity,
    CompetitionRuntimeSidecar,
    ConflictStatus,
    HumanReview,
    HumanReviewDecision,
    RecheckRequest,
    TraceEvent,
    TraceEventType,
)


def _identity() -> CompetitionRuntimeIdentity:
    return CompetitionRuntimeIdentity(
        case_id="2024-0001",
        stock_code="2410.HK",
        listing_date=date(2024, 8, 20),
        run_id="run-001",
        provider_name="openai_compatible",
        model_name="example-model",
        prompt_version="legal_v1",
    )


def test_competition_contracts_round_trip_without_business_specific_payloads():
    identity = _identity()
    agent = AgentResultEnvelope(
        case_id=identity.case_id,
        run_id=identity.run_id,
        agent_name="legal",
        status="completed",
        risk_ids=["risk-1"],
        evidence_ids=["ev-1"],
    )
    conflict = CompetitionConflict(
        case_id=identity.case_id,
        run_id=identity.run_id,
        involved_agents=["financial", "business"],
        risk_ids=["risk-1", "risk-2"],
        summary="Cash pressure conflicts with a stated financing mitigant.",
        evidence_ids=["ev-1", "ev-2"],
        status=ConflictStatus.DETECTED,
    )
    recheck = RecheckRequest(
        conflict_id=conflict.conflict_id,
        case_id=identity.case_id,
        run_id=identity.run_id,
        requested_by="final_supervisor",
        targets=["cash_runway", "use_of_proceeds"],
        reason="Verify whether the mitigant changes the liquidity conclusion.",
    )
    trace = TraceEvent(
        case_id=identity.case_id,
        run_id=identity.run_id,
        event_type=TraceEventType.LLM,
        status="success",
        agent_name="legal",
        provider_name="openai_compatible",
        model_name="example-model",
        prompt_version="legal_v1",
        evidence_ids=["ev-1"],
        latency_ms=12,
        request_id="req-1",
        raw_response_hash="abc123",
    )
    review = HumanReview(
        case_id=identity.case_id,
        run_id=identity.run_id,
        target_id="risk-1",
        original_machine_status="verified",
        decision=HumanReviewDecision.NEEDS_FOLLOW_UP,
        post_review_status="needs_follow_up",
        reviewer_id="reviewer-1",
        evidence_id="ev-1",
        page=10,
    )

    sidecar = CompetitionRuntimeSidecar(
        identity=identity,
        agent_results=[agent],
        conflicts=[conflict],
        rechecks=[recheck],
        trace_events=[trace],
        human_reviews=[review],
    )
    restored = CompetitionRuntimeSidecar.model_validate_json(sidecar.model_dump_json())
    assert restored == sidecar


def test_conflict_requires_two_distinct_agents():
    with pytest.raises(ValidationError):
        CompetitionConflict(
            case_id="case",
            run_id="run",
            involved_agents=["legal", "legal"],
            summary="invalid",
        )


def test_recheck_contract_enforces_single_controlled_attempt():
    with pytest.raises(ValidationError):
        RecheckRequest(
            conflict_id="conflict",
            case_id="case",
            run_id="run",
            requested_by="final_supervisor",
            targets=["cash_runway"],
            reason="re-check",
            max_attempts=2,
        )


def test_competition_contracts_reject_unknown_cross_lane_fields():
    with pytest.raises(ValidationError):
        CompetitionRuntimeIdentity(
            case_id="case",
            run_id="run",
            made_up_field="must fail closed",
        )
