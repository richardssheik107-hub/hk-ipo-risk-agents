from ipo_risk.schemas import DocumentChunk, Evidence

class MockDocumentRetriever:
    def retrieve(self, chunks: list[DocumentChunk], query: str, limit: int = 3) -> list[Evidence]:
        words = set(query.lower().split())
        matched = [chunk for chunk in chunks if words & set(chunk.text.lower().split())] or chunks[:1]
        return [Evidence(document_id=c.document_id, chunk_id=c.chunk_id, page=c.page, section=c.section, text=c.text) for c in matched[:limit]]
