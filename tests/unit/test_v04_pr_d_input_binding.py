from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

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
from ipo_risk.modeling.pr_d_input_binding import (
    build_pr_d_input_binding,
    verify_oracle_v2_upstream_binding,
    verify_pr_d_input_binding,
)
from ipo_risk.schemas.canonical_modeling import canonical_hash
from ipo_risk.schemas.market import (
    MarketBasePriceSource,
    MarketDataProvenance,
    MarketDatasetSplit,
    MarketLabelAvailability,
    MarketLabelHorizon,
    MarketOutcomeLabel,
)


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _rehash(payload: dict) -> dict:
    body = {key: value for key, value in payload.items() if key != "content_hash"}
    return body | {"content_hash": canonical_hash(body)}


def _fixture(tmp_path: Path) -> tuple[dict, dict[str, Path]]:
    roots = {name: tmp_path / name for name in ("production", "market", "target", "oracle")}
    doc_names = [item.name for item in DOCUMENT_FEATURE_MANIFEST_V1.features]
    market_names = [
        name
        for raw in IPO_MARKET_CONTEXT_RAW_FEATURE_ORDER
        for name in (raw, f"{raw}__missing")
    ]
    labels = []
    for index, year in enumerate((2022, 2023, 2024), start=1):
        case_id = f"ipo_{year}_{index:05d}"
        code = f"{index:05d}.HK"
        split = "development" if year <= 2023 else "validation"
        common = {
            "case_id": case_id,
            "stock_code": code,
            "cohort_year": year,
            "listing_date": f"{year}-01-03",
            "dataset_split": split,
        }
        _write(
            roots["production"] / f"{case_id}.json",
            _rehash(
                common
                | {
                    "document_id": f"doc-{case_id}",
                    "feature_schema_version": DOCUMENT_FEATURE_MANIFEST_V1.version,
                    "feature_manifest_hash": DOCUMENT_FEATURE_MANIFEST_V1.content_hash(),
                    "feature_names": doc_names,
                    "feature_values": [None] * len(doc_names),
                }
            ),
        )
        _write(
            roots["market"] / f"{case_id}.json",
            _rehash(
                common
                | {
                    "core_feature_schema_version": IPO_MARKET_CONTEXT_FEATURE_SCHEMA_VERSION,
                    "core_feature_policy_version": IPO_MARKET_CONTEXT_FEATURE_POLICY_VERSION,
                    "core_feature_manifest_hash": IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH,
                    "feature_names": market_names,
                    "feature_values": [None if i % 2 == 0 else 1 for i in range(30)],
                }
            ),
        )
        listing = date(year, 1, 3)
        labels.append(
            MarketOutcomeLabel(
                case_id=case_id,
                stock_code=code,
                cohort_year=year,
                dataset_split=MarketDatasetSplit(split),
                listing_date=listing,
                horizon=MarketLabelHorizon.FIVE_DAYS,
                base_price=Decimal("10"),
                base_price_source=MarketBasePriceSource.OFFICIAL_LISTING_PRICE,
                target_trading_date=listing + timedelta(days=7),
                target_close=Decimal("9"),
                raw_return=Decimal("-0.1"),
                availability=MarketLabelAvailability.AVAILABLE,
                label_policy_version="v04_market_label_policy_v1",
                source="fixture",
                provenance=MarketDataProvenance(
                    source="fixture", dataset_version="v1", source_record_id=case_id
                ),
            )
        )
    builder = FiveDayOutcomeBuilder()
    threshold = builder.freeze_threshold(label for label in labels if label.cohort_year <= 2023)
    targets = [builder.build_target(label, threshold) for label in labels]
    for target in targets:
        _write(
            roots["target"] / f"{target.case_id}.json",
            target.model_dump(mode="json") | {"content_hash": target.content_hash()},
        )
    first = labels[0]
    oracle_body = {
        "case_id": first.case_id,
        "stock_code": first.stock_code,
        "cohort_year": first.cohort_year,
        "listing_date": first.listing_date.isoformat(),
        "dataset_split": first.dataset_split.value,
        "document_id": f"doc-{first.case_id}",
        "evaluation_only": True,
        "oracle_feature_schema_version": ORACLE_DOCUMENT_FEATURE_SCHEMA_VERSION,
        "oracle_feature_policy_version": ORACLE_DOCUMENT_FEATURE_POLICY_VERSION,
        "oracle_manifest_hash": ORACLE_DOCUMENT_FEATURE_MANIFEST_HASH,
        "feature_names": list(oracle_feature_names()),
        "feature_values": [0] * len(oracle_feature_names()),
    }
    _write(roots["oracle"] / f"{first.case_id}.json", _rehash(oracle_body))
    manifests = {}
    for name in ("pr_a", "pr_b"):
        manifests[name] = tmp_path / f"{name}.json"
        _write(manifests[name], {"name": name})
    pr_c_body = {
        "official_case_count": 3,
        "policy_hash": builder.policy.content_hash(),
        "threshold_hash": threshold.content_hash(),
        "target_set_hash": canonical_hash(
            sorted(
                ({"case_id": target.case_id, "content_hash": target.content_hash()} for target in targets),
                key=lambda item: item["case_id"],
            )
        ),
    }
    manifests["pr_c"] = tmp_path / "pr_c.json"
    _write(manifests["pr_c"], pr_c_body | {"freeze_manifest_hash": canonical_hash(pr_c_body)})
    kwargs = {
        "production_dir": roots["production"],
        "market_core_dir": roots["market"],
        "target_dir": roots["target"],
        "oracle_dir": roots["oracle"],
        "pr_a_manifest_path": manifests["pr_a"],
        "pr_b_manifest_path": manifests["pr_b"],
        "pr_c_manifest_path": manifests["pr_c"],
    }
    return build_pr_d_input_binding(**kwargs), kwargs


def _oracle_verifier_kwargs(
    tmp_path: Path, binding: dict, kwargs: dict[str, Path]
) -> dict[str, Path]:
    binding_path = tmp_path / "binding.json"
    _write(binding_path, binding)
    production = binding["components"]["production_document"]
    outcome = binding["components"]["outcome_target"]
    pr_d_body = {
        "official_case_count": binding["official_case_count"],
        "input_binding_manifest_hash": binding["binding_manifest_hash"],
        "production_artifact_set_hash": production["artifact_set_hash"],
        "outcome_artifact_set_hash": outcome["artifact_set_hash"],
        "pr_c_target_set_hash": binding["pr_c_target_set_hash"],
    }
    pr_d_path = tmp_path / "pr_d_freeze.json"
    _write(pr_d_path, pr_d_body | {"freeze_manifest_hash": canonical_hash(pr_d_body)})
    return {
        "production_dir": kwargs["production_dir"],
        "target_dir": kwargs["target_dir"],
        "binding_manifest_path": binding_path,
        "pr_d_freeze_manifest_path": pr_d_path,
        "pr_a_manifest_path": kwargs["pr_a_manifest_path"],
        "pr_c_manifest_path": kwargs["pr_c_manifest_path"],
    }


def test_oracle_v2_real_binding_semantics_pass(tmp_path: Path) -> None:
    binding, kwargs = _fixture(tmp_path)
    result = verify_oracle_v2_upstream_binding(
        **_oracle_verifier_kwargs(tmp_path, binding, kwargs)
    )
    assert result["upstream_binding_verified"] is True
    assert result["official_case_count"] == 3
    assert result["production_artifact_set_hash"] == binding["components"][
        "production_document"
    ]["artifact_set_hash"]
    assert result["outcome_artifact_set_hash"] == binding["components"][
        "outcome_target"
    ]["artifact_set_hash"]


@pytest.mark.parametrize(
    "field", ["cohort_year", "listing_date", "dataset_split", "stock_code", "feature_values"]
)
def test_oracle_v2_self_consistent_production_tampering_fails(
    tmp_path: Path, field: str
) -> None:
    binding, kwargs = _fixture(tmp_path)
    verify_kwargs = _oracle_verifier_kwargs(tmp_path, binding, kwargs)
    path = sorted(kwargs["production_dir"].glob("*.json"))[0]
    payload = _read(path)
    mutations = {
        "cohort_year": 2021,
        "listing_date": "2021-02-03",
        "dataset_split": "validation",
        "stock_code": "99999.HK",
    }
    if field == "feature_values":
        payload[field][0] = 999
    else:
        payload[field] = mutations[field]
    _write(path, _rehash(payload))
    with pytest.raises(ValueError, match="artifact_set_hash|identity_set"):
        verify_oracle_v2_upstream_binding(**verify_kwargs)


def _make_unavailable_target(path: Path, *, reason: str) -> None:
    payload = _read(path)
    body = {key: value for key, value in payload.items() if key != "content_hash"}
    body.update(
        {
            "availability": "unavailable",
            "missing_reason": reason,
            "target_trading_date": None,
            "raw_return_5d": None,
            "poor_performer_5d": None,
        }
    )
    from ipo_risk.schemas.outcomes import FiveDayOutcomeTarget

    target = FiveDayOutcomeTarget.model_validate(body)
    _write(path, target.model_dump(mode="json") | {"content_hash": target.content_hash()})


def test_oracle_v2_self_consistent_availability_tampering_fails(tmp_path: Path) -> None:
    binding, kwargs = _fixture(tmp_path)
    verify_kwargs = _oracle_verifier_kwargs(tmp_path, binding, kwargs)
    _make_unavailable_target(
        sorted(kwargs["target_dir"].glob("*.json"))[0], reason="missing_base_price"
    )
    with pytest.raises(ValueError, match="artifact_set_hash|target_set_hash"):
        verify_oracle_v2_upstream_binding(**verify_kwargs)


def test_oracle_v2_self_consistent_missing_reason_tampering_fails(tmp_path: Path) -> None:
    _binding, initial_kwargs = _fixture(tmp_path)
    target_path = sorted(initial_kwargs["target_dir"].glob("*.json"))[0]
    _make_unavailable_target(target_path, reason="missing_base_price")
    pr_c = _read(initial_kwargs["pr_c_manifest_path"])
    target_entries = []
    from ipo_risk.schemas.outcomes import FiveDayOutcomeTarget

    for path in sorted(initial_kwargs["target_dir"].glob("*.json")):
        payload = _read(path)
        target = FiveDayOutcomeTarget.model_validate(
            {key: value for key, value in payload.items() if key != "content_hash"}
        )
        target_entries.append({"case_id": target.case_id, "content_hash": target.content_hash()})
    pr_c["target_set_hash"] = canonical_hash(target_entries)
    pr_c["freeze_manifest_hash"] = canonical_hash(
        {key: value for key, value in pr_c.items() if key != "freeze_manifest_hash"}
    )
    _write(initial_kwargs["pr_c_manifest_path"], pr_c)
    binding = build_pr_d_input_binding(**initial_kwargs)
    verify_kwargs = _oracle_verifier_kwargs(tmp_path, binding, initial_kwargs)
    _make_unavailable_target(target_path, reason="no_eligible_session")
    with pytest.raises(ValueError, match="artifact_set_hash|target_set_hash"):
        verify_oracle_v2_upstream_binding(**verify_kwargs)


@pytest.mark.parametrize("component", ["production_dir", "target_dir"])
@pytest.mark.parametrize("operation", ["missing", "orphan"])
def test_oracle_v2_missing_or_orphan_upstream_fails(
    tmp_path: Path, component: str, operation: str
) -> None:
    binding, kwargs = _fixture(tmp_path)
    verify_kwargs = _oracle_verifier_kwargs(tmp_path, binding, kwargs)
    directory = kwargs[component]
    source = sorted(directory.glob("*.json"))[0]
    if operation == "missing":
        source.unlink()
    else:
        payload = _read(source)
        payload["case_id"] = "ipo_2021_99999"
        if component == "target_dir":
            body = {key: value for key, value in payload.items() if key != "content_hash"}
            from ipo_risk.schemas.outcomes import FiveDayOutcomeTarget

            target = FiveDayOutcomeTarget.model_validate(body)
            payload = target.model_dump(mode="json") | {"content_hash": target.content_hash()}
        else:
            payload = _rehash(payload)
        _write(directory / "ipo_2021_99999.json", payload)
    with pytest.raises(ValueError, match="count_mismatch|case_set_mismatch"):
        verify_oracle_v2_upstream_binding(**verify_kwargs)


def test_oracle_v2_self_consistent_binding_manifest_tampering_fails(tmp_path: Path) -> None:
    binding, kwargs = _fixture(tmp_path)
    verify_kwargs = _oracle_verifier_kwargs(tmp_path, binding, kwargs)
    payload = _read(verify_kwargs["binding_manifest_path"])
    payload["components"]["production_document"]["artifact_set_hash"] = "0" * 64
    body = {key: value for key, value in payload.items() if key != "binding_manifest_hash"}
    payload["binding_manifest_hash"] = canonical_hash(body)
    _write(verify_kwargs["binding_manifest_path"], payload)
    with pytest.raises(ValueError, match="committed_binding_anchor_mismatch"):
        verify_oracle_v2_upstream_binding(**verify_kwargs)


def test_oracle_v2_self_consistent_pr_c_manifest_tampering_fails(tmp_path: Path) -> None:
    binding, kwargs = _fixture(tmp_path)
    verify_kwargs = _oracle_verifier_kwargs(tmp_path, binding, kwargs)
    payload = _read(kwargs["pr_c_manifest_path"])
    payload["target_set_hash"] = "0" * 64
    body = {key: value for key, value in payload.items() if key != "freeze_manifest_hash"}
    payload["freeze_manifest_hash"] = canonical_hash(body)
    _write(kwargs["pr_c_manifest_path"], payload)
    with pytest.raises(ValueError, match="manifest_identity|freeze_identity|target_set"):
        verify_oracle_v2_upstream_binding(**verify_kwargs)


@pytest.mark.parametrize("field", ["freeze_manifest_hash", "target_set_hash"])
def test_pr_c_freeze_identity_tampering_fails(tmp_path: Path, field: str) -> None:
    binding, kwargs = _fixture(tmp_path)
    manifest = _read(kwargs["pr_c_manifest_path"])
    manifest[field] = "0" * 64
    if field == "target_set_hash":
        manifest["freeze_manifest_hash"] = canonical_hash(
            {key: value for key, value in manifest.items() if key != "freeze_manifest_hash"}
        )
    _write(kwargs["pr_c_manifest_path"], manifest)
    with pytest.raises(ValueError, match="freeze_manifest_hash|target_set_hash"):
        verify_pr_d_input_binding(binding, **kwargs)


@pytest.mark.parametrize(
    ("directory_key", "mutation"),
    [
        ("production_dir", "feature_values"),
        ("market_core_dir", "feature_values"),
        ("target_dir", "source_label_hash"),
    ],
)
def test_self_consistent_bulk_mutation_fails(
    tmp_path: Path, directory_key: str, mutation: str
) -> None:
    binding, kwargs = _fixture(tmp_path)
    path = sorted(kwargs[directory_key].glob("*.json"))[0]
    payload = _read(path)
    if mutation == "feature_values":
        payload[mutation][0] = 999
        payload = _rehash(payload)
    else:
        payload[mutation] = "f" * 64
        body = {key: value for key, value in payload.items() if key != "content_hash"}
        from ipo_risk.schemas.outcomes import FiveDayOutcomeTarget

        target = FiveDayOutcomeTarget.model_validate(body)
        payload["content_hash"] = target.content_hash()
    _write(path, payload)
    with pytest.raises(ValueError, match="artifact_set_hash|target_set_hash"):
        verify_pr_d_input_binding(binding, **kwargs)


def test_duplicate_internal_case_fails(tmp_path: Path) -> None:
    _binding, kwargs = _fixture(tmp_path)
    source = sorted(kwargs["production_dir"].glob("*.json"))[0]
    _write(kwargs["production_dir"] / "duplicate.json", _read(source))
    with pytest.raises(ValueError, match="filename_case_mismatch"):
        build_pr_d_input_binding(**kwargs)


def test_missing_official_artifact_fails(tmp_path: Path) -> None:
    _binding, kwargs = _fixture(tmp_path)
    sorted(kwargs["market_core_dir"].glob("*.json"))[0].unlink()
    with pytest.raises(ValueError, match="case_set_mismatch"):
        build_pr_d_input_binding(**kwargs)


def test_orphan_case_fails(tmp_path: Path) -> None:
    _binding, kwargs = _fixture(tmp_path)
    source = sorted(kwargs["market_core_dir"].glob("*.json"))[0]
    payload = _read(source)
    payload["case_id"] = "ipo_2021_99999"
    payload = _rehash(payload)
    _write(kwargs["market_core_dir"] / "ipo_2021_99999.json", payload)
    with pytest.raises(ValueError, match="case_set_mismatch"):
        build_pr_d_input_binding(**kwargs)


def test_filename_internal_case_mismatch_fails(tmp_path: Path) -> None:
    _binding, kwargs = _fixture(tmp_path)
    path = sorted(kwargs["target_dir"].glob("*.json"))[0]
    path.rename(kwargs["target_dir"] / "wrong_case.json")
    with pytest.raises(ValueError, match="filename_case_mismatch"):
        build_pr_d_input_binding(**kwargs)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("feature_schema_version", "drift", "schema version mismatch"),
        ("feature_names", ["drift"], "feature order mismatch"),
    ],
)
def test_production_schema_or_feature_order_drift_fails(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    _binding, kwargs = _fixture(tmp_path)
    path = sorted(kwargs["production_dir"].glob("*.json"))[0]
    payload = _read(path)
    payload[field] = value
    _write(path, _rehash(payload))
    with pytest.raises(ValueError, match=message):
        build_pr_d_input_binding(**kwargs)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("hash", "content hash mismatch"),
        ("schema", "schema version mismatch"),
        ("order", "feature order mismatch"),
        ("evaluation", "evaluation-only"),
    ],
)
def test_oracle_governance_corruption_fails(
    tmp_path: Path, mutation: str, message: str
) -> None:
    _binding, kwargs = _fixture(tmp_path)
    path = next(kwargs["oracle_dir"].glob("*.json"))
    payload = _read(path)
    if mutation == "hash":
        payload["content_hash"] = "0" * 64
    elif mutation == "schema":
        payload["oracle_feature_schema_version"] = "drift"
        payload = _rehash(payload)
    elif mutation == "order":
        payload["feature_names"] = list(reversed(payload["feature_names"]))
        payload = _rehash(payload)
    else:
        payload["evaluation_only"] = False
        payload = _rehash(payload)
    _write(path, payload)
    with pytest.raises(ValueError, match=message):
        build_pr_d_input_binding(**kwargs)
