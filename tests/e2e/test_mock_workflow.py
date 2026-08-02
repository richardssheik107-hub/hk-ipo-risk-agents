from ipo_risk.schemas import IPOAnalysisRequest, VerificationStatus
from ipo_risk.services.analysis_service import IPOAnalysisService

def test_mock_workflow_exposes_all_review_buckets(tmp_path):
    from ipo_risk.repositories.json_repository import JsonAnalysisRepository
    result = IPOAnalysisService(JsonAnalysisRepository(tmp_path)).analyze(IPOAnalysisRequest(company_name="Demo"))
    assert all(item.verification_status is VerificationStatus.VERIFIED for item in result.verified_risks)
    assert result.pending_risks and result.prediction and result.report_sections
