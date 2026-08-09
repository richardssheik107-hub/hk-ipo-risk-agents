from ipo_risk.extraction import (
    LitigationComplianceExtractor,
    ShareholderRightsExtractor,
)


def test_shareholder_rights_prompt_identity_is_stable() -> None:
    assert ShareholderRightsExtractor.task_name == "shareholder_rights_extract"
    assert ShareholderRightsExtractor.prompt_version == "legal_shareholder_rights_v1"


def test_litigation_compliance_prompt_identity_is_stable() -> None:
    assert LitigationComplianceExtractor.task_name == "litigation_compliance_extract"
    assert LitigationComplianceExtractor.prompt_version == (
        "legal_litigation_compliance_v1"
    )
