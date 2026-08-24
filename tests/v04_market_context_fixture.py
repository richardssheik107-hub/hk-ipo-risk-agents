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
            "dataset_split": "development",
        },
        {
            "case_id": "ipo_2024_02410",
            "stock_code_wind": "2410.HK",
            "official_listed_date": "2024-08-20",
            "source_year": "2024",
            "dataset_split": "validation",
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


def write_governed_extended_fixture(root: Path) -> Path:
    """Write the Extended-only fields consumed by the runtime explanation layer."""

    path = root / "v04_c_extended_readiness_438.csv"
    rows = []
    for case_id, stock_code, listing_date, dataset_split, reason in (
        ("ipo_2020_00368", "0368.HK", "2020-07-17", "development", "INDUSTRY_MAPPING_PIT_BLOCKED"),
        ("ipo_2024_02410", "2410.HK", "2024-08-20", "validation", "INDUSTRY_MAPPING_PIT_BLOCKED"),
    ):
        row = {
            "case_id": case_id,
            "stock_code": stock_code,
            "listing_date": listing_date,
            "dataset_split": dataset_split,
        }
        for name, value in (
            ("hsi_return_5d", "0.01"),
            ("hsi_return_20d", "0.02"),
            ("market_turnover_20d_mean", "1000000"),
            ("market_volatility_20d", "0.03"),
        ):
            row[name] = value
            row[f"{name}__available"] = "True"
            row[f"{name}__missing"] = "False"
            row[f"{name}__missing_reason"] = ""
        for name in ("industry_return_5d", "industry_return_20d"):
            row[name] = ""
            row[f"{name}__available"] = "False"
            row[f"{name}__missing"] = "True"
            row[f"{name}__missing_reason"] = reason
        rows.append(row)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return path
