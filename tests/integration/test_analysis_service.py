from ipo_risk.services.analysis_service import IPOAnalysisService
from ipo_risk.schemas import IPOAnalysisRequest, TaskStatus

def test_mock_analysis_runs_end_to_end(tmp_path):
    from ipo_risk.repositories.json_repository import JsonAnalysisRepository
    result = IPOAnalysisService(JsonAnalysisRepository(tmp_path)).analyze(IPOAnalysisRequest(company_name="Demo"))
    assert result.status is TaskStatus.COMPLETED
    assert result.prediction is not None
    assert result.verified_risks and result.pending_risks and result.report_sections and result.agent_logs
