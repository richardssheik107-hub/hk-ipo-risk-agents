"""Run a no-input Mock analysis and print a compact health summary."""
from ipo_risk.schemas import IPOAnalysisRequest
from ipo_risk.services.analysis_service import IPOAnalysisService

result = IPOAnalysisService().analyze(IPOAnalysisRequest(company_name="Validation Demo"))
print(f"status={result.status} verified={len(result.verified_risks)} pending={len(result.pending_risks)}")
