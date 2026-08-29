"""A replay must look like a recording, and a bundle must be provably the run's.

The demo bundle exists so a demonstration cannot fail on a missing PDF, an
expired credential or a hostile network.  That convenience is exactly what makes
it dangerous: a replay that does not announce itself is a live run as far as the
audience is concerned, and a bundle nobody can verify is just a folder of
plausible files.

So these tests hold two lines. Every replayed payload carries the identity of the
run it is a recording of, and every bundled file carries the SHA-256 it was
copied with -- with a verifier that fails on a tampered or missing file rather
than passing quietly.

The third line is the same one the rest of the lane keeps: what the run did not
produce is not produced here. A case with no analysis result is refused instead
of shown as a run that found nothing, an Evidence item the screenshot export
refused has no image rather than another item's page, and the generated
walkthrough says which channels were unavailable instead of skipping them.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import runpy
import sys

import pytest

from ipo_risk.runtime.demo_replay import (
    DEMO_BUNDLE_SCHEMA_VERSION,
    MANIFEST_NAME,
    OPTIONAL_CASE_FILES,
    STATUS_BUNDLED,
    STATUS_UNAVAILABLE_SOURCE,
    available_recorded_cases,
    build_demo_bundle,
    load_recorded_case,
    render_demo_script,
    replay_screenshots,
    screenshot_index,
    verify_demo_bundle,
)

APP_DIR = Path(__file__).resolve().parents[2] / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from evidence_viewer import _replay_caption  # noqa: E402

CASE_ID = "ipo_2024_02410"
EVIDENCE_ID = "67ef7838-6af2-5ebd-8a5c-7a46c39bb804"
REFUSED_EVIDENCE_ID = "1a2b3c4d-6af2-5ebd-8a5c-7a46c39bb804"


def _result(**overrides) -> dict:
    result = {
        "analysis_id": "e3c2e509-9df6-4d0a-88e2-a7655289a5d4",
        "company_name": "同源康医药",
        "stock_code": "2410.HK",
        "status": "completed",
        "workflow_version": "enhanced_v2",
        "verified_risks": [
            {
                "risk_code": "cash_runway",
                "level": "critical",
                "calculation": {"skill_name": "cash_runway"},
                "evidence": [{"evidence_id": EVIDENCE_ID, "page": 563}],
            }
        ],
        "pending_risks": [{"risk_code": "material_litigation_compliance", "level": "medium"}],
        "rejected_risks": [],
        "metadata": {
            "final_supervision": {
                "channel_states": [
                    {"channel": "document", "status": "available"},
                    {"channel": "market", "status": "unavailable_error"},
                    {"channel": "model", "status": "disabled"},
                ]
            }
        },
    }
    result.update(overrides)
    return result


def _manifest() -> dict:
    return {
        "status": "rendered",
        "cited_evidence_count": 2,
        "screenshot_count": 1,
        "precise_localisation_count": 1,
        "items": [
            {
                "evidence_id": EVIDENCE_ID,
                "page": 563,
                "status": "rendered",
                "highlight_drawn": True,
                "localisation": {
                    "granularity": "snippet_line_match",
                    "precise_snippet_localisation": True,
                },
                "screenshot": {"filename": "page0563_evidence.png", "sha256": "ab" * 32},
            },
            {
                "evidence_id": REFUSED_EVIDENCE_ID,
                "page": 99,
                "status": "page_out_of_range",
                "highlight_drawn": False,
                "localisation": {"granularity": "unavailable"},
                "screenshot": None,
            },
        ],
    }


def _matrix() -> dict:
    return {
        "config": "configs/v045_competition_ai.yaml",
        "demo_version": "v045_role_e_demo_v2",
        "code_base_sha": "cd" * 20,
        "code_base_dirty": False,
        "cases_manifest_sha256": "ef" * 32,
        "config_sha256": "12" * 32,
    }


def _case_dir(root: Path, *, with_optional: bool = True, with_screenshot: bool = True) -> Path:
    case_dir = root / CASE_ID
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "analysis_result.json").write_text(json.dumps(_result()), encoding="utf-8")
    (root / "summary.json").write_text(json.dumps(_matrix()), encoding="utf-8")
    if with_optional:
        (case_dir / "prospectus_verification.json").write_text(
            json.dumps({"sha256": "9a" * 32, "pdf_page_count": 706}), encoding="utf-8"
        )
        (case_dir / "screenshot_manifest.json").write_text(
            json.dumps(_manifest()), encoding="utf-8"
        )
        (case_dir / "gate_e1_evidence.json").write_text(
            json.dumps({"satisfied": True, "successful_llm_arbitration": True}), encoding="utf-8"
        )
        (case_dir / "human_review_export.json").write_text(
            json.dumps({"review_count": 0, "reviewed": False}), encoding="utf-8"
        )
        (case_dir / "case_report.md").write_text("# case report", encoding="utf-8")
    if with_screenshot:
        shots = case_dir / "screenshots"
        shots.mkdir(exist_ok=True)
        (shots / "page0563_evidence.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")
    return case_dir


def test_a_replay_carries_the_identity_of_the_run_it_records(tmp_path: Path) -> None:
    case = load_recorded_case(_case_dir(tmp_path), _matrix())
    provenance = case.provenance
    assert provenance["is_replay"] is True
    assert provenance["analysis_id"] == "e3c2e509-9df6-4d0a-88e2-a7655289a5d4"
    assert provenance["config"] == "configs/v045_competition_ai.yaml"
    assert provenance["code_base_sha"] == "cd" * 20
    assert provenance["prospectus_sha256"] == "9a" * 32
    assert provenance["path_recorded"] is False
    assert "回放" in provenance["statement"]


def test_a_case_with_no_recorded_run_is_refused_not_shown_empty(tmp_path: Path) -> None:
    empty = tmp_path / "ipo_2024_09999"
    empty.mkdir()
    with pytest.raises(FileNotFoundError, match="no recorded run to replay"):
        load_recorded_case(empty)


def test_missing_sidecars_are_listed_rather_than_reconstructed(tmp_path: Path) -> None:
    case = load_recorded_case(_case_dir(tmp_path, with_optional=False), _matrix())
    assert set(case.missing) == set(OPTIONAL_CASE_FILES)
    assert case.screenshots is None
    assert case.case_report_markdown is None
    assert case.provenance["prospectus_sha256"] is None


def test_only_rendered_screenshots_are_offered_to_the_viewer(tmp_path: Path) -> None:
    case = load_recorded_case(_case_dir(tmp_path), _matrix())
    index = screenshot_index(case.screenshots)
    assert set(index) == {EVIDENCE_ID}
    assert index[EVIDENCE_ID]["granularity"] == "snippet_line_match"

    shots = replay_screenshots(case)
    assert shots.image_path(EVIDENCE_ID) is not None
    # The item the export refused has no image, and no other page stands in.
    assert shots.record(REFUSED_EVIDENCE_ID) is None
    assert shots.image_path(REFUSED_EVIDENCE_ID) is None


def test_a_listed_screenshot_whose_file_is_gone_is_not_substituted(tmp_path: Path) -> None:
    case = load_recorded_case(_case_dir(tmp_path, with_screenshot=False), _matrix())
    shots = replay_screenshots(case)
    assert shots.record(EVIDENCE_ID) is not None
    assert shots.image_path(EVIDENCE_ID) is None


@pytest.mark.parametrize(
    "record, expected",
    [
        ({"highlight_drawn": True, "granularity": "snippet_line_match"}, "精确到行"),
        ({"highlight_drawn": True, "granularity": "keyword_match"}, "关键词"),
        ({"highlight_drawn": True, "granularity": "page_text_union"}, "页级文本范围"),
        ({"highlight_drawn": False, "granularity": "unavailable"}, "未绘制高亮框"),
    ],
)
def test_the_replay_caption_repeats_the_manifest_granularity(record: dict, expected: str) -> None:
    assert expected in _replay_caption(record)


def test_the_bundle_is_hash_bound_and_needs_nothing_external(tmp_path: Path) -> None:
    source = tmp_path / "matrix"
    _case_dir(source)
    (source / "batch_report.md").write_text("# batch", encoding="utf-8")
    bundle = tmp_path / "bundle"

    manifest = build_demo_bundle(source_dir=source, output_dir=bundle)
    assert manifest["schema_version"] == DEMO_BUNDLE_SCHEMA_VERSION
    assert manifest["status"] == STATUS_BUNDLED
    assert manifest["replayable_case_count"] == 1
    assert manifest["requires_network"] is False
    assert manifest["requires_provider_credentials"] is False
    assert manifest["requires_prospectus_pdf"] is False
    assert manifest["matrix_identity"]["code_base_sha"] == "cd" * 20

    for item in manifest["files"]:
        copied = bundle / item["logical_path"]
        assert hashlib.sha256(copied.read_bytes()).hexdigest() == item["sha256"]
    assert (bundle / CASE_ID / "screenshots" / "page0563_evidence.png").is_file()
    assert (bundle / "batch_report.md").is_file()


def test_a_bundled_case_records_what_the_run_never_produced(tmp_path: Path) -> None:
    source = tmp_path / "matrix"
    _case_dir(source, with_optional=False, with_screenshot=False)
    manifest = build_demo_bundle(source_dir=source, output_dir=tmp_path / "bundle")
    case = manifest["cases"][0]
    assert case["replayable"] is True
    assert set(case["missing_files"]) == set(OPTIONAL_CASE_FILES)
    assert case["screenshot_count"] == 0


def test_verification_fails_on_a_tampered_or_missing_file(tmp_path: Path) -> None:
    source = tmp_path / "matrix"
    _case_dir(source)
    bundle = tmp_path / "bundle"
    manifest = build_demo_bundle(source_dir=source, output_dir=bundle)
    (bundle / MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    assert verify_demo_bundle(bundle)["passed"] is True

    (bundle / CASE_ID / "analysis_result.json").write_text("{}", encoding="utf-8")
    tampered = verify_demo_bundle(bundle)
    assert tampered["passed"] is False
    assert f"{CASE_ID}/analysis_result.json" in tampered["mismatched"]

    (bundle / CASE_ID / "screenshots" / "page0563_evidence.png").unlink()
    incomplete = verify_demo_bundle(bundle)
    assert incomplete["passed"] is False
    assert f"{CASE_ID}/screenshots/page0563_evidence.png" in incomplete["missing"]


def test_verification_of_a_directory_without_a_manifest_proves_nothing(tmp_path: Path) -> None:
    report = verify_demo_bundle(tmp_path)
    assert report["passed"] is False
    assert "nothing can be verified" in report["reason"]


def test_a_missing_source_directory_produces_no_bundle_and_no_claim(tmp_path: Path) -> None:
    manifest = build_demo_bundle(source_dir=tmp_path / "absent", output_dir=tmp_path / "bundle")
    assert manifest["status"] == STATUS_UNAVAILABLE_SOURCE
    assert manifest["cases"] == [] and manifest["files"] == []
    assert not (tmp_path / "bundle").exists()


def test_the_walkthrough_says_the_parts_a_demo_would_rather_skip(tmp_path: Path) -> None:
    source = tmp_path / "matrix"
    _case_dir(source)
    bundle = tmp_path / "bundle"
    manifest = build_demo_bundle(source_dir=source, output_dir=bundle)
    cases = [load_recorded_case(path, _matrix()) for path in available_recorded_cases(bundle)]
    script = render_demo_script(manifest, cases)

    assert "已记录运行的回放" in script
    assert "不需要网络" in script
    assert "market`=unavailable_error" in script or "`market`=unavailable_error" in script
    assert "未复核不等于已认可" in script
    assert "不是分数、不是概率、不是上市后表现预测" in script
    assert "cash_runway" in script and "563" in script


def test_a_case_that_found_nothing_is_scripted_as_finding_nothing(tmp_path: Path) -> None:
    source = tmp_path / "matrix"
    case_dir = _case_dir(source)
    (case_dir / "analysis_result.json").write_text(
        json.dumps(_result(verified_risks=[])), encoding="utf-8"
    )
    bundle = tmp_path / "bundle"
    manifest = build_demo_bundle(source_dir=source, output_dir=bundle)
    cases = [load_recorded_case(path, _matrix()) for path in available_recorded_cases(bundle)]
    assert "系统不会为了好看补一个风险" in render_demo_script(manifest, cases)


def test_cli_builds_then_verifies_the_bundle_it_wrote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "matrix"
    _case_dir(source)
    bundle = tmp_path / "bundle"

    monkeypatch.setattr(
        "sys.argv",
        [
            "build_v045_demo_bundle.py",
            "--source-dir", str(source),
            "--output-dir", str(bundle),
        ],
    )
    with pytest.raises(SystemExit) as build_exit:
        runpy.run_path("scripts/build_v045_demo_bundle.py", run_name="__main__")
    assert build_exit.value.code == 0
    assert json.loads(capsys.readouterr().out)["replayable_case_count"] == 1
    assert (bundle / "DEMO_SCRIPT.md").read_text(encoding="utf-8").startswith("# 演示脚本")

    monkeypatch.setattr(
        "sys.argv",
        ["build_v045_demo_bundle.py", "--output-dir", str(bundle), "--verify"],
    )
    with pytest.raises(SystemExit) as verify_exit:
        runpy.run_path("scripts/build_v045_demo_bundle.py", run_name="__main__")
    assert verify_exit.value.code == 0
    assert json.loads(capsys.readouterr().out)["passed"] is True


def test_cli_verification_exits_nonzero_when_the_bundle_does_not_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "matrix"
    _case_dir(source)
    bundle = tmp_path / "bundle"
    manifest = build_demo_bundle(source_dir=source, output_dir=bundle)
    (bundle / MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    (bundle / CASE_ID / "case_report.md").write_text("tampered", encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv", ["build_v045_demo_bundle.py", "--output-dir", str(bundle), "--verify"]
    )
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_path("scripts/build_v045_demo_bundle.py", run_name="__main__")
    assert exit_info.value.code == 1
    assert json.loads(capsys.readouterr().out)["passed"] is False
