"""Fail-closed preflight for the final-three Market-X and model channels."""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

from ipo_risk.agents.market_context import GovernedPRBMarketContextProvider
from ipo_risk.core.config import load_settings
from ipo_risk.modeling.frozen_model_evidence import FrozenModelPredictionProvider
from ipo_risk.schemas import IPOProfile
from ipo_risk.schemas.final_supervision import ChannelStatus


REPO_ROOT = Path(__file__).resolve().parents[1]


def _rooted(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def main() -> int:
    settings = load_settings(str(REPO_ROOT / "configs/v045_competition_offline.yaml"))
    cases = json.loads(
        (REPO_ROOT / "configs/v045_demo_cases.json").read_text(encoding="utf-8")
    )["cases"]
    bridge_path = _rooted(settings.market_official_bridge)
    with bridge_path.open("r", encoding="utf-8-sig", newline="") as handle:
        bridge = {row["case_id"]: row for row in csv.DictReader(handle)}

    market = GovernedPRBMarketContextProvider(
        feature_dir=_rooted(settings.market_feature_dir),
        official_bridge_path=bridge_path,
        extended_readiness_path=(
            _rooted(settings.market_extended_readiness)
            if settings.market_extended_readiness
            else None
        ),
    )
    model = FrozenModelPredictionProvider(
        run_dir=_rooted(settings.pr_f_run_dir),
        frozen_dir=_rooted(settings.report_dir) / "frozen",
    )

    rows: list[dict[str, object]] = []
    for item in cases:
        row = bridge[item["case_id"]]
        profile = IPOProfile(
            company_name=item["company_name"],
            stock_code=row["stock_code_wind"],
            listing_date=date.fromisoformat(row["official_listed_date"]),
            metadata={"case_id": item["case_id"]},
        )
        market_view = market.context(profile)
        model_view = model.prediction(profile)
        rows.append(
            {
                "case_id": item["case_id"],
                "market_status": market_view.status.value,
                "market_observation_count": len(market_view.observations),
                "market_reason": market_view.reason,
                "model_status": model_view.status.value,
                "model_score": model_view.score,
                "model_driver_count": len(model_view.drivers),
                "model_reason": model_view.reason,
            }
        )

    passed = all(
        row["market_status"] == ChannelStatus.AVAILABLE.value
        and row["model_status"] == ChannelStatus.AVAILABLE.value
        for row in rows
    )
    print(
        json.dumps(
            {
                "status": "pass" if passed else "fail",
                "case_count": len(rows),
                "market_available_count": sum(
                    row["market_status"] == ChannelStatus.AVAILABLE.value for row in rows
                ),
                "model_available_count": sum(
                    row["model_status"] == ChannelStatus.AVAILABLE.value for row in rows
                ),
                "cases": rows,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
