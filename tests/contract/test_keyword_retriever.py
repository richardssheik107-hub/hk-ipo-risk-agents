from __future__ import annotations

import json
from pathlib import Path

import pytest

from ipo_risk.core.config import load_settings
from ipo_risk.core.container import DependencyContainer, default_registry
from ipo_risk.retrieval.keyword import KeywordDocumentRetriever, normalize_for_match
from ipo_risk.retrieval.mock import MockDocumentRetriever
from ipo_risk.schemas import DocumentChunk


def chunk(page: int, text: str, *, document_id: str = "case") -> DocumentChunk:
    return DocumentChunk(document_id=document_id, chunk_id=f"{document_id}:page:{page}", page=page, section="financial", text=text)


@pytest.mark.parametrize(
    ("query", "text", "intent"),
    [
        ("现金及现金等价物", "现金及现金等价物 人民币千元", "cash_and_cash_equivalents"),
        ("現金及現金等價物", "現金及現金等價物 人民幣千元", "cash_and_cash_equivalents"),
        ("CASH AND CASH EQUIVALENTS", "Cash and cash equivalents RMB'000", "cash_and_cash_equivalents"),
        ("现金余额", "现金及现金等价物余额 人民币千元", "cash_balance"),
        ("現金流量表期末現金及現金等價物", "期末之現金及現金等價物 港幣千元", "cash_flow_ending_cash"),
        (
            "cash and cash equivalents at end of period",
            "Cash and cash equivalents at the end of the reporting period USD'000",
            "cash_flow_ending_cash",
        ),
        ("经营活动现金流", "经营活动所用净现金流量 人民币千元", "operating_cash_flow"),
        ("經營活動現金流", "經營活動所用淨現金流量 人民幣千元", "operating_cash_flow"),
        ("operating cash flow", "Net cash used in operating activities", "operating_cash_flow"),
        ("经营活动现金流", "經營活動產生╱（所用）現金流量淨額", "operating_cash_flow"),
        ("经营活动现金流", "經營活動（所用）╱所得現金淨額", "operating_cash_flow"),
        ("经营活动现金流", "經營活動所得╱（所用）現金淨額", "operating_cash_flow"),
        ("经营活动现金流", "經營活動所產生的現金淨額", "operating_cash_flow"),
        ("经营活动现金流", "經營活動所得現金淨額", "operating_cash_flow"),
    ],
)
def test_keyword_retriever_supports_cash_and_operating_cash_flow_synonyms(query, text, intent):
    evidence = KeywordDocumentRetriever().retrieve([chunk(2, text)], query)
    assert len(evidence) == 1
    assert evidence[0].metadata["query_intent"] == intent
    assert 0 <= evidence[0].relevance_score <= 1
    assert evidence[0].text in text


def test_normalization_handles_nfkc_newlines_spaces_and_pdf_leaders():
    text = "現金……及\n\n現金　等價物    人民幣千元"
    evidence = KeywordDocumentRetriever().retrieve([chunk(8, text)], "現金及現金等價物")
    assert normalize_for_match("ＡＢＣ\n  def") == "abc def"
    assert evidence and evidence[0].text == text


def test_generic_keyword_uses_the_same_traceable_evidence_contract():
    source = chunk(6, "Liquidity risk is monitored by management.")
    evidence = KeywordDocumentRetriever().retrieve([source], "LIQUIDITY RISK")
    assert len(evidence) == 1
    assert evidence[0].metadata["query_intent"] == "generic_keyword"
    assert evidence[0].text in source.text


def test_complete_phrase_financial_context_beats_partial_or_legal_context():
    chunks = [
        chunk(665, "主要法律及監管規定概要 經營活動 股東權利"),
        chunk(563, "綜合現金流量表 現金流量表所述現金及現金等價物 人民幣千元 77,208"),
        chunk(683, "組織章程細則概要 經營活動 清算"),
    ]
    evidence = KeywordDocumentRetriever().retrieve(chunks, "现金及现金等价物", limit=5)
    assert [item.page for item in evidence] == [563]
    assert evidence[0].metadata["financial_context"]


def test_complete_phrase_scores_above_broad_operating_activity_term():
    financial = chunk(562, "附錄一 會計師報告 綜合現金流量表 經營活動所用淨現金流量 人民幣千元")
    legal = chunk(665, "主要法律及監管規定概要 經營活動 股東權利")
    retriever = KeywordDocumentRetriever()

    specific = retriever.retrieve([financial, legal], "经营活动现金流", limit=5)
    broad = retriever.retrieve([financial, legal], "經營活動", limit=5)

    assert [item.page for item in specific] == [562]
    assert [item.page for item in broad] == [562]
    assert specific[0].relevance_score > broad[0].relevance_score
    assert broad[0].metadata["broad_query"] is True


def test_operating_cash_flow_does_not_rank_generic_legal_operating_activity_pages():
    chunks = [
        chunk(665, "主要法律及監管規定概要 經營活動 股東權利"),
        chunk(562, "綜合現金流量表 經營活動所用淨現金流量 人民幣千元 (83,918)"),
        chunk(683, "組織章程細則概要 經營活動 清算"),
    ]
    evidence = KeywordDocumentRetriever().retrieve(chunks, "经营活动现金流", limit=5)
    assert [item.page for item in evidence] == [562]
    assert evidence[0].relevance_score > 0.4


def test_primary_audited_statement_context_beats_a_summary_copy():
    chunks = [
        chunk(30, "概 要 綜合現金流量表 經營活動所用淨現金流量 人民幣千元 (83,918)"),
        chunk(562, "附錄一 會計師報告 綜合現金流量表 經營活動所用淨現金流量 人民幣千元 (83,918)"),
    ]
    evidence = KeywordDocumentRetriever().retrieve(chunks, "经营活动现金流")
    assert [item.page for item in evidence] == [562, 30]
    assert evidence[0].metadata["primary_statement_context"]


def test_statement_title_neighborhood_promotes_later_statement_pages():
    chunks = [
        chunk(10, "概 要 現金及現金等價物 500 流動資金及資本資源"),
        chunk(100, "附錄一 會計師報告 綜合現金流量表 人民幣千元 2022年 2023年"),
        chunk(101, "經營活動所用現金淨額 (100) (120) 投資活動所用現金淨額 (20) (30)"),
        chunk(
            102,
            "現金及現金等價物增加淨額 10 20 年初現金及現金等價物 100 120 "
            "匯率變動對現金及現金等價物的影響 1 2 年末現金及現金等價物 111 142",
        ),
    ]
    retriever = KeywordDocumentRetriever()

    cash = retriever.retrieve(chunks, "现金流量表期末现金及现金等价物", limit=5)
    operating = retriever.retrieve(chunks, "经营活动现金流", limit=5)

    assert cash[0].page == 102
    assert cash[0].metadata["query_intent"] == "cash_flow_ending_cash"
    assert cash[0].metadata["statement_distance"] == 2
    assert set(cash[0].metadata["cash_flow_companions"]) == {
        "beginning_cash",
        "net_change",
        "exchange_effect",
        "ending_cash",
    }
    assert operating[0].page == 101
    assert operating[0].metadata["statement_distance"] == 1


def test_cash_flow_ending_intent_beats_balance_sheet_note_and_policy():
    chunks = [
        chunk(20, "財務資料概要 現金及現金等價物期末結餘 300"),
        chunk(200, "附錄一 會計師報告 合併現金流量表 港幣千元 2021年 2022年"),
        chunk(
            201,
            "現金及現金等價物淨增加 10 20 期初現金及現金等價物 100 200 "
            "期末現金及現金等價物 110 220 2021年 2022年 "
            "1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20",
        ),
        chunk(250, "主要會計政策 現金及現金等價物包括銀行結餘及手頭現金"),
        chunk(270, "信用風險 現金及銀行結餘 220 借款 30"),
    ]

    evidence = KeywordDocumentRetriever().retrieve(
        chunks, "期末现金及现金等价物", limit=5
    )

    assert evidence[0].page == 201
    assert evidence[0].metadata["statement_titles"]
    assert evidence[0].metadata["table_context"]
    assert next(item for item in evidence if item.page == 20).metadata["summary_context"]


def test_cash_flow_ending_intent_accepts_a_concrete_reporting_date_in_statement():
    chunks = [
        chunk(210, "附錄一 會計師報告 簡明現金流量表 港幣千元 2021年 2022年"),
        chunk(
            211,
            "現金及現金等價物增加淨額 10 20 於一月一日的現金及現金等價物 100 200 "
            "於六月三十日的現金及現金等價物 110 220",
        ),
    ]

    evidence = KeywordDocumentRetriever().retrieve(
        chunks, "现金流量表期末现金及现金等价物", limit=5
    )

    assert evidence[0].page == 211
    assert evidence[0].metadata["query_intent"] == "cash_flow_ending_cash"
    assert evidence[0].metadata["statement_distance"] == 1


def test_stable_ranking_limit_empty_query_no_match_and_no_fallback():
    chunks = [chunk(4, "现金及现金等价物"), chunk(2, "现金及现金等价物")]
    retriever = KeywordDocumentRetriever()
    first = retriever.retrieve(chunks, "现金及现金等价物")
    second = retriever.retrieve(chunks, "现金及现金等价物")
    assert [item.page for item in first] == [2, 4]
    assert [item.evidence_id for item in first] == [item.evidence_id for item in second]
    assert len(retriever.retrieve(chunks, "现金及现金等价物", limit=1)) == 1
    assert retriever.retrieve(chunks, "现金及现金等价物", limit=0) == []
    assert retriever.retrieve(chunks, "现金及现金等价物", limit=-1) == []
    assert retriever.retrieve(chunks, "") == []
    assert retriever.retrieve([chunk(1, "unrelated first page")], "现金及现金等价物") == []


def test_evidence_is_traceable_contiguous_and_aggregated_per_chunk():
    text = "前缀 " + "现金及现金等价物 " * 2 + "77,208 人民币千元 后缀"
    source = chunk(12, text, document_id="doc-a")
    evidence = KeywordDocumentRetriever().retrieve([source], "现金及现金等价物")
    assert len(evidence) == 1
    item = evidence[0]
    assert item.document_id == source.document_id and item.chunk_id == source.chunk_id and item.page == source.page
    assert item.text in source.text
    assert item.metadata["snippet_start"] <= item.metadata["snippet_end"] <= len(source.text)
    assert item.metadata["matched_keywords"]
    assert item.source_type == "prospectus"


def test_keyword_retriever_is_selected_by_real_pdf_configuration():
    settings = load_settings("configs/real_pdf.yaml")
    workflow = DependencyContainer(settings, default_registry()).create_workflow()
    assert isinstance(workflow.retriever, KeywordDocumentRetriever)


def test_mock_retriever_regression_behavior_is_unchanged():
    chunks = [chunk(1, "first"), chunk(2, "second loss")]
    assert MockDocumentRetriever().retrieve(chunks, "absent")[0].page == 1


def test_real_case_fixture_is_provisional_and_pending_second_review():
    fixture_dir = Path(__file__).parents[1] / "fixtures" / "real_case_001"
    metadata = json.loads((fixture_dir / "case_metadata.json").read_text(encoding="utf-8"))
    expected = json.loads((fixture_dir / "expected_evidence.json").read_text(encoding="utf-8"))
    assert metadata["document_path"] == "data/local/real_case_001/prospectus.pdf"
    assert metadata["annotation_status"] == "provisional_gold"
    assert metadata["review_status"] == "pending_second_human_review"
    assert metadata["second_reviewer_status"] == "pending"
    assert expected["cash_and_cash_equivalents"]["page"] == 563
    assert expected["operating_cash_flow"]["page"] == 562
