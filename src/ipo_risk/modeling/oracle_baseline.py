"""Generic, deterministic Logistic Regression baseline for Oracle research datasets."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, average_precision_score, brier_score_loss, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score

FeatureGroup = Literal["document_only", "market_only", "combined"]

@dataclass(frozen=True)
class OracleBaselineResult:
    feature_group: str
    feature_names: tuple[str, ...]
    metrics: dict[str, float | int | list[list[int]] | None]

def select_feature_group(names: tuple[str, ...], group: FeatureGroup) -> tuple[int, ...]:
    doc = tuple(i for i, name in enumerate(names) if name.startswith("doc__"))
    market = tuple(i for i, name in enumerate(names) if name.startswith("market__"))
    chosen = doc if group == "document_only" else market if group == "market_only" else doc + market
    if not chosen:
        raise ValueError(f"feature group {group} is empty; use doc__/market__ names")
    return chosen

def train_oracle_logistic_regression(*, development_x, development_y, validation_x, validation_y,
                                    feature_names: tuple[str, ...], group: FeatureGroup,
                                    seed: int = 20260816) -> OracleBaselineResult:
    """Fit preprocessing on development only and evaluate untouched validation."""
    columns = select_feature_group(feature_names, group)
    train = np.asarray(development_x, dtype=float)[:, columns]
    valid = np.asarray(validation_x, dtype=float)[:, columns]
    y_train, y_valid = np.asarray(development_y, dtype=int), np.asarray(validation_y, dtype=int)
    if len(np.unique(y_train)) < 2:
        raise ValueError("development target needs both classes")
    imputer = SimpleImputer(strategy="median")
    train = imputer.fit_transform(train)
    valid = imputer.transform(valid)
    model = LogisticRegression(random_state=seed, max_iter=1000)
    model.fit(train, y_train)
    probability = model.predict_proba(valid)[:, 1]
    prediction = (probability >= 0.5).astype(int)
    metrics: dict[str, float | int | list[list[int]] | None] = {
        "sample_count": int(len(y_valid)), "positive_rate": float(y_valid.mean()),
        "accuracy": float(accuracy_score(y_valid, prediction)), "precision": float(precision_score(y_valid, prediction, zero_division=0)),
        "recall": float(recall_score(y_valid, prediction, zero_division=0)), "f1": float(f1_score(y_valid, prediction, zero_division=0)),
        "brier_score": float(brier_score_loss(y_valid, probability)), "confusion_matrix": confusion_matrix(y_valid, prediction).tolist(),
        "roc_auc": float(roc_auc_score(y_valid, probability)) if len(np.unique(y_valid)) == 2 else None,
        "pr_auc": float(average_precision_score(y_valid, probability)) if len(np.unique(y_valid)) == 2 else None,
    }
    return OracleBaselineResult(group, tuple(feature_names[i] for i in columns), metrics)
