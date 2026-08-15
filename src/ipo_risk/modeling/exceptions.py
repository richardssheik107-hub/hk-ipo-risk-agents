"""Fail-closed exceptions for the V04 document-to-market contract."""


class DocumentMarketContractError(Exception):
    """Base class for document-to-market contract failures."""


class DocumentSnapshotValidationError(DocumentMarketContractError):
    """The final structured result cannot produce a trustworthy snapshot."""


class DuplicateAuthoritativeRiskError(DocumentSnapshotValidationError):
    """More than one final item occupies a canonical risk position."""


class ModelingDatasetJoinError(DocumentMarketContractError):
    """Document and market identities or versions cannot be joined safely."""
