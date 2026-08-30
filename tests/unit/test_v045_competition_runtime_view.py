"""The product surface reads governed output; it never repairs or invents it.

These are the pure projections behind the five workspaces, plus the Evidence
Viewer's page capture.  A missing page, a missing bbox and an unresolved
conflict all have to survive the trip to the screen unchanged, and a drawn box
must be captioned with the granularity it actually has.
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
from ipo_risk.runtime.evidence_screenshots import (  # noqa: E402
    EvidenceCaptureError,
    LocalisedRegion,
    GRANULARITY_KEYWORD,
    GRANULARITY_PAGE_UNION,
    GRANULARITY_SNIPPET,
    GRANULARITY_UNAVAILABLE,
    METHOD_NONE,
    METHOD_PARSER_BBOX,
    capture_evidence_page,
)

from evidence_viewer import _capture, _localisation_caption  # noqa: E402

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
    assert row["新增原文证据"] == 1
    assert "新增 1 条范围内证据" in row["复核结论"]


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
    assert (row["智能体"], row["工具 / 技能"], row["原文证据"]) == ("financial", "financial", 1)


def test_traceability_metrics_report_the_measured_ratios() -> None:
    metrics = {row["指标"]: row["值"] for row in traceability_metrics(_payload())}
    assert metrics["综合可追溯率"] == 1.0
    assert metrics["原文证据引用可解析率"] == 1.0


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
def test_a_prospectus_page_renders_to_png_with_and_without_a_box() -> None:
    content = REAL_PDF.read_bytes()
    plain, plain_region, _, _ = capture_evidence_page(
        content, _capture({"evidence_id": "e", "page": 3, "text": "nowhere in this document"})
    )
    boxed, boxed_region, _, _ = capture_evidence_page(
        content,
        _capture(
            {
                "evidence_id": "e",
                "page": 3,
                "text": "nowhere in this document",
                "bbox": [72.0, 100.0, 400.0, 200.0],
            }
        ),
    )
    assert plain.startswith(b"\x89PNG") and boxed.startswith(b"\x89PNG")
    assert plain_region.granularity == GRANULARITY_UNAVAILABLE
    assert boxed_region.method == METHOD_PARSER_BBOX
    # The box is drawn on the page, so the two renders cannot be identical.
    assert plain != boxed


@pytest.mark.parametrize("content, page", [(b"", 1), (b"%PDF-1.4 broken", 1)])
def test_an_unrenderable_page_fails_instead_of_returning_a_blank_image(content, page) -> None:
    with pytest.raises(Exception):
        capture_evidence_page(content, _capture({"evidence_id": "e", "page": page, "text": "x"}))


@pytest.mark.skipif(not REAL_PDF.exists(), reason="the local prospectus is not present")
def test_a_page_beyond_the_document_is_refused_by_name() -> None:
    with pytest.raises(EvidenceCaptureError, match="beyond the document"):
        capture_evidence_page(
            REAL_PDF.read_bytes(), _capture({"evidence_id": "e", "page": 10**6, "text": "x"})
        )


def test_the_viewer_passes_retrieval_metadata_to_the_localiser_unchanged() -> None:
    item = evidence_catalog(_payload())[0]
    assert "evidence_metadata" in item
    capture = _capture(
        {**item, "evidence_metadata": {"matched_keywords": ["现金"], "bbox_granularity": "page_text_union"}}
    )
    assert capture.matched_keywords == ("现金",)
    assert capture.recorded_bbox_granularity == "page_text_union"


@pytest.mark.parametrize(
    "region, expected",
    [
        (LocalisedRegion(GRANULARITY_SNIPPET, "m", ((1.0, 1.0, 2.0, 2.0),)), "精确到行"),
        (LocalisedRegion(GRANULARITY_KEYWORD, "m", ((1.0, 1.0, 2.0, 2.0),)), "关键词"),
        (LocalisedRegion(GRANULARITY_PAGE_UNION, METHOD_PARSER_BBOX, ((1.0, 1.0, 2.0, 2.0),)), "页级文本范围"),
        (LocalisedRegion(GRANULARITY_UNAVAILABLE, METHOD_NONE), "未绘制高亮框"),
    ],
)
def test_the_caption_never_claims_a_finer_box_than_was_found(region, expected: str) -> None:
    assert expected in _localisation_caption(region)


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
