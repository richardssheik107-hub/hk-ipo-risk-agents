from __future__ import annotations

import json
from pathlib import Path

from ipo_risk.domain.risk_codes import V03_ENABLED_RISK_CODES
from ipo_risk.evaluation.retriever_v3_baseline import (
    PageCandidate,
    build_failure_rows,
    build_hard_negatives,
    unique_coverage,
    variant_metrics,
)
from ipo_risk.evaluation.retriever_v3_dataset import (
    RetrievalGoldRow,
    build_retrieval_gold_rows,
    load_source_manifest,
    load_split_manifest,
    validate_gold_against_source_manifest,
    write_preflight_outputs,
)
from ipo_risk.schemas import DocumentChunk


ROOT = Path(__file__).resolve().parents[2]


def _gold(*, page: int, requirement: str = "required", role: str = "primary") -> RetrievalGoldRow:
    return RetrievalGoldRow(
        row_id=f"gold-{page}-{requirement}-{role}",
        case_id="ipo_2099_00001",
        stock_code="0001.HK",
        company_name="Fixture",
        document_id="ipo_2099_00001",
        source_year=2099,
        retrieval_split="development",
        risk_code="cash_runway",
        evidence_index=page,
        page=page,
        exact_text="cash and cash equivalents at end of period 100",
        evidence_role=role,
        requirement=requirement,
        source_authority="accountants_report",
        confidence=0.9,
        gold_grade=3 if requirement == "required" and role == "primary" else 2,
        risk_applicable=True,
        risk_expected_status="verified",
        risk_expected_level="high",
        risk_state_source="pass1",
        risk_review_state=False,
        authoritative_source=True,
    )


def _candidate(page: int, rank: int, variant: str) -> PageCandidate:
    return PageCandidate(
        case_id="ipo_2099_00001",
        risk_code="cash_runway",
        variant=variant,
        rank=rank,
        page=page,
        chunk_id=f"c{page}",
        relevance_score=max(0.01, 1 - rank / 100),
        authority_hint="accountants_report",
        matched_terms=["cash"],
        provenance={},
        text_excerpt=f"candidate page {page}",
    )


def _rankings(v1_pages: list[int], v2_pages: list[int], v21_pages: list[int]):
    return {
        "cash_runway": {
            "v1": [_candidate(page, rank, "v1") for rank, page in enumerate(v1_pages, 1)],
            "v2": [_candidate(page, rank, "v2") for rank, page in enumerate(v2_pages, 1)],
            "v21": [_candidate(page, rank, "v21") for rank, page in enumerate(v21_pages, 1)],
        }
    }


def test_frozen_split_is_50_10_and_keeps_exposed_cases_in_development():
    split = load_split_manifest(ROOT / "configs/retriever_v3_split_manifest.json")
    assert split.source_case_count == 60
    assert len(split.development_cases) == 50
    assert len(split.locked_validation_cases) == 10
    assert not (set(split.development_cases) & set(split.locked_validation_cases))
    assert set(split.known_retrieval_exposed_cases) <= set(split.development_cases)
    assert not (set(split.manual_annotation_review_exclusions) & set(split.locked_validation_cases))
    locked_years = [case.split("_")[1] for case in split.locked_validation_cases]
    assert locked_years.count("2020") == 3
    assert locked_years.count("2021") == 3
    assert locked_years.count("2022") == 4


def test_real_60_case_gold_preflight_is_structurally_valid(tmp_path: Path):
    split = load_split_manifest(ROOT / "configs/retriever_v3_split_manifest.json")
    rows = build_retrieval_gold_rows(expert_root=ROOT / "expert_results", split_manifest=split)
    validation = validate_gold_against_source_manifest(
        rows,
        split_manifest=split,
        source_manifest=load_source_manifest(ROOT / "docs/annotation/gpt_expert_v1_1/source_manifest.csv"),
    )
    assert validation["valid"], validation["errors"]
    assert validation["case_count"] == 60
    assert len({row.case_id for row in rows if row.retrieval_split == "development"}) == 50
    assert len({row.case_id for row in rows if row.retrieval_split == "locked_validation"}) == 10
    assert {row.risk_code for row in rows} == set(V03_ENABLED_RISK_CODES)
    assert len({row.row_id for row in rows}) == len(rows)
    assert {row.gold_grade for row in rows} <= {1, 2, 3}

    paths = write_preflight_outputs(rows=rows, split_manifest=split, validation=validation, output_dir=tmp_path)
    assert all(path.exists() for path in paths)
    locked_payload = json.loads((tmp_path / "locked_validation_manifest.json").read_text(encoding="utf-8"))
    assert locked_payload["gold_evidence_exported"] is False
    development_csv = (tmp_path / "development_gold_evidence.csv").read_text(encoding="utf-8-sig")
    for case_id in split.locked_validation_cases:
        assert case_id not in development_csv


def test_variant_metrics_and_complementary_coverage():
    gold = [_gold(page=10), _gold(page=20)]
    rankings = _rankings(v1_pages=[10, 1, 2, 3, 4], v2_pages=[20, 5, 6, 7, 8], v21_pages=[30, 31, 32, 33, 34])
    metrics = variant_metrics(rankings, gold)
    assert metrics["v1"]["required_recall_at"]["5"] == 0.5
    assert metrics["v2"]["required_recall_at"]["5"] == 0.5
    assert metrics["v21"]["required_recall_at"]["5"] == 0.0
    coverage = unique_coverage({"ipo_2099_00001": rankings}, gold)
    assert coverage["20"]["v1_v2_union_recall"] == 1.0
    assert coverage["20"]["v1_v2_v21_union_recall"] == 1.0
    assert coverage["20"]["marginal_v2_over_v1"] == 1


def test_failure_taxonomy_separates_ranking_from_coverage_and_builds_hard_negatives():
    ranking_pages = list(range(1, 25)) + [50]
    rankings = _rankings(v1_pages=ranking_pages, v2_pages=list(range(30, 55)), v21_pages=[60, 61, 62, 63, 64])
    gold = [_gold(page=50)]
    all_rankings = {"ipo_2099_00001": rankings}
    chunks = {"ipo_2099_00001": [DocumentChunk(document_id="ipo_2099_00001", chunk_id="c50", page=50, section="unknown", text="cash and cash equivalents at end of period 100")]}
    failures = build_failure_rows(all_rankings, gold, chunks)
    assert failures[0].primary_failure == "RANKING_ONLY_MISS"
    assert "learning_to_rank" in failures[0].recommended_lane
    negatives = build_hard_negatives(all_rankings, gold, depth=20)
    assert negatives
    assert all(row.page != 50 for row in negatives)
    assert any(row.negative_tier == "top5" for row in negatives)
