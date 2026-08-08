"""Run v0.3 batch analysis over catalog-selected IPO cases (member #2, V3-10).

Examples
--------
Mock-mode smoke over two cases::

    python scripts/run_v03_batch_analysis.py --case-ids ipo_2020_00368,ipo_2020_00589

Real-document run over a golden manifest (PDFs under a local data root)::

    python scripts/run_v03_batch_analysis.py \
        --golden-manifest tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv \
        --config configs/real_pdf.yaml --data-root /path/to/prospectuses

The 2025 blind test is refused unless BOTH --include-blind-test and the exact
--blind-test-token are supplied.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ipo_risk.evaluation.batch import BLIND_TEST_TOKEN, run_batch


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--case-ids", help="comma-separated case ids")
    selection.add_argument("--split", help="select all cases in a dataset split")
    selection.add_argument("--golden-manifest", type=Path, help="select distinct case ids from a golden manifest")
    parser.add_argument("--catalog-dir", type=Path, default=Path("data/catalog"))
    parser.add_argument("--data-root", type=Path, default=Path("data/inputs"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/v03_batch"))
    parser.add_argument("--config", type=Path, help="settings YAML (default configs/mock.yaml)")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--overwrite", action="store_true", help="rerun cases that already have a result")
    parser.add_argument("--include-blind-test", action="store_true", help="opt in to the protected 2025 blind test")
    parser.add_argument("--blind-test-token", help=f"required acknowledgement: {BLIND_TEST_TOKEN}")
    args = parser.parse_args()

    case_ids = [item.strip() for item in args.case_ids.split(",") if item.strip()] if args.case_ids else None

    try:
        report = run_batch(
            catalog_dir=args.catalog_dir,
            data_root=args.data_root,
            output_dir=args.output_dir,
            config_path=args.config,
            case_ids=case_ids,
            split=args.split,
            golden_manifest=args.golden_manifest,
            limit=args.limit,
            overwrite=args.overwrite,
            include_blind_test=args.include_blind_test,
            blind_test_token=args.blind_test_token,
        )
    except PermissionError as exc:
        print(f"ERROR: {exc}")
        return 2

    counts = report.counts()
    print(f"batch complete: {counts} -> {args.output_dir}")
    # Non-zero exit if any case failed outright (protected/skipped are not failures).
    return 1 if counts.get("failed") else 0


if __name__ == "__main__":
    raise SystemExit(main())
