"""v0.4 AI workflow adapter for governed Market Intelligence.

This is an integration-only layer.  It keeps the frozen/legacy workflow graph
unchanged, enriches the existing governed MarketContext after it is loaded, and
hands the enriched context to the existing Final Supervisor.  Market facts stay
owned by the governed provider and deterministic Skills; the LLM can only
interpret the bounded context exposed by ``MarketIntelligenceAgent``.
"""

from __future__ import annotations

from ipo_risk.schemas import LogStatus
from ipo_risk.schemas.final_supervision import ChannelStatus
from ipo_risk.workflows.enhanced_v2 import EnhancedV2Workflow


class V04AIWorkflow(EnhancedV2Workflow):
    """Enhanced-v2 plus the competition Market Intelligence handoff."""

    def __init__(self, *args, market_intelligence_agent=None, **kwargs) -> None:
        self.market_intelligence_agent = market_intelligence_agent
        super().__init__(*args, **kwargs)

    def explain_market(self, state):
        """Load governed MarketContext, then enrich it without changing facts."""

        base = super().explain_market(state)
        if self.market_intelligence_agent is None:
            return base

        view = base.get("market_context_view")
        diagnostics = dict(base.get("component_diagnostics", {}))
        if view is None or view.status is not ChannelStatus.AVAILABLE:
            diagnostics["market_intelligence"] = {
                "status": "skipped_context_unavailable",
                "reason": (
                    view.reason
                    if view is not None
                    else "governed MarketContext did not produce a usable view"
                ),
            }
            return {**base, "component_diagnostics": diagnostics}

        try:
            bundle = self.market_intelligence_agent.analyze(
                view,
                run_id=state["request"].request_id,
            )
            intelligence_diagnostics = {
                "status": "completed",
                "interpretation_status": bundle.interpretation_status.value,
                "interpretation_reason": bundle.interpretation_reason,
                "ipo_heat": bundle.ipo_heat.model_dump(mode="json"),
                "market_regime": bundle.market_regime.model_dump(mode="json"),
                "interpretation": (
                    bundle.interpretation.model_dump(mode="json")
                    if bundle.interpretation is not None
                    else None
                ),
                "agent_result": bundle.agent_result.model_dump(mode="json"),
                "trace_events": [
                    event.model_dump(mode="json") for event in bundle.trace_events
                ],
            }
            diagnostics["market_intelligence"] = intelligence_diagnostics
            return {
                **base,
                "market_context_view": bundle.market_context,
                "component_diagnostics": diagnostics,
                "agent_logs": [
                    *base.get("agent_logs", []),
                    self._log(
                        state,
                        "market_intelligence",
                        "interpret_market_context",
                        text=(
                            "governed MarketContext enriched; "
                            f"LLM interpretation {bundle.interpretation_status.value}"
                        ),
                        metadata=intelligence_diagnostics,
                    ),
                ],
            }
        except Exception as exc:
            # The deterministic governed MarketContext remains usable.  An
            # unexpected integration failure is visible and makes the analysis
            # partial, but never erases or fabricates market facts.
            error = self._error("market_intelligence", exc)
            failure = {
                "status": "failed",
                "reason": str(exc),
                "deterministic_market_context_retained": True,
            }
            diagnostics["market_intelligence"] = failure
            return {
                **base,
                "market_context_view": view,
                "component_diagnostics": diagnostics,
                "errors": [*base.get("errors", []), error],
                "agent_logs": [
                    *base.get("agent_logs", []),
                    self._log(
                        state,
                        "market_intelligence",
                        "interpret_market_context",
                        LogStatus.FAILED,
                        str(exc),
                        error,
                        failure,
                    ),
                ],
            }
