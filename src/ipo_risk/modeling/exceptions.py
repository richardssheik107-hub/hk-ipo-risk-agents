"""Fail-closed exceptions for the V04 document-to-market contract."""


class DocumentMarketContractError(Exception):
    """Base class for document-to-market contract failures."""


class DocumentSnapshotValidationError(DocumentMarketContractError):
    """The final structured result cannot produce a trustworthy snapshot."""


class DuplicateAuthoritativeRiskError(DocumentSnapshotValidationError):
    """More than one final item occupies a canonical risk position."""


class ModelingDatasetJoinError(DocumentMarketContractError):
    """Document and market identities or versions cannot be joined safely."""


class DocumentMaterializationError(DocumentMarketContractError):
    """A source result cannot be materialized under the governed V04 contract."""


class DocumentMaterializationConflictError(DocumentMaterializationError):
    """A case artifact exists with different semantic content or provenance."""
