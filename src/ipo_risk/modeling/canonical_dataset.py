"""PR-D canonical joins and fair M/P/O/PM/OM projections."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from ipo_risk.market.ipo_market_context_features import (
    IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
    IPO_MARKET_CONTEXT_FEATURE_POLICY_VERSION,
    IPO_MARKET_CONTEXT_FEATURE_SCHEMA_VERSION,
    IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER,
)
from ipo_risk.modeling.features import DOCUMENT_FEATURE_MANIFEST_V1
from ipo_risk.modeling.oracle_document import (
    ORACLE_DOCUMENT_FEATURE_MANIFEST_HASH,
    ORACLE_DOCUMENT_FEATURE_POLICY_VERSION,
    ORACLE_DOCUMENT_FEATURE_SCHEMA_VERSION,
    oracle_feature_names,
)
from ipo_risk.schemas.canonical_modeling import (
    V04CanonicalCohort,
    V04CanonicalFeatureBlock,
    V04CanonicalModelingDataset,
    V04CanonicalModelingRecord,
    V04CanonicalModelMatrix,
    V04FeatureComponent,
    V04ModelFeatureGroup,
    canonical_hash,
)
from ipo_risk.schemas.market import MarketDatasetSplit, MarketLabelAvailability
from ipo_risk.schemas.outcomes import FiveDayOutcomeTarget


def _artifact_hash(payload: Mapping[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "content_hash"}
    return canonical_hash(body)


def _require_artifact_hash(payload: Mapping[str, Any], *, label: str) -> str:
    declared = payload.get("content_hash")
    actual = _artifact_hash(payload)
    if declared != actual:
        raise ValueError(f"{label} content hash mismatch")
    return actual


def _expected_core_names() -> tuple[str, ...]:
    return tuple(
        name
        for raw_name in IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER
        for name in (raw_name, f"{raw_name}__missing")
    )


def production_document_block(
    artifact: Mapping[str, Any],
) -> V04CanonicalFeatureBlock:
    """Validate one frozen PR-A Production Document-X artifact."""

    artifact_hash = _require_artifact_hash(artifact, label="Production Document-X")
    names = tuple(artifact.get("feature_names") or ())
    values = tuple(artifact.get("feature_values") or ())
    expected_names = tuple(item.name for item in DOCUMENT_FEATURE_MANIFEST_V1.features)
    if artifact.get("feature_schema_version") != DOCUMENT_FEATURE_MANIFEST_V1.version:
        raise ValueError("Production Document-X schema version mismatch")
    if artifact.get("feature_manifest_hash") != DOCUMENT_FEATURE_MANIFEST_V1.content_hash():
        raise ValueError("Production Document-X manifest hash mismatch")
    if names != expected_names:
        raise ValueError("Production Document-X feature order mismatch")
    return V04CanonicalFeatureBlock(
        component=V04FeatureComponent.PRODUCTION_DOCUMENT,
        schema_version=DOCUMENT_FEATURE_MANIFEST_V1.version,
        manifest_hash=DOCUMENT_FEATURE_MANIFEST_V1.content_hash(),
        artifact_hash=artifact_hash,
        feature_names=names,
        feature_values=values,
    )


def market_core_block(artifact: Mapping[str, Any]) -> V04CanonicalFeatureBlock:
    """Validate one frozen PR-B 30-position Market-X Core artifact."""

    artifact_hash = _require_artifact_hash(artifact, label="Market-X Core")
    names = tuple(artifact.get("feature_names") or ())
    values = tuple(artifact.get("feature_values") or ())
    if artifact.get("core_feature_schema_version") != IPO_MARKET_CONTEXT_FEATURE_SCHEMA_VERSION:
        raise ValueError("Market-X Core schema version mismatch")
    if artifact.get("core_feature_policy_version") != IPO_MARKET_CONTEXT_FEATURE_POLICY_VERSION:
        raise ValueError("Market-X Core policy version mismatch")
    if artifact.get("core_feature_manifest_hash") != IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH:
        raise ValueError("Market-X Core manifest hash mismatch")
    if names != _expected_core_names():
        raise ValueError("Market-X Core feature order mismatch")
    return V04CanonicalFeatureBlock(
        component=V04FeatureComponent.MARKET_CORE,
        schema_version=IPO_MARKET_CONTEXT_FEATURE_SCHEMA_VERSION,
        policy_version=IPO_MARKET_CONTEXT_FEATURE_POLICY_VERSION,
        manifest_hash=IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
        artifact_hash=artifact_hash,
        feature_names=names,
        feature_values=values,
    )


def oracle_document_block(artifact: Mapping[str, Any]) -> V04CanonicalFeatureBlock:
    """Validate one frozen PR-A Oracle X artifact without promoting it to runtime."""

    artifact_hash = _require_artifact_hash(artifact, label="Oracle Document-X")
    names = tuple(artifact.get("feature_names") or ())
    values = tuple(artifact.get("feature_values") or ())
    if artifact.get("evaluation_only") is not True:
        raise ValueError("Oracle Document-X must remain evaluation-only")
    if artifact.get("oracle_feature_schema_version") != ORACLE_DOCUMENT_FEATURE_SCHEMA_VERSION:
        raise ValueError("Oracle Document-X schema version mismatch")
    if artifact.get("oracle_feature_policy_version") != ORACLE_DOCUMENT_FEATURE_POLICY_VERSION:
        raise ValueError("Oracle Document-X policy version mismatch")
    if artifact.get("oracle_manifest_hash") != ORACLE_DOCUMENT_FEATURE_MANIFEST_HASH:
        raise ValueError("Oracle Document-X manifest hash mismatch")
    if names != oracle_feature_names():
        raise ValueError("Oracle Document-X feature order mismatch")
    return V04CanonicalFeatureBlock(
        component=V04FeatureComponent.ORACLE_DOCUMENT,
        schema_version=ORACLE_DOCUMENT_FEATURE_SCHEMA_VERSION,
        policy_version=ORACLE_DOCUMENT_FEATURE_POLICY_VERSION,
        manifest_hash=ORACLE_DOCUMENT_FEATURE_MANIFEST_HASH,
        artifact_hash=artifact_hash,
        feature_names=names,
        feature_values=values,
        evaluation_only=True,
    )


def load_target_artifact(payload: Mapping[str, Any]) -> FiveDayOutcomeTarget:
    """Validate a PR-C target file and its declared content hash."""

    body = dict(payload)
    declared = body.pop("content_hash", None)
    target = FiveDayOutcomeTarget.model_validate(body)
    if declared != target.content_hash():
        raise ValueError("PR-C target content hash mismatch")
    return target


def _identity_mismatches(
    production: Mapping[str, Any],
    market_core: Mapping[str, Any],
    target: FiveDayOutcomeTarget,
    oracle: Mapping[str, Any] | None,
) -> list[str]:
    expected = {
        "case_id": production.get("case_id"),
        "stock_code": production.get("stock_code"),
        "cohort_year": production.get("cohort_year"),
        "listing_date": production.get("listing_date"),
        "dataset_split": production.get("dataset_split"),
    }
    sources: list[tuple[str, Mapping[str, Any]]] = [("market_core", market_core)]
    if oracle is not None:
        sources.append(("oracle", oracle))
    mismatches: list[str] = []
    for source_name, source in sources:
        for field, expected_value in expected.items():
            value = source.get(field)
            if source_name == "oracle" and field == "listing_date" and value is None:
                continue
            if value != expected_value:
                mismatches.append(f"{source_name}.{field}")
    target_values = {
        "case_id": target.case_id,
        "stock_code": target.stock_code,
        "cohort_year": target.cohort_year,
        "listing_date": target.listing_date,
        "dataset_split": target.dataset_split.value,
    }
    for field, expected_value in expected.items():
        if target_values[field] != expected_value:
            mismatches.append(f"target.{field}")
    return mismatches


class V04CanonicalDatasetBuilder:
    """Build the only PR-D Core-first canonical model-ready dataset."""

    def join_artifacts(
        self,
        *,
        production: Mapping[str, Any],
        market_core: Mapping[str, Any],
        target_payload: Mapping[str, Any],
        source_manifest_hash: str,
        oracle: Mapping[str, Any] | None = None,
        market_extended: V04CanonicalFeatureBlock | None = None,
    ) -> V04CanonicalModelingRecord:
        target = load_target_artifact(target_payload)
        if target.availability is not MarketLabelAvailability.AVAILABLE:
            raise ValueError("unavailable PR-C target cannot enter PR-D modeling data")
        mismatches = _identity_mismatches(production, market_core, target, oracle)
        if mismatches:
            raise ValueError("canonical artifact identity mismatch: " + ", ".join(mismatches))
        if not production.get("document_id"):
            raise ValueError("Production Document-X is missing document_id")
        listing_date = production.get("listing_date")
        if not listing_date:
            raise ValueError("canonical modeling row requires official listing_date")
        if market_extended is not None and (
            market_extended.component is not V04FeatureComponent.MARKET_EXTENDED
        ):
            raise ValueError("optional Extended block has the wrong component")
        return V04CanonicalModelingRecord(
            case_id=str(production["case_id"]),
            document_id=str(production["document_id"]),
            stock_code=str(production["stock_code"]),
            cohort_year=int(production["cohort_year"]),
            listing_date=listing_date,
            dataset_split=production["dataset_split"],
            market_core=market_core_block(market_core),
            production_document=production_document_block(production),
            market_extended=market_extended,
            oracle_document=(oracle_document_block(oracle) if oracle is not None else None),
            target=target,
            source_manifest_hash=source_manifest_hash,
        )

    def build(
        self,
        records: Iterable[V04CanonicalModelingRecord],
        *,
        cohort: V04CanonicalCohort,
        dataset_split: MarketDatasetSplit,
    ) -> V04CanonicalModelingDataset:
        rows = sorted(records, key=lambda row: row.case_id)
        if not rows:
            raise ValueError("canonical modeling dataset cannot be empty")
        if any(row.dataset_split is not dataset_split for row in rows):
            raise ValueError("canonical builder received a different split")
        if cohort is V04CanonicalCohort.ORACLE_INTERSECTION:
            rows = [row for row in rows if row.oracle_document is not None]
            if not rows:
                raise ValueError("Oracle intersection is empty")
        source_hashes = {row.source_manifest_hash for row in rows}
        policy_hashes = {row.target.policy_hash for row in rows}
        threshold_hashes = {row.target.threshold_hash for row in rows}
        if len(source_hashes) != 1:
            raise ValueError("canonical records use different source manifests")
        if len(policy_hashes) != 1 or len(threshold_hashes) != 1:
            raise ValueError("canonical records use different target policies")
        return V04CanonicalModelingDataset(
            cohort=cohort,
            dataset_split=dataset_split,
            source_manifest_hash=next(iter(source_hashes)),
            target_policy_hash=next(iter(policy_hashes)),
            target_threshold_hash=next(iter(threshold_hashes)),
            records=tuple(rows),
        )


def _component_order(
    group: V04ModelFeatureGroup,
    *,
    include_extended: bool,
) -> tuple[V04FeatureComponent, ...]:
    market = (V04FeatureComponent.MARKET_CORE,) + (
        (V04FeatureComponent.MARKET_EXTENDED,) if include_extended else ()
    )
    return {
        V04ModelFeatureGroup.M: market,
        V04ModelFeatureGroup.P: (V04FeatureComponent.PRODUCTION_DOCUMENT,),
        V04ModelFeatureGroup.O: (V04FeatureComponent.ORACLE_DOCUMENT,),
        V04ModelFeatureGroup.PM: market + (V04FeatureComponent.PRODUCTION_DOCUMENT,),
        V04ModelFeatureGroup.OM: market + (V04FeatureComponent.ORACLE_DOCUMENT,),
    }[group]


def _block_for(
    row: V04CanonicalModelingRecord,
    component: V04FeatureComponent,
) -> V04CanonicalFeatureBlock:
    block = {
        V04FeatureComponent.MARKET_CORE: row.market_core,
        V04FeatureComponent.MARKET_EXTENDED: row.market_extended,
        V04FeatureComponent.PRODUCTION_DOCUMENT: row.production_document,
        V04FeatureComponent.ORACLE_DOCUMENT: row.oracle_document,
    }[component]
    if block is None:
        raise ValueError(f"{row.case_id} is missing required {component.value} X")
    return block


def project_model_matrix(
    dataset: V04CanonicalModelingDataset,
    group: V04ModelFeatureGroup,
    *,
    include_extended: bool = False,
) -> V04CanonicalModelMatrix:
    """Project one dataset with a frozen component order and prefixed names."""

    if group in {V04ModelFeatureGroup.O, V04ModelFeatureGroup.OM} and (
        dataset.cohort is not V04CanonicalCohort.ORACLE_INTERSECTION
    ):
        raise ValueError("Oracle feature groups require the Oracle intersection cohort")
    order = _component_order(group, include_extended=include_extended)
    first_blocks = [_block_for(dataset.records[0], component) for component in order]
    feature_names = tuple(
        f"{block.component.value}__{name}"
        for block in first_blocks
        for name in block.feature_names
    )
    component_manifest = [
        {
            "component": block.component.value,
            "schema_version": block.schema_version,
            "policy_version": block.policy_version,
            "manifest_hash": block.manifest_hash,
            "feature_names": block.feature_names,
        }
        for block in first_blocks
    ]
    rows: list[tuple[int | float | None, ...]] = []
    raw_returns = []
    binary_targets = []
    for record in dataset.records:
        blocks = [_block_for(record, component) for component in order]
        for expected, actual in zip(first_blocks, blocks, strict=True):
            if (
                actual.schema_version != expected.schema_version
                or actual.policy_version != expected.policy_version
                or actual.manifest_hash != expected.manifest_hash
                or actual.feature_names != expected.feature_names
            ):
                raise ValueError(f"feature manifest drift for {record.case_id}")
        rows.append(tuple(value for block in blocks for value in block.feature_values))
        assert record.target.raw_return_5d is not None
        assert record.target.poor_performer_5d is not None
        raw_returns.append(record.target.raw_return_5d)
        binary_targets.append(record.target.poor_performer_5d)
    return V04CanonicalModelMatrix(
        cohort=dataset.cohort,
        dataset_split=dataset.dataset_split,
        feature_group=group,
        source_dataset_hash=dataset.content_hash(),
        feature_manifest_hash=canonical_hash(component_manifest),
        target_policy_hash=dataset.target_policy_hash,
        target_threshold_hash=dataset.target_threshold_hash,
        case_ids=tuple(row.case_id for row in dataset.records),
        feature_names=feature_names,
        feature_values=tuple(rows),
        raw_return_5d=tuple(raw_returns),
        poor_performer_5d=tuple(binary_targets),
    )


def hash_source_manifests(paths: Sequence[Path]) -> str:
    """Bind PR-D to the exact reviewed PR-A/PR-B/PR-C freeze manifests."""

    entries = []
    for path in paths:
        if not path.is_file():
            raise ValueError(f"missing upstream freeze manifest: {path}")
        content = path.read_bytes()
        entries.append(
            {
                "name": path.name,
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    names = [entry["name"] for entry in entries]
    if len(names) != len(set(names)):
        raise ValueError("upstream freeze manifest names must be unique")
    return canonical_hash(sorted(entries, key=lambda item: item["name"]))

