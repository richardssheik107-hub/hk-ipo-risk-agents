"""The review API is an adapter, not a second brain.

Every test here fixes an invariant that has to survive a caller who asks for
something the run cannot support: a decision about an id that does not exist, an
unsigned review, an analysis that was never persisted.  The API must refuse each
of them rather than write a reviewer record that no machine claim can be
compared against.

The service and repository are real, pointed at a temporary directory, so these
exercise the actual write path rather than a mock of it.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ipo_risk.api.human_review import build_app
from ipo_risk.repositories.json_repository import JsonAnalysisRepository
from ipo_risk.schemas import (
    Evidence,
    IPOAnalysisResult,
    RiskCategory,
    RiskItem,
    RiskLevel,
)
from ipo_risk.services.human_review_service import HumanReviewService

ANALYSIS_ID = "analysis-0001"


def _risk(risk_id: str, *, status: str = "verified") -> RiskItem:
    return RiskItem(
        risk_id=risk_id,
        risk_code="cash_runway",
        category=RiskCategory.FINANCIAL,
        risk_type="liquidity",
        level=RiskLevel.CRITICAL,
        score=0.9,
        conclusion="short runway",
        agent_name="financial",
        verification_status=status,
        evidence=[
            Evidence(
                evidence_id="e1",
                page=5,
                text="cash position",
                source_type="prospectus",
                relevance_score=1.0,
            )
        ],
    )


def _result() -> IPOAnalysisResult:
    return IPOAnalysisResult(
        analysis_id=ANALYSIS_ID,
        request_id="request-0001",
        company_name="Fixture IPO",
        stock_code="2410.HK",
        workflow_version="v04_competition",
        schema_version="1.0",
        verified_risks=[_risk("r1")],
        pending_risks=[_risk("r2", status="pending")],
        metadata={
            "component_diagnostics": {
                "competition_runtime": {
                    "sidecar": {
                        "identity": {"case_id": "ipo_2024_02410", "run_id": "run-0001"}
                    }
                },
                "conflict_detection": {
                    "conflicts": [
                        {
                            "conflict_id": "c1",
                            "status": "unresolved",
                            "summary": "agents disagree",
                            "involved_agents": ["financial", "verifier"],
                            "evidence_ids": ["e1"],
                        },
                        {
                            "conflict_id": "c2",
                            "status": "resolved",
                            "summary": "settled by recheck",
                            "involved_agents": ["legal"],
                            "evidence_ids": [],
                        },
                    ]
                },
            }
        },
    )


@pytest.fixture
def client(tmp_path) -> TestClient:
    analyses = JsonAnalysisRepository(str(tmp_path / "results"))
    analyses.save(_result())
    app = build_app(
        analyses=analyses,
        reviews=HumanReviewService(tmp_path / "human_review"),
    )
    return TestClient(app)


def _accept(client: TestClient, target_id: str, **overrides):
    body = {
        "target_id": target_id,
        "decision": "accept",
        "reviewer_id": "reviewer_1",
        "reviewer_note": "checked against page 5",
    }
    body.update(overrides)
    return client.post(f"/analyses/{ANALYSIS_ID}/reviews", json=body)


# --- reading what may be reviewed ------------------------------------------


def test_every_risk_and_every_unsettled_conflict_is_offered_for_review(client) -> None:
    response = client.get(f"/analyses/{ANALYSIS_ID}/review-targets")
    assert response.status_code == 200
    body = response.json()
    assert {item["target_id"] for item in body["targets"]} == {"r1", "r2", "c1"}
    assert body["target_count"] == 3


def test_a_conflict_the_machine_settled_is_not_offered(client) -> None:
    """``c2`` is resolved: there is no open question for a person to answer."""
    body = client.get(f"/analyses/{ANALYSIS_ID}/review-targets").json()
    assert "c2" not in {item["target_id"] for item in body["targets"]}


def test_reviews_are_filed_under_the_governed_case_identity(client) -> None:
    """Not the stock code -- the sidecar has to join to the run it describes."""
    body = client.get(f"/analyses/{ANALYSIS_ID}/review-targets").json()
    assert body["case_id"] == "ipo_2024_02410"
    assert body["run_id"] == "run-0001"


def test_the_machine_verdict_travels_with_each_target(client) -> None:
    body = client.get(f"/analyses/{ANALYSIS_ID}/review-targets/r2").json()
    assert body["machine_status"] == "pending"
    assert body["evidence_ids"] == ["e1"]


def test_an_analysis_that_was_never_persisted_is_a_404(client) -> None:
    """The API reads results; it never runs one on demand to satisfy a request."""
    response = client.get("/analyses/does-not-exist/review-targets")
    assert response.status_code == 404


# --- writing a decision ----------------------------------------------------


def test_a_decision_is_recorded_against_the_machine_status_it_disputed(client) -> None:
    response = _accept(client, "r2")
    assert response.status_code == 201
    body = response.json()
    assert body["original_machine_status"] == "pending"
    assert body["decision"] == "accept"
    assert body["post_review_status"] == "human_accepted"
    assert body["reviewer_id"] == "reviewer_1"


def test_a_decision_about_an_id_absent_from_the_run_is_refused(client) -> None:
    """Fail closed: a verdict about nothing can never be compared to a claim."""
    response = _accept(client, "not-a-target")
    assert response.status_code == 404
    assert client.get(f"/analyses/{ANALYSIS_ID}/reviews").json() == []


def test_an_unsigned_review_is_refused(client) -> None:
    response = _accept(client, "r1", reviewer_id="")
    assert response.status_code == 422
    assert client.get(f"/analyses/{ANALYSIS_ID}/reviews").json() == []


def test_a_review_cannot_smuggle_extra_fields(client) -> None:
    """``extra=forbid``: the body is the contract, not a free-form dict."""
    response = _accept(client, "r1", post_review_status="human_accepted")
    assert response.status_code == 422


def test_an_unknown_decision_is_refused(client) -> None:
    response = _accept(client, "r1", decision="looks_fine")
    assert response.status_code == 422


# --- the two verdicts stay separate ----------------------------------------


def test_an_unreviewed_analysis_says_so_rather_than_showing_an_empty_table(client) -> None:
    body = client.get(f"/analyses/{ANALYSIS_ID}/review-ledger").json()
    assert body["reviewed"] is False
    assert body["review_count"] == 0
    assert "absence of review, not an endorsement" in body["statement"]
    assert all(row["human_decision"] is None for row in body["rows"])
    assert all(row["reviewed"] is False for row in body["rows"])


def test_the_ledger_keeps_both_verdicts_side_by_side(client) -> None:
    _accept(client, "r2")
    rows = {row["target_id"]: row for row in client.get(f"/analyses/{ANALYSIS_ID}/review-ledger").json()["rows"]}
    assert rows["r2"]["machine_status"] == "pending"
    assert rows["r2"]["human_decision"] == "accept"
    assert rows["r2"]["reviewed"] is True
    # The untouched target is still reported as unreviewed, not as agreement.
    assert rows["r1"]["human_decision"] is None
    assert rows["r1"]["reviewed"] is False


def test_a_recorded_decision_never_edits_the_machine_result(client, tmp_path) -> None:
    before = (tmp_path / "results" / f"{ANALYSIS_ID}.json").read_text(encoding="utf-8")
    _accept(client, "r1")
    after = (tmp_path / "results" / f"{ANALYSIS_ID}.json").read_text(encoding="utf-8")
    assert before == after


def test_the_review_history_reads_back_what_was_written(client) -> None:
    _accept(client, "r1")
    _accept(client, "r2", decision="reject", reviewer_id="reviewer_2")
    history = client.get(f"/analyses/{ANALYSIS_ID}/reviews").json()
    assert [item["target_id"] for item in history] == ["r1", "r2"]
    assert [item["reviewer_id"] for item in history] == ["reviewer_1", "reviewer_2"]
    assert history[1]["post_review_status"] == "human_rejected"


def test_the_api_publishes_an_openapi_contract(client) -> None:
    schema = client.get("/openapi.json").json()
    assert "/analyses/{analysis_id}/reviews" in schema["paths"]
    assert client.get("/health").json()["status"] == "ok"
