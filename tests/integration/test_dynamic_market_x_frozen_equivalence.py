"""The dynamic path must reproduce the frozen Market-X, not approximate it.

This is the claim that makes dynamic Market-X trustworthy for a new prospectus:
it is not a second, looser methodology, it is the frozen methodology recomputed
from its inputs. The check replays the dynamic builder over every frozen PR-B
artifact and compares all fifteen raw features value-for-value.

The outcome half of the comparison needs the licensed-derived prior-IPO outcome
pack, which is deliberately not committed, so those cases skip in a clean
checkout. Build it with ``scripts/build_prior_ipo_outcome_pack.py``.
"""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

import pytest

from ipo_risk.agents.dynamic_market_context import DynamicPITMarketContextProvider
from ipo_risk.market.ipo_market_context_features import (
    IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER,
)
from ipo_risk.schemas import IPOProfile
from ipo_risk.schemas.final_supervision import ChannelStatus

REPO_ROOT = Path(__file__).resolve().parents[2]
FROZEN_DIR = REPO_ROOT / "reports" / "v04_pr_b" / "core_features"
BRIDGE = REPO_ROOT / "data" / "catalog" / "ipo_official_master_bridge.csv"
OUTCOME_PACK = (
    REPO_ROOT / "data" / "competition" / "derived" / "prior_ipo_outcome_pack.json"
)

# Offer-fact families need only the committed bridge; the rest need the pack.
OFFER_FACT_FEATURES = (
    "ipo_count_30d",
    "ipo_count_60d",
    "log_prior_ipo_funds_raised_30d",
    "log_prior_ipo_funds_raised_60d",
    "prior_ipo_funds_raised_30d_sample_count",
    "prior_ipo_funds_raised_60d_sample_count",
    "same_industry_ipo_count_180d",
)

pytestmark = pytest.mark.skipif(
    not FROZEN_DIR.is_dir() or not any(FROZEN_DIR.glob("*.json")),
    reason="the frozen PR-B Market-X artifacts are not present",
)


def _bridge_rows() -> dict[str, dict[str, str]]:
    with BRIDGE.open(encoding="utf-8-sig", newline="") as handle:
        return {row["case_id"]: row for row in csv.DictReader(handle)}


def _replay(feature_names: tuple[str, ...], *, outcome_pack: Path | None) -> None:
    provider = DynamicPITMarketContextProvider(
        official_bridge_path=BRIDGE, outcome_pack_path=outcome_pack
    )
    rows = _bridge_rows()
    compared = 0
    for path in sorted(FROZEN_DIR.glob("*.json")):
        artifact = json.loads(path.read_text(encoding="utf-8"))
        row = rows[artifact["case_id"]]
        view = provider.context(IPOProfile(
            company_name=row["selected_name"],
            stock_code=artifact["stock_code"],
            listing_date=date.fromisoformat(artifact["listing_date"]),
            industry=(row.get("official_industry_name") or "").strip(),
            metadata={"case_id": artifact["case_id"]},
        ))
        # A handful of early-2020 cases have every feature outside the universe's
        # left boundary. The frozen provider still reports AVAILABLE (a validated
        # artifact of fifteen nulls) while the dynamic one reports UNAVAILABLE
        # (nothing could be computed). The observation-level facts are identical,
        # which is what this comparison is about; neither may be an error.
        assert view.status is not ChannelStatus.UNAVAILABLE_ERROR, artifact["case_id"]
        rebuilt = {item.name: item.value for item in view.observations}
        for name in feature_names:
            frozen_value = artifact["raw_values"][name]
            if frozen_value is None:
                assert rebuilt[name] is None, (artifact["case_id"], name)
                continue
            assert rebuilt[name] == pytest.approx(float(frozen_value)), (
                artifact["case_id"],
                name,
            )
        compared += 1
    assert compared >= 400, f"only {compared} frozen artifacts were replayed"


def test_offer_fact_families_match_the_frozen_artifacts_without_the_pack() -> None:
    """The committed bridge alone reproduces every non-outcome feature."""

    _replay(OFFER_FACT_FEATURES, outcome_pack=None)


@pytest.mark.skipif(
    not OUTCOME_PACK.is_file(),
    reason="the licensed-derived prior-IPO outcome pack is not materialized",
)
def test_every_core_feature_matches_the_frozen_artifacts_with_the_pack() -> None:
    """With the outcome tier configured, all fifteen features agree exactly."""

    _replay(IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER, outcome_pack=OUTCOME_PACK)


@pytest.mark.skipif(
    not OUTCOME_PACK.is_file(),
    reason="the licensed-derived prior-IPO outcome pack is not materialized",
)
def test_the_pack_shares_the_eod_lineage_of_the_frozen_artifacts() -> None:
    """Same EOD extract behind both, proven by hash rather than by assertion."""

    pack = json.loads(OUTCOME_PACK.read_text(encoding="utf-8"))
    artifact = json.loads(
        sorted(FROZEN_DIR.glob("*.json"))[0].read_text(encoding="utf-8")
    )
    assert pack["ipo_eod_sha256"] == artifact["source_provenance"]["ipo_eod_sha256"]
    assert pack["blind_outcomes_included"] is False
