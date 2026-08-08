"""Validate the machine-readable v0.3 golden-case annotation contract.

Without extra flags this runs the per-row annotation contract only (back-compat).
Add ``--integrity`` for the member #2 data checks (identity consistency, no
duplicate judgements, no 2025 blind-test leakage). Supply ``--prospectus-manifest``
(and optionally ``--data-root``) to cross-check real cases against the frozen
prospectus manifest for dataset split, SHA-256 and on-disk PDF presence.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ipo_risk.evaluation.v03_manifest import (
    validate_manifest,
    validate_manifest_integrity,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--integrity",
        action="store_true",
        help="run catalog-level integrity checks in addition to per-row checks",
    )
    parser.add_argument(
        "--prospectus-manifest",
        type=Path,
        help="cross-check real cases against this prospectus manifest CSV",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        help="verify each cross-checked case's PDF exists under this root",
    )
    args = parser.parse_args()

    if args.integrity or args.prospectus_manifest or args.data_root:
        errors = validate_manifest_integrity(
            args.manifest,
            prospectus_manifest_path=args.prospectus_manifest,
            data_root=args.data_root,
        )
    else:
        errors = validate_manifest(args.manifest)

    if errors:
        for error in errors:
            print(error)
        return 1
    print(f"valid v0.3 golden manifest: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
