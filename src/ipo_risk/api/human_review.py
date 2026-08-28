"""The human-review path as an HTTP API.

This is the second adapter over ``HumanReviewService``; the Streamlit console is
the first.  Both read the same persisted analysis result, offer the same review
targets and write to the same reviewer sidecar, so a decision recorded through
either surface is visible from the other.

What the API deliberately cannot do:

* run an analysis -- it only reads results the pipeline already persisted;
* change a machine verdict -- reviewer decisions are a sidecar, and every
  response carries both verdicts side by side rather than a merged one;
* invent a review target -- an id absent from the run is a 404, never an
  accepted decision about something that does not exist;
* record an unsigned review -- ``reviewer_id`` is required, and the service
  refuses a blank one.

Absence is reported as absence.  An analysis with no reviews returns
``reviewed: false`` and a null decision, never an empty table that could be read
as "nobody objected".
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Path as PathParam, status
from pydantic import BaseModel, ConfigDict, Field

from ipo_risk.repositories.human_review import HumanReviewStoreError
from ipo_risk.repositories.json_repository import JsonAnalysisRepository
from ipo_risk.runtime.review_projection import (
    REVIEW_TARGET_SCHEMA_VERSION,
    find_review_target,
    machine_vs_human,
    resolve_identity,
    review_targets,
)
from ipo_risk.schemas.competition_runtime import HumanReviewDecision
from ipo_risk.services.human_review_service import HumanReviewService

API_VERSION = "v046_role_e_human_review_api_v1"


# --- wire models -----------------------------------------------------------
#
# Declared rather than returned as bare dicts: the request body is validated
# before it reaches the service, and the response shape is part of the contract
# the OpenAPI document publishes.


class ReviewTarget(BaseModel):
    """One item a reviewer may rule on, with what the machine said about it."""

    model_config = ConfigDict(extra="forbid")

    target_id: str
    kind: str
    machine_status: str
    detail: str
    evidence_ids: list[str]
    risk_code: str
    risk_level: str
    involved_agents: list[str]


class ReviewTargetList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = REVIEW_TARGET_SCHEMA_VERSION
    analysis_id: str
    case_id: str
    run_id: str
    target_count: int
    targets: list[ReviewTarget]


class ReviewRequest(BaseModel):
    """A reviewer's decision about one target.

    ``reviewer_id`` has no default on purpose.  An unsigned review is not a
    review, and the service refuses one; requiring it here fails the request
    before anything is written.
    """

    model_config = ConfigDict(extra="forbid")

    target_id: str = Field(min_length=1)
    decision: HumanReviewDecision
    reviewer_id: str = Field(min_length=1)
    reviewer_note: str = ""
    evidence_id: str | None = None


class ReviewRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: str
    target_id: str
    original_machine_status: str
    decision: str
    post_review_status: str
    reviewer_id: str
    reviewer_note: str
    evidence_id: str | None
    reviewed_at: str


class LedgerRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: str
    kind: str
    machine_status: str
    reviewed: bool
    human_decision: str | None
    post_review_status: str | None
    reviewer_id: str | None
    reviewer_note: str | None
    reviewed_at: str | None


class ReviewLedger(BaseModel):
    """Machine and human verdicts side by side; the two are never merged."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = REVIEW_TARGET_SCHEMA_VERSION
    analysis_id: str
    review_count: int
    reviewed: bool
    statement: str
    rows: list[LedgerRow]


# --- application -----------------------------------------------------------


def _record_payload(review: Any) -> dict[str, Any]:
    data = review.model_dump(mode="json")
    return {
        "review_id": data["review_id"],
        "target_id": data["target_id"],
        "original_machine_status": data["original_machine_status"],
        "decision": data["decision"],
        "post_review_status": data["post_review_status"],
        "reviewer_id": data["reviewer_id"],
        "reviewer_note": data.get("reviewer_note", ""),
        "evidence_id": data.get("evidence_id"),
        "reviewed_at": data["reviewed_at"],
    }


def build_app(
    *,
    analyses: JsonAnalysisRepository,
    reviews: HumanReviewService,
) -> FastAPI:
    """Build the API over an explicit repository and service.

    Both collaborators are injected so tests drive the real code against a
    temporary directory rather than a mock of it.
    """

    app = FastAPI(
        title="IPO Risk — Human Review API",
        version=API_VERSION,
        description=__doc__,
    )

    def _load(analysis_id: str) -> dict[str, Any]:
        result = analyses.get(analysis_id)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"no persisted analysis {analysis_id!r}; the API never runs one on demand",
            )
        return result.model_dump(mode="json")

    def analysis(analysis_id: str = PathParam(min_length=1)) -> tuple[str, dict[str, Any]]:
        return analysis_id, _load(analysis_id)

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok", "api_version": API_VERSION}

    @app.get(
        "/analyses/{analysis_id}/review-targets",
        response_model=ReviewTargetList,
        tags=["review"],
    )
    def list_targets(bound=Depends(analysis)) -> ReviewTargetList:
        analysis_id, payload = bound
        targets = review_targets(payload)
        case_id, run_id = resolve_identity(payload)
        return ReviewTargetList(
            analysis_id=analysis_id,
            case_id=case_id,
            run_id=run_id,
            target_count=len(targets),
            targets=[ReviewTarget(**item) for item in targets],
        )

    @app.get(
        "/analyses/{analysis_id}/review-targets/{target_id}",
        response_model=ReviewTarget,
        tags=["review"],
    )
    def get_target(target_id: str, bound=Depends(analysis)) -> ReviewTarget:
        _, payload = bound
        target = find_review_target(payload, target_id)
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{target_id!r} is not a review target in this run",
            )
        return ReviewTarget(**target)

    @app.post(
        "/analyses/{analysis_id}/reviews",
        response_model=ReviewRecord,
        status_code=status.HTTP_201_CREATED,
        tags=["review"],
    )
    def record_review(request: ReviewRequest, bound=Depends(analysis)) -> ReviewRecord:
        analysis_id, payload = bound
        target = find_review_target(payload, request.target_id)
        if target is None:
            # Fail closed.  Accepting a decision about an id this run does not
            # contain would put a verdict in the sidecar that no machine claim
            # can ever be compared against.
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{request.target_id!r} is not a review target in this run",
            )
        case_id, run_id = resolve_identity(payload)
        try:
            review = reviews.record(
                analysis_id=analysis_id,
                case_id=case_id,
                run_id=run_id,
                target_id=request.target_id,
                original_machine_status=target["machine_status"],
                decision=request.decision,
                reviewer_id=request.reviewer_id,
                reviewer_note=request.reviewer_note,
                evidence_id=request.evidence_id,
            )
        except HumanReviewStoreError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc
        return ReviewRecord(**_record_payload(review))

    @app.get(
        "/analyses/{analysis_id}/reviews",
        response_model=list[ReviewRecord],
        tags=["review"],
    )
    def review_history(bound=Depends(analysis)) -> list[ReviewRecord]:
        analysis_id, _ = bound
        return [ReviewRecord(**_record_payload(item)) for item in reviews.history(analysis_id)]

    @app.get(
        "/analyses/{analysis_id}/review-ledger",
        response_model=ReviewLedger,
        tags=["review"],
    )
    def ledger(bound=Depends(analysis)) -> ReviewLedger:
        analysis_id, payload = bound
        latest = reviews.latest_by_target(analysis_id)
        rows = machine_vs_human(payload, latest)
        reviewed = [row for row in rows if row["reviewed"]]
        return ReviewLedger(
            analysis_id=analysis_id,
            review_count=len(reviewed),
            reviewed=bool(reviewed),
            statement=(
                "Reviewer decisions are a sidecar: they never modified any RiskItem, "
                "Evidence or machine conclusion in this run."
                if reviewed
                else "No human review was recorded for this analysis. This is an absence "
                "of review, not an endorsement."
            ),
            rows=[LedgerRow(**row) for row in rows],
        )

    return app


def create_app(
    *,
    results_dir: str = "data/results",
    review_dir: str = "data/human_review",
) -> FastAPI:
    """The default wiring, for ``uvicorn ipo_risk.api:create_app --factory``."""

    return build_app(
        analyses=JsonAnalysisRepository(results_dir),
        reviews=HumanReviewService(review_dir),
    )


__all__ = ["API_VERSION", "build_app", "create_app"]
