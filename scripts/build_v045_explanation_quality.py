"""Build the M4 explanation-quality review form, or the artifact from filled-in reviews.

Two steps, because the scores come from people and not from this command.

``--emit-form`` writes an empty review form seeded from the final case matrix:
each case carries its own run facts and points at the case report and the
reasoning log, with every score left null. Reviewers fill in the ``reviews``
list -- at least two of them, independently, per the frozen rubric.

Running without ``--emit-form`` reads those reviews back and writes
``explanation_quality.json``. The thresholds come from the frozen metric
protocol, not from this script, and an unreviewed or single-reviewer case leaves
the metric unmet with the reason named. No score is ever produced here.

The reviewer file is local working state and stays out of Git; the built
artifact ships with the submission.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ipo_risk.runtime.explanation_quality import (
    DEFAULT_PROTOCOL_PATH,
    ExplanationQualityRubric,
    build_explanation_quality,
    build_review_form,
    read_reviews,
    render_explanation_quality,
)

DEFAULT_MATRIX_DIR = Path("reports/v045_role_e")
DEFAULT_REVIEWS = Path("data/explanation_quality/reviews.json")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--role-e-dir", type=Path, default=DEFAULT_MATRIX_DIR)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL_PATH)
    parser.add_argument("--reviews", type=Path, default=DEFAULT_REVIEWS)
    parser.add_argument(
        "--emit-form",
        action="store_true",
        help="write the empty review form to --reviews instead of building the artifact",
    )
    parser.add_argument("--force", action="store_true", help="overwrite an existing review file")
    arguments = parser.parse_args()

    rubric = ExplanationQualityRubric.load(arguments.protocol)
    summary_path = arguments.role_e_dir / "summary.json"
    if not summary_path.is_file():
        raise SystemExit(
            f"{summary_path} is missing; run scripts/run_v04_role_e_demo.py first so the review "
            "form describes real cases"
        )
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    if arguments.emit_form:
        if arguments.reviews.exists() and not arguments.force:
            raise SystemExit(
                f"{arguments.reviews} already exists; pass --force to overwrite it. Reviewer input "
                "is never silently replaced."
            )
        form = build_review_form(rubric=rubric, matrix_summary=summary)
        arguments.reviews.parent.mkdir(parents=True, exist_ok=True)
        arguments.reviews.write_text(
            json.dumps(form, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"review form written to {arguments.reviews} ({len(form['cases'])} case(s), 0 scores)")
        return 0

    if not arguments.reviews.is_file():
        raise SystemExit(
            f"{arguments.reviews} is missing; run this command with --emit-form first, then have "
            f"at least {rubric.minimum_human_reviewers} reviewers fill it in"
        )
    reviews = read_reviews(arguments.reviews)
    declared = [
        case["case_id"]
        for case in summary.get("cases", [])
        if isinstance(case, dict) and case.get("case_id")
    ]
    artifact = build_explanation_quality(
        rubric=rubric, reviews=reviews, declared_case_ids=declared
    )
    output = arguments.role_e_dir / "explanation_quality.json"
    output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    (arguments.role_e_dir / "explanation_quality.md").write_text(
        render_explanation_quality(artifact), encoding="utf-8"
    )
    print(json.dumps({key: artifact[key] for key in (
        "metric_protocol_version",
        "declared_case_count",
        "reviewed_case_count",
        "mean_score",
        "min_case_score",
        "satisfied",
        "unmet_conditions",
        "verdict",
    )}, ensure_ascii=False, indent=2))
    # An unmet metric is a reported state, not a crash: the artifact is the point.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
