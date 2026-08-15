"""Physical-page PDF parsing backed by PyMuPDF."""

from __future__ import annotations

from pathlib import Path

import fitz

from ipo_risk.schemas import AnalysisError, DocumentChunk, DocumentParseRequest


class DocumentParseError(RuntimeError):
    """A whole-document parsing error that retains the internal error contract."""

    def __init__(self, error: AnalysisError) -> None:
        self.error = error
        super().__init__(error.message)


class PyMuPDFDocumentParser:
    """Convert a local PDF into one stable text chunk per physical page."""

    name = "pymupdf"

    def __init__(self) -> None:
        self.last_errors: list[AnalysisError] = []

    def parse(self, request: DocumentParseRequest) -> list[DocumentChunk]:
        """Parse non-blank physical pages without crossing page boundaries."""
        self.last_errors = []
        path = Path(request.prospectus_path)
        self._validate_path(path)

        try:
            document = fitz.open(path)
        except Exception as exc:
            raise self._failure("pdf_open_failure", "Unable to open PDF.", path, exc) from exc

        with document:
            if document.needs_pass:
                raise self._failure("encrypted_pdf", "Encrypted PDFs are not supported.", path)
            if document.page_count == 0:
                raise self._failure("empty_pdf", "PDF contains no pages.", path)

            chunks: list[DocumentChunk] = []
            for page_index in range(document.page_count):
                try:
                    chunk = self._parse_page(document, request.document_id, page_index)
                except Exception as exc:
                    self.last_errors.append(
                        AnalysisError(
                            stage="document_parser",
                            component=self.name,
                            code="page_parse_failure",
                            message="Unable to parse PDF page.",
                            context={"path": str(path), "page": page_index + 1, "exception": str(exc)},
                        )
                    )
                    continue
                if chunk is not None:
                    chunks.append(chunk)

        if not chunks and not self.last_errors:
            raise self._failure("empty_pdf", "PDF contains no non-blank text.", path)
        return chunks

    def _validate_path(self, path: Path) -> None:
        if not path.exists():
            raise self._failure("file_not_found", "PDF file does not exist.", path)
        if not path.is_file():
            raise self._failure("not_a_file", "PDF path must point to a file.", path)
        if path.suffix.lower() != ".pdf":
            raise self._failure("non_pdf_file", "Parser only accepts .pdf files.", path)

    def _parse_page(self, document: fitz.Document, document_id: str, page_index: int) -> DocumentChunk | None:
        page = document.load_page(page_index)
        text = page.get_text("text").strip()
        if not text:
            return None
        physical_page = page_index + 1
        return DocumentChunk(
            document_id=document_id,
            chunk_id=f"{document_id}:page:{physical_page}",
            page=physical_page,
            section="unknown",
            text=text,
            block_type="page_text",
            metadata={"parser": self.name, "page_index": page_index, "physical_page": physical_page},
        )

    def _failure(
        self,
        code: str,
        message: str,
        path: Path,
        exception: Exception | None = None,
    ) -> DocumentParseError:
        context = {"path": str(path)}
        if exception is not None:
            context["exception"] = str(exception)
        return DocumentParseError(
            AnalysisError(stage="document_parser", component=self.name, code=code, message=message, context=context)
        )


class PyMuPDFTableDocumentParser(PyMuPDFDocumentParser):
    """PyMuPDF parser that additionally reconstructs borderless financial tables.

    The emitted ``.text`` and every chunk-identity field (``chunk_id``, ``page``,
    ``section``, ``block_type``) are **byte-identical** to :class:`PyMuPDFDocumentParser`,
    so retrieval, chunk-identity checks, and every frozen text-only expectation are
    unaffected.  Structured tables are attached under ``metadata["tables"]`` only
    when a page actually yields a fiscal-year-anchored numeric grid, keeping the
    metadata (and repository payload) small.
    """

    name = "pymupdf_table"

    def _parse_page(self, document: fitz.Document, document_id: str, page_index: int) -> DocumentChunk | None:
        chunk = super()._parse_page(document, document_id, page_index)
        if chunk is None:
            return None
        try:
            from ipo_risk.parsers.table_reconstruction import reconstruct_page_tables

            page = document.load_page(page_index)
            tables = reconstruct_page_tables(page.get_text("words"))
        except Exception:
            # Table reconstruction is strictly additive; never fail a page over it.
            tables = []
        if not tables:
            return chunk
        metadata = {**chunk.metadata, "tables": tables, "has_structured_tables": True}
        return chunk.model_copy(update={"metadata": metadata})
