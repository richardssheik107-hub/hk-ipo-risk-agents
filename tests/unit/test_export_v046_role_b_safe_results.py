from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.export_v046_role_b_safe_results import _discover, _load_safe_json


def _write(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_discover_preserves_complete_and_preflight_only_rounds(tmp_path: Path) -> None:
    source = tmp_path / "reports"
    _write(
        source / "ablation" / "batch001" / "ablation_summary.json",
        {
            "selected_mode": "offline",
            "case_count": 2,
            "modes": {
                "offline": {
                    "m1": 0.5,
                    "m2": 0.75,
                    "evaluable_positive_risk_unit_count": 4,
                    "evaluable_evidence_unit_count": 8,
                }
            },
            "llm_quality": {"real_llm_case_count": 0},
            "validation_opened": False,
            "blind_2025_outcome_accessed": False,
        },
    )
    _write(
        source / "ablation" / "batch002" / "preflight.json",
        {
            "api_key_present": True,
            "raw_prompt_persisted": False,
            "validation_opened": False,
            "blind_2025_outcome_accessed": False,
        },
    )

    runs = _discover(source)

    assert [run["status"] for run in runs] == ["complete", "preflight_only"]
    assert runs[0]["metrics"]["m1_numerator"] == 2
    assert runs[0]["metrics"]["m2_numerator"] == 6
    assert runs[1]["summaries"]["preflight.json"]["raw_prompt_persisted"] is False


@pytest.mark.parametrize(
    "payload",
    [
        {"api_key_value": "secret"},
        {"exact_text": "licensed Evidence text"},
        {"metadata": {"value": r"C:\Users\person\private"}},
        {"metadata": {"value": "ark-1234567890abcdef"}},
    ],
)
def test_safe_json_rejects_sensitive_values(tmp_path: Path, payload: dict) -> None:
    path = _write(tmp_path / "summary.json", payload)

    with pytest.raises(ValueError):
        _load_safe_json(path)


def test_safe_json_allows_governance_flags_and_hashes(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "summary.json",
        {
            "raw_prompt_persisted": False,
            "raw_response_persisted": False,
            "exact_text_hash": "a" * 64,
            "api_key_present": True,
        },
    )

    assert _load_safe_json(path)["exact_text_hash"] == "a" * 64
