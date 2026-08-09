"""Evaluate v0.3 batch results against the golden manifest (member #2, V3-10).

Reads an ``analysis_results.jsonl`` produced by
``scripts/run_v03_batch_analysis.py`` and a golden-case manifest, then writes the
v0.3 evaluation bundle to ``--output-dir``:

    analysis_results.jsonl  risk_items.csv  evidence_results.csv
    case_summary.csv        failure_report.csv  evaluation_metrics.json

Example::

    python scripts/evaluate_v03_golden_cases.py \
        --results reports/v03_batch/analysis_results.jsonl \
        --golden-manifest tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv \
        --output-dir reports/v03_eval
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ipo_risk.evaluation.golden_eval import run_evaluation


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results", type=Path, required=True, help="analysis_results.jsonl from a batch run")
    parser.add_argument("--golden-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("reports/v03_eval"))
    args = parser.parse_args()

    if not args.results.is_file():
        print(f"ERROR: results file not found: {args.results}")
        return 2
    if not args.golden_manifest.is_file():
        print(f"ERROR: golden manifest not found: {args.golden_manifest}")
        return 2

    metrics = run_evaluation(args.results, args.golden_manifest, args.output_dir)
    print(json.dumps(metrics["cases"], ensure_ascii=False))
    print(json.dumps(metrics["risk"], ensure_ascii=False))
    print(f"evaluation bundle written to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
