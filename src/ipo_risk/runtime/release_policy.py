"""Active release-policy compatibility for the v1.0.0 submission tooling.

The frozen Metric-v2 implementation historically treated M4 human explanation
reviews as a mandatory release gate. The final competition product no longer
requires new human annotation. We intentionally leave the historical
metric/audit implementation intact for provenance and apply this small policy
adapter only at the active submission CLI boundary.

Human Review remains a product capability. Missing human-review artifacts do
not fail release readiness; present optional artifacts remain subject to the
normal security allowlist.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


ACTIVE_RELEASE_POLICY_VERSION = "v100_release_policy_final_docs_demo_bundle_v1"
DEFAULT_ROLE_E_DIR = "reports/v045_demo_bundle"
_OPTIONAL_ROLE_E_CASE_FILES = frozenset({"human_review_export.json"})
_OPTIONAL_ARTIFACT_SUFFIXES = (
    "/explanation_quality.json",
    "/human_review_export.json",
)
_ACTIVE_SUBMISSION_DOCS = (
    "README.md",
    "docs/README.md",
    "docs/RELEASE_NOTES_V1.0.0.md",
    "docs/V1_RELEASE_ACCEPTANCE.md",
    "docs/FINAL_SUBMISSION_STATUS.md",
    "docs/COMPETITION_CLOSURE_PLAN.md",
    "docs/COMPETITION_METRIC_PROTOCOL.md",
    "docs/SUBMISSION_RUNBOOK.md",
    "docs/TEAM_QUICKSTART.md",
    "docs/PROJECT_SPEC.md",
    "docs/ARCHITECTURE.md",
    "docs/DATA_SCHEMA.md",
    "docs/ROLE_D_MODEL_DECISION.md",
    "docs/V045_ROLE_D_FINAL_CLOSURE.md",
    "docs/FRONTEND_JUDGE_FACING_HANDOFF.md",
)


def activate_active_release_policy() -> None:
    """Make legacy discovery match the active v1.0.0 release policy.

    This mutation is process-local and is deliberately performed only by the
    active readiness/packaging CLIs. Library callers of the frozen historical
    audit remain unchanged unless they explicitly opt in.
    """

    from ipo_risk.runtime import submission_readiness as legacy

    legacy.ROLE_E_CASE_REQUIRED = tuple(
        name
        for name in legacy.ROLE_E_CASE_REQUIRED
        if name not in _OPTIONAL_ROLE_E_CASE_FILES
    )
    # Retire historical/superseded planning files from the final ZIP allowlist
    # and ship the v1.0.0 source-of-truth documentation set instead.
    legacy.SUBMISSION_DOCS = _ACTIVE_SUBMISSION_DOCS


def _optional_m4_blocker(blocker: Any) -> bool:
    text = str(blocker)
    return "Role-E M4" in text or "two independent human reviews" in text


def apply_active_release_readiness(readiness: dict[str, Any]) -> dict[str, Any]:
    """Remove only the retired human-review Gate from a readiness result.

    All non-M4 failures remain authoritative. In particular this adapter cannot
    turn a failed Final Supervisor, trace, Market, B, D, CI, security, provenance
    or determinism check into a PASS.
    """

    result = deepcopy(readiness)
    gates = [gate for gate in result.get("gates", []) if isinstance(gate, dict)]
    e_gate = next((gate for gate in gates if gate.get("owner") == "E"), None)
    if e_gate is not None:
        e_blockers = [
            str(blocker)
            for blocker in e_gate.get("blockers", []) or []
            if not _optional_m4_blocker(blocker)
        ]
        e_gate["blockers"] = e_blockers
        e_gate["passed"] = not e_blockers
        details = dict(e_gate.get("details") or {})
        historical = dict(details.get("m4") or {})
        historical.update(
            {
                "required_for_release": False,
                "release_policy": "optional_not_required_for_release",
            }
        )
        details["m4"] = historical
        e_gate["details"] = details

    rules = dict(result.get("rules") or {})
    rules.update(
        {
            "active_release_policy_version": ACTIVE_RELEASE_POLICY_VERSION,
            "human_review_required_for_release": False,
            "m4_required_for_release": False,
        }
    )
    result["rules"] = rules
    result["blockers"] = [
        str(blocker)
        for gate in gates
        for blocker in gate.get("blockers", []) or []
    ]
    ready = bool(gates) and all(gate.get("passed") is True for gate in gates)
    result["competition_ready"] = ready
    result["verdict"] = "COMPETITION_READY" if ready else "NOT_YET_COMPETITION_READY"
    return result


def _is_optional_record(record: dict[str, Any]) -> bool:
    logical = str(record.get("logical_path") or "")
    return logical.endswith(_OPTIONAL_ARTIFACT_SUFFIXES)


def apply_active_release_artifact_index(index: dict[str, Any]) -> dict[str, Any]:
    """Make Human Review artifacts optional without weakening security checks.

    Missing optional records are omitted because the packager's index/allowlist
    equality check must not expect a file that is intentionally absent. A
    present optional diagnostic remains indexed, hash-bound and security-checked.
    """

    result = deepcopy(index)
    records: list[dict[str, Any]] = []
    for raw in result.get("artifacts", []) or []:
        if not isinstance(raw, dict):
            continue
        record = dict(raw)
        if _is_optional_record(record):
            if record.get("exists") is not True:
                continue
            record["required"] = False
            record["gate"] = "OPTIONAL_HUMAN_REVIEW"
        records.append(record)

    records.sort(key=lambda item: str(item.get("logical_path") or ""))
    logical_paths = [str(item.get("logical_path") or "") for item in records]
    duplicates = sorted(
        {path for path in logical_paths if logical_paths.count(path) > 1}
    )
    missing = [
        str(item.get("logical_path") or "")
        for item in records
        if item.get("required") is True and item.get("exists") is not True
    ]
    rejected = [
        str(item.get("logical_path") or "")
        for item in records
        if item.get("exists") is True
        and item.get("allowed_in_submission") is not True
    ]
    result.update(
        {
            "active_release_policy_version": ACTIVE_RELEASE_POLICY_VERSION,
            "artifact_count": len(records),
            "required_count": sum(1 for item in records if item.get("required") is True),
            "present_count": sum(1 for item in records if item.get("exists") is True),
            "missing_count": len(missing),
            "rejected_count": len(rejected),
            "missing": missing,
            "rejected": rejected,
            "duplicate_logical_paths": duplicates,
            "passed": not missing and not rejected and not duplicates,
            "artifacts": records,
        }
    )
    return result
