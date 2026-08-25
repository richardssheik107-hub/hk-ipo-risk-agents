"""Run the lightweight Role-B competition Document benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ipo_risk.evaluation.document_intelligence_benchmark import (
    build_benchmark,
    write_benchmark,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--golden",
        type=Path,
        default=Path("tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv"),
    )
    parser.add_argument("--analysis-results", type=Path)
    parser.add_argument(
        "--retriever-summary",
        type=Path,
        default=Path("reports/retriever_v3/locked_phase_e_summary.json"),
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("reports/v045_role_b")
    )
    args = parser.parse_args()
    summary, risk_rows, evidence_rows = build_benchmark(
        golden_path=args.golden,
        results_path=args.analysis_results,
        retriever_summary_path=args.retriever_summary,
    )
    write_benchmark(args.output_dir, summary, risk_rows, evidence_rows)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
