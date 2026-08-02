from ipo_risk.schemas import DocumentChunk, DocumentParseRequest

class MockDocumentParser:
    def parse(self, request: DocumentParseRequest) -> list[DocumentChunk]:
        return [
            DocumentChunk(document_id=request.document_id, chunk_id="financial-1", page=12, section="Financial Information", text="The company recorded net losses and negative operating cash flow."),
            DocumentChunk(document_id=request.document_id, chunk_id="legal-1", page=48, section="Shareholders", text="Certain redemption rights remain effective before listing."),
            DocumentChunk(document_id=request.document_id, chunk_id="business-1", page=76, section="Business", text="The core product has not yet achieved commercialisation."),
        ]

class AlternateMockDocumentParser(MockDocumentParser):
    """Registry-only alternate used to prove configuration selection."""
