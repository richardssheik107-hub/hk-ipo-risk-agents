"""PR-C input-readiness audit using the unchanged market label generator."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any

from ipo_risk.market.eod_store import EXPECTED_OFFICIAL_CASE_COUNT
from ipo_risk.market.labels import MarketLabelGenerator
from ipo_risk.providers.filtered_eod_v2 import FilteredEODV2MarketDataProvider
from ipo_risk.schemas.market import (
    MarketLabelAvailability,
    MarketLabelHorizon,
)


LABEL_READINESS_VERSION = "v04_pr_c_label_readiness_v1"


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_label_readiness(
    provider: FilteredEODV2MarketDataProvider,
    *,
    expected_case_count: int | None = EXPECTED_OFFICIAL_CASE_COUNT,
) -> dict[str, Any]:
    """Measure 1D/5D input readiness without freezing any PR-C policy."""

    metadata = provider.iter_listing_metadata()
    if expected_case_count is not None and len(metadata) != expected_case_count:
        raise ValueError(
            f"official cohort drift: expected {expected_case_count}, found {len(metadata)}"
        )
    if any(item.cohort_year >= 2025 for item in metadata):
        raise ValueError("2025 Blind outcomes are forbidden in label readiness")

    identity = provider.provider_identity
    generator = MarketLabelGenerator()
    records: list[dict[str, Any]] = []
    audit_failures: list[dict[str, str]] = []
    for item in sorted(metadata, key=lambda value: value.case_id):
        row: dict[str, Any] = {
            "case_id": item.case_id,
            "stock_code": item.stock_code,
            "cohort_year": item.cohort_year,
            "dataset_split": "development"
            if item.cohort_year <= 2023
            else "validation",
            "listing_date": item.listing_date.isoformat()
            if item.listing_date
            else "",
            "official_issue_price_available": item.listing_price is not None,
            "eod_available": False,
            "eod_1d_session_ready": False,
            "eod_5d_session_ready": False,
            "1d_availability": "failed",
            "1d_target_trading_date": "",
            "1d_raw_return": None,
            "1d_missing_reason": "",
            "5d_availability": "failed",
            "5d_target_trading_date": "",
            "5d_raw_return": None,
            "5d_missing_reason": "",
            "audit_failure_reason": "",
            "eod_store_version": identity["filter_schema_version"],
            "eod_store_checksum": identity["filtered_store_sha256"],
            "eod_store_manifest_checksum": identity[
                "filtered_store_manifest_sha256"
            ],
            "raw_eod_checksum": identity["raw_eod_sha256"],
            "bridge_checksum": identity["official_bridge_sha256"],
        }
        try:
            bars = provider.get_daily_bars(item.stock_code)
            eligible = [
                bar
                for bar in bars
                if item.listing_date is not None
                and bar.trading_date >= item.listing_date
            ]
            row["eod_available"] = bool(eligible)
            row["eod_1d_session_ready"] = len(eligible) >= 1
            row["eod_5d_session_ready"] = len(eligible) >= 5
            labels = {
                label.horizon: label for label in generator.generate(item, bars)
            }
            for prefix, horizon in (
                ("1d", MarketLabelHorizon.ONE_DAY),
                ("5d", MarketLabelHorizon.FIVE_DAYS),
            ):
                label = labels[horizon]
                row[f"{prefix}_availability"] = label.availability.value
                row[f"{prefix}_target_trading_date"] = (
                    label.target_trading_date.isoformat()
                    if label.target_trading_date
                    else ""
                )
                row[f"{prefix}_raw_return"] = (
                    str(label.raw_return) if label.raw_return is not None else None
                )
                row[f"{prefix}_missing_reason"] = (
                    label.missing_reason.value if label.missing_reason else ""
                )
        except Exception as exc:
            row["audit_failure_reason"] = f"{type(exc).__name__}: {exc}"
            audit_failures.append(
                {
                    "case_id": item.case_id,
                    "reason": row["audit_failure_reason"],
                }
            )
        records.append(row)

    missing_reason_counts = {
        horizon: dict(
            sorted(
                Counter(
                    row[f"{horizon}_missing_reason"]
                    for row in records
                    if row[f"{horizon}_availability"]
                    == MarketLabelAvailability.UNAVAILABLE.value
                ).items()
            )
        )
        for horizon in ("1d", "5d")
    }
    summary = {
        "readiness_version": LABEL_READINESS_VERSION,
        "official_case_count": len(records),
        "development_case_count": sum(
            row["dataset_split"] == "development" for row in records
        ),
        "validation_case_count": sum(
            row["dataset_split"] == "validation" for row in records
        ),
        "eod_ready_count": sum(bool(row["eod_available"]) for row in records),
        "eod_1d_session_ready_count": sum(
            bool(row["eod_1d_session_ready"]) for row in records
        ),
        "eod_5d_session_ready_count": sum(
            bool(row["eod_5d_session_ready"]) for row in records
        ),
        "base_price_ready_count": sum(
            bool(row["official_issue_price_available"]) for row in records
        ),
        "one_day_label_available_count": sum(
            row["1d_availability"] == MarketLabelAvailability.AVAILABLE.value
            for row in records
        ),
        "five_day_label_available_count": sum(
            row["5d_availability"] == MarketLabelAvailability.AVAILABLE.value
            for row in records
        ),
        "missing_reason_counts": missing_reason_counts,
        "audit_failure_count": len(audit_failures),
        "audit_failures": audit_failures,
        "coverage_content_hash": _canonical_hash(records),
        "provider_identity": identity,
        "eod_coverage_is_not_label_coverage": True,
        "raw_returns_only": True,
        "abnormal_return_policy_selected": False,
        "poor_performer_threshold_selected": False,
        "blind_2025_y_accessed": False,
    }
    return {"summary": summary, "records": records}
