from ipo_risk.agents.mock import MockFinancialAgent
from ipo_risk.parsers.mock import MockDocumentParser
from ipo_risk.schemas import DocumentParseRequest, IPOProfile, VerificationStatus

def test_agent_returns_pending_risk_without_self_verification():
    chunks = MockDocumentParser().parse(DocumentParseRequest(document_id="d", prospectus_path="mock://d"))
    risk = MockFinancialAgent().analyze(IPOProfile(company_name="Demo"), chunks)[0]
    assert risk.verification_status is VerificationStatus.PENDING
