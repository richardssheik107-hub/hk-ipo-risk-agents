from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import gzip
from pathlib import Path

from ipo_risk.retrieval.keyword import KeywordDocumentRetriever
from ipo_risk.schemas import DocumentChunk


def _chunks(document_id: str = "runtime-doc") -> list[DocumentChunk]:
    return [
        DocumentChunk(
            document_id=document_id,
            chunk_id=f"{document_id}:page:1",
            page=1,
            section="financial",
            text="綜合現金流量表 會計師報告 人民幣千元",
        ),
        DocumentChunk(
            document_id=document_id,
            chunk_id=f"{document_id}:page:2",
            page=2,
            section="financial",
            text="經營活動所用現金淨額 (1,000)",
        ),
    ]


def _rows(values):
    return [item.model_dump(mode="json") for item in values]


def test_cold_warm_and_uncached_results_are_semantically_identical(tmp_path: Path) -> None:
    chunks = _chunks()
    expected = KeywordDocumentRetriever().retrieve(
        chunks, "operating_cash_flow", limit=5
    )
    cold_retriever = KeywordDocumentRetriever(cache_root=tmp_path / "cache")
    cold = cold_retriever.retrieve(chunks, "operating_cash_flow", limit=5)
    warm_retriever = KeywordDocumentRetriever(cache_root=tmp_path / "cache")
    warm = warm_retriever.retrieve(chunks, "operating_cash_flow", limit=5)

    assert _rows(cold) == _rows(expected) == _rows(warm)
    assert cold_retriever.last_cache_metrics["retrieval_cache_misses"] == 1
    assert warm_retriever.last_cache_metrics["retrieval_cache_hits"] == 1


def test_in_process_preprocessing_is_reused_for_multiple_queries(tmp_path: Path) -> None:
    retriever = KeywordDocumentRetriever(cache_root=tmp_path / "cache")
    chunks = _chunks()

    retriever.retrieve(chunks, "operating_cash_flow", limit=5)
    retriever.retrieve(chunks, "cash_and_cash_equivalents", limit=5)

    assert retriever.last_cache_metrics["retrieval_cache_misses"] == 1
    assert retriever.last_cache_metrics["retrieval_cache_hits"] == 1


def test_preprocessing_fingerprint_change_invalidates_cache(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    first = KeywordDocumentRetriever(
        cache_root=cache, preprocessing_fingerprint_override="a" * 64
    )
    second = KeywordDocumentRetriever(
        cache_root=cache, preprocessing_fingerprint_override="b" * 64
    )

    first.retrieve(_chunks(), "operating_cash_flow", limit=5)
    second.retrieve(_chunks(), "operating_cash_flow", limit=5)

    assert first.last_cache_metrics["retrieval_cache_misses"] == 1
    assert second.last_cache_metrics["retrieval_cache_misses"] == 1
    assert len(list((cache / "retrieval").rglob("*.json.gz"))) == 2


def test_document_identity_is_rehydrated_not_persisted(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    first = KeywordDocumentRetriever(cache_root=cache).retrieve(
        _chunks("first-runtime-id"), "operating_cash_flow", limit=5
    )
    second = KeywordDocumentRetriever(cache_root=cache).retrieve(
        _chunks("second-runtime-id"), "operating_cash_flow", limit=5
    )

    assert first[0].document_id == "first-runtime-id"
    assert second[0].document_id == "second-runtime-id"
    persisted = "".join(
        gzip.open(path, "rt", encoding="utf-8").read()
        for path in (cache / "retrieval").rglob("*.json.gz")
    )
    assert "first-runtime-id" not in persisted
    assert "second-runtime-id" not in persisted
    assert str(tmp_path) not in persisted
    assert "gold_label" not in persisted.casefold()
    assert "validation_outcome" not in persisted.casefold()
    assert "blind_outcome" not in persisted.casefold()


def test_concurrent_preprocessing_cache_access_is_atomic(tmp_path: Path) -> None:
    cache = tmp_path / "cache"

    def run(_):
        return _rows(
            KeywordDocumentRetriever(cache_root=cache).retrieve(
                _chunks(), "operating_cash_flow", limit=5
            )
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, range(2)))

    assert results[0] == results[1]
    assert len(list((cache / "retrieval").rglob("*.json.gz"))) == 1
    assert not list(cache.rglob("*.tmp"))
    assert not list(cache.rglob("*.lock"))
