"""Validate formal PR-C artifacts and optionally write the small freeze manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ipo_risk.modeling.pr_c_freeze import audit_pr_c_freeze


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir", type=Path, default=Path("reports/v04_pr_c")
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    manifest = audit_pr_c_freeze(args.input_dir)
    rendered = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.output.exists():
            existing = json.loads(args.output.read_text(encoding="utf-8"))
            if existing != manifest:
                raise ValueError(
                    f"freeze manifest conflict; use a new output path: {args.output}"
                )
        else:
            args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
