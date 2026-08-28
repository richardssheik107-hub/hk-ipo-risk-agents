from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from ipo_risk.evaluation.role_d_receipt import validate_role_d_materialization_receipt

REPO_ROOT = Path(__file__).resolve().parents[2]
RECEIPT = REPO_ROOT / "reports/frozen/v045_role_d_m5_materialization_receipt.json"
PR_F = REPO_ROOT / "reports/frozen/v04_pr_f_lightgbm_manifest.json"
PR_E = REPO_ROOT / "reports/frozen/v04_pr_e_baseline_manifest.json"
PROTOCOL = REPO_ROOT / "configs/v045_competition_metric_protocol.json"
SCRIPT = REPO_ROOT / "scripts/validate_v045_role_d_receipt.py"


def _validate(receipt: Path = RECEIPT):
    return validate_role_d_materialization_receipt(
        receipt,
        pr_f_manifest_path=PR_F,
        pr_e_manifest_path=PR_E,
        metric_protocol_path=PROTOCOL,
    )


def _mutated_receipt(tmp_path: Path, mutation) -> Path:
    payload = json.loads(RECEIPT.read_text(encoding="utf-8"))
    mutation(payload)
    path = tmp_path / "receipt.json"
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def test_committed_role_d_receipt_passes() -> None:
    result = _validate()

    assert result["passed"] is True
    assert result["verdict"] == "PASS"
    assert result["evaluation_case_count"] == 70
    assert result["artifact_count"] == 4
    assert result["metric_count"] == 8
    assert result["blockers"] == []
    assert all(result["checks"].values())


def test_receipt_rejects_missing_fourth_artifact(tmp_path: Path) -> None:
    path = _mutated_receipt(
        tmp_path,
        lambda payload: payload["artifact_sha256"].pop("ai_vs_offline_report.json"),
    )

    result = _validate(path)

    assert result["passed"] is False
    assert result["checks"]["artifact_contract"] is False


def test_receipt_rejects_pr_f_hash_drift(tmp_path: Path) -> None:
    path = _mutated_receipt(
        tmp_path,
        lambda payload: payload["input_bindings"]["pr_f"].__setitem__(
            "model_result_hash", "0" * 64
        ),
    )

    result = _validate(path)

    assert result["passed"] is False
    assert result["checks"]["pr_f_binding"] is False


def test_receipt_rejects_blind_access_or_validation_retuning(tmp_path: Path) -> None:
    def mutate(payload) -> None:
        payload["governance"]["blind_2025_y_accessed"] = True
        payload["governance"]["validation_retuning_performed"] = True

    result = _validate(_mutated_receipt(tmp_path, mutate))

    assert result["passed"] is False
    assert result["checks"]["governance"] is False


def test_receipt_rejects_local_absolute_paths(tmp_path: Path) -> None:
    def mutate(payload) -> None:
        payload["source"]["local_runtime"] = "/home/user/reports/v045_role_d"

    result = _validate(_mutated_receipt(tmp_path, mutate))

    assert result["passed"] is False
    assert result["checks"]["no_absolute_local_paths"] is False


def test_receipt_rejects_metric_or_horizon_drift(tmp_path: Path) -> None:
    def mutate(payload) -> None:
        payload["evaluation"]["horizons"] = [1, 5, 20]
        payload["five_day_metrics"].pop("base_prevalence")

    result = _validate(_mutated_receipt(tmp_path, mutate))

    assert result["passed"] is False
    assert result["checks"]["evaluation_horizons"] is False
    assert result["checks"]["metric_contract"] is False


def test_role_d_receipt_cli_is_fail_closed(tmp_path: Path) -> None:
    valid = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert valid.returncode == 0, valid.stdout + valid.stderr

    invalid_receipt = tmp_path / "invalid.json"
    shutil.copyfile(RECEIPT, invalid_receipt)
    payload = json.loads(invalid_receipt.read_text(encoding="utf-8"))
    payload["status"] = "unverified"
    invalid_receipt.write_text(json.dumps(payload), encoding="utf-8")

    invalid = subprocess.run(
        [sys.executable, str(SCRIPT), "--receipt", str(invalid_receipt)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert invalid.returncode == 2
    assert '"verdict": "FAIL"' in invalid.stdout
