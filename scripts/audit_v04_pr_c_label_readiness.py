"""Thin CLI for pre-PR-C 1D/5D label input-readiness measurement."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from ipo_risk.market.label_readiness import build_label_readiness
from ipo_risk.providers.filtered_eod_v2 import (
    FILTERED_EOD_FILENAME,
    FILTERED_EOD_MANIFEST_FILENAME,
    FilteredEODV2MarketDataProvider,
)


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_readiness_outputs(output_dir: Path, result: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = result["records"]
    _write_json(output_dir / "summary.json", result["summary"])
    _write_json(output_dir / "coverage.json", result)
    with (output_dir / "coverage.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        fieldnames = list(records[0]) if records else []
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog-dir", type=Path, default=Path("data/catalog"))
    parser.add_argument(
        "--store",
        type=Path,
        default=Path("data/cache") / FILTERED_EOD_FILENAME,
    )
    parser.add_argument(
        "--store-manifest",
        type=Path,
        default=Path("data/cache") / FILTERED_EOD_MANIFEST_FILENAME,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports/v04_pr_c_readiness"),
    )
    parser.add_argument("--expected-store-sha256", default=None)
    parser.add_argument("--verify-determinism", action="store_true")
    args = parser.parse_args()

    provider = FilteredEODV2MarketDataProvider(
        store_path=args.store,
        manifest_path=args.store_manifest,
        catalog_dir=args.catalog_dir,
        expected_store_sha256=args.expected_store_sha256,
    )
    first = build_label_readiness(provider)
    second = build_label_readiness(provider) if args.verify_determinism else None
    reproducibility = {
        "requested": args.verify_determinism,
        "first_coverage_content_hash": first["summary"]["coverage_content_hash"],
        "second_coverage_content_hash": (
            second["summary"]["coverage_content_hash"] if second else None
        ),
        "passed": bool(
            second
            and first["summary"]["coverage_content_hash"]
            == second["summary"]["coverage_content_hash"]
        ),
    }
    first["summary"]["determinism"] = reproducibility
    write_readiness_outputs(args.output_dir, first)
    _write_json(args.output_dir / "reproducibility_report.json", reproducibility)
    print(json.dumps(first["summary"], ensure_ascii=False, sort_keys=True))
    return int(
        first["summary"]["audit_failure_count"] != 0
        or (args.verify_determinism and not reproducibility["passed"])
    )


if __name__ == "__main__":
    raise SystemExit(main())
