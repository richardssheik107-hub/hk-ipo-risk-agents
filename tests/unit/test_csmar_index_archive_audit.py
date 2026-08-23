from __future__ import annotations

import zipfile
from pathlib import Path

from scripts.audit_csmar_index_archives import audit_archive, build_inventory


def test_archive_audit_reads_content_not_filename_and_counts_data_errors(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "misleading-name.zip"
    csv_text = "\n".join(
        (
            '"Indexcd","Trddt","Opnidx","Highidx","Lowidx","Clsidx","Vol","Value"',
            '"HSI","2020-01-02","1","2","1","2","100",""',
            '"HSI","2020-01-02","1","2","1","0","100","-1"',
            '"HSC","bad-date","1","2","1","","100",""',
        )
    ) + "\n"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("IDX_Gidxtrd.csv", csv_text.encode("utf-8"))
        archive.writestr("IDX_Gidxtrd[DES][csv].txt", "指数代码".encode("utf-8"))
    result = audit_archive(archive_path)
    data_member = next(
        item for item in result["members"] if item["member_name"].endswith(".csv")
    )
    assert data_member["row_count"] == 3
    assert data_member["column_names"][0] == "Indexcd"
    assert data_member["index_codes"] == ["HSC", "HSI"]
    assert data_member["min_trading_date"] == "2020-01-02"
    assert data_member["max_trading_date"] == "2020-01-02"
    assert data_member["duplicate_key_count"] == 1
    assert data_member["null_close_count"] == 1
    assert data_member["invalid_close_count"] == 1
    assert data_member["parse_errors"] == 1
    assert result["zip_crc_check"] == "PASS"


def test_inventory_is_deterministic_and_preserves_license_notice(tmp_path: Path) -> None:
    first_path = tmp_path / "b.zip"
    second_path = tmp_path / "a.zip"
    for path in (first_path, second_path):
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("note.txt", "恒生指数".encode("utf-8"))
    first = build_inventory([first_path, second_path])
    second = build_inventory([second_path, first_path])
    assert first == second
    assert [item["archive_filename"] for item in first["archives"]] == [
        "a.zip",
        "b.zip",
    ]
    assert first["raw_archives_kept_untouched"] is True
    assert "西安交通大学" in first["license_notice"]
