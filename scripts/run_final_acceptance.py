"""Run final competition acceptance preflight and write auditable evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ipo_risk.runtime.final_acceptance import (
    build_acceptance,
    command_specs,
    package_preflight_evidence,
    run_command,
    skipped_full_test_result,
    write_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/final_acceptance"))
    parser.add_argument("--skip-full-tests", action="store_true")
    parser.add_argument("--ci-status", choices=("pass", "fail", "unknown"), default="unknown")
    parser.add_argument("--ci-evidence-url", action="append", default=[])
    parser.add_argument("--package-preflight", action="store_true")
    parser.add_argument(
        "--preflight-zip",
        type=Path,
        default=Path("dist/hk_ipo_risk_agents_preflight_evidence.zip"),
    )
    parser.add_argument("--require-ready-for-packaging", action="store_true")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    results = [
        run_command(repo_root, spec)
        for spec in command_specs(include_full_tests=not args.skip_full_tests)
    ]
    if args.skip_full_tests:
        results.insert(1, skipped_full_test_result())
    payload = build_acceptance(
        repo_root,
        results,
        ci_status=args.ci_status,
        ci_evidence_urls=args.ci_evidence_url,
    )
    output_dir = args.output_dir if args.output_dir.is_absolute() else repo_root / args.output_dir
    write_outputs(output_dir, payload)
    packaged = None
    if args.package_preflight:
        output_zip = args.preflight_zip if args.preflight_zip.is_absolute() else repo_root / args.preflight_zip
        packaged = package_preflight_evidence(output_dir, output_zip)
    result = {
        "final_status": payload["final_status"],
        "ready_for_final_packaging": payload["ready_for_final_packaging"],
        "blocker_count": len(payload["blockers"]),
        "blockers": payload["blockers"],
        "output_dir": args.output_dir.as_posix(),
        "preflight_evidence_zip": packaged,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.require_ready_for_packaging and not payload["ready_for_final_packaging"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
