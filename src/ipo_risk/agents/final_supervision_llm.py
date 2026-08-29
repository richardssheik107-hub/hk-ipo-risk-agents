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

from pydantic import BaseModel, ConfigDict, Field

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
FINAL_SUPERVISION_PROMPT_VERSION = "v04_final_supervision_v3"
FINAL_SUPERVISION_TASK = "final_supervision_synthesis"
FINAL_SUPERVISOR_AGENT = "llm_final_supervisor"

_RISK_ORDER = (RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL)
_RISK_RANK = {level.value: index for index, level in enumerate(_RISK_ORDER)}

# A ``-`` that directly follows a digit is a separator, not a sign: it appears
# inside dates, identifiers and ranges.  Reading it as a sign made
# ``2021-01-11`` tokenise as ``2021``/``-01``/``-11``, so the payload never
# contributed the plain ``01``/``11`` and any restatement of a supplied date in
# another format was rejected as an invented number.
_NUMBER = re.compile(r"(?<![\d.])[-+]?\d[\d,]*(?:\.\d+)?")
# Vocabulary that would turn a supervisory synthesis into a prediction.  Both
# languages are listed because the product surface is bilingual.
_FORBIDDEN_TERMS = (
    "probability", "likelihood", "forecast", "expected return", "price target",
    "will rise", "will fall", "guaranteed", "概率", "预测收益", "涨幅", "跌幅", "必然",
)
_PROMPT_NEUTRAL_REPLACEMENT = "descriptive governance wording"


class SupervisionStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class SynthesisOutcome(StrEnum):
    """Why this run ended where it did.

    ``status`` alone cannot carry the acceptance evidence the competition Gate
    needs: a provider that was never configured, a transport failure and a
    judgement the scope guard refused are all ``unavailable``, but only the last
    one demonstrates that the out-of-scope guard actually fired against a real
    model response.  Keeping them apart is what stops an honest degradation from
    later being read as a successful arbitration.
    """

    ACCEPTED = "accepted"
    PROVIDER_NOT_CONFIGURED = "provider_not_configured"
    PROVIDER_CALL_FAILED = "provider_call_failed"
    REJECTED_OUT_OF_SCOPE = "rejected_out_of_scope"
    # A configured Final Supervisor that has no synthesis pass at all; the
    # composition is still valid, there is simply nothing to arbitrate.
    SUPERVISOR_WITHOUT_SYNTHESIS = "supervisor_without_synthesis"


class ScopeViolation(ValueError):
    """A refused judgement with separate machine and audit identities."""

    def __init__(self, message: str, *, code: "ScopeViolationCode") -> None:
        super().__init__(message)
        self.code = code


class ScopeViolationCode(StrEnum):
    REFERENCE_SCOPE_VIOLATION = "REFERENCE_SCOPE_VIOLATION"
    SEVERITY_FLOOR_NOT_MET = "SEVERITY_FLOOR_NOT_MET"
    UNGOVERNED_NUMBER_NOT_ALLOWED = "UNGOVERNED_NUMBER_NOT_ALLOWED"
    FORWARD_LOOKING_LANGUAGE_NOT_ALLOWED = "FORWARD_LOOKING_LANGUAGE_NOT_ALLOWED"


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
    """A bounded, descriptive judgement over supplied governed facts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    overall_risk: Literal["low", "medium", "high", "critical"]
    overall_risk_rationale: str = Field(min_length=1)
    key_findings: tuple[SupervisionFinding, ...] = Field(min_length=1)
    conflict_assessments: tuple[ConflictAssessment, ...] = ()
    uncertainties: tuple[str, ...] = ()
    recheck_required: bool = False
    recheck_targets: tuple[RecheckTarget, ...] = ()
    final_explanation: str = Field(min_length=1)

    # Prediction vocabulary is refused by ``_validate_scope``, not by a field
    # validator here.  The two enforced the same rule, but a model validator
    # fires inside the provider's ``model_validate``, where the failure becomes
    # an opaque transport error that pre-empts the bounded scope correction --
    # so a recoverable, classifiable violation was being reported as an
    # unreachable provider.  The scope guard covers every prose field rather
    # than these two, and its refusal is recorded and correctable.


class SynthesisAttempt(BaseModel):
    """One synthesis attempt, with the evidence a Gate reviewer has to see."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    judgement: FinalSupervisionJudgement | None
    status: SupervisionStatus
    outcome: SynthesisOutcome
    reason: str
    scope_check: dict[str, Any]
    call: dict[str, Any]
    trace_events: tuple[TraceEvent, ...]


class FinalSupervisionBundle(BaseModel):
    """Everything the E lane produced for one run, ready for trace and product."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    result: FinalSupervisionResult
    judgement: FinalSupervisionJudgement | None = None
    status: SupervisionStatus
    # Required: a default here would let a caller silently mislabel why a run
    # degraded, which is the one thing the acceptance evidence must not do.
    outcome: SynthesisOutcome
    reason: str
    scope_check: dict[str, Any] = Field(default_factory=dict)
    call: dict[str, Any] = Field(default_factory=dict)
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


def _normalise_number(token: str) -> str:
    """One canonical spelling per value, so a restatement is not a new number.

    ``08`` and ``8``, ``2,000`` and ``2000``, ``1.50`` and ``1.5`` are the same
    figure.  Only the spelling is folded -- never the value -- so this cannot let
    a genuinely invented number through.
    """

    cleaned = token.replace(",", "")
    sign = ""
    if cleaned[:1] in {"+", "-"}:
        sign = "-" if cleaned[0] == "-" else ""
        cleaned = cleaned[1:]
    whole, dot, fraction = cleaned.partition(".")
    whole = whole.lstrip("0") or "0"
    fraction = fraction.rstrip("0") if dot else ""
    cleaned = f"{whole}.{fraction}" if fraction else whole
    # ``-0`` and ``0`` are one value; zero itself is still a number and is kept,
    # so an invented "0" is caught like any other.
    return cleaned if cleaned == "0" else sign + cleaned


def _numbers(text: str) -> set[str]:
    return {_normalise_number(match.group(0)) for match in _NUMBER.finditer(text)}


def _prompt_safe_payload(value: Any, *, field_name: str = "") -> Any:
    """Project governed facts without feeding guard trigger terms to the model.

    The original payload remains the only input to ``_validate_scope`` and the
    audit trace.  This projection changes no identifiers, numbers, levels or
    channel states; it only neutralises wording in free-text fields and omits
    governance-only keys whose names contain a guarded term.
    """

    if isinstance(value, dict):
        projected: dict[str, Any] = {}
        for key, item in value.items():
            lowered_key = str(key).casefold()
            if any(term.casefold() in lowered_key for term in _FORBIDDEN_TERMS):
                continue
            if field_name == "model_prediction" and key == "score":
                continue
            if field_name == "rule_prediction" and key in {"risk_score", "explanation"}:
                continue
            if field_name == "drivers" and key in {"feature_value", "shap_value"}:
                continue
            projected[key] = _prompt_safe_payload(item, field_name=str(key))
        return projected
    if isinstance(value, (list, tuple)):
        return [_prompt_safe_payload(item, field_name=field_name) for item in value]
    if not isinstance(value, str):
        return value
    if field_name.endswith("_id") or field_name.endswith("_ids"):
        return value
    projected_text = value
    for term in sorted(_FORBIDDEN_TERMS, key=len, reverse=True):
        projected_text = re.sub(
            re.escape(term),
            _PROMPT_NEUTRAL_REPLACEMENT,
            projected_text,
            flags=re.IGNORECASE,
        )
    return projected_text


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
        attempt = self._synthesise(payload, case_id=case_id, run_id=run_id)
        judgement, status, reason = attempt.judgement, attempt.status, attempt.reason

        result = composed.model_copy(
            update={
                "metadata": {
                    **composed.metadata,
                    "final_supervision_llm": {
                        "schema_version": self.schema_version,
                        "prompt_version": self.prompt_version,
                        "status": status.value,
                        "outcome": attempt.outcome.value,
                        "reason": reason,
                        # True only when the scope guard refused a real model
                        # response; a missing provider never proves this.
                        "fail_closed": attempt.outcome is SynthesisOutcome.REJECTED_OUT_OF_SCOPE,
                        "scope_check": attempt.scope_check,
                        "call": attempt.call,
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
            outcome=attempt.outcome,
            reason=reason,
            scope_check=attempt.scope_check,
            call=attempt.call,
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
            trace_events=attempt.trace_events,
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
        risk_groups = (verified, list(unsettled_risks), list(rejected_risks))
        allowed_risk_ids = sorted({risk.risk_id for group in risk_groups for risk in group})
        allowed_evidence_ids = sorted(
            {
                evidence.evidence_id
                for group in risk_groups
                for risk in group
                for evidence in risk.evidence
            }
            | {
                evidence_id
                for conflict in conflicts
                for evidence_id in conflict.evidence_ids
            }
        )
        allowed_conflict_ids = sorted(conflict.conflict_id for conflict in conflicts)
        return {
            "deterministic_severity_floor": floor,
            "reference_scope": {
                "allowed_risk_ids": allowed_risk_ids,
                "allowed_evidence_ids": allowed_evidence_ids,
                "allowed_conflict_ids": allowed_conflict_ids,
            },
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
                self._market_context_summary(inputs.market_context)
                if inputs.market_context is not None
                else None
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
            "conflicts": [self._conflict_summary(conflict) for conflict in conflicts],
            "uncertainty_statement": composed.uncertainty_statement,
        }

    @staticmethod
    def _market_context_summary(market_context: Any) -> dict[str, Any]:
        """Keep governed market facts while omitting duplicate audit provenance.

        The full provenance remains in the runtime artifacts and trace.  The Final
        Supervisor only needs channel availability and the already-governed
        observations; sending the same manifest provenance again adds latency but
        no supervisory fact.
        """

        return {
            "status": market_context.status.value,
            "reason": market_context.reason,
            "blocking_gate": market_context.blocking_gate,
            "observations": [item.model_dump(mode="json") for item in market_context.observations],
            "feature_manifest_hash": market_context.feature_manifest_hash,
        }

    @staticmethod
    def _conflict_summary(conflict: CompetitionConflict) -> dict[str, Any]:
        """Project a conflict to the facts the synthesis and scope guard need.

        Case/run timestamps and claim bookkeeping are already retained by the
        conflict artifact.  Excluding them here avoids asking the model to reason
        over duplicate provenance while preserving every governed identifier it
        may legitimately cite.
        """

        return {
            "conflict_id": conflict.conflict_id,
            "status": conflict.status.value,
            "summary": conflict.summary,
            "resolution_note": conflict.resolution_note,
            "involved_agents": list(conflict.involved_agents),
            "risk_ids": list(conflict.risk_ids),
            "evidence_ids": list(conflict.evidence_ids),
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

    def _call_record(self, latency_fallback: int) -> dict[str, Any]:
        """The provider trace the Gate asks to be retained, whatever the outcome.

        A response the scope guard refused still came from a real provider call,
        so its identity is recorded there too; that is what makes a fail-closed
        run auditable rather than merely absent.
        """

        metadata = getattr(self.llm_provider, "last_call_metadata", None)
        return {
            "provider_name": (
                (metadata.provider_name if metadata else None) or getattr(self.llm_provider, "name", None)
            ),
            "model_name": metadata.model_name if metadata else None,
            "prompt_version": self.prompt_version,
            "request_id": metadata.request_id if metadata else None,
            "raw_response_hash": metadata.raw_response_hash if metadata else None,
            "latency_ms": metadata.latency_ms if metadata else latency_fallback,
        }

    @staticmethod
    def _correction_instruction(violation: ScopeViolation) -> str:
        """Feedback aimed at the rule that was actually broken."""

        if violation.code is ScopeViolationCode.FORWARD_LOOKING_LANGUAGE_NOT_ALLOWED:
            return (
                "Violation code FORWARD_LOOKING_LANGUAGE_NOT_ALLOWED. Rewrite all narrative "
                "fields using only descriptive, evidence-grounded language about established "
                "or unresolved facts. Do not discuss future outcomes or interpret a model score "
                "as a calibrated real-world estimate. Keep all cited IDs and overall_risk unchanged."
            )
        if violation.code is ScopeViolationCode.SEVERITY_FLOOR_NOT_MET:
            return (
                "The previous judgement was rejected because overall_risk was below the supplied "
                "deterministic_severity_floor. Return the same judgement with overall_risk at or "
                "above that floor."
            )
        if violation.code is ScopeViolationCode.UNGOVERNED_NUMBER_NOT_ALLOWED:
            return (
                "Violation code UNGOVERNED_NUMBER_NOT_ALLOWED. Rewrite all narrative fields "
                "using descriptive, evidence-grounded language about established or unresolved "
                "facts. Omit numeric Model and Rule scores. Use another number only when its exact "
                "form is necessary and present in the supplied evidence. Keep all cited IDs and "
                "overall_risk unchanged."
            )
        return (
            "Return a corrected judgement using only IDs in reference_scope. Use empty ID lists "
            "when none apply. Never cite supervision_input transport-envelope IDs."
        )

    @staticmethod
    def _attempt_accounting(
        attempts: int, rejected: Sequence[dict[str, Any]], *, evaluated: bool
    ) -> dict[str, Any]:
        """How many times the model was asked, and what the guard refused.

        The bounded scope correction is a legitimate recovery, not something to
        hide: a Gate reviewer has to be able to see that the first response cited
        something out of scope, which call produced it and what the violation
        was, even when the corrected judgement was accepted.

        ``evaluated`` says whether any response actually reached the scope check.
        A transport failure produced no judgement to check, so its first attempt
        neither passed nor failed -- reporting it as passed would be the exact
        overstatement this accounting exists to prevent.
        """

        return {
            "attempts": attempts,
            # Corrections issued, not responses refused: the last refusal of a
            # fail-closed run is never followed by another correction.
            "scope_corrections": max(0, attempts - 1),
            "refused_response_count": len(rejected),
            "first_attempt_passed": (not rejected) if evaluated else None,
            "rejected_attempts": list(rejected),
        }

    def _synthesise(self, payload: dict[str, Any], *, case_id: str, run_id: str) -> SynthesisAttempt:
        if self.llm_provider is None:
            reason = "LLM provider is not configured; the deterministic composition is retained in full"
            scope_check = {
                "status": "not_applicable",
                "reason": "no provider was configured, so no judgement was produced to check",
                **self._attempt_accounting(0, (), evaluated=False),
            }
            outcome = SynthesisOutcome.PROVIDER_NOT_CONFIGURED
            return SynthesisAttempt(
                judgement=None,
                status=SupervisionStatus.UNAVAILABLE,
                outcome=outcome,
                reason=reason,
                scope_check=scope_check,
                call={},
                trace_events=(
                    self._trace(
                        case_id, run_id, "unavailable",
                        reason=reason, outcome=outcome, scope_check=scope_check,
                    ),
                ),
            )
        started = perf_counter()
        # Every refused response is kept, with the identity of the call that
        # produced it.  A judgement the guard accepted only after a correction is
        # not the same event as one that was in scope first time, and the
        # acceptance evidence has to be able to tell them apart.
        rejected_attempts: list[dict[str, Any]] = []
        try:
            scope_payload = _prompt_safe_payload(payload)
            for scope_attempt in range(1, 3):
                result = self.llm_provider.generate_structured(
                    task_name=FINAL_SUPERVISION_TASK,
                    prompt_version=self.prompt_version,
                    evidence=self._bounded_evidence(scope_payload),
                    response_model=FinalSupervisionJudgement,
                )
                if not isinstance(result, FinalSupervisionJudgement):
                    result = FinalSupervisionJudgement.model_validate(result)
                try:
                    scope_check = self._validate_scope(result, payload)
                    scope_check.update(
                        self._attempt_accounting(
                            scope_attempt, rejected_attempts, evaluated=True
                        )
                    )
                    break
                except ScopeViolation as exc:
                    rejected_attempts.append(
                        {
                            "attempt": scope_attempt,
                            "violation_code": exc.code.value,
                            "audit_violation_detail": str(exc),
                            "violation": str(exc),
                            "call": self._call_record(
                                max(0, int((perf_counter() - started) * 1000))
                            ),
                        }
                    )
                    if scope_attempt >= 2:
                        raise
                    scope_payload = {
                        **payload,
                        "scope_correction": {
                            "previous_result_rejected": True,
                            "violation_code": exc.code.value,
                            "instruction": self._correction_instruction(exc),
                        },
                    }
        except Exception as exc:
            latency = max(0, int((perf_counter() - started) * 1000))
            refused = isinstance(exc, ScopeViolation)
            outcome = (
                SynthesisOutcome.REJECTED_OUT_OF_SCOPE if refused
                else SynthesisOutcome.PROVIDER_CALL_FAILED
            )
            reason = f"LLM final supervision unavailable: {type(exc).__name__}: {exc}"
            scope_check = (
                {
                    "status": "failed",
                    "violation_code": exc.code.value,
                    "audit_violation_detail": str(exc),
                    "violation": str(exc),
                } if refused
                else {
                    "status": "not_applicable",
                    "reason": "the provider call returned no judgement to check",
                }
            )
            scope_check.update(
                self._attempt_accounting(
                    len(rejected_attempts) or 1, rejected_attempts, evaluated=refused
                )
            )
            return SynthesisAttempt(
                judgement=None,
                status=SupervisionStatus.UNAVAILABLE,
                outcome=outcome,
                reason=reason,
                scope_check=scope_check,
                # A failed transport has no call identity worth asserting; a
                # refused response does, so it is kept.
                call=self._call_record(latency) if refused else {},
                trace_events=(
                    self._trace(
                        case_id, run_id, "unavailable", reason=reason, latency_ms=latency,
                        outcome=outcome, scope_check=scope_check,
                    ),
                ),
            )
        call = self._call_record(max(0, int((perf_counter() - started) * 1000)))
        return SynthesisAttempt(
            judgement=result,
            status=SupervisionStatus.AVAILABLE,
            outcome=SynthesisOutcome.ACCEPTED,
            reason="grounded supervisory synthesis available",
            scope_check=scope_check,
            call=call,
            trace_events=(
                self._trace(
                    case_id, run_id, "completed",
                    latency_ms=call["latency_ms"],
                    provider_name=call["provider_name"],
                    model_name=call["model_name"],
                    request_id=call["request_id"],
                    raw_response_hash=call["raw_response_hash"],
                    evidence_ids=sorted(
                        {item for finding in result.key_findings for item in finding.evidence_ids}
                    ),
                    structured_output=result.model_dump(mode="json"),
                    outcome=SynthesisOutcome.ACCEPTED,
                    scope_check=scope_check,
                ),
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
        outcome: SynthesisOutcome = SynthesisOutcome.ACCEPTED,
        scope_check: dict[str, Any] | None = None,
    ) -> TraceEvent:
        details: dict[str, Any] = {"schema_version": self.schema_version, "outcome": outcome.value}
        if scope_check is not None:
            details["scope_check"] = scope_check
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
    def _validate_scope(
        judgement: FinalSupervisionJudgement, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Reject the whole judgement if any cited id or number was not supplied.

        Returns the accounting a Gate reviewer needs -- what was cited, out of
        how much was supplied -- so that "no out-of-scope reference" is a
        measured statement about this run rather than an assertion about the code.
        """

        reference_scope = payload["reference_scope"]
        allowed_risks = set(reference_scope["allowed_risk_ids"])
        allowed_evidence = set(reference_scope["allowed_evidence_ids"])
        allowed_conflicts = set(reference_scope["allowed_conflict_ids"])

        cited_risks = {
            risk_id
            for finding in judgement.key_findings
            for risk_id in finding.risk_ids
        } | {risk_id for target in judgement.recheck_targets for risk_id in target.risk_ids}
        if not cited_risks <= allowed_risks:
            raise ScopeViolation(
                "supervisory synthesis cited a risk_id that was not supplied",
                code=ScopeViolationCode.REFERENCE_SCOPE_VIOLATION,
            )
        if allowed_risks and not cited_risks:
            raise ScopeViolation(
                "supervisory synthesis cited no risk although this run produced risks",
                code=ScopeViolationCode.REFERENCE_SCOPE_VIOLATION,
            )

        cited_evidence = {
            evidence_id for finding in judgement.key_findings for evidence_id in finding.evidence_ids
        }
        if not cited_evidence <= allowed_evidence:
            raise ScopeViolation(
                "supervisory synthesis cited an evidence_id that was not supplied",
                code=ScopeViolationCode.REFERENCE_SCOPE_VIOLATION,
            )

        cited_conflicts = {item.conflict_id for item in judgement.conflict_assessments}
        if not cited_conflicts <= allowed_conflicts:
            raise ScopeViolation(
                "supervisory synthesis assessed a conflict_id that was not supplied",
                code=ScopeViolationCode.REFERENCE_SCOPE_VIOLATION,
            )

        floor = payload["deterministic_severity_floor"]
        if _RISK_RANK[judgement.overall_risk] < _RISK_RANK[floor]:
            raise ScopeViolation(
                f"overall_risk {judgement.overall_risk!r} is below the deterministic severity floor {floor!r}",
                code=ScopeViolationCode.SEVERITY_FLOOR_NOT_MET,
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
                f"supervisory synthesis introduced number(s) absent from the supplied payload: {sorted(invented)}",
                code=ScopeViolationCode.UNGOVERNED_NUMBER_NOT_ALLOWED,
            )
        lowered = prose.lower()
        used = sorted(term for term in _FORBIDDEN_TERMS if term in lowered)
        if used:
            raise ScopeViolation(
                "supervisory synthesis used prediction vocabulary: " + ", ".join(used),
                code=ScopeViolationCode.FORWARD_LOOKING_LANGUAGE_NOT_ALLOWED,
            )

        return {
            "status": "passed",
            "cited_risk_ids": sorted(cited_risks),
            "cited_evidence_ids": sorted(cited_evidence),
            "cited_conflict_ids": sorted(cited_conflicts),
            "supplied_risk_id_count": len(allowed_risks),
            "supplied_evidence_id_count": len(allowed_evidence),
            "supplied_conflict_id_count": len(allowed_conflicts),
            "out_of_scope_reference_count": 0,
            "deterministic_severity_floor": floor,
            "overall_risk": judgement.overall_risk,
            "severity_floor_respected": True,
            "invented_number_count": 0,
            "prediction_vocabulary_used": False,
        }


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
    "ScopeViolationCode",
    "SupervisionFinding",
    "SupervisionStatus",
    "SynthesisAttempt",
    "SynthesisOutcome",
    "severity_floor",
]
