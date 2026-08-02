from ipo_risk.schemas import DocumentChunk, IPOAnalysisRequest, RiskCategory, RiskItem, RiskLevel

def test_schema_defaults_and_serialization():
    request = IPOAnalysisRequest(company_name="Demo")
    assert request.use_mock and request.model_dump()["workflow_version"] == "mvp_v1"
    chunk = DocumentChunk(document_id="d", chunk_id="c", page=1, text="text")
    risk = RiskItem(risk_code="loss", category=RiskCategory.FINANCIAL, risk_type="Loss", level=RiskLevel.HIGH, score=80, conclusion="x", agent_name="agent")
    assert chunk.metadata == {} and risk.evidence == []
