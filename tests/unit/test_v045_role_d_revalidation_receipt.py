from __future__ import annotations

import json
from pathlib import Path

from ipo_risk.evaluation.role_d_revalidation_receipt import (
    _canonical_text_sha256,
    validate_role_d_revalidation_receipt,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
RECEIPT = (
    REPO_ROOT
    / "reports/frozen/v045_role_d_current_main_revalidation_receipt.json"
)
PR_F = REPO_ROOT / "reports/frozen/v04_pr_f_lightgbm_manifest.json"
PR_E = REPO_ROOT / "reports/frozen/v04_pr_e_baseline_manifest.json"
PROTOCOL = REPO_ROOT / "configs/v045_competition_metric_protocol.json"


def _validate(path: Path = RECEIPT) -> dict:
    return validate_role_d_revalidation_receipt(
        path,
        pr_f_manifest_path=PR_F,
        pr_e_manifest_path=PR_E,
        metric_protocol_path=PROTOCOL,
    )


def test_committed_current_main_revalidation_receipt_passes() -> None:
    result = _validate()

    assert result["passed"] is True
    assert result["verdict"] == "PASS"
    assert result["blockers"] == []
    assert all(result["checks"].values())


def test_canonical_text_hash_treats_lf_and_crlf_as_equivalent(
    tmp_path: Path,
) -> None:
    lf = tmp_path / "lf.json"
    crlf = tmp_path / "crlf.json"
    logical_text = '{\n  "status": "frozen"\n}\n'
    lf.write_bytes(logical_text.encode("utf-8"))
    crlf.write_bytes(logical_text.replace("\n", "\r\n").encode("utf-8"))

    assert _canonical_text_sha256(lf) == _canonical_text_sha256(crlf)


def test_canonical_text_hash_rejects_content_mutation(tmp_path: Path) -> None:
    original = tmp_path / "original.json"
    mutated = tmp_path / "mutated.json"
    original.write_text('{"status":"frozen"}\n', encoding="utf-8")
    mutated.write_text('{"status":"changed"}\n', encoding="utf-8")

    assert _canonical_text_sha256(original) != _canonical_text_sha256(mutated)


def test_revalidation_receipt_rejects_artifact_drift(tmp_path: Path) -> None:
    payload = json.loads(RECEIPT.read_text(encoding="utf-8"))
    payload["artifact_sha256"] = {}
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    result = _validate(path)

    assert result["passed"] is False
    assert result["checks"]["artifact_hashes"] is False


def test_revalidation_receipt_rejects_unsafe_governance(tmp_path: Path) -> None:
    payload = json.loads(RECEIPT.read_text(encoding="utf-8"))
    payload["governance"]["validation_retuning_performed"] = True
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    result = _validate(path)

    assert result["passed"] is False
    assert result["checks"]["governance"] is False
