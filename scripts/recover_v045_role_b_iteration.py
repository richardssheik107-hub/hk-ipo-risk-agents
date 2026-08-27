#!/usr/bin/env python3
"""Recover Existing-Gold scoring from persisted fixed-10 real-LLM results.

This command is intentionally offline with respect to the external LLM provider. It
reuses an existing fixed-10 iteration directory, rebuilds the governed analysis JSONL
with canonical case identity, reruns the Existing-Gold evaluator, and materializes the
missing iteration summary/failure focus without invoking the analysis runtime again.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from run_v045_role_b_iteration import (
    DEFAULT_COVERAGE,
    DEFAULT_ITERATION_ROOT,
    DEFAULT_SUBSET,
    IterationRunnerError,
    _build_iteration_summary,
    _case_ids,
    _case_runtime_status,
    _ensure_coverage,
    _evaluate,
    _failure_focus,
    _format_metric,
    _load_case_result,
    _load_or_create_subset,
    _previous_summary,
    _read_json,
    _write_json,
    _write_results_jsonl,
)


def _existing_case_statuses(run_dir: Path, case_ids: list[str]) -> list[dict[str, object]]:
    statuses: list[dict[str, object]] = []
    for index, case_id in enumerate(case_ids, start=1):
        result = _load_case_result(run_dir / case_id / "analysis_result.json")
        status, real = _case_runtime_status(result)
        statuses.append(
            {
                "case_id": case_id,
                "ordinal": index,
                "reused": True,
                "subprocess_returncode": None,
                "elapsed_seconds": 0.0,
                "analysis_status": status,
                "real_external_llm": real,
                "analysis_result_present": result is not None,
            }
        )
    return statuses


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--coverage-manifest", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("--subset", type=Path, default=DEFAULT_SUBSET)
    parser.add_argument("--iteration-root", type=Path, default=DEFAULT_ITERATION_ROOT)
    parser.add_argument("--iteration", required=True, help="existing fixed-10 iteration id")
    parser.add_argument("--subset-size", type=int, default=10)
    args = parser.parse_args()

    root = args.root.resolve()

    def resolved(path: Path) -> Path:
        return path if path.is_absolute() else root / path

    coverage_path = resolved(args.coverage_manifest)
    subset_path = resolved(args.subset)
    iteration_root = resolved(args.iteration_root)
    iteration_dir = iteration_root / args.iteration
    context_path = iteration_dir / "iteration_context.json"
    run_dir = iteration_dir / "run"

    if not iteration_dir.is_dir() or not context_path.is_file():
        raise IterationRunnerError("existing iteration context is unavailable")
    if not run_dir.is_dir():
        raise IterationRunnerError("existing iteration run directory is unavailable")

    manifest = _ensure_coverage(root, coverage_path)
    subset = _load_or_create_subset(subset_path, manifest, size=args.subset_size)
    case_ids = _case_ids(subset)
    context = _read_json(context_path)

    if context.get("iteration_id") != args.iteration:
        raise IterationRunnerError("existing iteration identity mismatch")
    if context.get("subset_hash") != subset.get("subset_hash"):
        raise IterationRunnerError("existing iteration subset hash mismatch")
    if context.get("validation_opened") is not False:
        raise IterationRunnerError("recovery refuses an iteration that opened Validation")
    if context.get("blind_2025_outcome_accessed") is not False:
        raise IterationRunnerError("recovery refuses an iteration that accessed 2025 Blind outcomes")

    statuses = _existing_case_statuses(run_dir, case_ids)
    completed = sum(bool(item["analysis_result_present"]) for item in statuses)
    real = sum(bool(item["real_external_llm"]) for item in statuses)
    if completed != len(case_ids):
        raise IterationRunnerError(
            f"recovery requires all persisted analysis results; found {completed}/{len(case_ids)}"
        )
    if real != len(case_ids):
        raise IterationRunnerError(
            f"recovery requires all persisted results to be real-LLM; found {real}/{len(case_ids)}"
        )

    _write_json(iteration_dir / "case_statuses.json", statuses)
    results_path = iteration_dir / "analysis_results.jsonl"
    row_count = _write_results_jsonl(run_dir, case_ids, results_path)
    if row_count != len(case_ids):
        raise IterationRunnerError(
            f"recovery JSONL row count mismatch; found {row_count}/{len(case_ids)}"
        )

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
        iteration_id=args.iteration,
        subset=subset,
        git_state=dict(context.get("code_state") or {}),
        preflight=dict(context.get("runtime") or {}),
        case_statuses=statuses,
        evaluation=evaluation,
        previous=previous,
    )
    summary["recovered_from_persisted_results"] = True
    summary["recovery_external_llm_calls_added"] = 0
    _write_json(iteration_dir / "iteration_summary.json", summary)

    print("--- fixed-10 offline recovery summary ---")
    print(f"iteration={args.iteration}")
    print(f"cases={completed}/{len(case_ids)} real_llm={real}/{len(case_ids)}")
    print(f"M1={_format_metric(summary['m1'])}")
    print(f"M2={_format_metric(summary['m2'])}")
    print(f"dominant_failure={focus['dominant_failure_reason'] or 'none'}")
    print("external_llm_calls_added=0")
    print(f"summary={iteration_dir / 'iteration_summary.json'}")
    print(f"focus={iteration_dir / 'failure_focus.json'}")
    print("scope=development_debug_only; validation=false; blind_2025=false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except IterationRunnerError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(2) from None
