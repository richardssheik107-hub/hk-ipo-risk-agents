from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from ipo_risk.evaluation.existing_gold_metrics import _result_case_id


ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "scripts" / "run_v045_role_b_iteration.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("v045_role_b_iteration_runner", RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_analysis_result(run_dir: Path, case_id: str, payload: dict) -> Path:
    path = run_dir / case_id / "analysis_result.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _read_single_jsonl(path: Path) -> dict:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    assert len(rows) == 1
    return rows[0]


def test_write_results_jsonl_injects_canonical_case_id_without_mutating_source(tmp_path: Path) -> None:
    runner = _load_runner()
    case_id = "ipo_2020_01167"
    run_dir = tmp_path / "run"
    source_payload = {
        "status": "completed",
        "metadata": {"component_modes": {"llm_provider": "openai_responses"}},
        "verified_risks": [{"risk_code": "redemption_rights"}],
    }
    source_path = _write_analysis_result(run_dir, case_id, source_payload)
    destination = tmp_path / "analysis_results.jsonl"

    assert runner._write_results_jsonl(run_dir, [case_id], destination) == 1

    row = _read_single_jsonl(destination)
    assert row["case_id"] == case_id
    assert row["verified_risks"] == source_payload["verified_risks"]
    assert _result_case_id(row) == case_id
    assert json.loads(source_path.read_text(encoding="utf-8")) == source_payload


def test_write_results_jsonl_accepts_matching_existing_identity(tmp_path: Path) -> None:
    runner = _load_runner()
    case_id = "ipo_2020_01167"
    run_dir = tmp_path / "run"
    payload = {
        "case_id": case_id,
        "status": "completed",
        "metadata": {"case_id": case_id},
        "pending_risks": [{"risk_code": "customer_concentration"}],
    }
    _write_analysis_result(run_dir, case_id, payload)
    destination = tmp_path / "analysis_results.jsonl"

    runner._write_results_jsonl(run_dir, [case_id], destination)
    row = _read_single_jsonl(destination)

    assert row["case_id"] == case_id
    assert row["metadata"]["case_id"] == case_id
    assert row["pending_risks"] == payload["pending_risks"]
    assert _result_case_id(row) == case_id


@pytest.mark.parametrize(
    "payload",
    [
        {"case_id": "ipo_2020_01942", "status": "completed"},
        {"metadata": {"case_id": "ipo_2020_01942"}, "status": "completed"},
    ],
)
def test_write_results_jsonl_fails_closed_on_conflicting_identity(
    tmp_path: Path, payload: dict
) -> None:
    runner = _load_runner()
    expected_case_id = "ipo_2020_01167"
    run_dir = tmp_path / "run"
    _write_analysis_result(run_dir, expected_case_id, payload)
    destination = tmp_path / "analysis_results.jsonl"

    with pytest.raises(runner.IterationRunnerError, match="case_id mismatch"):
        runner._write_results_jsonl(run_dir, [expected_case_id], destination)
