"""Application boundary for reviewer decisions.

The UI never touches a repository directly.  It states who reviewed what and how,
and this service builds the validated ``HumanReview`` record and persists it to
the reviewer sidecar, which is separate from the machine analysis store.

Nothing here can change a machine verdict: the service only ever writes reviewer
records and reads them back.
"""

from __future__ import annotations

from pathlib import Path

from ipo_risk.repositories.human_review import (
    HUMAN_REVIEW_STORE_VERSION,
    HumanReviewStoreError,
    JsonHumanReviewStore,
)
from ipo_risk.schemas.competition_runtime import HumanReview, HumanReviewDecision

# The reviewer verdict each decision implies.  It is a reviewer-side status and
# never overwrites the machine's ``verification_status``.
POST_REVIEW_STATUS = {
    HumanReviewDecision.ACCEPT: "human_accepted",
    HumanReviewDecision.REJECT: "human_rejected",
    HumanReviewDecision.NEEDS_FOLLOW_UP: "human_follow_up_required",
}


class HumanReviewService:
    """Record and read reviewer decisions for one analysis at a time."""

    store_version = HUMAN_REVIEW_STORE_VERSION

    def __init__(self, directory: str | Path = "data/human_review", store=None) -> None:
        self.store = store or JsonHumanReviewStore(directory)

    def record(
        self,
        *,
        analysis_id: str,
        case_id: str,
        run_id: str,
        target_id: str,
        original_machine_status: str,
        decision: HumanReviewDecision,
        reviewer_id: str,
        reviewer_note: str = "",
        evidence_id: str | None = None,
        page: int | None = None,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> HumanReview:
        reviewer = reviewer_id.strip()
        if not reviewer:
            raise HumanReviewStoreError("an unsigned review is not recorded; reviewer_id is required")
        review = HumanReview(
            case_id=case_id,
            run_id=run_id,
            target_id=target_id,
            original_machine_status=original_machine_status or "unknown",
            decision=decision,
            post_review_status=POST_REVIEW_STATUS[decision],
            reviewer_id=reviewer,
            reviewer_note=reviewer_note.strip(),
            evidence_id=evidence_id,
            page=page,
            bbox=bbox,
        )
        self.store.append(analysis_id, review)
        return review

    def history(self, analysis_id: str) -> list[HumanReview]:
        return self.store.list(analysis_id)

    def latest_by_target(self, analysis_id: str) -> dict[str, HumanReview]:
        return self.store.latest_by_target(analysis_id)


__all__ = ["HumanReviewService", "HumanReviewStoreError", "POST_REVIEW_STATUS"]
