from __future__ import annotations

from types import SimpleNamespace

from ipo_risk.agents.business_models import (
    CommercializationCandidate,
    CoreProductCandidate,
)
from ipo_risk.agents.legal_models import (
    LitigationComplianceCandidate,
    ShareholderRightCandidate,
)
from scripts.check_v046_role_b_structured_smoke import run_probe


def _profile() -> dict:
    return {
        "profile_version": "v046_role_b_ablation_test",
        "allowed_tasks": [
            "shareholder_rights_extract",
            "litigation_compliance_extract",
            "business_precommercial_commercialization_extract",
            "business_precommercial_core_product_extract",
        ],
        "prompt_versions": {
            "shareholder_rights_extract": "legal_shareholder_rights_v1",
            "litigation_compliance_extract": "legal_litigation_compliance_v1",
            "business_precommercial_commercialization_extract": "business_precommercial_v1",
            "business_precommercial_core_product_extract": "business_precommercial_v1",
        },
    }


class _SafeProvider:
    name = "openai_responses"
    model = "test-model"

    def __init__(self, *, out_of_scope: bool = False) -> None:
        self.out_of_scope = out_of_scope
        self.last_attempt_trace = []
        self.last_call_metadata = None

    def structured_prompt_hash(self, task_name: str, prompt_version: str) -> str:
        return __import__("hashlib").sha256(
            f"{task_name}:{prompt_version}:exact-provider-instruction".encode("utf-8")
        ).hexdigest()

    def generate_structured(self, *, task_name, prompt_version, evidence, response_model):
        evidence_id = "outside" if self.out_of_scope else evidence[0].evidence_id
        self.last_call_metadata = SimpleNamespace(
            provider_name=self.name,
            model_name=self.model,
            prompt_version=prompt_version,
            request_id="sensitive-request-id",
            raw_response_hash="a" * 64,
            latency_ms=3,
            token_usage={"total_tokens": 5},
        )
        self.last_attempt_trace = [
            {"stage": "transport", "attempt": 1, "outcome": "success"}
        ]
        if response_model is ShareholderRightCandidate:
            return response_model(
                right_type="redemption_right",
                holder="investor",
                evidence_ids=[evidence_id],
            )
        if response_model is LitigationComplianceCandidate:
            return response_model(
                matter_type="none",
                current_status="not_applicable",
                evidence_ids=[evidence_id],
            )
        if response_model is CommercializationCandidate:
            return response_model(
                product_name="Candidate Alpha",
                development_stage="phase_ii",
                has_product_revenue=False,
                evidence_ids=[evidence_id],
            )
        assert response_model is CoreProductCandidate
        return response_model(
            product_name="Candidate Alpha",
            is_core_product=True,
            approval_status="not_approved",
            launch_status="not_launched",
            evidence_ids=[evidence_id],
        )


def test_allowed_task_smoke_is_bounded_synthetic_and_scope_valid() -> None:
    summary = run_probe(_SafeProvider(), profile=_profile())

    assert summary["passed"] is True
    assert summary["call_count"] == 4
    assert summary["passed_count"] == 4
    assert set(summary["allowed_tasks"]) == set(_profile()["allowed_tasks"])
    assert {item["task_name"] for item in summary["tasks"]} == set(
        _profile()["allowed_tasks"]
    )
    assert len(summary["profile_identity_hash"]) == 64
    assert summary["dataset_split"] == "development"
    assert summary["full_pdf_opened"] is False
    assert summary["validation_opened"] is False
    assert summary["blind_2025_outcome_accessed"] is False
    assert all(item["structured_valid"] for item in summary["tasks"])
    assert all(item["scope_valid"] for item in summary["tasks"])
    assert all(len(item["prompt_hash"]) == 64 for item in summary["tasks"])
    assert all(len(item["response_schema_hash"]) == 64 for item in summary["tasks"])
    serialized = str(summary)
    assert "sensitive-request-id" not in serialized


def test_scope_violation_fails_smoke_without_accepting_candidate() -> None:
    summary = run_probe(_SafeProvider(out_of_scope=True), profile=_profile())

    assert summary["passed"] is False
    assert summary["passed_count"] == 0
    assert {item["failure_kind"] for item in summary["tasks"]} == {
        "evidence_out_of_scope"
    }
