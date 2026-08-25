from __future__ import annotations

import json
from pathlib import Path


READINESS = Path("data/catalog/v04_c_market_intelligence_readiness.json")


def test_c_market_intelligence_readiness_is_real_grounded_and_complete() -> None:
    payload = json.loads(READINESS.read_text(encoding="utf-8"))
    assert payload["source"]["row_count"] == 438
    assert payload["selection_policy"]["uses_outcomes"] is False
    assert payload["selection_policy"]["uses_model_correctness"] is False
    assert payload["demo_pass"] == "4 / 4"
    assert len(payload["demo_case_ids"]) == 4
    assert payload["blind_2025_y_accessed"] is False
    assert payload["fake_industry_proxy"] is False
    assert payload["determinism"] == "PASS"
    assert payload["llm_interpretation"]["real_demo_status"] == "UNAVAILABLE_NO_PROVIDER"

    selection_reasons = {item["selection_reason"] for item in payload["demos"]}
    assert selection_reasons == {
        "risk_on_and_hot", "risk_off_and_cold", "high_volatility", "recent_ipo_sample_missing"
    }
    for demo in payload["demos"]:
        assert demo["final_supervisor_compatibility"] is True
        assert demo["llm_status"] == "unavailable"
        by_name = {item["name"]: item for item in demo["source_features"]}
        for feature in ("industry_return_5d", "industry_return_20d"):
            assert by_name[feature]["value"] is None
            assert by_name[feature]["missing_reason"] == "INDUSTRY_MAPPING_PIT_BLOCKED"
        assert demo["market_context"]["provenance"]["source_sha256"] == payload["source"]["sha256"]
        assert {item["event_type"] for item in demo["trace"]} == {"skill", "llm"}
