from pathlib import Path

import yaml


DICTIONARY = Path("configs/v03_legal_query_dictionary.yaml")


def _terms(groups: dict[str, list[str]]) -> set[str]:
    return {term for values in groups.values() for term in values}


def test_legal_dictionary_has_frozen_scope_and_owners() -> None:
    config = yaml.safe_load(DICTIONARY.read_text(encoding="utf-8"))
    assert config["version"] == "v03_legal_dictionary_v1"
    assert config["owner"] == "legal"
    assert set(config["risk_query_families"]) == {
        "redemption_rights",
        "material_litigation_compliance",
    }
    assert all(
        family["owner"] == "legal"
        for family in config["risk_query_families"].values()
    )


def test_special_rights_dictionary_covers_required_multilingual_terms() -> None:
    config = yaml.safe_load(DICTIONARY.read_text(encoding="utf-8"))
    family = config["risk_query_families"]["redemption_rights"]
    rights = _terms(family["right_terms"])
    required = {
        "赎回权", "贖回權", "redemption right", "redemption rights",
        "清算优先权", "清算優先權", "liquidation preference",
        "反摊薄", "反攤薄", "anti-dilution", "anti-dilution right",
        "优先认购权", "優先認購權", "pre-emptive right", "pre-emption right",
        "回购权", "回購權", "repurchase right", "buyback right",
        "否决权", "否決權", "veto right",
        "董事提名权", "董事提名權", "director nomination right",
        "特殊权利", "特殊權利", "special rights",
        "对赌安排", "對賭安排", "valuation adjustment mechanism", "VAM",
    }
    assert required <= rights

    statuses = _terms(family["status_terms"])
    assert {
        "terminate", "terminated", "termination", "cease", "ceases", "lapse",
        "expire", "waive", "waiver", "终止", "終止", "失效", "豁免",
        "restore", "restored", "revive", "reinstated", "resume",
        "恢复", "恢復", "重新生效",
    } <= statuses


def test_litigation_compliance_dictionary_covers_terms_and_statuses() -> None:
    config = yaml.safe_load(DICTIONARY.read_text(encoding="utf-8"))
    family = config["risk_query_families"]["material_litigation_compliance"]
    matters = _terms(family["matter_terms"])
    assert {
        "重大诉讼", "重大訴訟", "material litigation", "诉讼", "訴訟", "litigation",
        "仲裁", "arbitration", "行政处罚", "行政處罰", "administrative penalty",
        "监管调查", "監管調查", "regulatory investigation",
        "不合规", "不合規", "non-compliance", "牌照", "许可", "許可",
        "license", "licence", "permit", "税务", "稅務", "tax",
        "环境处罚", "環境處罰", "environmental penalty",
        "数据隐私", "數據隱私", "data privacy",
    } <= matters

    statuses = _terms(family["status_terms"])
    assert {
        "pending", "ongoing", "resolved", "settled", "closed", "remediated",
        "rectified", "尚未解决", "仍在进行", "已结案", "已和解", "已整改", "整改完成",
    } <= statuses


def test_dictionary_preserves_retriever_and_verification_boundaries() -> None:
    config = yaml.safe_load(DICTIONARY.read_text(encoding="utf-8"))
    contract = config["retrieval_contract"]
    assert contract == {
        "output_type": "Evidence",
        "no_match_result": "empty_list",
        "preserve_source_text": True,
        "preserve_physical_page": True,
        "stable_evidence_id": True,
        "term_hit_is_risk": False,
        "status_pairing_required_for_ranking": True,
        "verifier_decides_final_status": True,
    }
