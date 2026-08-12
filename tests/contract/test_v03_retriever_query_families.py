"""Contracts for deterministic v0.3 multi-domain Retriever query families."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from ipo_risk.retrieval.keyword import KeywordDocumentRetriever
from ipo_risk.retrieval.keyword import normalize_for_match
from ipo_risk.retrieval.query_families import QUERY_FAMILY_BY_NAME
from ipo_risk.schemas import DocumentChunk


BUSINESS_RECALL_FIXTURE = (
    Path(__file__).parents[1] / "fixtures" / "v03_retriever" / "business_recall_cases.json"
)
LEGAL_RECALL_FIXTURE = (
    Path(__file__).parents[1] / "fixtures" / "v03_retriever" / "legal_recall_cases.json"
)


def chunk(page: int, text: str, *, section: str, document_id: str = "synthetic-v03") -> DocumentChunk:
    return DocumentChunk(
        document_id=document_id,
        chunk_id=f"{document_id}:page:{page}",
        page=page,
        section=section,
        text=text,
    )


LANGUAGE_CASES = (
    ("revenue", "营业收入", "综合损益表 营业收入 100", "financial"),
    ("revenue", "營業收入", "綜合損益表 營業收入 100", "財務資料"),
    ("revenue", "revenue", "Statement of profit or loss: revenue 100", "financial"),
    ("continuous_loss", "持续亏损", "历史财务资料显示本集团持续亏损", "financial"),
    ("continuous_loss", "持續虧損", "歷史財務資料顯示本集團持續虧損", "財務資料"),
    ("continuous_loss", "history of losses", "Historical financial information shows a history of losses", "financial"),
    ("customer_concentration", "五大客户", "来自五大客户的收入占总收入80%", "customers"),
    ("customer_concentration", "五大客戶", "來自五大客戶的收入佔總收入80%", "客戶"),
    ("customer_concentration", "top five customers", "Revenue attributable to our top five customers was 80%", "customers"),
    ("supplier_concentration", "五大供应商", "向五大供应商采购占总采购额70%", "suppliers"),
    ("supplier_concentration", "五大供應商", "向五大供應商採購佔總採購額70%", "供應商"),
    ("supplier_concentration", "top five suppliers", "Purchases from our top five suppliers were 70%", "suppliers"),
    ("redemption_rights", "赎回权", "投资协议约定赎回权将于上市时终止", "history and reorganisation"),
    ("redemption_rights", "贖回權", "投資協議約定贖回權將於上市時終止", "歷史及重組"),
    ("redemption_rights", "redemption rights", "Redemption rights under the investment agreement terminate upon listing", "history"),
    ("material_litigation_compliance", "重大诉讼", "未决重大诉讼可能造成罚款及重大不利影响", "legal"),
    ("material_litigation_compliance", "重大訴訟", "未決重大訴訟可能造成罰款及重大不利影響", "legal"),
    ("material_litigation_compliance", "material litigation", "Pending material litigation may result in a fine and material adverse effect", "legal"),
    ("material_litigation_compliance", "社会保险", "公司因未足额缴纳社会保险及住房公积金而完成整改", "legal"),
    ("material_litigation_compliance", "社會保險", "公司因未足額繳納社會保險及住房公積金而完成整改", "legal"),
    ("material_litigation_compliance", "social insurance", "The company rectified unpaid social insurance and housing provident fund contributions", "legal"),
    ("commercialization_status", "尚未商业化", "核心产品处于临床阶段，尚未商业化且没有产品销售收入", "business"),
    ("commercialization_status", "尚未商業化", "核心產品處於臨床階段，尚未商業化且沒有產品銷售收入", "業務"),
    ("commercialization_status", "not yet commercialized", "Our core product is clinical stage and not yet commercialized", "business"),
    ("commercialization_status", "licensing agreement", "The core product remains clinical stage under a licensing agreement and generated milestone revenue", "business"),
    ("core_product_pipeline", "核心产品管线", "核心产品管线包括两个临床二期候选药物", "business"),
    ("core_product_pipeline", "核心產品管線", "核心產品管線包括兩個臨床二期候選藥物", "業務"),
    ("core_product_pipeline", "core product pipeline", "The core product pipeline includes two phase II drug candidates", "business"),
)


@pytest.mark.parametrize(("family", "alias", "text", "section"), LANGUAGE_CASES)
def test_each_query_family_supports_simplified_traditional_and_english(
    family: str,
    alias: str,
    text: str,
    section: str,
) -> None:
    evidence = KeywordDocumentRetriever().retrieve(
        [chunk(7, text, section=section)], family
    )

    assert len(evidence) == 1, (family, alias)
    assert evidence[0].metadata["query_intent"] == family
    assert evidence[0].metadata["query_family"] == family
    assert alias.casefold() in evidence[0].text.casefold()
    assert evidence[0].text in text


DECOY_CASES = (
    (
        "revenue", "收入",
        "综合损益表列示收入及分部资料", "financial",
        "行业概览仅说明市场收入定义", "industry overview",
    ),
    (
        "continuous_loss", "持续亏损",
        "历史财务资料显示年内亏损及持续亏损", "financial",
        "前瞻性陈述提示行业参与者可能持续亏损", "risk factors",
    ),
    (
        "customer_concentration", "五大客户",
        "来自五大客户的销售额占总收入75%", "customers",
        "释义：五大客户指若干一般客户", "definitions",
    ),
    (
        "supplier_concentration", "五大供应商",
        "向五大供应商采购占总采购额68%", "suppliers",
        "监管概览提及五大供应商的一般定义", "regulatory overview",
    ),
    (
        "redemption_rights", "赎回权",
        "投资协议项下赎回权将于上市时终止", "history and reorganisation",
        "公司条例及组织章程细则概要载列一般赎回权", "statutory",
    ),
    (
        "material_litigation_compliance", "重大诉讼",
        "未决重大诉讼涉及监管调查、罚款及整改", "legal",
        "一般监管规定称企业可能受到重大诉讼影响", "regulatory overview",
    ),
    (
        "commercialization_status", "尚未商业化",
        "核心产品仍处临床阶段，尚未商业化且没有产品销售收入", "business",
        "行业概览讨论一般药品尚未商业化的市场情况", "industry overview",
    ),
    (
        "core_product_pipeline", "核心产品管线",
        "核心产品管线列示临床二期候选药物及研发进度", "business",
        "释义仅定义核心产品管线及行业概览术语", "definitions",
    ),
)


@pytest.mark.parametrize(
    ("family", "query", "relevant_text", "relevant_section", "decoy_text", "decoy_section"),
    DECOY_CASES,
)
def test_domain_context_ranks_relevant_section_ahead_of_decoy(
    family: str,
    query: str,
    relevant_text: str,
    relevant_section: str,
    decoy_text: str,
    decoy_section: str,
) -> None:
    relevant = chunk(20, relevant_text, section=relevant_section)
    decoy = chunk(3, decoy_text, section=decoy_section)

    evidence = KeywordDocumentRetriever().retrieve([decoy, relevant], query, limit=5)

    assert [item.page for item in evidence] == [20, 3], family
    assert evidence[0].relevance_score > evidence[1].relevance_score
    assert evidence[0].metadata["domain_context"]
    assert evidence[0].metadata["preferred_section_context"]
    assert (
        evidence[1].metadata["domain_negative_context"]
        or evidence[1].metadata["discouraged_section_context"]
    )


@pytest.mark.parametrize(
    ("family", "query", "relevant_text", "decoy_text"),
    (
        (
            "revenue",
            "收入",
            "财务资料 综合损益表列示收入及分部资料",
            "行业概览仅说明市场收入定义",
        ),
        (
            "redemption_rights",
            "赎回权",
            "历史及重组 投资协议项下赎回权将于上市时终止",
            "法定及一般资料 公司条例及组织章程细则概要载列一般赎回权",
        ),
        (
            "core_product_pipeline",
            "核心产品管线",
            "业务 核心产品管线列示临床二期候选药物及研发进度",
            "释义 核心产品管线属于行业概览术语",
        ),
    ),
)
def test_unknown_parser_section_uses_visible_page_heading_signals(
    family: str,
    query: str,
    relevant_text: str,
    decoy_text: str,
) -> None:
    chunks = [
        chunk(3, decoy_text, section="unknown"),
        chunk(20, relevant_text, section="unknown"),
    ]

    evidence = KeywordDocumentRetriever().retrieve(chunks, query, limit=5)

    assert [item.page for item in evidence] == [20, 3], family
    assert evidence[0].relevance_score > evidence[1].relevance_score
    assert evidence[0].metadata["preferred_section_context"]
    assert evidence[1].metadata["discouraged_section_context"]


def test_short_ascii_fragments_do_not_create_pipeline_context_matches() -> None:
    source = chunk(
        12,
        "Core product pipeline terminology appears in an industry standard and mandatory disclosure.",
        section="unknown",
    )

    evidence = KeywordDocumentRetriever().retrieve([source], "core_product_pipeline")

    assert len(evidence) == 1
    assert "ind" not in evidence[0].metadata["domain_context"]
    assert "nda" not in evidence[0].metadata["domain_context"]


def test_explicit_drug_application_phrases_remain_positive_context() -> None:
    source = chunk(
        13,
        "Core product pipeline includes an IND application and a new drug application.",
        section="unknown",
    )

    evidence = KeywordDocumentRetriever().retrieve([source], "core_product_pipeline")

    assert {"ind application", "new drug application"}.issubset(
        set(evidence[0].metadata["domain_context"])
    )


def test_v03_family_ranking_ids_and_traceability_are_stable() -> None:
    chunks = [
        chunk(9, "来自五大客户的收入占总收入80%", section="customers", document_id="doc-v03"),
        chunk(4, "释义：五大客户为主要客户", section="definitions", document_id="doc-v03"),
    ]
    retriever = KeywordDocumentRetriever()

    first = retriever.retrieve(chunks, "customer_concentration", limit=5)
    second = retriever.retrieve(chunks, "customer_concentration", limit=5)

    assert [item.evidence_id for item in first] == [item.evidence_id for item in second]
    assert [item.page for item in first] == [9, 4]
    for item in first:
        source = next(value for value in chunks if value.chunk_id == item.chunk_id)
        assert item.document_id == source.document_id
        assert item.page == source.page
        assert item.text in source.text


def test_v03_family_no_match_has_no_fallback() -> None:
    source = chunk(1, "This paragraph is unrelated.", section="business")
    assert KeywordDocumentRetriever().retrieve([source], "core_product_pipeline") == []


def test_v03_query_family_catalog_and_public_signature_are_stable() -> None:
    assert set(QUERY_FAMILY_BY_NAME) == {
        "revenue",
        "continuous_loss",
        "customer_concentration",
        "supplier_concentration",
        "redemption_rights",
        "material_litigation_compliance",
        "commercialization_status",
        "core_product_pipeline",
    }
    signature = inspect.signature(KeywordDocumentRetriever.retrieve)
    assert list(signature.parameters) == ["self", "chunks", "query", "limit"]
    assert signature.parameters["limit"].default == 3


@pytest.mark.parametrize(
    "case",
    json.loads(BUSINESS_RECALL_FIXTURE.read_text(encoding="utf-8")),
    ids=lambda case: case["case_id"],
)
def test_business_fact_query_families_cover_multilingual_status_and_product_facts(
    case: dict[str, object],
) -> None:
    source = chunk(
        20,
        str(case["text"]),
        section=str(case["section"]),
        document_id=f"synthetic-{case['case_id']}",
    )

    evidence = KeywordDocumentRetriever().retrieve(
        [source], str(case["family"]), limit=5
    )

    assert len(evidence) == 1
    assert evidence[0].page == 20
    assert evidence[0].metadata["query_family"] == case["family"]
    assert set(case["expected_terms"]).issubset(
        set(evidence[0].metadata["matched_keywords"])
        | set(evidence[0].metadata["domain_context"])
    )
    assert evidence[0].document_id == source.document_id
    assert evidence[0].chunk_id == source.chunk_id
    assert evidence[0].text in source.text


@pytest.mark.parametrize(
    ("family", "primary_text", "decoy_text"),
    (
        (
            "commercialization_status",
            "業務 我們生產及銷售主要產品，產品所產生的收益佔總收益的大部分。",
            "行業概覽 一般製造商可能生產及銷售不同產品。",
        ),
        (
            "core_product_pipeline",
            "業務 我們的主要產品類別及產品組合如下，並列示產品所產生的收益。",
            "行業概覽 市場參與者通常擁有多種產品組合。",
        ),
    ),
)
def test_primary_business_facts_rank_ahead_of_generic_industry_decoys(
    family: str,
    primary_text: str,
    decoy_text: str,
) -> None:
    sources = [
        chunk(3, decoy_text, section="unknown", document_id="business-ranking"),
        chunk(20, primary_text, section="unknown", document_id="business-ranking"),
    ]

    evidence = KeywordDocumentRetriever().retrieve(sources, family, limit=5)

    assert evidence[0].page == 20
    assert evidence[0].metadata["preferred_section_context"]
    decoy = next((item for item in evidence if item.page == 3), None)
    if decoy is not None:
        assert evidence[0].relevance_score > decoy.relevance_score
        assert decoy.metadata["domain_negative_context"]


def test_business_recall_keeps_top_five_limit_and_stable_traceability() -> None:
    sources = [
        chunk(
            page,
            f"業務 我們生產及銷售第{page}類主要產品，並錄得產品所產生的收益。",
            section="unknown",
            document_id="business-limit",
        )
        for page in range(1, 8)
    ]
    retriever = KeywordDocumentRetriever()

    first = retriever.retrieve(sources, "commercialization_status", limit=5)
    second = retriever.retrieve(sources, "commercialization_status", limit=5)

    assert len(first) == 5
    assert [item.page for item in first] == [1, 2, 3, 4, 5]
    assert [item.evidence_id for item in first] == [item.evidence_id for item in second]
    assert all(item.document_id == "business-limit" for item in first)


@pytest.mark.parametrize(
    "case",
    json.loads(LEGAL_RECALL_FIXTURE.read_text(encoding="utf-8")),
    ids=lambda case: case["case_id"],
)
def test_legal_query_families_cover_multilingual_lifecycle_and_status_facts(
    case: dict[str, object],
) -> None:
    source = chunk(
        20,
        str(case["text"]),
        section=str(case["section"]),
        document_id=f"synthetic-{case['case_id']}",
    )

    evidence = KeywordDocumentRetriever().retrieve(
        [source], str(case["family"]), limit=5
    )

    assert len(evidence) == 1
    item = evidence[0]
    assert item.page == 20
    assert item.metadata["query_family"] == case["family"]
    assert {
        normalize_for_match(value) for value in case["expected_aliases"]
    }.issubset(set(item.metadata["matched_keywords"]))
    assert set(case["expected_context"]).issubset(
        set(item.metadata["domain_context"])
    )
    if case["negative_evidence"]:
        assert item.metadata["domain_negative_context"]
    assert item.document_id == source.document_id
    assert item.chunk_id == source.chunk_id
    assert item.text in source.text


@pytest.mark.parametrize(
    ("family", "primary_text", "decoy_text"),
    (
        (
            "redemption_rights",
            "歷史及重組 股東協議授予投資者清算優先權，上市申請被拒絕時將恢復。",
            "公司章程載列一般股東權利，包括普通股份的法定贖回及贖回權。",
        ),
        (
            "material_litigation_compliance",
            "業務 本集團有兩起重大未決訴訟並擔任被告，索賠金額尚未解決。",
            "風險因素 公司未來可能在日常業務中面臨一般訴訟風險。",
        ),
    ),
)
def test_direct_legal_facts_rank_ahead_of_generic_boilerplate(
    family: str,
    primary_text: str,
    decoy_text: str,
) -> None:
    sources = [
        chunk(3, decoy_text, section="unknown", document_id="legal-ranking"),
        chunk(20, primary_text, section="unknown", document_id="legal-ranking"),
    ]

    evidence = KeywordDocumentRetriever().retrieve(sources, family, limit=5)

    assert [item.page for item in evidence] == [20, 3]
    assert evidence[0].relevance_score > evidence[1].relevance_score
    assert evidence[0].metadata["domain_context"]
    assert evidence[1].metadata["domain_negative_context"]


def test_legal_recall_keeps_top_five_limit_stable_ids_and_traceability() -> None:
    sources = [
        chunk(
            page,
            f"歷史及重組 投資協議項下第{page}項清算優先權已終止。",
            section="unknown",
            document_id="legal-limit",
        )
        for page in range(1, 8)
    ]
    retriever = KeywordDocumentRetriever()

    first = retriever.retrieve(sources, "redemption_rights", limit=5)
    second = retriever.retrieve(sources, "redemption_rights", limit=5)

    assert len(first) == 5
    assert [item.page for item in first] == [1, 2, 3, 4, 5]
    assert [item.evidence_id for item in first] == [
        item.evidence_id for item in second
    ]
    assert all(item.document_id == "legal-limit" for item in first)
    assert all(item.chunk_id == f"legal-limit:page:{item.page}" for item in first)
