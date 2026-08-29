"""Conflict detection is deterministic; the re-check is bounded and honest.

The detector must produce the same conflict identities for the same run, name two
real producers per conflict, and never mint a risk or evidence id.  The re-check
must stay at one attempt, distinguish a retrieval gap from an extraction gap, and
report a conflict it cannot settle as unresolved rather than narrating it away.
"""

from __future__ import annotations

import pytest

from ipo_risk.agents.conflict_detection import (
    CONFLICT_POLICY_VERSION,
    RULE_AGENT_VERIFIER,
    RULE_DOCUMENT_MARKET,
    RULE_DOCUMENT_MODEL,
    RULE_DOCUMENT_RULE_SEVERITY,
    RULE_UNRESOLVED_CLAIM,
    ConflictDetector,
)
from ipo_risk.agents.targeted_recheck import TargetedRecheckRunner, conflict_rule
from ipo_risk.schemas import (
    ComponentDiagnostic,
    DiagnosticCode,
    DocumentChunk,
    Evidence,
    PredictionResult,
    RiskCategory,
    RiskItem,
    RiskLevel,
    SupervisionResult,
    VerificationResult,
    VerificationStatus,
)
from ipo_risk.schemas.competition_runtime import ConflictStatus, RecheckStatus
from ipo_risk.schemas.final_supervision import (
    ChannelStatus,
    MarketContextView,
    ModelDriver,
    ModelPredictionView,
)

CASE = "ipo_2024_02410"
RUN = "run-1"


def _risk(risk_id: str, *, level=RiskLevel.HIGH, status=VerificationStatus.VERIFIED,
          code="cash_runway", agent="financial", evidence_ids=("e1",)) -> RiskItem:
    return RiskItem(
        risk_id=risk_id, risk_code=code, category=RiskCategory.FINANCIAL, risk_type=code,
        level=level, score=70, conclusion=code, agent_name=agent, verification_status=status,
        evidence=[Evidence(evidence_id=item, text=f"text {item}", page=1) for item in evidence_ids],
    )


def _detect(**kwargs):
    return ConflictDetector().detect(case_id=CASE, run_id=RUN, **kwargs)


def test_conflict_identity_is_deterministic_across_runs() -> None:
    pending = [_risk("r1", status=VerificationStatus.PENDING)]
    first = _detect(unsettled_risks=pending)
    second = _detect(unsettled_risks=pending)
    assert [item.conflict_id for item in first] == [item.conflict_id for item in second]
    assert first[0].conflict_id.startswith(f"conflict:{RUN}:{RULE_AGENT_VERIFIER}:")


def test_every_conflict_names_the_policy_that_produced_it() -> None:
    conflicts = _detect(unsettled_risks=[_risk("r1", status=VerificationStatus.NEEDS_REVIEW)])
    assert conflicts[0].claim_ids[0] == f"policy:{CONFLICT_POLICY_VERSION}"
    assert conflict_rule(conflicts[0]) == RULE_AGENT_VERIFIER


def test_a_conflict_copies_ids_and_never_mints_them() -> None:
    conflicts = _detect(unsettled_risks=[_risk("r1", status=VerificationStatus.PENDING,
                                               evidence_ids=("e1", "e2"))])
    assert conflicts[0].risk_ids == ["r1"]
    assert conflicts[0].evidence_ids == ["e1", "e2"]
    assert len(set(conflicts[0].involved_agents)) == 2


def test_a_settled_risk_raises_no_agent_verifier_conflict() -> None:
    assert _detect(unsettled_risks=[_risk("r1", status=VerificationStatus.VERIFIED)]) == ()


def test_a_diagnostic_with_evidence_but_no_asserted_risk_is_a_coverage_conflict() -> None:
    diagnostic = ComponentDiagnostic(
        risk_code="redemption_rights", code=DiagnosticCode.EXTRACTION_FAILED,
        message="structured extraction failed", evidence_ids=["e9", "e10"],
    )
    conflicts = _detect(agent_diagnostics=[("legal", diagnostic)])
    assert len(conflicts) == 1
    assert conflict_rule(conflicts[0]) == RULE_UNRESOLVED_CLAIM
    assert conflicts[0].evidence_ids == ["e9", "e10"]


def test_a_diagnostic_whose_risk_code_did_reach_the_report_is_not_a_conflict() -> None:
    diagnostic = ComponentDiagnostic(
        risk_code="cash_runway", code=DiagnosticCode.NEEDS_REVIEW, message="x", evidence_ids=["e1"],
    )
    supervision = SupervisionResult(verified_risks=[_risk("r1")], summary="s")
    assert _detect(document_supervision=supervision, agent_diagnostics=[("financial", diagnostic)]) == ()


def test_a_diagnostic_without_evidence_is_not_a_conflict() -> None:
    diagnostic = ComponentDiagnostic(
        risk_code="revenue_growth", code=DiagnosticCode.EVIDENCE_NOT_FOUND, message="none",
    )
    assert _detect(agent_diagnostics=[("financial", diagnostic)]) == ()


def test_a_severe_document_risk_against_a_low_rule_score_is_a_conflict() -> None:
    supervision = SupervisionResult(verified_risks=[_risk("r1", level=RiskLevel.CRITICAL)], summary="s")
    prediction = PredictionResult(model_name="rule", risk_score=10, risk_level=RiskLevel.LOW)
    conflicts = _detect(document_supervision=supervision, rule_prediction=prediction)
    assert [conflict_rule(item) for item in conflicts] == [RULE_DOCUMENT_RULE_SEVERITY]


def test_an_agreeing_rule_score_raises_nothing() -> None:
    supervision = SupervisionResult(verified_risks=[_risk("r1", level=RiskLevel.CRITICAL)], summary="s")
    prediction = PredictionResult(model_name="rule", risk_score=90, risk_level=RiskLevel.CRITICAL)
    assert _detect(document_supervision=supervision, rule_prediction=prediction) == ()


def _market(risk_level: str) -> MarketContextView:
    return MarketContextView(
        status=ChannelStatus.AVAILABLE, reason="governed", observations=(),
        provenance={"market_intelligence": {"risk_level": risk_level}},
    )


def test_a_high_market_risk_with_no_severe_document_risk_is_a_conflict() -> None:
    conflicts = _detect(document_supervision=SupervisionResult(summary="s"), market_context=_market("high"))
    assert [conflict_rule(item) for item in conflicts] == [RULE_DOCUMENT_MARKET]


def test_an_unavailable_market_channel_raises_no_market_conflict() -> None:
    view = MarketContextView(status=ChannelStatus.UNAVAILABLE_ERROR, reason="io error")
    assert _detect(market_context=view) == ()


def test_a_model_driver_pointing_against_the_document_is_a_conflict() -> None:
    view = ModelPredictionView(
        status=ChannelStatus.AVAILABLE, reason="frozen handoff", score=0.4,
        drivers=(ModelDriver(feature="prior_ipo_break_rate", component="market",
                             shap_value=0.7, direction="increases"),),
    )
    conflicts = _detect(document_supervision=SupervisionResult(summary="s"), model_prediction=view)
    assert [conflict_rule(item) for item in conflicts] == [RULE_DOCUMENT_MODEL]


class _StubRetriever:
    name = "stub"

    def __init__(self, evidence: dict[str, list[Evidence]]) -> None:
        self.evidence = evidence
        self.calls: list[str] = []

    def retrieve(self, chunks, query, limit=3):
        self.calls.append(query)
        return self.evidence.get(query, [])[:limit]


class _StubVerifier:
    name = "stub_verifier"

    def __init__(self, settle: bool) -> None:
        self.settle = settle

    def verify(self, risks, evidence_by_code):
        if self.settle:
            return VerificationResult(verified_risks=list(risks))
        return VerificationResult(pending_risks=list(risks))


def _chunks() -> list[DocumentChunk]:
    return [DocumentChunk(document_id="d", chunk_id="c1", page=1, text="body")]


def test_a_settled_challenge_resolves_the_conflict_with_one_attempt() -> None:
    pending = _risk("r1", status=VerificationStatus.PENDING)
    conflicts = _detect(unsettled_risks=[pending])
    retriever = _StubRetriever({"cash_runway": [Evidence(evidence_id="e_new", text="new", page=2)]})
    updated, outcomes = TargetedRecheckRunner(retriever, _StubVerifier(True)).run(
        conflicts, case_id=CASE, run_id=RUN, chunks=_chunks(), risks=[pending]
    )
    assert updated[0].status is ConflictStatus.RESOLVED
    assert outcomes[0].new_evidence_ids == ("e_new",)
    assert outcomes[0].request.max_attempts == 1
    assert outcomes[0].request.status is RecheckStatus.COMPLETED
    assert retriever.calls == ["cash_runway"]


def test_an_unsettled_challenge_with_new_evidence_is_only_partially_resolved() -> None:
    pending = _risk("r1", status=VerificationStatus.PENDING)
    conflicts = _detect(unsettled_risks=[pending])
    retriever = _StubRetriever({"cash_runway": [Evidence(evidence_id="e_new", text="new", page=2)]})
    updated, _ = TargetedRecheckRunner(retriever, _StubVerifier(False)).run(
        conflicts, case_id=CASE, run_id=RUN, chunks=_chunks(), risks=[pending]
    )
    assert updated[0].status is ConflictStatus.PARTIALLY_RESOLVED


def test_no_new_evidence_and_no_ruling_change_stays_unresolved() -> None:
    pending = _risk("r1", status=VerificationStatus.PENDING)
    conflicts = _detect(unsettled_risks=[pending])
    updated, _ = TargetedRecheckRunner(_StubRetriever({}), _StubVerifier(False)).run(
        conflicts, case_id=CASE, run_id=RUN, chunks=_chunks(), risks=[pending]
    )
    assert updated[0].status is ConflictStatus.UNRESOLVED


@pytest.mark.parametrize(
    "found, expected, classification",
    [
        ([Evidence(evidence_id="e_new", text="n", page=2)], ConflictStatus.PARTIALLY_RESOLVED, "retrieval_gap"),
        ([], ConflictStatus.UNRESOLVED, "extraction_gap"),
    ],
)
def test_a_coverage_recheck_separates_a_retrieval_gap_from_an_extraction_gap(
    found, expected, classification
) -> None:
    diagnostic = ComponentDiagnostic(
        risk_code="redemption_rights", code=DiagnosticCode.EXTRACTION_FAILED,
        message="failed", evidence_ids=["e_old"],
    )
    conflicts = _detect(agent_diagnostics=[("legal", diagnostic)])
    retriever = _StubRetriever({"redemption_rights": found})
    updated, outcomes = TargetedRecheckRunner(retriever, _StubVerifier(True)).run(
        conflicts, case_id=CASE, run_id=RUN, chunks=_chunks()
    )
    assert updated[0].status is expected
    assert outcomes[0].trace_events[0].details["gap_classification"] == classification


def test_a_cross_channel_conflict_is_reported_unresolved_not_dropped() -> None:
    supervision = SupervisionResult(verified_risks=[_risk("r1", level=RiskLevel.CRITICAL)], summary="s")
    prediction = PredictionResult(model_name="rule", risk_score=10, risk_level=RiskLevel.LOW)
    conflicts = _detect(document_supervision=supervision, rule_prediction=prediction)
    updated, outcomes = TargetedRecheckRunner(_StubRetriever({}), _StubVerifier(True)).run(
        conflicts, case_id=CASE, run_id=RUN, chunks=_chunks()
    )
    assert updated[0].status is ConflictStatus.UNRESOLVED
    assert "outside the document" in updated[0].resolution_note
    event = outcomes[0].trace_events[0]
    assert event.event_type.value == "recheck"
    assert "not document-actionable" in event.details["no_evidence_reason"]


def test_the_recheck_budget_bounds_how_many_conflicts_are_attempted() -> None:
    pending = [
        _risk(f"r{index}", status=VerificationStatus.PENDING, code=f"code_{index}")
        for index in range(4)
    ]
    conflicts = _detect(unsettled_risks=pending)
    assert len(conflicts) == 4
    updated, outcomes = TargetedRecheckRunner(
        _StubRetriever({}), _StubVerifier(True), max_conflicts=2
    ).run(conflicts, case_id=CASE, run_id=RUN, chunks=_chunks(), risks=pending)
    assert len(outcomes) == 2
    assert "budget" in updated[-1].resolution_note


def test_a_failing_verifier_leaves_the_conflict_unresolved_rather_than_crashing() -> None:
    class _Boom:
        name = "boom"

        def verify(self, risks, evidence_by_code):
            raise RuntimeError("verifier down")

    pending = _risk("r1", status=VerificationStatus.PENDING)
    conflicts = _detect(unsettled_risks=[pending])
    updated, outcomes = TargetedRecheckRunner(_StubRetriever({}), _Boom()).run(
        conflicts, case_id=CASE, run_id=RUN, chunks=_chunks(), risks=[pending]
    )
    assert updated[0].status is ConflictStatus.UNRESOLVED
    assert "Verifier failed" in updated[0].resolution_note
    assert outcomes[0].trace_events[-1].status == "failed"
