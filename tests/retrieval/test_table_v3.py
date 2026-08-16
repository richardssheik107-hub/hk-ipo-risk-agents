from __future__ import annotations

import tempfile
from pathlib import Path

from ipo_risk.retrieval.table_v3 import (
    TABLE_VARIANTS, TableCandidateIndex, build_table_blocks, is_table_like_line, table_signal,
)
from ipo_risk.schemas import DocumentChunk


def _chunk(page: int, text: str) -> DocumentChunk:
    return DocumentChunk(document_id="case", chunk_id=f"p{page}", page=page, section="unknown", text=text)


ZH_TABLE = """收入類型
截至2022年12月31日
2020年
2021年
2022年
產品銷售 1,200 2,400 3,600
服務收入 300 420 510
總計 1,500 2,820 4,110"""


def test_table_signals_cover_chinese_english_currency_and_percentage() -> None:
    mixed = ZH_TABLE + "\nRevenue HK$1,200 HK$2,400\nMargin 10% 20% 30%"
    signal = table_signal(mixed)
    assert signal.is_table_like
    assert signal.percentage_count == 3
    assert signal.currency_count == 2
    assert signal.year_count == 3


def test_empty_and_numeric_prose_are_not_tables() -> None:
    assert not table_signal(None).is_table_like
    prose = ("The company was founded in 2018 and expanded in 2019. Revenue was 100 million in 2020, "
             "then 120 million in 2021, while management discussed these figures in ordinary prose.")
    assert not table_signal(prose).is_table_like


def test_table_like_line_and_block_grouping() -> None:
    assert is_table_like_line("Product sales 1,200 2,400 3,600")
    blocks = build_table_blocks(17, ZH_TABLE, max_chars=300)
    assert blocks
    assert {block.page for block in blocks} == {17}
    assert all(len(block.text) <= 380 for block in blocks)


def test_non_table_prose_does_not_create_microchunks() -> None:
    text = "Ordinary business description with a reference to 2020 and 2021 but no tabular row structure."
    assert build_table_blocks(1, text) == []


def test_page_aggregation_dedup_cap_and_determinism() -> None:
    chunks = [_chunk(page, ZH_TABLE + "\nrevenue growth 10% 20% 30%") for page in range(1, 70)]
    index = TableCandidateIndex(chunks, TABLE_VARIANTS[2])
    first = index.search("revenue_growth", top_k=50)
    second = index.search("revenue_growth", top_k=50)
    assert first == second
    assert len(first) == 50
    assert len({item.page for item in first}) == 50
    assert [item.page for item in first[:3]] == [1, 2, 3]


def test_all_variants_map_blocks_back_to_physical_pages() -> None:
    chunks = [_chunk(9, ZH_TABLE + "\n收入 增長 10% 20% 30%")]
    for variant in TABLE_VARIANTS:
        result = TableCandidateIndex(chunks, variant).search("revenue_growth")
        assert result and result[0].page == 9
        assert result[0].table_block_hit_count >= 1


def test_temporary_table_workspace_cleans_up() -> None:
    parent = Path.cwd()
    with tempfile.TemporaryDirectory(prefix=".tmp_table_unit_", dir=parent) as name:
        path = Path(name)
        assert path.exists()
    assert not path.exists()


def test_phase_c_split_excludes_locked_cases() -> None:
    from scripts.run_retriever_v3_phase_b_bm25 import _load_qrels, _load_split

    development, locked = _load_split(Path("reports/retriever_v3/split_manifest.json"))
    rows = _load_qrels(Path("reports/retriever_v3/gold_evidence.csv"), set(development), set(locked))
    assert len(development) == 50 and len(locked) == 10
    assert not ({row["case_id"] for row in rows} & set(locked))
