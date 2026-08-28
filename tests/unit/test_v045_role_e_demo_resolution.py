"""The demo runner must prove a prospectus is the frozen one before analysing it.

The licensed PDFs live outside the repository, so the case list carries only a
``case_id``.  Everything identifying the file -- name, SHA-256, size, page count
-- comes from the frozen catalog, and a mismatch has to fail closed rather than
quietly analyse whatever was found at that path.
"""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "run_v04_role_e_demo", REPO_ROOT / "scripts" / "run_v04_role_e_demo.py"
)
demo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(demo)


def _pdf(pages: int = 2) -> bytes:
    import pymupdf

    document = pymupdf.open()
    for _ in range(pages):
        document.new_page()
    content = document.tobytes()
    document.close()
    return content


def _catalog_row(content: bytes, pages: int = 2, **overrides) -> dict[str, str]:
    row = {
        "source_filename": "02460_15-10-2024_x.pdf",
        "relative_path": "2024/02460_15-10-2024_x.pdf",
        "sha256": hashlib.sha256(content).hexdigest(),
        "file_size_bytes": str(len(content)),
        "pdf_page_count": str(pages),
        "dataset_split": "validation",
    }
    row.update(overrides)
    return row


@pytest.fixture
def archive(tmp_path):
    content = _pdf()
    path = tmp_path / "2024" / "02460_15-10-2024_x.pdf"
    path.parent.mkdir(parents=True)
    path.write_bytes(content)
    return tmp_path, content


def test_a_matching_prospectus_resolves_and_reports_its_verification(archive) -> None:
    root, content = archive
    path, verification = demo.resolve_prospectus(_catalog_row(content), root, None)
    assert path.exists()
    assert verification["sha256"] == hashlib.sha256(content).hexdigest()
    assert verification["sha256_matches_frozen_catalog"] is True
    assert verification["size_matches_frozen_catalog"] is True
    assert verification["page_count_matches_frozen_catalog"] is True
    assert verification["dataset_split"] == "validation"


def test_the_verification_record_never_carries_the_local_path(archive) -> None:
    """The archive location is licensed local state; artifacts must not embed it."""
    root, content = archive
    _, verification = demo.resolve_prospectus(_catalog_row(content), root, None)
    assert verification["path_recorded"] is False
    assert not any(str(root) in str(value) for value in verification.values())


def test_a_wrong_sha256_is_refused_rather_than_analysed(archive) -> None:
    root, content = archive
    row = _catalog_row(content, sha256="0" * 64)
    with pytest.raises(demo.ProspectusIntegrityError, match="frozen catalog record"):
        demo.resolve_prospectus(row, root, None)


def test_a_wrong_size_is_refused(archive) -> None:
    root, content = archive
    row = _catalog_row(content, file_size_bytes=str(len(content) + 1))
    with pytest.raises(demo.ProspectusIntegrityError):
        demo.resolve_prospectus(row, root, None)


def test_a_wrong_page_count_is_refused(archive) -> None:
    """Size and hash can only be defended together with the physical page count."""
    root, content = archive
    row = _catalog_row(content, pdf_page_count="999")
    with pytest.raises(demo.ProspectusIntegrityError, match="physical pages"):
        demo.resolve_prospectus(row, root, None)


def test_a_missing_prospectus_is_reported_not_substituted(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="not present locally"):
        demo.resolve_prospectus(_catalog_row(_pdf()), tmp_path, None)


def test_no_root_and_no_override_names_the_environment_variable(archive) -> None:
    _, content = archive
    with pytest.raises(FileNotFoundError, match=demo.PROSPECTUS_ROOT_ENV):
        demo.resolve_prospectus(_catalog_row(content), None, None)


def test_an_override_path_is_still_verified_against_the_frozen_catalog(archive) -> None:
    root, content = archive
    override = str(root / "2024" / "02460_15-10-2024_x.pdf")
    _, verification = demo.resolve_prospectus(_catalog_row(content), None, override)
    assert verification["sha256_matches_frozen_catalog"] is True
    with pytest.raises(demo.ProspectusIntegrityError):
        demo.resolve_prospectus(_catalog_row(content, sha256="1" * 64), None, override)


def test_the_request_identity_is_deterministic_for_the_same_case_and_bytes() -> None:
    from datetime import date

    first = demo.deterministic_request_id("2460.HK", date(2024, 10, 23), "abc")
    second = demo.deterministic_request_id("2460.HK", date(2024, 10, 23), "abc")
    other = demo.deterministic_request_id("2460.HK", date(2024, 10, 23), "abd")
    assert first == second != other


def test_the_declared_cases_all_exist_in_the_frozen_catalogs() -> None:
    """A case list naming an unknown case would fail only at run time otherwise."""
    import json

    manifest = json.loads((REPO_ROOT / "configs" / "v045_demo_cases.json").read_text(encoding="utf-8"))
    catalog = demo._read_catalog(REPO_ROOT / demo.DEFAULT_CATALOG, "case_id")
    bridge = demo._read_catalog(REPO_ROOT / demo.DEFAULT_BRIDGE, "case_id")
    assert len(manifest["cases"]) >= 3
    for case in manifest["cases"]:
        assert case["case_id"] in catalog, case
        assert case["case_id"] in bridge, case


def test_the_case_list_carries_no_local_path() -> None:
    text = (REPO_ROOT / "configs" / "v045_demo_cases.json").read_text(encoding="utf-8")
    assert "data/local" not in text
    assert ".pdf" not in text


# --- matrix identity -------------------------------------------------------
#
# The provenance and determinism audits refuse the matrix unless the summary
# says which code, which case list and which config produced it.  Nothing was
# emitting those fields, so both audits failed on a missing identity rather
# than on anything the run actually got wrong.


def test_the_case_manifest_and_config_are_identified_by_their_own_bytes(tmp_path) -> None:
    target = tmp_path / "cases.json"
    target.write_bytes(b"{}\n")
    assert demo._file_sha256(target) == hashlib.sha256(b"{}\n").hexdigest()


def test_an_unreadable_input_reports_no_hash_rather_than_a_placeholder(tmp_path) -> None:
    """A hash we could not take must leave the audit blocked, not satisfied."""
    assert demo._file_sha256(tmp_path / "absent.json") is None


def test_the_frozen_case_manifest_and_config_both_hash(tmp_path) -> None:
    manifest_sha = demo._file_sha256(REPO_ROOT / "configs" / "v045_demo_cases.json")
    config_sha = demo._file_sha256(REPO_ROOT / "configs" / "v045_competition_ai.yaml")
    for value in (manifest_sha, config_sha):
        assert value is not None and len(value) == 64


def test_the_code_base_sha_is_the_commit_the_run_came_from() -> None:
    sha, dirty = demo.resolve_code_base_sha(REPO_ROOT)
    assert sha is not None and len(sha) == 40
    assert int(sha, 16) >= 0  # a real hex commit id, not a label
    assert isinstance(dirty, bool)


def test_outside_a_checkout_the_code_identity_is_absent_not_guessed(tmp_path) -> None:
    """Fail closed: no git answer means no identity, so readiness stays blocked."""
    sha, dirty = demo.resolve_code_base_sha(tmp_path)
    assert sha is None
    assert dirty is None
