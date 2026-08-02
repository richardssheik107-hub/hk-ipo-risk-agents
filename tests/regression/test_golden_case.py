from ipo_risk.schemas import IPOAnalysisRequest
from ipo_risk.services.analysis_service import IPOAnalysisService

def test_golden_mock_case_has_stable_risk_codes(tmp_path):
    from ipo_risk.repositories.json_repository import JsonAnalysisRepository
    result = IPOAnalysisService(JsonAnalysisRepository(tmp_path)).analyze(IPOAnalysisRequest(company_name="Golden"))
    assert {risk.risk_code for risk in result.verified_risks} == {"continuous_loss", "redemption_rights", "weak_ipo_market"}
