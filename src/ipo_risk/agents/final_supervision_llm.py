"""The LLM Final Supervisor: bounded synthesis on top of frozen composition.

``V04FinalSupervisor`` stays exactly what PR-G froze -- a pure composition layer.
This supervisor keeps that composition as its spine and adds one bounded LLM
synthesis pass over the *already composed* channels, plus the conflicts and
targeted re-check outcomes the E lane produced.

Four invariants hold whether or not the model answers:

1. Every ``risk_id``, ``evidence_id`` and ``conflict_id`` the model emits must be
   one that was supplied to it; anything else invalidates the whole judgement.
2. The model may raise ``overall_risk`` above the deterministic severity floor
   derived from verified document risks, never lower it.  A verified high risk
   cannot be talked down.
3. No number may appear in the synthesis prose that is not already present in the
   bounded payload, and no probability/forecast vocabulary may appear at all.
4. When the provider is missing, fails or returns something out of scope, the
   deterministic composition is returned unchanged with the reason stated.  The
   product never blanks and never silently degrades.
"""

from __future__ import annotations

import json
import re
from enum import StrEnum
from time import perf_counter
from typing import Any, Iterable, Literal, Sequence

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ipo_risk.agents.final_supervisor import V04FinalSupervisor
from ipo_risk.schemas import Evidence, EvidenceSourceType, RiskItem, RiskLevel
from ipo_risk.schemas.competition_runtime import (
    AgentResultEnvelope,
    CompetitionConflict,
    ConflictStatus,
    TraceEvent,
    TraceEventType,
)
from ipo_risk.schemas.final_supervision import FinalSupervisionInput, FinalSupervisionResult


FINAL_SUPERVISION_SCHEMA_VERSION = "v04_final_supervision_v1"
FINAL_SUPERVISION_PROMPT_VERSION = "v04_final_supervision_v1"
FINAL_SUPERVISION_TASK = "final_supervision_synthesis"
FINAL_SUPERVISOR_AGENT = "llm_final_supervisor"

_RISK_ORDER = (RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL)
_RISK_RANK = {level.value: index for index, level in enumerate(_RISK_ORDER)}

_NUMBER = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?")
# Vocabulary that would turn a supervisory synthesis into a prediction.  Both
# languages are listed because the product surface is bilingual.
_FORBIDDEN_TERMS = (
    "probability", "likelihood", "forecast", "expected return", "price target",
    "will rise", "will fall", "guaranteed", "概率", "预测收益", "涨幅", "跌幅", "必然",
)


class SupervisionStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class ScopeViolation(ValueError):
    """The model cited something it was not given."""


class SupervisionFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    statement: str = Field(min_length=1)
    # Empty only when the run produced no risk at all; ``_validate_scope``
    # requires a citation whenever there is something to cite.
    risk_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()


class ConflictAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    conflict_id: str = Field(min_length=1)
    assessment: str = Field(min_length=1)


class RecheckTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    target: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    risk_ids: tuple[str, ...] = ()


class FinalSupervisionJudgement(BaseModel):
    """The bounded structured output; it carries no score and no probability."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    overall_risk: Literal["low", "medium", "high", "critical"]
    overall_risk_rationale: str = Field(min_length=1)
    key_findings: tuple[SupervisionFinding, ...] = Field(min_length=1)
    conflict_assessments: tuple[ConflictAssessment, ...] = ()
    uncertainties: tuple[str, ...] = ()
    recheck_required: bool = False
    recheck_targets: tuple[RecheckTarget, ...] = ()
    final_explanation: str = Field(min_length=1)

    @field_validator("overall_risk_rationale", "final_explanation")
    @classmethod
    def _no_prediction_vocabulary(cls, value: str) -> str:
        lowered = value.lower()
        if any(term in lowered for term in _FORBIDDEN_TERMS):
            raise ValueError("supervisory synthesis cannot use prediction vocabulary")
        return value


class FinalSupervisionBundle(BaseModel):
    """Everything the E lane produced for one run, ready for trace and product."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    result: FinalSupervisionResult
    judgement: FinalSupervisionJudgement | None = None
    status: SupervisionStatus
    reason: str
    deterministic_severity_floor: str
    conflicts: tuple[CompetitionConflict, ...] = ()
    agent_result: AgentResultEnvelope
    trace_events: tuple[TraceEvent, ...] = ()


def severity_floor(risks: Iterable[RiskItem]) -> str:
    """The highest verified document severity; the judgement may not go below it."""

    levels = [risk.level.value for risk in risks]
    if not levels:
        return RiskLevel.LOW.value
    return max(levels, key=lambda level: _RISK_RANK[level])


def _numbers(text: str) -> set[str]:
    return {match.group(0).replace(",", "") for match in _NUMBER.finditer(text)}


class LLMFinalSupervisor:
    """PR-G composition plus one governed LLM synthesis pass."""

    name = "llm"
    schema_version = FINAL_SUPERVISION_SCHEMA_VERSION
    prompt_version = FINAL_SUPERVISION_PROMPT_VERSION

    def __init__(self, llm_provider=None, cohort_evidence=None) -> None:
        self.llm_provider = llm_provider
        self.composer = V04FinalSupervisor(cohort_evidence)

    # The FinalSupervisor Protocol.  A caller that knows nothing about the E lane
    # still gets the composed result, with the synthesis folded into metadata.
    def finalize(self, inputs: FinalSupervisionInput) -> FinalSupervisionResult:
        return self.supervise(inputs).result

    def supervise(
        self,
        inputs: FinalSupervisionInput,
        *,
        case_id: str = "unknown_case",
        run_id: str = "unknown_run",
        conflicts: Sequence[CompetitionConflict] = (),
        unsettled_risks: Sequence[RiskItem] = (),
        rejected_risks: Sequence[RiskItem] = (),
    ) -> FinalSupervisionBundle:
        composed = self.composer.finalize(inputs)
        verified = list(inputs.document_supervision.verified_risks) if inputs.document_supervision else []
        floor = severity_floor(verified)
        payload = self._payload(composed, inputs, conflicts, unsettled_risks, rejected_risks, floor)
        judgement, status, reason, trace = self._synthesise(payload, case_id=case_id, run_id=run_id)

        result = composed.model_copy(
            update={
                "metadata": {
                    **composed.metadata,
                    "final_supervision_llm": {
                        "schema_version": self.schema_version,
                        "prompt_version": self.prompt_version,
                        "status": status.value,
                        "reason": reason,
                        "deterministic_severity_floor": floor,
                        "judgement": judgement.model_dump(mode="json") if judgement else None,
                    },
                    "conflict_status_counts": self._status_counts(conflicts),
                    "unresolved_conflict_count": sum(
                        1 for conflict in conflicts if conflict.status is not ConflictStatus.RESOLVED
                    ) if conflicts else composed.metadata.get("unresolved_conflict_count", 0),
                }
            }
        )
        return FinalSupervisionBundle(
            result=result,
            judgement=judgement,
            status=status,
            reason=reason,
            deterministic_severity_floor=floor,
            conflicts=tuple(conflicts),
            agent_result=AgentResultEnvelope(
                case_id=case_id,
                run_id=run_id,
                agent_name=FINAL_SUPERVISOR_AGENT,
                status=status.value,
                risk_ids=list(result.referenced_risk_ids),
                evidence_ids=list(result.referenced_evidence_ids),
                provider_name=getattr(self.llm_provider, "name", None),
                prompt_version=self.prompt_version,
                warnings=[] if status is SupervisionStatus.AVAILABLE else [reason],
                metadata={
                    "task": "synthesise governed channels into a supervisory judgement",
                    "deterministic_severity_floor": floor,
                    "conflict_count": len(conflicts),
                    "creates_no_new_risk": True,
                    "probability_claimed": False,
                },
            ),
            trace_events=trace,
        )

    @staticmethod
    def _status_counts(conflicts: Sequence[CompetitionConflict]) -> dict[str, int]:
        counts = {status.value: 0 for status in ConflictStatus}
        for conflict in conflicts:
            counts[conflict.status.value] += 1
        return counts

    def _payload(
        self,
        composed: FinalSupervisionResult,
        inputs: FinalSupervisionInput,
        conflicts: Sequence[CompetitionConflict],
        unsettled_risks: Sequence[RiskItem],
        rejected_risks: Sequence[RiskItem],
        floor: str,
    ) -> dict[str, Any]:
        """The bounded payload; the model sees this and nothing else."""

        verified = list(inputs.document_supervision.verified_risks) if inputs.document_supervision else []
        return {
            "deterministic_severity_floor": floor,
            "document_summary": composed.summary,
            "verified_risks": [
                {
                    "risk_id": risk.risk_id,
                    "risk_code": risk.risk_code,
                    "category": risk.category.value,
                    "level": risk.level.value,
                    "conclusion": risk.conclusion,
                    "agent_name": risk.agent_name,
                    "verification_status": risk.verification_status.value,
                    "verification_notes": risk.verification_notes,
                    "evidence_ids": [item.evidence_id for item in risk.evidence],
                    "calculation": (
                        risk.calculation.model_dump(mode="json") if risk.calculation is not None else None
                    ),
                }
                for risk in verified
            ],
            "unsettled_risks": [self._risk_summary(risk) for risk in unsettled_risks],
            # The Verifier's rejections are part of the document channel's verdict;
            # the supervisor has to be able to say what was ruled out and why.
            "rejected_risks": [self._risk_summary(risk) for risk in rejected_risks],
            "channel_states": [state.model_dump(mode="json") for state in composed.channel_states],
            "composite_findings": [finding.model_dump(mode="json") for finding in composed.composite_findings],
            "market_context": (
                inputs.market_context.model_dump(mode="json") if inputs.market_context is not None else None
            ),
            "model_prediction": (
                inputs.model_prediction.model_dump(mode="json") if inputs.model_prediction is not None else None
            ),
            "rule_prediction": (
                {
                    "risk_score": inputs.rule_prediction.risk_score,
                    "risk_level": inputs.rule_prediction.risk_level.value,
                    "explanation": inputs.rule_prediction.explanation,
                    "model_name": inputs.rule_prediction.model_name,
                }
                if inputs.rule_prediction is not None
                else None
            ),
            "conflicts": [conflict.model_dump(mode="json") for conflict in conflicts],
            "uncertainty_statement": composed.uncertainty_statement,
        }

    @staticmethod
    def _risk_summary(risk: RiskItem) -> dict[str, Any]:
        return {
            "risk_id": risk.risk_id,
            "risk_code": risk.risk_code,
            "level": risk.level.value,
            "agent_name": risk.agent_name,
            "verification_status": risk.verification_status.value,
            "verification_notes": risk.verification_notes,
            "evidence_ids": [item.evidence_id for item in risk.evidence],
        }

    @staticmethod
    def _bounded_evidence(payload: dict[str, Any]) -> list[Evidence]:
        """One Evidence object per payload section, so scope is literally bounded."""

        evidence: list[Evidence] = []
        for section, value in sorted(payload.items()):
            if value in (None, [], {}):
                continue
            evidence.append(
                Evidence(
                    evidence_id=f"supervision_input:{section}",
                    text=json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                    section=section,
                    source_type=EvidenceSourceType.CALCULATION,
                    metadata={"section": section},
                )
            )
        return evidence

    def _synthesise(
        self, payload: dict[str, Any], *, case_id: str, run_id: str
    ) -> tuple[FinalSupervisionJudgement | None, SupervisionStatus, str, tuple[TraceEvent, ...]]:
        if self.llm_provider is None:
            reason = "LLM provider is not configured; the deterministic composition is retained in full"
            return None, SupervisionStatus.UNAVAILABLE, reason, (
                self._trace(case_id, run_id, "unavailable", reason=reason),
            )
        started = perf_counter()
        try:
            result = self.llm_provider.generate_structured(
                task_name=FINAL_SUPERVISION_TASK,
                prompt_version=self.prompt_version,
                evidence=self._bounded_evidence(payload),
                response_model=FinalSupervisionJudgement,
            )
            if not isinstance(result, FinalSupervisionJudgement):
                result = FinalSupervisionJudgement.model_validate(result)
            self._validate_scope(result, payload)
        except Exception as exc:
            reason = f"LLM final supervision unavailable: {type(exc).__name__}: {exc}"
            return None, SupervisionStatus.UNAVAILABLE, reason, (
                self._trace(
                    case_id, run_id, "unavailable", reason=reason,
                    latency_ms=max(0, int((perf_counter() - started) * 1000)),
                ),
            )
        metadata = getattr(self.llm_provider, "last_call_metadata", None)
        return result, SupervisionStatus.AVAILABLE, "grounded supervisory synthesis available", (
            self._trace(
                case_id, run_id, "completed",
                latency_ms=metadata.latency_ms if metadata else max(0, int((perf_counter() - started) * 1000)),
                provider_name=metadata.provider_name if metadata else getattr(self.llm_provider, "name", None),
                model_name=metadata.model_name if metadata else None,
                request_id=metadata.request_id if metadata else None,
                raw_response_hash=metadata.raw_response_hash if metadata else None,
                evidence_ids=sorted({item for finding in result.key_findings for item in finding.evidence_ids}),
                structured_output=result.model_dump(mode="json"),
            ),
        )

    def _trace(
        self,
        case_id: str,
        run_id: str,
        status: str,
        *,
        reason: str = "",
        latency_ms: int | None = None,
        provider_name: str | None = None,
        model_name: str | None = None,
        request_id: str | None = None,
        raw_response_hash: str | None = None,
        evidence_ids: Sequence[str] = (),
        structured_output: dict[str, Any] | None = None,
    ) -> TraceEvent:
        details: dict[str, Any] = {"schema_version": self.schema_version}
        if reason:
            details["reason"] = reason
        if not evidence_ids:
            # The synthesis reasons over composed channel state, not over a
            # document Evidence item; saying so keeps the trace accounted for.
            details["no_evidence_reason"] = (
                "the supervisory synthesis reasons over composed channel outputs; the Evidence it relies on "
                "is referenced by the risks it cites"
            )
        if structured_output is not None:
            details["structured_output"] = structured_output
        return TraceEvent(
            event_id=f"trace:{run_id}:final_supervision_llm",
            case_id=case_id,
            run_id=run_id,
            event_type=TraceEventType.LLM,
            status=status,
            agent_name=FINAL_SUPERVISOR_AGENT,
            action=FINAL_SUPERVISION_TASK,
            tool_or_skill="LLMProvider.generate_structured",
            provider_name=provider_name or getattr(self.llm_provider, "name", None),
            model_name=model_name,
            prompt_version=self.prompt_version,
            evidence_ids=list(evidence_ids),
            latency_ms=latency_ms if latency_ms is not None else 0,
            request_id=request_id,
            raw_response_hash=raw_response_hash,
            details=details,
        )

    @staticmethod
    def _validate_scope(judgement: FinalSupervisionJudgement, payload: dict[str, Any]) -> None:
        """Reject the whole judgement if any cited id or number was not supplied."""

        risk_groups = ("verified_risks", "unsettled_risks", "rejected_risks")
        allowed_risks = {
            risk["risk_id"] for group in risk_groups for risk in payload[group]
        }
        allowed_evidence = {
            evidence_id
            for group in risk_groups
            for risk in payload[group]
            for evidence_id in risk["evidence_ids"]
        }
        allowed_conflicts = {conflict["conflict_id"] for conflict in payload["conflicts"]}

        cited_risks = {
            risk_id
            for finding in judgement.key_findings
            for risk_id in finding.risk_ids
        } | {risk_id for target in judgement.recheck_targets for risk_id in target.risk_ids}
        if not cited_risks <= allowed_risks:
            raise ScopeViolation("supervisory synthesis cited a risk_id that was not supplied")
        if allowed_risks and not cited_risks:
            raise ScopeViolation("supervisory synthesis cited no risk although this run produced risks")

        cited_evidence = {
            evidence_id for finding in judgement.key_findings for evidence_id in finding.evidence_ids
        }
        if not cited_evidence <= allowed_evidence:
            raise ScopeViolation("supervisory synthesis cited an evidence_id that was not supplied")

        cited_conflicts = {item.conflict_id for item in judgement.conflict_assessments}
        if not cited_conflicts <= allowed_conflicts:
            raise ScopeViolation("supervisory synthesis assessed a conflict_id that was not supplied")

        floor = payload["deterministic_severity_floor"]
        if _RISK_RANK[judgement.overall_risk] < _RISK_RANK[floor]:
            raise ScopeViolation(
                f"overall_risk {judgement.overall_risk!r} is below the deterministic severity floor {floor!r}"
            )

        supplied = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        supplied_numbers = _numbers(supplied)
        prose = " ".join(
            [
                judgement.overall_risk_rationale,
                judgement.final_explanation,
                *(finding.statement for finding in judgement.key_findings),
                *(item.assessment for item in judgement.conflict_assessments),
                *judgement.uncertainties,
                *(target.reason for target in judgement.recheck_targets),
            ]
        )
        invented = _numbers(prose) - supplied_numbers
        if invented:
            raise ScopeViolation(
                f"supervisory synthesis introduced number(s) absent from the supplied payload: {sorted(invented)}"
            )
        lowered = prose.lower()
        if any(term in lowered for term in _FORBIDDEN_TERMS):
            raise ScopeViolation("supervisory synthesis used prediction vocabulary")


__all__ = [
    "ConflictAssessment",
    "FINAL_SUPERVISION_PROMPT_VERSION",
    "FINAL_SUPERVISION_SCHEMA_VERSION",
    "FINAL_SUPERVISION_TASK",
    "FinalSupervisionBundle",
    "FinalSupervisionJudgement",
    "LLMFinalSupervisor",
    "RecheckTarget",
    "ScopeViolation",
    "SupervisionFinding",
    "SupervisionStatus",
    "severity_floor",
]
