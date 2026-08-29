from __future__ import annotations

import json
from pathlib import Path
import zipfile

from ipo_risk.runtime.final_acceptance import (
    CommandResult,
    build_acceptance,
    command_specs,
    package_preflight_evidence,
    write_outputs,
)


def _command(name: str, passed: bool = True) -> CommandResult:
    return CommandResult(name, (name,), 0 if passed else 1, passed, 0.01, "", "")


def _git_repo(path: Path) -> None:
    import subprocess

    subprocess.run(("git", "init", "-q"), cwd=path, check=True)
    subprocess.run(("git", "config", "user.email", "test@example.com"), cwd=path, check=True)
    subprocess.run(("git", "config", "user.name", "Test"), cwd=path, check=True)
    (path / "README.md").write_text("fixture\n", encoding="utf-8")
    subprocess.run(("git", "add", "README.md"), cwd=path, check=True)
    subprocess.run(("git", "commit", "-qm", "fixture"), cwd=path, check=True)


def test_final_acceptance_runtime_audits_are_read_only() -> None:
    specs = {item.name: item for item in command_specs()}
    assert "--no-write" in specs["dynamic_market_strict"].argv
    assert "--no-write" in specs["dynamic_model_strict"].argv
    assert specs["product_capability_acceptance"].argv[-1] == (
        "scripts/check_final_product_capabilities.py"
    )


def test_missing_formal_artifacts_remain_blockers(tmp_path: Path) -> None:
    _git_repo(tmp_path)
    commands = [
        _command("compileall"),
        _command("full_pytest"),
        _command("project_validator"),
        _command("competition_data_validator"),
        _command("competition_runtime_validator"),
        _command("role_d_v2_release"),
        _command("product_runtime"),
        _command("team_clone_ready"),
        _command("dynamic_market_strict", False),
        _command("git_diff_check"),
        _command("tracked_worktree_clean"),
    ]
    result = build_acceptance(
        tmp_path,
        commands,
        ci_status="pass",
        ci_evidence_urls=("https://github.com/example/repo/actions/runs/1",),
    )
    assert result["final_status"] == "NOT_COMPETITION_READY"
    assert result["competition_ready"] is False
    assert any(item.startswith("G2:") for item in result["blockers"])
    assert any(item.startswith("G7:") for item in result["blockers"])
    assert result["governance"]["validation_opened_by_preflight"] is False


def test_preflight_zip_is_explicitly_not_final(tmp_path: Path) -> None:
    payload = {
        "final_status": "NOT_COMPETITION_READY",
        "main_sha": "a" * 40,
        "generated_at_utc": "2026-08-29T00:00:00+00:00",
        "gates": [],
        "blockers": ["G2: missing"],
        "commands": [],
    }
    output = tmp_path / "evidence"
    write_outputs(output, payload)
    archive = tmp_path / "preflight.zip"
    manifest = package_preflight_evidence(output, archive)
    assert manifest["final_submission"] is False
    with zipfile.ZipFile(archive) as bundle:
        assert "README_NOT_FINAL.txt" in bundle.namelist()
        assert b"NOT A FINAL COMPETITION SUBMISSION" in bundle.read("README_NOT_FINAL.txt")
        parsed = json.loads(bundle.read("final_acceptance.json"))
        assert parsed["final_status"] == "NOT_COMPETITION_READY"


def test_dynamic_market_gate_uses_persisted_summary_and_strict_command(tmp_path: Path) -> None:
    _git_repo(tmp_path)
    audit_dir = tmp_path / "reports/v046_market_runtime"
    audit_dir.mkdir(parents=True)
    (audit_dir / "historical_market_runtime_audit.json").write_text(
        json.dumps(
            {
                "historical_summary": {
                    "governed_case_count": 562,
                    "integrity_violation_count": 0,
                    "error": 0,
                    "by_failure_code": {},
                    "by_model_handoff": {"bound": 550, "not_projectable": 12},
                }
            }
        ),
        encoding="utf-8",
    )
    commands = [
        _command("compileall"),
        _command("full_pytest"),
        _command("project_validator"),
        _command("competition_data_validator"),
        _command("competition_runtime_validator"),
        _command("role_d_v2_release"),
        _command("product_runtime"),
        _command("team_clone_ready"),
        _command("dynamic_market_strict"),
        _command("git_diff_check"),
        _command("tracked_worktree_clean"),
    ]
    result = build_acceptance(
        tmp_path,
        commands,
        ci_status="pass",
        ci_evidence_urls=("https://github.com/example/repo/actions/runs/1",),
    )
    market_gate = next(item for item in result["gates"] if item["gate"] == "G3")
    assert market_gate["passed"] is True
    assert market_gate["evidence"]["by_model_handoff"] == {
        "bound": 550,
        "not_projectable": 12,
    }
