from __future__ import annotations

from ipo_risk.core.container import default_registry
from ipo_risk.parsers.pymupdf_parser import (
    PyMuPDFRoleBRecallParser,
    _table_search_text,
    _unique_search_text_variants,
)


def test_search_variants_are_bounded_and_deduplicated() -> None:
    variants = _unique_search_text_variants(
        "primary text",
        (
            ("same", " primary   text "),
            ("word_stream", "primary text recovered anchor"),
            ("empty", ""),
        ),
    )

    assert variants == {
        "word_stream": "primary text recovered anchor"
    }


def test_structured_table_view_serializes_header_label_and_cells() -> None:
    observed = _table_search_text(
        [
            {
                "period_columns": [
                    {
                        "period_group": "截至十二月三十一日止年度",
                        "year_label": "2023年",
                    },
                    {
                        "period_group": "截至十二月三十一日止年度",
                        "year_label": "2024年",
                    },
                ],
                "rows": [
                    {"label": "收益", "cells": ["100", "120"]},
                    {"label": "年內虧損", "cells": ["(20)", "(25)"]},
                ],
            }
        ]
    )

    assert "截至十二月三十一日止年度 2023年 2024年" in observed
    assert "收益 100 120" in observed
    assert "年內虧損 (20) (25)" in observed


class _FakePage:
    def get_text(self, mode: str, sort: bool = False):
        if mode == "text":
            return "主頁文字缺少表格列" if not sort else "主頁文字缺少表格列"
        if mode == "blocks":
            return [(0, 0, 10, 10, "主頁文字缺少表格列")]
        if mode == "words":
            return [
                (0, 0, 10, 10, "五大客戶", 0, 0, 0),
                (11, 0, 20, 10, "佔總收益", 0, 0, 1),
                (21, 0, 25, 10, "80%", 0, 0, 2),
            ]
        raise AssertionError(mode)


class _FakeDocument:
    def load_page(self, _page_index: int) -> _FakePage:
        return _FakePage()


def test_recall_parser_keeps_primary_identity_and_attaches_word_view() -> None:
    parser = PyMuPDFRoleBRecallParser()

    chunk = parser._parse_page(_FakeDocument(), "doc", 4)

    assert chunk is not None
    assert chunk.chunk_id == "doc:page:5"
    assert chunk.page == 5
    assert chunk.text == "主頁文字缺少表格列"
    assert (
        chunk.metadata["search_text_variants"]["word_stream"]
        == "五大客戶 佔總收益 80%"
    )
    assert chunk.metadata["parser_version"] == "pymupdf_role_b_recall_v1"


def test_recall_parser_is_registered_without_replacing_released_parsers() -> None:
    registry = default_registry()

    observed = registry.create("parser", "pymupdf_role_b_recall")
    released = registry.create("parser", "pymupdf")

    assert observed.name == "pymupdf_role_b_recall"
    assert released.name == "pymupdf"
