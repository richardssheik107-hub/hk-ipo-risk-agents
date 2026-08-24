"""Pure v0.4 pipeline-stage model for the PR-H end-to-end skeleton.

No Streamlit import lives here so the whole stage model stays testable headlessly;
the Streamlit layer only renders what ``resolve_stages`` returns.

The governing rule: a stage that is not AVAILABLE renders no fabricated number.
A missing runtime asset is described as a capability/runtime limitation; already
frozen gates must never be reported as if they still block the chain.

PR-G implementation is delivered and A review passed.  PR-H preparation is
unblocked; formal PR-H starts after the local PR-G freeze manifest is committed.

Scope note: these seven stages are the *baseline* E2E chain.  The competition
report described in docs/COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md adds
evidence screenshots, market sentiment, multi-horizon validation views and a
reviewer audit trail on top.  That work (CH-0..CH-6) starts after PR-H baseline
E2E is frozen, so no stage here promises it.
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


def _document_analysis(payload: dict[str, object]) -> StageView:
    counts = payload.get("risk_status_counts") or {}
    return StageView(
        stage_id="document_analysis", ordinal=1, title="Document Analysis",
        status=StageStatus.AVAILABLE,
        summary="Frozen v0.3 Document Intelligence: parser, retriever and the financial / legal / business agents.",
        metrics=(
            Metric("Verified", str(counts.get("verified", 0))),
            Metric("Needs review", str(counts.get("needs_review", 0))),
            Metric("Pending", str(counts.get("pending", 0))),
            Metric("Rejected", str(counts.get("rejected", 0))),
        ),
    )


def _document_features(payload: dict[str, object]) -> StageView:
    return StageView(
        stage_id="document_features", ordinal=2, title="Document Risk Features",
        status=StageStatus.PARTIAL,
        summary="The frozen v04_document_features_v1 manifest is available; per-case vectors come from the "
                "PR-A materialization run, whose bulk artifacts are not part of this checkout.",
        blocking_reason="per-case feature vectors require the local PR-A run output, not a gate",
        what_appears_when_unblocked=(
            "the 100-dimension feature vector for this IPO",
            "its feature and snapshot provenance hashes",
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
        summary="PR-B Market-X Core is frozen and governed HSI Extended data is available, but this runtime "
                "scenario has not supplied a governed per-case Market-X snapshot to the product channel.",
        blocking_reason="governed runtime Market-X projection/handoff is not configured; PR-B itself is not blocking",
        what_appears_when_unblocked=(
            "pre-listing HSI and prior-IPO context with point-in-time provenance",
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
    if model:
        metrics.append(Metric("Model score", str(model.get("score", "Unavailable"))))
        return StageView(
            stage_id="prediction", ordinal=4, title="Prediction",
            status=StageStatus.AVAILABLE,
            summary="The frozen model score is available for this case. It remains an uncalibrated model score, not a probability.",
            metrics=tuple(metrics),
        )
    return StageView(
        stage_id="prediction", ordinal=4, title="Prediction",
        status=StageStatus.PARTIAL,
        summary="The deterministic rule score and frozen PR-F cohort evidence are available. A per-case frozen model "
                "score appears only when a hash-bound PR-F runtime handoff is configured; neither score is a probability.",
        blocking_reason="per-case PR-F runtime artifact is absent in this scenario; PR-F itself is COMPLETE / FROZEN",
        what_appears_when_unblocked=(
            "the frozen per-case model score with explicit score semantics",
            "model version and frozen result identity",
        ),
        metrics=tuple(metrics),
    )


def _explainability(payload: dict[str, object]) -> StageView:
    model = payload.get("model_prediction") or {}
    if model:
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
        summary="Evidence text, prospectus page provenance and deterministic calculations are available. "
                "PR-F global explainability is frozen, but per-case SHAP drivers require the local hash-bound runtime handoff.",
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
    final = payload.get("final_supervision") or {}
    if final:
        return StageView(
            stage_id="final_report", ordinal=7, title="Final Risk Report",
            status=StageStatus.PARTIAL,
            summary="The v0.4 Final Supervisor report path is available. PR-H must prove the complete governed runtime "
                    "Market-X + per-case model + Streamlit chain across 3–5 real IPO demo cases.",
            blocking_gate=GATE_E2E,
            blocking_reason="PR-H real-case E2E demo matrix and freeze are not complete",
            what_appears_when_unblocked=(
                "prospectus page to evidence to risk to market context to model driver to conclusion",
                "3-5 real IPO end-to-end demo cases",
                "run provenance and reproducible demo artifacts",
            ),
        )
    return StageView(
        stage_id="final_report", ordinal=7, title="Final Risk Report",
        status=StageStatus.PARTIAL,
        summary="The document-scope Markdown and JSON report is available. The v0.4 cross-channel report requires the Final Supervisor configuration.",
        blocking_gate=GATE_E2E,
        blocking_reason="PR-H requires a v0.4 Final Supervisor runtime and real-case demo chain",
        what_appears_when_unblocked=(
            "prospectus page to evidence to risk to market context to model driver to conclusion",
            "3-5 real IPO end-to-end demo cases",
            "run provenance and reproducible demo artifacts",
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
