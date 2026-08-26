"""Build the final governed Role-D M5 submission handoff."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ipo_risk.evaluation.role_d_m5 import build_role_d_handoff
from ipo_risk.providers.filtered_eod_v2 import FilteredEODV2MarketDataProvider


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr-f-run-dir", type=Path, default=Path("reports/v04_pr_f"))
    parser.add_argument("--pr-e-run-dir", type=Path, default=Path("reports/v04_pr_e"))
    parser.add_argument(
        "--pr-f-frozen-manifest",
        type=Path,
        default=Path("reports/frozen/v04_pr_f_lightgbm_manifest.json"),
    )
    parser.add_argument(
        "--pr-e-frozen-manifest",
        type=Path,
        default=Path("reports/frozen/v04_pr_e_baseline_manifest.json"),
    )
    parser.add_argument(
        "--filtered-eod-store",
        type=Path,
        default=Path("data/cache/v04_ipo_eod.csv"),
    )
    parser.add_argument(
        "--filtered-eod-manifest",
        type=Path,
        default=Path("data/cache/v04_ipo_eod.manifest.json"),
    )
    parser.add_argument("--catalog-dir", type=Path, default=Path("data/catalog"))
    parser.add_argument(
        "--output-dir", type=Path, default=Path("reports/v045_role_d")
    )
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    provider = FilteredEODV2MarketDataProvider(
        store_path=args.filtered_eod_store,
        manifest_path=args.filtered_eod_manifest,
        catalog_dir=args.catalog_dir,
    )
    result = build_role_d_handoff(
        pr_f_run_dir=args.pr_f_run_dir,
        pr_f_frozen_manifest=args.pr_f_frozen_manifest,
        pr_e_run_dir=args.pr_e_run_dir,
        pr_e_frozen_manifest=args.pr_e_frozen_manifest,
        market_provider=provider,
        output_dir=args.output_dir,
        resume=args.resume,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
