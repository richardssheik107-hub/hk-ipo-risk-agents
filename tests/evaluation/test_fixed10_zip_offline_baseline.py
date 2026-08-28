from pathlib import Path

import pytest

from scripts.run_fixed10_zip_offline_baseline import Fixed10ZipError, load_subset


def test_fixed10_subset_rejects_validation(tmp_path: Path) -> None:
    path = tmp_path / "subset.json"
    path.write_text('{"split":"validation","validation_opened":true,"blind_2025_outcome_accessed":false,"cases":[]}', encoding="utf-8")
    with pytest.raises(Fixed10ZipError, match="Development-only"):
        load_subset(path)
