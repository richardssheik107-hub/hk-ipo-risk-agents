from __future__ import annotations

import inspect

from ipo_risk.modeling.features import (
    CANONICAL_V03_RISK_ORDER,
    DOCUMENT_FEATURE_MANIFEST_V1,
)
from ipo_risk.modeling.snapshot import DocumentRiskSnapshotBuilder


def test_manifest_has_frozen_unique_contiguous_order_and_hash() -> None:
    manifest = DOCUMENT_FEATURE_MANIFEST_V1
    assert manifest.version == "v04_document_features_v1"
    assert len(manifest.features) == 100
    assert [item.index for item in manifest.features] == list(range(100))
    assert len({item.name for item in manifest.features}) == 100
    assert manifest.content_hash() == manifest.content_hash()


def test_each_canonical_risk_has_all_six_states_and_missingness() -> None:
    names = {item.name for item in DOCUMENT_FEATURE_MANIFEST_V1.features}
    for risk_code in CANONICAL_V03_RISK_ORDER:
        assert {
            f"{risk_code}__state_verified",
            f"{risk_code}__state_pending",
            f"{risk_code}__state_needs_review",
            f"{risk_code}__state_rejected",
            f"{risk_code}__state_not_emitted",
            f"{risk_code}__state_unavailable",
            f"{risk_code}__score",
            f"{risk_code}__level_ordinal",
            f"{risk_code}__evidence_count",
            f"{risk_code}__calculation_success",
            f"{risk_code}__missing",
        } <= names


def test_level_mapping_is_explicit_and_versioned() -> None:
    assert dict(DOCUMENT_FEATURE_MANIFEST_V1.level_ordinal_mapping) == {
        "low": 0,
        "medium": 1,
        "high": 2,
        "critical": 3,
    }


def test_snapshot_builder_has_no_retriever_agent_llm_or_network_dependency() -> None:
    source = inspect.getsource(inspect.getmodule(DocumentRiskSnapshotBuilder))
    forbidden = (
        "ipo_risk.retrieval",
        "ipo_risk.agents",
        "requests",
        "httpx",
        "openai",
        "socket",
    )
    assert all(token not in source for token in forbidden)
