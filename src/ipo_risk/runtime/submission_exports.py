"""Evidence and Human Review exports for the submission bundle.

CH-6 asks for Evidence and Human Review exports alongside the case reports. Both
are flat, readable views of what one run produced: every Evidence item a risk
actually cites, and every reviewer decision recorded against that analysis.

Neither export adds anything. The Evidence rows carry the ids, pages and
retrieval metadata the run recorded, with an explicit note when the parser
produced no bbox; the Human Review export reads the reviewer sidecar and, when
nobody has reviewed the case, says exactly that instead of rendering an empty
table that could read as approval.

The reviewer sidecar stays separate from the machine result here as it is in
storage: this module reads both, and merges neither.
"""

from __future__ import annotations

import csv
import io
from typing import Any, Iterable, Sequence

from ipo_risk.schemas.competition_runtime import HumanReview


EVIDENCE_EXPORT_SCHEMA_VERSION = "v045_role_e_evidence_export_v1"
HUMAN_REVIEW_EXPORT_SCHEMA_VERSION = "v045_role_e_human_review_export_v1"

EVIDENCE_EXPORT_COLUMNS = (
    "case_id",
    "stock_code",
    "risk_id",
    "risk_code",
    "risk_level",
    "verification_status",
    "agent_name",
    "evidence_id",
    "page",
    "section",
    "source_type",
    "has_bbox",
    "retriever",
    "relevance_score",
    "snippet",
)

# The full Evidence text already ships inside analysis_result.json; the export is
# a navigation aid, so it carries a bounded snippet rather than restating the
# whole chunk of a licensed prospectus.
SNIPPET_LIMIT = 240


def _snippet(text: str) -> str:
    flat = " ".join((text or "").split())
    return flat if len(flat) <= SNIPPET_LIMIT else f"{flat[:SNIPPET_LIMIT]}…"


def build_evidence_export(
    *, case_id: str, stock_code: str, result: dict[str, Any]
) -> dict[str, Any]:
    """One row per (risk, Evidence) pair the run actually asserted."""

    rows: list[dict[str, Any]] = []
    for group in ("verified_risks", "pending_risks", "rejected_risks"):
        for risk in result.get(group, []):
            for evidence in risk.get("evidence", []):
                metadata = evidence.get("metadata") or {}
                rows.append(
                    {
                        "case_id": case_id,
                        "stock_code": stock_code,
                        "risk_id": risk.get("risk_id"),
                        "risk_code": risk.get("risk_code"),
                        "risk_level": risk.get("level"),
                        "verification_status": risk.get("verification_status"),
                        "agent_name": risk.get("agent_name"),
                        "evidence_id": evidence.get("evidence_id"),
                        "page": evidence.get("page"),
                        "section": evidence.get("section"),
                        "source_type": evidence.get("source_type"),
                        "has_bbox": bool(evidence.get("bbox")),
                        "retriever": metadata.get("retriever"),
                        "relevance_score": evidence.get("relevance_score"),
                        "snippet": _snippet(evidence.get("text", "")),
                    }
                )
    with_page = sum(1 for row in rows if row["page"] is not None)
    with_bbox = sum(1 for row in rows if row["has_bbox"])
    return {
        "schema_version": EVIDENCE_EXPORT_SCHEMA_VERSION,
        "case_id": case_id,
        "stock_code": stock_code,
        "columns": list(EVIDENCE_EXPORT_COLUMNS),
        "evidence_row_count": len(rows),
        "distinct_evidence_ids": len({row["evidence_id"] for row in rows}),
        "rows_with_page": with_page,
        "rows_with_bbox": with_bbox,
        "grounding_note": (
            "Every exported Evidence item carries the physical page the parser recorded. "
            "The parser produces no bbox, so no box is drawn and none is inferred."
            if with_bbox == 0
            else "Page grounding is present; bbox is present where the parser produced one."
        ),
        "rows": rows,
    }


def render_evidence_export_csv(export: dict[str, Any]) -> str:
    """The same rows as CSV, for a reviewer who wants a spreadsheet."""

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(EVIDENCE_EXPORT_COLUMNS), lineterminator="\n")
    writer.writeheader()
    for row in export["rows"]:
        writer.writerow({column: row.get(column) for column in EVIDENCE_EXPORT_COLUMNS})
    return buffer.getvalue()


def build_human_review_export(
    *,
    case_id: str,
    analysis_id: str,
    reviews: Sequence[HumanReview] | Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Reviewer decisions for one analysis, or an explicit statement of none.

    An unreviewed case is reported as unreviewed. Rendering an empty decision
    table would let "nobody looked at this" read as "nobody objected".
    """

    records: list[dict[str, Any]] = []
    for review in reviews:
        payload = review.model_dump(mode="json") if isinstance(review, HumanReview) else dict(review)
        records.append(
            {
                "review_id": payload.get("review_id"),
                "target_id": payload.get("target_id"),
                "original_machine_status": payload.get("original_machine_status"),
                "decision": payload.get("decision"),
                "post_review_status": payload.get("post_review_status"),
                "reviewer_id": payload.get("reviewer_id"),
                "reviewer_note": payload.get("reviewer_note", ""),
                "evidence_id": payload.get("evidence_id"),
                "page": payload.get("page"),
                "reviewed_at": payload.get("reviewed_at"),
            }
        )
    decisions: dict[str, int] = {}
    for record in records:
        key = str(record["decision"])
        decisions[key] = decisions.get(key, 0) + 1
    return {
        "schema_version": HUMAN_REVIEW_EXPORT_SCHEMA_VERSION,
        "case_id": case_id,
        "analysis_id": analysis_id,
        "review_count": len(records),
        "reviewed": bool(records),
        "decision_counts": decisions,
        "distinct_reviewers": sorted({str(record["reviewer_id"]) for record in records}),
        "statement": (
            "Reviewer decisions are a sidecar: they never modified any RiskItem, Evidence or "
            "machine conclusion in this run."
            if records
            else "No human review was recorded for this case. This is an absence of review, not "
            "an approval."
        ),
        "reviews": records,
    }


__all__ = [
    "EVIDENCE_EXPORT_COLUMNS",
    "EVIDENCE_EXPORT_SCHEMA_VERSION",
    "HUMAN_REVIEW_EXPORT_SCHEMA_VERSION",
    "SNIPPET_LIMIT",
    "build_evidence_export",
    "build_human_review_export",
    "render_evidence_export_csv",
]
