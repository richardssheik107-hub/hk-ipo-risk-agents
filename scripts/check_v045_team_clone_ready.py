"""Fail-closed checker for the canonical offline final-three demo replay."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from app.pipeline_stages import resolve_stages  # noqa: E402
from app.presenters import result_payload  # noqa: E402
from ipo_risk.schemas import IPOAnalysisResult  # noqa: E402
from ipo_risk.runtime.demo_replay import (  # noqa: E402
    available_recorded_cases,
    load_recorded_case,
    verify_demo_bundle,
)
from ipo_risk.runtime.submission_readiness import (  # noqa: E402
    _scan_path_for_sensitive_material,
)

SCHEMA_VERSION = "v045_team_clone_ready_v1"
SNAPSHOT_SCHEMA_VERSION = "v045_current_runtime_snapshot_v1"
DEFAULT_BUNDLE = Path("reports/v045_demo_bundle")
DEFAULT_EQUIVALENCE = Path("reports/final_status/runtime_equivalence.json")
DEFAULT_SNAPSHOT = Path("reports/final_status/current_runtime_snapshot.json")
EXPECTED_CASE_COUNT = 3
FORBIDDEN_NAME_PARTS = (
    "llm_journal",
    "raw_provider_response",
    "raw_eod",
    "prospectus.pdf",
)
FORBIDDEN_EXACT_KEYS = {
    "api_key",
    "authorization",
    "access_token",
    "refresh_token",
    "client_secret",
    "raw_response",
    "raw_provider_response",
}


def _json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _nested_forbidden_keys(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            logical = f"{prefix}.{key}" if prefix else str(key)
            if str(key).casefold() in FORBIDDEN_EXACT_KEYS:
                found.append(logical)
            found.extend(_nested_forbidden_keys(child, logical))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_nested_forbidden_keys(child, f"{prefix}[{index}]"))
    return found


def _iter_files(roots: Iterable[Path]) -> Iterable[Path]:
    for root in roots:
        if root.is_file():
            yield root
        elif root.is_dir():
            yield from (path for path in sorted(root.rglob("*")) if path.is_file())


def _security_issues(roots: Iterable[Path]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for path in _iter_files(roots):
        logical = path.as_posix()
        lowered = logical.casefold()
        reasons = list(_scan_path_for_sensitive_material(path))
        if any(part in lowered for part in FORBIDDEN_NAME_PARTS):
            reasons.append("forbidden raw/local artifact name")
        if path.suffix.casefold() == ".json":
            try:
                forbidden = _nested_forbidden_keys(_json(path))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
                forbidden = []
            if forbidden:
                reasons.append("forbidden secret/raw response key(s): " + ", ".join(forbidden))
        if reasons:
            issues.append({"path": logical, "reasons": sorted(set(reasons))})
    return issues


def derive_snapshot(bundle: Path, equivalence: dict[str, Any]) -> dict[str, Any]:
    manifest_path = bundle / "demo_manifest.json"
    manifest = _json(manifest_path)
    summary = _json(bundle / "summary.json")
    screenshot_summary = _json(bundle / "screenshot_summary.json")
    matrix_cases = {str(item["case_id"]): item for item in summary.get("cases", [])}
    cases: dict[str, Any] = {}
    for case_dir in available_recorded_cases(bundle):
        case_id = case_dir.name
        case_summary = matrix_cases[case_id]
        reasoning = _json(case_dir / "agent_reasoning_log.json")
        recheck_budget = reasoning.get("recheck_budget") or {}
        recorded = load_recorded_case(case_dir, summary)
        # Exercise the same schema-validation and presentation path the
        # Streamlit replay uses; resolving stages from the raw service JSON
        # would omit metadata projected by ``result_payload``.
        replay_payload = result_payload(IPOAnalysisResult.model_validate(recorded.result))
        stages = resolve_stages(replay_payload)
        gate = case_summary.get("gate_e1") or {}
        scope = gate.get("out_of_scope_reference_check") or {}
        channels = case_summary.get("channel_states") or {}
        cases[case_id] = {
            "stock_code": case_summary.get("stock_code"),
            "market_available": channels.get("market") == "available",
            "model_available": channels.get("model") == "available",
            "gate_e1_satisfied": gate.get("satisfied") is True,
            "real_provider_accepted": gate.get("successful_llm_arbitration") is True,
            "first_attempt_accepted": scope.get("first_attempt_passed") is True,
            "scope_corrections": int(scope.get("scope_corrections") or 0),
            "fallback_used": gate.get("deterministic_fallback_used") is True,
            "severity_floor_respected": gate.get("severity_floor_respected") is True,
            "scope_violation_count": int(scope.get("out_of_scope_reference_count") or 0),
            "m3": float((case_summary.get("traceability") or {}).get("overall_traceability") or 0),
            "rechecks_attempted": int(recheck_budget.get("attempted") or 0),
            "conflicts_detected": int(recheck_budget.get("conflicts_detected") or 0),
            "budget_skipped": len(recheck_budget.get("conflicts_not_attempted") or []),
            "seven_stage_available": sum(
                1 for stage in stages if getattr(stage.status, "value", stage.status) == "available"
            ),
            "final_supervisor_judgement_present": bool(
                ((recorded.result.get("metadata") or {}).get("final_supervision") or {}).get(
                    "llm_synthesis"
                )
                or (case_dir / "final_supervision.json").is_file()
            ),
        }
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "recorded_runtime_sha": (manifest.get("matrix_identity") or {}).get("code_base_sha"),
        "release_equivalence_head_sha": equivalence.get("release_head_sha"),
        "runtime_equivalent": equivalence.get("runtime_equivalent") is True,
        "runtime_rerun_required": equivalence.get("rerun_required") is True,
        "case_count": len(cases),
        "cases": cases,
        "aggregate": {
            "market_available": sum(item["market_available"] for item in cases.values()),
            "model_available": sum(item["model_available"] for item in cases.values()),
            "gate_e1_satisfied": sum(item["gate_e1_satisfied"] for item in cases.values()),
            "real_provider_accepted": sum(item["real_provider_accepted"] for item in cases.values()),
            "first_attempt_accepted": sum(item["first_attempt_accepted"] for item in cases.values()),
            "scope_corrections": sum(item["scope_corrections"] for item in cases.values()),
            "fallback_used": sum(item["fallback_used"] for item in cases.values()),
            "severity_floor_respected": sum(item["severity_floor_respected"] for item in cases.values()),
            "scope_violation_count": sum(item["scope_violation_count"] for item in cases.values()),
            "m3_at_one": sum(item["m3"] == 1.0 for item in cases.values()),
            "rechecks_attempted": sum(item["rechecks_attempted"] for item in cases.values()),
            "budget_skipped": sum(item["budget_skipped"] for item in cases.values()),
            "seven_stage_available": sum(item["seven_stage_available"] for item in cases.values()),
            "seven_stage_required": 7 * len(cases),
        },
        "evidence": {
            "rendered": int(screenshot_summary.get("screenshot_count") or 0),
            "required": int(screenshot_summary.get("cited_evidence_count") or 0),
            "precise": int(screenshot_summary.get("precise_localisation_count") or 0),
            "precise_rate": float(screenshot_summary.get("precise_localisation_rate") or 0),
        },
        "demo": {
            "path": bundle.as_posix(),
            "cases": int(manifest.get("replayable_case_count") or 0),
            "file_count": int(manifest.get("file_count") or 0),
            "bytes": int(manifest.get("total_byte_size") or 0),
            "manifest_sha256": _sha256(manifest_path),
        },
    }


def evaluate(snapshot: dict[str, Any], verify: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    count = int(snapshot.get("case_count") or 0)
    aggregate = snapshot.get("aggregate") or {}
    evidence = snapshot.get("evidence") or {}
    demo = snapshot.get("demo") or {}
    if snapshot.get("runtime_equivalent") is not True or snapshot.get("runtime_rerun_required"):
        blockers.append("runtime equivalence did not pass")
    if count != EXPECTED_CASE_COUNT or demo.get("cases") != EXPECTED_CASE_COUNT:
        blockers.append("canonical bundle does not contain three replayable cases")
    expected_three = (
        "market_available",
        "model_available",
        "gate_e1_satisfied",
        "real_provider_accepted",
        "first_attempt_accepted",
        "severity_floor_respected",
        "m3_at_one",
    )
    for key in expected_three:
        if aggregate.get(key) != count:
            blockers.append(f"{key} is not satisfied for every case")
    if aggregate.get("scope_corrections") != 0:
        blockers.append("scope correction count is non-zero")
    if aggregate.get("fallback_used") != 0:
        blockers.append("deterministic fallback count is non-zero")
    if aggregate.get("scope_violation_count") != 0:
        blockers.append("scope violation count is non-zero")
    if aggregate.get("budget_skipped") != 0:
        blockers.append("one or more conflicts were skipped by the recheck budget")
    if aggregate.get("seven_stage_available") != aggregate.get("seven_stage_required"):
        blockers.append("one or more replay stages are unavailable")
    if any(not item.get("final_supervisor_judgement_present") for item in snapshot.get("cases", {}).values()):
        blockers.append("one or more Final Supervisor judgements are missing")
    if evidence.get("rendered") != evidence.get("required"):
        blockers.append("Evidence screenshots do not account for every required citation")
    if evidence.get("precise") != evidence.get("required") or evidence.get("precise_rate") != 1.0:
        blockers.append("Evidence screenshot localisation is not fully precise")
    if not verify.get("passed"):
        blockers.append("canonical bundle hash verification failed")
    if int(demo.get("bytes") or 0) > 75 * 1024 * 1024:
        blockers.append("canonical bundle exceeds 75 MiB")
    return blockers


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--equivalence", type=Path, default=DEFAULT_EQUIVALENCE)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--write-snapshot", action="store_true")
    args = parser.parse_args()

    bundle = args.bundle
    equivalence = _json(args.equivalence)
    snapshot = derive_snapshot(bundle, equivalence)
    verify = verify_demo_bundle(bundle)
    blockers = evaluate(snapshot, verify)
    tracked_snapshot = None
    if args.write_snapshot:
        args.snapshot.parent.mkdir(parents=True, exist_ok=True)
        args.snapshot.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    elif args.snapshot.is_file():
        tracked_snapshot = _json(args.snapshot)
        if tracked_snapshot != snapshot:
            blockers.append("tracked current_runtime_snapshot.json is stale")

    scan_roots = [bundle, args.equivalence]
    if args.snapshot.is_file():
        scan_roots.append(args.snapshot)
    security_issues = _security_issues(scan_roots)
    if security_issues:
        blockers.append("sanitization scan found prohibited material")

    largest = max(_iter_files((bundle,)), key=lambda path: path.stat().st_size)
    report = {
        "schema_version": SCHEMA_VERSION,
        "passed": not blockers,
        "blockers": blockers,
        "bundle_verification": verify,
        "snapshot": snapshot,
        "sanitization": {"passed": not security_issues, "issues": security_issues},
        "repository_artifact_size": {
            "file_count": sum(1 for _ in _iter_files((bundle,))),
            "total_bytes": sum(path.stat().st_size for path in _iter_files((bundle,))),
            "largest_file": largest.relative_to(bundle).as_posix(),
            "largest_file_bytes": largest.stat().st_size,
        },
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("TEAM_CLONE_READY = " + ("PASS" if report["passed"] else "FAIL"))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
