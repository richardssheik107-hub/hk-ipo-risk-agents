from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal

import pytest

from ipo_risk.market.ipo_market_context_features import (
    IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
    IPO_MARKET_CONTEXT_FEATURE_POLICY_VERSION,
    IPO_MARKET_CONTEXT_FEATURE_SCHEMA_VERSION,
    IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER,
)
from ipo_risk.market.outcomes import FiveDayOutcomeBuilder
from ipo_risk.modeling.canonical_dataset import (
    V04CanonicalDatasetBuilder,
    project_model_matrix,
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
    V04ModelFeatureGroup,
    canonical_hash,
)
from ipo_risk.schemas.market import (
    MarketBasePriceSource,
    MarketDataProvenance,
    MarketDatasetSplit,
    MarketLabelAvailability,
    MarketLabelHorizon,
    MarketLabelMissingReason,
    MarketOutcomeLabel,
)


def _with_hash(body):
    return body | {"content_hash": canonical_hash(body)}


def _identity(case_id: str, year: int, code: str):
    return {
        "case_id": case_id,
        "stock_code": code,
        "cohort_year": year,
        "listing_date": f"{year}-01-02",
        "dataset_split": "development" if year <= 2023 else "validation",
    }


def _production(case_id="ipo_2023_0001", year=2023, code="0001.HK"):
    names = tuple(item.name for item in DOCUMENT_FEATURE_MANIFEST_V1.features)
    return _with_hash(
        _identity(case_id, year, code)
        | {
            "document_id": f"doc-{case_id}",
            "snapshot_hash": "a" * 64,
            "feature_schema_version": DOCUMENT_FEATURE_MANIFEST_V1.version,
            "feature_manifest_hash": DOCUMENT_FEATURE_MANIFEST_V1.content_hash(),
            "feature_names": names,
            "feature_values": [None] * len(names),
        }
    )


def _core(case_id="ipo_2023_0001", year=2023, code="0001.HK"):
    names = tuple(
        name
        for raw in IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER
        for name in (raw, f"{raw}__missing")
    )
    return _with_hash(
        _identity(case_id, year, code)
        | {
            "cutoff_semantics": "strictly_before_target_listing_date",
            "core_feature_schema_version": IPO_MARKET_CONTEXT_FEATURE_SCHEMA_VERSION,
            "core_feature_policy_version": IPO_MARKET_CONTEXT_FEATURE_POLICY_VERSION,
            "core_feature_manifest_hash": IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
            "feature_names": names,
            "feature_values": [None if index % 2 == 0 else 1 for index in range(len(names))],
            "raw_values": {name: None for name in IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER},
            "source_provenance": {"fixture": True},
        }
    )


def _oracle(case_id="ipo_2023_0001", year=2023, code="0001.HK"):
    names = oracle_feature_names()
    return _with_hash(
        _identity(case_id, year, code)
        | {
            "document_id": f"doc-{case_id}",
            "company_name": "Fixture",
            "source_annotation_version": "expert_annotation_v1",
            "source_annotation_kind": "pass1_only",
            "base_pass_hash": "b" * 64,
            "audit_hash": None,
            "audit_source_pass_hash": None,
            "audit_status": "no_audit",
            "audit_applied_risks": [],
            "effective_annotation_hash": "c" * 64,
            "evaluation_only": True,
            "oracle_feature_schema_version": ORACLE_DOCUMENT_FEATURE_SCHEMA_VERSION,
            "oracle_feature_policy_version": ORACLE_DOCUMENT_FEATURE_POLICY_VERSION,
            "oracle_manifest_hash": ORACLE_DOCUMENT_FEATURE_MANIFEST_HASH,
            "feature_names": names,
            "feature_values": [0] * len(names),
        }
    )


def _raw_label(case_id, year, code, value: str | None):
    listing = date(year, 1, 2)
    available = value is not None
    return MarketOutcomeLabel(
        case_id=case_id,
        stock_code=code,
        cohort_year=year,
        dataset_split=(
            MarketDatasetSplit.DEVELOPMENT
            if year <= 2023
            else MarketDatasetSplit.VALIDATION
        ),
        listing_date=listing,
        horizon=MarketLabelHorizon.FIVE_DAYS,
        base_price=Decimal("10"),
        base_price_source=MarketBasePriceSource.OFFICIAL_LISTING_PRICE,
        target_trading_date=listing + timedelta(days=7) if available else None,
        target_close=(Decimal("10") * (1 + Decimal(value))) if available else None,
        raw_return=Decimal(value) if available else None,
        availability=(
            MarketLabelAvailability.AVAILABLE
            if available
            else MarketLabelAvailability.UNAVAILABLE
        ),
        missing_reason=(
            None if available else MarketLabelMissingReason.NO_ELIGIBLE_SESSION
        ),
        label_policy_version="v04_market_label_policy_v1",
        source="fixture",
        provenance=MarketDataProvenance(
            source="fixture", dataset_version="v1", source_record_id=case_id
        ),
    )


def _targets():
    builder = FiveDayOutcomeBuilder()
    development = [
        _raw_label("ipo_2023_0001", 2023, "0001.HK", "-0.2"),
        _raw_label("ipo_2023_0002", 2023, "0002.HK", "0.1"),
    ]
    threshold = builder.freeze_threshold(development)
    labels = development + [
        _raw_label("ipo_2024_0003", 2024, "0003.HK", "-0.3")
    ]
    return {
        label.case_id: (
            builder.build_target(label, threshold).model_dump(mode="json")
            | {"content_hash": builder.build_target(label, threshold).content_hash()}
        )
        for label in labels
    }


def _record(case_id, year, code, target, *, oracle=False):
    return V04CanonicalDatasetBuilder().join_artifacts(
        production=_production(case_id, year, code),
        market_core=_core(case_id, year, code),
        target_payload=target,
        oracle=_oracle(case_id, year, code) if oracle else None,
        source_manifest_hash="d" * 64,
    )


def test_canonical_join_freezes_core_and_document_without_mutating_old_v1() -> None:
    target = _targets()["ipo_2023_0001"]
    record = _record("ipo_2023_0001", 2023, "0001.HK", target, oracle=True)
    assert len(record.market_core.feature_names) == 30
    assert len(record.production_document.feature_names) == 100
    assert len(record.oracle_document.feature_names) == len(oracle_feature_names())
    assert record.market_extended is None
    assert record.oracle_document.evaluation_only is True


def test_fair_feature_group_projection_has_explicit_stable_order() -> None:
    targets = _targets()
    records = [
        _record("ipo_2023_0002", 2023, "0002.HK", targets["ipo_2023_0002"], oracle=True),
        _record("ipo_2023_0001", 2023, "0001.HK", targets["ipo_2023_0001"], oracle=True),
    ]
    builder = V04CanonicalDatasetBuilder()
    full = builder.build(
        records,
        cohort=V04CanonicalCohort.FULL_PRODUCTION,
        dataset_split=MarketDatasetSplit.DEVELOPMENT,
    )
    intersection = builder.build(
        records,
        cohort=V04CanonicalCohort.ORACLE_INTERSECTION,
        dataset_split=MarketDatasetSplit.DEVELOPMENT,
    )
    m = project_model_matrix(full, V04ModelFeatureGroup.M)
    p = project_model_matrix(full, V04ModelFeatureGroup.P)
    pm = project_model_matrix(full, V04ModelFeatureGroup.PM)
    o = project_model_matrix(intersection, V04ModelFeatureGroup.O)
    om = project_model_matrix(intersection, V04ModelFeatureGroup.OM)
    intersection_m = project_model_matrix(intersection, V04ModelFeatureGroup.M)
    intersection_pm = project_model_matrix(intersection, V04ModelFeatureGroup.PM)
    assert m.case_ids == p.case_ids == pm.case_ids == tuple(sorted(m.case_ids))
    assert o.case_ids == om.case_ids == m.case_ids
    assert intersection_m.case_ids == intersection_pm.case_ids == o.case_ids
    assert len(m.feature_names) == 30
    assert len(p.feature_names) == 100
    assert len(pm.feature_names) == 130
    assert len(o.feature_names) == len(oracle_feature_names())
    assert len(om.feature_names) == 30 + len(oracle_feature_names())
    assert pm.feature_names[:30] == m.feature_names
    assert all(name.startswith("market_core__") for name in m.feature_names)
    assert all(name.startswith("production_document__") for name in p.feature_names)


def test_oracle_projection_requires_fair_intersection_cohort() -> None:
    targets = _targets()
    full = V04CanonicalDatasetBuilder().build(
        [_record("ipo_2023_0001", 2023, "0001.HK", targets["ipo_2023_0001"], oracle=True)],
        cohort=V04CanonicalCohort.FULL_PRODUCTION,
        dataset_split=MarketDatasetSplit.DEVELOPMENT,
    )
    with pytest.raises(ValueError, match="Oracle feature groups"):
        project_model_matrix(full, V04ModelFeatureGroup.O)


def test_identity_mismatch_and_unavailable_target_fail_closed() -> None:
    targets = _targets()
    wrong_core = _core("ipo_2023_0001", 2023, "9999.HK")
    with pytest.raises(ValueError, match="market_core.stock_code"):
        V04CanonicalDatasetBuilder().join_artifacts(
            production=_production(),
            market_core=wrong_core,
            target_payload=targets["ipo_2023_0001"],
            source_manifest_hash="d" * 64,
        )

    builder = FiveDayOutcomeBuilder()
    threshold = builder.freeze_threshold(
        [_raw_label("ipo_2023_0001", 2023, "0001.HK", "-0.2")]
    )
    unavailable = builder.build_target(
        _raw_label("ipo_2023_0001", 2023, "0001.HK", None), threshold
    )
    payload = unavailable.model_dump(mode="json") | {
        "content_hash": unavailable.content_hash()
    }
    with pytest.raises(ValueError, match="unavailable PR-C target"):
        V04CanonicalDatasetBuilder().join_artifacts(
            production=_production(),
            market_core=_core(),
            target_payload=payload,
            source_manifest_hash="d" * 64,
        )


def test_target_and_feature_artifact_tampering_is_rejected() -> None:
    target = _targets()["ipo_2023_0001"]
    target["poor_performer_5d"] = not target["poor_performer_5d"]
    with pytest.raises(ValueError, match="target content hash"):
        _record("ipo_2023_0001", 2023, "0001.HK", target)

    target = _targets()["ipo_2023_0001"]
    production = _production()
    production["feature_values"][0] = 999
    with pytest.raises(ValueError, match="Production Document-X content hash"):
        V04CanonicalDatasetBuilder().join_artifacts(
            production=production,
            market_core=_core(),
            target_payload=target,
            source_manifest_hash="d" * 64,
        )
