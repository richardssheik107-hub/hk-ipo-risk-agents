from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pymupdf

from scripts.scan_nested_prospectus_corpus import scan


def test_scan_nested_zip_persists_metadata_only(tmp_path: Path) -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "secret prospectus text")
    payload = document.tobytes()
    document.close()
    inner_bytes = io.BytesIO()
    with zipfile.ZipFile(inner_bytes, "w") as inner:
        inner.writestr("2020/sample.pdf", payload)
    outer_path = tmp_path / "outer.zip"
    with zipfile.ZipFile(outer_path, "w") as outer:
        outer.writestr("corpus/2020.zip", inner_bytes.getvalue())
        outer.writestr("__MACOSX/._2020.zip", b"ignored")
    csv_path = tmp_path / "health.csv"
    summary_path = tmp_path / "health.json"

    summary = scan(outer_path, csv_path, summary_path)

    assert summary["pdf_total"] == 1
    assert summary["parse_success"] == 1
    assert summary["median_pages"] == 1
    assert "secret prospectus text" not in csv_path.read_text(encoding="utf-8-sig")
    assert json.loads(summary_path.read_text(encoding="utf-8"))["pdfs_extracted"] == 0
