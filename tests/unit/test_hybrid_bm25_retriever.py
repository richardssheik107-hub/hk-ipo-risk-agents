from ipo_risk.retrieval.hybrid_bm25 import HybridBM25DocumentRetriever
from ipo_risk.schemas import DocumentChunk


def _chunk(page: int, text: str, *, document_id: str = "doc") -> DocumentChunk:
    return DocumentChunk(
        document_id=document_id,
        chunk_id=f"{document_id}-p{page}",
        page=page,
        section="unknown",
        text=text,
    )


def test_bm25_recovers_semantic_page_absent_from_exact_query_lane() -> None:
    chunks = [
        _chunk(1, "The issuer sells ordinary consumer goods."),
        _chunk(
            2,
            "During the track record period, income attributable to the five "
            "largest clients represented 42.1% of total turnover.",
        ),
    ]

    evidence = HybridBM25DocumentRetriever().retrieve(
        chunks, "customer_concentration", limit=2
    )

    assert [item.page for item in evidence] == [2]
    assert evidence[0].metadata["candidate_origin"] == "bm25_only"
    assert evidence[0].metadata["persistent_index"] is False


def test_revenue_denominator_outranks_receivable_balance_context() -> None:
    chunks = [
        _chunk(
            1,
            "Trade receivables due from our five largest customers represented "
            "80% of the receivable balance.",
        ),
        _chunk(
            2,
            "Revenue attributable to our top five customers represented 42.1% "
            "of total revenue during FY2024.",
        ),
    ]

    evidence = HybridBM25DocumentRetriever().retrieve(
        chunks, "customer_concentration", limit=2
    )

    assert [item.page for item in evidence] == [2, 1]
    assert "total revenue" in evidence[0].text


def test_unsupported_query_and_multi_document_input_degrade_to_keyword() -> None:
    retriever = HybridBM25DocumentRetriever()
    generic = [_chunk(1, "exact uncommon phrase")]
    assert retriever.retrieve(generic, "uncommon phrase", limit=1)[0].metadata[
        "retriever"
    ] == "keyword"

    multiple = [
        _chunk(1, "top five customers represented 20% of revenue", document_id="a"),
        _chunk(1, "top five customers represented 30% of revenue", document_id="b"),
    ]
    assert all(
        item.metadata["retriever"] == "keyword"
        for item in retriever.retrieve(multiple, "customer_concentration", limit=2)
    )


def test_regressive_risk_families_keep_the_mature_keyword_route() -> None:
    chunks = [
        _chunk(1, "cash and cash equivalents at end of year HK$100"),
        _chunk(2, "operating cash flow and liquidity runway discussion"),
    ]

    evidence = HybridBM25DocumentRetriever().retrieve(
        chunks, "cash and cash equivalents", limit=2
    )

    assert evidence
    assert all(item.metadata["retriever"] == "keyword" for item in evidence)

    litigation = HybridBM25DocumentRetriever().retrieve(
        [_chunk(1, "material litigation and regulatory non-compliance")],
        "material_litigation_compliance",
        limit=2,
    )
    assert litigation
    assert all(item.metadata["retriever"] == "keyword" for item in litigation)


def test_empty_or_non_positive_limit_returns_no_evidence() -> None:
    retriever = HybridBM25DocumentRetriever()
    chunks = [_chunk(1, "revenue")]
    assert retriever.retrieve(chunks, "", limit=3) == []
    assert retriever.retrieve(chunks, "revenue", limit=0) == []


def test_index_is_reused_only_for_the_same_active_document() -> None:
    retriever = HybridBM25DocumentRetriever()
    first = [_chunk(1, "revenue and turnover increased")]
    retriever.retrieve(first, "revenue", limit=1)
    first_index = retriever._cached_index

    retriever.retrieve(first, "continuous_loss", limit=1)
    assert retriever._cached_index is first_index

    second = [
        _chunk(
            1,
            "top five customers represented 40% of revenue",
            document_id="b",
        )
    ]
    retriever.retrieve(second, "customer_concentration", limit=1)
    assert retriever._cached_index is not first_index
    assert retriever._cached_first_chunk is second[0]
