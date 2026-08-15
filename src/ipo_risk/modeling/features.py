"""Frozen V04 document-feature manifest and deterministic vectorization."""

from __future__ import annotations

from ipo_risk.domain.risk_codes import V03_ENABLED_RISK_CODES
from ipo_risk.schemas.modeling import (
    DocumentFeatureDefinition,
    DocumentFeatureDType,
    DocumentFeatureManifest,
    DocumentFeatureVector,
    DocumentRiskFeatureState,
    V03DocumentRiskSnapshot,
)


CANONICAL_V03_RISK_ORDER = tuple(sorted(V03_ENABLED_RISK_CODES))
LEVEL_ORDINAL_MAPPING = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def _build_manifest() -> DocumentFeatureManifest:
    definitions: list[DocumentFeatureDefinition] = []

    def add(
        name: str,
        dtype: DocumentFeatureDType,
        source: str,
        missing_semantics: str,
    ) -> None:
        definitions.append(
            DocumentFeatureDefinition(
                index=len(definitions),
                name=name,
                dtype=dtype,
                source=source,
                missing_semantics=missing_semantics,
            )
        )

    for risk_code in CANONICAL_V03_RISK_ORDER:
        prefix = f"{risk_code}__"
        for state in DocumentRiskFeatureState:
            add(
                f"{prefix}state_{state.value}",
                DocumentFeatureDType.INT8,
                f"snapshot.{risk_code}.state",
                "always present one-hot state indicator",
            )
        add(
            f"{prefix}score",
            DocumentFeatureDType.FLOAT64,
            f"snapshot.{risk_code}.score",
            "null unless verified; never imputed as a safe zero",
        )
        add(
            f"{prefix}level_ordinal",
            DocumentFeatureDType.INT8,
            f"snapshot.{risk_code}.level",
            "null unless verified; mapping is frozen in this manifest",
        )
        add(
            f"{prefix}evidence_count",
            DocumentFeatureDType.INT32,
            f"snapshot.{risk_code}.evidence_count",
            "zero means no evidence attached, not absence of risk",
        )
        add(
            f"{prefix}calculation_success",
            DocumentFeatureDType.INT8,
            f"snapshot.{risk_code}.calculation_success",
            "null when no verified calculation is present",
        )
        add(
            f"{prefix}missing",
            DocumentFeatureDType.INT8,
            f"snapshot.{risk_code}.state",
            "one when a verified model score is unavailable",
        )

    aggregate_definitions = (
        ("verified_risk_count", DocumentFeatureDType.INT32, "always present"),
        ("pending_risk_count", DocumentFeatureDType.INT32, "always present"),
        ("needs_review_risk_count", DocumentFeatureDType.INT32, "always present"),
        ("rejected_risk_count", DocumentFeatureDType.INT32, "always present"),
        ("not_emitted_risk_count", DocumentFeatureDType.INT32, "always present"),
        ("unavailable_risk_count", DocumentFeatureDType.INT32, "always present"),
        ("high_risk_count", DocumentFeatureDType.INT32, "verified risks only"),
        ("critical_risk_count", DocumentFeatureDType.INT32, "verified risks only"),
        (
            "max_verified_score",
            DocumentFeatureDType.FLOAT64,
            "null when no verified score exists",
        ),
        (
            "mean_verified_score",
            DocumentFeatureDType.FLOAT64,
            "null when no verified score exists",
        ),
        (
            "conflict_count",
            DocumentFeatureDType.INT32,
            "null when authoritative supervision diagnostics are unavailable",
        ),
        ("missing_risk_feature_count", DocumentFeatureDType.INT32, "always present"),
    )
    for name, dtype, missing_semantics in aggregate_definitions:
        add(name, dtype, "snapshot.aggregate", missing_semantics)

    return DocumentFeatureManifest(
        features=tuple(definitions),
        level_ordinal_mapping=tuple(LEVEL_ORDINAL_MAPPING.items()),
    )


DOCUMENT_FEATURE_MANIFEST_V1 = _build_manifest()


def vectorize_document_snapshot(
    snapshot: V03DocumentRiskSnapshot,
    manifest: DocumentFeatureManifest = DOCUMENT_FEATURE_MANIFEST_V1,
) -> DocumentFeatureVector:
    """Convert a semantic snapshot without collapsing missingness into safety."""

    if snapshot.feature_schema_version != manifest.version:
        raise ValueError("snapshot and feature manifest versions differ")
    by_code = {item.risk_code: item for item in snapshot.risk_features}
    if tuple(item.risk_code for item in snapshot.risk_features) != CANONICAL_V03_RISK_ORDER:
        raise ValueError("snapshot risk positions do not match canonical order")

    values: dict[str, int | float | None] = {}
    level_mapping = dict(manifest.level_ordinal_mapping)
    for risk_code in CANONICAL_V03_RISK_ORDER:
        item = by_code[risk_code]
        prefix = f"{risk_code}__"
        for state in DocumentRiskFeatureState:
            values[f"{prefix}state_{state.value}"] = int(item.state is state)
        trusted = item.state is DocumentRiskFeatureState.VERIFIED
        values[f"{prefix}score"] = item.score if trusted else None
        values[f"{prefix}level_ordinal"] = (
            level_mapping[item.level]
            if trusted and item.level is not None
            else None
        )
        values[f"{prefix}evidence_count"] = item.evidence_count
        values[f"{prefix}calculation_success"] = (
            int(item.calculation_success)
            if trusted and item.calculation_success is not None
            else None
        )
        values[f"{prefix}missing"] = int(not trusted)

    states = [item.state for item in snapshot.risk_features]
    verified = [
        item
        for item in snapshot.risk_features
        if item.state is DocumentRiskFeatureState.VERIFIED and item.score is not None
    ]
    verified_scores = [item.score for item in verified if item.score is not None]
    values.update(
        {
            "verified_risk_count": states.count(DocumentRiskFeatureState.VERIFIED),
            "pending_risk_count": states.count(DocumentRiskFeatureState.PENDING),
            "needs_review_risk_count": states.count(DocumentRiskFeatureState.NEEDS_REVIEW),
            "rejected_risk_count": states.count(DocumentRiskFeatureState.REJECTED),
            "not_emitted_risk_count": states.count(DocumentRiskFeatureState.NOT_EMITTED),
            "unavailable_risk_count": states.count(DocumentRiskFeatureState.UNAVAILABLE),
            "high_risk_count": sum(item.level == "high" for item in verified),
            "critical_risk_count": sum(item.level == "critical" for item in verified),
            "max_verified_score": max(verified_scores) if verified_scores else None,
            "mean_verified_score": (
                sum(verified_scores) / len(verified_scores) if verified_scores else None
            ),
            "conflict_count": snapshot.conflict_count,
            "missing_risk_feature_count": sum(
                state is not DocumentRiskFeatureState.VERIFIED for state in states
            ),
        }
    )
    names = tuple(item.name for item in manifest.features)
    return DocumentFeatureVector(
        feature_schema_version=manifest.version,
        manifest_hash=manifest.content_hash(),
        feature_names=names,
        feature_values=tuple(values[name] for name in names),
    )
