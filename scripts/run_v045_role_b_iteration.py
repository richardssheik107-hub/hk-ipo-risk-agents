#!/usr/bin/env python3
"""Run one fixed-10 real-LLM Development iteration and score Existing-Gold M1/M2.

This is deliberately a boring orchestration script: it freezes one deterministic
10-case Development subset, runs only those cases through the already-governed
v0.4.5 real-LLM runtime, suppresses verbose subprocess output into local ignored
logs, collects governed analysis JSONL, invokes the Existing-Gold evaluator, and
writes a compact score/failure summary for the next optimization round.

It never opens Validation, never reads 2025 Blind outcomes, never modifies Gold,
and never changes code or prompts.  Re-running the same iteration id resumes
completed cases; a new iteration id is required for a new code/prompt version.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from ipo_risk.core.config import load_settings
from ipo_risk.evaluation.existing_gold_metrics import verify_coverage_manifest


SUBSET_VERSION = "v045_role_b_fixed10_subset_v1"
ITERATION_VERSION = "v045_role_b_fixed10_iteration_v1"
SELECTION_ALGORITHM = "balanced_positive_primary_families_v1"
DEFAULT_COVERAGE = Path("reports/v045_role_b/existing_gold_evaluable_manifest.json")
DEFAULT_SUBSET = Path("reports/v045_role_b/fixed10_development_subset.json")
DEFAULT_ITERATION_ROOT = Path("reports/v045_role_b/iterations")
DEFAULT_BRIDGE = Path("data/catalog/ipo_official_master_bridge.csv")
DEFAULT_CONFIG = Path("configs/v045_competition_ai.yaml")
EXPECTED_PROVIDER = "openai_responses"
EXPECTED_MODEL = "ark-code-latest"
EXPECTED_TIMEOUT_SECONDS = 300
EXPECTED_TRANSPORT_RETRIES = 0
_ITERATION_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


class IterationRunnerError(RuntimeError):
    """Fail-closed orchestration error with no secret-bearing payload."""


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IterationRunnerError(f"invalid_json:{path.name}") from exc
    if not isinstance(payload, dict):
        raise IterationRunnerError(f"expected_json_object:{path.name}")
    return payload


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _run_captured(
    command: list[str],
    *,
    cwd: Path,
    log_path: Path,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess without flooding the caller/Codex context with logs."""

    started = time.monotonic()
    process = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        env=os.environ.copy(),
    )
    elapsed = time.monotonic() - started
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        "\n".join(
            [
                f"returncode={process.returncode}",
                f"elapsed_seconds={elapsed:.3f}",
                "--- stdout ---",
                process.stdout,
                "--- stderr ---",
                process.stderr,
            ]
        ),
        encoding="utf-8",
    )
    return process


def _ensure_coverage(root: Path, coverage_path: Path) -> dict[str, Any]:
    if not coverage_path.is_file():
        process = _run_captured(
            [
                sys.executable,
                "scripts/audit_v045_existing_gold.py",
                "--root",
                str(root),
                "--output-dir",
                str(coverage_path.parent),
            ],
            cwd=root,
            log_path=coverage_path.parent / "fixed10_auto_audit.log",
        )
        if process.returncode != 0 or not coverage_path.is_file():
            raise IterationRunnerError(
                "Existing-Gold coverage manifest is unavailable; auto-audit failed. "
                "See reports/v045_role_b/fixed10_auto_audit.log."
            )
    manifest = _read_json(coverage_path)
    try:
        verify_coverage_manifest(manifest)
    except ValueError as exc:
        raise IterationRunnerError("Existing-Gold coverage manifest verification failed") from exc
    return manifest


def _development_positive_inventory(
    manifest: dict[str, Any],
) -> tuple[dict[str, set[str]], Counter[str], dict[str, str]]:
    families: dict[str, set[str]] = defaultdict(set)
    stock_codes: dict[str, str] = {}
    for row in manifest.get("risk_units", []):
        if not isinstance(row, dict):
            continue
        if row.get("split") != "development":
            continue
        if row.get("primary_scope") is not True or row.get("evaluable_positive") is not True:
            continue
        family = row.get("competition_risk_family")
        case_id = str(row.get("case_id") or "")
        if not case_id or not isinstance(family, str) or not family:
            continue
        families[case_id].add(family)
        stock_codes[case_id] = str(row.get("stock_code") or "")

    evidence_counts: Counter[str] = Counter()
    for row in manifest.get("evidence_units", []):
        if not isinstance(row, dict):
            continue
        if (
            row.get("split") == "development"
            and row.get("primary_scope") is True
            and str(row.get("case_id") or "") in families
        ):
            evidence_counts[str(row["case_id"])] += 1
    return dict(families), evidence_counts, stock_codes


def select_fixed_debug_cases(manifest: dict[str, Any], size: int = 10) -> list[str]:
    """Deterministically balance supported positive risk families across the subset."""

    if size <= 0:
        raise IterationRunnerError("subset size must be positive")
    families, evidence_counts, _ = _development_positive_inventory(manifest)
    if len(families) < size:
        raise IterationRunnerError(
            f"only {len(families)} positive Development cases are available for a {size}-case subset"
        )

    family_selected: Counter[str] = Counter()
    selected: list[str] = []
    remaining = set(families)
    while len(selected) < size:
        ranked: list[tuple[float, int, int, str]] = []
        for case_id in remaining:
            case_families = families[case_id]
            balance_score = sum(1.0 / (1 + family_selected[item]) for item in case_families)
            ranked.append(
                (
                    -balance_score,
                    -len(case_families),
                    -int(evidence_counts.get(case_id, 0)),
                    case_id,
                )
            )
        _, _, _, chosen = min(ranked)
        selected.append(chosen)
        remaining.remove(chosen)
        family_selected.update(families[chosen])
    return selected


def _subset_hash(payload: dict[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "subset_hash"}
    return _canonical_hash(body)


def _build_subset(manifest: dict[str, Any], size: int) -> dict[str, Any]:
    case_ids = select_fixed_debug_cases(manifest, size=size)
    families, evidence_counts, stock_codes = _development_positive_inventory(manifest)
    cases = [
        {
            "case_id": case_id,
            "stock_code": stock_codes.get(case_id, ""),
            "positive_primary_families": sorted(families[case_id]),
            "primary_evidence_unit_count": int(evidence_counts.get(case_id, 0)),
        }
        for case_id in case_ids
    ]
    payload: dict[str, Any] = {
        "subset_version": SUBSET_VERSION,
        "selection_algorithm": SELECTION_ALGORITHM,
        "metric_protocol_version": manifest["metric_protocol_version"],
        "source_coverage_manifest_hash": manifest["manifest_hash"],
        "split": "development",
        "case_count": size,
        "cases": cases,
        "debug_subset_only": True,
        "validation_opened": False,
        "blind_2025_outcome_accessed": False,
    }
    payload["subset_hash"] = _subset_hash(payload)
    return payload


def _verify_subset(
    subset: dict[str, Any],
    manifest: dict[str, Any],
    *,
    size: int,
) -> None:
    if subset.get("subset_version") != SUBSET_VERSION:
        raise IterationRunnerError("unexpected fixed-10 subset version")
    if subset.get("selection_algorithm") != SELECTION_ALGORITHM:
        raise IterationRunnerError("unexpected fixed-10 selection algorithm")
    if subset.get("split") != "development":
        raise IterationRunnerError("fixed subset must remain Development-only")
    if subset.get("source_coverage_manifest_hash") != manifest.get("manifest_hash"):
        raise IterationRunnerError(
            "Existing-Gold manifest drift detected; do not silently regenerate the debug subset"
        )
    if subset.get("subset_hash") != _subset_hash(subset):
        raise IterationRunnerError("fixed subset hash mismatch")
    cases = subset.get("cases")
    if not isinstance(cases, list) or len(cases) != size:
        raise IterationRunnerError(f"fixed subset must contain exactly {size} cases")
    case_ids = [str(item.get("case_id") or "") for item in cases if isinstance(item, dict)]
    if len(case_ids) != size or len(set(case_ids)) != size or any(not item for item in case_ids):
        raise IterationRunnerError("fixed subset contains invalid or duplicate case ids")
    expected = select_fixed_debug_cases(manifest, size=size)
    if case_ids != expected:
        raise IterationRunnerError(
            "fixed subset no longer matches the deterministic frozen selection; investigate source drift"
        )
    if subset.get("validation_opened") is not False or subset.get("blind_2025_outcome_accessed") is not False:
        raise IterationRunnerError("fixed subset governance flags are invalid")


def _load_or_create_subset(
    subset_path: Path,
    manifest: dict[str, Any],
    *,
    size: int,
) -> dict[str, Any]:
    if subset_path.is_file():
        subset = _read_json(subset_path)
        _verify_subset(subset, manifest, size=size)
        return subset
    subset = _build_subset(manifest, size=size)
    _verify_subset(subset, manifest, size=size)
    _write_json(subset_path, subset)
    return subset


def _bridge_names(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise IterationRunnerError("official bridge is unavailable")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {
        str(row.get("case_id") or ""): str(row.get("selected_name") or "").strip()
        for row in rows
        if row.get("case_id")
    }


def _build_runtime_cases_manifest(
    subset: dict[str, Any],
    bridge_path: Path,
    destination: Path,
) -> None:
    names = _bridge_names(bridge_path)
    cases = []
    for item in subset["cases"]:
        case_id = item["case_id"]
        company_name = names.get(case_id, "")
        if not company_name:
            raise IterationRunnerError(f"company name unavailable for fixed case {case_id}")
        cases.append({"case_id": case_id, "company_name": company_name})
    _write_json(
        destination,
        {
            "manifest_version": "v045_role_b_fixed10_runtime_cases_v1",
            "note": (
                "Generated locally from the frozen Existing-Gold debug subset. "
                "Development-only; no Validation or Blind cases."
            ),
            "cases": cases,
        },
    )


def _preflight(root: Path, config_path: Path) -> dict[str, Any]:
    settings = load_settings(str(config_path))
    if settings.use_mock:
        raise IterationRunnerError("real-LLM fixed-10 runner refuses use_mock=true")
    if settings.llm_provider != EXPECTED_PROVIDER:
        raise IterationRunnerError(
            f"effective llm_provider must be {EXPECTED_PROVIDER}; current={settings.llm_provider}"
        )
    if settings.llm_model != EXPECTED_MODEL:
        raise IterationRunnerError(
            f"effective llm_model must be {EXPECTED_MODEL}; current={settings.llm_model or 'missing'}"
        )
    if not settings.llm_api_key or not settings.llm_base_url:
        raise IterationRunnerError("real LLM credentials/base URL are incomplete")
    if int(settings.llm_timeout_seconds) != EXPECTED_TIMEOUT_SECONDS:
        raise IterationRunnerError(
            f"effective LLM timeout must remain frozen at {EXPECTED_TIMEOUT_SECONDS}s"
        )
    if int(settings.llm_max_retries) != EXPECTED_TRANSPORT_RETRIES:
        raise IterationRunnerError(
            f"effective LLM transport retries must remain frozen at {EXPECTED_TRANSPORT_RETRIES}"
        )
    prospectus_root = os.getenv("IPO_RISK_PROSPECTUS_ROOT")
    if not prospectus_root:
        raise IterationRunnerError("IPO_RISK_PROSPECTUS_ROOT is not set")
    if not Path(prospectus_root).is_dir():
        raise IterationRunnerError("IPO_RISK_PROSPECTUS_ROOT does not point to a directory")
    return {
        "effective_provider": settings.llm_provider,
        "effective_model": settings.llm_model,
        "effective_timeout_seconds": int(settings.llm_timeout_seconds),
        "effective_transport_retries": int(settings.llm_max_retries),
        "api_key_present": True,
        "base_url_present": True,
        "prospectus_root_present": True,
    }


def _git_state(root: Path) -> dict[str, Any]:
    def run(args: list[str]) -> str:
        process = subprocess.run(
            ["git", *args], cwd=root, text=True, capture_output=True, check=False
        )
        return process.stdout.strip() if process.returncode == 0 else ""

    head = run(["rev-parse", "HEAD"]) or "UNKNOWN"
    porcelain = run(["status", "--porcelain"])
    diff = run(["diff", "--no-ext-diff", "--binary"])
    fingerprint = _canonical_hash(
        {"head": head, "porcelain": porcelain, "tracked_diff": diff}
    )
    return {
        "git_head": head,
        "git_dirty": bool(porcelain),
        "code_fingerprint": fingerprint,
    }


def _next_iteration_id(iteration_root: Path) -> str:
    numbers = []
    if iteration_root.is_dir():
        for item in iteration_root.iterdir():
            match = re.fullmatch(r"iter_(\d{3})", item.name)
            if item.is_dir() and match:
                numbers.append(int(match.group(1)))
    return f"iter_{(max(numbers) + 1) if numbers else 1:03d}"


def _resolve_iteration_id(requested: str, iteration_root: Path) -> str:
    if requested == "auto":
        return _next_iteration_id(iteration_root)
    if not _ITERATION_RE.fullmatch(requested):
        raise IterationRunnerError("iteration id may contain only letters, numbers, dot, dash, underscore")
    return requested


def _case_ids(subset: dict[str, Any]) -> list[str]:
    return [str(item["case_id"]) for item in subset["cases"]]


def _load_case_result(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _case_runtime_status(result: dict[str, Any] | None) -> tuple[str, bool]:
    if result is None:
        return "missing_result", False
    status = str(result.get("status") or "unknown")
    metadata = result.get("metadata") or {}
    modes = metadata.get("component_modes") or {}
    provider = str(modes.get("llm_provider") or "")
    llm_status = str(modes.get("llm_status") or "")
    real = provider == EXPECTED_PROVIDER and llm_status == "available"
    return status, real


def _run_cases(
    *,
    root: Path,
    config_path: Path,
    cases_manifest: Path,
    case_ids: Iterable[str],
    run_dir: Path,
    log_dir: Path,
    force: bool,
) -> list[dict[str, Any]]:
    statuses: list[dict[str, Any]] = []
    for index, case_id in enumerate(case_ids, start=1):
        result_path = run_dir / case_id / "analysis_result.json"
        reused = result_path.is_file() and not force
        elapsed = 0.0
        returncode: int | None = None
        if not reused:
            started = time.monotonic()
            process = _run_captured(
                [
                    sys.executable,
                    "scripts/run_v04_role_e_demo.py",
                    "--cases",
                    str(cases_manifest),
                    "--config",
                    str(config_path),
                    "--output-dir",
                    str(run_dir),
                    "--case-id",
                    case_id,
                ],
                cwd=root,
                log_path=log_dir / f"{case_id}.log",
            )
            elapsed = time.monotonic() - started
            returncode = process.returncode
        result = _load_case_result(result_path)
        status, real = _case_runtime_status(result)
        statuses.append(
            {
                "case_id": case_id,
                "ordinal": index,
                "reused": reused,
                "subprocess_returncode": returncode,
                "elapsed_seconds": round(elapsed, 3),
                "analysis_status": status,
                "real_external_llm": real,
                "analysis_result_present": result is not None,
            }
        )
        print(
            f"[{index:02d}/{len(list(case_ids)) if not isinstance(case_ids, list) else len(case_ids):02d}] "
            f"{case_id} status={status} real_llm={str(real).lower()} reused={str(reused).lower()}"
        )
    return statuses


def _write_results_jsonl(run_dir: Path, case_ids: list[str], destination: Path) -> int:
    rows = []
    for case_id in case_ids:
        result = _load_case_result(run_dir / case_id / "analysis_result.json")
        if result is None:
            continue

        metadata = result.get("metadata")
        metadata_case_id = (
            str(metadata.get("case_id") or "") if isinstance(metadata, dict) else ""
        )
        top_level_case_id = str(result.get("case_id") or "")
        for observed_case_id in (metadata_case_id, top_level_case_id):
            if observed_case_id and observed_case_id != case_id:
                raise IterationRunnerError(
                    f"governed result case_id mismatch for expected case {case_id}"
                )

        row = dict(result)
        row["case_id"] = case_id
        rows.append(row)

    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    return len(rows)


def _evaluate(
    *,
    root: Path,
    coverage_path: Path,
    results_path: Path,
    case_ids: list[str],
    output_dir: Path,
    log_path: Path,
) -> dict[str, Any]:
    process = _run_captured(
        [
            sys.executable,
            "scripts/evaluate_v045_existing_gold.py",
            "--root",
            str(root),
            "--coverage-manifest",
            str(coverage_path),
            "--results",
            str(results_path),
            "--split",
            "development",
            "--case-ids",
            ",".join(case_ids),
            "--output-dir",
            str(output_dir),
        ],
        cwd=root,
        log_path=log_path,
    )
    summary_path = output_dir / "document_benchmark_summary.json"
    if process.returncode != 0 or not summary_path.is_file():
        raise IterationRunnerError(
            "Existing-Gold debug evaluation failed; see the local evaluation.log"
        )
    return _read_json(summary_path)


def _failure_focus(evaluation_dir: Path) -> dict[str, Any]:
    path = evaluation_dir / "risk_benchmark.csv"
    if not path.is_file():
        return {"dominant_failure_reason": None, "failure_reasons": []}
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        reason = (row.get("failure_reason") or "").strip()
        if reason:
            grouped[reason].append(row)
    ordered = sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))
    reasons = []
    for reason, items in ordered:
        reasons.append(
            {
                "reason": reason,
                "count": len(items),
                "case_ids": sorted({item.get("case_id", "") for item in items if item.get("case_id")}),
                "risk_codes": sorted(
                    {item.get("source_risk_code", "") for item in items if item.get("source_risk_code")}
                ),
            }
        )
    return {
        "dominant_failure_reason": reasons[0]["reason"] if reasons else None,
        "failure_reasons": reasons,
    }


def _previous_summary(iteration_root: Path, current_dir: Path) -> dict[str, Any] | None:
    candidates = [
        item / "iteration_summary.json"
        for item in iteration_root.iterdir()
        if item.is_dir() and item != current_dir and (item / "iteration_summary.json").is_file()
    ] if iteration_root.is_dir() else []
    if not candidates:
        return None
    latest = max(candidates, key=lambda path: path.stat().st_mtime)
    return _read_json(latest)


def _delta(current: float | None, previous: float | None) -> float | None:
    if not isinstance(current, (int, float)) or not isinstance(previous, (int, float)):
        return None
    return float(current) - float(previous)


def _build_iteration_summary(
    *,
    iteration_id: str,
    subset: dict[str, Any],
    git_state: dict[str, Any],
    preflight: dict[str, Any],
    case_statuses: list[dict[str, Any]],
    evaluation: dict[str, Any],
    previous: dict[str, Any] | None,
) -> dict[str, Any]:
    m1 = evaluation.get("risk_extraction", {}).get("official_aligned_accuracy")
    m2 = evaluation.get("evidence_coverage", {}).get("coverage_recall")
    previous_m1 = previous.get("m1") if previous else None
    previous_m2 = previous.get("m2") if previous else None
    completed = sum(item["analysis_result_present"] for item in case_statuses)
    real = sum(item["real_external_llm"] for item in case_statuses)
    return {
        "iteration_version": ITERATION_VERSION,
        "iteration_id": iteration_id,
        "debug_subset_only": True,
        "competition_pass_claim_eligible": False,
        "subset_hash": subset["subset_hash"],
        "source_coverage_manifest_hash": subset["source_coverage_manifest_hash"],
        "case_count": len(case_statuses),
        "analysis_result_count": completed,
        "real_external_llm_case_count": real,
        "all_cases_have_results": completed == len(case_statuses),
        "all_cases_real_llm": real == len(case_statuses),
        "m1": m1,
        "m2": m2,
        "m1_official_threshold": 0.80,
        "m2_official_threshold": 0.85,
        "m1_project_target": 0.85,
        "m2_project_target": 0.88,
        "previous_iteration_id": previous.get("iteration_id") if previous else None,
        "m1_delta_vs_previous": _delta(m1, previous_m1),
        "m2_delta_vs_previous": _delta(m2, previous_m2),
        "per_risk": evaluation.get("risk_extraction", {}).get("per_risk", {}),
        "retrieval_diagnostics": evaluation.get("retrieval_diagnostics", {}),
        "failure_taxonomy": evaluation.get("failure_taxonomy", {}),
        "case_statuses": case_statuses,
        "runtime": preflight,
        "code_state": git_state,
        "new_manual_annotations_added": False,
        "existing_gold_modified": False,
        "validation_opened": False,
        "blind_2025_outcome_accessed": False,
    }


def _format_metric(value: Any) -> str:
    return "NA" if not isinstance(value, (int, float)) else f"{float(value):.4f}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--coverage-manifest", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("--subset", type=Path, default=DEFAULT_SUBSET)
    parser.add_argument("--bridge", type=Path, default=DEFAULT_BRIDGE)
    parser.add_argument("--iteration-root", type=Path, default=DEFAULT_ITERATION_ROOT)
    parser.add_argument("--iteration", default="auto", help="label, or auto for iter_001/002/...")
    parser.add_argument("--subset-size", type=int, default=10)
    parser.add_argument("--subset-only", action="store_true", help="freeze/print the fixed subset without LLM calls")
    parser.add_argument("--force-case-rerun", action="store_true")
    parser.add_argument("--require-all-cases", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()

    def resolved(path: Path) -> Path:
        return path if path.is_absolute() else root / path

    coverage_path = resolved(args.coverage_manifest)
    subset_path = resolved(args.subset)
    bridge_path = resolved(args.bridge)
    config_path = resolved(args.config)
    iteration_root = resolved(args.iteration_root)

    manifest = _ensure_coverage(root, coverage_path)
    subset = _load_or_create_subset(subset_path, manifest, size=args.subset_size)
    case_ids = _case_ids(subset)

    if args.subset_only:
        print(f"subset_hash={subset['subset_hash']}")
        print(f"case_count={len(case_ids)}")
        print("case_ids=" + ",".join(case_ids))
        print("scope=development_debug_only")
        return 0

    preflight = _preflight(root, config_path)
    git_state = _git_state(root)
    iteration_id = _resolve_iteration_id(args.iteration, iteration_root)
    iteration_dir = iteration_root / iteration_id
    iteration_dir.mkdir(parents=True, exist_ok=True)
    context_path = iteration_dir / "iteration_context.json"

    context = {
        "iteration_version": ITERATION_VERSION,
        "iteration_id": iteration_id,
        "subset_hash": subset["subset_hash"],
        "source_coverage_manifest_hash": subset["source_coverage_manifest_hash"],
        "code_state": git_state,
        "runtime": preflight,
        "validation_opened": False,
        "blind_2025_outcome_accessed": False,
    }
    if context_path.is_file() and not args.force_case_rerun:
        existing_context = _read_json(context_path)
        if existing_context.get("subset_hash") != context["subset_hash"]:
            raise IterationRunnerError("cannot resume iteration with a different fixed subset")
        if existing_context.get("code_state", {}).get("code_fingerprint") != git_state["code_fingerprint"]:
            raise IterationRunnerError(
                "cannot resume an existing iteration after code state changed; use a new iteration id"
            )
    else:
        _write_json(context_path, context)

    cases_manifest = iteration_dir / "runtime_cases.json"
    _build_runtime_cases_manifest(subset, bridge_path, cases_manifest)
    run_dir = iteration_dir / "run"
    log_dir = iteration_dir / "logs"
    statuses = _run_cases(
        root=root,
        config_path=config_path,
        cases_manifest=cases_manifest,
        case_ids=case_ids,
        run_dir=run_dir,
        log_dir=log_dir,
        force=args.force_case_rerun,
    )
    _write_json(iteration_dir / "case_statuses.json", statuses)

    results_path = iteration_dir / "analysis_results.jsonl"
    _write_results_jsonl(run_dir, case_ids, results_path)
    evaluation_dir = iteration_dir / "evaluation"
    evaluation = _evaluate(
        root=root,
        coverage_path=coverage_path,
        results_path=results_path,
        case_ids=case_ids,
        output_dir=evaluation_dir,
        log_path=iteration_dir / "evaluation.log",
    )
    focus = _failure_focus(evaluation_dir)
    _write_json(iteration_dir / "failure_focus.json", focus)
    previous = _previous_summary(iteration_root, iteration_dir)
    summary = _build_iteration_summary(
        iteration_id=iteration_id,
        subset=subset,
        git_state=git_state,
        preflight=preflight,
        case_statuses=statuses,
        evaluation=evaluation,
        previous=previous,
    )
    _write_json(iteration_dir / "iteration_summary.json", summary)

    print("--- fixed-10 iteration summary ---")
    print(f"iteration={iteration_id}")
    print(
        f"cases={summary['analysis_result_count']}/{summary['case_count']} "
        f"real_llm={summary['real_external_llm_case_count']}/{summary['case_count']}"
    )
    print(
        f"M1={_format_metric(summary['m1'])} "
        f"delta={_format_metric(summary['m1_delta_vs_previous'])}"
    )
    print(
        f"M2={_format_metric(summary['m2'])} "
        f"delta={_format_metric(summary['m2_delta_vs_previous'])}"
    )
    print(f"dominant_failure={focus['dominant_failure_reason'] or 'none'}")
    print(f"summary={iteration_dir / 'iteration_summary.json'}")
    print(f"focus={iteration_dir / 'failure_focus.json'}")
    print("scope=development_debug_only; validation=false; blind_2025=false")

    if args.require_all_cases and (
        not summary["all_cases_have_results"] or not summary["all_cases_real_llm"]
    ):
        return 2
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except IterationRunnerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
