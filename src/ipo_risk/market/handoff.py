"""Versioned Market-X feature handoff for the model lane.

The model owner must not recompute Market-X. This module projects whatever the
market channel produced -- a frozen PR-B artifact or a dynamic point-in-time
build -- into one stable payload: case identity, the frozen feature order, the
values, an explicit missingness mask with reasons, the PIT cutoff and the source
provenance, all bound by a content hash.

The missingness mask is the point of the contract. A model input built from this
payload can tell "this feature is zero" from "this feature is unknown", which is
the distinction the whole market lane exists to preserve.
"""

from __future__ import annotations

from typing import Any

from ipo_risk.market.ipo_market_context_features import (
    IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
    IPO_MARKET_CONTEXT_FEATURE_POLICY_VERSION,
    IPO_MARKET_CONTEXT_FEATURE_SCHEMA_VERSION,
    IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER,
    content_hash,
    vectorize_ipo_market_context,
)
from ipo_risk.schemas.final_supervision import ChannelStatus, MarketContextView

MARKET_FEATURE_HANDOFF_SCHEMA_VERSION = "v046_market_feature_handoff_v1"


class MarketFeatureHandoffError(ValueError):
    """The market view cannot be projected into a model-ready handoff."""


def build_market_feature_handoff(view: MarketContextView) -> dict[str, Any]:
    """Project a governed market view into the model lane's stable contract."""

    if view.status is not ChannelStatus.AVAILABLE:
        raise MarketFeatureHandoffError(
            f"market channel is {view.status.value}, not available"
        )
    if view.feature_manifest_hash != IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH:
        raise MarketFeatureHandoffError(
            "market view does not carry the frozen Market-X Core manifest hash"
        )

    by_name = {item.name: item for item in view.observations}
    missing_names = set(IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER) - set(by_name)
    if missing_names:
        raise MarketFeatureHandoffError(
            "market view omits frozen Core features: "
            + ", ".join(sorted(missing_names))
        )

    raw: dict[str, float | int | None] = {}
    missing_reasons: dict[str, str] = {}
    for name in IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER:
        observation = by_name[name]
        if observation.availability == "available":
            raw[name] = observation.value
            continue
        raw[name] = None
        missing_reasons[name] = observation.missing_reason or "unspecified"

    names, vector = vectorize_ipo_market_context(raw)
    provenance = dict(view.provenance)
    body: dict[str, Any] = {
        "schema_version": MARKET_FEATURE_HANDOFF_SCHEMA_VERSION,
        "core_feature_schema_version": IPO_MARKET_CONTEXT_FEATURE_SCHEMA_VERSION,
        "core_feature_policy_version": IPO_MARKET_CONTEXT_FEATURE_POLICY_VERSION,
        "core_feature_manifest_hash": IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
        "case_id": provenance.get("case_id"),
        "stock_code": provenance.get("stock_code"),
        "listing_date": provenance.get("listing_date"),
        "dataset_split": provenance.get("dataset_split"),
        "market_runtime_path": provenance.get("runtime_path"),
        "feature_pipeline": provenance.get("feature_pipeline"),
        "pit_cutoff_date": provenance.get("pit_cutoff_date")
        or provenance.get("listing_date"),
        "cutoff_semantics": provenance.get("cutoff_semantics"),
        "feature_names": list(names),
        "feature_values": list(vector),
        "available_features": [
            name for name in IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER
            if raw[name] is not None
        ],
        "missing_features": sorted(missing_reasons),
        "missing_mask": {
            name: int(raw[name] is None)
            for name in IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER
        },
        "missing_reasons": dict(sorted(missing_reasons.items())),
        "source_provenance": provenance.get("source_provenance"),
        "artifact_content_hash": provenance.get("artifact_content_hash"),
        "extended_observations": [
            {
                "name": item.name,
                "value": item.value,
                "availability": item.availability,
                "missing_reason": item.missing_reason,
                "source": item.source,
            }
            for item in view.observations
            if item.name not in set(IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER)
        ],
    }
    body["content_hash"] = content_hash(body)
    return body
