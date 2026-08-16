import hashlib
import json

from scripts.run_retriever_v3_phase_e_locked import (
    PROTOCOL_HASH_NAME,
    PROTOCOL_NAME,
    prepare_protocol,
    source_oracles,
    verify_protocol,
)


def test_protocol_is_written_and_hash_verified_without_opening_locked_gold(tmp_path):
    result = prepare_protocol(tmp_path)
    protocol = json.loads((tmp_path / PROTOCOL_NAME).read_text(encoding="utf-8"))
    actual = hashlib.sha256((tmp_path / PROTOCOL_NAME).read_bytes()).hexdigest()
    assert result == {"protocol_frozen": True, "protocol_sha256": actual, "locked_metrics_opened": False}
    assert (tmp_path / PROTOCOL_HASH_NAME).read_text(encoding="ascii").split()[0] == actual
    assert protocol["predeclared_risk_watch"] == ["customer_concentration"]
    assert protocol["candidate_cap"] == 100
    assert all(protocol["frozen_state"].values())
    verified, verified_hash = verify_protocol(tmp_path)
    assert verified_hash == actual
    assert verified["locked_metrics_opened"] is False


def test_source_oracle_uses_frozen_lane_cutoffs():
    required = [{"case_id": "ipo_x", "risk_code": "cash_runway", "page": 7}]
    lanes = {("ipo_x", "cash_runway"): {
        "v1": [], "v2": [], "v21": [], "bm25": list(range(101, 150)) + [7], "table": [],
    }}
    result = source_oracles(required, lanes)
    assert result["old"]["native"] == 0
    assert result["plus_bm25"]["at_20"] == 0
    assert result["plus_bm25"]["at_50"] == 1
    assert result["full"]["native"] == 1
