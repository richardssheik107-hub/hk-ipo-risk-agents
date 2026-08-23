"""Guards for the read-only Oracle Gold coverage audit.

These tests run against the real repository annotation assets, so they pin the
current Oracle reality rather than a fixture's idea of it.

Revised 2026-08-23 after the 2023/2024 blind annotation landed (61 -> 101 pass1).
The previous ``test_oracle_has_no_validation_coverage`` trip-wire fired exactly as
its docstring promised and has been replaced by
``test_oracle_now_has_validation_coverage``.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ipo_risk.modeling.oracle_document import build_oracle_document_features
from scripts import audit_oracle_gold_coverage as audit_module

REPO_ROOT = Path(__file__).resolve().parents[2]
FROZEN_MANIFEST = REPO_ROOT / "reports" / "frozen" / "v04_pr_a_document_materialization_manifest.json"
# Eligible cases whose 5D outcome is unavailable; PR-C refuses them before PR-D.
OUTCOME_UNAVAILABLE = {
    "ipo_2020_01248", "ipo_2020_06688", "ipo_2020_06813",
    "ipo_2021_01491", "ipo_2022_06678", "ipo_2022_07841",
}


@pytest.fixture(scope="module")
def audit_result() -> tuple[list[dict[str, object]], dict[str, object]]:
    return audit_module.audit(REPO_ROOT)


@pytest.fixture(scope="module")
def frozen_manifest() -> dict[str, object]:
    return json.loads(FROZEN_MANIFEST.read_text(encoding="utf-8"))


def _official(rows):
    return [row for row in rows if row["in_official_universe"]]


def test_funnel_arithmetic_is_closed(audit_result) -> None:
    rows, summary = audit_result
    funnel = summary["funnel"]
    assert funnel["case_packets"] == sum(row["packet_present"] for row in rows)
    assert funnel["pass1_present"] == sum(row["pass1_present"] for row in rows)
    assert funnel["oracle_buildable"] == sum(row["oracle_buildable"] for row in rows)
    # Buildable inside the official universe is exactly the annotated, schema-valid subset.
    official = _official(rows)
    buildable = {row["case_id"] for row in official if row["oracle_buildable"]}
    annotated = {row["case_id"] for row in official if row["pass1_present"]}
    assert buildable <= annotated
    assert annotated - buildable == {
        row["case_id"] for row in official if row["failure_reason"].startswith("ValueError")
    }
    assert funnel["oracle_buildable_in_official_universe"] == len(buildable)


def test_every_official_case_is_present_and_classified(audit_result, frozen_manifest) -> None:
    rows, _ = audit_result
    official = _official(rows)
    assert len(official) == frozen_manifest["official_case_count"] == 438
    for row in official:
        assert row["oracle_buildable"] or row["failure_reason"], row["case_id"]


def test_oracle_now_has_validation_coverage(audit_result) -> None:
    """The former no-validation trip-wire, inverted after the 2023/2024 annotation.

    Oracle previously covered 60 development cases and zero validation cases, which
    made PR-E's fit-on-development / evaluate-on-validation protocol impossible for
    the O and OM arms.  The blind annotation of the 2023 and 2024 packets closed
    that gap.  If validation coverage ever returns to zero, the audit document's
    protocol recommendation has to be revisited again.
    """
    _, summary = audit_result
    coverage = summary["oracle_coverage_by_official_split"]
    assert coverage["development"] == 79
    assert coverage["validation"] == 19
    assert coverage.get("blind", 0) == 0


def test_annotation_backlog_is_cleared(audit_result) -> None:
    _, summary = audit_result
    opportunity = summary["annotation_opportunity"]
    assert opportunity["official_packets_without_pass1"] == 0
    assert opportunity["case_ids"] == []


def test_frozen_pr_a_record_no_longer_matches_reality(audit_result, frozen_manifest) -> None:
    """PR-A's freeze predates the 2023/2024 annotation and is now stale.

    This is a governance finding, not a defect in either artifact: PR-A correctly
    froze what existed at revision 13e0281f.  Whether the Oracle side of PR-A should
    be re-materialized is A's decision.  The assertion records the divergence so it
    cannot be forgotten, and will need updating if PR-A is re-frozen.
    """
    _, summary = audit_result
    frozen_count = frozen_manifest["oracle_materialized_count"]
    current_count = summary["funnel"]["oracle_buildable_in_official_universe"]
    assert frozen_count == 60, "PR-A freeze manifest changed; re-check this finding"
    assert current_count == 98
    assert current_count > frozen_count
    assert summary["no_reviewed_gold_count"] == 340
    assert frozen_manifest["no_reviewed_gold_count"] == 378
    # The official universe itself did not move; only the annotation coverage did.
    assert current_count + summary["no_reviewed_gold_count"] == 438


def test_blind_cohort_is_never_read(audit_result) -> None:
    rows, summary = audit_result
    assert summary["blind_2025_accessed"] is False
    assert all(row["official_cohort_year"] in ("", *range(2020, 2025)) for row in rows)
    assert all(row["official_dataset_split"] != "blind" for row in rows)


def test_identity_defect_fired_on_the_newly_annotated_cases(audit_result) -> None:
    """Oracle artifacts stamp annotation ``source_year``, not official listing year.

    ``join_oracle_outcome`` and PR-D's ``_identity_mismatches`` both compare
    ``cohort_year`` and ``dataset_split``, so every case here is a hard join failure.

    Three cases were already materialized before the 2023/2024 annotation.  The two
    added since -- ipo_2023_02503 and ipo_2024_02410 -- were previously reported as
    "latent mismatch if annotated"; annotating them fired the defect exactly as
    predicted, and both land in the scarce validation split.
    """
    _, summary = audit_result
    identity = summary["oracle_identity_provenance"]
    assert identity["compared_fields"] == ["cohort_year", "dataset_split"]
    assert identity["materialized_mismatches"] == {
        "ipo_2020_08489": "cohort_year",
        "ipo_2020_09600": "cohort_year",
        "ipo_2022_02450": "cohort_year",
        "ipo_2023_02503": "cohort_year,dataset_split",
        "ipo_2024_02410": "dataset_split",
    }
    assert identity["materialized_mismatch_count"] == 5
    # Nothing is latent any more: every official packet is annotated.
    assert identity["latent_mismatch_if_annotated"] == {}


def test_usable_cohort_after_pr_c_and_pr_d_rejection(audit_result) -> None:
    """What PR-E actually receives, after both downstream gates refuse rows.

    PR-C rejects cases whose 5D outcome is unavailable; PR-D rejects cases whose
    Oracle identity disagrees with Production. The remainder is the real Oracle
    intersection cohort, and it is smaller than the raw buildable count.
    """
    rows, _ = audit_result
    usable = {"development": 0, "validation": 0}
    for row in _official(rows):
        if not row["oracle_buildable"]:
            continue
        if row["case_id"] in OUTCOME_UNAVAILABLE or row["identity_mismatch"]:
            continue
        usable[str(row["official_dataset_split"])] += 1
    assert usable == {"development": 75, "validation": 17}
    # The identity defect costs two of the nineteen validation cases, the scarcest arm.
    assert usable["validation"] == 19 - 2


def test_oracle_rebuild_is_deterministic() -> None:
    for case_id in ("ipo_2020_00368", "ipo_2021_00013", "ipo_2024_02410"):
        first = build_oracle_document_features(REPO_ROOT, case_id)
        second = build_oracle_document_features(REPO_ROOT, case_id)
        assert first["content_hash"] == second["content_hash"]
        assert first["effective_annotation_hash"] == second["effective_annotation_hash"]
        assert first["evaluation_only"] is True
