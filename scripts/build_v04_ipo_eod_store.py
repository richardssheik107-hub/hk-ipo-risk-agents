"""CLI for the governed official-IPO EOD filtered store."""

from __future__ import annotations

import argparse
from pathlib import Path

from ipo_risk.market.eod_store import (
    EXPECTED_OFFICIAL_CASE_COUNT,
    FILTER_SCHEMA_VERSION,
    OFFICIAL_LISTING_YEARS,
    OUTPUT_COLUMNS,
    _cache_is_compatible,
    build_store,
    load_official_target_codes,
    sha256_file,
)

# Re-export the deterministic helpers for compatibility with existing research
# scripts/tests. Business/data logic lives in ipo_risk.market.eod_store.
__all__ = [
    "EXPECTED_OFFICIAL_CASE_COUNT",
    "FILTER_SCHEMA_VERSION",
    "OFFICIAL_LISTING_YEARS",
    "OUTPUT_COLUMNS",
    "_cache_is_compatible",
    "build_store",
    "load_official_target_codes",
    "sha256_file",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-root", type=Path, default=Path("data/competition")
    )
    parser.add_argument(
        "--catalog-dir", type=Path, default=Path("data/catalog")
    )
    parser.add_argument("--cache-dir", type=Path, default=Path("data/cache"))
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()

    manifest = build_store(
        data_root=args.data_root,
        catalog_dir=args.catalog_dir,
        cache_dir=args.cache_dir,
        rebuild=args.rebuild,
    )
    print(
        "cache_valid=true "
        f"rows={manifest.get('row_count')} "
        f"targets={manifest.get('target_case_count')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
