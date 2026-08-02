from typing import Protocol
from ipo_risk.schemas import DocumentChunk, DocumentParseRequest

class DocumentParser(Protocol):
    def parse(self, request: DocumentParseRequest) -> list[DocumentChunk]: ...
