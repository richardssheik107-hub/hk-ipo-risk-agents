"""The PR-G synthesis contract: it composes, preserves and states limits.

The four purity invariants pinned for the reference implementation in
tests/contract/test_final_supervisor_contract.py are re-run here against the
implementation PR-G actually wires.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from ipo_risk.agents.final_supervisor import UNCALIBRATED_DISCLAIMER, V04FinalSupervisor
from ipo_risk.modeling.frozen_model_evidence import NOT_VALIDATED_PHRASE, load_frozen_cohort_evidence
from ipo_risk.schemas import (
    Evidence,
    EvidenceSourceType,
    RiskCategory,
    RiskConflict,
    RiskItem,
    RiskLevel,
    SupervisionResult,
    VerificationStatus,
)
from ipo_risk.schemas.final_supervision import (
    ChannelStatus,
    FinalSupervisionInput,
    FinalSupervisionResult,
    MarketContextView,
    ModelPredictionView,
    SupervisionChannel,
)

FORBIDDEN_NAME = re.compile(r"prob|likelihood|forecast", re.IGNORECASE)
# docs/V04_ORACLE_GOLD_COVERAGE_AUDIT.md forbids these framings.
FORBIDDEN_FRAMING = re.compile(r"useless|no signal|no value|worthless", re.IGNORECASE)
FROZEN_DIR = Path(__file__).resolve().parents[2] / "reports" / "frozen"


def _risk(risk_id: str, *, evidence: list[Evidence] | None = None) -> RiskItem:
    return RiskItem(
        risk_id=risk_id, risk_code="cash_runway", category=RiskCategory.FINANCIAL,
        risk_type="cash_runway", level=RiskLevel.HIGH, score=70.0,
        conclusion="runway is short", evidence=evidence or [], agent_name="v03_financial",
        verification_status=VerificationStatus.VERIFIED,
    )


def _evidence(evidence_id: str) -> Evidence:
    return Evidence(evidence_id=evidence_id, source_type=EvidenceSourceType.PROSPECTUS,
                    text="cash and cash equivalents", page=42)


def _supervision(*risks: RiskItem, conflicts: list[RiskConflict] | None = None) -> SupervisionResult:
    return SupervisionResult(verified_risks=list(risks), summary="1 verified risk",
                             conflicts=conflicts or [])


@pytest.fixture(scope="module")
def supervisor() -> V04FinalSupervisor:
    return V04FinalSupervisor(load_frozen_cohort_evidence(FROZEN_DIR))


def test_no_evidence_or_risk_is_fabricated(supervisor) -> None:
    supervision = _supervision(_risk("r-1", evidence=[_evidence("e-1")]), _risk("r-2"))
    result = supervisor.finalize(FinalSupervisionInput(document_supervision=supervision))
    assert set(result.referenced_risk_ids) <= {"r-1", "r-2"}
    assert set(result.referenced_evidence_ids) <= {"e-1"}


def test_zero_evidence_input_yields_zero_evidence_references(supervisor) -> None:
    result = supervisor.finalize(FinalSupervisionInput(document_supervision=_supervision(_risk("r-1"))))
    assert result.referenced_evidence_ids == ()


def test_result_cannot_express_a_probability(supervisor) -> None:
    assert not [n for n in FinalSupervisionResult.model_fields if FORBIDDEN_NAME.search(n)]
    assert not [n for n in ModelPredictionView.model_fields if FORBIDDEN_NAME.search(n)]
    result = supervisor.finalize(FinalSupervisionInput())
    assert [key for key in result.metadata if FORBIDDEN_NAME.search(key)] == ["probability_claimed"]
    assert result.metadata["probability_claimed"] is False
    assert result.metadata["creates_no_new_risk"] is True


def test_conflicts_are_preserved_not_resolved(supervisor) -> None:
    """Arbitration is CH-4, after PR-H. PR-G carries conflicts through verbatim."""
    conflict = RiskConflict(risk_code="revenue_semantics", risk_ids=["r-1"],
                            description="product revenue coexists with pre-commercial framing")
    supervision = _supervision(_risk("r-1"), conflicts=[conflict])
    result = supervisor.finalize(FinalSupervisionInput(document_supervision=supervision))
    assert result.conflicts == (conflict,)
    assert result.metadata["unresolved_conflict_count"] == 1


def test_absent_channels_are_disabled_and_name_no_retired_gate(supervisor) -> None:
    result = supervisor.finalize(FinalSupervisionInput(document_supervision=_supervision(_risk("r-1"))))
    states = {state.channel: state for state in result.channel_states}
    for channel in (SupervisionChannel.MARKET, SupervisionChannel.MODEL):
        assert states[channel].status is ChannelStatus.DISABLED
        assert states[channel].blocking_gate is None
    assert result.metadata["blocking_gates"] == []


def test_absent_channels_change_nothing_but_channel_state(supervisor) -> None:
    supervision = _supervision(_risk("r-1", evidence=[_evidence("e-1")]))
    explicit = supervisor.finalize(FinalSupervisionInput(
        document_supervision=supervision, market_context=None, model_prediction=None))
    omitted = supervisor.finalize(FinalSupervisionInput(document_supervision=supervision))
    assert explicit.content_hash() == omitted.content_hash()


def test_missing_market_never_upgrades_the_document_conclusion(supervisor) -> None:
    supervision = _supervision(_risk("r-1"))
    result = supervisor.finalize(FinalSupervisionInput(document_supervision=supervision))
    assert result.summary == supervision.summary
    assert result.composite_findings == ()


def test_uncalibrated_score_carries_its_disclaimer(supervisor) -> None:
    prediction = ModelPredictionView(status=ChannelStatus.AVAILABLE, reason="frozen baseline",
                                     model_name="lightgbm", model_version="v1", score=0.82,
                                     calibration_status="uncalibrated")
    result = supervisor.finalize(FinalSupervisionInput(model_prediction=prediction))
    assert UNCALIBRATED_DISCLAIMER in result.uncertainty_statement
    assert result.metadata["probability_claimed"] is False


def test_uncertainty_carries_the_frozen_cohort_limits(supervisor) -> None:
    """Both frozen ablation intervals span zero, so neither sign may be asserted."""
    statement = supervisor.finalize(FinalSupervisionInput()).uncertainty_statement
    assert statement.count(NOT_VALIDATED_PHRASE) == 2
    assert not FORBIDDEN_FRAMING.search(statement)
    assert result_has_no_bare_sign(statement)


def result_has_no_bare_sign(statement: str) -> bool:
    return "-0.0143" not in statement and "+0.0143" not in statement


def test_composed_channels_are_echoed_for_the_renderer(supervisor) -> None:
    market = MarketContextView(status=ChannelStatus.DISABLED, reason="fixture, not market data")
    result = supervisor.finalize(FinalSupervisionInput(market_context=market))
    assert result.market_context == market
    assert result.model_prediction is None


def test_finalize_is_deterministic(supervisor) -> None:
    inputs = FinalSupervisionInput(document_supervision=_supervision(_risk("r-1", evidence=[_evidence("e-1")])))
    assert supervisor.finalize(inputs).content_hash() == supervisor.finalize(inputs).content_hash()


def test_supervisor_composes_without_frozen_evidence() -> None:
    result = V04FinalSupervisor().finalize(FinalSupervisionInput())
    assert result.metadata["frozen_model_evidence_available"] is False
    assert NOT_VALIDATED_PHRASE not in result.uncertainty_statement
