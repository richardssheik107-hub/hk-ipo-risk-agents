from __future__ import annotations

import argparse
import json
from pathlib import Path

from ipo_risk.quality.annotation_phase2 import run_phase2


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase-2 expert annotation correction/triage.")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/annotation_audit/phase2"),
    )
    parser.add_argument(
        "--no-write-corrections",
        action="store_true",
        help="Do not materialize deterministic correction artifacts under expert_results/*/audit/.",
    )
    args = parser.parse_args()
    summary = run_phase2(
        args.root,
        args.output_dir,
        write_corrections=not args.no_write_corrections,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
