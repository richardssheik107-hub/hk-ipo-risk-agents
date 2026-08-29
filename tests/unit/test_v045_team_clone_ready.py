from __future__ import annotations

from scripts.check_v045_runtime_equivalence import build_report, parse_name_status
from scripts.check_v045_team_clone_ready import evaluate


def test_runtime_equivalence_accepts_only_role_d_ci_workflow() -> None:
    changes = parse_name_status("A\t.github/workflows/role-d-runtime.yml\n")
    report = build_report(recorded_sha="a" * 40, release_sha="b" * 40, changes=changes)

    assert report["runtime_equivalent"] is True
    assert report["runtime_files_changed"] == []
    assert report["rerun_required"] is False


def test_runtime_equivalence_fails_closed_on_runtime_change() -> None:
    report = build_report(
        recorded_sha="a" * 40,
        release_sha="b" * 40,
        changes=[{"status": "M", "path": "src/ipo_risk/workflows/competition.py"}],
    )

    assert report["runtime_equivalent"] is False
    assert report["rerun_required"] is True


def test_team_ready_evaluation_rejects_stage_or_hash_failure() -> None:
    snapshot = {
        "runtime_equivalent": True,
        "runtime_rerun_required": False,
        "case_count": 3,
        "cases": {str(i): {"final_supervisor_judgement_present": True} for i in range(3)},
        "aggregate": {
            "market_available": 3,
            "model_available": 3,
            "gate_e1_satisfied": 3,
            "real_provider_accepted": 3,
            "first_attempt_accepted": 3,
            "severity_floor_respected": 3,
            "m3_at_one": 3,
            "scope_corrections": 0,
            "fallback_used": 0,
            "scope_violation_count": 0,
            "budget_skipped": 0,
            "seven_stage_available": 20,
            "seven_stage_required": 21,
        },
        "evidence": {"rendered": 17, "required": 17, "precise": 17, "precise_rate": 1.0},
        "demo": {"cases": 3, "bytes": 1},
    }

    blockers = evaluate(snapshot, {"passed": False})

    assert "one or more replay stages are unavailable" in blockers
    assert "canonical bundle hash verification failed" in blockers


def test_stage_gate_requires_exactly_seven_available_per_case() -> None:
    snapshot = {
        "runtime_equivalent": True,
        "runtime_rerun_required": False,
        "case_count": 3,
        "cases": {str(i): {"final_supervisor_judgement_present": True} for i in range(3)},
        "aggregate": {
            "market_available": 3,
            "model_available": 3,
            "gate_e1_satisfied": 3,
            "real_provider_accepted": 3,
            "first_attempt_accepted": 3,
            "severity_floor_respected": 3,
            "m3_at_one": 3,
            "scope_corrections": 0,
            "fallback_used": 0,
            "scope_violation_count": 0,
            "budget_skipped": 0,
            "seven_stage_available": 21,
            "seven_stage_required": 21,
        },
        "evidence": {"rendered": 17, "required": 17, "precise": 17, "precise_rate": 1.0},
        "demo": {"cases": 3, "bytes": 1},
    }

    assert evaluate(snapshot, {"passed": True}) == []
