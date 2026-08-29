from __future__ import annotations

from datetime import date

from ipo_risk.runtime.issuer_catalog import (
    IssuerCatalogRecord,
    normalize_stock_code,
    search_issuer_catalog,
)


RECORDS = (
    IssuerCatalogRecord("ipo_2024_02410", "浙江同源康医药股份有限公司", "2410.HK", date(2024, 8, 20)),
    IssuerCatalogRecord("ipo_2024_02460", "华润饮料控股有限公司", "2460.HK", date(2024, 10, 23)),
    IssuerCatalogRecord("ipo_2024_01318", "毛戈平化妆品股份有限公司", "1318.HK", date(2024, 12, 10)),
)


def test_stock_code_normalization_accepts_common_hk_forms() -> None:
    assert normalize_stock_code("02460") == "2460"
    assert normalize_stock_code("2460") == "2460"
    assert normalize_stock_code("2460.HK") == "2460"
    assert normalize_stock_code(" 02460.hk ") == "2460"


def test_exact_stock_code_finds_one_issuer() -> None:
    assert search_issuer_catalog(RECORDS, "2460") == (RECORDS[1],)


def test_name_substring_finds_the_expected_issuer() -> None:
    assert search_issuer_catalog(RECORDS, "华润饮料") == (RECORDS[1],)


def test_listing_date_can_be_used_as_the_lookup_field() -> None:
    assert search_issuer_catalog(RECORDS, "2024-12-10") == (RECORDS[2],)


def test_unknown_new_ipo_returns_no_catalog_match() -> None:
    assert search_issuer_catalog(RECORDS, "9999.HK") == ()
