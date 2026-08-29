from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ipo_risk.runtime.product_capability_acceptance import (
    AUDITABLE_PROOF_CAPABILITIES,
    CAPABILITY_PROOF_DIR,
    CAPABILITY_PROOF_SCHEMA_VERSION,
    REQUIRED_CAPABILITIES,
    ProductCapabilityAcceptanceError,
    build_capability_manifest,
    build_product_acceptance,
    evaluate_capability_proof,
    verify_persisted,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_current_governed_evidence_closes_g5_without_opening_validation() -> None:
    artifact = build_product_acceptance(REPO_ROOT)
    assert artifact["status"] == "pass"
    assert artifact["truthful_channel_states"] is True
    assert set(artifact["modes"]) == {
        "offline_demo_replay",
        "historical_governed_ipo",
        "fresh_new_ipo_analysis",
    }
    assert artifact["governance"]["validation_opened"] is False
    assert artifact["governance"]["blind_2025_y_accessed"] is False


def test_current_capability_manifest_fails_closed_without_real_case_proofs() -> None:
    artifact = build_capability_manifest(REPO_ROOT)
    assert artifact["status"] == "fail"
    assert artifact["capabilities"] == list(REQUIRED_CAPABILITIES)
    assert artifact["incomplete_capabilities"] == list(AUDITABLE_PROOF_CAPABILITIES)
    details = {item["capability"]: item for item in artifact["capability_details"]}
    for capability in AUDITABLE_PROOF_CAPABILITIES:
        detail = details[capability]
        assert detail["implementation_evidence_present"] is True
        assert detail["proof_complete"] is False
        assert detail["status"] == "fail"
        assert detail["missing_reasons"]
    assert all(
        item["classification"] == "QUALITATIVE_DEMONSTRATION"
        and item["included_in_m1_m2"] is False
        for item in artifact["capability_details"]
    )


def _write_artifact(root: Path, relative_path: str, payload) -> dict[str, str]:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, (dict, list)):
        path.write_text(json.dumps(payload), encoding="utf-8")
    else:
        path.write_text(str(payload), encoding="utf-8")
    return {
        "path": relative_path,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _complete_proof(root: Path, capability: str, payload: dict) -> tuple[dict, Path]:
    input_ref = _write_artifact(root, "fixtures/input.json", {"case_id": "case-1"})
    output_ref = _write_artifact(root, "fixtures/output.json", payload)
    evidence_ref = _write_artifact(root, "fixtures/evidence.txt", "bounded source")
    trace_ref = _write_artifact(root, "fixtures/trace.json", {"trace_id": "trace-1"})
    product_ref = _write_artifact(root, "fixtures/report.md", "auditable projection")
    proof = {
        "schema_version": CAPABILITY_PROOF_SCHEMA_VERSION,
        "capability": capability,
        "status": "pass",
        "classification": "QUALITATIVE_DEMONSTRATION",
        "included_in_m1_m2": False,
        "case": {"case_id": "case-1", "input_artifact": input_ref},
        "output": {"artifact": output_ref, "payload": payload},
        "evidence": [
            {
                "evidence_id": "e-1",
                "source_artifact": evidence_ref,
                "locator": {"page": 8},
            }
        ],
        "provenance": {
            "producer": "capability-agent",
            "schema_version": "trace-v1",
            "trace_id": "trace-1",
            "input_sha256": input_ref["sha256"],
            "trace_artifact": trace_ref,
        },
        "product_proof": {"kind": "report", "artifact": product_ref},
    }
    path = root / CAPABILITY_PROOF_DIR / f"{capability}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(proof), encoding="utf-8")
    return proof, path


@pytest.mark.parametrize(
    ("capability", "payload"),
    (
        (
            "text_embellishment",
            {"tone_risk": True, "supporting_evidence_ids": ["e-1"]},
        ),
        (
            "related_party_transaction",
            {
                "counterparty": "Controller",
                "relationship": "controlling shareholder",
                "transaction_nature": "continuing service agreement",
                "evidence_ids": ["e-1"],
            },
        ),
        (
            "comparable_ipo_valuation",
            {
                "peer_identities": ["peer-1"],
                "valuation_calculation": {
                    "multiple": "price_to_adjusted_nta",
                    "target_value": 2.0,
                    "peer_values": [1.5],
                    "result": "premium",
                    "evidence_ids": ["e-1"],
                },
            },
        ),
    ),
)
def test_complete_auditable_proof_can_pass(
    tmp_path: Path, capability: str, payload: dict
) -> None:
    _complete_proof(tmp_path, capability, payload)
    result = evaluate_capability_proof(tmp_path, capability)
    assert result["proof_complete"] is True
    assert result["missing_reasons"] == []


def test_source_and_test_files_without_real_proof_do_not_pass(tmp_path: Path) -> None:
    result = evaluate_capability_proof(tmp_path, "text_embellishment")
    assert result["proof_complete"] is False
    assert set(result["missing_reasons"]) == {
        "missing_real_case_proof",
        "missing_capability_output",
        "missing_evidence_binding",
        "missing_provenance",
        "missing_product_projection",
    }


@pytest.mark.parametrize(
    ("field", "reason"),
    (
        ("evidence", "missing_evidence_binding"),
        ("provenance", "missing_provenance"),
        ("product_proof", "missing_product_projection"),
    ),
)
def test_incomplete_proof_fails_with_specific_reason(
    tmp_path: Path, field: str, reason: str
) -> None:
    proof, path = _complete_proof(
        tmp_path,
        "text_embellishment",
        {"tone_risk": True, "supporting_evidence_ids": ["e-1"]},
    )
    proof[field] = [] if field == "evidence" else {}
    path.write_text(json.dumps(proof), encoding="utf-8")
    result = evaluate_capability_proof(tmp_path, "text_embellishment")
    assert result["proof_complete"] is False
    assert reason in result["missing_reasons"]


def test_single_issuer_structure_feature_is_not_comparable_valuation_proof(
    tmp_path: Path,
) -> None:
    _complete_proof(
        tmp_path,
        "comparable_ipo_valuation",
        {"price_to_adj_nta": 2.0, "evidence_ids": ["e-1"]},
    )
    result = evaluate_capability_proof(tmp_path, "comparable_ipo_valuation")
    assert result["proof_complete"] is False
    assert "missing_capability_output" in result["missing_reasons"]


def test_stale_persisted_artifact_is_rejected(tmp_path: Path) -> None:
    artifact = build_product_acceptance(REPO_ROOT)
    path = tmp_path / "product_acceptance.json"
    stale = {**artifact, "truthful_channel_states": False}
    path.write_text(json.dumps(stale), encoding="utf-8")
    with pytest.raises(ProductCapabilityAcceptanceError, match="stale"):
        verify_persisted(artifact, path)

