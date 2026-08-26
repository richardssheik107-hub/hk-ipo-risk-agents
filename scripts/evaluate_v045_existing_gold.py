#!/usr/bin/env python3
"""Evaluate governed analysis JSONL against frozen Existing-Gold-only M1/M2."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ipo_risk.evaluation.existing_gold_metrics import (
    _load_jsonl,
    build_existing_gold_coverage,
    evaluate_existing_gold,
    verify_coverage_manifest,
    write_existing_gold_evaluation,
)


def _parse_case_ids(value: str | None) -> set[str] | None:
    if value is None:
        return None
    case_ids = {item.strip() for item in value.split(",") if item.strip()}
    if not case_ids:
        raise ValueError("--case-ids cannot be empty")
    return case_ids


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--coverage-manifest",
        type=Path,
        default=Path("reports/v045_role_b/existing_gold_evaluable_manifest.json"),
    )
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument(
        "--split",
        choices=("development", "validation"),
        default="development",
    )
    parser.add_argument(
        "--case-ids",
        help="comma-separated Existing-Gold case ids; debug only, not final PASS scope",
    )
    parser.add_argument(
        "--open-validation",
        action="store_true",
        help="explicitly open the one-shot Validation evaluator",
    )
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="fail unless every evaluable case in the selected scope has a result",
    )
    parser.add_argument(
        "--require-real-llm",
        action="store_true",
        help="fail unless at least one governed real external LLM case is measured",
    )
    parser.add_argument(
        "--require-pass",
        action="store_true",
        help="fail unless full-split, complete, real-LLM M1>=80% and M2>=85%",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/v045_role_b"),
    )
    args = parser.parse_args()

    root = args.root.resolve()
    manifest_path = args.coverage_manifest
    if not manifest_path.is_absolute():
        manifest_path = root / manifest_path
    results_path = args.results
    if not results_path.is_absolute():
        results_path = root / results_path
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = root / output_dir

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    verify_coverage_manifest(manifest)

    current = build_existing_gold_coverage(root)
    if current["manifest_hash"] != manifest["manifest_hash"]:
        raise SystemExit(
            "Existing-Gold manifest drift: resolve source drift before scoring; "
            "do not evaluate against changed Gold."
        )

    results = _load_jsonl(results_path)
    case_ids = _parse_case_ids(args.case_ids)
    summary, risk_rows, evidence_rows = evaluate_existing_gold(
        manifest,
        results,
        split=args.split,
        open_validation=args.open_validation,
        case_ids=case_ids,
    )
    write_existing_gold_evaluation(output_dir, summary, risk_rows, evidence_rows)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))

    gate = summary["measurement_gate"]
    if args.require_complete and not gate["all_expected_cases_present"]:
        return 2
    if args.require_real_llm and not gate["real_llm_measurement_present"]:
        return 3
    if args.require_pass:
        if not gate["competition_pass_claim_eligible"]:
            return 4
        if gate["official_m1_pass"] is not True or gate["official_m2_pass"] is not True:
            return 5
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
