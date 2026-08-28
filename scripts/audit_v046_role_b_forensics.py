"""Generate post-run Role-B fixed-10 forensic artifacts without changing runtime."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ipo_risk.evaluation.role_b_forensics import ForensicInputs, run_forensics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--run-root",
        type=Path,
        default=Path("reports/v046_role_b/ablation/main_candidate_real"),
    )
    parser.add_argument(
        "--coverage",
        type=Path,
        default=Path("reports/v045_role_b/existing_gold_evaluable_manifest.json"),
    )
    parser.add_argument(
        "--subset",
        type=Path,
        default=Path("reports/v045_role_b/fixed10_development_subset.json"),
    )
    parser.add_argument(
        "--catalog", type=Path, default=Path("data/catalog/ipo_prospectus_manifest.csv")
    )
    parser.add_argument("--prospectus-root", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/v046_role_b/forensics/forensic_001"),
    )
    parser.add_argument(
        "--legacy-v045-root",
        type=Path,
        default=None,
        help="optional read-only reports/v045_role_b root from another checkout",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    resolve = lambda value: value if value.is_absolute() else root / value
    inventory = [
        ("v045", root / "reports/v045_role_b"),
        ("v046", root / "reports/v046_role_b"),
    ]
    if args.legacy_v045_root is not None:
        inventory.append(("legacy_v045_external", args.legacy_v045_root.resolve()))
    summary = run_forensics(
        ForensicInputs(
            root=root,
            run_root=resolve(args.run_root),
            coverage_path=resolve(args.coverage),
            subset_path=resolve(args.subset),
            catalog_path=resolve(args.catalog),
            prospectus_root=args.prospectus_root.resolve(),
            output_dir=resolve(args.output_dir),
            inventory_roots=tuple(inventory),
        )
    )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
