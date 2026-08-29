"""Market context providers for the PR-G Final Supervisor.

Deliberately *not* ``RiskAgent`` implementations.  The market channel is an
explanatory input, not a risk producer; giving it the ``RiskAgent`` shape would
let it inject unverified ``RiskItem`` values into the verified set, which is
precisely the failure mode the governance boundary exists to prevent.

Availability is decided by the snapshot's ``source``, never by whether its fields
happen to be non-null.  ``MockMarketDataProvider`` returns fixture numbers; a
renderer that treated those as market context would be fabricating data.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import date
from pathlib import Path

from ipo_risk.agents.base import MarketContextProvider
from ipo_risk.market.ipo_market_context_features import (
    IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
    IPO_MARKET_CONTEXT_FEATURE_POLICY_VERSION,
    IPO_MARKET_CONTEXT_FEATURE_UNITS,
    IPO_MARKET_CONTEXT_FEATURE_SCHEMA_VERSION,
    IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER,
    content_hash,
    vectorize_ipo_market_context,
)
from ipo_risk.market.prior_ipo_history import line_ending_agnostic_hashes
from ipo_risk.schemas import IPOProfile, MarketSnapshot
from ipo_risk.schemas.final_supervision import ChannelStatus, MarketContextView, MarketObservation
from ipo_risk.schemas.market import expected_market_split
from ipo_risk.schemas.market_features import MARKET_RAW_FEATURE_ORDER

# Retired in PR-G: PR-B is COMPLETE / FROZEN, so no gate blocks this channel any
# more.  What is missing is a governed runtime adapter, which is a capability
# statement, not a gate statement.
MOCK_SOURCE = "mock"
UNAVAILABLE_SOURCE = "unavailable"
LEGACY_PIPELINE_NOTE = "legacy_market_snapshot_not_v04_market_x"

# name -> (unit, derivation, reason when the governed source cannot supply it)
_OBSERVATION_SPECS: dict[str, tuple[str, str, str]] = {
    "hsi_return_5d": ("ratio", "HSI close(t)/close(t-5) - 1 over observed sessions", "missing_benchmark"),
    "hsi_return_20d": ("ratio", "HSI close(t)/close(t-20) - 1 over observed sessions", "missing_benchmark"),
    "industry_return_5d": ("ratio", "industry benchmark close(t)/close(t-5) - 1", "missing_industry_series"),
    "industry_return_20d": ("ratio", "industry benchmark close(t)/close(t-20) - 1", "missing_industry_series"),
    "recent_ipo_break_rate": ("ratio", "share of recent prior IPOs closing below offer on day one", "no_recent_ipo_sample"),
    "recent_ipo_return_5d": ("ratio", "mean 5-session return of recent prior IPOs", "no_recent_ipo_sample"),
    "market_turnover": ("currency", "aggregate market turnover at the observation date", "missing_turnover_source"),
    "market_volatility": ("ratio", "realised volatility of the benchmark over the observation window", "missing_benchmark"),
    "sentiment_score": ("index", "composite pre-listing sentiment index", "source_unavailable"),
}

_CORE_UNITS = IPO_MARKET_CONTEXT_FEATURE_UNITS

_EXTENDED_ONLY_RAW_FEATURE_ORDER = tuple(
    name for name in MARKET_RAW_FEATURE_ORDER if name not in _CORE_UNITS
)
_EXTENDED_UNITS: dict[str, str] = {
    "hsi_return_5d": "ratio",
    "hsi_return_20d": "ratio",
    "industry_return_5d": "ratio",
    "industry_return_20d": "ratio",
    "market_turnover_20d_mean": "currency",
    "market_volatility_20d": "ratio",
}
_INDUSTRY_MISSING_REASONS = {
    "INDUSTRY_MAPPING_PIT_BLOCKED",
    "MISSING_INDUSTRY_CLASSIFICATION",
}
_FROZEN_PR_B_LISTING_YEARS = frozenset({2020, 2021, 2022, 2023, 2024})

# Machine-readable failure buckets for the coverage audit. A report that has to
# grep an exception message to tell an identity mismatch from a missing file is
# a report that will misclassify the first time a message is reworded.
FAILURE_MISSING_ARTIFACT = "missing_or_unreadable_artifact"
FAILURE_IDENTITY_MISMATCH = "identity_mismatch"
FAILURE_PROVENANCE = "provenance_failure"
FAILURE_SCHEMA_OR_HASH = "schema_or_hash_failure"
FAILURE_OTHER = "validation_failure"

_IDENTITY_MARKERS = (
    "does not match the frozen PR-B contract",
    "dataset_split does not match",
    "resolves to multiple official IPO cases",
    "Extended readiness",
    "does not resolve to exactly one",
)
_PROVENANCE_MARKERS = (
    "provenance hash",
    "source_provenance is missing",
)
_SCHEMA_MARKERS = (
    "content_hash",
    "raw feature membership",
    "feature vector is not a lossless projection",
    "is not finite",
    "availability flags",
    "must remain null",
    "value is incomplete",
    "governed PIT-blocked",
)


def classify_frozen_failure(exc: Exception) -> str:
    """Bucket a frozen-projection failure without parsing it at the call site."""

    if isinstance(exc, (OSError, json.JSONDecodeError)):
        return FAILURE_MISSING_ARTIFACT
    detail = str(exc)
    for marker in _IDENTITY_MARKERS:
        if marker in detail:
            return FAILURE_IDENTITY_MISMATCH
    for marker in _PROVENANCE_MARKERS:
        if marker in detail:
            return FAILURE_PROVENANCE
    for marker in _SCHEMA_MARKERS:
        if marker in detail:
            return FAILURE_SCHEMA_OR_HASH
    return FAILURE_OTHER


class UnsupportedNewCaseMarketContextProvider:
    """Honest dynamic-path placeholder for cases outside frozen PR-B.

    A deployable dynamic provider must be backed by governed, point-in-time
    reference inputs.  The current public deployment has no licensed-safe HSI
    or Extended lookup configured, so this provider exposes that capability
    gap without treating a valid new IPO as a broken frozen artifact.
    """

    name = "dynamic_new_case_market_x"

    def context(
        self,
        profile: IPOProfile,
        market: MarketSnapshot | None = None,
    ) -> MarketContextView:
        del market
        identity_complete = bool(profile.stock_code and profile.listing_date is not None)
        reason_code = (
            "unsupported_new_case"
            if identity_complete
            else "new_case_identity_incomplete"
        )
        reason = (
            "dynamic Market-X inputs are not configured for this non-frozen IPO"
            if identity_complete
            else "dynamic Market-X requires stock_code and listing_date for a non-frozen IPO"
        )
        return MarketContextView(
            status=ChannelStatus.UNAVAILABLE,
            reason=reason,
            provenance={
                "feature_pipeline": self.name,
                "runtime_path": "dynamic_new_case",
                "reason_code": reason_code,
                "frozen_cohort_lookup": "not_applicable",
                "frozen_artifact_read_attempted": False,
                "stock_code": profile.stock_code,
                "listing_date": (
                    profile.listing_date.isoformat()
                    if profile.listing_date is not None
                    else None
                ),
                "cutoff_semantics": "market_data_strictly_before_listing_date",
                "dynamic_provider": "unconfigured",
            },
        )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class GovernedPRBMarketContextProvider:
    """Load governed point-in-time Core and optional Extended projections.

    The provider does not calculate or impute features.  It validates and
    presents the already frozen 30-position PR-B artifact, keeping every
    unavailable raw feature explicit instead of replacing it with zero.  When
    supplied, the local C-lane readiness audit adds only the six Extended names
    not already represented in Core; it does not alter either frozen manifest.
    """

    name = "governed_pr_b_core"

    def __init__(
        self,
        *,
        feature_dir: str | Path,
        official_bridge_path: str | Path,
        extended_readiness_path: str | Path | None = None,
        new_case_provider: MarketContextProvider | None = None,
    ) -> None:
        self.feature_dir = Path(feature_dir)
        self.official_bridge_path = Path(official_bridge_path)
        self.extended_readiness_path = (
            Path(extended_readiness_path) if extended_readiness_path else None
        )
        self.new_case_provider = (
            new_case_provider or UnsupportedNewCaseMarketContextProvider()
        )

    def context(self, profile: IPOProfile, market: MarketSnapshot | None = None) -> MarketContextView:
        frozen_artifact_read_attempted = False
        try:
            row = self._official_row(profile)
            if row is None:
                return self.new_case_provider.context(profile, market)
            # PR-B is the governed frozen source; the legacy snapshot is not
            # mixed into a known official-cohort projection.
            del market
            frozen_artifact_read_attempted = True
            artifact = self._artifact(row)
            observations = self._observations(artifact)
            extended_row = None
            if self.extended_readiness_path is not None:
                extended_row = self._extended_row(row)
                observations += self._extended_observations(extended_row)
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            detail = str(exc) if isinstance(exc, (ValueError, KeyError, TypeError)) else "artifact_io_or_json_error"
            return MarketContextView(
                status=ChannelStatus.UNAVAILABLE_ERROR,
                reason=f"governed PR-B Market-X projection failed validation: {detail}",
                provenance={
                    "feature_pipeline": self.name,
                    "runtime_path": "frozen",
                    "frozen_artifact_read_attempted": frozen_artifact_read_attempted,
                    "failure_code": classify_frozen_failure(exc),
                },
            )
        return MarketContextView(
            status=ChannelStatus.AVAILABLE,
            reason=(
                "validated frozen PR-B Market-X Core and governed Extended readiness projection"
                if extended_row is not None
                else "validated frozen PR-B Market-X Core projection"
            ),
            observations=observations,
            feature_manifest_hash=IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
            provenance={
                "feature_pipeline": self.name,
                "runtime_path": "frozen",
                "frozen_artifact_read_attempted": True,
                "case_id": artifact["case_id"],
                "stock_code": artifact["stock_code"],
                "listing_date": artifact["listing_date"],
                "dataset_split": artifact["dataset_split"],
                "artifact_content_hash": artifact["content_hash"],
                "cutoff_semantics": artifact["cutoff_semantics"],
                "source_provenance": artifact["source_provenance"],
                "extended_readiness_sha256": (
                    _sha256_file(self.extended_readiness_path)
                    if self.extended_readiness_path is not None
                    else None
                ),
            },
        )

    def _official_row(self, profile: IPOProfile) -> dict[str, str] | None:
        if not profile.stock_code or profile.listing_date is None:
            return None
        with self.official_bridge_path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {"case_id", "stock_code_wind", "official_listed_date"}
            missing = required - set(reader.fieldnames or ())
            if missing:
                raise ValueError(
                    "official bridge missing fields: " + ", ".join(sorted(missing))
                )
            rows = [
                row for row in reader
                if row.get("stock_code_wind") == profile.stock_code
                and row.get("official_listed_date") == profile.listing_date.isoformat()
            ]
        if len(rows) > 1:
            raise ValueError("profile resolves to multiple official IPO cases")
        if not rows:
            return None
        row = rows[0]
        try:
            listing_year = date.fromisoformat(row["official_listed_date"]).year
        except (KeyError, ValueError) as exc:
            raise ValueError("official bridge listing date is invalid") from exc
        if listing_year not in _FROZEN_PR_B_LISTING_YEARS:
            return None
        return row

    def _artifact(self, row: dict[str, str]) -> dict[str, object]:
        path = self.feature_dir / f"{row['case_id']}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        expected = {
            "case_id": row["case_id"],
            "stock_code": row["stock_code_wind"],
            "listing_date": row["official_listed_date"],
            "core_feature_schema_version": IPO_MARKET_CONTEXT_FEATURE_SCHEMA_VERSION,
            "core_feature_policy_version": IPO_MARKET_CONTEXT_FEATURE_POLICY_VERSION,
            "core_feature_manifest_hash": IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
        }
        for key, value in expected.items():
            if payload.get(key) != value:
                raise ValueError(f"{key} does not match the frozen PR-B contract")
        expected_split = expected_market_split(
            int(row["official_listed_date"][:4])
        ).value
        if payload.get("dataset_split") != expected_split:
            raise ValueError("dataset_split does not match the official cohort")
        provenance = payload.get("source_provenance")
        if not isinstance(provenance, dict):
            raise ValueError("source_provenance is missing")
        if provenance.get("official_bridge_sha256") not in line_ending_agnostic_hashes(
            self.official_bridge_path
        ):
            raise ValueError("official bridge provenance hash does not match")
        stored_hash = payload.get("content_hash")
        body = dict(payload)
        body.pop("content_hash", None)
        if stored_hash != content_hash(body):
            raise ValueError("artifact content_hash does not match")
        raw = payload.get("raw_values")
        if not isinstance(raw, dict) or set(raw) != set(IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER):
            raise ValueError("raw feature membership does not match the frozen manifest")
        names, values = vectorize_ipo_market_context(raw)
        if payload.get("feature_names") != list(names) or payload.get("feature_values") != list(values):
            raise ValueError("feature vector is not a lossless projection of raw_values")
        return payload

    def _extended_row(self, official_row: dict[str, str]) -> dict[str, str]:
        assert self.extended_readiness_path is not None
        with self.extended_readiness_path.open(encoding="utf-8-sig", newline="") as handle:
            rows = [
                row for row in csv.DictReader(handle)
                if row.get("case_id") == official_row["case_id"]
            ]
        if len(rows) != 1:
            raise ValueError("case does not resolve to exactly one Extended readiness row")
        row = rows[0]
        expected = {
            "stock_code": official_row["stock_code_wind"],
            "listing_date": official_row["official_listed_date"],
            "dataset_split": expected_market_split(
                int(official_row["official_listed_date"][:4])
            ).value,
        }
        for key, value in expected.items():
            if row.get(key) != value:
                raise ValueError(f"Extended readiness {key} does not match the official cohort")
        return row

    @staticmethod
    def _extended_observations(row: dict[str, str]) -> tuple[MarketObservation, ...]:
        observations: list[MarketObservation] = []
        for name in _EXTENDED_ONLY_RAW_FEATURE_ORDER:
            available = row.get(f"{name}__available")
            missing = row.get(f"{name}__missing")
            if available not in {"True", "False"} or missing not in {"True", "False"}:
                raise ValueError(f"{name} Extended availability flags are invalid")
            is_available = available == "True"
            if is_available == (missing == "True"):
                raise ValueError(f"{name} Extended availability flags are not complementary")
            raw_value = row.get(name, "")
            missing_reason = row.get(f"{name}__missing_reason", "")
            if is_available:
                if raw_value == "" or missing_reason:
                    raise ValueError(f"{name} available Extended value is incomplete")
                numeric = float(raw_value)
                if not math.isfinite(numeric):
                    raise ValueError(f"{name} Extended value is not finite")
                observations.append(MarketObservation(
                    name=name,
                    value=numeric,
                    unit=_EXTENDED_UNITS[name],
                    availability="available",
                    derivation="governed point-in-time Market-X Extended readiness feature",
                    source="v04_c_extended_readiness",
                ))
                continue
            if raw_value != "" or not missing_reason:
                raise ValueError(f"{name} unavailable Extended value must remain null with a reason")
            if name.startswith("industry_return_") and missing_reason not in _INDUSTRY_MISSING_REASONS:
                raise ValueError(f"{name} does not use the governed PIT-blocked industry semantics")
            observations.append(MarketObservation(
                name=name,
                availability="unavailable",
                missing_reason=missing_reason,
                source="v04_c_extended_readiness",
            ))
        return tuple(observations)

    @staticmethod
    def _observations(artifact: dict[str, object]) -> tuple[MarketObservation, ...]:
        raw = artifact["raw_values"]
        provenance = artifact["source_provenance"]
        assert isinstance(raw, dict) and isinstance(provenance, dict)
        rows: list[MarketObservation] = []
        for name in IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER:
            value = raw[name]
            if value is None:
                rows.append(MarketObservation(
                    name=name,
                    availability="unavailable",
                    missing_reason="insufficient_governed_prelisting_history",
                    source="pr_b_market_x_core",
                ))
                continue
            numeric = float(value)
            if not math.isfinite(numeric):
                raise ValueError(f"{name} is not finite")
            rows.append(MarketObservation(
                name=name,
                value=numeric,
                unit=_CORE_UNITS[name],
                availability="available",
                derivation="frozen PR-B point-in-time Market-X Core feature",
                source="pr_b_market_x_core",
            ))
        return tuple(rows)


class GatePendingMarketContextProvider:
    """Historical reference implementation; reports the channel as unconfigured."""

    name = "gate_pending"

    def context(self, profile: IPOProfile, market: MarketSnapshot | None = None) -> MarketContextView:
        return MarketContextView(
            status=ChannelStatus.DISABLED,
            reason="market context is not configured in this runtime",
        )


class SnapshotMarketContextProvider:
    """Explains the market snapshot the workflow already loaded, or its absence."""

    name = "snapshot"

    def context(self, profile: IPOProfile, market: MarketSnapshot | None = None) -> MarketContextView:
        if market is None:
            return MarketContextView(
                status=ChannelStatus.UNAVAILABLE_ERROR,
                reason="the market snapshot node did not produce a snapshot",
                provenance={"feature_pipeline": LEGACY_PIPELINE_NOTE},
            )
        metadata = market.metadata or {}
        if market.source == UNAVAILABLE_SOURCE or metadata.get("available") is False:
            return MarketContextView(
                status=ChannelStatus.UNAVAILABLE_ERROR,
                # The provider's own words, not a paraphrase.
                reason=str(metadata.get("reason") or "the market data provider reported no governed snapshot"),
                provenance={"feature_pipeline": LEGACY_PIPELINE_NOTE, "source": market.source},
            )
        if market.source == MOCK_SOURCE:
            return MarketContextView(
                status=ChannelStatus.DISABLED,
                reason="the mock market snapshot is a fixture, not market data",
                provenance={"feature_pipeline": LEGACY_PIPELINE_NOTE, "source": market.source},
            )
        return MarketContextView(
            status=ChannelStatus.AVAILABLE,
            reason=f"derived from the {market.source} pre-listing market snapshot",
            observations=self._observations(market),
            # Deliberately None: a snapshot-derived view did not come from the
            # PR-B Market-X pipeline, and stamping its manifest hash here would
            # claim a lineage this value does not have.
            feature_manifest_hash=None,
            provenance={
                "feature_pipeline": LEGACY_PIPELINE_NOTE,
                "source": market.source,
                "observation_date": market.observation_date.isoformat() if market.observation_date else None,
            },
        )

    @staticmethod
    def _observations(market: MarketSnapshot) -> tuple[MarketObservation, ...]:
        rows = []
        for name, (unit, derivation, missing_reason) in _OBSERVATION_SPECS.items():
            value = getattr(market, name, None)
            if value is None:
                rows.append(MarketObservation(
                    name=name, availability="unavailable",
                    missing_reason=missing_reason, source=market.source))
            else:
                rows.append(MarketObservation(
                    name=name, value=float(value), unit=unit, availability="available",
                    derivation=derivation, source=market.source))
        return tuple(rows)
