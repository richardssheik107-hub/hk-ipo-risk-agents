"""Explicit failures for the v0.4 market-foundation boundary."""


class MarketFoundationError(Exception):
    """Base class for market-foundation failures."""


class MarketDataError(MarketFoundationError):
    """Base class for market-data contract failures."""


class MissingMarketMetadataError(MarketDataError):
    """Raised when a known security has no IPO market metadata."""


class MissingDailyBarError(MarketDataError):
    """Raised when a requested security has no daily-bar series."""


class DuplicateMarketBarError(MarketDataError):
    """Raised when a stock/date pair occurs more than once."""


class UnsupportedStockError(MarketDataError):
    """Raised when a provider does not know the requested stock code."""


class UnsupportedExchangeError(MarketDataError):
    """Raised when a market outside the frozen v0.4 scope is requested."""


class MarketDatasetGovernanceError(MarketFoundationError):
    """Raised when a dataset use conflicts with the chronological policy."""


class BlindDataLeakageError(MarketDatasetGovernanceError):
    """Raised when blind data is offered to any development operation."""


class UnexpectedCohortYearError(MarketDatasetGovernanceError):
    """Raised when a cohort falls outside the frozen 2020-2025 universe."""
