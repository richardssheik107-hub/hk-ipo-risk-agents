from __future__ import annotations

import numpy as np
import pytest

import ipo_risk.modeling.role_d_v3_candidate as candidate_module
from ipo_risk.modeling.role_d_v2_candidate import ROLE_D_V2_CORE_REGIME_FEATURES
from ipo_risk.modeling.role_d_v3_candidate import (
    role_d_v3_seed_positions,
    select_role_d_v3_features,
)


def test_seed_positions_preserve_the_governed_v2_contract() -> None:
    names = ["unrelated", *ROLE_D_V2_CORE_REGIME_FEATURES]

    positions = role_d_v3_seed_positions(names)

    assert tuple(names[position] for position in positions) == (
        ROLE_D_V2_CORE_REGIME_FEATURES
    )


def test_seed_positions_reject_missing_or_duplicate_features() -> None:
    with pytest.raises(ValueError, match="missing seed features"):
        role_d_v3_seed_positions(ROLE_D_V2_CORE_REGIME_FEATURES[:-1])
    with pytest.raises(ValueError, match="non-empty and unique"):
        role_d_v3_seed_positions(["duplicate", "duplicate"])


def test_selection_is_bounded_to_development_years() -> None:
    with pytest.raises(ValueError, match="Development years 2020-2023 only"):
        select_role_d_v3_features(
            feature_names=ROLE_D_V2_CORE_REGIME_FEATURES,
            feature_values=np.zeros((5, 7)),
            labels=np.asarray([0, 1, 0, 1, 0]),
            years=np.asarray([2020, 2021, 2022, 2023, 2024]),
        )


def test_backward_selection_accepts_only_strict_development_improvements(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    names = ROLE_D_V2_CORE_REGIME_FEATURES
    first_drop = "same_industry_ipo_count_180d"
    second_drop = "same_industry_recent_return_5d"

    def fake_evaluate_positions(*, feature_names, positions, **_kwargs):
        selected = {feature_names[position] for position in positions}
        score = 1.0
        if first_drop not in selected:
            score = 2.0
        if first_drop not in selected and second_drop not in selected:
            score = 3.0
        if len(selected) < 5:
            score = 2.5
        metrics = {
            "feature_count": len(positions),
            "feature_names": [feature_names[position] for position in positions],
            "pooled_pr_auc": score,
            "pooled_roc_auc": score,
            "pooled_brier_score": 1.0 / score,
            "macro_forward_year_pr_auc": score,
            "minimum_forward_year_pr_auc": score,
            "macro_forward_year_roc_auc": score,
            "folds": [],
        }
        return metrics, np.full(8, score)

    monkeypatch.setattr(
        candidate_module, "_evaluate_positions", fake_evaluate_positions
    )
    selected, scores, rounds = select_role_d_v3_features(
        feature_names=names,
        feature_values=np.zeros((8, len(names))),
        labels=np.asarray([0, 1] * 4),
        years=np.asarray([2020, 2020, 2021, 2021, 2022, 2022, 2023, 2023]),
    )

    selected_names = tuple(names[position] for position in selected)
    assert first_drop not in selected_names
    assert second_drop not in selected_names
    assert len(selected_names) == 5
    assert np.all(scores == 3.0)
    assert [round_result["accepted"] for round_result in rounds] == [
        True,
        True,
        True,
        False,
    ]
