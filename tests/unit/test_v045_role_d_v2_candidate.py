from __future__ import annotations

import pytest

from ipo_risk.modeling.role_d_v2_candidate import (
    ROLE_D_V2_CORE_REGIME_FEATURES,
    role_d_v2_feature_groups,
)


def _feature_names() -> list[str]:
    names: list[str] = []
    for name in ROLE_D_V2_CORE_REGIME_FEATURES:
        names.extend((name, f"{name}__missing"))
    names.extend(
        (
            "prior_ipo_funds_raised_30d_sample_count",
            "prior_ipo_funds_raised_30d_sample_count__missing",
        )
    )
    return names


def test_feature_groups_select_exact_core_regime_contract() -> None:
    names = _feature_names()
    groups = role_d_v2_feature_groups(names)
    selected = tuple(names[index] for index in groups["core_regime"])
    assert selected == ROLE_D_V2_CORE_REGIME_FEATURES
    assert all(not names[index].endswith("__missing") for index in groups["raw_only"])


def test_feature_groups_reject_missing_required_feature() -> None:
    names = _feature_names()
    names.remove("recent_ipo_break_rate")
    with pytest.raises(ValueError, match="missing core regime"):
        role_d_v2_feature_groups(names)
