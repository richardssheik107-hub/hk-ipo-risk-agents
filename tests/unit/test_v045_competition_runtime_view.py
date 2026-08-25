"""The product surface reads governed output; it never repairs or invents it.

These are the pure projections behind the five workspaces, plus the Evidence
Viewer's page renderer.  A missing page, a missing bbox and an unresolved
conflict all have to survive the trip to the screen unchanged.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parents[2] / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from competition_runtime_view import (  # noqa: E402
    conflict_rows,
    conflict_short_name,
    conflict_status_counts,
    evidence_catalog,
    evidence_label,
    judgement,
    machine_vs_human_rows,
    review_targets,
    supervision_synthesis,
    trace_rows,
    traceability_metrics,
)
from evidence_viewer import PageRenderError, render_page_png  # noqa: E402

REAL_PDF = Path(__file__).resolve().parents[2] / "data" / "local" / "real_case_001" / "prospectus.pdf"


def _payload() -> dict:
    return {
        "verified_risks": [
            {
                "risk_id": "r1", "risk_code": "cash_runway", "level": "critical", "category": "financial",
                "conclusion": "short runway", "agent_name": "financial", "verification_status": "verified",
                "verification_notes": "", "calculation": {"formula": "cash / burn"}, "metadata": {"months": 2.76},
                "evidence": [
                    {"evidence_id": "e2", "page": 12, "bbox": None, "section": "", "text": "later page",
                     "source_type": "prospectus", "relevance_score": 0.8},
                    {"evidence_id": "e1", "page": 5, "bbox": [1.0, 2.0, 3.0, 4.0], "section": "财务",
                     "text": "cash position", "source_type": "prospectus", "relevance_score": 1.0},
                ],
            }
        ],
        "pending_risks": [],
        "rejected_risks": [],
        "component_diagnostics": {
            "final_supervision_llm": {
                "status": "available", "reason": "grounded", "deterministic_severity_floor": "critical",
                "judgement": {"overall_risk": "critical", "final_explanation": "funding risk dominates"},
            },
            "conflict_detection": {
                "conflict_count": 1,
                "conflicts": [
                    {
                        "conflict_id": "conflict:run-1:unresolved_agent_claim:legal:redemption_rights",
                        "involved_agents": ["document_supervisor", "legal"], "risk_ids": [],
                        "summary": "legal held evidence the report never asserts",
                        "evidence_ids": ["e9"], "status": "partially_resolved",
                        "resolution_note": "retrieval gap",
                    }
                ],
            },
            "targeted_recheck": {
                "attempted": 1,
                "outcomes": [
                    {
                        "conflict_id": "conflict:run-1:unresolved_agent_claim:legal:redemption_rights",
                        "status": "partially_resolved", "targets": ["redemption_rights"],
                        "new_evidence_ids": ["e10"], "revised_risk_ids": [],
                    }
                ],
            },
            "competition_runtime": {
                "status": "completed",
                "sidecar": {
                    "trace_events": [
                        {
                            "event_type": "agent", "agent_name": "financial", "action": "analyze",
                            "tool_or_skill": "financial", "status": "completed", "provider_name": None,
                            "model_name": None, "prompt_version": None, "evidence_ids": ["e1"],
                            "calculation_ids": [], "latency_ms": 12, "details": {},
                        }
                    ]
                },
                "traceability": {
                    "event_count": 1, "agent_identified_count": 1, "tool_identified_count": 1,
                    "evidence_accounted_count": 1, "referenced_evidence_count": 1,
                    "resolved_evidence_count": 1, "unresolved_evidence_ids": [],
                    "agent_traceability": 1.0, "tool_traceability": 1.0, "evidence_traceability": 1.0,
                    "overall_traceability": 1.0,
                },
            },
        },
    }


def test_the_evidence_catalog_walks_the_document_in_page_order() -> None:
    catalog = evidence_catalog(_payload())
    assert [item["evidence_id"] for item in catalog] == ["e1", "e2"]
    assert catalog[0]["risk_code"] == "cash_runway"
    assert catalog[0]["bbox"] == [1.0, 2.0, 3.0, 4.0]
    assert catalog[0]["calculation"] == {"formula": "cash / burn"}


def test_an_evidence_without_a_page_is_labelled_unavailable_not_guessed() -> None:
    assert "页码不可用" in evidence_label({"evidence_id": "e3", "page": None, "risk_code": "x"})


def test_conflict_rows_carry_the_recheck_result_beside_the_conflict() -> None:
    row = conflict_rows(_payload())[0]
    assert row["状态"] == "部分解决"
    assert row["定向复核"] == "已执行"
    assert row["新增 Evidence"] == 1
    assert row["复核结论"] == "retrieval gap"


def test_a_conflict_without_a_recheck_is_shown_as_not_attempted() -> None:
    payload = _payload()
    payload["component_diagnostics"]["targeted_recheck"]["outcomes"] = []
    assert conflict_rows(payload)[0]["定向复核"] == "未执行（受控预算）"


def test_the_conflict_short_name_exposes_the_rule_that_fired() -> None:
    conflict = _payload()["component_diagnostics"]["conflict_detection"]["conflicts"][0]
    assert conflict_short_name(conflict) == "unresolved_agent_claim · legal:redemption_rights"


def test_conflict_status_counts_do_not_collapse_partial_into_resolved() -> None:
    assert conflict_status_counts(_payload()) == {"partially_resolved": 1}


def test_trace_rows_expose_actor_tool_and_evidence_counts() -> None:
    row = trace_rows(_payload())[0]
    assert (row["Agent"], row["工具 / Skill"], row["Evidence"]) == ("financial", "financial", 1)


def test_traceability_metrics_report_the_measured_ratios() -> None:
    metrics = {row["指标"]: row["值"] for row in traceability_metrics(_payload())}
    assert metrics["综合可追溯率"] == 1.0
    assert metrics["Evidence 引用可解析率"] == 1.0


def test_a_run_without_the_e_lane_yields_no_synthetic_metrics() -> None:
    assert traceability_metrics({}) == []
    assert trace_rows({}) == []
    assert conflict_rows({}) == []
    assert judgement({}) is None
    assert supervision_synthesis({}) == {}


def test_review_targets_include_risks_and_every_unsettled_conflict() -> None:
    targets = {item["target_id"] for item in review_targets(_payload())}
    assert targets == {"r1", "conflict:run-1:unresolved_agent_claim:legal:redemption_rights"}


def test_a_resolved_conflict_is_not_offered_for_review() -> None:
    payload = _payload()
    payload["component_diagnostics"]["conflict_detection"]["conflicts"][0]["status"] = "resolved"
    assert [item["target_id"] for item in review_targets(payload)] == ["r1"]


def test_machine_and_human_verdicts_are_shown_side_by_side_not_merged() -> None:
    rows = machine_vs_human_rows(_payload(), {})
    assert rows[0]["机器结论"] == "verified"
    assert rows[0]["人工结论"] == "未复核"


@pytest.mark.skipif(not REAL_PDF.exists(), reason="the local prospectus is not present")
def test_a_prospectus_page_renders_to_png_with_and_without_a_bbox() -> None:
    content = REAL_PDF.read_bytes()
    plain = render_page_png(content, 3)
    highlighted = render_page_png(content, 3, (72.0, 100.0, 400.0, 200.0))
    assert plain.startswith(b"\x89PNG") and highlighted.startswith(b"\x89PNG")
    # The highlight is drawn on the page, so the two renders cannot be identical.
    assert plain != highlighted


@pytest.mark.parametrize(
    "content, page",
    [(b"", 1), (b"%PDF-1.4 broken", 1)],
)
def test_an_unrenderable_page_raises_instead_of_returning_a_blank_image(content, page) -> None:
    with pytest.raises(PageRenderError):
        render_page_png(content, page)


@pytest.mark.skipif(not REAL_PDF.exists(), reason="the local prospectus is not present")
def test_a_page_beyond_the_document_is_refused_by_name() -> None:
    with pytest.raises(PageRenderError, match="beyond the document"):
        render_page_png(REAL_PDF.read_bytes(), 10**6)


def _app_source() -> str:
    return (APP_DIR / "streamlit_app.py").read_text(encoding="utf-8")


def test_the_frozen_summary_is_never_labelled_as_the_final_supervisor_conclusion() -> None:
    """`FinalSupervisionResult.summary` is the Document Supervisor's string.

    Presenting it under a Final Supervisor heading is what made 2410 read
    "0 unresolved conflict(s)" while the competition layer held five. The label
    is fixed here so the defect cannot come back through a second surface.
    """
    assert "Final Supervisor 综合结论" not in _app_source()


def test_the_channel_grid_is_rendered_once_per_page() -> None:
    """It sits above the workspaces; a second copy inside a tab is redundant."""
    assert _app_source().count("render_channel_grid(payload)") == 1


def test_the_report_surface_reuses_the_shared_supervisor_projection() -> None:
    """One helper decides LLM-vs-deterministic labelling for every surface."""
    assert "executive_supervisor_view(payload)" in _app_source()
