"""Guards for the read-only Oracle Gold coverage audit.

These tests run against the real repository annotation assets, so they pin the
current Oracle reality rather than a fixture's idea of it.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ipo_risk.modeling.oracle_document import build_oracle_document_features
from scripts import audit_oracle_gold_coverage as audit_module

REPO_ROOT = Path(__file__).resolve().parents[2]
FROZEN_MANIFEST = REPO_ROOT / "reports" / "frozen" / "v04_pr_a_document_materialization_manifest.json"


@pytest.fixture(scope="module")
def audit_result() -> tuple[list[dict[str, object]], dict[str, object]]:
    return audit_module.audit(REPO_ROOT)


@pytest.fixture(scope="module")
def frozen_manifest() -> dict[str, object]:
    return json.loads(FROZEN_MANIFEST.read_text(encoding="utf-8"))


def test_funnel_arithmetic_is_closed(audit_result) -> None:
    rows, summary = audit_result
    funnel = summary["funnel"]
    assert funnel["case_packets"] == sum(row["packet_present"] for row in rows)
    assert funnel["pass1_present"] == sum(row["pass1_present"] for row in rows)
    # Buildable is exactly the officially-eligible, annotated, schema-valid subset.
    buildable = {row["case_id"] for row in rows if row["oracle_buildable"]}
    official_annotated = {row["case_id"] for row in rows if row["in_official_universe"] and row["pass1_present"]}
    assert buildable <= official_annotated
    assert official_annotated - buildable == {row["case_id"] for row in rows if row["failure_reason"].startswith("ValueError") and row["in_official_universe"]}
    assert funnel["oracle_buildable_in_official_universe"] == len(buildable)


def test_every_official_case_is_present_and_classified(audit_result, frozen_manifest) -> None:
    rows, summary = audit_result
    official = [row for row in rows if row["in_official_universe"]]
    assert len(official) == frozen_manifest["official_case_count"] == 438
    for row in official:
        assert row["oracle_buildable"] or row["failure_reason"], row["case_id"]


def test_coverage_reproduces_the_frozen_pr_a_oracle_counts(audit_result, frozen_manifest) -> None:
    """Independent local reproduction of PR-A's Oracle counts.

    PR-A's bulk runtime artifacts are not in the repository, so this compares
    counts against the committed freeze manifest; it is not a re-verification of
    PR-A's own per-case hashes.
    """
    _, summary = audit_result
    assert summary["funnel"]["oracle_buildable_in_official_universe"] == frozen_manifest["oracle_materialized_count"] == 60
    assert summary["no_reviewed_gold_count"] == frozen_manifest["no_reviewed_gold_count"] == 378
    assert summary["funnel"]["oracle_buildable_in_official_universe"] + summary["no_reviewed_gold_count"] == 438


def test_oracle_has_no_validation_coverage(audit_result) -> None:
    """The PR-E escalation, encoded executably.

    The Oracle arms O and OM — and therefore the Production-vs-Oracle diagnostic
    on the intersection cohort — have zero validation-split cases today.  When
    this assertion starts failing, the Oracle arm has become evaluable under
    PR-E's fit-on-development / evaluate-on-validation protocol, and
    ``docs/V04_ORACLE_GOLD_COVERAGE_AUDIT.md`` must be revised in the same change.
    """
    _, summary = audit_result
    coverage = summary["oracle_coverage_by_official_split"]
    assert coverage.get("development") == 60
    assert coverage.get("validation", 0) == 0
    assert coverage.get("blind", 0) == 0


def test_blind_cohort_is_never_read(audit_result) -> None:
    rows, summary = audit_result
    assert summary["blind_2025_accessed"] is False
    assert all(row["official_cohort_year"] in ("", *range(2020, 2025)) for row in rows)
    assert all(row["official_dataset_split"] != "blind" for row in rows)


def test_artifact_identity_disagreements_are_reported_not_hidden(audit_result) -> None:
    """Oracle artifacts stamp annotation ``source_year``, not official listing year.

    ``join_oracle_outcome`` compares ``cohort_year`` and ``dataset_split`` between
    the Oracle feature and the outcome label, so each mismatch here is a hard join
    failure waiting at PR-D / PR-E.  Fixing it would rewrite frozen PR-A Oracle
    content hashes, so it is reported as a precondition rather than patched here.
    """
    _, summary = audit_result
    identity = summary["oracle_identity_provenance"]
    assert identity["compared_fields"] == ["cohort_year", "dataset_split"]
    assert identity["materialized_mismatch_count"] == 3
    assert set(identity["materialized_mismatches"]) == {"ipo_2020_08489", "ipo_2020_09600", "ipo_2022_02450"}
    assert all(value == "cohort_year" for value in identity["materialized_mismatches"].values())
    # No materialized artifact lands in the wrong split today; two un-annotated
    # 2024 packets would, which is precisely the cohort the escalation asks for.
    assert identity["latent_mismatch_if_annotated"] == {
        "ipo_2023_02503": "cohort_year,dataset_split",
        "ipo_2024_02410": "dataset_split",
    }


def test_annotation_opportunity_is_enumerated(audit_result) -> None:
    _, summary = audit_result
    opportunity = summary["annotation_opportunity"]
    assert opportunity["official_packets_without_pass1"] == 38
    assert opportunity["by_official_split"] == {"development": 19, "validation": 19}
    assert len(opportunity["case_ids"]) == 38


def test_oracle_rebuild_is_deterministic() -> None:
    for case_id in ("ipo_2020_00368", "ipo_2021_00013", "ipo_2022_00314"):
        first = build_oracle_document_features(REPO_ROOT, case_id)
        second = build_oracle_document_features(REPO_ROOT, case_id)
        assert first["content_hash"] == second["content_hash"]
        assert first["effective_annotation_hash"] == second["effective_annotation_hash"]
        assert first["evaluation_only"] is True
