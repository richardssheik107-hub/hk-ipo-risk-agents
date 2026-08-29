from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import gzip
import json
from pathlib import Path

import fitz

from ipo_risk.parsers.pymupdf_parser import PyMuPDFRoleBRecallParser
from ipo_risk.schemas import DocumentParseRequest


def _pdf(path: Path, text: str) -> Path:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    document.save(path)
    document.close()
    return path


def _request(path: Path, document_id: str = "doc") -> DocumentParseRequest:
    return DocumentParseRequest(document_id=document_id, prospectus_path=str(path))


def _parse(path: Path, cache: Path, **kwargs):
    parser = PyMuPDFRoleBRecallParser(cache_root=cache, **kwargs)
    chunks = parser.parse(_request(path))
    return chunks, parser.last_cache_metrics


def test_cold_and_warm_cache_are_semantically_identical(tmp_path: Path) -> None:
    pdf = _pdf(tmp_path / "sample.pdf", "Revenue 100 Customer concentration 45%")
    cache = tmp_path / "cache"

    cold, cold_metrics = _parse(pdf, cache)
    warm, warm_metrics = _parse(pdf, cache)

    assert cold == warm
    assert cold_metrics["raw_page_cache_misses"] == 1
    assert cold_metrics["table_cache_misses"] == 1
    assert cold_metrics["parser_cache_misses"] == 1
    assert warm_metrics["raw_page_cache_hits"] == 1
    assert warm_metrics["table_cache_hits"] == 1
    assert warm_metrics["parser_cache_hits"] == 1


def test_document_identity_is_rehydrated_not_cached(tmp_path: Path) -> None:
    pdf = _pdf(tmp_path / "sample.pdf", "Cash and operating activities")
    cache = tmp_path / "cache"

    first = PyMuPDFRoleBRecallParser(cache_root=cache).parse(_request(pdf, "first"))
    second = PyMuPDFRoleBRecallParser(cache_root=cache).parse(_request(pdf, "second"))

    assert first[0].document_id == "first"
    assert second[0].document_id == "second"
    assert second[0].chunk_id == "second:page:1"
    assert first[0].text == second[0].text


def test_parser_change_invalidates_only_parser_stage(tmp_path: Path) -> None:
    pdf = _pdf(tmp_path / "sample.pdf", "Supplier concentration 60%")
    cache = tmp_path / "cache"
    _parse(pdf, cache)

    _, metrics = _parse(
        pdf,
        cache,
        fingerprint_overrides={"parser_chunks": "a" * 64},
    )

    assert metrics["raw_page_cache_hits"] == 1
    assert metrics["table_cache_hits"] == 1
    assert metrics["parser_cache_misses"] == 1


def test_pdf_byte_change_misses_every_stage(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    first = _pdf(tmp_path / "first.pdf", "First document")
    second = _pdf(tmp_path / "second.pdf", "Second document")
    _parse(first, cache)

    _, metrics = _parse(second, cache)

    assert metrics["raw_page_cache_misses"] == 1
    assert metrics["table_cache_misses"] == 1
    assert metrics["parser_cache_misses"] == 1


def test_corrupt_cache_is_rebuilt_without_accepting_payload(tmp_path: Path) -> None:
    pdf = _pdf(tmp_path / "sample.pdf", "Material litigation")
    cache = tmp_path / "cache"
    expected, _ = _parse(pdf, cache)
    raw_cache = next((cache / "raw").rglob("*.json.gz"))
    raw_cache.write_bytes(b"not-a-gzip-file")

    observed, metrics = _parse(pdf, cache)

    assert observed == expected
    assert metrics["raw_page_cache_misses"] == 1


def test_wrong_cache_schema_is_rebuilt(tmp_path: Path) -> None:
    pdf = _pdf(tmp_path / "sample.pdf", "Redemption rights")
    cache = tmp_path / "cache"
    expected, _ = _parse(pdf, cache)
    raw_cache = next((cache / "raw").rglob("*.json.gz"))
    with gzip.open(raw_cache, "rt", encoding="utf-8") as handle:
        envelope = json.load(handle)
    envelope["cache_format_version"] = "wrong"
    with gzip.open(raw_cache, "wt", encoding="utf-8") as handle:
        json.dump(envelope, handle)

    observed, metrics = _parse(pdf, cache)

    assert observed == expected
    assert metrics["raw_page_cache_misses"] == 1


def test_concurrent_cache_access_is_atomic(tmp_path: Path) -> None:
    pdf = _pdf(tmp_path / "sample.pdf", "Five largest customers 70%")
    cache = tmp_path / "cache"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: _parse(pdf, cache), range(2)))

    assert results[0][0] == results[1][0]
    assert not list(cache.rglob("*.tmp"))
    assert not list(cache.rglob("*.lock"))
    assert len(list((cache / "raw").rglob("*.json.gz"))) == 1


def test_cache_payload_contains_no_local_path_or_governance_labels(tmp_path: Path) -> None:
    pdf = _pdf(tmp_path / "sample.pdf", "Ordinary development disclosure")
    cache = tmp_path / "cache"
    _parse(pdf, cache)

    for path in cache.rglob("*.json.gz"):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            persisted = handle.read()
        assert str(tmp_path) not in persisted
        lowered = persisted.casefold()
        assert "prospectus_path" not in lowered
        assert "gold_label" not in lowered
        assert "validation_outcome" not in lowered
        assert "blind_outcome" not in lowered
