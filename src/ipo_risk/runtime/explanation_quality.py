"""M4 Explanation Quality: the frozen rubric, the review form and the artifact.

The competition asks for explanation quality but fixes no absolute number, so
the protocol froze a rubric instead: five dimensions, a 1-5 scale, at least two
human reviewers, a mean target and a per-case floor, and -- explicitly -- an LLM
may not be the sole reviewer.  Those thresholds are read from
``configs/v045_competition_metric_protocol.json`` rather than restated here, so
this module cannot drift away from the frozen protocol.

Scores come from people.  This module can build the empty review form and it can
aggregate filled-in reviews into ``explanation_quality.json``, but it never
invents a score and never scores a case itself.  A case nobody reviewed, a case
one person reviewed, or a case only a model reviewed each leave the Gate unmet
with the reason named, which is the same fail-closed reading the Gate E1
evidence uses.

LLM reviews may be recorded, but they are advisory: the primary mean is computed
from human reviews alone.  A model cannot lift its own explanation past the bar.
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from statistics import fmean
from typing import Any, Iterable, Sequence

from pydantic import BaseModel, ConfigDict, Field


EXPLANATION_QUALITY_SCHEMA_VERSION = "v045_role_e_explanation_quality_v1"
REVIEW_FORM_SCHEMA_VERSION = "v045_role_e_explanation_review_form_v1"
DEFAULT_PROTOCOL_PATH = Path("configs/v045_competition_metric_protocol.json")


class ExplanationQualityError(ValueError):
    """A review could not be accepted, so no artifact is built from it."""


class ReviewerKind(StrEnum):
    HUMAN = "human"
    LLM = "llm"


class ExplanationQualityRubric(BaseModel):
    """The frozen M4 rubric, read from the competition metric protocol."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    protocol_version: str
    dimensions: tuple[str, ...] = Field(min_length=1)
    scale_min: int
    scale_max: int
    minimum_human_reviewers: int
    mean_score_target: float
    minimum_case_score: float
    llm_reviewer_may_be_sole_reviewer: bool

    @classmethod
    def load(cls, path: Path | str = DEFAULT_PROTOCOL_PATH) -> "ExplanationQualityRubric":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        try:
            block = payload["explanation_quality"]
        except (KeyError, TypeError) as exc:  # pragma: no cover - malformed protocol
            raise ExplanationQualityError(
                f"{path} carries no explanation_quality block; the frozen protocol is required"
            ) from exc
        return cls(protocol_version=payload["protocol_version"], **block)


class ExplanationReview(BaseModel):
    """One reviewer's scoring of one case's explanation."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    # A pseudonymous label such as ``reviewer_1``: this artifact ships with the
    # submission, so it must not carry a reviewer's contact details.
    reviewer_id: str = Field(min_length=1)
    reviewer_kind: ReviewerKind
    scores: dict[str, int]
    note: str = ""
    reviewed_at: datetime | None = None


def _check(review: ExplanationReview, rubric: ExplanationQualityRubric) -> None:
    if "@" in review.reviewer_id:
        raise ExplanationQualityError(
            f"reviewer_id {review.reviewer_id!r} looks like an address; use a pseudonymous label, "
            "because this artifact is shipped with the submission"
        )
    missing = [name for name in rubric.dimensions if name not in review.scores]
    unknown = [name for name in review.scores if name not in rubric.dimensions]
    if missing or unknown:
        raise ExplanationQualityError(
            f"{review.reviewer_id} on {review.case_id}: the frozen rubric has "
            f"{list(rubric.dimensions)}; missing={missing} unknown={unknown}"
        )
    for name, score in review.scores.items():
        if not isinstance(score, int) or isinstance(score, bool):
            raise ExplanationQualityError(
                f"{review.reviewer_id} on {review.case_id}: {name} is not an integer score"
            )
        if not rubric.scale_min <= score <= rubric.scale_max:
            raise ExplanationQualityError(
                f"{review.reviewer_id} on {review.case_id}: {name}={score} is outside the frozen "
                f"scale {rubric.scale_min}-{rubric.scale_max}"
            )


def _reviewer_mean(review: ExplanationReview, rubric: ExplanationQualityRubric) -> float:
    return fmean(review.scores[name] for name in rubric.dimensions)


def build_explanation_quality(
    *,
    rubric: ExplanationQualityRubric,
    reviews: Sequence[ExplanationReview],
    declared_case_ids: Sequence[str],
) -> dict[str, Any]:
    """Aggregate filled-in reviews into the M4 artifact.

    Every review is validated against the frozen rubric first: a malformed or
    out-of-scale review raises rather than being silently coerced, because a
    quality metric built from unchecked input is worth nothing.
    """

    for review in reviews:
        _check(review, rubric)

    by_case: dict[str, list[ExplanationReview]] = {case_id: [] for case_id in declared_case_ids}
    unknown_cases: list[str] = []
    for review in reviews:
        if review.case_id not in by_case:
            unknown_cases.append(review.case_id)
            continue
        by_case[review.case_id].append(review)
    if unknown_cases:
        raise ExplanationQualityError(
            f"reviews reference cases outside the declared matrix: {sorted(set(unknown_cases))}"
        )

    cases: list[dict[str, Any]] = []
    unmet: list[str] = []
    for case_id in declared_case_ids:
        case_reviews = by_case[case_id]
        human = [item for item in case_reviews if item.reviewer_kind is ReviewerKind.HUMAN]
        advisory = [item for item in case_reviews if item.reviewer_kind is ReviewerKind.LLM]
        human_ids = sorted({item.reviewer_id for item in human})

        # The primary score is human-only; an LLM review is recorded but never
        # counted, so a model cannot lift its own explanation past the bar.
        case_mean = fmean(_reviewer_mean(item, rubric) for item in human) if human else None
        dimension_means = {
            name: (fmean(item.scores[name] for item in human) if human else None)
            for name in rubric.dimensions
        }
        enough_humans = len(human_ids) >= rubric.minimum_human_reviewers
        meets_floor = case_mean is not None and case_mean >= rubric.minimum_case_score
        case_passed = enough_humans and meets_floor

        if not human:
            unmet.append(
                f"{case_id}: no human review recorded"
                + (" (only advisory LLM reviews)" if advisory else "")
            )
        elif not enough_humans:
            unmet.append(
                f"{case_id}: {len(human_ids)} human reviewer(s), the frozen rubric requires "
                f"{rubric.minimum_human_reviewers}"
            )
        if human and not meets_floor:
            unmet.append(
                f"{case_id}: case mean {case_mean:.2f} is below the per-case floor "
                f"{rubric.minimum_case_score}"
            )
        cases.append(
            {
                "case_id": case_id,
                "human_reviewer_count": len(human_ids),
                "human_reviewer_ids": human_ids,
                "advisory_llm_review_count": len(advisory),
                "dimension_means": dimension_means,
                "case_mean": case_mean,
                "meets_minimum_case_score": meets_floor,
                "meets_minimum_human_reviewers": enough_humans,
                "passed": case_passed,
                "reviews": [
                    {
                        "reviewer_id": item.reviewer_id,
                        "reviewer_kind": item.reviewer_kind.value,
                        "scores": {name: item.scores[name] for name in rubric.dimensions},
                        "reviewer_mean": _reviewer_mean(item, rubric),
                        "note": item.note,
                        "counted_in_primary": item.reviewer_kind is ReviewerKind.HUMAN,
                        "reviewed_at": item.reviewed_at.isoformat() if item.reviewed_at else None,
                    }
                    for item in case_reviews
                ],
            }
        )

    scored = [case["case_mean"] for case in cases if case["case_mean"] is not None]
    mean_score = fmean(scored) if scored else None
    min_case_score = min(scored) if scored else None
    if mean_score is not None and mean_score < rubric.mean_score_target:
        unmet.append(
            f"mean score {mean_score:.2f} is below the target {rubric.mean_score_target}"
        )
    if not declared_case_ids:
        unmet.append("no case was declared for review")

    all_human_ids = sorted(
        {item.reviewer_id for item in reviews if item.reviewer_kind is ReviewerKind.HUMAN}
    )
    return {
        "schema_version": EXPLANATION_QUALITY_SCHEMA_VERSION,
        "metric": "M4_explanation_quality",
        "metric_protocol_version": rubric.protocol_version,
        "rubric": {
            "dimensions": list(rubric.dimensions),
            "scale": [rubric.scale_min, rubric.scale_max],
            "minimum_human_reviewers": rubric.minimum_human_reviewers,
            "mean_score_target": rubric.mean_score_target,
            "minimum_case_score": rubric.minimum_case_score,
            "llm_reviewer_may_be_sole_reviewer": rubric.llm_reviewer_may_be_sole_reviewer,
        },
        "scoring_policy": (
            "The primary mean is computed from human reviews only; LLM reviews are recorded as "
            "advisory and never counted. The frozen protocol forbids an LLM being the sole "
            "reviewer, so a case without human review cannot pass."
        ),
        "declared_case_count": len(declared_case_ids),
        "reviewed_case_count": len(scored),
        "distinct_human_reviewers": all_human_ids,
        "mean_score": mean_score,
        "min_case_score": min_case_score,
        "cases": cases,
        "satisfied": bool(scored) and not unmet,
        "unmet_conditions": unmet,
        "verdict": (
            "M4 explanation quality met on the declared matrix"
            if bool(scored) and not unmet
            else "M4 NOT met: the rubric is frozen and unscored cases cannot be assumed to pass"
        ),
    }


def build_review_form(
    *, rubric: ExplanationQualityRubric, matrix_summary: dict[str, Any]
) -> dict[str, Any]:
    """The empty form, seeded with each case's facts and no scores at all.

    The reviewer needs to know what they are judging, so every entry carries the
    run's own numbers and points at the case report and the reasoning log. The
    score fields are null: this module states what to look at, never what to
    conclude.
    """

    entries: list[dict[str, Any]] = []
    for case in matrix_summary.get("cases", []):
        if not isinstance(case, dict) or not case.get("case_id"):
            continue
        traceability = case.get("traceability") or {}
        entries.append(
            {
                "case_id": case["case_id"],
                "stock_code": case.get("stock_code"),
                "artifacts_to_read": [
                    f"{case['case_id']}/case_report.md",
                    f"{case['case_id']}/agent_reasoning_log.md",
                    f"{case['case_id']}/gate_e1_evidence.json",
                ],
                "run_facts": {
                    "status": case.get("status"),
                    "verified_risk_count": case.get("verified_risk_count"),
                    "pending_risk_count": case.get("pending_risk_count"),
                    "rejected_risk_count": case.get("rejected_risk_count"),
                    "conflict_count": case.get("conflict_count"),
                    "recheck_attempted": case.get("recheck_attempted"),
                    "llm_synthesis_outcome": case.get("llm_synthesis_outcome"),
                    "channel_states": case.get("channel_states"),
                    "overall_traceability": traceability.get("overall_traceability"),
                },
                "review_template": {
                    "case_id": case["case_id"],
                    "reviewer_id": "<pseudonymous label, e.g. reviewer_1>",
                    "reviewer_kind": ReviewerKind.HUMAN.value,
                    "scores": {name: None for name in rubric.dimensions},
                    "note": "",
                },
            }
        )
    return {
        "schema_version": REVIEW_FORM_SCHEMA_VERSION,
        "metric_protocol_version": rubric.protocol_version,
        "instructions": (
            f"Score each dimension from {rubric.scale_min} to {rubric.scale_max} after reading the "
            "listed artifacts. At least "
            f"{rubric.minimum_human_reviewers} people must score every case independently; an LLM "
            "review may be attached but is advisory only and is never counted."
        ),
        "dimensions": {
            "evidence_grounding": "Is every claim tied to Evidence the run actually produced?",
            "logical_consistency": "Do the conclusion, severity and stated reasons agree?",
            "conflict_handling": "Are cross-agent conflicts surfaced honestly rather than smoothed over?",
            "recheck_quality": "Is the targeted re-check purposeful, bounded and reported truthfully?",
            "final_conclusion": "Is the final judgement useful, bounded and free of overclaim?",
        },
        "cases": entries,
        "reviews": [],
    }


def read_reviews(path: Path | str) -> list[ExplanationReview]:
    """Load filled-in reviews from the reviewer file.

    Accepts either the review form with its ``reviews`` list filled in, or a
    bare list of reviews, so a reviewer can hand back the same file they were
    given.
    """

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    records: Iterable[Any]
    if isinstance(payload, dict):
        records = payload.get("reviews", [])
    elif isinstance(payload, list):
        records = payload
    else:  # pragma: no cover - defensive
        raise ExplanationQualityError(f"{path} is neither a review form nor a list of reviews")
    reviews: list[ExplanationReview] = []
    for record in records:
        if not isinstance(record, dict):
            raise ExplanationQualityError(f"{path} contains a non-object review entry")
        if any(value is None for value in (record.get("scores") or {}).values()):
            raise ExplanationQualityError(
                f"{path} still contains an unscored dimension for "
                f"{record.get('reviewer_id')} on {record.get('case_id')}; "
                "an unfilled form is not a review"
            )
        reviews.append(ExplanationReview.model_validate(record))
    return reviews


def render_explanation_quality(artifact: dict[str, Any]) -> str:
    """The M4 result as a short readable summary for the submission bundle."""

    rubric = artifact["rubric"]
    lines = [
        "# M4 Explanation Quality",
        "",
        f"- metric protocol: `{artifact['metric_protocol_version']}`",
        f"- rubric: {', '.join(rubric['dimensions'])} on {rubric['scale'][0]}-{rubric['scale'][1]}",
        f"- required human reviewers per case: {rubric['minimum_human_reviewers']} "
        f"(LLM sole reviewer allowed: {str(rubric['llm_reviewer_may_be_sole_reviewer']).lower()})",
        f"- mean target: {rubric['mean_score_target']} · per-case floor: {rubric['minimum_case_score']}",
        "",
        f"- reviewed cases: {artifact['reviewed_case_count']} / {artifact['declared_case_count']}",
        f"- mean score: {artifact['mean_score'] if artifact['mean_score'] is not None else '—'}",
        f"- lowest case score: "
        f"{artifact['min_case_score'] if artifact['min_case_score'] is not None else '—'}",
        f"- distinct human reviewers: {len(artifact['distinct_human_reviewers'])}",
        "",
        f"**{artifact['verdict']}**",
        "",
        "## Per case",
        "",
    ]
    for case in artifact["cases"]:
        mean = case["case_mean"]
        lines.append(
            f"- `{case['case_id']}` — mean "
            f"{f'{mean:.2f}' if mean is not None else 'not reviewed'} · "
            f"{case['human_reviewer_count']} human reviewer(s) · "
            f"{'passed' if case['passed'] else 'NOT passed'}"
        )
        for name, value in case["dimension_means"].items():
            lines.append(f"  - {name}: {f'{value:.2f}' if value is not None else '—'}")
    if artifact["unmet_conditions"]:
        lines += ["", "## Unmet", ""]
        lines.extend(f"- {item}" for item in artifact["unmet_conditions"])
    lines.append("")
    return "\n".join(lines)


__all__ = [
    "DEFAULT_PROTOCOL_PATH",
    "EXPLANATION_QUALITY_SCHEMA_VERSION",
    "ExplanationQualityError",
    "ExplanationQualityRubric",
    "ExplanationReview",
    "REVIEW_FORM_SCHEMA_VERSION",
    "ReviewerKind",
    "build_explanation_quality",
    "build_review_form",
    "read_reviews",
    "render_explanation_quality",
]
