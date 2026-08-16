from pathlib import Path
import json

from ipo_risk.modeling.oracle_document import build_oracle_document_features, load_risk_gold

ROOT = Path(__file__).resolve().parents[2]


def test_no_audit_uses_current_pass1() -> None:
    view = load_risk_gold(ROOT, "ipo_2022_00314")
    assert view.source_kind == "pass1_only"
    assert view.audit_applied_risks == ()


def test_stale_audit_is_explicit_and_deterministic() -> None:
    first = load_risk_gold(ROOT, "ipo_2020_00368")
    second = load_risk_gold(ROOT, "ipo_2020_00368")
    assert first.audit_status == "applied_stale_audit"
    assert "supplier_concentration" in first.audit_applied_risks
    assert first.effective_annotation_hash == second.effective_annotation_hash
    # The current pass hash remains the base provenance even where audit wins.
    assert first.base_pass_hash != first.audit_source_pass_hash


def test_audit_does_not_replace_unrelated_current_pass1_risks() -> None:
    view = load_risk_gold(ROOT, "ipo_2020_00368")
    payload = json.loads((ROOT / "expert_results" / "ipo_2020_00368" / "pass1" / "expert_annotation_v1.json").read_text(encoding="utf-8"))
    current = next(item for item in payload["risks"] if item["risk_code"] == "material_litigation_compliance")
    effective = next(item for item in view.bundle.risks if item.risk_code == "material_litigation_compliance")
    assert "material_litigation_compliance" not in view.audit_applied_risks
    assert effective.expected_status.value == current["expected_status"]
    assert effective.expected_level.value == current["expected_level"]


def test_oracle_features_record_effective_provenance_without_production_score() -> None:
    artifact = build_oracle_document_features(ROOT, "ipo_2020_00368")
    assert artifact["evaluation_only"] is True
    assert artifact["source_annotation_kind"] == "audited_pass1"
    assert "score" not in artifact["feature_names"]
    assert artifact["audit_applied_risks"]
