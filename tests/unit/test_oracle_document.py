from pathlib import Path
import json
import shutil

from ipo_risk.modeling.oracle_document import build_oracle_document_features, load_risk_gold

ROOT = Path(__file__).resolve().parents[2]
CASE_ID = "ipo_2020_00368"


def test_no_audit_uses_current_pass1() -> None:
    view = load_risk_gold(ROOT, "ipo_2022_00314")
    assert view.source_kind == "pass1_only"
    assert view.audit_applied_risks == ()


def test_current_audit_state_is_explicit_and_deterministic() -> None:
    first = load_risk_gold(ROOT, CASE_ID)
    second = load_risk_gold(ROOT, CASE_ID)
    assert "supplier_concentration" in first.audit_applied_risks
    assert first.audit_status == second.audit_status
    assert first.effective_annotation_hash == second.effective_annotation_hash
    if first.audit_source_pass_hash == first.base_pass_hash:
        assert first.audit_status == "applied"
    else:
        assert first.audit_status == "applied_stale_audit"


def test_synthetic_stale_audit_is_detected(tmp_path: Path) -> None:
    metadata_src = ROOT / "docs" / "annotation" / "gpt_expert_v1_1" / "case_packets" / CASE_ID / "case_metadata.json"
    pass1_src = ROOT / "expert_results" / CASE_ID / "pass1" / "expert_annotation_v1.json"
    audit_src = ROOT / "expert_results" / CASE_ID / "audit" / "financial_resolution_v1.json"

    metadata_dst = tmp_path / "docs" / "annotation" / "gpt_expert_v1_1" / "case_packets" / CASE_ID / "case_metadata.json"
    pass1_dst = tmp_path / "expert_results" / CASE_ID / "pass1" / "expert_annotation_v1.json"
    audit_dst = tmp_path / "expert_results" / CASE_ID / "audit" / "financial_resolution_v1.json"
    metadata_dst.parent.mkdir(parents=True, exist_ok=True)
    pass1_dst.parent.mkdir(parents=True, exist_ok=True)
    audit_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(metadata_src, metadata_dst)
    shutil.copyfile(pass1_src, pass1_dst)

    audit_payload = json.loads(audit_src.read_text(encoding="utf-8"))
    audit_payload["source_pass1_sha256"] = "0" * 64
    audit_dst.write_text(json.dumps(audit_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    view = load_risk_gold(tmp_path, CASE_ID)
    assert view.audit_status == "applied_stale_audit"
    assert view.audit_source_pass_hash != view.base_pass_hash
    assert "supplier_concentration" in view.audit_applied_risks


def test_audit_does_not_replace_unrelated_current_pass1_risks() -> None:
    view = load_risk_gold(ROOT, CASE_ID)
    payload = json.loads((ROOT / "expert_results" / CASE_ID / "pass1" / "expert_annotation_v1.json").read_text(encoding="utf-8"))
    current = next(item for item in payload["risks"] if item["risk_code"] == "material_litigation_compliance")
    effective = next(item for item in view.bundle.risks if item.risk_code == "material_litigation_compliance")
    assert "material_litigation_compliance" not in view.audit_applied_risks
    assert effective.expected_status.value == current["expected_status"]
    assert effective.expected_level.value == current["expected_level"]


def test_oracle_features_record_effective_provenance_without_production_score() -> None:
    artifact = build_oracle_document_features(ROOT, CASE_ID)
    assert artifact["evaluation_only"] is True
    assert artifact["source_annotation_kind"] == "audited_pass1"
    assert "score" not in artifact["feature_names"]
    assert artifact["audit_applied_risks"]
