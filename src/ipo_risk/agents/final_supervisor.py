"""Gate-pending Final Supervisor: pure composition, explicit unavailability.

PR-G is the current formal gate.  This gate-pending implementation is its
starting reference: it composes whatever channels exist, and reports the rest as
blocked by a named gate rather than silently omitting them or filling them in.
"""

from __future__ import annotations

from ipo_risk.agents.market_context import PENDING_MARKET_GATE
from ipo_risk.schemas.final_supervision import (
    ChannelState,
    ChannelStatus,
    FinalSupervisionInput,
    FinalSupervisionResult,
    SupervisionChannel,
)

PENDING_MODEL_GATE = "PR-F"
UNCALIBRATED_DISCLAIMER = "model score is uncalibrated and must not be read as a probability"


def _document_state(inputs: FinalSupervisionInput) -> ChannelState:
    if inputs.document_supervision is None:
        return ChannelState(channel=SupervisionChannel.DOCUMENT, status=ChannelStatus.UNAVAILABLE_ERROR,
                            reason="document supervision did not run")
    return ChannelState(channel=SupervisionChannel.DOCUMENT, status=ChannelStatus.AVAILABLE,
                        reason="v0.3 document supervision result passed through unchanged")


def _channel_state(channel: SupervisionChannel, view, gate: str, absent_reason: str) -> ChannelState:
    if view is None:
        return ChannelState(channel=channel, status=ChannelStatus.PENDING_GATE, reason=absent_reason, blocking_gate=gate)
    return ChannelState(channel=channel, status=view.status, reason=view.reason,
                        blocking_gate=view.blocking_gate if view.status is not ChannelStatus.AVAILABLE else None)


class GatePendingFinalSupervisor:
    """Composes available channels; never synthesises a missing one."""

    name = "gate_pending"

    def finalize(self, inputs: FinalSupervisionInput) -> FinalSupervisionResult:
        states = (
            _document_state(inputs),
            _channel_state(SupervisionChannel.MARKET, inputs.market_context, PENDING_MARKET_GATE,
                           "governed pre-listing Market-X is not built yet"),
            _channel_state(SupervisionChannel.MODEL, inputs.model_prediction, PENDING_MODEL_GATE,
                           "no frozen prediction model exists yet"),
            ChannelState(channel=SupervisionChannel.RULE,
                         status=ChannelStatus.AVAILABLE if inputs.rule_prediction else ChannelStatus.DISABLED,
                         reason="deterministic rule score" if inputs.rule_prediction else "no rule prediction supplied"),
        )
        supervision = inputs.document_supervision
        risks = tuple(supervision.verified_risks) if supervision else ()
        # Every id below is copied from the input; nothing is minted here.
        risk_ids = tuple(risk.risk_id for risk in risks)
        evidence_ids = tuple(dict.fromkeys(item.evidence_id for risk in risks for item in risk.evidence))
        findings = tuple(supervision.composite_findings) if supervision else ()
        blocked = tuple(state for state in states if state.status is ChannelStatus.PENDING_GATE)
        return FinalSupervisionResult(
            summary=supervision.summary if supervision else "no document supervision available",
            channel_states=states,
            referenced_risk_ids=risk_ids,
            referenced_evidence_ids=evidence_ids,
            composite_findings=findings,
            uncertainty_statement=self._uncertainty(inputs, blocked),
            metadata={
                "classification": "SUPERVISORY_SYNTHESIS",
                "creates_no_new_risk": True,
                "probability_claimed": False,
                "blocking_gates": [state.blocking_gate for state in blocked if state.blocking_gate],
            },
        )

    @staticmethod
    def _uncertainty(inputs: FinalSupervisionInput, blocked: tuple[ChannelState, ...]) -> str:
        parts = [
            f"{state.channel.value} channel unavailable, blocked by {state.blocking_gate}"
            for state in blocked
        ]
        prediction = inputs.model_prediction
        if prediction is not None and prediction.calibration_status == "uncalibrated":
            parts.append(UNCALIBRATED_DISCLAIMER)
        if not parts:
            parts.append("all channels contributed; residual uncertainty is documented per risk")
        return "; ".join(parts)
