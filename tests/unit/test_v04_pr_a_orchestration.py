from __future__ import annotations

import csv
import json
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from ipo_risk.schemas import IPOAnalysisResult, TaskStatus
from scripts import run_v04_pr_a as pr_a


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _catalog(tmp_path: Path) -> Path:
    catalog = tmp_path / "data" / "catalog"
    fields = [
        "case_id",
        "source_year",
        "stock_code_raw",
        "stock_code_wind",
        "dataset_split",
        "official_match_status",
        "official_listed_date",
        "official_ipo_price",
    ]
    _write_csv(
        catalog / "ipo_official_master_bridge.csv",
        fields,
        [
            {
                "case_id": "ipo_2024_00368",
                "source_year": "2024",
                "stock_code_raw": "00368",
                "stock_code_wind": "0368.HK",
                "dataset_split": "validation",
                "official_match_status": "matched",
                # Deliberately 2023: PR-A must use official listing year, not source_year.
                "official_listed_date": "2023-01-03",
                "official_ipo_price": "1.25",
            },
            {
                "case_id": "ipo_2024_00999",
                "source_year": "2024",
                "stock_code_raw": "00999",
                "stock_code_wind": "0999.HK",
                "dataset_split": "validation",
                "official_match_status": "matched",
                "official_listed_date": "2024-02-01",
                "official_ipo_price": "2.50",
            },
            {
                "case_id": "ipo_2025_00700",
                "source_year": "2025",
                "stock_code_raw": "00700",
                "stock_code_wind": "0700.HK",
                "dataset_split": "blind_test",
                "official_match_status": "matched",
                "official_listed_date": "2025-01-02",
                "official_ipo_price": "99.0",
            },
        ],
    )
    _write_csv(
        catalog / "ipo_prospectus_manifest.csv",
        ["case_id", "sha256", "relative_path", "company_short_name"],
        [
            {
                "case_id": "ipo_2024_00368",
                "sha256": "a" * 64,
                "relative_path": "2024/00368.pdf",
                "company_short_name": "A",
            },
            {
                "case_id": "ipo_2024_00999",
                "sha256": "b" * 64,
                "relative_path": "2024/00999.pdf",
                "company_short_name": "B",
            },
            {
                "case_id": "ipo_2025_00700",
                "sha256": "c" * 64,
                "relative_path": "2025/00700.pdf",
                "company_short_name": "C",
            },
        ],
    )
    return catalog


def _authoritative_result(case_id: str = "ipo_2024_00368") -> IPOAnalysisResult:
    return IPOAnalysisResult(
        analysis_id=f"analysis-{case_id}",
        request_id=f"request-{case_id}",
        company_name="Fixture IPO",
        stock_code="0368.HK",
        workflow_version="enhanced_v2",
        schema_version="1.0",
        status=TaskStatus.COMPLETED,
        metadata={
            "case_id": case_id,
            "dataset_split": "validation",
            "ipo_profile": {
                "stock_code": "0368.HK",
                "listing_date": "2023-01-03",
            },
            "configuration": {
                "workflow_version": "enhanced_v2",
                "use_mock": False,
            },
            "component_modes": {
                "workflow": "enhanced_v2",
                "parser": "real",
                "retriever": "real",
                "financial_agent": "real",
                "legal_agent": "real",
                "business_agent": "real",
            },
            "supervision": {"conflicts": []},
        },
    )


def test_official_selection_uses_listing_year_and_excludes_2025(tmp_path: Path) -> None:
    catalog = _catalog(tmp_path)
    metadata = pr_a.load_official_metadata(catalog)
    assert tuple(item.case_id for item in metadata) == (
        "ipo_2024_00368",
        "ipo_2024_00999",
    )
    first = metadata[0]
    assert first.cohort_year == 2023
    context = pr_a.build_snapshot_context(first, pipeline_commit="a" * 40)
    assert context.dataset_split.value == "development"
    assert context.cohort_year == 2023


def test_case_selection_is_deterministic_and_rejects_outside_cohort(tmp_path: Path) -> None:
    metadata = pr_a.load_official_metadata(_catalog(tmp_path))
    assert tuple(item.case_id for item in pr_a.select_metadata(metadata, limit=1)) == (
        "ipo_2024_00368",
    )
    with pytest.raises(ValueError, match="outside official"):
        pr_a.select_metadata(metadata, case_ids=["ipo_2025_00700"])


def test_clean_worktree_is_accepted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        pr_a.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0, stdout="", stderr=""
        ),
    )
    pr_a.require_clean_worktree(tmp_path)


def test_dirty_worktree_is_rejected_before_production(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "argv", ["run_v04_pr_a.py", "--repo-root", str(tmp_path)])
    monkeypatch.setattr(
        pr_a.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0, stdout=" M scripts/run_v04_pr_a.py\n", stderr=""
        ),
    )
    monkeypatch.setattr(
        pr_a,
        "load_official_metadata",
        lambda *args, **kwargs: pytest.fail("production preflight was reached"),
    )
    with pytest.raises(RuntimeError, match="clean git working tree"):
        pr_a.main()


def test_offline_config_masks_and_restores_ambient_llm_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "v03_offline.yaml"
    config.write_text(
        "runtime_mode: offline\nllm_provider: unavailable\n",
        encoding="utf-8",
    )
    for name in pr_a.OFFLINE_PROVIDER_ENV_VARS:
        monkeypatch.setenv(name, "sensitive-runtime-value")

    with pr_a.offline_provider_boundary(config):
        assert all(name not in pr_a.os.environ for name in pr_a.OFFLINE_PROVIDER_ENV_VARS)

    assert all(
        pr_a.os.environ[name] == "sensitive-runtime-value"
        for name in pr_a.OFFLINE_PROVIDER_ENV_VARS
    )


def test_offline_config_rejects_network_llm_provider(tmp_path: Path) -> None:
    config = tmp_path / "invalid_offline.yaml"
    config.write_text(
        "runtime_mode: offline\nllm_provider: openai\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="llm_provider: unavailable"):
        with pr_a.offline_provider_boundary(config):
            pytest.fail("invalid offline config entered runtime boundary")


def test_execution_context_is_portable_hashed_and_reusable(tmp_path: Path) -> None:
    catalog = _catalog(tmp_path)
    config = tmp_path / "configs" / "v03_offline.yaml"
    config.parent.mkdir(parents=True)
    config.write_text("workflow_version: enhanced_v2\nuse_mock: false\n", encoding="utf-8")
    selected = pr_a.load_official_metadata(catalog)[:1]
    output = tmp_path / "reports" / "v04_pr_a"

    first = pr_a.freeze_execution_context(
        repo_root=tmp_path,
        catalog_dir=catalog,
        config_path=config,
        output_dir=output,
        selected=selected,
        revision="a" * 40,
        resume=False,
    )
    second = pr_a.freeze_execution_context(
        repo_root=tmp_path,
        catalog_dir=catalog,
        config_path=config,
        output_dir=output,
        selected=selected,
        revision="a" * 40,
        resume=True,
    )
    assert first == second
    encoded = (output / "execution_context.json").read_text(encoding="utf-8")
    assert str(tmp_path) not in encoded
    assert first["config"]["relative_path"] == "configs/v03_offline.yaml"
    assert len(first["document_feature_manifest_hash"]) == 64
    assert len(first["selected_case_ids_hash"]) == 64

    config.write_text("workflow_version: enhanced_v2\nuse_mock: true\n", encoding="utf-8")
    with pytest.raises(ValueError, match="existing artifact differs"):
        pr_a.freeze_execution_context(
            repo_root=tmp_path,
            catalog_dir=catalog,
            config_path=config,
            output_dir=output,
            selected=selected,
            revision="a" * 40,
            resume=True,
        )


def test_production_orchestration_reuses_existing_components(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    catalog = _catalog(tmp_path)
    selected = pr_a.load_official_metadata(catalog)[:1]
    output = tmp_path / "reports" / "v04_pr_a"
    data_root = tmp_path / "pdfs"
    config = tmp_path / "configs" / "v03_offline.yaml"
    config.parent.mkdir(parents=True)
    config.write_text("workflow_version: enhanced_v2\n", encoding="utf-8")

    def fake_run_batch(**kwargs):
        analysis_dir = Path(kwargs["output_dir"])
        cases = analysis_dir / "cases"
        cases.mkdir(parents=True, exist_ok=True)
        case_id = selected[0].case_id
        (cases / f"{case_id}.json").write_text(
            _authoritative_result(case_id).model_dump_json(indent=2), encoding="utf-8"
        )
        outcome = SimpleNamespace(case_id=case_id, status="completed", message="")
        return SimpleNamespace(outcomes=[outcome])

    monkeypatch.setattr(pr_a, "run_batch", fake_run_batch)
    states = pr_a.run_production(
        selected=selected,
        catalog_dir=catalog,
        data_root=data_root,
        config_path=config,
        output_dir=output,
        revision="a" * 40,
        resume=False,
    )
    state = states[selected[0].case_id]
    assert state["production_document_available"] is True
    assert state["snapshot_status"] == "created"
    assert state["feature_status"] == "created"
    assert len(state["snapshot_hash"]) == 64
    assert len(state["feature_hash"]) == 64

    feature = json.loads(
        (output / "production_features" / f"{selected[0].case_id}.json").read_text(
            encoding="utf-8"
        )
    )
    assert feature["cohort_year"] == 2023
    assert feature["dataset_split"] == "development"
    assert feature["feature_manifest_hash"] == pr_a.DOCUMENT_FEATURE_MANIFEST_V1.content_hash()


def test_oracle_missing_gold_is_explicit_not_silently_dropped(tmp_path: Path) -> None:
    selected = pr_a.load_official_metadata(_catalog(tmp_path))
    states = pr_a.run_oracle(
        repo_root=tmp_path,
        selected=selected,
        output_dir=tmp_path / "reports" / "v04_pr_a",
        resume=False,
    )
    assert set(states) == {item.case_id for item in selected}
    assert all(row["status"] == "unavailable" for row in states.values())
    assert all(row["failure_reason"] == "no_reviewed_gold" for row in states.values())


def test_coverage_keeps_every_selected_case_and_separates_source_year(tmp_path: Path) -> None:
    catalog = _catalog(tmp_path)
    selected = pr_a.load_official_metadata(catalog)
    first, second = selected
    production = {
        first.case_id: {
            "analysis_status": "completed",
            "snapshot_status": "created",
            "production_document_available": True,
            "failure_stage": "",
            "failure_reason": "",
            "snapshot_hash": "a" * 64,
            "feature_hash": "b" * 64,
            "feature_manifest_hash": "c" * 64,
        }
    }
    oracle = {
        second.case_id: {
            "oracle_document_available": True,
            "failure_reason": "",
            "feature_hash": "d" * 64,
            "feature_manifest_hash": "e" * 64,
            "effective_annotation_hash": "f" * 64,
        }
    }
    output = tmp_path / "reports" / "coverage"
    summary = pr_a.build_coverage(
        selected=selected,
        catalog_dir=catalog,
        production=production,
        oracle=oracle,
        output_dir=output,
    )
    with (output / "coverage.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert rows[0]["source_year"] == "2024"
    assert rows[0]["official_listing_year"] == "2023"
    assert rows[0]["dataset_split"] == "development"
    assert rows[1]["production_document_available"] == "false"
    assert rows[1]["oracle_document_available"] == "true"
    assert summary["selected_case_count"] == 2
    assert summary["production_materialized_count"] == 1
    assert summary["oracle_materialized_count"] == 1
    assert summary["production_oracle_intersection_count"] == 0


def test_conflict_safe_writer_never_overwrites_different_provenance(tmp_path: Path) -> None:
    target = tmp_path / "artifact.json"
    assert pr_a._write_json_conflict_safe(target, {"hash": "a"}, resume=False) == "created"
    assert pr_a._write_json_conflict_safe(target, {"hash": "a"}, resume=True) == "reused"
    before = target.read_bytes()
    with pytest.raises(ValueError, match="existing artifact differs"):
        pr_a._write_json_conflict_safe(target, {"hash": "b"}, resume=True)
    assert target.read_bytes() == before
