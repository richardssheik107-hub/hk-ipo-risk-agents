from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from ipo_risk.schemas.data_readiness import (
    SourceAvailability,
    V04SourceManifest,
    V04SourceManifestEntry,
)
from ipo_risk.schemas.market import (
    IPOMarketMetadata,
    MarketDataProvenance,
    MarketExchange,
    MarketSecurityEligibility,
    MarketSecurityEligibilityReason,
)
from scripts import run_v04_pr_b as pr_b


def _metadata(case_id: str, stock_code: str, listing_date: date) -> IPOMarketMetadata:
    return IPOMarketMetadata(
        case_id=case_id,
        stock_code=stock_code,
        cohort_year=listing_date.year,
        listing_date=listing_date,
        listing_price=1,
        currency="HKD",
        exchange=MarketExchange.HKEX,
        official_ipo_universe_member=True,
        modeling_eligibility=MarketSecurityEligibility.ELIGIBLE,
        eligibility_reason=MarketSecurityEligibilityReason.OFFICIAL_IPO_UNIVERSE_MEMBER,
        source="test",
        provenance=MarketDataProvenance(
            source="test",
            dataset_version="v1",
            source_record_id=case_id,
        ),
    )


def _source_manifest() -> V04SourceManifest:
    entries = []
    for logical_id in sorted(pr_b.EXTENDED_SOURCE_IDS):
        entries.append(
            V04SourceManifestEntry(
                source_name=logical_id,
                logical_id=logical_id,
                dataset_version="not_supplied",
                availability=SourceAvailability.MISSING,
                provenance={"blocker": f"{logical_id.upper()}_SOURCE_REQUIRED"},
            )
        )
    return V04SourceManifest(entries=tuple(entries))


def test_select_metadata_rejects_blind_2025() -> None:
    blind = _metadata("blind", "0001.HK", date(2025, 1, 2))
    with pytest.raises(ValueError, match="2025 blind cohort"):
        pr_b.select_metadata([blind])


def test_core_artifact_ignores_future_ipo_and_future_outcome() -> None:
    target = _metadata("target", "0002.HK", date(2022, 3, 1))
    bridge = {"official_industry_name": "A"}
    known = {
        "case_id": "prior",
        "stock_code": "0001.HK",
        "listing_date": date(2022, 2, 10),
        "industry": "A",
        "funds_raised": 10,
        "target_1d": date(2022, 2, 11),
        "return_1d": -0.1,
        "target_5d": date(2022, 2, 17),
        "return_5d": -0.2,
    }
    future = {
        "case_id": "future",
        "stock_code": "0003.HK",
        "listing_date": date(2022, 3, 2),
        "industry": "A",
        "funds_raised": 999999,
        "target_1d": date(2022, 3, 3),
        "return_1d": -0.99,
        "target_5d": date(2022, 3, 9),
        "return_5d": -0.99,
    }

    first = pr_b.build_core_feature_artifact(
        metadata=target,
        bridge_row=bridge,
        prior_records=[known],
        bridge_sha256="a" * 64,
        eod_sha256="b" * 64,
    )
    second = pr_b.build_core_feature_artifact(
        metadata=target,
        bridge_row=bridge,
        prior_records=[known, future],
        bridge_sha256="a" * 64,
        eod_sha256="b" * 64,
    )

    assert first == second
    assert first["raw_values"]["recent_ipo_break_rate"] == 1
    assert first["raw_values"]["recent_ipo_return_5d"] == pytest.approx(-0.2)


def test_json_resume_is_conflict_safe(tmp_path: Path) -> None:
    path = tmp_path / "artifact.json"
    assert pr_b._write_json_conflict_safe(path, {"a": 1}, resume=False) == "created"
    assert pr_b._write_json_conflict_safe(path, {"a": 1}, resume=True) == "reused"

    with pytest.raises(ValueError, match="provenance/content conflict"):
        pr_b._write_json_conflict_safe(path, {"a": 2}, resume=True)

    with pytest.raises(ValueError, match="already exists"):
        pr_b._write_json_conflict_safe(path, {"a": 1}, resume=False)


def test_extended_missing_sources_are_explicit_not_core_failure() -> None:
    status = pr_b._extended_source_status(_source_manifest())
    assert status == {
        "hsi": "missing",
        "industry_mapping": "missing",
        "industry_index": "missing",
        "market_turnover": "missing",
    }


def test_materialization_keeps_failed_case_in_coverage_and_resumes_stably(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = _metadata("case_a", "0001.HK", date(2022, 1, 10))
    second = _metadata("case_b", "0002.HK", date(2022, 2, 10))
    metadata = (first, second)

    monkeypatch.setattr(pr_b, "require_clean_worktree", lambda _root: None)
    monkeypatch.setattr(pr_b, "_git_revision", lambda _root: "a" * 40)
    monkeypatch.setattr(pr_b, "load_official_metadata", lambda _catalog: metadata)
    monkeypatch.setattr(
        pr_b,
        "_read_bridge_rows",
        lambda _catalog: {
            "case_a": {
                "official_industry_name": "A",
                "official_funds_raised": "10",
            }
            # case_b deliberately missing to exercise isolated failure behavior.
        },
    )
    manifest = _source_manifest()
    source_manifest_path = tmp_path / "source_manifest.json"
    source_manifest_path.write_text(manifest.model_dump_json(), encoding="utf-8")
    monkeypatch.setattr(
        pr_b,
        "_load_source_manifest",
        lambda _catalog: (manifest, source_manifest_path),
    )
    monkeypatch.setattr(
        pr_b,
        "build_store",
        lambda **_kwargs: {
            "bridge_sha256": "a" * 64,
            "raw_eod_sha256": "b" * 64,
            "target_case_count": 438,
            "row_count": 100,
            "distinct_target_securities": 432,
        },
    )
    monkeypatch.setattr(pr_b, "freeze_execution_context", lambda **_kwargs: {})

    class FakeProvider:
        def __init__(self, *_args, **_kwargs) -> None:
            pass

        def readiness_report(self):
            return SimpleNamespace(
                source_sha256="b" * 64,
                ohlcv_matched=432,
                ohlcv_missing=6,
            )

    monkeypatch.setattr(pr_b, "CompetitionCSVMarketDataProvider", FakeProvider)
    monkeypatch.setattr(
        pr_b,
        "build_prior_ipo_records",
        lambda **_kwargs: (
            [],
            {
                "case_a": {"one_day_available": False, "five_day_available": False},
                "case_b": {"one_day_available": False, "five_day_available": False},
            },
        ),
    )

    output = tmp_path / "out"
    first_run = pr_b.materialize_pr_b(
        repo_root=tmp_path,
        catalog_dir=tmp_path,
        data_root=tmp_path,
        output_dir=output,
        require_clean=False,
    )
    assert len(first_run["coverage"]) == 2
    assert first_run["summary"]["core_market_x_materialized_count"] == 1
    assert first_run["summary"]["failed_count"] == 1
    failed = next(row for row in first_run["coverage"] if row["case_id"] == "case_b")
    assert failed["core_market_x_available"] is False
    assert failed["failure_stage"] == "core_feature_build"

    resumed = pr_b.materialize_pr_b(
        repo_root=tmp_path,
        catalog_dir=tmp_path,
        data_root=tmp_path,
        output_dir=output,
        resume=True,
        verify_determinism=True,
        require_clean=False,
    )
    assert resumed["summary"]["coverage_content_hash"] == first_run["summary"][
        "coverage_content_hash"
    ]
    assert resumed["reproducibility"]["passed"] is True
