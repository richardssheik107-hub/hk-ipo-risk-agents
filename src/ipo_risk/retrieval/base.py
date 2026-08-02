from typing import Protocol
from ipo_risk.schemas import DocumentChunk, Evidence

class DocumentRetriever(Protocol):
    def retrieve(self, chunks: list[DocumentChunk], query: str, limit: int = 3) -> list[Evidence]: ...
