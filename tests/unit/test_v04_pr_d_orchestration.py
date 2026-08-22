from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from ipo_risk.market.ipo_market_context_features import (
    IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
    IPO_MARKET_CONTEXT_FEATURE_POLICY_VERSION,
    IPO_MARKET_CONTEXT_FEATURE_SCHEMA_VERSION,
    IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER,
)
from ipo_risk.market.outcomes import FiveDayOutcomeBuilder
from ipo_risk.modeling.features import DOCUMENT_FEATURE_MANIFEST_V1
from ipo_risk.modeling.oracle_document import (
    ORACLE_DOCUMENT_FEATURE_MANIFEST_HASH,
    ORACLE_DOCUMENT_FEATURE_POLICY_VERSION,
    ORACLE_DOCUMENT_FEATURE_SCHEMA_VERSION,
    oracle_feature_names,
)
from ipo_risk.schemas.canonical_modeling import canonical_hash
from ipo_risk.schemas.market import (
    MarketBasePriceSource,
    MarketDataProvenance,
    MarketDatasetSplit,
    MarketLabelAvailability,
    MarketLabelHorizon,
    MarketLabelMissingReason,
    MarketOutcomeLabel,
)
from scripts.run_v04_pr_d import materialize_pr_d


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _with_hash(body):
    return body | {"content_hash": canonical_hash(body)}


def _label(
    case_id: str,
    code: str,
    year: int,
    available: bool,
    *,
    missing_reason: MarketLabelMissingReason = MarketLabelMissingReason.NO_ELIGIBLE_SESSION,
) -> MarketOutcomeLabel:
    listing = date(year, 1, 2)
    value = Decimal((sum(ord(char) for char in case_id) % 61 - 30)) / Decimal("100")
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
        base_price=Decimal("10") if available else None,
        base_price_source=(
            MarketBasePriceSource.OFFICIAL_LISTING_PRICE if available else None
        ),
        target_trading_date=listing + timedelta(days=7) if available else None,
        target_close=Decimal("10") * (1 + value) if available else None,
        raw_return=value if available else None,
        availability=(
            MarketLabelAvailability.AVAILABLE
            if available
            else MarketLabelAvailability.UNAVAILABLE
        ),
        missing_reason=None if available else missing_reason,
        label_policy_version="v04_market_label_policy_v1",
        source="fixture",
        provenance=MarketDataProvenance(
            source="fixture", dataset_version="v1", source_record_id=case_id
        ),
    )


def test_pr_d_full_orchestration_materializes_fair_cohorts_and_resumes(
    tmp_path: Path,
) -> None:
    pr_a_dir = tmp_path / "pr_a"
    pr_b_dir = tmp_path / "pr_b"
    pr_c_dir = tmp_path / "pr_c"
    years = [2020] * 125 + [2021] * 97 + [2022] * 78 + [2023] * 68 + [2024] * 70
    identities = [
        (f"ipo_{year}_{index:05d}", f"{index:05d}.HK", year)
        for index, year in enumerate(years, start=1)
    ]
    development_ids = sorted(
        case_id for case_id, _code, year in identities if year <= 2023
    )
    missing_base_price = set(development_ids[:12])
    no_eligible_session = set(development_ids[12:14])
    unavailable = missing_base_price | no_eligible_session
    raw_labels = [
        _label(
            case_id,
            code,
            year,
            case_id not in unavailable,
            missing_reason=(
                MarketLabelMissingReason.MISSING_BASE_PRICE
                if case_id in missing_base_price
                else MarketLabelMissingReason.NO_ELIGIBLE_SESSION
            ),
        )
        for case_id, code, year in identities
    ]
    outcome_builder = FiveDayOutcomeBuilder()
    threshold = outcome_builder.freeze_threshold(
        label
        for label in raw_labels
        if label.dataset_split is MarketDatasetSplit.DEVELOPMENT
    )
    document_names = tuple(item.name for item in DOCUMENT_FEATURE_MANIFEST_V1.features)
    core_names = tuple(
        name
        for raw in IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER
        for name in (raw, f"{raw}__missing")
    )
    for index, (identity, raw_label) in enumerate(zip(identities, raw_labels, strict=True)):
        case_id, code, year = identity
        split = "development" if year <= 2023 else "validation"
        common = {
            "case_id": case_id,
            "stock_code": code,
            "cohort_year": year,
            "listing_date": f"{year}-01-02",
            "dataset_split": split,
        }
        production = _with_hash(
            common
            | {
                "document_id": f"doc-{case_id}",
                "snapshot_hash": "a" * 64,
                "feature_schema_version": DOCUMENT_FEATURE_MANIFEST_V1.version,
                "feature_manifest_hash": DOCUMENT_FEATURE_MANIFEST_V1.content_hash(),
                "feature_names": document_names,
                "feature_values": [None] * len(document_names),
            }
        )
        core = _with_hash(
            common
            | {
                "cutoff_semantics": "strictly_before_target_listing_date",
                "core_feature_schema_version": IPO_MARKET_CONTEXT_FEATURE_SCHEMA_VERSION,
                "core_feature_policy_version": IPO_MARKET_CONTEXT_FEATURE_POLICY_VERSION,
                "core_feature_manifest_hash": IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
                "feature_names": core_names,
                "feature_values": [None if i % 2 == 0 else 1 for i in range(30)],
                "raw_values": {name: None for name in IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER},
                "source_provenance": {"fixture": True},
            }
        )
        target = outcome_builder.build_target(raw_label, threshold)
        _write(pr_a_dir / "production_features" / f"{case_id}.json", production)
        _write(pr_b_dir / "core_features" / f"{case_id}.json", core)
        _write(
            pr_c_dir / "targets" / f"{case_id}.json",
            target.model_dump(mode="json") | {"content_hash": target.content_hash()},
        )
        if 14 <= index < 17:  # governed Oracle is intentionally Development-only here
            oracle = _with_hash(
                common
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
                    "feature_names": oracle_feature_names(),
                    "feature_values": [0] * len(oracle_feature_names()),
                }
            )
            _write(pr_a_dir / "oracle_features" / f"{case_id}.json", oracle)

    pr_a_manifest = tmp_path / "v04_pr_a_manifest.json"
    pr_b_manifest = tmp_path / "v04_pr_b_manifest.json"
    pr_c_manifest = tmp_path / "v04_pr_c_manifest.json"
    _write(
        pr_a_manifest,
        {
            "official_case_count": 438,
            "production_materialized_count": 438,
            "determinism_passed": True,
            "blind_2025_accessed": False,
        },
    )
    _write(
        pr_b_manifest,
        {
            "status": "complete_frozen",
            "official_case_count": 438,
            "materialized_count": 438,
            "determinism": {"passed": True},
            "blind_2025_y_accessed": False,
        },
    )
    _write(
        pr_c_manifest,
        {
            "gate_passed": True,
            "official_case_count": 438,
            "available_count": 424,
            "unavailable_count": 14,
            "failure_count": 0,
            "determinism_mismatch_count": 0,
            "validation_used_for_threshold": False,
            "blind_2025_y_accessed": False,
            "policy_hash": outcome_builder.policy.content_hash(),
            "threshold_hash": threshold.content_hash(),
        },
    )
    output = tmp_path / "out"
    kwargs = {
        "production_dir": pr_a_dir / "production_features",
        "market_core_dir": pr_b_dir / "core_features",
        "target_dir": pr_c_dir / "targets",
        "oracle_dir": pr_a_dir / "oracle_features",
        "pr_a_manifest_path": pr_a_manifest,
        "pr_b_manifest_path": pr_b_manifest,
        "pr_c_manifest_path": pr_c_manifest,
        "output_dir": output,
    }
    first = materialize_pr_d(**kwargs)
    second = materialize_pr_d(**kwargs, resume=True)
    assert first["summary"] == second["summary"]
    assert first["summary"]["official_case_count"] == 438
    assert first["summary"]["full_production_model_ready_count"] == 424
    assert first["summary"]["target_unavailable_count"] == 14
    assert first["summary"]["target_unavailable_reason_counts"] == {
        "missing_base_price": 12,
        "no_eligible_session": 2,
    }
    assert first["summary"]["development_model_ready_count"] == 354
    assert first["summary"]["validation_model_ready_count"] == 70
    assert first["summary"]["oracle_intersection_model_ready_count"] == 3
    assert first["summary"]["oracle_split_status"] == {
        "development": "available",
        "validation": "unavailable_no_reviewed_gold",
    }
    assert (output / "matrices" / "full_production_PM_validation.json").is_file()
    assert (output / "matrices" / "oracle_intersection_OM_development.json").is_file()
    assert not (output / "matrices" / "oracle_intersection_OM_validation.json").exists()
