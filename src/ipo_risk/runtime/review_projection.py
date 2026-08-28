"""What a person is allowed to rule on, in machine-readable form.

The Streamlit console and the review API must agree on exactly one thing: which
items in a run are open to human judgement, and what the machine already said
about each of them.  Two independent answers to that question would let the two
surfaces disagree about what was reviewed, which is the one thing a reviewer
sidecar cannot afford.

So the structure lives here and the display labels live in the UI.  These
functions read what the service already produced and reshape it.  None of them
recompute a status, re-derive a level or fill in a missing value: an absent
field stays absent, because a review surface is not allowed to repair backend
facts.
"""

from __future__ import annotations

from typing import Any


REVIEW_TARGET_SCHEMA_VERSION = "v046_role_e_review_target_v1"

# The risk buckets a reviewer may rule on, paired with the neutral ``kind`` the
# API reports.  Rejected risks are included deliberately: a reviewer disagreeing
# with a rejection is exactly the kind of finding the sidecar exists to capture.
RISK_BUCKETS = (
    ("verified_risks", "verified_risk"),
    ("pending_risks", "pending_risk"),
    ("rejected_risks", "rejected_risk"),
)


def _diagnostics(payload: dict[str, Any]) -> dict[str, Any]:
    """Diagnostics from either payload shape.

    The console reads a presenter payload that has lifted ``component_diagnostics``
    to the top level; the API reads a persisted ``IPOAnalysisResult`` where it is
    still nested under ``metadata``.  Accepting both keeps one projection serving
    both surfaces instead of a presenter copy drifting inside the API.
    """

    direct = payload.get("component_diagnostics")
    if direct:
        return direct
    return (payload.get("metadata") or {}).get("component_diagnostics") or {}


def conflicts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return list((_diagnostics(payload).get("conflict_detection") or {}).get("conflicts") or [])


def resolve_identity(payload: dict[str, Any]) -> tuple[str, str]:
    """The ``(case_id, run_id)`` a reviewer decision is filed under.

    The governed competition sidecar is preferred because its ``case_id`` is the
    one every other artifact uses (``ipo_2024_02410``).  Deriving it from the
    stock code instead would file reviews under ``2410.HK`` and leave the
    sidecar unjoinable to the run it describes -- and if the console and the API
    each picked their own source, the two surfaces would write records that
    cannot be compared at all.

    The fallback is only for a payload with no competition sidecar, which is a
    plain non-competition run.
    """

    identity = (
        (_diagnostics(payload).get("competition_runtime") or {}).get("sidecar") or {}
    ).get("identity") or {}
    case_id = str(
        identity.get("case_id")
        or (payload.get("profile") or {}).get("stock_code")
        or payload.get("stock_code")
        or "unknown_case"
    )
    run_id = str(identity.get("run_id") or payload.get("request_id") or "unknown_run")
    return case_id, run_id


def review_targets(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Every risk in the run, plus every conflict the machine did not settle.

    A ``resolved`` conflict is not offered: the machine closed it and there is
    no open question for a person to answer.  Everything else is offered even
    when the machine was confident, because "the machine was sure" is not a
    reason to withhold something from review.
    """

    targets: list[dict[str, Any]] = []
    for bucket, kind in RISK_BUCKETS:
        for risk in payload.get(bucket) or []:
            targets.append(
                {
                    "target_id": risk["risk_id"],
                    "kind": kind,
                    "machine_status": risk.get("verification_status", ""),
                    "detail": risk.get("conclusion", ""),
                    "evidence_ids": [item["evidence_id"] for item in risk.get("evidence") or []],
                    "risk_code": risk.get("risk_code", ""),
                    "risk_level": risk.get("level", ""),
                    "involved_agents": [],
                }
            )
    for conflict in conflicts(payload):
        if conflict.get("status") == "resolved":
            continue
        targets.append(
            {
                "target_id": conflict["conflict_id"],
                "kind": "conflict",
                "machine_status": conflict.get("status", ""),
                "detail": conflict.get("summary", ""),
                "evidence_ids": list(conflict.get("evidence_ids") or []),
                "risk_code": "",
                "risk_level": "",
                "involved_agents": list(conflict.get("involved_agents") or []),
            }
        )
    return targets


def find_review_target(payload: dict[str, Any], target_id: str) -> dict[str, Any] | None:
    """One target by id, or ``None`` when the run has no such thing to review."""

    for target in review_targets(payload):
        if target["target_id"] == target_id:
            return target
    return None


def machine_vs_human(
    payload: dict[str, Any], reviews_by_target: dict[str, Any]
) -> list[dict[str, Any]]:
    """The two verdicts side by side; they are never merged into one.

    An unreviewed target reports ``reviewed: false`` and a null decision rather
    than an empty string, so "nobody looked at this" cannot be read downstream
    as "nobody objected".
    """

    ledger: list[dict[str, Any]] = []
    for target in review_targets(payload):
        review = reviews_by_target.get(target["target_id"])
        ledger.append(
            {
                "target_id": target["target_id"],
                "kind": target["kind"],
                "machine_status": target["machine_status"],
                "reviewed": review is not None,
                "human_decision": review.decision.value if review is not None else None,
                "post_review_status": review.post_review_status if review is not None else None,
                "reviewer_id": review.reviewer_id if review is not None else None,
                "reviewer_note": review.reviewer_note if review is not None else None,
                "reviewed_at": (
                    review.reviewed_at.isoformat()
                    if review is not None and getattr(review, "reviewed_at", None) is not None
                    else None
                ),
            }
        )
    return ledger


__all__ = [
    "REVIEW_TARGET_SCHEMA_VERSION",
    "RISK_BUCKETS",
    "conflicts",
    "find_review_target",
    "machine_vs_human",
    "resolve_identity",
    "review_targets",
]
