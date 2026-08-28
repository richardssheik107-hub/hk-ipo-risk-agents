"""Reviewer decisions, stored strictly apart from machine results.

A ``HumanReview`` never mutates a ``RiskItem``, an ``Evidence`` object or an
``IPOAnalysisResult``.  It is an append-only sidecar keyed by analysis, so the
machine verdict and the human verdict stay independently auditable: reading the
machine result gives what the system concluded, reading this store gives what a
person decided about it, and the two are never merged in storage.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from ipo_risk.schemas.competition_runtime import HumanReview


HUMAN_REVIEW_STORE_VERSION = "v04_e_human_review_store_v1"


class HumanReviewStoreError(RuntimeError):
    """The reviewer sidecar could not be read or written safely."""


class JsonHumanReviewStore:
    """Append-only per-analysis reviewer sidecar in its own directory."""

    name = "json_human_review"
    store_version = HUMAN_REVIEW_STORE_VERSION

    def __init__(self, directory: str | Path = "data/human_review") -> None:
        self.directory = Path(directory)

    def _path(self, analysis_id: str) -> Path:
        if not analysis_id or any(char in analysis_id for char in "/\\"):
            raise HumanReviewStoreError("analysis_id must be a non-empty path-safe identifier")
        return self.directory / f"{analysis_id}.json"

    def list(self, analysis_id: str) -> list[HumanReview]:
        path = self._path(analysis_id)
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            records = payload["reviews"]
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise HumanReviewStoreError(f"reviewer sidecar for {analysis_id} is unreadable: {exc}") from exc
        return [HumanReview.model_validate(record) for record in records]

    def append(self, analysis_id: str, review: HumanReview) -> list[HumanReview]:
        """Append one decision; existing decisions are preserved verbatim."""

        existing = self.list(analysis_id)
        if any(item.review_id == review.review_id for item in existing):
            raise HumanReviewStoreError(f"review {review.review_id} already exists for {analysis_id}")
        return self._write(analysis_id, [*existing, review])

    def replace(self, analysis_id: str, reviews: Sequence[HumanReview]) -> list[HumanReview]:
        return self._write(analysis_id, list(reviews))

    def _write(self, analysis_id: str, reviews: list[HumanReview]) -> list[HumanReview]:
        path = self._path(analysis_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "store_version": self.store_version,
            "analysis_id": analysis_id,
            "reviews": [review.model_dump(mode="json") for review in reviews],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return reviews

    def latest_by_target(self, analysis_id: str) -> dict[str, HumanReview]:
        """The most recent decision per target; earlier ones remain in the file."""

        latest: dict[str, HumanReview] = {}
        # The sidecar is an append-only journal, so persisted order is the
        # authoritative decision order.  Sorting by wall-clock timestamps is
        # not safe on Windows: consecutive records can receive the same clock
        # tick, at which point the UUID tie-breaker makes "latest" random.
        for review in self.list(analysis_id):
            latest[review.target_id] = review
        return latest
