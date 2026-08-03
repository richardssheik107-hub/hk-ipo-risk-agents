from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from ipo_risk.core.config import load_settings
from ipo_risk.core.container import DependencyContainer, default_registry
from ipo_risk.parsers.pymupdf_parser import DocumentParseError, PyMuPDFDocumentParser
from ipo_risk.schemas import DocumentParseRequest


def make_pdf(path: Path, pages: list[str]) -> Path:
    document = fitz.open()
    for text in pages:
        page = document.new_page()
        if text:
            page.insert_text((72, 72), text, fontname="china-s")
    document.save(path)
    document.close()
    return path


def request(path: Path) -> DocumentParseRequest:
    return DocumentParseRequest(document_id="case-001", prospectus_path=str(path))


def test_pymupdf_parser_returns_stable_physical_page_chunks(tmp_path):
    pdf = make_pdf(tmp_path / "numbers.pdf", ["现金（1,234.50）万元，经营现金流为-45.6万元", "", "第三页"])
    parser = PyMuPDFDocumentParser()
    first = parser.parse(request(pdf))
    second = parser.parse(request(pdf))

    assert [chunk.page for chunk in first] == [1, 3]
    assert [chunk.chunk_id for chunk in first] == ["case-001:page:1", "case-001:page:3"]
    assert first == second
    assert first[0].section == "unknown"
    assert first[0].block_type == "page_text"
    assert "（1,234.50）" in first[0].text and "-45.6" in first[0].text


def test_pymupdf_parser_preserves_chinese_text(tmp_path):
    pdf = make_pdf(tmp_path / "中文文件名.pdf", ["现金及现金等价物"])
    chunks = PyMuPDFDocumentParser().parse(request(pdf))
    assert chunks[0].text == "现金及现金等价物"


def test_pymupdf_parser_reports_whole_document_failures(tmp_path):
    parser = PyMuPDFDocumentParser()
    with pytest.raises(DocumentParseError) as missing:
        parser.parse(request(tmp_path / "不存在.pdf"))
    assert missing.value.error.code == "file_not_found"

    text_file = tmp_path / "not-pdf.txt"
    text_file.write_text("not a PDF", encoding="utf-8")
    with pytest.raises(DocumentParseError) as non_pdf:
        parser.parse(request(text_file))
    assert non_pdf.value.error.code == "non_pdf_file"

    empty_pdf = make_pdf(tmp_path / "empty.pdf", [""])
    with pytest.raises(DocumentParseError) as empty:
        parser.parse(request(empty_pdf))
    assert empty.value.error.code == "empty_pdf"


def test_pymupdf_parser_rejects_encrypted_pdf(tmp_path):
    encrypted_pdf = tmp_path / "encrypted.pdf"
    document = fitz.open()
    document.new_page()
    document.save(encrypted_pdf, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="user")
    document.close()

    with pytest.raises(DocumentParseError) as encrypted:
        PyMuPDFDocumentParser().parse(request(encrypted_pdf))
    assert encrypted.value.error.code == "encrypted_pdf"


def test_pymupdf_parser_continues_after_one_page_failure(tmp_path, monkeypatch):
    pdf = make_pdf(tmp_path / "pages.pdf", ["第一页", "第二页"])
    parser = PyMuPDFDocumentParser()
    original = parser._parse_page

    def fail_first(document, document_id, page_index):
        if page_index == 0:
            raise RuntimeError("broken page")
        return original(document, document_id, page_index)

    monkeypatch.setattr(parser, "_parse_page", fail_first)
    chunks = parser.parse(request(pdf))
    assert [chunk.page for chunk in chunks] == [2]
    assert parser.last_errors[0].code == "page_parse_failure"


def test_pymupdf_configuration_selects_real_parser():
    settings = load_settings("configs/real_pdf.yaml")
    workflow = DependencyContainer(settings, default_registry()).create_workflow()
    assert isinstance(workflow.parser, PyMuPDFDocumentParser)
