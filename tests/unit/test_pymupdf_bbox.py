from __future__ import annotations

from ipo_risk.parsers.pymupdf_parser import _page_text_bbox


def test_page_text_bbox_unions_real_word_rectangles() -> None:
    words = [
        (10.0, 20.0, 30.0, 40.0, "alpha", 0, 0, 0),
        (5.0, 25.0, 50.0, 60.0, "beta", 0, 0, 1),
        (100.0, 100.0, 110.0, 110.0, "   ", 0, 0, 2),
    ]

    assert _page_text_bbox(words) == [5.0, 20.0, 50.0, 60.0]


def test_page_text_bbox_ignores_invalid_coordinates_and_fails_closed() -> None:
    words = [
        (10.0, 20.0, 10.0, 40.0, "degenerate", 0, 0, 0),
        (float("nan"), 20.0, 30.0, 40.0, "nan", 0, 0, 1),
        ("bad", 20.0, 30.0, 40.0, "invalid", 0, 0, 2),
        (10.0, 20.0, 30.0, 40.0, "", 0, 0, 3),
    ]

    assert _page_text_bbox(words) is None
