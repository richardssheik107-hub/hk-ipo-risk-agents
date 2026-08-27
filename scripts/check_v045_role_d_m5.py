"""Strictly validate the canonical Role-D M5 handoff without modifying it."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ipo_risk.evaluation.role_d_acceptance import check_role_d_acceptance


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role-d-dir", type=Path, default=Path("reports/v045_role_d"))
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
        "--metric-protocol",
        type=Path,
        default=Path("configs/v045_competition_metric_protocol.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/v045_role_d_acceptance/acceptance.json"),
    )
    args = parser.parse_args()

    role_d_resolved = args.role_d_dir.resolve()
    output_resolved = args.output.resolve()
    if output_resolved == role_d_resolved or role_d_resolved in output_resolved.parents:
        parser.error("acceptance output must be outside the canonical Role-D directory")

    report = check_role_d_acceptance(
        role_d_dir=args.role_d_dir,
        pr_f_run_dir=args.pr_f_run_dir,
        pr_e_run_dir=args.pr_e_run_dir,
        pr_f_frozen_manifest=args.pr_f_frozen_manifest,
        pr_e_frozen_manifest=args.pr_e_frozen_manifest,
        filtered_eod_store=args.filtered_eod_store,
        filtered_eod_manifest=args.filtered_eod_manifest,
        catalog_dir=args.catalog_dir,
        metric_protocol=args.metric_protocol,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "verdict": report["verdict"],
                "passed": report["passed"],
                "blocker_count": len(report.get("blockers") or []),
                "output": args.output.as_posix(),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if report["passed"] is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
