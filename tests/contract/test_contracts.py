from ipo_risk.parsers.mock import MockDocumentParser
from ipo_risk.predictors.rule_based import RuleBasedPredictor
from ipo_risk.schemas import DocumentParseRequest

def test_parser_and_predictor_contracts():
    chunks = MockDocumentParser().parse(DocumentParseRequest(document_id="x", prospectus_path="mock://x"))
    assert chunks and chunks[0].page >= 1
    prediction = RuleBasedPredictor().predict([], None)
    assert 0 <= prediction.risk_score <= 100
