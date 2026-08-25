from __future__ import annotations

import hashlib
import importlib.util
import inspect
import io
import json
import shutil
import zipfile
from pathlib import Path
from types import SimpleNamespace

import fitz
import pytest


SCRIPT = Path(__file__).parents[2] / "scripts" / "run_v045_role_b_offline_pdf_benchmark.py"
SPEC = importlib.util.spec_from_file_location("role_b_offline_pdf_benchmark", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _nested_zip(path: Path, *, inner_name: str = "09898_test.pdf", data: bytes = b"pdf") -> None:
    inner_bytes = io.BytesIO()
    with zipfile.ZipFile(inner_bytes, "w") as inner:
        inner.writestr(inner_name, data)
    with zipfile.ZipFile(path, "w") as outer:
        outer.writestr("root/2021_88份.zip", inner_bytes.getvalue())


def test_outer_and_nested_zip_use_exact_unique_members(tmp_path: Path) -> None:
    archive_path = tmp_path / "outer.zip"
    _nested_zip(archive_path)
    year_path = tmp_path / "current_year.zip"
    pdf_path = tmp_path / "current.pdf"
    with zipfile.ZipFile(archive_path) as outer:
        infos = MODULE.validate_archive_members(outer.infolist())
        info = MODULE.exact_member(infos, basename="2021_88份.zip")
        MODULE.stream_member(outer, info, year_path, buffer_bytes=2)
    with zipfile.ZipFile(year_path) as annual:
        infos = MODULE.validate_archive_members(annual.infolist())
        info = MODULE.exact_member(infos, basename="09898_test.pdf")
        MODULE.stream_member(annual, info, pdf_path, buffer_bytes=2)
    assert pdf_path.read_bytes() == b"pdf"


def test_case_allowlist_and_2024_2025_rejection() -> None:
    assert MODULE.validate_case_selection(["ipo_2021_09898"]) == ["ipo_2021_09898"]
    for case_id in ("ipo_2024_02410", "ipo_2025_00001"):
        with pytest.raises(MODULE.OfflineBenchmarkError, match="allowlist"):
            MODULE.validate_case_selection([case_id])


@pytest.mark.parametrize("name", ["../escape.pdf", "/absolute.pdf", "dir\\escape.pdf"])
def test_path_traversal_is_rejected(name: str) -> None:
    with pytest.raises(MODULE.OfflineBenchmarkError, match="unsafe"):
        MODULE._safe_member_name(name)


def test_duplicate_member_is_rejected() -> None:
    with pytest.raises(MODULE.OfflineBenchmarkError, match="duplicate"):
        MODULE.validate_archive_members(
            [zipfile.ZipInfo("same.pdf"), zipfile.ZipInfo("same.pdf")]
        )


def test_pdf_sha_and_page_count_validation(tmp_path: Path) -> None:
    path = tmp_path / "current.pdf"
    document = fitz.open()
    document.new_page()
    document.save(path)
    document.close()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    row = {
        "case_id": "ipo_2021_09898",
        "file_size_bytes": str(path.stat().st_size),
        "sha256": digest,
        "pdf_page_count": "1",
    }
    assert MODULE.validate_pdf_identity(path, row)["physical_pages"] == 1
    with pytest.raises(MODULE.OfflineBenchmarkError, match="SHA-256"):
        MODULE.validate_pdf_identity(path, {**row, "sha256": "0" * 64})
    with pytest.raises(MODULE.OfflineBenchmarkError, match="PAGE_COUNT_MISMATCH"):
        MODULE.validate_pdf_identity(path, {**row, "pdf_page_count": "2"})


def test_offline_only_guard_rejects_provider_and_mock() -> None:
    settings = MODULE.Settings(
        runtime_mode="offline",
        use_mock=False,
        parser="pymupdf",
        retriever="keyword",
        legal_agent="v03",
        business_agent="v03",
        llm_provider="unavailable",
        market_data_provider="unavailable",
    )
    MODULE.assert_offline_policy(settings)
    with pytest.raises(MODULE.OfflineBenchmarkError, match="offline-only"):
        MODULE.assert_offline_policy(MODULE.replace(settings, llm_provider="openai_responses"))
    with pytest.raises(MODULE.OfflineBenchmarkError, match="offline-only"):
        MODULE.assert_offline_policy(MODULE.replace(settings, use_mock=True))


def _risk() -> SimpleNamespace:
    evidence = SimpleNamespace(
        evidence_id="e-1",
        document_id="doc",
        chunk_id="chunk",
        page=3,
        section="Business",
        relevance_score=0.9,
        text="must never persist",
    )
    return SimpleNamespace(
        risk_id="r-1",
        risk_code="precommercial_product",
        verification_status=SimpleNamespace(value="verified"),
        agent_name="business_agent_v03",
        evidence=[evidence],
        calculation=None,
    )


def _analysis_result(*, parser_mode: str = "real") -> SimpleNamespace:
    return SimpleNamespace(
        metadata={
            "component_modes": {
                "parser": parser_mode,
                "retriever": "real",
                "legal_agent": "real",
                "business_agent": "real",
                "llm_provider": "unavailable",
                "llm_status": "offline_unavailable",
            },
            "configuration": {"use_mock": False, "runtime_mode": "offline"},
        },
        verified_risks=[_risk()],
        pending_risks=[],
        rejected_risks=[],
        errors=[],
        status=SimpleNamespace(value="completed"),
    )


def _compact(result: SimpleNamespace) -> dict:
    return MODULE.compact_result(
        result,
        case_id="ipo_2021_09898",
        stock_code="9898.HK",
        revision="abc",
        config_path=Path("configs/v045_competition_offline.yaml"),
        config_sha256="c" * 64,
        pdf_identity={"sha256": "d" * 64, "file_size_bytes": 5, "physical_pages": 10},
        elapsed_seconds=1.2,
    )


def test_mock_component_rejected_and_projection_is_compact() -> None:
    with pytest.raises(MODULE.OfflineBenchmarkError, match="component identity"):
        _compact(_analysis_result(parser_mode="mock"))
    projected = _compact(_analysis_result())
    serialized = json.dumps(projected)
    assert "must never persist" not in serialized
    assert '"text"' not in serialized
    assert projected["metadata"]["gold_used_for_prediction"] is False


def test_prediction_module_has_no_gold_or_expert_input_parameter() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "golden_path" not in source
    assert "expert_results" not in source
    assert "gold_used_for_prediction" in source
    assert list(inspect.signature(MODULE.run).parameters) == ["args"]


def test_atomic_jsonl_and_resume_identity(tmp_path: Path) -> None:
    path = tmp_path / "results.jsonl"
    payload = _compact(_analysis_result())
    MODULE.atomic_write_jsonl(path, {"ipo_2021_09898": payload})
    assert not path.with_suffix(".jsonl.tmp").exists()
    loaded = MODULE.load_existing_results(path)
    row = {
        "case_id": "ipo_2021_09898",
        "stock_code_wind": "9898.HK",
        "sha256": "d" * 64,
    }
    assert MODULE.resume_matches(loaded["ipo_2021_09898"], row=row, revision="abc", config_sha256="c" * 64)
    assert not MODULE.resume_matches(loaded["ipo_2021_09898"], row=row, revision="changed", config_sha256="c" * 64)


def test_case_and_year_staging_cleanup(tmp_path: Path) -> None:
    temp = tmp_path / "stage"
    temp.mkdir()
    year = temp / "current_year.zip"
    pdf = temp / "current.pdf"
    year.write_bytes(b"year")
    pdf.write_bytes(b"pdf")
    MODULE._cleanup_file(pdf)
    MODULE._cleanup_file(year)
    assert not pdf.exists()
    assert not year.exists()
    assert list(temp.iterdir()) == []


def test_disk_floor_guard(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    usage = shutil._ntuple_diskusage(total=10, used=9, free=1)
    monkeypatch.setattr(MODULE.shutil, "disk_usage", lambda _: usage)
    with pytest.raises(MODULE.OfflineBenchmarkError, match="safety floor"):
        MODULE.enforce_disk_floor(tmp_path, floor_bytes=2)
