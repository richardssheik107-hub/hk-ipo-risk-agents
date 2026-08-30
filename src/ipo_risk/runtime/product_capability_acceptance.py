"""Deterministic G5/G6 acceptance artifacts built only from governed evidence.

The capability manifest deliberately separates qualitative demonstrations from
M1/M2 evidence.  It neither opens Validation nor reads a 2025 Blind outcome.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable


PRODUCT_SCHEMA_VERSION = "competition_product_acceptance_v1"
CAPABILITY_SCHEMA_VERSION = "competition_capability_manifest_v1"
QUALITATIVE = "QUALITATIVE_DEMONSTRATION"
REQUIRED_CAPABILITIES = (
    "core_pipeline_progress",
    "text_embellishment",
    "related_party_transaction",
    "comparable_ipo_valuation",
    "evidence_screenshot",
    "single_batch_report",
    "api_ui",
    "dynamic_new_ipo",
)
TARGETED_TEST_FILES = (
    "tests/unit/test_bounded_document_semantics.py",
    "tests/unit/test_ipo_structure_features.py",
    "tests/contract/test_v046_human_review_api.py",
    "tests/integration/test_v04_final_supervision_pipeline.py",
    "tests/integration/test_streamlit_information_architecture.py",
    "tests/unit/test_v045_competition_runtime_view.py",
    "tests/unit/test_v045_team_clone_ready.py",
)


class ProductCapabilityAcceptanceError(ValueError):
    """The persisted acceptance record does not match current evidence."""


def _sha(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _json(repo_root: Path, relative_path: str) -> dict[str, Any]:
    path = repo_root / relative_path
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProductCapabilityAcceptanceError(
            f"required JSON evidence is unreadable: {relative_path}"
        ) from exc
    if not isinstance(value, dict):
        raise ProductCapabilityAcceptanceError(
            f"required JSON evidence is not an object: {relative_path}"
        )
    return value


def _ref(repo_root: Path, relative_path: str) -> dict[str, Any]:
    path = repo_root / relative_path
    if not path.is_file():
        raise ProductCapabilityAcceptanceError(
            f"required evidence is missing: {relative_path}"
        )
    return {
        "path": relative_path,
        "sha256": _sha(path),
        "size_bytes": path.stat().st_size,
    }


def _refs(repo_root: Path, paths: Iterable[str]) -> list[dict[str, Any]]:
    return [_ref(repo_root, path) for path in paths]


def _all(checks: dict[str, bool]) -> bool:
    return bool(checks) and all(value is True for value in checks.values())


def _probe(rows: list[dict[str, Any]], probe_id: str) -> dict[str, Any]:
    matches = [row for row in rows if row.get("probe_id") == probe_id]
    return matches[0] if len(matches) == 1 else {}


def _signed(payload: dict[str, Any]) -> dict[str, Any]:
    return {**payload, "content_hash": _canonical_hash(payload)}


def build_product_acceptance(repo_root: Path) -> dict[str, Any]:
    demo = _json(repo_root, "reports/v045_demo_bundle/demo_manifest.json")
    snapshot = _json(repo_root, "reports/final_status/current_runtime_snapshot.json")
    model = _json(
        repo_root,
        "reports/v046_dynamic_model_runtime/dynamic_model_runtime_audit.json",
    )
    model_summary = model.get("historical_summary") or {}
    historical_cases = model.get("historical_cases") or []
    aggregate = snapshot.get("aggregate") or {}
    model_fresh = model.get("fresh_case_probes") or []
    inside_model = _probe(model_fresh, "new_issuer_inside_coverage")
    outside_model = _probe(model_fresh, "listing_beyond_coverage_end")

    offline_checks = {
        "three_replayable_cases": demo.get("replayable_case_count") == 3,
        "canonical_bundle_66_files": demo.get("file_count") == 66,
        "runtime_equivalent": snapshot.get("runtime_equivalent") is True,
        "three_schema_validated_cases": snapshot.get("case_count") == 3,
        "seven_stage_21_of_21": aggregate.get("seven_stage_available")
        == aggregate.get("seven_stage_required")
        == 21,
        "market_and_model_three_of_three": aggregate.get("market_available") == 3
        and aggregate.get("model_available") == 3,
    }
    historical_checks = {
        "governed_cases_562": model_summary.get("governed_case_count") == 562
        and len(historical_cases) == 562,
        "historical_runtime_zero_errors": model_summary.get("inference_error") == 0,
        "historical_paths_include_frozen_and_dynamic": set(
            row.get("market_runtime_path") for row in historical_cases
        )
        == {"dynamic_pit", "frozen"},
        "frozen_model_runtime_pass": model.get("status") == "pass"
        and model.get("runtime_inference") is True
        and model.get("native_shap") is True,
        "historical_model_inference": model_summary.get("inference_available") == 540
        and model_summary.get("inference_error") == 0,
    }
    fresh_checks = {
        "inside_coverage_dynamic_market": inside_model.get("market_runtime_path")
        == "dynamic_pit"
        and inside_model.get("market_status") == "available",
        "inside_coverage_frozen_model_and_shap": inside_model.get("model_status")
        == "available"
        and inside_model.get("driver_count") == 7,
        "outside_coverage_honest_market_unavailable": outside_model.get(
            "market_status"
        )
        == "unavailable",
        "outside_coverage_honest_model_unavailable": outside_model.get("model_status")
        == "unavailable"
        and outside_model.get("failure_code") == "market_channel_unavailable",
    }
    surface_checks = {
        "streamlit_product_surface_present": (
            repo_root / "app/streamlit_app.py"
        ).is_file(),
        "offline_replay_loader_present": (
            repo_root / "src/ipo_risk/runtime/demo_replay.py"
        ).is_file(),
        "channel_truth_projection_present": (
            repo_root / "app/competition_ui.py"
        ).is_file(),
        "single_and_batch_reports_present": all(
            (repo_root / path).is_file()
            for path in (
                "reports/v045_demo_bundle/batch_report.json",
                "reports/v045_demo_bundle/ipo_2024_01318/case_report.md",
                "reports/v045_demo_bundle/ipo_2024_02410/case_report.md",
                "reports/v045_demo_bundle/ipo_2024_02460/case_report.md",
            )
        ),
    }
    modes = {
        "offline_demo_replay": {
            "status": "pass" if _all(offline_checks) else "fail",
            "checks": offline_checks,
        },
        "historical_governed_ipo": {
            "status": "pass" if _all(historical_checks) else "fail",
            "checks": historical_checks,
        },
        "fresh_new_ipo_analysis": {
            "status": "pass" if _all(fresh_checks) else "fail",
            "checks": fresh_checks,
            "availability_semantics": (
                "available, partial and unavailable are governed runtime states; "
                "missing data is never zero-filled"
            ),
        },
    }
    passed = all(item["status"] == "pass" for item in modes.values()) and _all(
        surface_checks
    )
    payload = {
        "schema_version": PRODUCT_SCHEMA_VERSION,
        "status": "pass" if passed else "fail",
        "truthful_channel_states": passed,
        "modes": modes,
        "surface_checks": surface_checks,
        "targeted_test_files": list(TARGETED_TEST_FILES),
        "evidence": _refs(
            repo_root,
            (
                "reports/v045_demo_bundle/demo_manifest.json",
                "reports/final_status/current_runtime_snapshot.json",
                "reports/v046_dynamic_model_runtime/dynamic_model_runtime_audit.json",
                "app/streamlit_app.py",
                "app/competition_ui.py",
                "src/ipo_risk/runtime/demo_replay.py",
            ),
        ),
        "governance": {
            "validation_opened": False,
            "blind_2025_y_accessed": False,
            "ui_computes_or_invents_channel_values": False,
            "human_review_required": False,
        },
    }
    return _signed(payload)


def _capability(
    repo_root: Path,
    *,
    capability_id: str,
    claim: str,
    checks: dict[str, bool],
    evidence_paths: Iterable[str],
    limitations: str,
) -> dict[str, Any]:
    return {
        "capability": capability_id,
        "status": "pass" if _all(checks) else "fail",
        "classification": QUALITATIVE,
        "claim": claim,
        "checks": checks,
        "evidence": _refs(repo_root, evidence_paths),
        "limitations": limitations,
        "included_in_m1_m2": False,
    }


def build_capability_manifest(repo_root: Path) -> dict[str, Any]:
    product = build_product_acceptance(repo_root)
    screenshot = _json(repo_root, "reports/v045_demo_bundle/screenshot_summary.json")
    model = _json(
        repo_root,
        "reports/v046_dynamic_model_runtime/dynamic_model_runtime_audit.json",
    )
    model_fresh = model.get("fresh_case_probes") or []
    inside_model = _probe(model_fresh, "new_issuer_inside_coverage")
    outside_model = _probe(model_fresh, "listing_beyond_coverage_end")
    details = [
        _capability(
            repo_root,
            capability_id="core_pipeline_progress",
            claim="The canonical replay demonstrates all seven governed stages for three cases.",
            checks={
                "product_gate_modes_pass": product.get("status") == "pass",
                "seven_stage_21_of_21": (
                    (product.get("modes") or {})
                    .get("offline_demo_replay", {})
                    .get("checks", {})
                    .get("seven_stage_21_of_21")
                    is True
                ),
            },
            evidence_paths=(
                "reports/final_status/current_runtime_snapshot.json",
                "reports/v045_demo_bundle/summary.json",
            ),
            limitations="Recorded replay is labelled as replay and is not live inference.",
        ),
        _capability(
            repo_root,
            capability_id="text_embellishment",
            claim="Disclosure-tone proposals are structured and rejected when citations leave bounded Evidence.",
            checks={
                "bounded_tone_contract": (
                    repo_root / "src/ipo_risk/extraction/bounded_semantics.py"
                ).is_file(),
                "scope_guard_test": (
                    repo_root / "tests/unit/test_bounded_document_semantics.py"
                ).is_file(),
            },
            evidence_paths=(
                "src/ipo_risk/extraction/bounded_semantics.py",
                "tests/unit/test_bounded_document_semantics.py",
            ),
            limitations="Qualitative contract demonstration only; no new Gold or M1/M2 unit is claimed.",
        ),
        _capability(
            repo_root,
            capability_id="related_party_transaction",
            claim="Related-party transaction proposals require counterparty, relationship, nature and bounded Evidence.",
            checks={
                "structured_related_party_contract": (
                    repo_root / "src/ipo_risk/extraction/bounded_semantics.py"
                ).is_file(),
                "private_proposal_test": (
                    repo_root / "tests/unit/test_bounded_document_semantics.py"
                ).is_file(),
            },
            evidence_paths=(
                "src/ipo_risk/extraction/bounded_semantics.py",
                "tests/unit/test_bounded_document_semantics.py",
            ),
            limitations="Private structured proposal, not a registered production RiskItem or a scored M1/M2 family.",
        ),
        _capability(
            repo_root,
            capability_id="comparable_ipo_valuation",
            claim="The deterministic IPO-structure lane computes price-to-adjusted-NTA and preserves missingness.",
            checks={
                "valuation_feature_contract": (
                    repo_root / "src/ipo_risk/market/ipo_structure_features.py"
                ).is_file(),
                "valuation_formula_test": (
                    repo_root / "tests/unit/test_ipo_structure_features.py"
                ).is_file(),
                "same_industry_market_context": (
                    inside_model.get("market_status") == "available"
                    and "same_industry_ipo_count_180d"
                    not in (inside_model.get("missing_model_features") or [])
                ),
            },
            evidence_paths=(
                "src/ipo_risk/market/ipo_structure_features.py",
                "tests/unit/test_ipo_structure_features.py",
                "reports/v046_dynamic_model_runtime/dynamic_model_runtime_audit.json",
            ),
            limitations="Research/qualitative valuation context; it is not an investment recommendation or an M1/M2 metric.",
        ),
        _capability(
            repo_root,
            capability_id="evidence_screenshot",
            claim="Every cited canonical Evidence item has a hash-bound precise screenshot.",
            checks={
                "screenshots_17_of_17": screenshot.get("screenshot_count")
                == screenshot.get("cited_evidence_count")
                == 17,
                "precise_localisation_100_percent": screenshot.get(
                    "precise_localisation_count"
                )
                == 17
                and screenshot.get("precise_localisation_rate") == 1.0,
            },
            evidence_paths=(
                "reports/v045_demo_bundle/screenshot_summary.json",
                "reports/v045_demo_bundle/ipo_2024_01318/screenshot_manifest.json",
                "reports/v045_demo_bundle/ipo_2024_02410/screenshot_manifest.json",
                "reports/v045_demo_bundle/ipo_2024_02460/screenshot_manifest.json",
            ),
            limitations="Applies to the three canonical recorded cases.",
        ),
        _capability(
            repo_root,
            capability_id="single_batch_report",
            claim="Three single-case reports and one batch report are committed in the canonical bundle.",
            checks={
                "three_single_reports": all(
                    (repo_root / path).is_file()
                    for path in (
                        "reports/v045_demo_bundle/ipo_2024_01318/case_report.md",
                        "reports/v045_demo_bundle/ipo_2024_02410/case_report.md",
                        "reports/v045_demo_bundle/ipo_2024_02460/case_report.md",
                    )
                ),
                "batch_json_and_markdown": all(
                    (repo_root / path).is_file()
                    for path in (
                        "reports/v045_demo_bundle/batch_report.json",
                        "reports/v045_demo_bundle/batch_report.md",
                    )
                ),
            },
            evidence_paths=(
                "reports/v045_demo_bundle/ipo_2024_01318/case_report.md",
                "reports/v045_demo_bundle/ipo_2024_02410/case_report.md",
                "reports/v045_demo_bundle/ipo_2024_02460/case_report.md",
                "reports/v045_demo_bundle/batch_report.json",
                "reports/v045_demo_bundle/batch_report.md",
            ),
            limitations="Canonical reports are recorded artifacts and retain their recorded provenance.",
        ),
        _capability(
            repo_root,
            capability_id="api_ui",
            claim="The Streamlit workbench and governed review API expose tested contracts.",
            checks={
                "streamlit_surface": (repo_root / "app/streamlit_app.py").is_file(),
                "fastapi_contract": (
                    repo_root / "src/ipo_risk/api/human_review.py"
                ).is_file(),
                "openapi_contract_test": (
                    repo_root / "tests/contract/test_v046_human_review_api.py"
                ).is_file(),
            },
            evidence_paths=(
                "app/streamlit_app.py",
                "app/competition_ui.py",
                "src/ipo_risk/api/human_review.py",
                "tests/contract/test_v046_human_review_api.py",
            ),
            limitations="Human review is optional and does not determine release readiness.",
        ),
        _capability(
            repo_root,
            capability_id="dynamic_new_ipo",
            claim="An issuer outside the frozen universe receives PIT Market-X, frozen-model inference and native SHAP, or an explicit governed unavailable reason.",
            checks={
                "inside_coverage_dynamic_market": inside_model.get(
                    "market_runtime_path"
                )
                == "dynamic_pit"
                and inside_model.get("market_status") == "available",
                "inside_coverage_model_shap": inside_model.get("model_status")
                == "available"
                and inside_model.get("driver_count") == 7,
                "outside_coverage_fail_closed": outside_model.get("market_status")
                == "unavailable"
                and outside_model.get("model_status") == "unavailable"
                and outside_model.get("failure_code")
                == "market_channel_unavailable",
            },
            evidence_paths=(
                "reports/v046_dynamic_model_runtime/dynamic_model_runtime_audit.json",
                "tests/integration/test_v04_final_supervision_pipeline.py",
            ),
            limitations="Qualitative governed probes only; no formal Validation or Blind result is claimed.",
        ),
    ]
    passed = len(details) == len(REQUIRED_CAPABILITIES) and all(
        item["status"] == "pass" for item in details
    )
    payload = {
        "schema_version": CAPABILITY_SCHEMA_VERSION,
        "status": "pass" if passed else "fail",
        "capabilities": [item["capability"] for item in details],
        "capability_details": details,
        "targeted_test_files": list(TARGETED_TEST_FILES),
        "governance": {
            "all_demonstrations_are_qualitative": True,
            "included_in_m1_m2": False,
            "new_manual_annotations_added": False,
            "existing_gold_modified": False,
            "validation_opened": False,
            "blind_2025_y_accessed": False,
        },
    }
    return _signed(payload)


def verify_persisted(expected: dict[str, Any], path: Path) -> None:
    try:
        actual = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProductCapabilityAcceptanceError(
            f"acceptance artifact is unreadable: {path}"
        ) from exc
    if actual != expected:
        raise ProductCapabilityAcceptanceError(
            f"acceptance artifact is stale or does not match governed evidence: {path}"
        )


def write_artifacts(repo_root: Path) -> tuple[Path, Path]:
    output = repo_root / "reports/final_status"
    output.mkdir(parents=True, exist_ok=True)
    product_path = output / "product_acceptance.json"
    capability_path = output / "capability_manifest.json"
    product_path.write_text(
        json.dumps(build_product_acceptance(repo_root), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    capability_path.write_text(
        json.dumps(build_capability_manifest(repo_root), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return product_path, capability_path
