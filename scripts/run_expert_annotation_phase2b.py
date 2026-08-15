from __future__ import annotations

import argparse
import json
from pathlib import Path

from ipo_risk.quality.annotation_phase2b import run_phase2b


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Expert Annotation Phase-2b P0 structured-input backfill.")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/annotation_audit/phase2b"),
    )
    parser.add_argument(
        "--no-write-backfills",
        action="store_true",
        help="Do not materialize per-Case audit/structured_input_backfill_v1.json artifacts.",
    )
    args = parser.parse_args()
    summary = run_phase2b(
        args.root,
        args.output_dir,
        write_backfills=not args.no_write_backfills,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
