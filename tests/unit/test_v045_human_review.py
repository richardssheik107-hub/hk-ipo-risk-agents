"""Reviewer decisions live in their own store and never touch a machine result."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ipo_risk.repositories.human_review import (
    HUMAN_REVIEW_STORE_VERSION,
    HumanReviewStoreError,
    JsonHumanReviewStore,
)
from ipo_risk.schemas.competition_runtime import HumanReview, HumanReviewDecision
from ipo_risk.services.human_review_service import HumanReviewService


def _service(tmp_path: Path) -> HumanReviewService:
    return HumanReviewService(directory=tmp_path / "human_review")


def _record(service: HumanReviewService, **overrides):
    payload = {
        "analysis_id": "analysis-1",
        "case_id": "ipo_2024_02410",
        "run_id": "run-1",
        "target_id": "r1",
        "original_machine_status": "verified",
        "decision": HumanReviewDecision.ACCEPT,
        "reviewer_id": "analyst_e",
        "reviewer_note": "checked against page 562",
    }
    payload.update(overrides)
    return service.record(**payload)


def test_a_recorded_decision_is_read_back_with_its_reviewer_identity(tmp_path) -> None:
    service = _service(tmp_path)
    review = _record(service)
    history = service.history("analysis-1")
    assert [item.review_id for item in history] == [review.review_id]
    assert history[0].post_review_status == "human_accepted"
    assert history[0].reviewer_id == "analyst_e"


def test_the_reviewer_sidecar_is_a_separate_file_from_any_analysis_result(tmp_path) -> None:
    service = _service(tmp_path)
    _record(service)
    files = sorted(path.name for path in (tmp_path / "human_review").glob("*.json"))
    assert files == ["analysis-1.json"]
    payload = json.loads((tmp_path / "human_review" / "analysis-1.json").read_text(encoding="utf-8"))
    assert payload["store_version"] == HUMAN_REVIEW_STORE_VERSION
    # The reviewer record carries no machine risk object; it only points at one.
    assert set(payload["reviews"][0]) == {
        "review_id", "case_id", "run_id", "target_id", "original_machine_status", "decision",
        "post_review_status", "reviewer_id", "reviewer_note", "evidence_id", "page", "bbox", "reviewed_at",
    }


def test_the_original_machine_status_is_preserved_beside_the_human_one(tmp_path) -> None:
    service = _service(tmp_path)
    review = _record(service, decision=HumanReviewDecision.REJECT, original_machine_status="verified")
    assert (review.original_machine_status, review.post_review_status) == ("verified", "human_rejected")


def test_appending_preserves_earlier_decisions(tmp_path) -> None:
    service = _service(tmp_path)
    _record(service)
    _record(service, decision=HumanReviewDecision.NEEDS_FOLLOW_UP, reviewer_id="analyst_b")
    assert len(service.history("analysis-1")) == 2


def test_the_latest_decision_per_target_is_resolvable(tmp_path) -> None:
    service = _service(tmp_path)
    _record(service)
    second = _record(service, decision=HumanReviewDecision.REJECT)
    latest = service.latest_by_target("analysis-1")
    assert latest["r1"].review_id == second.review_id


def test_an_unsigned_review_is_refused(tmp_path) -> None:
    with pytest.raises(HumanReviewStoreError):
        _record(_service(tmp_path), reviewer_id="   ")


def test_an_unknown_analysis_has_an_empty_history_rather_than_an_error(tmp_path) -> None:
    assert _service(tmp_path).history("never-analysed") == []


def test_a_duplicate_review_id_is_refused(tmp_path) -> None:
    store = JsonHumanReviewStore(tmp_path / "human_review")
    review = HumanReview(
        review_id="fixed", case_id="c", run_id="r", target_id="r1",
        original_machine_status="verified", decision=HumanReviewDecision.ACCEPT,
        post_review_status="human_accepted", reviewer_id="analyst_e",
    )
    store.append("analysis-1", review)
    with pytest.raises(HumanReviewStoreError):
        store.append("analysis-1", review)


@pytest.mark.parametrize("analysis_id", ["", "../escape", "nested/id"])
def test_an_unsafe_analysis_id_cannot_address_a_file(tmp_path, analysis_id) -> None:
    with pytest.raises(HumanReviewStoreError):
        JsonHumanReviewStore(tmp_path / "human_review").list(analysis_id)


def test_a_corrupt_sidecar_fails_loudly_instead_of_returning_nothing(tmp_path) -> None:
    directory = tmp_path / "human_review"
    directory.mkdir(parents=True)
    (directory / "analysis-1.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(HumanReviewStoreError):
        JsonHumanReviewStore(directory).list("analysis-1")
