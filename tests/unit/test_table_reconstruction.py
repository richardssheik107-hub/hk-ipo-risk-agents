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


def _mixed_period_page_words() -> list[tuple]:
    """A track-record page mixing three full years with two nine-month stubs.

    Layout matches the consolidated income statements this cohort actually
    prints: one caption over the annual columns, a second over the interim
    columns, and ``2024年`` appearing under both.  A subtotal rule opens a gap
    that splits the statement into two blocks, so only the first sits under the
    caption.
    """
    return [
        # --- header: two captions, each centred over the columns it governs ---
        # Each caption is centred over the columns it governs, as printed.
        _word(312, 10, "截至12月31日止年度", width=115),   # centre ~370
        _word(445, 10, "截至9月30日止九個月", width=100),  # centre ~495
        _word(300, 22, "2022年"),
        _word(350, 22, "2023年"),
        _word(400, 22, "2024年"),
        _word(450, 22, "2024年"),
        _word(500, 22, "2025年"),
        _word(40, 34, "千美元", width=30),
        # --- block 0 -----------------------------------------------------------
        _word(40, 50, "收入", width=60),
        _word(302, 50, "3,460"),
        _word(352, 50, "30,523"),
        _word(402, 50, "19,454"),
        _word(452, 50, "53,437"),
        _word(502, 50, "70,110"),
        # --- block 1: below a wide gap, so it has no header of its own ---------
        _word(40, 160, "年內╱期內虧損", width=90),
        _word(302, 160, "(73,728)"),
        _word(352, 160, "(269,246)"),
        _word(402, 160, "(465,238)"),
        _word(452, 160, "(304,342)"),
        _word(502, 160, "(512,013)"),
    ]


def test_mixed_period_columns_split_annual_from_interim() -> None:
    table = reconstruct_page_tables(_mixed_period_page_words())[0]

    assert table["period_basis_mixed"] is True
    assert [column["year_label"] for column in table["period_columns"]] == [
        "2022年",
        "2023年",
        "2024年",
        "2024年",
        "2025年",
    ]
    # The repeated 2024年 is governed by two different captions, so the two
    # columns are separate periods rather than one duplicated year.
    assert [column["group_line"] for column in table["period_columns"]] == [
        "截至12月31日止年度",
        "截至12月31日止年度",
        "截至12月31日止年度",
        "截至9月30日止九個月",
        "截至9月30日止九個月",
    ]
    # One period column per value cell is what removes value_period_count_mismatch.
    assert len(table["period_columns"]) == len(table["rows"][0]["cells"])


def test_block_without_own_header_inherits_the_page_period_header() -> None:
    tables = reconstruct_page_tables(_mixed_period_page_words())

    assert [table["period_header_source"] for table in tables] == [
        "block",
        "carried_forward",
    ]
    # All blocks on the page share one column geometry, hence one period map.
    assert tables[1]["period_columns"] == tables[0]["period_columns"]
    assert tables[1]["rows"][0]["label"] == "年內╱期內虧損"
    # The inherited header carries the caption, not the block above's data row.
    assert "千美元" in tables[1]["header_lines"]
    assert "(73,728)" not in tables[1]["header_lines"]


def test_interim_column_without_a_repeated_year_falls_back_to_geometry() -> None:
    """Three annual columns plus a lone 2025 stub: no year repeats, so the
    repeat cue cannot split the header and the caption geometry must."""
    words = [
        _word(312, 10, "截至12月31日止年度", width=115),  # centre ~370
        _word(470, 10, "截至9月30日止九個月", width=100),  # centre ~520
        _word(300, 22, "2022年"),
        _word(350, 22, "2023年"),
        _word(400, 22, "2024年"),
        _word(500, 22, "2025年"),
        _word(40, 50, "收入", width=60),
        _word(302, 50, "3,460"),
        _word(352, 50, "30,523"),
        _word(402, 50, "19,454"),
        _word(502, 50, "53,437"),
    ]
    table = reconstruct_page_tables(words)[0]

    assert [column["group_line"] for column in table["period_columns"]] == [
        "截至12月31日止年度",
        "截至12月31日止年度",
        "截至12月31日止年度",
        "截至9月30日止九個月",
    ]


def test_wrapped_chinese_period_caption_is_rejoined_before_column_assignment() -> None:
    """A split interim caption must not make its columns inherit annual basis."""
    words = [
        _word(290, 10, "截至12月31日止年度", width=105),
        _word(450, 10, "截至8", width=30),
        _word(481, 10, "月31日止八個月", width=75),
        _word(290, 32, "2020年"),
        _word(360, 32, "2021年"),
        _word(430, 32, "2021年"),
        _word(500, 32, "2022年"),
        _word(40, 55, "經營活動所用現金流量淨額", width=150),
        _word(292, 55, "(34,199)"),
        _word(362, 55, "(62,491)"),
        _word(432, 55, "(33,880)"),
        _word(502, 55, "(59,969)"),
    ]

    table = reconstruct_page_tables(words)[0]

    assert [column["group_line"] for column in table["period_columns"]] == [
        "截至12月31日止年度",
        "截至12月31日止年度",
        "截至8月31日止八個月",
        "截至8月31日止八個月",
    ]


def test_period_group_grammar_matches_the_extractor() -> None:
    """The parser's caption grammar must not drift from the extractor's."""
    from ipo_risk.extraction.financial import V03FinancialFactExtractor
    from ipo_risk.parsers.table_reconstruction import _PERIOD_GROUP_RE

    samples = [
        "截至12月31日止年度",
        "截至9月30日止九個月",
        "截至2023年12月31日止年度",
        "year ended 31 December 2023",
        "nine months ended 30 September 2025",
        "Year Ended December 31",
        "2023年",
        "人民幣千元",
        "綜合損益表",
        "",
    ]
    for sample in samples:
        assert bool(_PERIOD_GROUP_RE.search(sample)) is (
            V03FinancialFactExtractor._is_period_group(sample)
        ), sample


def _right_aligned_word(x1: float, y0: float, text: str, char_width: float = 5.0) -> tuple:
    """A cell printed against a right-hand column rule, as a statement prints it."""
    width = char_width * len(text)
    return (x1 - width, y0, x1, y0 + 8.0, text, 0, 0, 0)


def test_short_right_aligned_cell_is_not_dropped() -> None:
    """A dash and a five-digit figure share a column rule but not a centre.

    Geometry copied from MiniMax 00100 physical page 542: the year headers are
    *centred* over columns whose values are *right*-aligned, so the dash in the
    first column centres 16.9pt right of its anchor and used to fall outside the
    16pt snapping tolerance, leaving an empty cell behind.
    """
    words = [
        _word(281.3, 122.6, "2022年", width=22.7),   # centre 292.7
        _word(330.9, 122.6, "2023年", width=22.7),   # centre 342.3
        _word(380.6, 122.6, "2024年", width=22.7),   # centre 391.9
        _word(85.0, 182.9, "收入", width=18.0),
        _word(242.6, 182.9, "5", width=7.7),         # note reference column
        _right_aligned_word(311.8, 182.9, "–", char_width=4.4),
        _right_aligned_word(361.4, 182.9, "3,460"),
        _right_aligned_word(411.0, 182.9, "30,523"),
        _word(85.0, 201.2, "銷售成本", width=36.0),
        _right_aligned_word(311.8, 201.2, "–", char_width=4.4),
        _right_aligned_word(364.3, 201.2, "(4,314)"),
        _right_aligned_word(414.0, 201.2, "(26,785)"),
    ]
    table = reconstruct_page_tables(words)[0]

    assert [row["cells"] for row in table["rows"]] == [
        ["–", "3,460", "30,523"],
        ["–", "(4,314)", "(26,785)"],
    ]
    # The note reference sits a full column left of the first value box, so it
    # stays in the label even though "5" is a well-formed amount token.
    assert table["rows"][0]["label"] == "收入 5"


def test_wide_cell_left_of_its_anchor_still_lands_in_its_own_column() -> None:
    """The mirror case: a long figure centres *left* of the year label above it."""
    words = [
        _word(281.3, 122.6, "2022年", width=22.7),   # centre 292.7
        _word(330.9, 122.6, "2023年", width=22.7),   # centre 342.3
        _word(380.6, 122.6, "2024年", width=22.7),   # centre 391.9
        _word(85.0, 182.9, "稅前虧損", width=36.0),
        _right_aligned_word(314.7, 182.9, "(1,073,728)"),  # centre 287.2
        _right_aligned_word(364.3, 182.9, "(269,246)"),
        _right_aligned_word(414.0, 182.9, "(465,238)"),
    ]
    table = reconstruct_page_tables(words)[0]

    assert table["rows"][0]["cells"] == ["(1,073,728)", "(269,246)", "(465,238)"]


def test_two_tokens_in_one_column_box_do_not_fabricate_a_data_row() -> None:
    """A page footer such as ``I-5`` puts two dashes inside the first column.

    Spilling the surplus into the empty neighbouring column would turn the footer
    into a two-cell data row, so a contested box keeps only its first token.
    """
    words = [
        _word(281.3, 122.6, "2022年", width=22.7),
        _word(330.9, 122.6, "2023年", width=22.7),
        _word(380.6, 122.6, "2024年", width=22.7),
        _word(85.0, 182.9, "收入", width=18.0),
        _right_aligned_word(311.8, 182.9, "–", char_width=4.4),
        _right_aligned_word(361.4, 182.9, "3,460"),
        _right_aligned_word(411.0, 182.9, "30,523"),
        # footer: both dashes fall inside the first column's interval
        _right_aligned_word(287.8, 760.0, "–", char_width=4.4),
        _right_aligned_word(312.7, 760.0, "–", char_width=4.4),
    ]
    tables = reconstruct_page_tables(words)
    labels = [row["label"] for table in tables for row in table["rows"]]

    assert labels == ["收入"]


def test_column_bounds_split_the_axis_at_anchor_midpoints() -> None:
    from ipo_risk.parsers.table_reconstruction import _column_bounds

    lower, upper = _column_bounds([100.0, 150.0, 200.0])

    assert lower == [75.0, 125.0, 175.0]
    assert upper == [125.0, 175.0, 225.0]
    # Contiguous and gapless: every x between the outer bounds has exactly one column.
    assert lower[1:] == upper[:-1]


def test_label_wrapped_over_two_lines_is_rejoined() -> None:
    """A caption's tail can name a different metric than the whole caption.

    "年內利潤及全面" / "收入總額" is *profit and total comprehensive income*, but the
    line carrying the values reads as 收入總額 — revenue — so the row's net profit
    would be extracted as the company's revenue.
    """
    words = [
        _word(320, 20, "2021年"),
        _word(390, 20, "2022年"),
        _word(460, 20, "2023年"),
        _word(40, 50, "年內利潤及全面", width=70),  # label line 1: no values
        _word(40, 62, "收入總額", width=40),
        _word(322, 62, "31,155"),
        _word(392, 62, "37,439"),
        _word(462, 62, "51,018"),
    ]
    table = reconstruct_page_tables(words)[0]

    assert table["rows"][0]["label"] == "年內利潤及全面收入總額"
    assert table["rows"][0]["cells"] == ["31,155", "37,439", "51,018"]


def test_label_wrapped_over_three_lines_keeps_reading_order() -> None:
    """Collected walking upwards, the lines must be replayed top-to-bottom."""
    words = [
        _word(320, 20, "2021年"),
        _word(390, 20, "2022年"),
        _word(460, 20, "2023年"),
        _word(40, 44, "以公允價值計量且其", width=80),
        _word(40, 56, "變動計入損益的金", width=80),
        _word(40, 68, "融資產的公允價值", width=80),
        _word(40, 80, "收益", width=20),
        _word(322, 80, "941"),
        _word(392, 80, "788"),
        _word(462, 80, "15,710"),
    ]
    table = reconstruct_page_tables(words)[0]

    assert table["rows"][0]["label"] == "以公允價值計量且其變動計入損益的金融資產的公允價值收益"


def test_column_captions_are_never_absorbed_into_a_label() -> None:
    """The unit line reaches into the value columns, so it is not a label line."""
    words = [
        _word(320, 20, "2021年"),
        _word(390, 20, "2022年"),
        _word(460, 20, "2023年"),
        _word(40, 32, "人民幣千元", width=50),
        _word(320, 32, "人民幣千元", width=50),
        _word(390, 32, "人民幣千元", width=50),
        _word(40, 50, "收益", width=30),
        _word(322, 50, "593,660"),
        _word(392, 50, "706,816"),
        _word(462, 50, "862,247"),
    ]
    table = reconstruct_page_tables(words)[0]

    assert table["rows"][0]["label"] == "收益"
