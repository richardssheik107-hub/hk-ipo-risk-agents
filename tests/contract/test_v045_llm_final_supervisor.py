"""The LLM Final Supervisor may weigh governed channels; it may not invent one.

Every test here fixes an invariant that has to survive a model that answers
badly: cited ids must have been supplied, a verified severity cannot be talked
down, prose cannot introduce numbers or prediction vocabulary, and a provider
that fails must leave the frozen PR-G composition untouched.
"""

from __future__ import annotations

import pytest

from ipo_risk.agents.final_supervision_llm import (
    FINAL_SUPERVISION_PROMPT_VERSION,
    FINAL_SUPERVISION_TASK,
    FinalSupervisionJudgement,
    LLMFinalSupervisor,
    SupervisionStatus,
    SynthesisOutcome,
    severity_floor,
)
from ipo_risk.agents.final_supervisor import V04FinalSupervisor
from ipo_risk.providers.mock import MockLLMProvider
from ipo_risk.providers.prompt_registry import PromptResolutionError, resolve_domain_instruction
from ipo_risk.schemas import (
    Evidence,
    RiskCategory,
    RiskItem,
    RiskLevel,
    SupervisionResult,
    VerificationStatus,
)
from ipo_risk.schemas.competition_runtime import CompetitionConflict, ConflictStatus
from ipo_risk.schemas.final_supervision import FinalSupervisionInput


EVIDENCE_ID = "evidence-1"
RISK_ID = "risk-1"


def _risk(level: RiskLevel = RiskLevel.HIGH) -> RiskItem:
    return RiskItem(
        risk_id=RISK_ID,
        risk_code="cash_runway",
        category=RiskCategory.FINANCIAL,
        risk_type="cash_runway",
        level=level,
        score=80,
        conclusion="runway is short",
        agent_name="financial",
        verification_status=VerificationStatus.VERIFIED,
        evidence=[Evidence(evidence_id=EVIDENCE_ID, text="cash position", page=12)],
    )


def _inputs(level: RiskLevel = RiskLevel.HIGH) -> FinalSupervisionInput:
    return FinalSupervisionInput(
        document_supervision=SupervisionResult(verified_risks=[_risk(level)], summary="one risk")
    )


def _conflict() -> CompetitionConflict:
    return CompetitionConflict(
        conflict_id="conflict:run-1:agent_verifier_disagreement:financial:cash_runway",
        case_id="ipo_2024_02410",
        run_id="run-1",
        involved_agents=["financial", "verifier"],
        risk_ids=[RISK_ID],
        summary="the agent asserted a risk the verifier left pending",
        status=ConflictStatus.UNRESOLVED,
    )


def _judgement(**overrides) -> dict:
    payload = {
        "overall_risk": "high",
        "overall_risk_rationale": "the document channel verified a severe funding risk",
        "key_findings": [
            {
                "statement": "cash runway is the dominant verified concern",
                "risk_ids": [RISK_ID],
                "evidence_ids": [EVIDENCE_ID],
            }
        ],
        "conflict_assessments": [],
        "uncertainties": ["the market channel did not run"],
        "recheck_required": False,
        "recheck_targets": [],
        "final_explanation": "the verified funding risk drives the supervisory conclusion",
    }
    payload.update(overrides)
    return payload


def _supervisor(payload: dict | None) -> LLMFinalSupervisor:
    provider = MockLLMProvider({FINAL_SUPERVISION_TASK: payload} if payload is not None else {})
    return LLMFinalSupervisor(llm_provider=provider)


class _SequenceProvider:
    name = "sequence"
    last_call_metadata = None

    def __init__(self, payloads: list[dict]) -> None:
        self.payloads = list(payloads)
        self.calls: list[list[Evidence]] = []

    def generate_structured(self, *, task_name, prompt_version, evidence, response_model):
        self.calls.append(evidence)
        return response_model.model_validate(self.payloads.pop(0))


def test_the_supervision_prompt_identity_is_registered_and_exact() -> None:
    assert resolve_domain_instruction(FINAL_SUPERVISION_TASK, FINAL_SUPERVISION_PROMPT_VERSION)
    with pytest.raises(PromptResolutionError):
        resolve_domain_instruction(FINAL_SUPERVISION_TASK, "v04_final_supervision_v0")


def test_a_grounded_judgement_is_attached_without_replacing_the_composition() -> None:
    bundle = _supervisor(_judgement()).supervise(_inputs(), case_id="c", run_id="r")
    assert bundle.status is SupervisionStatus.AVAILABLE
    frozen = V04FinalSupervisor().finalize(_inputs())
    # Everything the frozen composition asserts is preserved verbatim.
    assert bundle.result.summary == frozen.summary
    assert bundle.result.referenced_risk_ids == frozen.referenced_risk_ids
    assert bundle.result.referenced_evidence_ids == frozen.referenced_evidence_ids
    assert bundle.result.metadata["final_supervision_llm"]["judgement"]["overall_risk"] == "high"


@pytest.mark.parametrize(
    "payload, reason",
    [
        (_judgement(key_findings=[{"statement": "invented", "risk_ids": ["risk-unknown"]}]), "risk id"),
        (
            _judgement(
                key_findings=[
                    {"statement": "cited", "risk_ids": [RISK_ID], "evidence_ids": ["evidence-unknown"]}
                ]
            ),
            "evidence id",
        ),
        (
            _judgement(conflict_assessments=[{"conflict_id": "conflict:unknown", "assessment": "x"}]),
            "conflict id",
        ),
    ],
)
def test_an_out_of_scope_citation_invalidates_the_whole_judgement(payload, reason) -> None:
    bundle = _supervisor(payload).supervise(_inputs(), conflicts=[_conflict()])
    assert bundle.judgement is None, reason
    assert bundle.status is SupervisionStatus.UNAVAILABLE
    assert "ScopeViolation" in bundle.reason


def test_one_bounded_scope_correction_can_recover_without_relaxing_scope() -> None:
    provider = _SequenceProvider(
        [
            _judgement(
                key_findings=[
                    {"statement": "invalid", "risk_ids": ["risk-unknown"], "evidence_ids": []}
                ]
            ),
            _judgement(),
        ]
    )

    bundle = LLMFinalSupervisor(provider).supervise(_inputs())

    assert bundle.status is SupervisionStatus.AVAILABLE
    assert len(provider.calls) == 2
    correction = next(item for item in provider.calls[1] if item.section == "scope_correction")
    assert "reference_scope" in correction.text
    assert "supervision_input" in correction.text


_OUT_OF_SCOPE = _judgement(
    key_findings=[{"statement": "invalid", "risk_ids": ["risk-unknown"], "evidence_ids": []}]
)


def test_a_bounded_scope_correction_is_recorded_rather_than_absorbed() -> None:
    """A corrected run must not be indistinguishable from a first-shot clean one.

    Gate E1 asks that the synthesis reference nothing out of scope. The bounded
    correction is a legitimate recovery, but a reviewer has to be able to see
    that the model did emit an out-of-scope reference before it, and which call
    produced it -- otherwise the acceptance evidence quietly overstates the run.
    """
    provider = _SequenceProvider([_OUT_OF_SCOPE, _judgement()])
    bundle = LLMFinalSupervisor(provider).supervise(_inputs())

    assert bundle.status is SupervisionStatus.AVAILABLE
    check = bundle.scope_check
    assert check["status"] == "passed"
    assert check["attempts"] == 2
    assert check["scope_corrections"] == 1
    assert check["refused_response_count"] == 1
    assert check["first_attempt_passed"] is False

    refused = check["rejected_attempts"][0]
    assert refused["attempt"] == 1
    assert "risk_id that was not supplied" in refused["violation"]
    # The refused response came from a real call; its identity is kept too.
    assert refused["call"]["provider_name"] == "sequence"
    assert refused["call"]["prompt_version"] == FINAL_SUPERVISION_PROMPT_VERSION


def test_an_in_scope_first_response_records_no_correction() -> None:
    bundle = _supervisor(_judgement()).supervise(_inputs())
    check = bundle.scope_check
    assert check["attempts"] == 1
    assert check["scope_corrections"] == 0
    assert check["first_attempt_passed"] is True
    assert check["rejected_attempts"] == []


def test_a_fail_closed_run_records_every_refused_response() -> None:
    provider = _SequenceProvider([_OUT_OF_SCOPE, _OUT_OF_SCOPE])
    bundle = LLMFinalSupervisor(provider).supervise(_inputs())

    assert bundle.outcome is SynthesisOutcome.REJECTED_OUT_OF_SCOPE
    check = bundle.scope_check
    assert check["status"] == "failed"
    # Two responses were refused, but only one correction was ever issued.
    assert check["refused_response_count"] == 2
    assert check["scope_corrections"] == 1
    assert len(check["rejected_attempts"]) == 2


def test_a_run_without_a_provider_claims_no_attempt_at_all() -> None:
    """Zero attempts must not read as "the first attempt passed"."""
    bundle = LLMFinalSupervisor(llm_provider=None).supervise(_inputs())
    check = bundle.scope_check
    assert check["attempts"] == 0
    assert check["first_attempt_passed"] is None
    assert check["rejected_attempts"] == []


def test_a_transport_failure_never_claims_its_first_attempt_passed() -> None:
    """No judgement reached the guard, so nothing about scope was established.

    Reporting an unanswered call as a passed first attempt would be exactly the
    overstatement this accounting exists to prevent.
    """
    bundle = _supervisor(None).supervise(_inputs())
    assert bundle.outcome is SynthesisOutcome.PROVIDER_CALL_FAILED
    check = bundle.scope_check
    assert check["status"] == "not_applicable"
    assert check["first_attempt_passed"] is None
    assert check["refused_response_count"] == 0


def test_scope_correction_remains_fail_closed_after_one_retry() -> None:
    invalid = _judgement(
        key_findings=[
            {"statement": "invalid", "risk_ids": ["risk-unknown"], "evidence_ids": []}
        ]
    )
    provider = _SequenceProvider([invalid, invalid])

    bundle = LLMFinalSupervisor(provider).supervise(_inputs())

    assert bundle.status is SupervisionStatus.UNAVAILABLE
    assert bundle.outcome is SynthesisOutcome.REJECTED_OUT_OF_SCOPE
    assert len(provider.calls) == 2


def test_the_judgement_cannot_go_below_the_verified_severity_floor() -> None:
    """A verified critical document risk cannot be talked down to medium."""
    bundle = _supervisor(_judgement(overall_risk="medium")).supervise(_inputs(RiskLevel.CRITICAL))
    assert bundle.judgement is None
    assert bundle.deterministic_severity_floor == "critical"
    assert "below the deterministic severity floor" in bundle.reason


def test_the_judgement_may_escalate_above_the_floor() -> None:
    bundle = _supervisor(_judgement(overall_risk="critical")).supervise(_inputs(RiskLevel.HIGH))
    assert bundle.judgement is not None
    assert bundle.judgement.overall_risk == "critical"


def test_prose_cannot_introduce_a_number_that_was_never_supplied() -> None:
    bundle = _supervisor(
        _judgement(final_explanation="the runway is 2.76 months and 999 days short")
    ).supervise(_inputs())
    assert bundle.judgement is None
    assert "introduced number" in bundle.reason


@pytest.mark.parametrize(
    "field, text",
    [
        ("final_explanation", "the break probability is elevated"),
        ("overall_risk_rationale", "our forecast of the listing outcome"),
    ],
)
def test_prediction_vocabulary_is_rejected(field, text) -> None:
    bundle = _supervisor(_judgement(**{field: text})).supervise(_inputs())
    assert bundle.judgement is None
    assert bundle.status is SupervisionStatus.UNAVAILABLE


def test_prediction_vocabulary_is_refused_by_the_scope_guard_and_named() -> None:
    """Enforcement lives at the scope guard, where it is recoverable.

    It used to be a field validator on the model as well, which fired inside the
    provider's own ``model_validate``: the violation surfaced as an opaque
    transport error, was classified as an unreachable provider, and pre-empted
    the bounded correction entirely. Measured against a real model, that turned
    a fixable phrasing slip into four failed runs out of five. The scope guard
    covers every prose field rather than two, and names what it refused.
    """
    bundle = _supervisor(
        _judgement(final_explanation="the probability of a first-day break is high")
    ).supervise(_inputs())

    assert bundle.judgement is None
    assert bundle.outcome is SynthesisOutcome.REJECTED_OUT_OF_SCOPE
    assert bundle.scope_check["status"] == "failed"
    assert "prediction vocabulary" in bundle.scope_check["violation"]
    # The offending term is named, so the correction can address it.
    assert "probability" in bundle.scope_check["violation"]


def test_the_scope_guard_covers_prose_the_old_field_validator_never_saw() -> None:
    """A key finding or an uncertainty could smuggle the vocabulary through."""
    for payload in (
        _judgement(uncertainties=["the likelihood of dilution is unclear"]),
        _judgement(
            key_findings=[
                {
                    "statement": "a forecast of continued losses",
                    "risk_ids": [RISK_ID],
                    "evidence_ids": [EVIDENCE_ID],
                }
            ]
        ),
    ):
        bundle = _supervisor(payload).supervise(_inputs())
        assert bundle.judgement is None
        assert bundle.outcome is SynthesisOutcome.REJECTED_OUT_OF_SCOPE


def test_a_vocabulary_slip_is_recoverable_within_the_bounded_correction() -> None:
    """The point of moving enforcement: one slip no longer loses the run."""
    provider = _SequenceProvider(
        [_judgement(final_explanation="the likelihood of a break is elevated"), _judgement()]
    )
    bundle = LLMFinalSupervisor(provider).supervise(_inputs())

    assert bundle.status is SupervisionStatus.AVAILABLE
    assert bundle.outcome is SynthesisOutcome.ACCEPTED
    assert bundle.scope_check["scope_corrections"] == 1
    assert bundle.scope_check["first_attempt_passed"] is False
    assert "likelihood" in bundle.scope_check["rejected_attempts"][0]["violation"]


def test_the_correction_feedback_addresses_the_rule_that_was_broken() -> None:
    """Telling a model that used a banned word to fix its ids would help nobody."""
    provider = _SequenceProvider(
        [_judgement(final_explanation="the likelihood of a break is elevated"), _judgement()]
    )
    LLMFinalSupervisor(provider).supervise(_inputs())

    correction = next(item for item in provider.calls[1] if item.section == "scope_correction")
    assert "prediction vocabulary" in correction.text
    assert "likelihood" in correction.text
    assert "Keep the same findings" in correction.text


def test_the_registered_prompt_bans_the_vocabulary_outright() -> None:
    """The v1 wording only forbade restating a model score that way.

    A model reading it wrote "the likelihood of dilution" and lost the whole
    judgement, so v2 states the ban as a ban over every string it produces.
    """
    instruction = resolve_domain_instruction(
        FINAL_SUPERVISION_TASK, FINAL_SUPERVISION_PROMPT_VERSION
    )
    assert FINAL_SUPERVISION_PROMPT_VERSION == "v04_final_supervision_v2"
    # Normalised: the instruction is hard-wrapped, so raw substrings would be
    # asserting about line breaks rather than about the ban.
    flattened = " ".join(instruction.split())
    for term in ("probability", "likelihood", "forecast", "概率"):
        assert term in flattened
    assert "must not appear anywhere" in flattened
    assert "rejected in full" in flattened
    # v1 stays resolvable so historical traces still identify their prompt.
    assert resolve_domain_instruction(FINAL_SUPERVISION_TASK, "v04_final_supervision_v1")


def test_no_provider_degrades_to_the_frozen_composition_and_says_so() -> None:
    bundle = LLMFinalSupervisor(llm_provider=None).supervise(_inputs())
    assert bundle.judgement is None
    assert bundle.status is SupervisionStatus.UNAVAILABLE
    assert "not configured" in bundle.reason
    assert bundle.result.summary == V04FinalSupervisor().finalize(_inputs()).summary
    assert bundle.result.metadata["probability_claimed"] is False
    assert bundle.result.metadata["creates_no_new_risk"] is True


def test_the_protocol_method_still_returns_a_plain_composition_result() -> None:
    result = _supervisor(_judgement()).finalize(_inputs())
    assert result.metadata["classification"] == "SUPERVISORY_SYNTHESIS"
    assert set(result.referenced_evidence_ids) == {EVIDENCE_ID}


def test_conflict_status_counts_are_carried_into_the_result_metadata() -> None:
    bundle = _supervisor(_judgement()).supervise(_inputs(), conflicts=[_conflict()])
    counts = bundle.result.metadata["conflict_status_counts"]
    assert counts["unresolved"] == 1
    assert bundle.result.metadata["unresolved_conflict_count"] == 1


def test_bounded_payload_keeps_conflict_scope_but_omits_duplicate_provenance() -> None:
    supervisor = LLMFinalSupervisor(llm_provider=None)
    inputs = _inputs()
    composed = V04FinalSupervisor().finalize(inputs)
    payload = supervisor._payload(
        composed,
        inputs,
        [_conflict()],
        (),
        (),
        "high",
    )

    projected = payload["conflicts"][0]
    assert projected["conflict_id"] == _conflict().conflict_id
    assert projected["risk_ids"] == [RISK_ID]
    assert "case_id" not in projected
    assert "run_id" not in projected
    assert "created_at" not in projected
    assert "claim_ids" not in projected
    assert payload["reference_scope"]["allowed_risk_ids"] == [RISK_ID]
    assert payload["reference_scope"]["allowed_conflict_ids"] == [_conflict().conflict_id]


def test_conflict_evidence_is_in_scope_without_becoming_a_risk() -> None:
    conflict = _conflict().model_copy(update={"evidence_ids": ["conflict-evidence-1"]})
    supervisor = LLMFinalSupervisor(llm_provider=None)
    inputs = FinalSupervisionInput(document_supervision=SupervisionResult())
    composed = V04FinalSupervisor().finalize(inputs)
    payload = supervisor._payload(composed, inputs, [conflict], (), (), "low")
    judgement = FinalSupervisionJudgement.model_validate(
        _judgement(
            overall_risk="low",
            key_findings=[
                {
                    "statement": "an unresolved conflict remains",
                    "risk_ids": [],
                    "evidence_ids": ["conflict-evidence-1"],
                }
            ],
            conflict_assessments=[
                {"conflict_id": conflict.conflict_id, "assessment": "requires review"}
            ],
        )
    )

    check = supervisor._validate_scope(judgement, payload)

    assert check["status"] == "passed"
    assert check["supplied_risk_id_count"] == 0
    assert check["cited_evidence_ids"] == ["conflict-evidence-1"]


def test_the_severity_floor_is_the_highest_verified_level() -> None:
    assert severity_floor([]) == "low"
    assert severity_floor([_risk(RiskLevel.MEDIUM), _risk(RiskLevel.CRITICAL)]) == "critical"


def test_a_refused_judgement_is_classified_apart_from_a_transport_failure() -> None:
    """Both degrade honestly, but only one proves the scope guard fired.

    Gate E1 asks for evidence that no out-of-scope reference survived. A provider
    that never answered says nothing about scope; a response the guard refused
    says a great deal, so the two outcomes must not collapse into one status.
    """
    refused = _supervisor(
        _judgement(key_findings=[{"statement": "invented", "risk_ids": ["risk-unknown"]}])
    ).supervise(_inputs())
    unanswered = _supervisor(None).supervise(_inputs())

    assert refused.status is unanswered.status is SupervisionStatus.UNAVAILABLE
    assert refused.outcome is SynthesisOutcome.REJECTED_OUT_OF_SCOPE
    assert unanswered.outcome is SynthesisOutcome.PROVIDER_CALL_FAILED
    assert refused.scope_check["status"] == "failed"
    assert unanswered.scope_check["status"] == "not_applicable"
    assert refused.result.metadata["final_supervision_llm"]["fail_closed"] is True
    assert unanswered.result.metadata["final_supervision_llm"]["fail_closed"] is False


def test_a_refused_response_still_records_the_call_that_produced_it() -> None:
    """A fail-closed run has to stay auditable, not merely absent."""
    refused = _supervisor(
        _judgement(key_findings=[{"statement": "invented", "risk_ids": ["risk-unknown"]}])
    ).supervise(_inputs())
    assert refused.call["provider_name"] == "mock"
    assert refused.call["prompt_version"] == FINAL_SUPERVISION_PROMPT_VERSION


def test_an_absent_provider_is_not_reported_as_a_failed_call() -> None:
    bundle = LLMFinalSupervisor(llm_provider=None).supervise(_inputs())
    assert bundle.outcome is SynthesisOutcome.PROVIDER_NOT_CONFIGURED
    assert bundle.call == {}
    assert bundle.scope_check["status"] == "not_applicable"


def test_an_accepted_judgement_records_what_it_cited_and_what_was_supplied() -> None:
    """"No out-of-scope reference" has to be measured on the run, not asserted."""
    bundle = _supervisor(_judgement()).supervise(_inputs(), conflicts=[_conflict()])
    assert bundle.outcome is SynthesisOutcome.ACCEPTED
    check = bundle.scope_check
    assert check["status"] == "passed"
    assert check["cited_risk_ids"] == [RISK_ID]
    assert check["cited_evidence_ids"] == [EVIDENCE_ID]
    assert check["out_of_scope_reference_count"] == 0
    assert check["supplied_conflict_id_count"] == 1
    assert check["severity_floor_respected"] is True
    assert bundle.result.metadata["final_supervision_llm"]["scope_check"] == check


def test_an_accepted_judgement_retains_the_provider_call_trace() -> None:
    bundle = _supervisor(_judgement()).supervise(_inputs())
    call = bundle.call
    assert call["provider_name"] == "mock"
    assert call["model_name"] == "mock-structured"
    assert call["prompt_version"] == FINAL_SUPERVISION_PROMPT_VERSION
    assert call["latency_ms"] is not None
    assert bundle.result.metadata["final_supervision_llm"]["call"] == call


def test_the_result_carries_no_probability_field() -> None:
    """The composed result exposes no field a renderer could read as a likelihood."""
    bundle = _supervisor(_judgement()).supervise(_inputs())
    for name in type(bundle.result).model_fields:
        assert not any(token in name for token in ("prob", "likelihood", "forecast"))
