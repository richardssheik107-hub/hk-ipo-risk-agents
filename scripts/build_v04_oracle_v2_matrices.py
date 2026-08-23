"""Build governed Oracle-v2 M/P/O/PM/OM matrices for PR-E and PR-F."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ipo_risk.modeling.oracle_v2_matrices import build_oracle_v2_matrices


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr-d-dir", type=Path, required=True)
    parser.add_argument("--oracle-v2-dir", type=Path, required=True)
    parser.add_argument(
        "--pr-d-freeze-manifest",
        type=Path,
        default=Path("reports/frozen/v04_pr_d_canonical_dataset_manifest.json"),
    )
    parser.add_argument(
        "--oracle-v2-freeze-manifest",
        type=Path,
        default=Path("reports/frozen/v04_oracle_v2_manifest.json"),
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("reports/v04_oracle_v2_matrices")
    )
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    manifest = build_oracle_v2_matrices(
        production_matrix_dir=args.pr_d_dir / "matrices",
        oracle_feature_dir=args.oracle_v2_dir / "features",
        pr_d_freeze_manifest_path=args.pr_d_freeze_manifest,
        oracle_v2_freeze_manifest_path=args.oracle_v2_freeze_manifest,
        output_dir=args.output_dir,
        resume=args.resume,
    )
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
