"""Streamlit issuer-identity intake backed by the official IPO catalog."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import streamlit as st

from ipo_risk.runtime.issuer_catalog import (
    IssuerCatalogRecord,
    load_issuer_catalog,
    search_issuer_catalog,
)


CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "catalog" / "ipo_official_master_bridge.csv"


@st.cache_data(show_spinner=False)
def _load_catalog(path: str, mtime_ns: int) -> tuple[IssuerCatalogRecord, ...]:
    del mtime_ns  # cache invalidation key only
    return load_issuer_catalog(path)


def _catalog() -> tuple[IssuerCatalogRecord, ...]:
    try:
        stat = CATALOG_PATH.stat()
        return _load_catalog(str(CATALOG_PATH), stat.st_mtime_ns)
    except (OSError, ValueError):
        return ()


def _apply_match(record: IssuerCatalogRecord, *, key_prefix: str) -> None:
    """Apply a catalog choice before the editable widgets are instantiated."""

    applied_key = f"{key_prefix}_issuer_match_applied"
    if st.session_state.get(applied_key) == record.case_id:
        return
    st.session_state[f"{key_prefix}_company"] = record.company_name
    st.session_state[f"{key_prefix}_code"] = record.stock_code
    st.session_state[f"{key_prefix}_listing"] = record.listing_date
    st.session_state[applied_key] = record.case_id


def _format_match(record: IssuerCatalogRecord) -> str:
    return record.label


def render_issuer_identity_inputs(
    *,
    key_prefix: str = "analysis",
    default_company: str = "Demo Biotech",
    default_code: str = "9999.HK",
    default_listing: date | None = None,
) -> tuple[str, str, date]:
    """Search one identity field, then keep all three values editable.

    Users may enter an issuer name, an HK stock code (with or without ``.HK``), a
    catalog case id, or an ISO listing date. A unique catalog hit is applied
    immediately. Ambiguous hits are shown as a compact selector. No match simply
    leaves the manual fields available, which preserves support for new IPOs that
    are outside the committed historical catalog.
    """

    if default_listing is None:
        default_listing = date.today()

    company_key = f"{key_prefix}_company"
    code_key = f"{key_prefix}_code"
    listing_key = f"{key_prefix}_listing"
    st.session_state.setdefault(company_key, default_company)
    st.session_state.setdefault(code_key, default_code)
    st.session_state.setdefault(listing_key, default_listing)

    query = st.text_input(
        "快速匹配发行人",
        key=f"{key_prefix}_issuer_lookup",
        placeholder="公司名称 / 股票代码 / 上市日期，例如：华润饮料、2460、2024-10-23",
        help="从官方 IPO catalog 匹配；匹配后仍可手工修改三个字段。",
    ).strip()

    records = _catalog()
    matches = search_issuer_catalog(records, query) if query and records else ()
    selected: IssuerCatalogRecord | None = None

    if query and not records:
        st.caption("官方 IPO catalog 当前不可读取；仍可直接手工填写发行人信息。")
    elif query and not matches:
        st.caption("未在官方 IPO catalog 找到匹配项；可继续手工填写新 IPO。")
    elif len(matches) == 1:
        selected = matches[0]
    elif len(matches) > 1:
        by_case = {record.case_id: record for record in matches}
        choice = st.selectbox(
            "匹配候选",
            options=list(by_case),
            index=None,
            placeholder=f"找到 {len(matches)} 个候选，请选择",
            format_func=lambda case_id: _format_match(by_case[case_id]),
            key=f"{key_prefix}_issuer_match_choice",
        )
        if choice:
            selected = by_case[choice]

    if selected is not None:
        _apply_match(selected, key_prefix=key_prefix)
        st.success(f"已匹配官方案例：{selected.label}")

    company = st.text_input("公司名称", key=company_key)
    code = st.text_input("股票代码", key=code_key)
    listing = st.date_input("上市日期", key=listing_key)
    return str(company).strip(), str(code).strip(), listing
