"""Materialize the Market-X feature handoff the model lane consumes.

The model owner must not recompute Market-X, and must not have to trust a
dynamic case on its word. This command projects whatever the market channel
produced -- a frozen PR-B artifact or a dynamic point-in-time build -- into one
payload per case, and binds each one to the frozen model's feature identity
before writing it. A case whose lineage cannot be proven is reported, not
written.

Selection is by governed identity only: ``--case-id`` for catalog cases, or
``--stock-code`` with ``--listing-date`` for a prospectus that is not in the
catalog at all. Company names never select a case.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path
from typing import Any

from ipo_risk.agents.dynamic_market_context import DynamicPITMarketContextProvider
from ipo_risk.agents.market_context import GovernedPRBMarketContextProvider
from ipo_risk.core.config import load_settings
from ipo_risk.market.dynamic_extended import DynamicExtendedMarketSource
from ipo_risk.market.handoff import (
    MarketFeatureHandoffError,
    MarketHandoffBindingError,
    build_market_feature_handoff,
    verify_market_handoff_binding,
)
from ipo_risk.schemas import IPOProfile

REPO_ROOT = Path(__file__).resolve().parents[1]


def _rooted(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def _provider(settings):
    bridge_path = _rooted(settings.market_official_bridge)
    extended = None
    if (
        settings.market_dynamic_extended_hsi_csv
        and settings.market_dynamic_extended_turnover_csv
    ):
        extended = DynamicExtendedMarketSource(
            hsi_normalized_csv=_rooted(settings.market_dynamic_extended_hsi_csv),
            turnover_normalized_csv=_rooted(
                settings.market_dynamic_extended_turnover_csv
            ),
            hsi_manifest=_rooted("data/catalog/csmar_hsi_source_manifest.json"),
            external_manifest=_rooted(
                "data/catalog/v04_c_external_market_source_manifest.json"
            ),
        )
    return GovernedPRBMarketContextProvider(
        feature_dir=_rooted(settings.market_feature_dir),
        official_bridge_path=bridge_path,
        extended_readiness_path=(
            _rooted(settings.market_extended_readiness)
            if settings.market_extended_readiness
            else None
        ),
        new_case_provider=DynamicPITMarketContextProvider(
            official_bridge_path=bridge_path,
            outcome_pack_path=(
                _rooted(settings.market_dynamic_outcome_pack)
                if settings.market_dynamic_outcome_pack
                else None
            ),
            extended_source=extended,
        ),
    ), bridge_path


def _profiles(args, bridge_path: Path) -> list[IPOProfile]:
    if args.stock_code:
        if args.listing_date is None:
            raise SystemExit("--stock-code requires --listing-date")
        return [
            IPOProfile(
                company_name=args.company_name or "unnamed new issuer",
                stock_code=args.stock_code,
                listing_date=args.listing_date,
                industry=args.industry or "",
            )
        ]
    with bridge_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = {row["case_id"]: row for row in csv.DictReader(handle)}
    selected = args.case_id or sorted(rows)
    profiles: list[IPOProfile] = []
    for case_id in selected:
        row = rows.get(case_id)
        if row is None:
            raise SystemExit(f"case_id is not in the official bridge: {case_id}")
        listing = (row.get("official_listed_date") or "").strip()
        if not listing:
            raise SystemExit(f"case has no official listing date: {case_id}")
        profiles.append(
            IPOProfile(
                company_name=(row.get("selected_name") or "").strip(),
                stock_code=(row.get("stock_code_wind") or "").strip(),
                listing_date=date.fromisoformat(listing),
                industry=(row.get("official_industry_name") or "").strip(),
                metadata={"case_id": case_id},
            )
        )
    return profiles


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/v045_competition_offline.yaml")
    parser.add_argument("--case-id", action="append")
    parser.add_argument("--stock-code")
    parser.add_argument("--listing-date", type=date.fromisoformat)
    parser.add_argument("--company-name")
    parser.add_argument("--industry")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "reports" / "v046_market_handoff",
    )
    args = parser.parse_args()

    settings = load_settings(str(_rooted(args.config)))
    provider, bridge_path = _provider(settings)
    frozen_dir = _rooted(settings.report_dir) / "frozen"

    written: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for profile in _profiles(args, bridge_path):
        case_id = str(profile.metadata.get("case_id") or "").strip() or (
            f"{profile.stock_code}_{profile.listing_date.isoformat()}"
        )
        view = provider.context(profile)
        try:
            handoff = build_market_feature_handoff(view)
            binding = verify_market_handoff_binding(handoff, frozen_dir=frozen_dir)
        except (MarketFeatureHandoffError, MarketHandoffBindingError) as exc:
            skipped.append({"case_id": case_id, "reason": str(exc)})
            continue
        payload = {"handoff": handoff, "model_binding": binding}
        (args.output_dir / f"{case_id}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written.append(
            {
                "case_id": case_id,
                "market_runtime_path": handoff["market_runtime_path"],
                "available_feature_count": len(handoff["available_features"]),
                "missing_feature_count": len(handoff["missing_features"]),
                "content_hash": handoff["content_hash"],
            }
        )

    print(
        json.dumps(
            {
                "status": "pass" if written else "fail",
                "output_dir": str(args.output_dir),
                "written_count": len(written),
                "skipped_count": len(skipped),
                "written": written[:20],
                "skipped": skipped[:20],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if written else 2


if __name__ == "__main__":
    raise SystemExit(main())
