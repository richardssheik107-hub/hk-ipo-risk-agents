"""Close the Role-B real Document benchmark without opening Validation implicitly.

The runner consumes only governed metadata, Human Golden rows and optional
pre-existing analysis JSONL.  It never parses PDFs, invokes an LLM, or writes
analysis/page text.  Missing governed runtime inputs remain NOT AVAILABLE.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ipo_risk.evaluation.document_intelligence_benchmark import (
    build_real_benchmark_closure,
    write_benchmark,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--protocol",
        type=Path,
        default=Path("reports/v045_role_b/document_benchmark_protocol.json"),
    )
    parser.add_argument(
        "--golden",
        type=Path,
        default=Path("tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv"),
    )
    parser.add_argument(
        "--prospectus-manifest",
        type=Path,
        default=Path("data/catalog/ipo_prospectus_manifest.csv"),
    )
    parser.add_argument("--data-root", type=Path, default=Path("data/competition"))
    parser.add_argument("--annotation-root", type=Path, default=Path("expert_results"))
    parser.add_argument(
        "--demo-manifest",
        type=Path,
        default=Path("configs/v045_demo_cases.json"),
    )
    parser.add_argument("--development-results", type=Path)
    parser.add_argument("--validation-results", type=Path)
    parser.add_argument(
        "--open-validation",
        action="store_true",
        help="single-open gate; refused until every Development Golden case is evaluated",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("reports/v045_role_b"))
    args = parser.parse_args()

    summary, risk_rows, evidence_rows = build_real_benchmark_closure(
        protocol_path=args.protocol,
        golden_path=args.golden,
        prospectus_manifest_path=args.prospectus_manifest,
        data_root=args.data_root,
        annotation_root=args.annotation_root,
        demo_manifest_path=args.demo_manifest,
        development_results_path=args.development_results,
        validation_results_path=args.validation_results,
        open_validation=args.open_validation,
    )
    write_benchmark(args.output_dir, summary, risk_rows, evidence_rows)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if summary["result"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
