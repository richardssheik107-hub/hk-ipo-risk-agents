from __future__ import annotations

from ipo_risk.runtime.release_policy import (
    ACTIVE_RELEASE_POLICY_VERSION,
    apply_active_release_artifact_index,
    apply_active_release_readiness,
)


def _gate(owner: str, *, passed: bool = True, blockers: list[str] | None = None) -> dict:
    return {
        "name": f"{owner}1",
        "owner": owner,
        "passed": passed,
        "blockers": list(blockers or []),
        "details": {},
    }


def test_active_release_policy_removes_only_m4_human_review_blockers() -> None:
    readiness = {
        "competition_ready": False,
        "verdict": "NOT_YET_COMPETITION_READY",
        "blockers": [
            "Role-E M4 explanation_quality.json is missing",
            "Role-E M4 lacks two independent human reviews per case or misses its frozen thresholds",
        ],
        "rules": {},
        "gates": [
            _gate("B"),
            _gate("C"),
            _gate("D"),
            {
                **_gate(
                    "E",
                    passed=False,
                    blockers=[
                        "Role-E M4 explanation_quality.json is missing",
                        "Role-E M4 lacks two independent human reviews per case or misses its frozen thresholds",
                    ],
                ),
                "details": {"m4": {"artifact_present": False, "satisfied": False}},
            },
            _gate("A"),
        ],
    }

    result = apply_active_release_readiness(readiness)

    e_gate = next(gate for gate in result["gates"] if gate["owner"] == "E")
    assert e_gate["passed"] is True
    assert e_gate["blockers"] == []
    assert e_gate["details"]["m4"]["required_for_release"] is False
    assert result["competition_ready"] is True
    assert result["verdict"] == "COMPETITION_READY"
    assert result["blockers"] == []
    assert result["rules"]["human_review_required_for_release"] is False
    assert result["rules"]["m4_required_for_release"] is False
    assert result["rules"]["active_release_policy_version"] == ACTIVE_RELEASE_POLICY_VERSION


def test_active_release_policy_never_hides_non_m4_failure() -> None:
    readiness = {
        "competition_ready": False,
        "verdict": "NOT_YET_COMPETITION_READY",
        "blockers": [],
        "rules": {},
        "gates": [
            _gate("B"),
            _gate("C"),
            _gate("D"),
            _gate(
                "E",
                passed=False,
                blockers=[
                    "Role-E M4 explanation_quality.json is missing",
                    "ipo_2024_02410: real-provider Final Supervisor Gate E1 is not satisfied",
                ],
            ),
            _gate("A"),
        ],
    }

    result = apply_active_release_readiness(readiness)

    e_gate = next(gate for gate in result["gates"] if gate["owner"] == "E")
    assert e_gate["passed"] is False
    assert e_gate["blockers"] == [
        "ipo_2024_02410: real-provider Final Supervisor Gate E1 is not satisfied"
    ]
    assert result["competition_ready"] is False


def _record(logical: str, *, exists: bool, required: bool = True, allowed: bool = True) -> dict:
    return {
        "logical_path": logical,
        "exists": exists,
        "required": required,
        "allowed_in_submission": allowed,
        "sha256": "ab" * 32 if exists else None,
        "size_bytes": 1 if exists else None,
        "gate": "M4" if "review" in logical or "explanation" in logical else "E1",
    }


def test_artifact_index_drops_missing_optional_review_artifacts() -> None:
    index = {
        "artifacts": [
            _record("artifacts/role_e/summary.json", exists=True),
            _record("artifacts/role_e/explanation_quality.json", exists=False),
            _record(
                "artifacts/role_e/ipo_2024_02410/human_review_export.json",
                exists=False,
            ),
        ]
    }

    result = apply_active_release_artifact_index(index)

    assert [item["logical_path"] for item in result["artifacts"]] == [
        "artifacts/role_e/summary.json"
    ]
    assert result["required_count"] == 1
    assert result["missing_count"] == 0
    assert result["passed"] is True


def test_present_optional_explanation_artifact_remains_hash_bound_but_not_required() -> None:
    index = {
        "artifacts": [
            _record("artifacts/role_e/summary.json", exists=True),
            _record("artifacts/role_e/explanation_quality.json", exists=True),
        ]
    }

    result = apply_active_release_artifact_index(index)

    optional = next(
        item
        for item in result["artifacts"]
        if item["logical_path"].endswith("explanation_quality.json")
    )
    assert optional["required"] is False
    assert optional["gate"] == "OPTIONAL_HUMAN_REVIEW"
    assert result["required_count"] == 1
    assert result["present_count"] == 2
    assert result["passed"] is True
