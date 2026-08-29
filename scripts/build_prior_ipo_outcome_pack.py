"""Materialize the licensed-derived prior-IPO outcome pack for dynamic Market-X.

Requires the local licensed competition EOD extract. The pack itself is small
and derived, but it is written under ``data/competition/`` -- which the
repository ignores wholesale -- so a run never stages licensed-derived rows for
commit by accident.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ipo_risk.market.outcome_pack import build_prior_ipo_outcome_pack
from ipo_risk.providers.competition_market import (
    DEFAULT_CATALOG_DIR,
    DEFAULT_COMPETITION_DATA_ROOT,
    CompetitionCSVMarketDataProvider,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    REPO_ROOT / "data" / "competition" / "derived" / "prior_ipo_outcome_pack.json"
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=REPO_ROOT / DEFAULT_COMPETITION_DATA_ROOT)
    parser.add_argument("--catalog-dir", type=Path, default=REPO_ROOT / DEFAULT_CATALOG_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    provider = CompetitionCSVMarketDataProvider(
        args.data_root,
        catalog_dir=args.catalog_dir,
    )
    readiness = provider.readiness_report()
    payload = build_prior_ipo_outcome_pack(
        metadata=provider.iter_listing_metadata(),
        bar_source=provider,
        bridge_path=args.catalog_dir / "ipo_official_master_bridge.csv",
        ipo_eod_sha256=readiness.source_sha256,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "record_count": len(payload["records"]),
                "content_hash": payload["content_hash"],
                "ipo_eod_sha256": payload["ipo_eod_sha256"],
                "blind_outcomes_included": payload["blind_outcomes_included"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
