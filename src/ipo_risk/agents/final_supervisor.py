"""Final Supervisors: pure composition, explicit unavailability.

PR-G is the current formal gate.  Both implementations here compose whatever
channels exist and report the rest as unconfigured, rather than silently omitting
them or filling them in.  Neither creates a risk, cites evidence it was not
given, or presents an uncalibrated score as a probability.

``GatePendingFinalSupervisor`` is the minimal reference kept for degradation and
contract tests.  ``V04FinalSupervisor`` is the one PR-G wires: it additionally
preserves conflicts, echoes the composed channels, and folds the frozen model
cohort evidence into its uncertainty statement.
"""

from __future__ import annotations

from ipo_risk.schemas.final_supervision import (
    ChannelState,
    ChannelStatus,
    FinalSupervisionInput,
    FinalSupervisionResult,
    SupervisionChannel,
)

UNCALIBRATED_DISCLAIMER = "model score is uncalibrated and must not be read as a probability"


def _document_state(inputs: FinalSupervisionInput) -> ChannelState:
    if inputs.document_supervision is None:
        return ChannelState(channel=SupervisionChannel.DOCUMENT, status=ChannelStatus.UNAVAILABLE_ERROR,
                            reason="document supervision did not run")
    return ChannelState(channel=SupervisionChannel.DOCUMENT, status=ChannelStatus.AVAILABLE,
                        reason="v0.3 document supervision result passed through unchanged")


def _channel_state(channel: SupervisionChannel, view, absent_reason: str) -> ChannelState:
    """An absent channel is DISABLED, not gate-blocked.

    PR-B and PR-F are both COMPLETE / FROZEN, so no gate blocks the market or
    model channel any more.  What an absent channel means is that this runtime
    did not configure it -- a capability statement, not a gate statement.
    """
    if view is None:
        return ChannelState(channel=channel, status=ChannelStatus.DISABLED, reason=absent_reason)
    return ChannelState(channel=channel, status=view.status, reason=view.reason,
                        blocking_gate=view.blocking_gate if view.status is not ChannelStatus.AVAILABLE else None)


class GatePendingFinalSupervisor:
    """Minimal reference: composes available channels; never synthesises one."""

    name = "gate_pending"

    def finalize(self, inputs: FinalSupervisionInput) -> FinalSupervisionResult:
        states = (
            _document_state(inputs),
            _channel_state(SupervisionChannel.MARKET, inputs.market_context,
                           "market context is not configured in this runtime"),
            _channel_state(SupervisionChannel.MODEL, inputs.model_prediction,
                           "model prediction is not configured in this runtime"),
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


class V04FinalSupervisor:
    """The PR-G synthesis: composes four channels and states what is missing.

    Everything it emits is copied from its input or from a frozen artifact.  It
    resolves nothing: conflicts raised by the Document Supervisor are carried
    through verbatim, because arbitration is CH-4 and comes after PR-H.
    """

    name = "v04"

    def __init__(self, cohort_evidence=None):
        # Tier-1 frozen PR-F evidence; optional so the supervisor stays testable
        # and still composes when the freeze manifest is not readable.
        self.cohort_evidence = cohort_evidence

    def finalize(self, inputs: FinalSupervisionInput) -> FinalSupervisionResult:
        states = (
            _document_state(inputs),
            _channel_state(SupervisionChannel.MARKET, inputs.market_context,
                           "market context is not configured in this runtime"),
            _channel_state(SupervisionChannel.MODEL, inputs.model_prediction,
                           "model prediction is not configured in this runtime"),
            ChannelState(channel=SupervisionChannel.RULE,
                         status=ChannelStatus.AVAILABLE if inputs.rule_prediction else ChannelStatus.DISABLED,
                         reason="deterministic rule score" if inputs.rule_prediction else "no rule prediction supplied"),
        )
        supervision = inputs.document_supervision
        risks = tuple(supervision.verified_risks) if supervision else ()
        return FinalSupervisionResult(
            summary=supervision.summary if supervision else "no document supervision available",
            channel_states=states,
            # Copied from the input; nothing is minted here.
            referenced_risk_ids=tuple(risk.risk_id for risk in risks),
            referenced_evidence_ids=tuple(
                dict.fromkeys(item.evidence_id for risk in risks for item in risk.evidence)),
            composite_findings=tuple(supervision.composite_findings) if supervision else (),
            conflicts=tuple(supervision.conflicts) if supervision else (),
            market_context=inputs.market_context,
            model_prediction=inputs.model_prediction,
            uncertainty_statement=self._uncertainty(inputs, states),
            metadata={
                "classification": "SUPERVISORY_SYNTHESIS",
                "creates_no_new_risk": True,
                "probability_claimed": False,
                "blocking_gates": [],
                "unresolved_conflict_count": len(supervision.conflicts) if supervision else 0,
                "frozen_model_evidence_available": self.cohort_evidence is not None,
            },
        )

    def _uncertainty(self, inputs: FinalSupervisionInput, states: tuple[ChannelState, ...]) -> str:
        """Deterministic, fixed-order: absences, then calibration, then cohort limits."""
        parts = [
            f"{state.channel.value} channel {state.status.value}: {state.reason}"
            for state in states
            if state.status is not ChannelStatus.AVAILABLE
        ]
        prediction = inputs.model_prediction
        if prediction is not None and prediction.calibration_status == "uncalibrated":
            parts.append(UNCALIBRATED_DISCLAIMER)
        if self.cohort_evidence is not None:
            # Cohort-level, never a claim about the case in hand.  Where the
            # frozen bootstrap interval spans zero the sign is suppressed.
            parts.extend(
                f"frozen model cohort evidence: {statement}"
                for statement in self.cohort_evidence.statements()
            )
        if not parts:
            parts.append("all channels contributed; residual uncertainty is documented per risk")
        return "; ".join(parts)
