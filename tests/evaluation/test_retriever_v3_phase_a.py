from pathlib import Path
import hashlib
import json
import tempfile

import pytest

from ipo_risk.evaluation.retriever_v3 import (
    EffectiveQrel, candidate_judgement, classify_failure, completion_at,
    deterministic_split, oracle_union, recall_at, resolve_qrels, rrf_fuse, unique_contribution,
    validate_case_sets,
)
import scripts.refresh_expert_results_from_main as refresh
from scripts.refresh_expert_results_from_main import (
    REMOTE_PATTERN, require_remote_count, restore, safe_expert_results_path,
)


def _qrel(page: int) -> EffectiveQrel:
    return EffectiveQrel("c", "r", page, "primary", "required", "business", 1.0,
                         "e", 3, "JUDGED", "a.json", "not_available", "")


def test_split_is_deterministic_and_has_no_leakage():
    cases = [f"ipo_2022_{index:05d}" for index in range(20)]
    left, right = deterministic_split(cases)
    assert (left, right) == deterministic_split(reversed(cases))
    assert len(left) == len(right) == 10
    assert set(left).isdisjoint(right)


def test_dataset_gate_requires_60_and_historical_40():
    all_cases = [f"c{index}" for index in range(60)]
    historical, new = validate_case_sets(all_cases, all_cases[:40])
    assert len(historical) == 40 and len(new) == 20
    with pytest.raises(ValueError):
        validate_case_sets(all_cases[:-1], all_cases[:40])


def test_unannotated_candidate_is_unjudged():
    assert candidate_judgement(9, [_qrel(3)]) == (-1, "UNJUDGED", "")
    assert candidate_judgement(3, [_qrel(3)])[:2] == (3, "JUDGED")


def test_recall_and_multiple_required_completion():
    assert recall_at([1, None, 5], 5) == pytest.approx(2 / 3)
    groups = {("a", "r"): [1, 5], ("b", "r"): [1, None]}
    assert completion_at(groups, 5) == 0.5


def test_unique_contribution_and_oracle():
    rows = [{"v1": True, "v2": False, "v21": False},
            {"v1": False, "v2": True, "v21": True},
            {"v1": False, "v2": False, "v21": False}]
    counts = unique_contribution(rows)
    assert counts["V1_only"] == 1 and counts["V2_and_V21"] == 1 and counts["none"] == 1
    assert oracle_union(rows, ("v1", "v2")) == pytest.approx(2 / 3)


def test_equal_weight_rrf_is_deterministic():
    rankings = {"v1": [1, 2, 3], "v2": [3, 2, 4], "v21": [3, 5]}
    assert rrf_fuse(rankings) == rrf_fuse(dict(reversed(list(rankings.items()))))
    assert rrf_fuse(rankings)[0] == 3


def test_failure_taxonomy_separates_ranking_and_candidate_generation():
    assert classify_failure(page_present=False, native_ranks={}, top20_ranks={})[0] == "PARSER_OR_INPUT_MISS"
    assert classify_failure(page_present=True, native_ranks={"v1": 31}, top20_ranks={"v1": 31})[0] == "RANKING_ONLY_MISS"
    assert classify_failure(page_present=True, native_ranks={"v1": None}, top20_ranks={}, table_like=True)[0] == "TABLE_FRAGMENTATION"
    assert classify_failure(page_present=True, native_ranks={"v1": None}, top20_ranks={})[0] == "QUERY_COVERAGE_MISS"


def test_remote_enumeration_contract_excludes_real_case_and_count_gate():
    valid = [f"expert_results/ipo_2022_{index:05d}/pass1/expert_annotation_v1.json" for index in range(60)]
    assert all(REMOTE_PATTERN.fullmatch(path) for path in valid)
    assert not REMOTE_PATTERN.fullmatch("expert_results/real_case_001/pass1/expert_annotation_v1.json")
    require_remote_count(valid)
    with pytest.raises(ValueError):
        require_remote_count(valid[:-1])


def test_safe_expert_results_path_guard(tmp_path: Path):
    assert safe_expert_results_path(tmp_path, tmp_path / "expert_results") == (tmp_path / "expert_results").resolve()
    with pytest.raises(ValueError):
        safe_expert_results_path(tmp_path, tmp_path)


def test_temporary_directory_cleanup(tmp_path: Path):
    with tempfile.TemporaryDirectory(prefix=".tmp_retriever_v3_", dir=tmp_path) as name:
        current = Path(name) / "current.pdf"
        current.write_bytes(b"temporary")
        root = Path(name)
    assert not root.exists()


def test_restore_writes_exactly_60_annotation_blobs(monkeypatch, tmp_path: Path):
    blobs = {}
    records = []
    for index in range(60):
        case = f"ipo_2022_{index:05d}"
        path = f"expert_results/{case}/pass1/expert_annotation_v1.json"
        content = json.dumps({"case_id": case, "risks": []}).encode()
        blobs[path] = content
        records.append({"path": path, "case_id": case, "sha256": hashlib.sha256(content).hexdigest()})
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"remote_ref": "origin/main", "remote_annotations": records}), encoding="utf-8")

    def fake_git(repo, *args):
        assert args[0] == "show"
        return blobs[args[1].split(":", 1)[1]]

    monkeypatch.setattr(refresh, "_git", fake_git)
    assert restore(tmp_path, manifest) == 60
    assert len(list((tmp_path / "expert_results").rglob("expert_annotation_v1.json"))) == 60


def test_gold_resolver_keeps_pages_and_attaches_audit(tmp_path: Path):
    annotation = tmp_path / "expert_results/ipo_2022_00001/pass1/expert_annotation_v1.json"
    annotation.parent.mkdir(parents=True)
    annotation.write_text(json.dumps({"case_id": "ipo_2022_00001", "risks": [{"risk_code": "cash_runway", "evidence": [
        {"page": 7, "evidence_role": "primary", "requirement": "required", "source_authority": "accountants_report", "exact_text": "cash"}
    ]}]}), encoding="utf-8")
    audit = annotation.parent.parent / "audit/financial_resolution_v1.json"
    audit.parent.mkdir(parents=True)
    audit.write_text(json.dumps({"entries": [{"risk_code": "cash_runway", "closure_status": "CLOSED"}]}), encoding="utf-8")
    qrels = resolve_qrels(annotation, repository_root=tmp_path)
    assert [(item.page, item.gold_label, item.audit_status) for item in qrels] == [(7, 3, "available")]
