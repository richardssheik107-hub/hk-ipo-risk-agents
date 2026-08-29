"""Pure v0.4 pipeline-stage model for the competition-facing runtime.

No Streamlit import lives here so the whole stage model stays testable headlessly;
the Streamlit layer only renders what ``resolve_stages`` returns.

A stage status answers one question only: did this current-case runtime surface
materialize enough governed state to render its product step? It does not claim
that every optional channel is available and it does not claim that project-level
competition gates are closed. Optional Market/Model/LLM assets therefore remain
explicit in the stage summary/metrics instead of turning an otherwise completed
case surface amber.

Formal competition readiness stays in ``docs/V0.4_RELEASE_ACCEPTANCE.md`` and is
never inferred from this presentation model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class StageStatus(StrEnum):
    AVAILABLE = "available"
    # ``COMPLETED`` is a semantic alias used by the stage model.  Its wire/display
    # value intentionally remains ``available`` so older presentation helpers
    # that predate the completed state do not misclassify a finished current-case
    # stage as partial and resurrect stale project-level Gate copy.
    COMPLETED = "available"
    PARTIAL = "partial"
    PENDING_GATE = "pending_gate"


@dataclass(frozen=True)
class Metric:
    label: str
    value: str


@dataclass(frozen=True)
class StageView:
    """One page of the v0.4 chain with runtime-surface state and honest detail."""

    stage_id: str
    ordinal: int
    title: str
    status: StageStatus
    summary: str
    blocking_gate: str | None = None
    blocking_reason: str = ""
    what_appears_when_unblocked: tuple[str, ...] = ()
    metrics: tuple[Metric, ...] = field(default_factory=tuple)

    @property
    def is_available(self) -> bool:
        return self.status in {StageStatus.AVAILABLE, StageStatus.COMPLETED}


def pending_notice(stage: StageView) -> str | None:
    """Return unavailable copy only for a genuinely incomplete stage surface."""
    if stage.is_available:
        return None
    gate = f"pending gate {stage.blocking_gate}" if stage.blocking_gate else "not available"
    return f"**NOT AVAILABLE — {gate}**\n\n{stage.blocking_reason}"


def _runtime_completed(payload: dict[str, object]) -> bool:
    status = str(payload.get("runtime_completion_status") or payload.get("status") or "")
    return status == "completed" or status.startswith("completed_")


def _all_runtime_risks(payload: dict[str, object]) -> list[dict[str, object]]:
    risks: list[dict[str, object]] = []
    for bucket in ("verified_risks", "pending_risks", "rejected_risks"):
        values = payload.get(bucket) or []
        if isinstance(values, list):
            risks.extend(item for item in values if isinstance(item, dict))
    return risks


def _evidence_count(payload: dict[str, object]) -> int:
    return sum(
        len(risk.get("evidence") or [])
        for risk in _all_runtime_risks(payload)
        if isinstance(risk.get("evidence") or [], list)
    )


def _document_analysis(payload: dict[str, object]) -> StageView:
    counts = payload.get("risk_status_counts") or {}
    if payload.get("status") == "failed":
        return StageView(
            stage_id="document_analysis", ordinal=1, title="Document Analysis",
            status=StageStatus.PARTIAL,
            summary="The document workflow stopped before a complete governed result was produced.",
            blocking_reason="inspect the structured runtime errors for the parser/retriever/agent failure",
        )
    if _runtime_completed(payload):
        status = StageStatus.COMPLETED
        summary = "The parser, retriever and financial / legal / business agents completed this current-case document pass."
    else:
        status = StageStatus.PARTIAL
        summary = "The document-analysis surface is ready but no completed current-case runtime is loaded yet."
    return StageView(
        stage_id="document_analysis", ordinal=1, title="Document Analysis",
        status=status,
        summary=summary,
        blocking_reason="run the current case to materialize document-agent results" if not _runtime_completed(payload) else "",
        metrics=(
            Metric("Verified", str(counts.get("verified", 0))),
            Metric("Needs review", str(counts.get("needs_review", 0))),
            Metric("Pending", str(counts.get("pending", 0))),
            Metric("Rejected", str(counts.get("rejected", 0))),
        ) if _runtime_completed(payload) else (),
    )


def _document_features(payload: dict[str, object]) -> StageView:
    if _runtime_completed(payload):
        risks = _all_runtime_risks(payload)
        return StageView(
            stage_id="document_features", ordinal=2, title="Document Risk Features",
            status=StageStatus.COMPLETED,
            summary=(
                "Runtime document-risk features were materialized as governed RiskItems, Evidence and deterministic calculations. "
                "The separate frozen modeling feature matrix is not required for this UI surface."
            ),
            metrics=(
                Metric("Risk items", str(len(risks))),
                Metric("Evidence anchors", str(_evidence_count(payload))),
            ),
        )
    return StageView(
        stage_id="document_features", ordinal=2, title="Document Risk Features",
        status=StageStatus.PARTIAL,
        summary="No completed runtime document-risk projection is present yet.",
        blocking_reason="run a document analysis successfully to materialize RiskItems and Evidence",
        what_appears_when_unblocked=(
            "governed document RiskItems",
            "Evidence anchors and deterministic calculations",
        ),
    )


def _market_features(payload: dict[str, object]) -> StageView:
    market = payload.get("market_context") or {}
    observations = (market.get("observations") or []) if isinstance(market, dict) else []
    if market:
        available = sum(1 for item in observations if item.get("availability") == "available")
        state = str(market.get("status") or "unavailable")
        provenance = market.get("provenance") or {}
        runtime_path = str(provenance.get("runtime_path") or "") if isinstance(provenance, dict) else ""
        if state == "available":
            summary = (
                "The governed point-in-time Market-X stage completed and exposes the available and unavailable observations for this case."
            )
            if runtime_path == "dynamic_pit":
                # This case has no frozen artifact; saying so is the difference
                # between a preloaded demo asset and a generalizable runtime.
                summary = (
                    "This case is outside the frozen Market-X universe, so the stage recomputed the same point-in-time "
                    "contract from the governed prior-IPO history. Available and unavailable observations are both exposed; "
                    "no market value is imputed."
                )
        else:
            reasons = sorted({
                str(item.get("missing_reason") or "")
                for item in observations
                if item.get("availability") != "available"
            } - {""})
            summary = (
                "The Market-X stage completed to an explicit unavailable/partial state. Missing governed observations remain visible with their reasons; "
                "the UI does not impute market values."
            )
            if reasons:
                # Naming the governed reason separates a data boundary from a
                # broken channel, which "unavailable" on its own cannot do.
                summary += " Stated reasons: " + ", ".join(reasons) + "."
        return StageView(
            stage_id="market_features", ordinal=3, title="Market Features",
            status=StageStatus.COMPLETED if _runtime_completed(payload) else StageStatus.AVAILABLE,
            summary=summary,
            metrics=(
                Metric("Observations available", f"{available} of {len(observations)}"),
                Metric("Market channel", state),
            )
            + ((Metric("Market runtime path", runtime_path),) if runtime_path else ()),
        )
    if _runtime_completed(payload):
        return StageView(
            stage_id="market_features", ordinal=3, title="Market Features",
            status=StageStatus.COMPLETED,
            summary=(
                "The current-case runtime completed without a materialized Market-X projection. The product surface remains available and records the market channel as unavailable; no proxy or zero fill is created."
            ),
            metrics=(Metric("Market channel", "unavailable"),),
        )
    return StageView(
        stage_id="market_features", ordinal=3, title="Market Features",
        status=StageStatus.PARTIAL,
        summary="The Market-X product surface is ready, but no current-case runtime result has been supplied yet.",
        blocking_reason="run a competition scenario to materialize governed Market-X state or explicit missingness",
        what_appears_when_unblocked=(
            "prior-IPO context with point-in-time provenance",
            "per-feature availability and missing reasons",
        ),
    )


def _prediction(payload: dict[str, object]) -> StageView:
    prediction = payload.get("prediction") or {}
    model = payload.get("model_prediction") or {}
    metrics: list[Metric] = []
    if prediction:
        metrics.extend((
            Metric("Rule score", str(prediction.get("risk_score", "Unavailable"))),
            Metric("Rule level", str(prediction.get("risk_level", "Unavailable"))),
        ))
    model_available = bool(model and model.get("status", "available") == "available")
    if model_available:
        metrics.append(Metric("Model score", str(model.get("score", "Unavailable"))))
        if model.get("alert") is not None:
            metrics.append(Metric("V2 triage alert", "yes" if model["alert"] else "no"))
    elif _runtime_completed(payload):
        metrics.append(Metric("Model channel", str(model.get("status") or "unavailable")))

    if _runtime_completed(payload):
        summary = (
            "The prediction stage completed for this case. Deterministic rule output is shown when produced; the authentic hash-bound model signal is shown only when present and otherwise remains explicitly unavailable. Neither signal is a probability."
        )
        return StageView(
            stage_id="prediction", ordinal=4, title="Prediction",
            status=StageStatus.COMPLETED,
            summary=summary,
            metrics=tuple(metrics),
        )
    return StageView(
        stage_id="prediction", ordinal=4, title="Prediction",
        status=StageStatus.PARTIAL,
        summary=(
            "The prediction product surface is ready, but no completed current-case runtime is loaded. Any future deterministic rule or uncalibrated model score remains a prioritization signal, not a probability."
        ),
        blocking_reason="run the current case; an authentic model handoff remains optional for rendering the deterministic rule result",
        what_appears_when_unblocked=(
            "deterministic rule score and level",
            "the frozen per-case model score only when an authentic handoff exists",
        ),
        metrics=tuple(metrics),
    )


def _explainability(payload: dict[str, object]) -> StageView:
    model = payload.get("model_prediction") or {}
    model_available = bool(model and model.get("status", "available") == "available")
    drivers = (model.get("drivers") or []) if isinstance(model, dict) else []
    if _runtime_completed(payload):
        summary = (
            "The explainability surface completed with the current-case Document Evidence/Calculation provenance. "
            "Per-case model drivers are additive: they appear only when the authentic model handoff is available and are otherwise reported as unavailable."
        )
        metrics = [Metric("Evidence anchors", str(_evidence_count(payload)))]
        if model_available:
            metrics.append(Metric("Model drivers", str(len(drivers))))
        else:
            metrics.append(Metric("Model drivers", "unavailable"))
        return StageView(
            stage_id="explainability", ordinal=5, title="Evidence / Explainability",
            status=StageStatus.COMPLETED,
            summary=summary,
            metrics=tuple(metrics),
        )
    return StageView(
        stage_id="explainability", ordinal=5, title="Evidence / Explainability",
        status=StageStatus.PARTIAL,
        summary="The Evidence/Explainability surface is ready, but no completed current-case runtime is loaded.",
        blocking_reason="run a case to materialize Evidence and Calculation provenance",
        what_appears_when_unblocked=(
            "Evidence text, physical page and bbox when available",
            "deterministic calculations",
            "per-case model drivers only when an authentic handoff exists",
        ),
    )


def _final_supervisor(payload: dict[str, object]) -> StageView:
    final = payload.get("final_supervision") or {}
    completion = str(payload.get("runtime_completion_status") or "")
    if final:
        states = final.get("channel_states", [])
        available = sum(1 for state in states if state.get("status") == "available")
        degraded = completion in {
            "completed_with_partial_llm",
            "completed_with_deterministic_fallback",
        }
        summary = (
            "The Final Supervisor stage completed with deterministic fallback because the real LLM synthesis did not complete successfully. The fallback state remains explicit and is not counted as real-provider acceptance."
            if degraded
            else "The Final Supervisor stage completed for this case; channel states and unresolved conflicts remain explicit."
        )
        metrics: list[Metric] = [
            Metric("Channels available", f"{available} of {len(states)}"),
            Metric("Unresolved conflicts", str(final.get("metadata", {}).get("unresolved_conflict_count", 0))),
            Metric("Referenced risks", str(len(final.get("referenced_risk_ids", [])))),
        ]
        if degraded:
            metrics.append(Metric("LLM synthesis", "deterministic fallback"))
        return StageView(
            stage_id="final_supervisor", ordinal=6, title="Final Supervisor",
            status=StageStatus.COMPLETED if _runtime_completed(payload) else StageStatus.AVAILABLE,
            summary=summary,
            metrics=tuple(metrics),
        )

    supervision = payload.get("supervision") or {}
    supervision_metrics: tuple[Metric, ...] = ()
    if supervision:
        supervision_metrics = (
            Metric("Duplicate groups", str(len(supervision.get("duplicate_groups", [])))),
            Metric("Conflicts", str(len(supervision.get("conflicts", [])))),
            Metric("Composite findings", str(len(supervision.get("composite_findings", [])))),
        )
        if _runtime_completed(payload):
            return StageView(
                stage_id="final_supervisor", ordinal=6, title="Final Supervisor",
                status=StageStatus.COMPLETED,
                summary=(
                    "The supervision stage completed with the document-scope deterministic supervisor. Cross-channel/LLM synthesis is not materialized in this runtime and remains explicitly unavailable rather than blocking the product surface."
                ),
                metrics=(*supervision_metrics, Metric("Cross-channel LLM", "unavailable")),
            )

    return StageView(
        stage_id="final_supervisor", ordinal=6, title="Final Supervisor",
        status=StageStatus.PARTIAL,
        summary="The Supervisor product surface is ready, but no completed current-case supervision artifact is loaded.",
        blocking_reason="run a scenario with document or cross-channel supervision enabled",
        metrics=supervision_metrics,
    )


def _final_report(payload: dict[str, object]) -> StageView:
    report_sections = payload.get("report_sections") or []
    final = payload.get("final_supervision") or {}
    if report_sections:
        return StageView(
            stage_id="final_report", ordinal=7, title="Final Risk Report",
            status=StageStatus.COMPLETED if _runtime_completed(payload) else StageStatus.AVAILABLE,
            summary=(
                "The current runtime produced the governed final report artifact. Formal competition-readiness gates are tracked separately and do not make this completed case report unavailable."
            ),
            metrics=(Metric("Report sections", str(len(report_sections))),),
        )
    if final:
        return StageView(
            stage_id="final_report", ordinal=7, title="Final Risk Report",
            status=StageStatus.PARTIAL,
            summary="Final Supervisor output exists, but this runtime did not materialize report sections.",
            blocking_reason="report generation did not produce the current case artifact; inspect report-generator diagnostics",
            what_appears_when_unblocked=("the governed current-case report sections",),
        )
    return StageView(
        stage_id="final_report", ordinal=7, title="Final Risk Report",
        status=StageStatus.PARTIAL,
        summary="No current-case final report artifact is loaded yet.",
        blocking_reason="run the report path to materialize the current-case report; project-level competition gates do not block this UI surface",
        what_appears_when_unblocked=(
            "prospectus page to Evidence to RiskItem to market context to model driver to conclusion",
            "run provenance and reproducible current-case report artifacts",
        ),
    )


_RESOLVERS = (
    _document_analysis, _document_features, _market_features,
    _prediction, _explainability, _final_supervisor, _final_report,
)


def resolve_stages(payload: dict[str, object]) -> tuple[StageView, ...]:
    """Build the seven-stage current-case runtime view."""
    return tuple(resolver(payload) for resolver in _RESOLVERS)


def blocking_gates() -> tuple[str, ...]:
    """The frontend current-case chain carries no project-level release gates."""
    return ()
