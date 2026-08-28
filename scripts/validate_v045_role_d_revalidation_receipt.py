"""Validate the committed Role-D current-main revalidation receipt."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ipo_risk.evaluation.role_d_revalidation_receipt import (
    validate_role_d_revalidation_receipt,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--receipt",
        type=Path,
        default=Path(
            "reports/frozen/v045_role_d_current_main_revalidation_receipt.json"
        ),
    )
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
        "--metric-protocol",
        type=Path,
        default=Path("configs/v045_competition_metric_protocol.json"),
    )
    args = parser.parse_args()
    report = validate_role_d_revalidation_receipt(
        args.receipt,
        pr_f_manifest_path=args.pr_f_frozen_manifest,
        pr_e_manifest_path=args.pr_e_frozen_manifest,
        metric_protocol_path=args.metric_protocol,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
