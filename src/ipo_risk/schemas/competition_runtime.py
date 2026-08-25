"""Versioned competition-runtime sidecars for cross-lane integration.

These models deliberately reference frozen/runtime objects by stable IDs instead of
embedding or mutating PR-A--PR-G schemas. They form the hand-off boundary between
Document, Market, Model, Supervisor, trace, and human-review lanes.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


COMPETITION_RUNTIME_SCHEMA_VERSION = "competition_runtime_v1"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class CompetitionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CompetitionRuntimeIdentity(CompetitionModel):
    schema_version: str = COMPETITION_RUNTIME_SCHEMA_VERSION
    case_id: str = Field(min_length=1)
    stock_code: str = ""
    listing_date: date | None = None
    run_id: str = Field(min_length=1)
    provider_name: str | None = None
    model_name: str | None = None
    prompt_version: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)


class AgentResultEnvelope(CompetitionModel):
    """Generic, non-business-specific output envelope consumed across lanes."""

    case_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    agent_name: str = Field(min_length=1)
    status: str = Field(min_length=1)
    risk_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    calculation_ids: list[str] = Field(default_factory=list)
    provider_name: str | None = None
    model_name: str | None = None
    prompt_version: str | None = None
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConflictStatus(StrEnum):
    DETECTED = "detected"
    RECHECKING = "rechecking"
    RESOLVED = "resolved"
    PARTIALLY_RESOLVED = "partially_resolved"
    UNRESOLVED = "unresolved"


class CompetitionConflict(CompetitionModel):
    conflict_id: str = Field(default_factory=lambda: str(uuid4()))
    case_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    involved_agents: list[str] = Field(min_length=2)
    risk_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    summary: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    status: ConflictStatus = ConflictStatus.DETECTED
    resolution_note: str | None = None
    created_at: datetime = Field(default_factory=_now_utc)

    @field_validator("involved_agents")
    @classmethod
    def _unique_agents(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if len(set(cleaned)) < 2:
            raise ValueError("a conflict must involve at least two distinct agents")
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("involved_agents must be unique")
        return cleaned


class RecheckStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RecheckRequest(CompetitionModel):
    """One controlled re-check request; open-ended autonomous loops are forbidden."""

    recheck_id: str = Field(default_factory=lambda: str(uuid4()))
    conflict_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    requested_by: str = Field(min_length=1)
    targets: list[str] = Field(min_length=1)
    reason: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    max_attempts: int = Field(default=1, ge=1, le=1)
    status: RecheckStatus = RecheckStatus.PENDING
    created_at: datetime = Field(default_factory=_now_utc)


class TraceEventType(StrEnum):
    PARSER = "parser"
    RETRIEVER = "retriever"
    AGENT = "agent"
    SKILL = "skill"
    LLM = "llm"
    VERIFIER = "verifier"
    MARKET = "market"
    MODEL = "model"
    CONFLICT = "conflict"
    RECHECK = "recheck"
    SUPERVISOR = "supervisor"
    HUMAN_REVIEW = "human_review"


class TraceEvent(CompetitionModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    case_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    event_type: TraceEventType
    status: str = Field(min_length=1)
    agent_name: str | None = None
    action: str = ""
    tool_or_skill: str = ""
    provider_name: str | None = None
    model_name: str | None = None
    prompt_version: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    calculation_ids: list[str] = Field(default_factory=list)
    conflict_id: str | None = None
    recheck_id: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    request_id: str | None = None
    raw_response_hash: str | None = None
    occurred_at: datetime = Field(default_factory=_now_utc)
    details: dict[str, Any] = Field(default_factory=dict)


class HumanReviewDecision(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"
    NEEDS_FOLLOW_UP = "needs_follow_up"


class HumanReview(CompetitionModel):
    """Reviewer sidecar; never mutates machine Evidence or the original claim."""

    review_id: str = Field(default_factory=lambda: str(uuid4()))
    case_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    original_machine_status: str = Field(min_length=1)
    decision: HumanReviewDecision
    post_review_status: str = Field(min_length=1)
    reviewer_id: str = Field(min_length=1)
    reviewer_note: str = ""
    evidence_id: str | None = None
    page: int | None = Field(default=None, ge=1)
    bbox: tuple[float, float, float, float] | None = None
    reviewed_at: datetime = Field(default_factory=_now_utc)


class CompetitionRuntimeSidecar(CompetitionModel):
    identity: CompetitionRuntimeIdentity
    agent_results: list[AgentResultEnvelope] = Field(default_factory=list)
    conflicts: list[CompetitionConflict] = Field(default_factory=list)
    rechecks: list[RecheckRequest] = Field(default_factory=list)
    trace_events: list[TraceEvent] = Field(default_factory=list)
    human_reviews: list[HumanReview] = Field(default_factory=list)
