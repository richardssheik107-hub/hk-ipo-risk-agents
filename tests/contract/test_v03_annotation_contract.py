from pathlib import Path

from ipo_risk.evaluation.v03_manifest import REQUIRED_COLUMNS, validate_manifest


FIXTURE = Path("tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv")


def test_v03_golden_manifest_matches_frozen_contract():
    assert len(REQUIRED_COLUMNS) == 14
    assert validate_manifest(FIXTURE) == []
