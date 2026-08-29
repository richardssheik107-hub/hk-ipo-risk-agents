"""Submission-sprint regression tests for the v2 targeted re-check budget."""
from __future__ import annotations

from ipo_risk.agents.conflict_detection import (
    RULE_AGENT_VERIFIER,
    RULE_DOCUMENT_RULE_SEVERITY,
    ConflictDetector,
    conflict_rule,
)
from ipo_risk.agents.targeted_recheck import RECHECK_POLICY_VERSION, TargetedRecheckRunner
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

CASE = "ipo_2024_demo"
RUN = "run-budget-v2"


class _EmptyRetriever:
    name = "empty"

    def retrieve(self, chunks, query, limit=3):
        return []


class _PendingVerifier:
    name = "pending"

    def verify(self, risks, evidence_by_code):
        return VerificationResult(pending_risks=list(risks))


def _chunks() -> list[DocumentChunk]:
    return [DocumentChunk(document_id="d", chunk_id="c1", page=1, text="body")]


def _risk() -> RiskItem:
    return RiskItem(
        risk_id="r1",
        risk_code="cash_runway",
        category=RiskCategory.FINANCIAL,
        risk_type="cash_runway",
        level=RiskLevel.HIGH,
        score=70,
        conclusion="cash runway",
        agent_name="financial",
        verification_status=VerificationStatus.PENDING,
        evidence=[Evidence(evidence_id="e1", text="text", page=1)],
    )


def _coverage_conflicts(count: int):
    diagnostics = [
        (
            "financial",
            ComponentDiagnostic(
                risk_code=f"coverage_code_{index:02d}",
                code=DiagnosticCode.EXTRACTION_FAILED,
                message="bounded evidence held but no risk emitted",
                evidence_ids=[f"e{index:02d}"],
            ),
        )
        for index in range(count)
    ]
    return ConflictDetector().detect(
        case_id=CASE,
        run_id=RUN,
        agent_diagnostics=diagnostics,
    )


def test_submission_sprint_default_allows_six_actionable_conflicts() -> None:
    runner = TargetedRecheckRunner(_EmptyRetriever(), _PendingVerifier())
    assert RECHECK_POLICY_VERSION == "v04_e_recheck_policy_v2"
    assert runner.max_conflicts == 12
    assert runner.evidence_limit == 5

    conflicts = _coverage_conflicts(6)
    updated, outcomes = runner.run(
        conflicts,
        case_id=CASE,
        run_id=RUN,
        chunks=_chunks(),
    )

    assert len(conflicts) == 6
    assert len(outcomes) == 6
    assert all(outcome.request.max_attempts == 1 for outcome in outcomes)
    assert all("budget" not in item.resolution_note for item in updated)


def test_cross_channel_conflict_does_not_consume_document_budget() -> None:
    risk = _risk()
    detector = ConflictDetector()
    document_conflict = detector.detect(
        case_id=CASE,
        run_id=RUN,
        unsettled_risks=[risk],
    )[0]
    cross_channel_conflict = detector.detect(
        case_id=CASE,
        run_id=RUN,
        document_supervision=SupervisionResult(
            verified_risks=[risk.model_copy(update={"verification_status": VerificationStatus.VERIFIED})],
            summary="s",
        ),
        rule_prediction=PredictionResult(
            model_name="rule",
            risk_score=10,
            risk_level=RiskLevel.LOW,
        ),
    )[0]

    assert conflict_rule(document_conflict) == RULE_AGENT_VERIFIER
    assert conflict_rule(cross_channel_conflict) == RULE_DOCUMENT_RULE_SEVERITY

    updated, outcomes = TargetedRecheckRunner(
        _EmptyRetriever(), _PendingVerifier(), max_conflicts=1
    ).run(
        (cross_channel_conflict, document_conflict),
        case_id=CASE,
        run_id=RUN,
        chunks=_chunks(),
        risks=[risk],
    )

    assert len(outcomes) == 2
    assert "outside the document" in updated[0].resolution_note
    assert "budget" not in updated[1].resolution_note


def test_more_than_twelve_actionable_conflicts_remains_bounded() -> None:
    conflicts = _coverage_conflicts(13)
    updated, outcomes = TargetedRecheckRunner(
        _EmptyRetriever(), _PendingVerifier()
    ).run(
        conflicts,
        case_id=CASE,
        run_id=RUN,
        chunks=_chunks(),
    )

    assert len(outcomes) == 12
    assert "budget of 12 actionable conflict" in updated[-1].resolution_note
