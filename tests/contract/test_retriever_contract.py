from ipo_risk.parsers.mock import MockDocumentParser
from ipo_risk.retrieval.mock import MockDocumentRetriever
from ipo_risk.schemas import DocumentParseRequest

def test_retriever_returns_traceable_evidence():
    chunks = MockDocumentParser().parse(DocumentParseRequest(document_id="d", prospectus_path="mock://d"))
    evidence = MockDocumentRetriever().retrieve(chunks, "loss")
    assert evidence and evidence[0].page and evidence[0].text
