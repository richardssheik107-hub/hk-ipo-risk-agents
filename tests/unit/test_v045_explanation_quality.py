"""M4 must be scored by people, and an unscored case must never read as a pass.

The rubric is frozen in the competition metric protocol: five dimensions, a 1-5
scale, at least two human reviewers per case, a mean target and a per-case
floor, and no LLM as sole reviewer. The tests here fix the two things that would
quietly destroy the metric -- thresholds drifting away from the frozen protocol,
and a case with no human review being aggregated as if it had passed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ipo_risk.runtime.explanation_quality import (
    DEFAULT_PROTOCOL_PATH,
    ExplanationQualityError,
    ExplanationQualityRubric,
    ExplanationReview,
    build_explanation_quality,
    build_review_form,
    read_reviews,
    render_explanation_quality,
)


CASES = ["ipo_2024_02410", "ipo_2024_02460", "ipo_2024_01318"]


@pytest.fixture
def rubric() -> ExplanationQualityRubric:
    return ExplanationQualityRubric.load(DEFAULT_PROTOCOL_PATH)


def _review(
    case_id: str, reviewer: str, score: int = 4, kind: str = "human", **overrides
) -> ExplanationReview:
    payload = {
        "case_id": case_id,
        "reviewer_id": reviewer,
        "reviewer_kind": kind,
        "scores": {
            "evidence_grounding": score,
            "logical_consistency": score,
            "conflict_handling": score,
            "recheck_quality": score,
            "final_conclusion": score,
        },
    }
    payload.update(overrides)
    return ExplanationReview.model_validate(payload)


def _full(score: int = 4) -> list[ExplanationReview]:
    return [
        _review(case_id, reviewer, score)
        for case_id in CASES
        for reviewer in ("reviewer_1", "reviewer_2")
    ]


# --- the rubric is the frozen protocol, not a local copy --------------------


def test_the_rubric_comes_from_the_frozen_metric_protocol(rubric) -> None:
    """A local restatement of the thresholds could drift; reading them cannot."""
    protocol = json.loads(DEFAULT_PROTOCOL_PATH.read_text(encoding="utf-8"))
    block = protocol["explanation_quality"]
    assert rubric.protocol_version == protocol["protocol_version"]
    assert list(rubric.dimensions) == block["dimensions"]
    assert rubric.minimum_human_reviewers == block["minimum_human_reviewers"]
    assert rubric.mean_score_target == block["mean_score_target"]
    assert rubric.minimum_case_score == block["minimum_case_score"]
    assert rubric.llm_reviewer_may_be_sole_reviewer is False


# --- fail-closed aggregation ------------------------------------------------


def test_no_reviews_at_all_is_unmet_not_empty_pass(rubric) -> None:
    artifact = build_explanation_quality(rubric=rubric, reviews=[], declared_case_ids=CASES)
    assert artifact["satisfied"] is False
    assert artifact["mean_score"] is None
    assert len(artifact["unmet_conditions"]) == len(CASES)
    assert "NOT met" in artifact["verdict"]


def test_a_single_reviewer_does_not_satisfy_the_frozen_minimum(rubric) -> None:
    reviews = [_review(case_id, "reviewer_1", 5) for case_id in CASES]
    artifact = build_explanation_quality(rubric=rubric, reviews=reviews, declared_case_ids=CASES)
    assert artifact["satisfied"] is False
    assert all("1 human reviewer(s)" in item for item in artifact["unmet_conditions"])
    # A perfect score from one person still does not clear the reviewer minimum.
    assert artifact["mean_score"] == 5.0


def test_an_llm_review_can_never_stand_in_for_a_human(rubric) -> None:
    """The protocol forbids a sole LLM reviewer, so its score is never counted."""
    reviews = [
        _review(case_id, reviewer, 5, kind="llm")
        for case_id in CASES
        for reviewer in ("model_a", "model_b")
    ]
    artifact = build_explanation_quality(rubric=rubric, reviews=reviews, declared_case_ids=CASES)
    assert artifact["satisfied"] is False
    assert artifact["mean_score"] is None
    assert all(case["advisory_llm_review_count"] == 2 for case in artifact["cases"])
    assert all("no human review recorded" in item for item in artifact["unmet_conditions"])


def test_an_llm_review_cannot_lift_a_human_score(rubric) -> None:
    reviews = _full(4) + [_review(case_id, "model_a", 5, kind="llm") for case_id in CASES]
    artifact = build_explanation_quality(rubric=rubric, reviews=reviews, declared_case_ids=CASES)
    assert artifact["mean_score"] == 4.0, "advisory reviews must not enter the primary mean"
    for case in artifact["cases"]:
        counted = [item for item in case["reviews"] if item["counted_in_primary"]]
        assert len(counted) == 2


def test_one_unreviewed_case_blocks_the_whole_matrix(rubric) -> None:
    reviews = [item for item in _full(5) if item.case_id != CASES[-1]]
    artifact = build_explanation_quality(rubric=rubric, reviews=reviews, declared_case_ids=CASES)
    assert artifact["reviewed_case_count"] == 2
    assert artifact["satisfied"] is False
    assert any(CASES[-1] in item for item in artifact["unmet_conditions"])


def test_a_case_below_the_per_case_floor_fails_even_with_a_good_mean(rubric) -> None:
    reviews = _full(5)
    reviews = [item for item in reviews if item.case_id != CASES[0]]
    reviews += [_review(CASES[0], reviewer, 2) for reviewer in ("reviewer_1", "reviewer_2")]
    artifact = build_explanation_quality(rubric=rubric, reviews=reviews, declared_case_ids=CASES)
    assert artifact["min_case_score"] == 2.0
    assert artifact["satisfied"] is False
    assert any("per-case floor" in item for item in artifact["unmet_conditions"])


def test_a_mean_below_the_target_is_unmet(rubric) -> None:
    artifact = build_explanation_quality(rubric=rubric, reviews=_full(3), declared_case_ids=CASES)
    assert artifact["mean_score"] == 3.0
    assert artifact["satisfied"] is False
    assert any("below the target" in item for item in artifact["unmet_conditions"])


def test_two_human_reviewers_above_the_target_satisfy_the_metric(rubric) -> None:
    artifact = build_explanation_quality(rubric=rubric, reviews=_full(4), declared_case_ids=CASES)
    assert artifact["satisfied"] is True
    assert artifact["unmet_conditions"] == []
    assert artifact["distinct_human_reviewers"] == ["reviewer_1", "reviewer_2"]
    assert all(case["passed"] for case in artifact["cases"])


# --- input that must be refused rather than coerced ------------------------


def test_a_score_outside_the_frozen_scale_is_refused(rubric) -> None:
    with pytest.raises(ExplanationQualityError, match="outside the frozen scale"):
        build_explanation_quality(
            rubric=rubric, reviews=[_review(CASES[0], "reviewer_1", 9)], declared_case_ids=CASES
        )


def test_a_review_missing_a_dimension_is_refused(rubric) -> None:
    review = _review(CASES[0], "reviewer_1")
    review.scores.pop("recheck_quality")
    with pytest.raises(ExplanationQualityError, match="missing="):
        build_explanation_quality(rubric=rubric, reviews=[review], declared_case_ids=CASES)


def test_a_review_for_an_undeclared_case_is_refused(rubric) -> None:
    with pytest.raises(ExplanationQualityError, match="outside the declared matrix"):
        build_explanation_quality(
            rubric=rubric, reviews=[_review("ipo_2024_09999", "reviewer_1")], declared_case_ids=CASES
        )


def test_a_reviewer_id_that_looks_like_an_address_is_refused(rubric) -> None:
    """This artifact ships; a reviewer's contact details must not ship with it."""
    with pytest.raises(ExplanationQualityError, match="pseudonymous label"):
        build_explanation_quality(
            rubric=rubric,
            reviews=[_review(CASES[0], "someone@example.com")],
            declared_case_ids=CASES,
        )


# --- the form carries facts, never conclusions ------------------------------


def test_the_review_form_contains_no_scores(rubric, tmp_path: Path) -> None:
    summary = {
        "cases": [
            {
                "case_id": CASES[0],
                "stock_code": "2410.HK",
                "status": "completed",
                "verified_risk_count": 1,
                "conflict_count": 6,
                "recheck_attempted": 3,
                "llm_synthesis_outcome": "provider_call_failed",
                "channel_states": {"market": "unavailable_error"},
                "traceability": {"overall_traceability": 1.0},
            }
        ]
    }
    form = build_review_form(rubric=rubric, matrix_summary=summary)
    assert form["reviews"] == []
    entry = form["cases"][0]
    assert set(entry["review_template"]["scores"].values()) == {None}
    # The reviewer is told what to read and what the run did, not what to think.
    assert entry["run_facts"]["conflict_count"] == 6
    assert f"{CASES[0]}/case_report.md" in entry["artifacts_to_read"]
    assert "provider_call_failed" in json.dumps(entry)


def test_an_unfilled_form_is_refused_as_a_review(rubric, tmp_path: Path) -> None:
    form = build_review_form(
        rubric=rubric, matrix_summary={"cases": [{"case_id": CASES[0], "stock_code": "2410.HK"}]}
    )
    form["reviews"] = [form["cases"][0]["review_template"]]
    path = tmp_path / "reviews.json"
    path.write_text(json.dumps(form, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ExplanationQualityError, match="unscored dimension"):
        read_reviews(path)


def test_filled_reviews_round_trip_through_the_reviewer_file(rubric, tmp_path: Path) -> None:
    path = tmp_path / "reviews.json"
    path.write_text(
        json.dumps({"reviews": [item.model_dump(mode="json") for item in _full(4)]}),
        encoding="utf-8",
    )
    reviews = read_reviews(path)
    assert len(reviews) == len(CASES) * 2
    artifact = build_explanation_quality(
        rubric=rubric, reviews=reviews, declared_case_ids=CASES
    )
    assert artifact["satisfied"] is True


def test_the_rendered_summary_states_the_verdict_and_the_reviewer_count(rubric) -> None:
    artifact = build_explanation_quality(rubric=rubric, reviews=[], declared_case_ids=CASES)
    rendered = render_explanation_quality(artifact)
    assert "M4 NOT met" in rendered
    assert "not reviewed" in rendered
    assert "required human reviewers per case: 2" in rendered
