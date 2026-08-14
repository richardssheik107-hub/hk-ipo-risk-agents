from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from scripts.run_retriever_v21_ten_case import _json_hash, _verify_freeze
from ipo_risk.retrieval.domain_aware_v21 import policy_hashes


def test_manifest_hash_detects_mutation() -> None:
    payload = {"a": 1, "locked_gold_opened": False}
    digest = _json_hash(payload)
    payload["a"] = 2
    assert digest != _json_hash(payload)


def test_freeze_rejects_policy_hash_change(tmp_path: Path) -> None:
    output = tmp_path / "out"
    output.mkdir()
    manifest = {**policy_hashes(), "freeze_manifest_sha256": "invalid"}
    (output / "v21_freeze_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="MANIFEST_CHANGED"):
        _verify_freeze(argparse.Namespace(output_root=output))


def test_split_identities_are_frozen() -> None:
    from scripts.run_retriever_v21_ten_case import DEVELOPMENT_CASES, HISTORICAL_CASES, LOCKED_CASES
    assert DEVELOPMENT_CASES == ("ipo_2020_00368", "ipo_2020_01167", "ipo_2020_01408")
    assert HISTORICAL_CASES == ("ipo_2020_01961",)
    assert len(LOCKED_CASES) == 6
