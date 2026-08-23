"""Deterministic v0.4 market-data, label, and governance foundation."""

from ipo_risk.market.csmar_hsi import (
    CSMARHSIError,
    CSMARHSIProvider,
    CSMARHSISourceManifest,
    load_csmar_hsi_bars,
)
from ipo_risk.market.features import (
    MARKET_FEATURE_MANIFEST_V1,
    PreListingMarketFeatureEngine,
    PreListingMarketFeatureError,
    vectorize_market_snapshot,
)
from ipo_risk.market.governance import (
    MarketDatasetGuard,
    MarketDatasetSplitPolicy,
    MarketSecurityEligibilityPolicy,
)
from ipo_risk.market.labels import MarketLabelGenerator
from ipo_risk.market.outcomes import FiveDayOutcomeBuilder
from ipo_risk.market.validation import MarketDataValidator

__all__ = [
    "CSMARHSIError",
    "CSMARHSIProvider",
    "CSMARHSISourceManifest",
    "FiveDayOutcomeBuilder",
    "MARKET_FEATURE_MANIFEST_V1",
    "MarketDataValidator",
    "MarketDatasetGuard",
    "MarketDatasetSplitPolicy",
    "MarketLabelGenerator",
    "MarketSecurityEligibilityPolicy",
    "PreListingMarketFeatureEngine",
    "PreListingMarketFeatureError",
    "load_csmar_hsi_bars",
    "vectorize_market_snapshot",
]
