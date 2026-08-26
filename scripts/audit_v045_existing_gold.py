#!/usr/bin/env python3
"""Build the read-only Existing-Gold coverage/evaluable manifest for M1/M2."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ipo_risk.evaluation.existing_gold_metrics import (
    build_existing_gold_coverage,
    write_existing_gold_coverage,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/v045_role_b"),
    )
    args = parser.parse_args()

    root = args.root.resolve()
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = root / output_dir

    manifest = build_existing_gold_coverage(root)
    write_existing_gold_coverage(output_dir, manifest)
    summary = {
        "metric_protocol_version": manifest["metric_protocol_version"],
        "manifest_hash": manifest["manifest_hash"],
        "official_existing_gold_case_count": manifest["official_existing_gold_case_count"],
        "evaluable_development_case_count": manifest["evaluable_development_case_count"],
        "evaluable_validation_case_count": manifest["evaluable_validation_case_count"],
        "primary_positive_risk_unit_count": manifest["primary_positive_risk_unit_count"],
        "primary_evidence_unit_count": manifest["primary_evidence_unit_count"],
        "primary_risk_support": manifest["primary_risk_support"],
        "new_manual_annotations_added": manifest["new_manual_annotations_added"],
        "existing_gold_modified": manifest["existing_gold_modified"],
        "blind_2025_outcome_accessed": manifest["blind_2025_outcome_accessed"],
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
