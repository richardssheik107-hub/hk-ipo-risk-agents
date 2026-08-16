#!/usr/bin/env python3
"""Run the read-only Phase-1 GPT expert annotation audit."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ipo_risk.quality.annotation_audit import run_audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit pass1 expert annotations without modifying them."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("."),
        help="Repository root (default: current directory).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/annotation_audit"),
        help="Directory for generated audit reports.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = root / output_dir

    summary = run_audit(root, output_dir)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if not summary.get("pass1_unchanged"):
        raise SystemExit("pass1 mutation guard failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
