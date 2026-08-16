"""Unit contracts for the V2.3 two-route research experiment."""

from __future__ import annotations

from pathlib import Path
import tempfile

from ipo_risk.retrieval.precommercial_v23 import (
    EvidenceIntent, PrecommercialCandidateRetrieverV23, V23_VARIANTS,
    bounded_candidate_union, classify_evidence_intent,
)
from ipo_risk.schemas import DocumentChunk, Evidence
from scripts.run_precommercial_candidate_v23 import FROZEN_VARIANT, case_split


def _chunk(page: int, text: str, *, tables=None) -> DocumentChunk:
    metadata = {"tables": tables} if tables else {}
    return DocumentChunk(document_id="d", chunk_id=f"p{page}", page=page, text=text, metadata=metadata)


def _evidence(page: int) -> Evidence:
    return Evidence(document_id="d", chunk_id=f"p{page}", page=page, text=f"page {page}")


class _Baseline:
    def retrieve_for_risk(self, chunks, risk_code, *, limit=50):
        return [_evidence(chunk.page) for chunk in chunks[:limit]]


class _Base:
    def retrieve(self, chunks, query, limit=50):
        if query == "commercialization_status":
            pages = [chunk.page for chunk in chunks if "尚未商業化" in chunk.text]
        elif query == "core_product_pipeline":
            pages = [chunk.page for chunk in chunks if "核心產品" in chunk.text]
        else:
            pages = [chunk.page for chunk in chunks if "收益" in chunk.text]
        return [_evidence(page) for page in pages[:limit]]


def test_intent_classification_uses_fact_meaning() -> None:
    assert classify_evidence_intent("產品尚未獲准商業銷售，亦未產生產品收入", "business_section", True) is EvidenceIntent.NOT_COMMERCIALISED
    assert classify_evidence_intent("核心產品正在二期臨床研究", "business_section", True) is EvidenceIntent.PRODUCT_LIFECYCLE
    assert classify_evidence_intent("產品銷售收入為人民幣100百萬元", "accountants_report", False) is EvidenceIntent.PRODUCT_REVENUE_EXISTS
    assert classify_evidence_intent("我們提供管理服務並收取服務費", "business_section", False) is EvidenceIntent.SERVICE_REVENUE_EXISTS
    assert classify_evidence_intent("收益 100 200 300", "accountants_report", False) is EvidenceIntent.REVENUE_NATURE
    assert classify_evidence_intent("我 們 提 供 裝 修 服 務", "business_section", False) is EvidenceIntent.SERVICE_REVENUE_EXISTS
    assert classify_evidence_intent("註冊申請目前正在審核中", "business_section", False) is EvidenceIntent.PRODUCT_LIFECYCLE


def test_route_a_finds_lifecycle_and_noncommercial_pages() -> None:
    chunks = [_chunk(1, "其他"), _chunk(2, "核心產品仍在二期臨床開發"), _chunk(3, "產品尚未商業化")]
    universe = PrecommercialCandidateRetrieverV23(route_base=_Base(), baseline=_Baseline()).candidate_universe(chunks, "precommercial_product")
    assert {item.page for item in universe.route_a} >= {2, 3}
    assert all(item.metadata["candidate_route"] == "route_a" for item in universe.route_a)


def test_route_b_finds_structured_revenue_and_service_activity() -> None:
    tables = [{"rows": [{"label": "收益", "cells": ["100", "200"]}]}]
    chunks = [_chunk(1, "其他"), _chunk(2, "收益 2019 2020 人民幣千元 " + "1" * 40, tables=tables), _chunk(3, "我們提供物業管理服務並收取服務費")]
    universe = PrecommercialCandidateRetrieverV23(route_base=_Base(), baseline=_Baseline()).candidate_universe(chunks, "precommercial_product")
    assert {item.page for item in universe.route_b} >= {2, 3}
    assert all(item.metadata["candidate_route"] == "route_b" for item in universe.route_b)


def test_bounded_union_deduplicates_and_caps_pool() -> None:
    base = [_evidence(page) for page in range(1, 51)]
    route_a = [_evidence(page) for page in range(40, 70)]
    route_b = [_evidence(page) for page in range(60, 100)]
    result = bounded_candidate_union(base, route_a, route_b, policy=V23_VARIANTS["v23_b"], limit=50)
    pages = [item.page for item in result]
    assert len(pages) == len(set(pages)) == 50
    assert pages[0] == 1
    # Pages 40-50 overlap Route A and may legitimately consume a route slot;
    # non-overlapping base candidates must retain their internal order.
    base_subsequence = [page for page in pages if page < 40]
    assert base_subsequence == sorted(base_subsequence)


def test_route_quota_places_both_routes_in_bounded_head() -> None:
    base = [_evidence(page) for page in range(1, 51)]
    route_a = [_evidence(page) for page in range(101, 151)]
    route_b = [_evidence(page) for page in range(201, 251)]
    result = bounded_candidate_union(base, route_a, route_b, policy=V23_VARIANTS["v23_b"], limit=50)
    head = {item.page for item in result[:20]}
    assert len(head & set(range(101, 151))) == 3
    assert len(head & set(range(201, 251))) == 5
    assert len(head & set(range(1, 51))) == 12


def test_other_risks_preserve_old_candidates_exactly() -> None:
    chunks = [_chunk(page, "收益") for page in range(1, 8)]
    retriever = PrecommercialCandidateRetrieverV23(route_base=_Base(), baseline=_Baseline())
    result = retriever.retrieve_for_risk(chunks, "cash_runway", limit=5)
    assert [item.page for item in result] == [1, 2, 3, 4, 5]


def test_runner_uses_development_selected_frozen_variant_and_case_split() -> None:
    assert FROZEN_VARIANT == "v23_b"
    cases = ["ipo_2020_00368", "ipo_2020_06618", "ipo_2020_03347", "ipo_2021_09982"]
    split = case_split(cases)
    assert split["ipo_2020_00368"] == "historical_development"
    assert set(split) == set(cases)


def test_v23_temporary_directory_is_cleaned() -> None:
    parent = Path(tempfile.gettempdir())
    with tempfile.TemporaryDirectory(prefix="precommercial_v23_test_", dir=parent) as name:
        path = Path(name)
        (path / "current.pdf").write_bytes(b"temporary")
        assert path.exists()
    assert not path.exists()
