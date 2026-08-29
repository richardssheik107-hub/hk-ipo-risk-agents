"""Repository-level competition acceptance preflight and evidence bundle.

This module does not infer an open release gate as PASS and never opens the
Validation or Blind cohorts.  It records the evidence already available in a
checkout, runs the declared offline validation commands, and writes a concise
machine-readable and human-readable release report.  When the project is not
ready it may create a clearly labelled *preflight evidence* ZIP; that archive is
not the final competition submission.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Iterable
import zipfile


SCHEMA_VERSION = "competition_final_acceptance_preflight_v1"
REQUIRED_CAPABILITIES = (
    "core_pipeline_progress",
    "text_embellishment",
    "related_party_transaction",
    "comparable_ipo_valuation",
    "evidence_screenshot",
    "single_batch_report",
    "api_ui",
    "dynamic_new_ipo",
)


@dataclass(frozen=True)
class CommandSpec:
    name: str
    argv: tuple[str, ...]
    expect_empty_stdout: bool = False


@dataclass(frozen=True)
class CommandResult:
    name: str
    argv: tuple[str, ...]
    exit_code: int | None
    passed: bool
    duration_seconds: float
    stdout_tail: str
    stderr_tail: str
    skipped_reason: str | None = None


def _sha(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _clean_output(text: str, repo_root: Path, *, limit: int = 5000) -> str:
    clean = text.replace(str(repo_root.resolve()), "<repo>")
    return clean[-limit:]


def command_specs(*, include_full_tests: bool = True) -> list[CommandSpec]:
    python = sys.executable
    specs = [
        CommandSpec("compileall", (python, "-m", "compileall", "-q", "app", "src", "scripts")),
    ]
    if include_full_tests:
        specs.append(CommandSpec("full_pytest", (python, "-m", "pytest", "-q")))
    specs.extend(
        [
            CommandSpec("project_validator", (python, "scripts/validate_project.py")),
            CommandSpec("competition_data_validator", (python, "scripts/validate_competition_data.py")),
            CommandSpec("competition_runtime_validator", (python, "scripts/validate_competition_runtime.py")),
            CommandSpec("role_d_v2_release", (python, "scripts/check_v045_role_d_v2_release.py")),
            CommandSpec("product_runtime", (python, "scripts/check_v045_product_runtime.py")),
            CommandSpec("team_clone_ready", (python, "scripts/check_v045_team_clone_ready.py")),
            CommandSpec(
                "dynamic_market_strict",
                (python, "scripts/run_market_runtime_audit.py", "--strict", "--no-write"),
            ),
            CommandSpec(
                "dynamic_model_strict",
                (
                    python,
                    "scripts/run_dynamic_model_runtime_audit.py",
                    "--strict",
                    "--no-write",
                ),
            ),
            CommandSpec("git_diff_check", ("git", "diff", "--check"), True),
            CommandSpec(
                "tracked_worktree_clean",
                ("git", "status", "--porcelain", "--untracked-files=no"),
                True,
            ),
        ]
    )
    return specs


def run_command(repo_root: Path, spec: CommandSpec) -> CommandResult:
    started = time.monotonic()
    completed = subprocess.run(
        spec.argv,
        cwd=repo_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    passed = completed.returncode == 0 and (
        not spec.expect_empty_stdout or not stdout.strip()
    )
    return CommandResult(
        name=spec.name,
        argv=spec.argv,
        exit_code=completed.returncode,
        passed=passed,
        duration_seconds=round(time.monotonic() - started, 3),
        stdout_tail=_clean_output(stdout, repo_root),
        stderr_tail=_clean_output(stderr, repo_root),
    )


def skipped_full_test_result() -> CommandResult:
    return CommandResult(
        name="full_pytest",
        argv=(sys.executable, "-m", "pytest", "-q"),
        exit_code=None,
        passed=False,
        duration_seconds=0.0,
        stdout_tail="",
        stderr_tail="",
        skipped_reason="full test suite was explicitly skipped; final G0 cannot pass",
    )


def _gate(
    gate_id: str,
    title: str,
    passed: bool,
    evidence: dict[str, Any],
    blockers: Iterable[str] = (),
) -> dict[str, Any]:
    blocker_list = [str(item) for item in blockers]
    return {
        "gate": gate_id,
        "title": title,
        "status": "PASS" if passed and not blocker_list else "BLOCKED",
        "passed": passed and not blocker_list,
        "evidence": evidence,
        "blockers": blocker_list,
    }


def _role_b_gate(repo_root: Path) -> dict[str, Any]:
    summary_path = repo_root / "reports/v045_role_b/document_benchmark_summary.json"
    summary = _read_json(summary_path)
    if summary is None:
        return _gate(
            "G2",
            "ALL79 Document Intelligence",
            False,
            {"summary_path": "reports/v045_role_b/document_benchmark_summary.json"},
            ("formal ALL79 real-LLM Development benchmark artifact is missing",),
        )
    risk = summary.get("risk_extraction") or {}
    evidence = summary.get("evidence_coverage") or {}
    m1 = risk.get("official_aligned_accuracy")
    m2 = evidence.get("coverage_recall")
    evaluated = int(summary.get("evaluated_case_count") or 0)
    real_llm = int(summary.get("real_llm_cases") or 0)
    checks = {
        "full_79": evaluated == 79,
        "real_llm_79": real_llm == 79,
        "m1_at_least_0_80": isinstance(m1, (int, float)) and not isinstance(m1, bool) and m1 >= 0.80,
        "m2_at_least_0_85": isinstance(m2, (int, float)) and not isinstance(m2, bool) and m2 >= 0.85,
        "existing_gold_unchanged": summary.get("existing_gold_modified") is False,
        "blind_untouched": summary.get("blind_2025_outcome_accessed") is False,
    }
    blockers = [name for name, passed in checks.items() if not passed]
    return _gate(
        "G2",
        "ALL79 Document Intelligence",
        all(checks.values()),
        {"m1": m1, "m2": m2, "evaluated_cases": evaluated, "real_llm_cases": real_llm, "checks": checks},
        blockers,
    )


def _dynamic_model_gate(repo_root: Path, command_map: dict[str, CommandResult]) -> dict[str, Any]:
    manifest_path = repo_root / "reports/frozen/v045_role_d_v2_promotion_manifest.json"
    manifest = _read_json(manifest_path) or {}
    promotion = manifest.get("promotion_record") or {}
    promotion_effective = all(
        (
            manifest.get("formal_gate_passed") is True,
            promotion.get("decision") == "promote_v2",
            manifest.get("status") == "complete_frozen",
            command_map.get("role_d_v2_release") is not None,
            command_map["role_d_v2_release"].passed,
        )
    )
    audit_path = repo_root / "reports/v046_dynamic_model_runtime/dynamic_model_runtime_audit.json"
    audit = _read_json(audit_path)
    # The artifact alone could be stale, so the audit is re-run here and both the
    # fresh exit status and the committed evidence have to agree.
    audit_command = command_map.get("dynamic_model_strict")
    dynamic_ok = bool(
        audit_command is not None
        and audit_command.passed
        and audit
        and audit.get("status") == "pass"
        and audit.get("runtime_inference") is True
        and audit.get("native_shap") is True
        and audit.get("uses_frozen_model") is True
        and audit.get("per_case_handoff_only") is False
        and audit.get("blind_2025_y_accessed") is False
    )
    blockers: list[str] = []
    if not promotion_effective:
        blockers.append("Role-D V2 promotion identity/strict checker is not PASS")
    if not dynamic_ok:
        blockers.append("real frozen-model dynamic inference + native SHAP audit is missing or not PASS")
    published_parity = (audit or {}).get("published_parity") or {}
    return _gate(
        "G4",
        "Dynamic Model / SHAP",
        promotion_effective and dynamic_ok,
        {
            "promotion_effective": promotion_effective,
            "promotion_manifest": "reports/frozen/v045_role_d_v2_promotion_manifest.json",
            "dynamic_runtime_audit": "reports/v046_dynamic_model_runtime/dynamic_model_runtime_audit.json",
            "dynamic_runtime_passed": dynamic_ok,
            "historical_inference_available": (
                ((audit or {}).get("historical_summary") or {}).get("inference_available")
            ),
            "available_outside_the_per_case_handoff": (
                ((audit or {}).get("historical_summary") or {}).get(
                    "available_outside_the_per_case_handoff"
                )
            ),
            "published_parity_mismatch_count": published_parity.get("mismatch_count"),
        },
        blockers,
    )


def _declared_artifact_gate(
    repo_root: Path,
    *,
    gate_id: str,
    title: str,
    relative_path: str,
    predicate,
    missing_blocker: str,
) -> dict[str, Any]:
    payload = _read_json(repo_root / relative_path)
    passed = bool(payload and predicate(payload))
    return _gate(
        gate_id,
        title,
        passed,
        {"artifact": relative_path, "present": payload is not None},
        () if passed else (missing_blocker,),
    )


def build_acceptance(
    repo_root: Path,
    command_results: list[CommandResult],
    *,
    ci_status: str,
    ci_evidence_urls: Iterable[str] = (),
) -> dict[str, Any]:
    command_map = {item.name: item for item in command_results}
    ci_urls = tuple(str(item) for item in ci_evidence_urls)
    head = subprocess.run(
        ("git", "rev-parse", "HEAD"), cwd=repo_root, capture_output=True, text=True, check=False
    ).stdout.strip()
    command_pass = bool(command_results) and all(item.passed for item in command_results)
    ci_pass = ci_status == "pass" and bool(ci_urls)
    g0_blockers: list[str] = []
    if not command_pass:
        g0_blockers.append("one or more required local validation commands did not PASS")
    if not ci_pass:
        g0_blockers.append("latest-main GitHub CI PASS evidence was not supplied")
    g0 = _gate(
        "G0",
        "Runtime / contracts / CI",
        command_pass and ci_pass,
        {"local_commands_passed": command_pass, "ci_status": ci_status, "ci_evidence_urls": list(ci_urls)},
        g0_blockers,
    )

    g1_commands = ("product_runtime", "team_clone_ready")
    g1_ok = all(command_map.get(name) and command_map[name].passed for name in g1_commands)
    g1 = _gate(
        "G1",
        "Stable final-three baseline",
        g1_ok,
        {"required_commands": list(g1_commands)},
        () if g1_ok else ("product runtime or team clone baseline is not PASS",),
    )

    market = _read_json(repo_root / "reports/v046_market_runtime/historical_market_runtime_audit.json") or {}
    market_summary = market.get("historical_summary") or {}
    market_command_ok = bool(command_map.get("dynamic_market_strict") and command_map["dynamic_market_strict"].passed)
    g3_ok = (
        market_command_ok
        and market_summary.get("governed_case_count") == 562
        and market_summary.get("integrity_violation_count") == 0
        and market_summary.get("error") == 0
        and not (market_summary.get("by_failure_code") or {})
    )
    g3 = _gate(
        "G3",
        "Dynamic Market-X",
        g3_ok,
        {
            "strict_command_passed": market_command_ok,
            "governed_case_count": market_summary.get("governed_case_count"),
            "integrity_violation_count": market_summary.get("integrity_violation_count"),
            "by_model_handoff": market_summary.get("by_model_handoff"),
        },
        () if g3_ok else ("Dynamic Market-X strict audit is not PASS",),
    )

    g5 = _declared_artifact_gate(
        repo_root,
        gate_id="G5",
        title="Final Frontend / Product",
        relative_path="reports/final_status/product_acceptance.json",
        predicate=lambda p: p.get("status") == "pass" and p.get("truthful_channel_states") is True,
        missing_blocker="formal final product acceptance artifact is missing or not PASS",
    )
    g6 = _declared_artifact_gate(
        repo_root,
        gate_id="G6",
        title="Competition capability demonstrations",
        relative_path="reports/final_status/capability_manifest.json",
        predicate=lambda p: p.get("status") == "pass"
        and set(REQUIRED_CAPABILITIES) <= set(p.get("capabilities") or []),
        missing_blocker="auditable competition capability manifest is missing or incomplete",
    )
    freeze = _read_json(repo_root / "reports/final_status/final_freeze_manifest.json")
    validation = _read_json(repo_root / "reports/final_status/one_shot_validation_receipt.json")
    g7_ok = bool(
        freeze
        and freeze.get("status") == "frozen"
        and validation
        and validation.get("status") == "pass"
        and validation.get("one_shot") is True
        and validation.get("post_hoc_tuning") is False
        and validation.get("blind_2025_y_accessed") is False
    )
    g7_blockers: list[str] = []
    if not freeze or freeze.get("status") != "frozen":
        g7_blockers.append("final freeze manifest is missing or not frozen")
    if not validation or validation.get("status") != "pass":
        g7_blockers.append("governed one-shot Validation receipt is missing or not PASS")
    g7 = _gate(
        "G7",
        "Freeze / one-shot Validation / final package",
        g7_ok,
        {
            "freeze_manifest": "reports/final_status/final_freeze_manifest.json",
            "validation_receipt": "reports/final_status/one_shot_validation_receipt.json",
            "final_submission_zip_generated": False,
        },
        g7_blockers,
    )

    gates = [g0, g1, _role_b_gate(repo_root), g3, _dynamic_model_gate(repo_root, command_map), g5, g6, g7]
    blockers = [f"{gate['gate']}: {item}" for gate in gates for item in gate["blockers"]]
    ready_before_package = bool(gates) and all(gate["passed"] for gate in gates)
    # The actual final ZIP remains a post-gate operation.  A preflight report can
    # never claim COMPETITION_READY merely because it packaged its own evidence.
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "main_sha": head,
        "final_status": "READY_FOR_FINAL_PACKAGING" if ready_before_package else "NOT_COMPETITION_READY",
        "competition_ready": False,
        "ready_for_final_packaging": ready_before_package,
        "gates": gates,
        "blockers": blockers,
        "commands": [asdict(item) for item in command_results],
        "governance": {
            "validation_opened_by_preflight": False,
            "blind_2025_y_accessed_by_preflight": False,
            "preflight_evidence_zip_is_final_submission": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Final Submission Acceptance Report",
        "",
        f"- FINAL_STATUS: `{payload['final_status']}`",
        f"- MAIN_SHA: `{payload['main_sha']}`",
        f"- Generated (UTC): `{payload['generated_at_utc']}`",
        "- Validation opened by this preflight: `false`",
        "- 2025 Blind outcome accessed by this preflight: `false`",
        "",
        "## Gate summary",
        "",
        "| Gate | Status | Evidence / blocker |",
        "|---|---|---|",
    ]
    for gate in payload["gates"]:
        detail = "; ".join(gate["blockers"]) if gate["blockers"] else "recorded checks passed"
        lines.append(f"| {gate['gate']} {gate['title']} | {gate['status']} | {detail} |")
    lines.extend(["", "## Required next actions", ""])
    if payload["blockers"]:
        lines.extend(f"- {item}" for item in payload["blockers"])
    else:
        lines.append("- Run the fail-closed final packager and bind its ZIP SHA-256 into G7.")
    lines.extend(
        [
            "",
            "## Local command evidence",
            "",
            "| Command | Result | Duration (s) |",
            "|---|---:|---:|",
        ]
    )
    for command in payload["commands"]:
        status = "PASS" if command["passed"] else "BLOCKED"
        lines.append(f"| {command['name']} | {status} | {command['duration_seconds']} |")
    lines.extend(
        [
            "",
            "> This is a preflight acceptance record. If any Gate is BLOCKED, any accompanying ZIP is evidence-only and must not be submitted as the final competition bundle.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(output_dir: Path, payload: dict[str, Any]) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "final_acceptance.json"
    report_path = output_dir / "FINAL_ACCEPTANCE_REPORT.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(render_markdown(payload), encoding="utf-8")
    sums_path = output_dir / "SHA256SUMS.txt"
    sums_path.write_text(
        "".join(f"{_sha(path)}  {path.name}\n" for path in (json_path, report_path)),
        encoding="utf-8",
    )
    return json_path, report_path, sums_path


def package_preflight_evidence(output_dir: Path, output_zip: Path) -> dict[str, Any]:
    names = ("final_acceptance.json", "FINAL_ACCEPTANCE_REPORT.md", "SHA256SUMS.txt")
    missing = [name for name in names if not (output_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(f"missing preflight evidence: {missing}")
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    notice = (
        "NOT A FINAL COMPETITION SUBMISSION\n"
        "This archive contains acceptance-preflight evidence only. Read "
        "FINAL_ACCEPTANCE_REPORT.md and close every BLOCKED Gate before final packaging.\n"
    )
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.writestr("README_NOT_FINAL.txt", notice)
        for name in names:
            archive.write(output_dir / name, arcname=name)
    return {
        "path": output_zip.as_posix(),
        "sha256": _sha(output_zip),
        "size_bytes": output_zip.stat().st_size,
        "final_submission": False,
        "members": ["README_NOT_FINAL.txt", *names],
    }
