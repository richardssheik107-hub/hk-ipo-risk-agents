"""The checked-in final-three product projections must work in a fresh clone."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import date
from pathlib import Path

import pytest

from ipo_risk.agents.market_context import GovernedPRBMarketContextProvider
from ipo_risk.core.config import load_settings
from ipo_risk.modeling.frozen_model_evidence import FrozenModelPredictionProvider
from ipo_risk.modeling.pr_f_product_handoff import validate_product_handoff
from ipo_risk.schemas import IPOProfile
from ipo_risk.schemas.final_supervision import ChannelStatus


ROOT = Path(__file__).resolve().parents[2]
CASES = json.loads((ROOT / "configs/v045_demo_cases.json").read_text(encoding="utf-8"))[
    "cases"
]


def _path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


@pytest.mark.parametrize(
    "config",
    ["configs/v045_competition_offline.yaml", "configs/v045_competition_ai.yaml"],
)
def test_competition_configs_enable_the_receipt_bound_model_handoff(config) -> None:
    settings = load_settings(str(ROOT / config))
    assert settings.pr_f_run_dir == "reports/v045_role_d_v2_product_handoff_final3"


def test_final_three_market_and_model_channels_are_available() -> None:
    settings = load_settings(str(ROOT / "configs/v045_competition_offline.yaml"))
    bridge_path = _path(settings.market_official_bridge)
    with bridge_path.open("r", encoding="utf-8-sig", newline="") as handle:
        bridge = {row["case_id"]: row for row in csv.DictReader(handle)}
    market = GovernedPRBMarketContextProvider(
        feature_dir=_path(settings.market_feature_dir),
        official_bridge_path=bridge_path,
    )
    model = FrozenModelPredictionProvider(
        run_dir=_path(settings.pr_f_run_dir),
        frozen_dir=ROOT / "reports/frozen",
    )

    for item in CASES:
        row = bridge[item["case_id"]]
        profile = IPOProfile(
            company_name=item["company_name"],
            stock_code=row["stock_code_wind"],
            listing_date=date.fromisoformat(row["official_listed_date"]),
            metadata={"case_id": item["case_id"]},
        )
        market_view = market.context(profile)
        model_view = model.prediction(profile)
        assert market_view.status is ChannelStatus.AVAILABLE, market_view.reason
        assert len(market_view.observations) == 15
        assert model_view.status is ChannelStatus.AVAILABLE, model_view.reason
        assert model_view.score is not None
        assert len(model_view.drivers) == 7
        assert model_view.alert is not None


def test_final_three_handoff_matches_the_current_main_receipt() -> None:
    receipt = json.loads(
        (ROOT / "reports/frozen/v045_role_d_v2_promotion_receipt.json").read_text(
            encoding="utf-8"
        )
    )
    frozen = json.loads(
        (ROOT / "reports/frozen/v045_role_d_v2_promotion_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    handoff = ROOT / "reports/v045_role_d_v2_product_handoff_final3"
    manifest, signals = validate_product_handoff(
        handoff,
        expected_source_model_result_hash=frozen["model_result_hash"],
        expected_case_ids=receipt["product_handoff"]["case_ids"],
    )
    assert manifest["contains_target_labels"] is False
    assert [row["case_id"] for row in signals] == receipt["product_handoff"]["case_ids"]
    assert all(isinstance(row["alert"], bool) for row in signals)
    assert {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in handoff.iterdir()
        if path.is_file()
    } == receipt["product_handoff"]["file_sha256"]
