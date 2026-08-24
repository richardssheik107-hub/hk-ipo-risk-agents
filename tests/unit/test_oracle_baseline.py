import numpy as np
import json
import subprocess
import sys
from pathlib import Path
from ipo_risk.modeling.oracle_baseline import select_feature_group, train_oracle_logistic_regression


def test_feature_groups_are_deterministic() -> None:
    names = ("doc__risk", "market__hsi", "doc__count")
    assert select_feature_group(names, "document_only") == (0, 2)
    assert select_feature_group(names, "market_only") == (1,)


def test_baseline_is_reproducible_with_development_only_imputation() -> None:
    kwargs = dict(development_x=[[0, np.nan], [1, 1], [0, 2], [1, 3]], development_y=[0, 1, 0, 1],
                  validation_x=[[0, np.nan], [1, 999]], validation_y=[0, 1],
                  feature_names=("doc__risk", "market__hsi"), group="combined")
    assert train_oracle_logistic_regression(**kwargs) == train_oracle_logistic_regression(**kwargs)


def test_training_cli_smoke(tmp_path) -> None:
    payload = {"feature_names": ["doc__a", "market__b"], "records": [
        {"feature_values": [0, 1], "target": 0}, {"feature_values": [1, 1], "target": 1},
        {"feature_values": [0, 2], "target": 0}, {"feature_values": [1, 2], "target": 1},
    ]}
    validation = {**payload, "records": payload["records"][:2]}
    development_path, validation_path = tmp_path / "development.json", tmp_path / "validation.json"
    development_path.write_text(json.dumps(payload), encoding="utf-8")
    validation_path.write_text(json.dumps(validation), encoding="utf-8")
    root = Path(__file__).resolve().parents[2]
    subprocess.run([sys.executable, "scripts/train_oracle_baseline.py", "--development", str(development_path), "--validation", str(validation_path), "--output-dir", str(tmp_path / "out")], cwd=root, check=True)
    assert len(json.loads((tmp_path / "out" / "metrics.json").read_text(encoding="utf-8"))) == 3
