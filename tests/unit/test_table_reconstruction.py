"""Unit tests for the dependency-free financial-table reconstructor."""

from __future__ import annotations

from ipo_risk.parsers.table_reconstruction import reconstruct_page_tables


def _word(x0: float, y0: float, text: str, width: float = 40.0) -> tuple:
    # (x0, y0, x1, y1, text, block, line, word_no) — matches fitz get_text("words")
    return (x0, y0, x0 + width, y0 + 8.0, text, 0, 0, 0)


def _cashflow_page_words() -> list[tuple]:
    """A borderless 3-year cash-flow grid like physical page 29 of 01354."""
    return [
        # header
        _word(40, 10, "截至12月31日止年度", width=90),
        _word(320, 20, "2021年"),
        _word(390, 20, "2022年"),
        _word(460, 20, "2023年"),
        _word(40, 30, "（人民幣千元）（人民幣千元）（人民幣千元）", width=120),
        # data rows: label + three year-aligned value columns
        _word(40, 50, "經營活動所得╱（所用）現金淨額", width=140),
        _word(322, 50, "60,227"),
        _word(392, 50, "(24,763)"),
        _word(462, 50, "160,584"),
        _word(40, 62, "年末現金及現金等價物", width=110),
        _word(322, 62, "248,585"),
        _word(392, 62, "202,877"),
        _word(462, 62, "257,430"),
    ]


def test_reconstructs_year_anchored_columns() -> None:
    tables = reconstruct_page_tables(_cashflow_page_words())

    assert len(tables) == 1
    table = tables[0]
    assert table["period_header_cells"] == ["2021年", "2022年", "2023年"]
    labels = {row["label"]: row["cells"] for row in table["rows"]}
    assert labels["經營活動所得╱（所用）現金淨額"] == ["60,227", "(24,763)", "160,584"]
    assert labels["年末現金及現金等價物"] == ["248,585", "202,877", "257,430"]
    # The period-group line and the caption ride in header_lines for `_parse_periods`.
    assert "截至12月31日止年度" in table["header_lines"]


def test_note_reference_stays_in_label_not_cells() -> None:
    words = [
        _word(320, 20, "2021年"),
        _word(390, 20, "2022年"),
        _word(460, 20, "2023年"),
        _word(40, 50, "償還計息借款", width=70),
        _word(150, 50, "18(b)", width=25),  # note reference, left of value columns
        _word(322, 50, "(41,500)"),
        _word(392, 50, "(2,000)"),
        _word(462, 50, "(12,000)"),
    ]
    table = reconstruct_page_tables(words)[0]
    row = table["rows"][0]
    assert row["cells"] == ["(41,500)", "(2,000)", "(12,000)"]
    assert "18(b)" in row["label"]


def test_returns_empty_without_year_anchors() -> None:
    words = [
        _word(40, 10, "本公司主要從事物業管理服務。", width=160),
        _word(40, 22, "收益增加主要由於業務擴張。", width=160),
    ]
    assert reconstruct_page_tables(words) == []


def test_ignores_blank_words() -> None:
    assert reconstruct_page_tables([_word(0, 0, "  ")]) == []
