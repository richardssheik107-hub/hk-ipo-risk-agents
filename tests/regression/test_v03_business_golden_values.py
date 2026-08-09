from __future__ import annotations

import csv
from pathlib import Path

from ipo_risk.agents.business_v03 import V03BusinessAgent
from ipo_risk.schemas import DocumentChunk, IPOProfile


MANIFEST = Path("tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv")


def business_rows() -> list[dict[str, str]]:
    with MANIFEST.open(encoding="utf-8", newline="") as handle:
        return [
            row
            for row in csv.DictReader(handle)
            if row["risk_code"] == "precommercial_product"
            and row["reviewer"] == "member-5"
        ]


def test_real_business_draft_annotations_are_positive_negative_and_unreviewed() -> None:
    rows = business_rows()
    assert {row["applicable"] for row in rows} == {"true", "false"}
    assert all(row["review_status"] == "draft" for row in rows)
    assert all(row["second_reviewer"] == "" for row in rows)
    assert all(row["case_id"].startswith("ipo_2020_") for row in rows)


def test_real_positive_text_generates_pending_candidate_without_pdf_or_network() -> None:
    rows = business_rows()
    core = next(
        row
        for row in rows
        if row["applicable"] == "true" and row["gold_page"] == "13"
    )
    revenue = next(
        row
        for row in rows
        if row["applicable"] == "true" and row["gold_page"] == "17"
    )
    chunks = [
        DocumentChunk(
            document_id=core["document_id"],
            chunk_id="core",
            page=int(core["gold_page"]),
            section="概要",
            text=core["exact_text"] + "處於臨床II期。",
        ),
        DocumentChunk(
            document_id=revenue["document_id"],
            chunk_id="revenue",
            page=int(revenue["gold_page"]),
            section="概要",
            text=revenue["exact_text"],
        ),
    ]
    risks = V03BusinessAgent().analyze(
        IPOProfile(company_name=core["company_name"], stock_code=core["stock_code"]),
        chunks,
    )
    assert len(risks) == 1
    assert risks[0].risk_code == "precommercial_product"
    assert [item.page for item in risks[0].evidence] == [13, 17]


def test_real_negative_text_does_not_generate_precommercial_candidate() -> None:
    row = next(row for row in business_rows() if row["applicable"] == "false")
    text = row["exact_text"] + "包裝飲用水產品所產生的收益佔我們總收益的57.9%。"
    chunk = DocumentChunk(
        document_id=row["document_id"],
        chunk_id="negative",
        page=int(row["gold_page"]),
        section="業務",
        text=text,
    )
    agent = V03BusinessAgent()
    assert agent.analyze(
        IPOProfile(company_name=row["company_name"], stock_code=row["stock_code"]),
        [chunk],
    ) == []
    assert agent.last_diagnostics[0].code.value == "not_applicable"
