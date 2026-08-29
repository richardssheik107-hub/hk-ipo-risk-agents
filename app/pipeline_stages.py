"""Pure v0.4 pipeline-stage model for the PR-H end-to-end skeleton.

No Streamlit import lives here so the whole stage model stays testable headlessly;
the Streamlit layer only renders what ``resolve_stages`` returns.

The governing rule: a stage that is not AVAILABLE renders no fabricated number.
A missing runtime asset is described as a capability/runtime limitation; already
frozen gates must never be reported as if they still block the chain.

Formal competition readiness is intentionally separate from per-run availability:
a successfully materialized runtime stage is green even while project-level
acceptance gates remain open elsewhere in the product.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

GATE_E2E = "PR-H"


class StageStatus(StrEnum):
    AVAILABLE = "available"
    PARTIAL = "partial"
    PENDING_GATE = "pending_gate"


@dataclass(frozen=True)
class Metric:
    label: str
    value: str


@dataclass(frozen=True)
class StageView:
    """One page of the v0.4 chain, with its honest availability state."""

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
        return self.status is StageStatus.AVAILABLE


def pending_notice(stage: StageView) -> str | None:
    """Return unavailable copy only for a genuinely unavailable/partial stage."""
    if stage.status is StageStatus.AVAILABLE:
        return None
    gate = f"pending gate {stage.blocking_gate}" if stage.blocking_gate else "not available"
    return f"**NOT AVAILABLE — {gate}**\n\n{stage.blocking_reason}"


def _all_runtime_risks(payload: dict[str, object]) -> list[dict[str, object]]:
    risks: list[dict[str, object]] = []
    for bucket in ("verified_risks", "pending_risks", "rejected_risks"):
        values = payload.get(bucket) or []
        if isinstance(values, list):
            risks.extend(item for item in values if isinstance(item, dict))
    return risks


def _document_analysis(payload: dict[str, object]) -> StageView:
    counts = payload.get("risk_status_counts") or {}
    if payload.get("status") == "failed":
        return StageView(
            stage_id="document_analysis", ordinal=1, title="Document Analysis",
            status=StageStatus.PARTIAL,
            summary="The document workflow stopped before a complete governed result was produced.",
            blocking_reason="inspect the structured runtime errors for the parser/retriever/agent failure",
        )
    return StageView(
        stage_id="document_analysis", ordinal=1, title="Document Analysis",
        status=StageStatus.AVAILABLE,
        summary="The parser, retriever and financial / legal / business agents completed this runtime document pass.",
        metrics=(
            Metric("Verified", str(counts.get("verified", 0))),
            Metric("Needs review", str(counts.get("needs_review", 0))),
            Metric("Pending", str(counts.get("pending", 0))),
            Metric("Rejected", str(counts.get("rejected", 0))),
        ),
    )


def _document_features(payload: dict[str, object]) -> StageView:
    if payload.get("status") not in {None, "failed"}:
        risks = _all_runtime_risks(payload)
        evidence_count = sum(
            len(risk.get("evidence") or [])
            for risk in risks
            if isinstance(risk.get("evidence") or [], list)
        )
        return StageView(
            stage_id="document_features", ordinal=2, title="Document Risk Features",
            status=StageStatus.AVAILABLE,
            summary=(
                "Runtime document-risk features were materialized as governed RiskItems, Evidence and deterministic calculations. "
                "The separate frozen modeling feature matrix is not required for this UI stage."
            ),
            metrics=(
                Metric("Risk items", str(len(risks))),
                Metric("Evidence anchors", str(evidence_count)),
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
    if market and market.get("status") == "available":
        observations = market.get("observations") or []
        available = sum(1 for item in observations if item.get("availability") == "available")
        return StageView(
            stage_id="market_features", ordinal=3, title="Market Features",
            status=StageStatus.AVAILABLE,
            summary="Governed point-in-time market context is available for this runtime scenario.",
            metrics=(Metric("Observations available", f"{available} of {len(observations)}"),),
        )
    return StageView(
        stage_id="market_features", ordinal=3, title="Market Features",
        status=StageStatus.PARTIAL,
        summary="PR-B Market-X Core is frozen, but this runtime scenario has not supplied its governed per-case product projection to the market channel.",
        blocking_reason="governed runtime Market-X projection/handoff is not configured; PR-B itself is not blocking",
        what_appears_when_unblocked=(
            "prior-IPO context with point-in-time provenance",
            "HSI Extended observations only when their governed local projection is present",
            "per-feature availability and missing reasons",
            "industry/turnover only when authoritative sources exist",
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
    if model and model.get("status", "available") == "available":
        metrics.append(Metric("Model score", str(model.get("score", "Unavailable"))))
        return StageView(
            stage_id="prediction", ordinal=4, title="Prediction",
            status=StageStatus.AVAILABLE,
            summary="The hash-bound frozen model score is available for this case. It remains an uncalibrated model score, not a probability.",
            metrics=tuple(metrics),
        )
    return StageView(
        stage_id="prediction", ordinal=4, title="Prediction",
        status=StageStatus.PARTIAL,
        summary="The deterministic rule score is available. A per-case frozen model score appears only when an authentic hash-bound PR-F runtime handoff is configured; neither score is a probability.",
        blocking_reason="per-case PR-F runtime artifact is absent or unavailable in this scenario; PR-F itself is COMPLETE / FROZEN",
        what_appears_when_unblocked=(
            "the frozen per-case model score with explicit score semantics",
            "model version and frozen result identity",
        ),
        metrics=tuple(metrics),
    )


def _explainability(payload: dict[str, object]) -> StageView:
    model = payload.get("model_prediction") or {}
    if model and model.get("status", "available") == "available":
        drivers = model.get("drivers") or []
        return StageView(
            stage_id="explainability", ordinal=5, title="Evidence / Explainability",
            status=StageStatus.AVAILABLE,
            summary="Document Evidence/Calculation provenance and frozen per-case model drivers are available.",
            metrics=(Metric("Model drivers", str(len(drivers))),),
        )
    return StageView(
        stage_id="explainability", ordinal=5, title="Evidence / Explainability",
        status=StageStatus.PARTIAL,
        summary="Evidence text, prospectus page provenance and deterministic calculations are available. Per-case SHAP drivers require the authentic local hash-bound PR-F runtime handoff.",
        blocking_reason="per-case model drivers are not present in this runtime; PR-F is not a blocking gate",
        what_appears_when_unblocked=(
            "per-IPO SHAP/top-driver records bound to the frozen model result",
            "document-versus-market contribution context when supported by the frozen artifact",
        ),
    )


def _final_supervisor(payload: dict[str, object]) -> StageView:
    final = payload.get("final_supervision") or {}
    if final:
        states = final.get("channel_states", [])
        available = sum(1 for state in states if state.get("status") == "available")
        completion = payload.get("runtime_completion_status")
        if completion in {
            "completed_with_partial_llm",
            "completed_with_deterministic_fallback",
        }:
            return StageView(
                stage_id="final_supervisor", ordinal=6, title="Final Supervisor",
                status=StageStatus.PARTIAL,
                summary="Deterministic cross-channel composition is available, but the LLM Final Supervisor did not complete successfully.",
                blocking_reason="the real LLM synthesis degraded; inspect the recorded provider diagnostics",
                metrics=(
                    Metric("Channels available", f"{available} of {len(states)}"),
                    Metric("Unresolved conflicts", str(final.get("metadata", {}).get("unresolved_conflict_count", 0))),
                    Metric("Referenced risks", str(len(final.get("referenced_risk_ids", [])))),
                ),
            )
        return StageView(
            stage_id="final_supervisor", ordinal=6, title="Final Supervisor",
            status=StageStatus.AVAILABLE,
            summary="Document, market, model and rule channels are composed; conflicts are preserved, not resolved.",
            metrics=(
                Metric("Channels available", f"{available} of {len(states)}"),
                Metric("Unresolved conflicts", str(final.get("metadata", {}).get("unresolved_conflict_count", 0))),
                Metric("Referenced risks", str(len(final.get("referenced_risk_ids", [])))),
            ),
        )
    supervision = payload.get("supervision") or {}
    metrics: tuple[Metric, ...] = ()
    if supervision:
        metrics = (
            Metric("Duplicate groups", str(len(supervision.get("duplicate_groups", [])))),
            Metric("Conflicts", str(len(supervision.get("conflicts", [])))),
            Metric("Composite findings", str(len(supervision.get("composite_findings", [])))),
        )
    return StageView(
        stage_id="final_supervisor", ordinal=6, title="Final Supervisor",
        status=StageStatus.PARTIAL,
        summary="Document-scope supervision is available. The cross-channel Final Supervisor is not configured in this runtime scenario.",
        blocking_reason="the Final Supervisor channel is not enabled by the selected configuration",
        metrics=metrics,
    )


def _final_report(payload: dict[str, object]) -> StageView:
    report_sections = payload.get("report_sections") or []
    final = payload.get("final_supervision") or {}
    if report_sections:
        return StageView(
            stage_id="final_report", ordinal=7, title="Final Risk Report",
            status=StageStatus.AVAILABLE,
            summary=(
                "The current runtime produced the governed final report artifact. "
                "Formal competition-readiness gates are tracked separately and do not make this completed case report unavailable."
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
        summary="No cross-channel final report is present in the current runtime result.",
        blocking_gate=GATE_E2E,
        blocking_reason="run the v0.4 Final Supervisor path successfully to materialize the current-case report",
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
    """Build the seven-stage view of the v0.4 chain for one analysis payload."""
    return tuple(resolver(payload) for resolver in _RESOLVERS)


def blocking_gates() -> tuple[str, ...]:
    """Distinct gates referenced by the chain, in stage order."""
    stages = resolve_stages({})
    return tuple(dict.fromkeys(stage.blocking_gate for stage in stages if stage.blocking_gate))