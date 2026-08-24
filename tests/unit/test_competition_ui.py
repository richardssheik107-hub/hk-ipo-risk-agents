from __future__ import annotations

import sys
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[2] / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from competition_ui import (  # noqa: E402
    available_market_observation_count,
    channel_state_map,
    domain_summary_rows,
    evidence_reference_count,
    risk_inventory_rows,
    roadmap_rows,
)


def _payload() -> dict[str, object]:
    return {
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
        "domains": {
            "financial": {
                "risk_count": 1,
                "status": "completed",
                "status_counts": {"verified": 1},
                "risks": [
                    {
                        "risk_code": "cash_runway",
                        "level": "critical",
                        "score": 90,
                        "verification_status": "verified",
                        "evidence": [{"evidence_id": "e1"}, {"evidence_id": "e2"}],
                    }
                ],
            },
            "legal": {
                "risk_count": 0,
                "status": "no_risk_emitted",
                "status_counts": {},
                "risks": [],
            },
            "business": {
                "risk_count": 0,
                "status": "no_risk_emitted",
                "status_counts": {},
                "risks": [],
            },
        },
    }


def test_executive_helpers_only_derive_existing_payload_values() -> None:
    payload = _payload()

    assert evidence_reference_count(payload) == 2
    assert available_market_observation_count(payload) == (2, 3)
    assert channel_state_map(payload) == {
        "document": "available",
        "market": "available",
        "model": "disabled",
        "rule": "available",
    }


def test_workspace_inventory_only_projects_existing_risks() -> None:
    rows = risk_inventory_rows(_payload())
    assert rows == [
        {
            "Domain": "Financial",
            "Risk": "cash_runway",
            "Level": "critical",
            "Rule score": 90,
            "Verification": "verified",
            "Evidence": 2,
        }
    ]


def test_domain_summary_preserves_emitted_counts_and_statuses() -> None:
    rows = domain_summary_rows(_payload())
    assert [row["Domain"] for row in rows] == ["Financial", "Legal & Compliance", "Business"]
    assert rows[0]["Risks"] == 1
    assert rows[0]["Verified"] == 1
    assert rows[1]["Status"] == "no_risk_emitted"
    assert rows[2]["Risks"] == 0


def test_future_modules_are_explicitly_planned_and_have_no_fake_metrics() -> None:
    rows = roadmap_rows()
    assert [row["Stage"] for row in rows] == ["CH-1", "CH-2", "CH-3", "CH-4", "CH-5", "CH-6"]
    assert all(row["Status"] == "PLANNED AFTER v0.4.3" for row in rows)
    assert all(set(row) == {"Stage", "Module", "Status", "Purpose"} for row in rows)
