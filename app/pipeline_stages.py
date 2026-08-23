"""Pure v0.4 pipeline-stage model for the PR-H end-to-end skeleton.

No Streamlit import lives here so the whole stage model stays testable headlessly;
the Streamlit layer only renders what ``resolve_stages`` returns.

The governing rule: a stage that is not AVAILABLE renders no number.  Un-frozen
stages name the gate that blocks them and say what will appear once it lands,
rather than showing a greyed-out chart, a zero, or a placeholder value.

PR-H is NOT STARTED.  This is preparation only; no stage here claims a gate has
been started or passed.

Scope note: these seven stages are the *baseline* E2E chain.  The competition
report described in docs/COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md section 12
adds evidence screenshots, market sentiment, multi-horizon validation views and a
reviewer audit trail on top.  That work (CH-0..CH-6) only starts after the PR-H
baseline E2E is running, so no stage here promises it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

# Gates that currently block parts of the chain, per docs/V04_FIVE_PERSON_EXECUTION_PLAN.md.
GATE_MARKET = "PR-B"
GATE_MODEL = "PR-F"
GATE_FINAL_SUPERVISOR = "PR-G"
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
    return StageView(
        stage_id="market_features", ordinal=3, title="Market Features",
        status=StageStatus.PENDING_GATE,
        summary="Governed point-in-time pre-listing Market-X.",
        blocking_gate=GATE_MARKET,
        blocking_reason="Market-X Core and the governed EOD store have not been built yet",
        what_appears_when_unblocked=(
            "IPO structure and listing context features",
            "prior-IPO point-in-time history",
            "HSI and industry benchmark context",
            "per-feature missingness and point-in-time provenance",
        ),
    )


def _prediction(payload: dict[str, object]) -> StageView:
    prediction = payload.get("prediction") or {}
    metrics: tuple[Metric, ...] = ()
    if prediction:
        metrics = (
            Metric("Rule score", str(prediction.get("risk_score", "Unavailable"))),
            Metric("Rule level", str(prediction.get("risk_level", "Unavailable"))),
        )
    return StageView(
        stage_id="prediction", ordinal=4, title="Prediction",
        status=StageStatus.PARTIAL,
        summary="The deterministic rule score is available. It is a prioritization signal, never a probability. "
                "No trained model prediction exists yet.",
        blocking_gate=GATE_MODEL,
        blocking_reason="no frozen, calibrated model has been trained yet",
        what_appears_when_unblocked=(
            "the frozen model's score and its calibration provenance",
            "model version and the dataset it was fit on",
        ),
        metrics=metrics,
    )


def _explainability(payload: dict[str, object]) -> StageView:
    return StageView(
        stage_id="explainability", ordinal=5, title="Evidence / Explainability",
        status=StageStatus.PARTIAL,
        summary="Evidence text, prospectus page provenance and deterministic calculations are available. "
                "Model-driven explanations are not.",
        blocking_gate=GATE_MODEL,
        blocking_reason="SHAP and feature importance need a trained model",
        what_appears_when_unblocked=(
            "global and per-IPO feature importance",
            "document-versus-market contribution split",
        ),
    )


def _final_supervisor(payload: dict[str, object]) -> StageView:
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
        summary="Document-scope supervision is available. The cross-channel Final Supervisor, which reconciles "
                "document, market and model signals, is a contract only.",
        blocking_gate=GATE_FINAL_SUPERVISOR,
        blocking_reason="the Final Supervisor and Market Agent are contracts, not yet wired into any workflow",
        what_appears_when_unblocked=(
            "reconciled document, market and model conclusions",
            "preserved cross-channel conflicts",
            "per-channel availability and uncertainty statement",
        ),
        metrics=metrics,
    )


def _final_report(payload: dict[str, object]) -> StageView:
    return StageView(
        stage_id="final_report", ordinal=7, title="Final Risk Report",
        status=StageStatus.PARTIAL,
        summary="The document-scope Markdown and JSON report is available for download. The full end-to-end "
                "report covering market context and model drivers is not.",
        blocking_gate=GATE_E2E,
        blocking_reason="the full report needs the Final Supervisor and the end-to-end demo chain",
        what_appears_when_unblocked=(
            "prospectus page to evidence to risk to feature to model driver to conclusion",
            "3-5 real IPO end-to-end demo cases",
            "reviewer audit trail and run provenance",
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
