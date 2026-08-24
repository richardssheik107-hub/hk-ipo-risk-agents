"""Hermetic PR-B Core artifacts for runtime-channel tests."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from ipo_risk.market.ipo_market_context_features import (
    IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
    IPO_MARKET_CONTEXT_FEATURE_POLICY_VERSION,
    IPO_MARKET_CONTEXT_FEATURE_SCHEMA_VERSION,
    IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER,
    content_hash,
    vectorize_ipo_market_context,
)


def write_governed_pr_b_fixture(root: Path) -> tuple[Path, Path]:
    """Write two self-consistent PR-B projections without runtime artifacts."""

    bridge_path = root / "ipo_official_master_bridge.csv"
    feature_dir = root / "core_features"
    feature_dir.mkdir(parents=True)
    bridge_rows = (
        {
            "case_id": "ipo_2020_00368",
            "stock_code_wind": "0368.HK",
            "official_listed_date": "2020-07-17",
            "source_year": "2020",
        },
        {
            "case_id": "ipo_2024_02410",
            "stock_code_wind": "2410.HK",
            "official_listed_date": "2024-08-20",
            "source_year": "2024",
        },
    )
    with bridge_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(bridge_rows[0]))
        writer.writeheader()
        writer.writerows(bridge_rows)
    bridge_hash = hashlib.sha256(bridge_path.read_bytes()).hexdigest()

    available = {
        name: float(index + 1)
        for index, name in enumerate(IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER)
    }
    early = dict(available)
    for name in (
        "same_industry_ipo_count_180d",
        "same_industry_recent_break_rate",
        "same_industry_recent_return_5d",
        "same_industry_recent_1d_sample_count",
        "same_industry_recent_5d_sample_count",
    ):
        early[name] = None

    for row, raw_values in zip(bridge_rows, (early, available), strict=True):
        names, values = vectorize_ipo_market_context(raw_values)
        payload = {
            "case_id": row["case_id"],
            "cohort_year": int(row["source_year"]),
            "core_feature_manifest_hash": IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
            "core_feature_policy_version": IPO_MARKET_CONTEXT_FEATURE_POLICY_VERSION,
            "core_feature_schema_version": IPO_MARKET_CONTEXT_FEATURE_SCHEMA_VERSION,
            "cutoff_semantics": "strictly_before_target_listing_date",
            "dataset_split": (
                "development" if int(row["source_year"]) <= 2023 else "validation"
            ),
            "feature_names": list(names),
            "feature_values": list(values),
            "listing_date": row["official_listed_date"],
            "raw_values": raw_values,
            "source_provenance": {
                "official_bridge_sha256": bridge_hash,
                "fixture": True,
            },
            "stock_code": row["stock_code_wind"],
        }
        payload["content_hash"] = content_hash(payload)
        (feature_dir / f"{row['case_id']}.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
    return feature_dir, bridge_path
