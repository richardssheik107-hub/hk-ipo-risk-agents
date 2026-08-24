from __future__ import annotations

import sys
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[2] / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from competition_ui import (  # noqa: E402
    available_market_observation_count,
    channel_state_map,
    evidence_reference_count,
    roadmap_rows,
)


def test_executive_helpers_only_derive_existing_payload_values() -> None:
    payload = {
        "verified_risks": [
            {"evidence": [{"evidence_id": "e1"}, {"evidence_id": "e2"}]},
            {"evidence": []},
        ],
        "market_context": {
            "observations": [
                {"availability": "available"},
                {"availability": "missing"},
                {"availability": "available"},
            ]
        },
        "final_supervision": {
            "channel_states": [
                {"channel": "document", "status": "available"},
                {"channel": "market", "status": "available"},
                {"channel": "model", "status": "disabled"},
                {"channel": "rule", "status": "available"},
            ]
        },
    }

    assert evidence_reference_count(payload) == 2
    assert available_market_observation_count(payload) == (2, 3)
    assert channel_state_map(payload) == {
        "document": "available",
        "market": "available",
        "model": "disabled",
        "rule": "available",
    }


def test_future_modules_are_explicitly_planned_and_have_no_fake_metrics() -> None:
    rows = roadmap_rows()
    assert [row["Stage"] for row in rows] == ["CH-1", "CH-2", "CH-3", "CH-4", "CH-5", "CH-6"]
    assert all(row["Status"] == "PLANNED AFTER v0.4.3" for row in rows)
    assert all(set(row) == {"Stage", "Module", "Status", "Purpose"} for row in rows)
