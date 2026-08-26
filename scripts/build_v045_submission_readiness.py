"""Build the Role-A v0.4.5 submission readiness evidence.

The command is intentionally useful before the project is ready: missing B/D/E
hand-offs are written as explicit blockers instead of causing the audit itself to
crash. Use ``--require-ready`` only for the final freeze when a non-zero exit is
desired for any open Gate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ipo_risk.runtime.submission_readiness import (
    build_artifact_index,
    build_submission_readiness,
    write_artifact_index,
    write_submission_audits,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--role-b-dir", type=Path, default=Path("reports/v045_role_b"))
    parser.add_argument("--role-d-dir", type=Path, default=Path("reports/v045_role_d"))
    parser.add_argument("--role-e-dir", type=Path, default=Path("reports/v045_role_e"))
    parser.add_argument("--baseline-role-e-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("reports/v045_submission"))
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="return non-zero unless every measured B/C/D/E/A Gate is PASS",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    readiness, blind, provenance, determinism = build_submission_readiness(
        repo_root=repo_root,
        role_b_dir=args.role_b_dir,
        role_d_dir=args.role_d_dir,
        role_e_dir=args.role_e_dir,
        a_output_dir=args.output_dir,
        baseline_role_e_dir=args.baseline_role_e_dir,
    )
    write_submission_audits(
        output_dir=args.output_dir,
        readiness=readiness,
        blind=blind,
        provenance=provenance,
        determinism=determinism,
    )
    index = build_artifact_index(
        role_b_dir=args.role_b_dir,
        role_d_dir=args.role_d_dir,
        role_e_dir=args.role_e_dir,
        a_output_dir=args.output_dir,
        runbook_path=repo_root / "docs/SUBMISSION_RUNBOOK.md",
    )
    write_artifact_index(args.output_dir / "artifact_index.json", index)

    print(
        json.dumps(
            {
                "verdict": readiness["verdict"],
                "competition_ready": readiness["competition_ready"],
                "blocker_count": len(readiness["blockers"]),
                "blockers": readiness["blockers"],
                "artifact_count": index["artifact_count"],
                "output_dir": str(args.output_dir),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if args.require_ready and readiness["competition_ready"] is not True:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
