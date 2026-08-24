"""PR-G preparation contract: the Final Supervisor composes, it never invents.

PR-G is NOT STARTED.  These tests pin the purity invariants and the honest
degradation path so a later implementation cannot quietly relax them.
"""
from __future__ import annotations

import dataclasses
import re

import pytest

from ipo_risk.agents.final_supervisor import GatePendingFinalSupervisor
from ipo_risk.agents.market_context import GatePendingMarketContextProvider
from ipo_risk.core.config import Settings
from ipo_risk.core.container import default_registry
from ipo_risk.core.config import ComponentConfigurationError
from ipo_risk.schemas import (
    Evidence,
    EvidenceSourceType,
    RiskCategory,
    RiskItem,
    RiskLevel,
    SupervisionResult,
    VerificationStatus,
)
from ipo_risk.schemas.final_supervision import (
    ChannelStatus,
    FinalSupervisionInput,
    FinalSupervisionResult,
    ModelPredictionView,
    SupervisionChannel,
)

FORBIDDEN_NAME = re.compile(r"prob|likelihood|forecast", re.IGNORECASE)


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


def _supervision(*risks: RiskItem) -> SupervisionResult:
    return SupervisionResult(verified_risks=list(risks), summary="1 verified risk")


def test_no_evidence_or_risk_is_fabricated() -> None:
    supervision = _supervision(_risk("r-1", evidence=[_evidence("e-1")]), _risk("r-2"))
    result = GatePendingFinalSupervisor().finalize(FinalSupervisionInput(document_supervision=supervision))
    assert set(result.referenced_risk_ids) <= {"r-1", "r-2"}
    assert set(result.referenced_evidence_ids) <= {"e-1"}


def test_zero_evidence_input_yields_zero_evidence_references() -> None:
    result = GatePendingFinalSupervisor().finalize(
        FinalSupervisionInput(document_supervision=_supervision(_risk("r-1"))))
    assert result.referenced_evidence_ids == ()
    assert result.referenced_risk_ids == ("r-1",)


def test_result_cannot_express_a_probability() -> None:
    """Guards the shape itself, so a probability field cannot be reintroduced by accident."""
    assert not [name for name in FinalSupervisionResult.model_fields if FORBIDDEN_NAME.search(name)]
    assert not [name for name in ModelPredictionView.model_fields if FORBIDDEN_NAME.search(name)]
    result = GatePendingFinalSupervisor().finalize(FinalSupervisionInput())
    # "probability_claimed" is the explicit negative flag, not a probability value.
    assert [key for key in result.metadata if FORBIDDEN_NAME.search(key)] == ["probability_claimed"]
    assert result.metadata["probability_claimed"] is False
    assert result.metadata["creates_no_new_risk"] is True


def test_uncalibrated_score_carries_its_disclaimer() -> None:
    prediction = ModelPredictionView(status=ChannelStatus.AVAILABLE, reason="frozen baseline",
                                     model_name="logistic", model_version="v1", score=0.82,
                                     calibration_status="uncalibrated")
    result = GatePendingFinalSupervisor().finalize(FinalSupervisionInput(model_prediction=prediction))
    assert "not be read as a probability" in result.uncertainty_statement
    assert result.metadata["probability_claimed"] is False


def test_missing_channels_are_reported_as_pending_gates() -> None:
    """Today's real state: no Market-X and no frozen model exist."""
    result = GatePendingFinalSupervisor().finalize(
        FinalSupervisionInput(document_supervision=_supervision(_risk("r-1"))))
    pending = {state.channel: state.blocking_gate for state in result.channel_states
               if state.status is ChannelStatus.PENDING_GATE}
    assert pending == {SupervisionChannel.MARKET: "PR-B", SupervisionChannel.MODEL: "PR-F"}
    assert result.metadata["blocking_gates"] == ["PR-B", "PR-F"]


def test_absent_channels_change_nothing_but_channel_state() -> None:
    supervision = _supervision(_risk("r-1", evidence=[_evidence("e-1")]))
    explicit_none = GatePendingFinalSupervisor().finalize(
        FinalSupervisionInput(document_supervision=supervision, market_context=None, model_prediction=None))
    omitted = GatePendingFinalSupervisor().finalize(FinalSupervisionInput(document_supervision=supervision))
    assert explicit_none.content_hash() == omitted.content_hash()
    assert explicit_none.referenced_risk_ids == omitted.referenced_risk_ids == ("r-1",)


def test_missing_market_never_upgrades_the_document_conclusion() -> None:
    supervision = _supervision(_risk("r-1"))
    result = GatePendingFinalSupervisor().finalize(FinalSupervisionInput(document_supervision=supervision))
    assert result.summary == supervision.summary
    assert result.composite_findings == ()


def test_finalize_is_deterministic() -> None:
    inputs = FinalSupervisionInput(document_supervision=_supervision(_risk("r-1", evidence=[_evidence("e-1")])))
    supervisor = GatePendingFinalSupervisor()
    assert supervisor.finalize(inputs).content_hash() == supervisor.finalize(inputs).content_hash()


def test_market_context_provider_reports_the_blocking_gate() -> None:
    view = GatePendingMarketContextProvider().context(profile=None)
    assert view.status is ChannelStatus.PENDING_GATE
    assert view.blocking_gate == "PR-B"
    assert view.observations == ()


def test_registry_exposes_the_contracts_but_nothing_wires_them() -> None:
    registry = default_registry()
    assert registry.create("final_supervisor", "gate_pending").name == "gate_pending"
    assert registry.create("market_context", "gate_pending").name == "gate_pending"
    with pytest.raises(ComponentConfigurationError):
        registry.create("final_supervisor", "v04")


def test_settings_has_no_final_supervisor_field_before_pr_g() -> None:
    """Guards against wiring PR-G ahead of its gate.

    When PR-G formally starts, this test is deleted in the same change that adds
    the Settings field and the create_workflow wiring.
    """
    names = {field.name for field in dataclasses.fields(Settings)}
    assert "final_supervisor" not in names
    assert "market_context" not in names
