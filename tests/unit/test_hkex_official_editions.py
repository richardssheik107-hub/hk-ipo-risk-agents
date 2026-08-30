from __future__ import annotations

import json
from datetime import date

import pytest

from ipo_risk.sources.hkex_editions import (
    HKEXEditionResolver,
    HKEXSourceError,
    edition_relationship_confidence,
    normalize_hkex_stock_code,
    parse_active_stock_index,
    parse_stock_index_candidates,
    parse_title_search_response,
    select_official_prospectus,
)


def _title_payload(rows: list[dict[str, str]]) -> bytes:
    return json.dumps({"result": json.dumps(rows)}).encode()


def _row(*, title: str, long_text: str, link: str, size: str = "9MB") -> dict[str, str]:
    return {
        "STOCK_CODE": "00816",
        "STOCK_NAME": "JINMAO SERVICES",
        "DATE_TIME": "25/02/2022 06:19",
        "TITLE": title,
        "LONG_TEXT": long_text,
        "FILE_LINK": link,
        "FILE_INFO": size,
        "NEWS_ID": "10130094",
    }


def test_normalizes_stock_code_without_issuer_special_cases() -> None:
    assert normalize_hkex_stock_code("816.HK") == "00816"
    assert normalize_hkex_stock_code("00816") == "00816"
    with pytest.raises(HKEXSourceError):
        normalize_hkex_stock_code("not-a-code")


def test_parses_official_stock_index_and_preserves_reused_delisted_codes() -> None:
    payload = json.dumps([{"i": 1000140857, "c": "00816", "n": "JINMAO SERVICES"}]).encode()
    assert parse_active_stock_index(payload)["00816"].stock_id == 1000140857
    duplicate = json.dumps(
        [
            {"i": 1, "c": "00816", "n": "A"},
            {"i": 2, "c": "00816", "n": "B"},
        ]
    ).encode()
    assert len(parse_stock_index_candidates(duplicate)["00816"]) == 2
    assert parse_active_stock_index(duplicate)["00816"].stock_id == 1


def test_prospectus_selection_requires_official_listing_document_category() -> None:
    rows = [
        _row(
            title="GLOBAL OFFERING",
            long_text="Announcements and Notices - [Formal Notice]",
            link="/listedco/listconews/sehk/2022/0225/formal.pdf",
        ),
        _row(
            title="GREEN APPLICATION FORM",
            long_text="Listing Documents - [Offer for Subscription]",
            link="/listedco/listconews/sehk/2022/0225/form.pdf",
        ),
        _row(
            title="GLOBAL OFFERING",
            long_text="Listing Documents - [Offer for Subscription]",
            link="/listedco/listconews/sehk/2022/0225/prospectus.pdf",
        ),
    ]
    documents = parse_title_search_response(_title_payload(rows), language="en")
    selected = select_official_prospectus(documents, disclosure_date=date(2022, 2, 25))
    assert selected is not None
    assert selected.file_url.endswith("prospectus.pdf")


def test_bilingual_relationship_uses_official_stock_date_and_document_class() -> None:
    en = parse_title_search_response(
        _title_payload(
            [
                _row(
                    title="GLOBAL OFFERING",
                    long_text="Listing Documents - [Offer for Subscription]",
                    link="/listedco/listconews/sehk/2022/0225/en.pdf",
                )
            ]
        ),
        language="en",
    )[0]
    zh = parse_title_search_response(
        _title_payload(
            [
                _row(
                    title="全球發售",
                    long_text="上市文件 - [發售以供認購]",
                    link="/listedco/listconews/sehk/2022/0225/zh.pdf",
                )
            ]
        ),
        language="zh-Hant",
    )[0]
    assert edition_relationship_confidence(en, zh, disclosure_date=date(2022, 2, 25)) == "high"


def test_resolver_queries_both_languages_without_gold() -> None:
    stock_payload = json.dumps(
        [{"i": 1000140857, "c": "00816", "n": "JINMAO SERVICES"}]
    ).encode()
    en_payload = _title_payload(
        [
            _row(
                title="GLOBAL OFFERING",
                long_text="Listing Documents - [Offer for Subscription]",
                link="/listedco/listconews/sehk/2022/0225/en.pdf",
            )
        ]
    )
    zh_payload = _title_payload(
        [
            _row(
                title="全球發售",
                long_text="上市文件 - [發售以供認購]",
                link="/listedco/listconews/sehk/2022/0225/zh.pdf",
            )
        ]
    )

    def fetch(url: str) -> bytes:
        if "activestock" in url:
            return stock_payload
        return en_payload if "lang=E" in url else zh_payload

    result = HKEXEditionResolver(fetch=fetch).discover(
        stock_code="816.HK", disclosure_date=date(2022, 2, 25)
    )
    assert result.bilingual is True
    assert result.relationship_confidence == "high"
    assert result.listing_identity == "SEHK:00816:2022-02-25:prospectus"


def test_resolver_falls_back_to_official_delisted_index() -> None:
    active_payload = json.dumps([]).encode()
    inactive_payload = json.dumps(
        [{"i": 1000140857, "c": "00816", "n": "JINMAO SERVICES"}]
    ).encode()
    en_payload = _title_payload(
        [
            _row(
                title="GLOBAL OFFERING",
                long_text="Listing Documents - [Offer for Subscription]",
                link="/listedco/listconews/sehk/2022/0225/en.pdf",
            )
        ]
    )
    zh_payload = _title_payload(
        [
            _row(
                title="全球發售",
                long_text="上市文件 - [發售以供認購]",
                link="/listedco/listconews/sehk/2022/0225/zh.pdf",
            )
        ]
    )

    def fetch(url: str) -> bytes:
        if "inactivestock" in url:
            return inactive_payload
        if "activestock" in url:
            return active_payload
        return en_payload if "lang=E" in url else zh_payload

    result = HKEXEditionResolver(fetch=fetch).discover(
        stock_code="816.HK", disclosure_date=date(2022, 2, 25)
    )
    assert result.bilingual is True
    assert result.stock_identity.stock_id == 1000140857
