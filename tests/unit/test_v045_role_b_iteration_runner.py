from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.run_v045_role_b_iteration as iteration_runner
from scripts.run_v045_role_b_iteration import (
    IterationRunnerError,
    _build_runtime_cases_manifest,
    _build_subset,
    _verify_subset,
    select_fixed_debug_cases,
)


FAMILIES = (
    "cash_burn_pressure",
    "customer_concentration",
    "redemption_rights",
    "supplier_concentration",
)


def _manifest() -> dict:
    risk_units = []
    evidence_units = []
    for index in range(12):
        case_id = f"ipo_202{index // 4}_{index:05d}"
        family = FAMILIES[index % len(FAMILIES)]
        risk_units.append(
            {
                "case_id": case_id,
                "stock_code": f"{index:04d}.HK",
                "split": "development",
                "primary_scope": True,
                "evaluable_positive": True,
                "competition_risk_family": family,
            }
        )
        if index % 3 == 0:
            second = FAMILIES[(index + 1) % len(FAMILIES)]
            risk_units.append(
                {
                    "case_id": case_id,
                    "stock_code": f"{index:04d}.HK",
                    "split": "development",
                    "primary_scope": True,
                    "evaluable_positive": True,
                    "competition_risk_family": second,
                }
            )
        for evidence_index in range(1 + (index % 4)):
            evidence_units.append(
                {
                    "case_id": case_id,
                    "split": "development",
                    "primary_scope": True,
                    "evidence_unit_id": f"{case_id}-{evidence_index}",
                }
            )

    # A tempting Validation case must never enter the debug subset.
    validation_id = "ipo_2024_99999"
    for family in FAMILIES:
        risk_units.append(
            {
                "case_id": validation_id,
                "stock_code": "9999.HK",
                "split": "validation",
                "primary_scope": True,
                "evaluable_positive": True,
                "competition_risk_family": family,
            }
        )
    for evidence_index in range(50):
        evidence_units.append(
            {
                "case_id": validation_id,
                "split": "validation",
                "primary_scope": True,
                "evidence_unit_id": f"validation-{evidence_index}",
            }
        )

    return {
        "metric_protocol_version": "v045_competition_metric_protocol_v2_existing_gold_only",
        "manifest_hash": "frozen-manifest-hash",
        "risk_units": risk_units,
        "evidence_units": evidence_units,
    }


def test_fixed10_selection_is_deterministic_and_development_only() -> None:
    manifest = _manifest()
    first = select_fixed_debug_cases(manifest, size=10)
    second = select_fixed_debug_cases(copy.deepcopy(manifest), size=10)

    assert first == second
    assert len(first) == 10
    assert len(set(first)) == 10
    assert "ipo_2024_99999" not in first


def test_subset_payload_is_hash_bound_to_existing_gold_manifest() -> None:
    manifest = _manifest()
    subset = _build_subset(manifest, size=10)

    _verify_subset(subset, manifest, size=10)
    assert subset["split"] == "development"
    assert subset["debug_subset_only"] is True
    assert subset["validation_opened"] is False
    assert subset["blind_2025_outcome_accessed"] is False

    drifted = copy.deepcopy(manifest)
    drifted["manifest_hash"] = "different-manifest-hash"
    with pytest.raises(IterationRunnerError, match="manifest drift"):
        _verify_subset(subset, drifted, size=10)


def test_runtime_cases_manifest_distinguishes_full_development_from_debug(
    tmp_path: Path,
) -> None:
    bridge = tmp_path / "bridge.csv"
    bridge.write_text(
        "case_id,selected_name\nipo_2023_00001,Issuer One\n",
        encoding="utf-8",
    )
    destination = tmp_path / "runtime_cases.json"
    subset = {
        "debug_subset_only": False,
        "cases": [{"case_id": "ipo_2023_00001"}],
    }

    # A caller must prove exact full-universe membership; the legacy flag alone
    # is not sufficient because child filters inherit it.
    _build_runtime_cases_manifest(subset, bridge, destination)
    unproven_payload = iteration_runner._read_json(destination)
    assert unproven_payload["scope"] == "debug_subset"

    _build_runtime_cases_manifest(
        subset,
        bridge,
        destination,
        full_development=True,
    )

    payload = iteration_runner._read_json(destination)
    assert payload["manifest_version"] == "v046_role_b_development_runtime_cases_v1"
    assert payload["scope"] == "full_development"
    assert "ALL-Development" in payload["note"]

    _build_runtime_cases_manifest(subset, bridge, destination)
    debug_payload = iteration_runner._read_json(destination)
    assert debug_payload["manifest_version"] == "v045_role_b_fixed10_runtime_cases_v1"
    assert debug_payload["scope"] == "debug_subset"


def test_subset_tampering_fails_closed() -> None:
    manifest = _manifest()
    subset = _build_subset(manifest, size=10)
    subset["cases"][0]["case_id"] = "ipo_2020_tampered"

    with pytest.raises(IterationRunnerError, match="hash mismatch"):
        _verify_subset(subset, manifest, size=10)


def test_full_split_evaluation_omits_debug_case_filter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    commands: list[list[str]] = []

    def fake_run(command, *, cwd, log_path):
        commands.append(command)
        output_dir = Path(command[command.index("--output-dir") + 1])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "document_benchmark_summary.json").write_text(
            "{}", encoding="utf-8"
        )
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(iteration_runner, "_run_captured", fake_run)

    iteration_runner._evaluate(
        root=tmp_path,
        coverage_path=tmp_path / "coverage.json",
        results_path=tmp_path / "results.jsonl",
        case_ids=None,
        output_dir=tmp_path / "full",
        log_path=tmp_path / "full.log",
    )
    iteration_runner._evaluate(
        root=tmp_path,
        coverage_path=tmp_path / "coverage.json",
        results_path=tmp_path / "results.jsonl",
        case_ids=["ipo_2020_00001"],
        output_dir=tmp_path / "debug",
        log_path=tmp_path / "debug.log",
    )

    assert "--case-ids" not in commands[0]
    assert commands[1][commands[1].index("--case-ids") + 1] == "ipo_2020_00001"
