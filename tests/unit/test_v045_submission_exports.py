"""The Evidence and Human Review exports must not say more than the run did.

The Evidence export is a flat view of what the risks actually cite -- so it may
not contain an Evidence item no risk cited, and it must state plainly that the
parser produced no bbox rather than leaving the column ambiguous.

The Human Review export has one job beyond listing decisions: an unreviewed case
must read as unreviewed. An empty decision table would let "nobody looked at
this" pass for "nobody objected", which is exactly the claim the reviewer
sidecar exists to prevent.
"""

from __future__ import annotations

import csv
import io

from ipo_risk.runtime.submission_exports import (
    EVIDENCE_EXPORT_COLUMNS,
    SNIPPET_LIMIT,
    build_evidence_export,
    build_human_review_export,
    render_evidence_export_csv,
)
from ipo_risk.schemas.competition_runtime import HumanReview, HumanReviewDecision


EVIDENCE_ID = "67ef7838-6af2-5ebd-8a5c-7a46c39bb804"
RISK_ID = "69066732-91e7-5238-850d-b162104dcab9"


def _evidence(**overrides) -> dict:
    evidence = {
        "evidence_id": EVIDENCE_ID,
        "page": 563,
        "section": "financial_information",
        "source_type": "prospectus",
        "bbox": None,
        "relevance_score": 1.0,
        "text": "期末現金及現金等價物 77,208",
        "metadata": {"retriever": "keyword"},
    }
    evidence.update(overrides)
    return evidence


def _result(**overrides) -> dict:
    result = {
        "verified_risks": [
            {
                "risk_id": RISK_ID,
                "risk_code": "cash_runway",
                "level": "critical",
                "verification_status": "verified",
                "agent_name": "financial",
                "evidence": [_evidence()],
            }
        ],
        "pending_risks": [],
        "rejected_risks": [],
    }
    result.update(overrides)
    return result


def _export(result: dict | None = None) -> dict:
    return build_evidence_export(
        case_id="ipo_2024_02410", stock_code="2410.HK", result=result or _result()
    )


def test_every_exported_row_belongs_to_a_risk_the_run_asserted() -> None:
    export = _export()
    assert export["evidence_row_count"] == 1
    row = export["rows"][0]
    assert row["risk_id"] == RISK_ID
    assert row["evidence_id"] == EVIDENCE_ID
    assert row["page"] == 563
    assert row["retriever"] == "keyword"


def test_a_run_with_no_risk_exports_no_evidence() -> None:
    """Retrieved-but-unused Evidence is not a finding, so it is not exported."""
    export = _export(_result(verified_risks=[]))
    assert export["evidence_row_count"] == 0
    assert export["rows"] == []


def test_pending_and_rejected_risks_are_exported_too() -> None:
    result = _result(
        pending_risks=[
            {
                "risk_id": "risk-2",
                "risk_code": "continuous_loss",
                "level": "high",
                "verification_status": "pending",
                "agent_name": "financial",
                "evidence": [_evidence(evidence_id="e-2", page=120)],
            }
        ]
    )
    export = _export(result)
    assert export["evidence_row_count"] == 2
    assert {row["verification_status"] for row in export["rows"]} == {"verified", "pending"}


def test_missing_bbox_is_stated_rather_than_left_ambiguous() -> None:
    export = _export()
    assert export["rows_with_bbox"] == 0
    assert export["rows_with_page"] == 1
    assert "no box is drawn and none is inferred" in export["grounding_note"]


def test_a_present_bbox_is_reported_as_present() -> None:
    export = _export(
        _result(
            verified_risks=[
                {
                    "risk_id": RISK_ID,
                    "risk_code": "cash_runway",
                    "level": "critical",
                    "verification_status": "verified",
                    "agent_name": "financial",
                    "evidence": [_evidence(bbox=[1.0, 2.0, 3.0, 4.0])],
                }
            ]
        )
    )
    assert export["rows_with_bbox"] == 1
    assert export["rows"][0]["has_bbox"] is True


def test_the_snippet_is_bounded_and_single_line() -> None:
    """The full text already ships in analysis_result.json; this is a pointer."""
    long_text = "现金 " * 400
    export = _export(
        _result(
            verified_risks=[
                {
                    "risk_id": RISK_ID,
                    "risk_code": "cash_runway",
                    "level": "critical",
                    "verification_status": "verified",
                    "agent_name": "financial",
                    "evidence": [_evidence(text=f"line one\nline two {long_text}")],
                }
            ]
        )
    )
    snippet = export["rows"][0]["snippet"]
    assert "\n" not in snippet
    assert len(snippet) <= SNIPPET_LIMIT + 1


def test_the_csv_carries_the_declared_columns_in_order() -> None:
    rendered = render_evidence_export_csv(_export())
    reader = csv.DictReader(io.StringIO(rendered))
    assert reader.fieldnames == list(EVIDENCE_EXPORT_COLUMNS)
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["evidence_id"] == EVIDENCE_ID


# --- human review -----------------------------------------------------------


def _review(**overrides) -> HumanReview:
    payload = {
        "case_id": "ipo_2024_02410",
        "run_id": "run-1",
        "target_id": RISK_ID,
        "original_machine_status": "verified",
        "decision": HumanReviewDecision.ACCEPT,
        "post_review_status": "human_accepted",
        "reviewer_id": "reviewer_1",
        "reviewer_note": "runway calculation checks out",
        "evidence_id": EVIDENCE_ID,
        "page": 563,
    }
    payload.update(overrides)
    return HumanReview.model_validate(payload)


def test_an_unreviewed_case_is_exported_as_unreviewed() -> None:
    export = build_human_review_export(case_id="ipo_2024_02460", analysis_id="a-1")
    assert export["reviewed"] is False
    assert export["review_count"] == 0
    assert export["reviews"] == []
    assert "not an approval" in export["statement"]


def test_recorded_decisions_are_exported_with_their_reviewer_and_target() -> None:
    export = build_human_review_export(
        case_id="ipo_2024_02410",
        analysis_id="a-1",
        reviews=[_review(), _review(decision=HumanReviewDecision.NEEDS_FOLLOW_UP)],
    )
    assert export["reviewed"] is True
    assert export["review_count"] == 2
    assert export["decision_counts"] == {"accept": 1, "needs_follow_up": 1}
    assert export["distinct_reviewers"] == ["reviewer_1"]
    assert export["reviews"][0]["target_id"] == RISK_ID


def test_the_export_states_that_review_never_altered_the_machine_result() -> None:
    export = build_human_review_export(
        case_id="ipo_2024_02410", analysis_id="a-1", reviews=[_review()]
    )
    assert "never modified" in export["statement"]
    assert export["reviews"][0]["original_machine_status"] == "verified"
    assert export["reviews"][0]["post_review_status"] == "human_accepted"
