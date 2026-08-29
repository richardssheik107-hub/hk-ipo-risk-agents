"""A screenshot is a claim about where something is, so it must be earned.

These tests hold the export to the two rules that make it usable as competition
evidence: geometry may only come from the real document, and the granularity it
is labelled with may not be better than the geometry it actually found.  A page
union stays a page union; a located snippet line is reported as one; an item
with no geometry renders an unmarked page rather than a box somewhere plausible.

The remaining guards are about binding.  Every image carries its own SHA-256 and
the SHA-256 of the PDF it came from, and a PDF that does not match the hash the
run verified is refused outright -- a screenshot of the wrong document would
misattribute Evidence to a company that never filed it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import runpy

import pymupdf
import pytest

from ipo_risk.runtime.evidence_screenshots import (
    GRANULARITY_KEYWORD,
    GRANULARITY_PAGE_UNION,
    GRANULARITY_SNIPPET,
    GRANULARITY_UNAVAILABLE,
    MANIFEST_STATUS_NO_EVIDENCE,
    MANIFEST_STATUS_PDF_MISMATCH,
    MANIFEST_STATUS_RENDERED,
    MANIFEST_STATUS_UNAVAILABLE_PDF,
    METHOD_PARSER_BBOX,
    STATUS_PAGE_OUT_OF_RANGE,
    STATUS_RENDERED,
    build_evidence_screenshots,
    MAX_ANCHOR_CHARS,
    collect_cited_evidence,
    page_lines,
    snippet_anchors,
    summarise_screenshot_manifests,
)


PAGE_ONE_LINES = (
    "Consolidated statements of cash flows",
    "Cash and cash equivalents at end of the period 77,208",
    "Net cash used in operating activities (412,905)",
)
PAGE_TWO_LINES = ("Directors and senior management", "No material litigation is pending")

EVIDENCE_ID = "67ef7838-6af2-5ebd-8a5c-7a46c39bb804"
OTHER_EVIDENCE_ID = "1a2b3c4d-6af2-5ebd-8a5c-7a46c39bb804"
RISK_ID = "69066732-91e7-5238-850d-b162104dcab9"
OTHER_RISK_ID = "aa066732-91e7-5238-850d-b162104dcab9"


@pytest.fixture(scope="module")
def pdf_bytes() -> bytes:
    """A two-page PDF whose text we know, so localisation can be checked."""

    document = pymupdf.open()
    for lines in (PAGE_ONE_LINES, PAGE_TWO_LINES):
        page = document.new_page()
        for index, line in enumerate(lines):
            page.insert_text((72, 100 + index * 28), line, fontsize=11)
    payload = document.tobytes()
    document.close()
    return payload


def _evidence(**overrides) -> dict:
    evidence = {
        "evidence_id": EVIDENCE_ID,
        "page": 1,
        "section": "financial_information",
        "source_type": "prospectus",
        "bbox": [50.0, 80.0, 520.0, 200.0],
        "text": "\n".join(PAGE_ONE_LINES),
        "metadata": {
            "retriever": "keyword",
            "bbox_granularity": "page_text_union",
            "matched_keywords": ["cash and cash equivalents"],
        },
    }
    evidence.update(overrides)
    return evidence


def _result(evidence: list[dict] | None = None, **overrides) -> dict:
    result = {
        "verified_risks": [
            {
                "risk_id": RISK_ID,
                "risk_code": "cash_runway",
                "level": "critical",
                "verification_status": "verified",
                "agent_name": "financial",
                "evidence": evidence if evidence is not None else [_evidence()],
            }
        ],
        "pending_risks": [],
        "rejected_risks": [],
    }
    result.update(overrides)
    return result


def _build(pdf: bytes | None, result: dict | None = None, **kwargs) -> dict:
    return build_evidence_screenshots(
        case_id="ipo_2024_02410",
        stock_code="2410.HK",
        result=result or _result(),
        pdf_bytes=pdf,
        **kwargs,
    )


def test_cited_text_is_located_on_the_page_rather_than_boxed_at_page_level(
    pdf_bytes: bytes,
) -> None:
    manifest = _build(pdf_bytes)
    assert manifest["status"] == MANIFEST_STATUS_RENDERED
    item = manifest["items"][0]
    assert item["status"] == STATUS_RENDERED
    localisation = item["localisation"]
    assert localisation["granularity"] == GRANULARITY_SNIPPET
    assert localisation["precise_snippet_localisation"] is True
    assert item["highlight_drawn"] is True

    # The located region must be a genuine subset of the recorded page union,
    # otherwise "precise" would be a bigger claim than the page-level box.
    recorded = item["recorded_bbox"]
    located = localisation["bbox"]
    assert recorded[0] <= located[0] and recorded[1] <= located[1]
    assert located[2] <= recorded[2] and located[3] <= recorded[3]
    assert manifest["precise_localisation_count"] == 1


def test_anchors_record_what_was_searched_without_restating_the_document(
    pdf_bytes: bytes,
) -> None:
    anchors = _build(pdf_bytes)["items"][0]["localisation"]["anchors"]
    assert anchors
    for anchor in anchors:
        assert anchor["kind"] in {"snippet_line", "matched_keyword"}
        assert anchor["matched_page_line_count"] == 1
        assert len(anchor["sha256"]) == 64
        assert len(anchor["preview"]) <= 41  # bounded preview, ellipsis included


def test_a_snippet_absent_from_the_page_falls_back_to_the_parser_box_and_says_so(
    pdf_bytes: bytes,
) -> None:
    evidence = _evidence(
        text="A sentence that is nowhere in this document at all.",
        metadata={"retriever": "keyword", "bbox_granularity": "page_text_union"},
    )
    manifest = _build(pdf_bytes, _result([evidence]))
    localisation = manifest["items"][0]["localisation"]
    assert localisation["granularity"] == GRANULARITY_PAGE_UNION
    assert localisation["method"] == METHOD_PARSER_BBOX
    assert localisation["precise_snippet_localisation"] is False
    assert localisation["bbox"] == [50.0, 80.0, 520.0, 200.0]
    assert manifest["precise_localisation_count"] == 0
    assert manifest["page_level_fallback_count"] == 1


def test_matched_keywords_localise_when_no_snippet_line_is_searchable(
    pdf_bytes: bytes,
) -> None:
    evidence = _evidence(
        text="nowhere",
        metadata={
            "retriever": "keyword",
            "matched_keywords": ["Net cash used in operating activities"],
        },
        bbox=None,
    )
    localisation = _build(pdf_bytes, _result([evidence]))["items"][0]["localisation"]
    assert localisation["granularity"] == GRANULARITY_KEYWORD
    assert localisation["precise_snippet_localisation"] is True
    assert localisation["rect_count"] >= 1


def test_no_geometry_renders_an_unmarked_page_instead_of_a_guessed_box(
    pdf_bytes: bytes,
) -> None:
    evidence = _evidence(text="nowhere", bbox=None, metadata={"retriever": "keyword"})
    manifest = _build(pdf_bytes, _result([evidence]))
    item = manifest["items"][0]
    assert item["status"] == STATUS_RENDERED
    assert item["highlight_drawn"] is False
    assert item["localisation"]["granularity"] == GRANULARITY_UNAVAILABLE
    assert item["localisation"]["rects"] == []
    assert item["screenshot"]["sha256"]
    assert manifest["no_geometry_count"] == 1


def test_text_that_appears_twice_on_the_page_is_refused_rather_than_boxed_twice() -> None:
    """Two occurrences cannot say which one the Evidence came from."""

    document = pymupdf.open()
    page = document.new_page()
    repeated = "Net cash used in operating activities (412,905)"
    page.insert_text((72, 100), repeated, fontsize=11)
    page.insert_text((72, 400), repeated, fontsize=11)
    payload = document.tobytes()
    document.close()

    evidence = _evidence(
        text=f"leading context line\n{repeated}\ntrailing context line",
        bbox=None,
        metadata={"retriever": "keyword"},
    )
    manifest = _build(payload, _result([evidence]))
    item = manifest["items"][0]
    assert item["highlight_drawn"] is False
    assert item["localisation"]["granularity"] == GRANULARITY_UNAVAILABLE
    rejected = [anchor for anchor in item["localisation"]["anchors"] if not anchor["accepted"]]
    assert rejected and rejected[0]["matched_page_line_count"] == 2
    assert "ambiguous" in rejected[0]["rejection_reason"]
    assert manifest["ambiguous_anchor_count"] == 1


def test_a_wrapped_line_is_one_place_on_the_page_not_two(pdf_bytes: bytes) -> None:
    """A hit spanning two visual lines must not read as two occurrences."""

    import pymupdf

    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
        lines = page_lines(document.load_page(0))
    assert [line["text"] for line in lines] == list(PAGE_ONE_LINES)
    assert all(line["bbox"][2] > line["bbox"][0] for line in lines)


def test_a_page_beyond_the_document_is_reported_not_substituted(pdf_bytes: bytes) -> None:
    manifest = _build(pdf_bytes, _result([_evidence(page=99)]))
    item = manifest["items"][0]
    assert item["status"] == STATUS_PAGE_OUT_OF_RANGE
    assert item["screenshot"] is None
    assert "2 physical page" in item["reason"]
    assert manifest["screenshot_count"] == 0
    assert manifest["unrendered_count"] == 1


def test_images_are_written_and_bound_to_their_own_hash(
    pdf_bytes: bytes, tmp_path: Path
) -> None:
    manifest = _build(pdf_bytes, output_dir=tmp_path)
    screenshot = manifest["items"][0]["screenshot"]
    written = tmp_path / screenshot["filename"]
    content = written.read_bytes()
    assert hashlib.sha256(content).hexdigest() == screenshot["sha256"]
    assert len(content) == screenshot["byte_size"]
    assert content.startswith(b"\x89PNG")
    assert manifest["source_pdf"]["sha256"] == hashlib.sha256(pdf_bytes).hexdigest()
    assert manifest["source_pdf"]["path_recorded"] is False


def test_a_pdf_that_is_not_the_verified_one_is_refused(pdf_bytes: bytes, tmp_path: Path) -> None:
    manifest = _build(pdf_bytes, expected_pdf_sha256="00" * 32, output_dir=tmp_path)
    assert manifest["status"] == MANIFEST_STATUS_PDF_MISMATCH
    assert manifest["items"] == []
    assert manifest["screenshot_count"] == 0
    assert manifest["source_pdf"]["sha256_matches_expected"] is False
    assert not list(tmp_path.glob("*.png"))


def test_a_missing_prospectus_produces_no_image_and_no_claim() -> None:
    manifest = _build(None)
    assert manifest["status"] == MANIFEST_STATUS_UNAVAILABLE_PDF
    assert manifest["screenshot_count"] == 0
    assert manifest["cited_evidence_count"] == 1
    assert manifest["source_pdf"]["sha256"] is None


def test_a_run_that_cites_no_evidence_says_so(pdf_bytes: bytes) -> None:
    manifest = _build(pdf_bytes, _result([]))
    assert manifest["status"] == MANIFEST_STATUS_NO_EVIDENCE
    assert manifest["items"] == []


def test_one_evidence_item_cited_twice_is_one_screenshot_with_both_risks() -> None:
    result = _result()
    result["pending_risks"] = [
        {
            "risk_id": OTHER_RISK_ID,
            "risk_code": "going_concern",
            "verification_status": "pending",
            "agent_name": "financial",
            "evidence": [_evidence(), _evidence(evidence_id=OTHER_EVIDENCE_ID, page=2)],
        }
    ]
    captures = collect_cited_evidence(result)
    assert [capture.evidence_id for capture in captures] == [EVIDENCE_ID, OTHER_EVIDENCE_ID]
    assert captures[0].risk_ids == [RISK_ID, OTHER_RISK_ID]
    assert captures[0].risk_codes == ["cash_runway", "going_concern"]


def test_snippet_anchors_prefer_interior_lines_and_stay_searchable() -> None:
    snippet = "of the peri\nCash and cash equivalents at end of the period 77,208\nshort\nNet cash used in operating activities (412,905)\ntruncated tai"
    anchors = snippet_anchors(snippet)
    assert anchors[0].startswith("Cash and cash equivalents")
    assert all(len(anchor) <= MAX_ANCHOR_CHARS for anchor in anchors)
    assert "short" not in anchors
    assert "of the peri" in anchors  # truncated edges stay, at lower priority


def test_matrix_summary_reports_the_precise_share_without_rounding_it_up(
    pdf_bytes: bytes,
) -> None:
    precise = _build(pdf_bytes)
    fallback = _build(
        pdf_bytes,
        _result([_evidence(text="absent from the document", metadata={"retriever": "keyword"})]),
    )
    summary = summarise_screenshot_manifests([precise, fallback])
    assert summary["screenshot_count"] == 2
    assert summary["precise_localisation_count"] == 1
    assert summary["precise_localisation_rate"] == 0.5
    assert summary["cases_with_screenshots"] == 2


def test_summary_of_cases_without_screenshots_has_no_rate_to_report() -> None:
    summary = summarise_screenshot_manifests([_build(None)])
    assert summary["screenshot_count"] == 0
    assert summary["precise_localisation_rate"] is None


def test_cli_reports_an_absent_local_prospectus_instead_of_failing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    case_dir = tmp_path / "reports" / "ipo_2024_02410"
    case_dir.mkdir(parents=True)
    (case_dir / "analysis_result.json").write_text(
        json.dumps(_result()), encoding="utf-8"
    )
    (case_dir / "prospectus_verification.json").write_text(
        json.dumps({"sha256": "ab" * 32}), encoding="utf-8"
    )
    catalog = tmp_path / "catalog.csv"
    catalog.write_text(
        "case_id,relative_path,sha256\nipo_2024_02410,2024/absent.pdf,ab" + "ab" * 31 + "\n",
        encoding="utf-8",
    )
    bridge = tmp_path / "bridge.csv"
    bridge.write_text("case_id,stock_code_wind\nipo_2024_02410,2410.HK\n", encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "build_v045_evidence_screenshots.py",
            "--input-dir", str(tmp_path / "reports"),
            "--catalog", str(catalog),
            "--bridge", str(bridge),
            "--prospectus-root", str(tmp_path / "archive"),
        ],
    )
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_path("scripts/build_v045_evidence_screenshots.py", run_name="__main__")
    assert exit_info.value.code == 0

    manifest = json.loads((case_dir / "screenshot_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == MANIFEST_STATUS_UNAVAILABLE_PDF
    assert manifest["stock_code"] == "2410.HK"
    assert "not present in the local archive" in manifest["source_pdf"]["unavailable_reason"]
    summary = json.loads(capsys.readouterr().out)
    assert summary["cases_with_screenshots"] == 0
    assert summary["cited_evidence_count"] == 1


def test_cli_renders_and_binds_when_the_prospectus_is_present(
    pdf_bytes: bytes, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case_dir = tmp_path / "reports" / "ipo_2024_02410"
    case_dir.mkdir(parents=True)
    (case_dir / "analysis_result.json").write_text(json.dumps(_result()), encoding="utf-8")
    archive = tmp_path / "archive" / "2024"
    archive.mkdir(parents=True)
    (archive / "present.pdf").write_bytes(pdf_bytes)
    digest = hashlib.sha256(pdf_bytes).hexdigest()
    (case_dir / "prospectus_verification.json").write_text(
        json.dumps({"sha256": digest}), encoding="utf-8"
    )
    catalog = tmp_path / "catalog.csv"
    catalog.write_text(
        f"case_id,relative_path,sha256\nipo_2024_02410,2024/present.pdf,{digest}\n",
        encoding="utf-8",
    )
    bridge = tmp_path / "bridge.csv"
    bridge.write_text("case_id,stock_code_wind\nipo_2024_02410,2410.HK\n", encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "build_v045_evidence_screenshots.py",
            "--input-dir", str(tmp_path / "reports"),
            "--catalog", str(catalog),
            "--bridge", str(bridge),
            "--prospectus-root", str(tmp_path / "archive"),
        ],
    )
    with pytest.raises(SystemExit):
        runpy.run_path("scripts/build_v045_evidence_screenshots.py", run_name="__main__")

    manifest = json.loads((case_dir / "screenshot_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == MANIFEST_STATUS_RENDERED
    assert manifest["source_pdf"]["sha256_matches_expected"] is True
    screenshot = manifest["items"][0]["screenshot"]
    image = (case_dir / "screenshots" / screenshot["filename"]).read_bytes()
    assert hashlib.sha256(image).hexdigest() == screenshot["sha256"]
    summary = json.loads((tmp_path / "reports" / "screenshot_summary.json").read_text("utf-8"))
    assert summary["screenshot_count"] == 1
    assert summary["manifest_sha256"]["ipo_2024_02410"]
