"""Recover the exact final-three PR-F product package from a frozen D export.

This command is a disaster-recovery path for the already-validated product
handoff.  It does not train or score a model.  It accepts only the byte-exact
``test_predictions.csv`` recorded by the immutable current-main Role-D receipt
and refuses the output unless all four product files reproduce the receipt's
previously validated SHA-256 values.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ipo_risk.evaluation.role_d_revalidation_receipt import (
    validate_role_d_revalidation_receipt,
)
from ipo_risk.modeling.pr_f_product_handoff import (
    write_receipt_bound_product_handoff,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--receipt",
        type=Path,
        default=Path("reports/frozen/v045_role_d_current_main_revalidation_receipt.json"),
    )
    parser.add_argument(
        "--pr-f-manifest",
        type=Path,
        default=Path("reports/frozen/v04_pr_f_lightgbm_manifest.json"),
    )
    parser.add_argument(
        "--pr-e-manifest",
        type=Path,
        default=Path("reports/frozen/v04_pr_e_baseline_manifest.json"),
    )
    parser.add_argument(
        "--metric-protocol",
        type=Path,
        default=Path("configs/v045_competition_metric_protocol.json"),
    )
    args = parser.parse_args()

    validation = validate_role_d_revalidation_receipt(
        args.receipt,
        pr_f_manifest_path=args.pr_f_manifest,
        pr_e_manifest_path=args.pr_e_manifest,
        metric_protocol_path=args.metric_protocol,
    )
    if validation.get("passed") is not True:
        parser.error(
            "current-main Role-D receipt failed validation: "
            + "; ".join(validation.get("blockers") or ["unknown receipt error"])
        )

    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    frozen = json.loads(args.pr_f_manifest.read_text(encoding="utf-8"))
    handoff = receipt["product_handoff"]
    manifest = write_receipt_bound_product_handoff(
        args.predictions,
        args.output_dir,
        expected_predictions_sha256=receipt["artifact_sha256"]["test_predictions.csv"],
        expected_product_sha256=handoff["file_sha256"],
        expected_source_model_result_hash=frozen["model_result_hash"],
        case_ids=handoff["case_ids"],
        source_pr_f={
            "pr_f_version": frozen.get("pr_f_version"),
            "model_policy_version": frozen.get("model_policy_version"),
            "execution_revision": frozen.get("execution_revision"),
            "freeze_manifest_hash": frozen.get("freeze_manifest_hash"),
        },
    )
    print(
        json.dumps(
            {
                "status": "complete_receipt_bound_recovery",
                "case_count": manifest["case_count"],
                "output_dir": str(args.output_dir),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
