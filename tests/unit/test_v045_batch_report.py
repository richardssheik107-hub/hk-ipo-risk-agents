"""A portfolio view is where a summary is most tempted to say more than the runs.

The batch report puts several companies in an order, and an order invites the
reader to treat it as a verdict.  These tests hold it to the opposite: the
ordering rule travels with the ordering, a case that found nothing stays a case
that found nothing, an unavailable channel contributes no fact, an unreviewed
case does not read as approved, and a deterministic fallback is never counted as
a real-provider arbitration.

A declared case that did not execute also has to survive into the report. A
batch that silently shrinks to the cases that worked is the one failure mode
that would make every aggregate below it wrong.
"""

from __future__ import annotations

import json
from pathlib import Path
import runpy

import pytest

from ipo_risk.runtime.batch_report import (
    BATCH_REPORT_SCHEMA_VERSION,
    TRIAGE_RULE,
    build_batch_report,
    render_batch_report,
)


def _risk(code: str, level: str, *, evidence: int = 1, calculation: bool = False) -> dict:
    return {
        "risk_id": f"risk-{code}",
        "risk_code": code,
        "level": level,
        "verification_status": "verified",
        "agent_name": "financial",
        "conclusion": f"{code} conclusion",
        "evidence": [{"evidence_id": f"e-{code}-{index}"} for index in range(evidence)],
        "calculation": {"skill_name": "cash_runway"} if calculation else None,
    }


def _result(company: str, verified: list[dict], pending: list[dict] | None = None) -> dict:
    return {
        "company_name": company,
        "status": "completed",
        "verified_risks": verified,
        "pending_risks": pending or [],
        "rejected_risks": [],
    }


def _case(case_id: str, stock_code: str, **overrides) -> dict:
    case = {
        "case_id": case_id,
        "stock_code": stock_code,
        "listing_date": "2024-08-20",
        "status": "completed",
        "analysis_id": f"analysis-{case_id}",
        "channel_states": {
            "document": "available",
            "market": "unavailable_error",
            "model": "disabled",
            "rule": "available",
        },
        "conflict_count": 2,
        "conflict_statuses": {"resolved": 2},
        "recheck_attempted": 1,
        "llm_synthesis_status": "available",
        "llm_synthesis_outcome": "accepted",
        "llm_synthesis_reason": "grounded supervisory synthesis available",
        "deterministic_severity_floor": "critical",
        "evidence_export_row_count": 4,
        "traceability": {"overall_traceability": 1.0},
        "probability_claimed": False,
        "creates_no_new_risk": True,
        "prospectus_verification": {"sha256": "ab" * 32},
        "gate_e1": {
            "satisfied": True,
            "successful_llm_arbitration": True,
            "provider_is_real_remote": True,
            "deterministic_fallback_used": False,
            "provider_name": "openai_compatible",
            "scope_corrected": False,
        },
    }
    case.update(overrides)
    return case


def _summary(cases: list[dict], **overrides) -> dict:
    summary = {
        "demo_version": "v045_role_e_demo_v2",
        "config": "configs/v045_competition_ai.yaml",
        "code_base_sha": "cd" * 20,
        "code_base_dirty": False,
        "cases_manifest_sha256": "ef" * 32,
        "config_sha256": "12" * 32,
        "declared_case_count": len(cases),
        "executed_case_count": len(cases),
        "all_prospectus_sha256_verified": True,
        "outcome_labels_accessed": False,
        "blind_2025_y_accessed": False,
        "cases": cases,
    }
    summary.update(overrides)
    return summary


def _report(**kwargs) -> dict:
    cases = [
        _case("ipo_2024_02410", "2410.HK"),
        _case("ipo_2024_02460", "2460.HK", deterministic_severity_floor="medium"),
        _case("ipo_2024_01318", "1318.HK", deterministic_severity_floor="low"),
    ]
    results = {
        "ipo_2024_02410": _result(
            "A", [_risk("cash_runway", "critical", evidence=2, calculation=True),
                  _risk("redemption_rights", "medium")],
            [_risk("material_litigation_compliance", "medium")],
        ),
        "ipo_2024_02460": _result("B", [_risk("redemption_rights", "medium")]),
        "ipo_2024_01318": _result("C", []),
    }
    payload = {"summary": _summary(cases), "results": results}
    payload.update(kwargs)
    return build_batch_report(**payload)


def test_the_order_is_by_recorded_severity_and_carries_its_own_rule() -> None:
    report = _report()
    assert report["schema_version"] == BATCH_REPORT_SCHEMA_VERSION
    assert [case["case_id"] for case in report["cases"]] == [
        "ipo_2024_02410",
        "ipo_2024_02460",
        "ipo_2024_01318",
    ]
    assert report["triage_rule"] == TRIAGE_RULE
    for phrase in ("not a score", "not a probability", "not a prediction"):
        assert phrase in report["triage_rule"]
    assert report["triage_rule"] in render_batch_report(report)


def test_a_case_that_found_nothing_is_shown_as_finding_nothing() -> None:
    report = _report()
    empty = [case for case in report["cases"] if case["case_id"] == "ipo_2024_01318"][0]
    assert empty["verified_risk_count"] == 0
    assert empty["verified_level_counts"] == {"critical": 0, "high": 0, "medium": 0, "low": 0}
    assert "不代填" in render_batch_report(report)


def test_a_declared_case_that_never_ran_stays_in_the_report() -> None:
    cases = [
        _case("ipo_2024_02410", "2410.HK"),
        {
            "case_id": "ipo_2024_09999",
            "stock_code": "9999.HK",
            "status": "unavailable_prospectus",
            "reason": "declared prospectus is not present locally",
        },
    ]
    report = build_batch_report(
        summary=_summary(cases, declared_case_count=2, executed_case_count=1),
        results={"ipo_2024_02410": _result("A", [_risk("cash_runway", "critical")])},
    )
    assert [case["case_id"] for case in report["unexecuted_cases"]] == ["ipo_2024_09999"]
    assert report["aggregate"]["case_count"] == 1
    assert "not present locally" in render_batch_report(report)


def test_a_deterministic_fallback_is_never_counted_as_real_provider_arbitration() -> None:
    fallback_gate = {
        "satisfied": False,
        "successful_llm_arbitration": False,
        "provider_is_real_remote": False,
        "deterministic_fallback_used": True,
        "provider_name": "mock",
        "scope_corrected": False,
    }
    report = build_batch_report(
        summary=_summary(
            [
                _case(
                    "ipo_2024_02410",
                    "2410.HK",
                    gate_e1=fallback_gate,
                    llm_synthesis_outcome="deterministic_fallback",
                )
            ]
        ),
        results={"ipo_2024_02410": _result("A", [_risk("cash_runway", "critical")])},
    )
    supervision = report["cases"][0]["final_supervision"]
    assert supervision["real_provider_arbitration"] is False
    assert supervision["gate_e1_satisfied"] is False
    aggregate = report["aggregate"]
    assert aggregate["cases_with_real_provider_arbitration"] == 0
    assert aggregate["cases_with_deterministic_fallback"] == 1
    assert any("do not count as real-provider acceptance" in note for note in report["limitations"])


def test_an_unavailable_channel_contributes_no_fact_and_is_named() -> None:
    report = _report()
    assert report["cases"][0]["unavailable_channels"] == ["market", "model"]
    assert report["aggregate"]["channel_unavailability"] == {
        "market:unavailable_error": 3,
        "model:disabled": 3,
    }
    assert any("did not run" in note for note in report["limitations"])


def test_an_unreviewed_case_does_not_read_as_approved() -> None:
    report = _report()
    assert report["aggregate"]["human_review_total"] == 0
    assert report["aggregate"]["cases_reviewed_by_a_human"] == 0
    assert any("not an approval" in note for note in report["limitations"])
    assert "未复核 ≠ 已认可" in render_batch_report(report)


def test_human_reviews_are_counted_only_where_a_reviewer_recorded_one() -> None:
    report = _report(
        human_reviews={"ipo_2024_02460": {"review_count": 2, "reviewed": True}}
    )
    reviewed = [case for case in report["cases"] if case["case_id"] == "ipo_2024_02460"][0]
    assert reviewed["human_review"] == {"review_count": 2, "reviewed": True}
    assert report["aggregate"]["cases_reviewed_by_a_human"] == 1


def test_screenshot_coverage_is_reported_as_absent_when_it_was_not_exported() -> None:
    report = _report(
        screenshots={
            "ipo_2024_02410": {
                "status": "rendered",
                "cited_evidence_count": 7,
                "screenshot_count": 7,
                "precise_localisation_count": 6,
                "page_level_fallback_count": 1,
                "no_geometry_count": 0,
            }
        }
    )
    exported = report["cases"][0]["screenshots"]
    assert exported["available"] is True and exported["precise_localisation_count"] == 6
    assert report["cases"][1]["screenshots"] == {
        "available": False,
        "status": "not_exported",
        "screenshot_count": None,
        "precise_localisation_count": None,
    }
    assert report["aggregate"]["cases_without_screenshot_export"] == 2
    assert "未导出" in render_batch_report(report)


def test_the_matrix_identity_travels_with_the_report() -> None:
    report = _report()
    assert report["matrix"]["code_base_sha"] == "cd" * 20
    assert report["matrix"]["cases_manifest_sha256"] == "ef" * 32
    assert report["matrix"]["outcome_labels_accessed"] is False
    rendered = render_batch_report(report)
    assert "cd" * 20 in rendered
    assert "读取上市后 outcome: `False`" in rendered


def test_a_dirty_working_tree_is_stated_in_the_rendered_report() -> None:
    report = build_batch_report(
        summary=_summary([_case("ipo_2024_02410", "2410.HK")], code_base_dirty=True),
        results={"ipo_2024_02410": _result("A", [_risk("cash_runway", "critical")])},
    )
    assert "工作树有未提交改动" in render_batch_report(report)


def test_risk_codes_are_counted_across_cases_not_within_one() -> None:
    frequency = _report()["aggregate"]["risk_code_frequency"]
    assert frequency == {"redemption_rights": 2, "cash_runway": 1}


def test_cli_writes_both_renderings_and_reports_the_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    matrix = tmp_path / "reports"
    (matrix / "ipo_2024_02410").mkdir(parents=True)
    (matrix / "ipo_2024_02460").mkdir(parents=True)
    (matrix / "summary.json").write_text(
        json.dumps(
            _summary([_case("ipo_2024_02410", "2410.HK"), _case("ipo_2024_02460", "2460.HK")])
        ),
        encoding="utf-8",
    )
    (matrix / "ipo_2024_02410" / "analysis_result.json").write_text(
        json.dumps(_result("A", [_risk("cash_runway", "critical")])), encoding="utf-8"
    )
    (matrix / "ipo_2024_02460" / "analysis_result.json").write_text(
        json.dumps(_result("B", [_risk("redemption_rights", "medium")])), encoding="utf-8"
    )
    (matrix / "ipo_2024_02460" / "human_review_export.json").write_text(
        json.dumps({"review_count": 1, "reviewed": True}), encoding="utf-8"
    )

    monkeypatch.setattr(
        "sys.argv", ["build_v045_batch_report.py", "--input-dir", str(matrix)]
    )
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_path("scripts/build_v045_batch_report.py", run_name="__main__")
    assert exit_info.value.code == 0

    report = json.loads((matrix / "batch_report.json").read_text(encoding="utf-8"))
    assert [case["case_id"] for case in report["cases"]] == [
        "ipo_2024_02410",
        "ipo_2024_02460",
    ]
    assert report["aggregate"]["cases_reviewed_by_a_human"] == 1
    assert (matrix / "batch_report.md").read_text(encoding="utf-8").startswith("# 批量风险报告")
    assert json.loads(capsys.readouterr().out)["status"] == "built"


def test_cli_without_a_matrix_summary_reports_that_rather_than_failing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "sys.argv", ["build_v045_batch_report.py", "--input-dir", str(tmp_path / "missing")]
    )
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_path("scripts/build_v045_batch_report.py", run_name="__main__")
    assert exit_info.value.code == 0
    assert json.loads(capsys.readouterr().out)["status"] == "unavailable_matrix_summary"
