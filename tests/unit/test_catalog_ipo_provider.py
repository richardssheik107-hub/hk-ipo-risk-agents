"""Unit tests for the catalog-backed IPO data provider (member #2, V3-2)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from ipo_risk.providers.catalog import (
    SPECIAL_SECURITIES,
    CatalogIPODataProvider,
    governance_table,
)

CATALOG_DIR = Path(__file__).resolve().parents[2] / "data" / "catalog"


@pytest.fixture(scope="module")
def provider() -> CatalogIPODataProvider:
    return CatalogIPODataProvider(CATALOG_DIR)


def test_loads_full_master_bridge(provider: CatalogIPODataProvider) -> None:
    assert len(provider) == 565
    assert len(provider.case_ids()) == len(set(provider.case_ids())) == 565


def test_matched_case_has_full_offering_facts(provider: CatalogIPODataProvider) -> None:
    profile = provider.get_by_case_id("ipo_2020_00368")
    assert profile.company_name == "德合集团"
    assert profile.stock_code == "0368.HK"
    assert profile.listing_date == date(2020, 7, 17)
    assert profile.industry == "楼宇建造"
    assert profile.issue_price == pytest.approx(0.63)
    assert profile.issue_size == pytest.approx(126_000_000)
    assert profile.metadata["data_complete"] is True
    assert profile.metadata["official_match_status"] == "matched"
    assert profile.metadata["net_proceed"] == pytest.approx(79_400_000)
    assert profile.metadata["dataset_split"] == "development"


def test_all_matched_cases_load_with_identity(provider: CatalogIPODataProvider) -> None:
    matched = [
        profile
        for profile in provider.iter_profiles()
        if profile.metadata["official_match_status"] == "matched"
    ]
    assert len(matched) == 562
    for profile in matched:
        assert profile.company_name  # official name present
        assert profile.stock_code.endswith(".HK")
        assert profile.metadata["data_complete"] is True


def test_lookup_by_stock_code_variants(provider: CatalogIPODataProvider) -> None:
    by_wind = provider.get_by_stock_code("0368.HK")
    by_raw = provider.get_by_stock_code("00368")
    by_bare = provider.get_by_stock_code("368")
    assert by_wind.metadata["case_id"] == by_raw.metadata["case_id"] == by_bare.metadata["case_id"]


def test_lookup_by_stock_code_and_year(provider: CatalogIPODataProvider) -> None:
    profile = provider.get_by_stock_code_and_year("07801", 2022)
    assert profile.metadata["case_id"] == "ipo_2022_07801"


def test_unknown_lookups_raise(provider: CatalogIPODataProvider) -> None:
    with pytest.raises(KeyError):
        provider.get_by_case_id("ipo_1999_99999")
    with pytest.raises(KeyError):
        provider.get_by_stock_code("99999")
    with pytest.raises(KeyError):
        provider.get_by_stock_code_and_year("00368", 1999)


def test_get_profile_resolves_and_degrades(provider: CatalogIPODataProvider) -> None:
    resolved = provider.get_profile("德合集团", "0368.HK")
    assert resolved.metadata["case_id"] == "ipo_2020_00368"

    degraded = provider.get_profile("Nonexistent Co", "99999")
    assert degraded.company_name == "Nonexistent Co"
    assert degraded.stock_code == "99999"
    assert degraded.metadata["official_match_status"] == "not_in_catalog"
    assert degraded.metadata["data_complete"] is False
    # No fabricated offering facts.
    assert degraded.issue_price is None
    assert degraded.issue_size is None
    assert degraded.industry == ""
    assert degraded.listing_date is None


def test_placeholder_degrades_without_guessing(provider: CatalogIPODataProvider) -> None:
    reit = provider.get_by_case_id("ipo_2021_02191")
    # Identity comes from the disclosed prospectus short name, not guessed.
    assert reit.company_name == "順豐房託"
    assert reit.stock_code == "2191.HK"
    assert reit.metadata["data_complete"] is False
    assert reit.metadata["official_match_status"] == "manifest_only_placeholder"
    # Offering facts are NOT fabricated for unmatched rows.
    assert reit.issue_price is None
    assert reit.issue_size is None
    assert reit.listing_date is None
    assert reit.industry == ""
    assert "offer_price" not in reit.metadata
    assert reit.metadata["degradation_reason"]


def test_reit_special_governance(provider: CatalogIPODataProvider) -> None:
    reit = provider.get_by_stock_code("2191.HK")
    special = reit.metadata["special_security"]
    assert special["security_category"] == "reit_units"
    assert special["canonical_stock_code"] == "2191.HK"
    assert special["related_warrant_code"] is None
    assert special["ordinary_equity_eligible"] is False
    assert special["market_label_eligible"] is True


def test_spac_warrants_link_to_a_shares(provider: CatalogIPODataProvider) -> None:
    for warrant, a_share in (("4801.HK", "7801.HK"), ("4841.HK", "7841.HK")):
        profile = provider.get_by_stock_code(warrant)
        special = profile.metadata["special_security"]
        assert special["security_category"] == "spac_warrant"
        assert special["canonical_stock_code"] == a_share
        assert special["related_warrant_code"] == warrant
        assert special["ordinary_equity_eligible"] is False
        assert special["market_label_eligible"] is False


def test_only_governed_codes_carry_special_security(provider: CatalogIPODataProvider) -> None:
    ordinary = provider.get_by_case_id("ipo_2020_00368")
    assert "special_security" not in ordinary.metadata
    governed = {rec["stock_code"] for rec in governance_table()}
    assert governed == set(SPECIAL_SECURITIES)
    assert governed == {"2191.HK", "4801.HK", "4841.HK"}


def test_profile_metadata_is_json_serializable(provider: CatalogIPODataProvider) -> None:
    # metadata must survive result serialization (model_dump(mode="json")).
    for case_id in ("ipo_2020_00368", "ipo_2021_02191", "ipo_2022_04801"):
        provider.get_by_case_id(case_id).model_dump(mode="json")
