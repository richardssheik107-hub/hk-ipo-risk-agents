from __future__ import annotations

import csv
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5
import zipfile

import pytest

from ipo_risk.runtime.submission_readiness import (
    ROLE_E_CASE_REQUIRED,
    _scan_path_for_sensitive_material,
    build_artifact_index,
    build_submission_readiness,
    package_submission_bundle,
    write_artifact_index,
    write_submission_audits,
)


def _json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _csv(path: Path, fieldnames: list[str], row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)


def _repo(root: Path) -> None:
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs/SUBMISSION_RUNBOOK.md").write_text("# runbook\n", encoding="utf-8")
    (root / "README.md").write_text("# project\n", encoding="utf-8")
    (root / ".env.example").write_text("IPO_RISK_LLM_API_KEY=\n", encoding="utf-8")


def _role_b(root: Path) -> None:
    _json(
        root / "document_benchmark_summary.json",
        {
            "benchmark_version": "v045_role_b_real_document_benchmark_v1",
            "result": "PASS",
            "real_llm_cases": 10,
            "external_llm_called": True,
            "risk_target_at_least_80_percent": True,
            "evidence_target_at_least_85_percent": True,
            "blind_2025_outcome_accessed": False,
        },
    )
    _csv(root / "risk_benchmark.csv", ["risk_code", "precision", "recall", "f1"], {"risk_code": "r", "precision": 1, "recall": 1, "f1": 1})
    _csv(root / "evidence_benchmark.csv", ["risk_code", "recall_at_5"], {"risk_code": "r", "recall_at_5": 1})
    _json(root / "ai_vs_offline_report.json", {"comparison": "governed", "blind_2025_outcome_accessed": False})


def _role_d(root: Path) -> None:
    _csv(root / "test_predictions.csv", ["case_id", "score"], {"case_id": "c", "score": 0.2})
    fields = ["case_id", "return_1d", "return_5d", "return_20d", "return_60d"]
    _csv(
        root / "multi_horizon_results.csv",
        fields,
        {"case_id": "c", "return_1d": 0.01, "return_5d": 0.02, "return_20d": 0.03, "return_60d": 0.04},
    )
    _json(root / "evaluation_summary.json", {"blind_2025_y_accessed": False, "status": "complete"})


def _case_payload(case_id: str, stock_code: str, listing_date: str, digest: str) -> dict:
    request_id = str(uuid5(NAMESPACE_URL, f"v04-real-e2e:{stock_code}:{listing_date}:{digest}"))
    return {
        "case_id": case_id,
        "stock_code": stock_code,
        "listing_date": listing_date,
        "status": "completed",
        "deterministic_request_id": request_id,
        "parsed_chunk_count": 100,
        "final_supervision_content_hash": "ab" * 32,
        "channel_states": {"document": "available", "market": "available", "model": "unavailable", "rule": "available"},
        "gate_e1": {"satisfied": True},
        "traceability": {"overall_traceability": 1.0},
        "prospectus_verification": {"sha256": digest},
    }


def _role_e(root: Path, gate_satisfied: bool = True) -> None:
    cases = []
    for index, (case_id, stock_code) in enumerate(
        (("ipo_2024_02410", "2410.HK"), ("ipo_2024_02460", "2460.HK"), ("ipo_2024_01318", "1318.HK")),
        start=1,
    ):
        digest = f"{index:02x}" * 32
        case = _case_payload(case_id, stock_code, "2024-08-20", digest)
        case["gate_e1"] = {"satisfied": gate_satisfied}
        cases.append(case)
        case_root = root / case_id
        verification = {
            "sha256": digest,
            "sha256_matches_frozen_catalog": True,
            "size_matches_frozen_catalog": True,
            "page_count_matches_frozen_catalog": True,
            "path_recorded": False,
        }
        sidecar = {
            "identity": {
                "run_id": f"run-{index}",
                "provenance": {
                    "workflow": "v04_competition",
                    "trace_schema_version": "v04_e_agent_trace_v1",
                    "conflict_policy_version": "v04_e_conflict_policy_v1",
                    "recheck_policy_version": "v04_e_recheck_policy_v1",
                },
            },
            "trace_events": [
                {
                    "event_id": f"market-{index}",
                    "event_type": "market",
                    "agent_name": "market_intelligence",
                    "tool_or_skill": "IPOHeatSkill",
                    "evidence_ids": ["market_feature:hsi"],
                    "calculation_ids": [],
                    "details": {},
                }
            ],
        }
        gate = {
            "satisfied": gate_satisfied,
            "call": {
                "provider_name": "openai_compatible",
                "model_name": "model",
                "prompt_version": "v04_final_supervision_v1",
                "request_id": f"req-{index}",
                "raw_response_hash": "cd" * 32,
                "latency_ms": 50,
            },
        }
        for name in ROLE_E_CASE_REQUIRED:
            if name == "prospectus_verification.json":
                _json(case_root / name, verification)
            elif name == "trace_sidecar.json":
                _json(case_root / name, sidecar)
            elif name == "gate_e1_evidence.json":
                _json(case_root / name, gate)
            elif name == "final_supervision.json":
                _json(case_root / name, {"llm_synthesis": {"call": gate["call"]}})
            elif name.endswith(".json"):
                _json(case_root / name, {})
            else:
                (case_root / name).parent.mkdir(parents=True, exist_ok=True)
                (case_root / name).write_text("recorded artifact\n", encoding="utf-8")
    _json(
        root / "summary.json",
        {
            "declared_case_count": 3,
            "executed_case_count": 3,
            "all_prospectus_sha256_verified": True,
            "blind_2025_y_accessed": False,
            "outcome_labels_accessed": False,
            "gate_e1": {"satisfied": gate_satisfied},
            "cases": cases,
        },
    )


def _ready_tree(tmp_path: Path):
    repo = tmp_path / "repo"
    b = tmp_path / "b"
    d = tmp_path / "d"
    e = tmp_path / "e"
    a = tmp_path / "a"
    _repo(repo)
    _role_b(b)
    _role_d(d)
    _role_e(e)
    return repo, b, d, e, a


def test_all_governed_handoffs_produce_competition_ready(tmp_path: Path) -> None:
    repo, b, d, e, a = _ready_tree(tmp_path)
    readiness, blind, provenance, determinism = build_submission_readiness(
        repo_root=repo,
        role_b_dir=b,
        role_d_dir=d,
        role_e_dir=e,
        a_output_dir=a,
    )
    assert readiness["competition_ready"] is True
    assert readiness["verdict"] == "COMPETITION_READY"
    assert blind["passed"] is True
    assert provenance["passed"] is True
    assert determinism["passed"] is True
    assert all(gate["passed"] for gate in readiness["gates"])


def test_unaccepted_real_provider_gate_blocks_submission(tmp_path: Path) -> None:
    repo, b, d, e, a = _ready_tree(tmp_path)
    _role_e(e, gate_satisfied=False)
    readiness, *_ = build_submission_readiness(
        repo_root=repo,
        role_b_dir=b,
        role_d_dir=d,
        role_e_dir=e,
        a_output_dir=a,
    )
    assert readiness["competition_ready"] is False
    assert any("Gate E1" in blocker for blocker in readiness["blockers"])


def test_missing_multi_horizon_column_blocks_d(tmp_path: Path) -> None:
    repo, b, d, e, a = _ready_tree(tmp_path)
    _csv(d / "multi_horizon_results.csv", ["case_id", "return_1d"], {"case_id": "c", "return_1d": 0.01})
    readiness, *_ = build_submission_readiness(
        repo_root=repo,
        role_b_dir=b,
        role_d_dir=d,
        role_e_dir=e,
        a_output_dir=a,
    )
    assert readiness["competition_ready"] is False
    d_gate = next(item for item in readiness["gates"] if item["owner"] == "D")
    assert d_gate["passed"] is False
    assert "return_60d" in " ".join(d_gate["blockers"])


def test_audit_writer_and_index_hash_real_files(tmp_path: Path) -> None:
    repo, b, d, e, a = _ready_tree(tmp_path)
    readiness, blind, provenance, determinism = build_submission_readiness(
        repo_root=repo,
        role_b_dir=b,
        role_d_dir=d,
        role_e_dir=e,
        a_output_dir=a,
    )
    write_submission_audits(
        output_dir=a,
        readiness=readiness,
        blind=blind,
        provenance=provenance,
        determinism=determinism,
    )
    index = build_artifact_index(
        role_b_dir=b,
        role_d_dir=d,
        role_e_dir=e,
        a_output_dir=a,
        runbook_path=repo / "docs/SUBMISSION_RUNBOOK.md",
    )
    write_artifact_index(a / "artifact_index.json", index)
    assert index["artifact_count"] > 20
    assert all(len(item["sha256"]) == 64 for item in index["artifacts"])


def test_the_audits_never_write_the_local_path_their_own_packager_forbids(
    tmp_path: Path,
) -> None:
    """The tooling must not refuse its own output.

    The audits are packaged and shipped, and the packager rejects any artifact
    carrying a local absolute path. Recording the role directories verbatim made
    that self-contradictory whenever the dirs were passed as absolute paths --
    which is exactly what a run outside the working tree does. The scan itself is
    the oracle here, so the producer and the check cannot drift apart again.
    """
    repo, b, d, e, a = _ready_tree(tmp_path)
    assert b.is_absolute(), "the fixture must exercise absolute role directories"

    readiness, blind, provenance, determinism = build_submission_readiness(
        repo_root=repo, role_b_dir=b, role_d_dir=d, role_e_dir=e, a_output_dir=a
    )
    write_submission_audits(
        output_dir=a,
        readiness=readiness,
        blind=blind,
        provenance=provenance,
        determinism=determinism,
    )
    for written in sorted(a.glob("*.json")):
        assert _scan_path_for_sensitive_material(written) == [], written.name


def test_packager_refuses_before_competition_ready(tmp_path: Path) -> None:
    repo, b, d, e, a = _ready_tree(tmp_path)
    a.mkdir(parents=True, exist_ok=True)
    _json(a / "submission_readiness.json", {"competition_ready": False})
    with pytest.raises(RuntimeError, match="COMPETITION_READY"):
        package_submission_bundle(
            repo_root=repo,
            role_b_dir=b,
            role_d_dir=d,
            role_e_dir=e,
            a_output_dir=a,
            output_zip=tmp_path / "submission.zip",
        )


def test_ready_packager_has_manifest_and_no_pdf(tmp_path: Path) -> None:
    repo, b, d, e, a = _ready_tree(tmp_path)
    readiness, blind, provenance, determinism = build_submission_readiness(
        repo_root=repo,
        role_b_dir=b,
        role_d_dir=d,
        role_e_dir=e,
        a_output_dir=a,
    )
    write_submission_audits(
        output_dir=a,
        readiness=readiness,
        blind=blind,
        provenance=provenance,
        determinism=determinism,
    )
    index = build_artifact_index(
        role_b_dir=b,
        role_d_dir=d,
        role_e_dir=e,
        a_output_dir=a,
        runbook_path=repo / "docs/SUBMISSION_RUNBOOK.md",
    )
    write_artifact_index(a / "artifact_index.json", index)
    manifest = package_submission_bundle(
        repo_root=repo,
        role_b_dir=b,
        role_d_dir=d,
        role_e_dir=e,
        a_output_dir=a,
        output_zip=tmp_path / "submission.zip",
    )
    assert manifest["competition_ready"] is True
    assert len(manifest["bundle_sha256"]) == 64
    with zipfile.ZipFile(tmp_path / "submission.zip") as archive:
        names = archive.namelist()
        assert "submission_manifest.json" in names
        assert not any(name.casefold().endswith(".pdf") for name in names)
        embedded = json.loads(archive.read("submission_manifest.json"))
        assert embedded["security"]["licensed_pdf_included"] is False
