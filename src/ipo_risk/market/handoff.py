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

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ipo_risk.market.ipo_market_context_features import (
    IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
    IPO_MARKET_CONTEXT_FEATURE_POLICY_VERSION,
    IPO_MARKET_CONTEXT_FEATURE_SCHEMA_VERSION,
    IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER,
    content_hash,
    vectorize_ipo_market_context,
)
from ipo_risk.market.prior_ipo_history import line_ending_agnostic_hashes
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


MARKET_HANDOFF_BINDING_VERSION = "v046_market_handoff_model_binding_v1"
_PR_B_MANIFEST_NAME = "v04_pr_b_market_x_core_manifest.json"
_PR_D_MANIFEST_NAME = "v04_pr_d_input_binding_manifest.json"
_NOT_ASSERTED = "not_asserted"


class MarketHandoffBindingError(ValueError):
    """A handoff cannot be bound to the frozen model's feature identity."""


def verify_market_handoff_binding(
    handoff: Mapping[str, Any],
    *,
    frozen_dir: str | Path,
) -> dict[str, Any]:
    """Prove a handoff carries the identity the frozen model was fitted on.

    The model lane must not have to take a dynamic case on trust. A frozen
    artifact and a dynamic rebuild are interchangeable model inputs only if the
    feature schema, the policy, the manifest hash and the vector width are the
    same object -- and, where the handoff asserts them, if the EOD extract and
    the prior-IPO universe boundary are the same ones the frozen Market-X was
    built from.

    Every mismatch raises. A handoff that cannot prove its lineage is not
    downgraded to a warning, because a silently mis-bound feature vector is
    exactly the failure the frozen model identity exists to prevent.
    """

    frozen_root = Path(frozen_dir)
    pr_b = _read_frozen_manifest(frozen_root / _PR_B_MANIFEST_NAME)

    checks: dict[str, str] = {}
    _bind(
        checks,
        "core_feature_schema_version",
        handoff.get("core_feature_schema_version"),
        pr_b.get("feature_schema_version"),
    )
    _bind(
        checks,
        "core_feature_policy_version",
        handoff.get("core_feature_policy_version"),
        pr_b.get("feature_policy_version"),
    )
    _bind(
        checks,
        "core_feature_manifest_hash",
        handoff.get("core_feature_manifest_hash"),
        pr_b.get("feature_manifest_hash"),
    )
    _bind(
        checks,
        "feature_position_count",
        len(handoff.get("feature_names") or ()),
        pr_b.get("feature_position_count"),
    )

    provenance = handoff.get("source_provenance")
    provenance = provenance if isinstance(provenance, Mapping) else {}
    checks["ipo_eod_sha256"] = _bind_optional(
        provenance.get("ipo_eod_sha256"),
        (pr_b.get("governed_eod") or {}).get("raw_eod_sha256"),
        label="ipo_eod_sha256",
    )
    checks["prior_ipo_history_start_date"] = _bind_optional(
        provenance.get("prior_ipo_history_start_date")
        or provenance.get("history_start_date"),
        pr_b.get("prior_ipo_history_start_date"),
        label="prior_ipo_history_start_date",
    )

    binding: dict[str, Any] = {
        "binding_version": MARKET_HANDOFF_BINDING_VERSION,
        "market_runtime_path": handoff.get("market_runtime_path"),
        "case_id": handoff.get("case_id"),
        "listing_date": handoff.get("listing_date"),
        "frozen_pr_b_manifest": _PR_B_MANIFEST_NAME,
        "frozen_pr_b_manifest_sha256": _sha256_file(frozen_root / _PR_B_MANIFEST_NAME),
        "frozen_feature_manifest_hash": pr_b.get("feature_manifest_hash"),
        "frozen_raw_feature_count": pr_b.get("raw_feature_count"),
        "frozen_feature_position_count": pr_b.get("feature_position_count"),
        "checks": checks,
        "available_feature_count": len(handoff.get("available_features") or ()),
        "missing_feature_count": len(handoff.get("missing_features") or ()),
        "handoff_content_hash": handoff.get("content_hash"),
    }
    binding.update(_pr_d_chain(frozen_root))
    # A model input is buildable from any validated handoff; the missing mask,
    # not the availability count, is what keeps unknown distinct from zero.
    binding["model_input_ready"] = True
    return binding


def _read_frozen_manifest(path: Path) -> Mapping[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MarketHandoffBindingError(
            f"frozen manifest is unreadable: {path.name}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise MarketHandoffBindingError(f"frozen manifest is not an object: {path.name}")
    return payload


def _bind(checks: dict[str, str], label: str, actual: Any, frozen: Any) -> None:
    if frozen is None:
        raise MarketHandoffBindingError(f"frozen manifest does not declare {label}")
    if actual != frozen:
        raise MarketHandoffBindingError(
            f"{label} does not match the frozen model identity: "
            f"handoff={actual!r} frozen={frozen!r}"
        )
    checks[label] = "match"


def _bind_optional(actual: Any, frozen: Any, *, label: str) -> str:
    """Assert an optional lineage field, or record that it was not claimed."""

    if actual is None:
        return _NOT_ASSERTED
    if frozen is None:
        raise MarketHandoffBindingError(f"frozen manifest does not declare {label}")
    if actual != frozen:
        raise MarketHandoffBindingError(
            f"{label} does not match the frozen Market-X lineage: "
            f"handoff={actual!r} frozen={frozen!r}"
        )
    return "match"


def _pr_d_chain(frozen_root: Path) -> dict[str, Any]:
    """Confirm the model's own input binding still points at this PR-B manifest."""

    pr_d_path = frozen_root / _PR_D_MANIFEST_NAME
    if not pr_d_path.is_file():
        return {"pr_d_input_binding": "not_present"}
    pr_d = _read_frozen_manifest(pr_d_path)
    upstream = (pr_d.get("upstream_manifests") or {}).get("pr_b") or {}
    declared = upstream.get("sha256")
    # PR-D recorded this hash from a Windows checkout; Git stores the same
    # manifest with LF endings. Only the newline representation may differ.
    candidates = line_ending_agnostic_hashes(frozen_root / _PR_B_MANIFEST_NAME)
    if declared is not None and declared not in candidates:
        raise MarketHandoffBindingError(
            "the model input binding was built against a different PR-B manifest"
        )
    return {
        "pr_d_input_binding": "match" if declared else "not_asserted",
        "pr_d_binding_version": pr_d.get("binding_version"),
        "pr_d_market_core_count": (
            (pr_d.get("components") or {}).get("market_core") or {}
        ).get("count"),
        "pr_d_market_extended_status": pr_d.get("market_extended_status"),
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
