"""Validate the machine-readable v0.3 golden-case annotation contract."""

from __future__ import annotations

import argparse
from pathlib import Path

from ipo_risk.evaluation.v03_manifest import validate_manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    errors = validate_manifest(args.manifest)
    if errors:
        for error in errors:
            print(error)
        return 1
    print(f"valid v0.3 golden manifest: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
