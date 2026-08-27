"""Deterministic extraction of structured values from retrieved evidence."""

from ipo_risk.extraction import financial as _financial
from ipo_risk.extraction.financial import FinancialEvidenceExtractor
from ipo_risk.extraction.concentration_reconciliation import (
    TableAwareV03FinancialFactExtractor,
    V03FinancialFactExtractor,
)
from ipo_risk.extraction.legal_matter_classifier import (
    LegalMatterEvidenceClassification,
    LegalMatterEvidenceKind,
    classify_legal_matter_evidence,
)
from ipo_risk.extraction.litigation_compliance import LitigationComplianceExtractor
from ipo_risk.extraction.models import (
    ConcentrationFact,
    ExtractionStatus,
    FinancialExtractionResult,
    FinancialMetricValue,
    FinancialPeriodFact,
    FinancialPeriodSeriesResult,
    LegalMatterObservation,
    ShareholderRightsFact,
    V03FinancialExtractionResult,
)
from ipo_risk.extraction.shareholder_rights import ShareholderRightsExtractor

# Compatibility overlay: some existing runtime wiring imports the extractor classes
# directly from ``ipo_risk.extraction.financial``.  Package initialization always
# precedes that submodule import, so bind the narrow v0.4.5 subclasses onto the
# historical module names without changing any public registry/config identity.
_financial.V03FinancialFactExtractor = V03FinancialFactExtractor
_financial.TableAwareV03FinancialFactExtractor = TableAwareV03FinancialFactExtractor

__all__ = [
    "ConcentrationFact",
    "ExtractionStatus",
    "FinancialEvidenceExtractor",
    "FinancialExtractionResult",
    "FinancialMetricValue",
    "FinancialPeriodFact",
    "FinancialPeriodSeriesResult",
    "LegalMatterEvidenceClassification",
    "LegalMatterEvidenceKind",
    "LegalMatterObservation",
    "LitigationComplianceExtractor",
    "ShareholderRightsExtractor",
    "ShareholderRightsFact",
    "TableAwareV03FinancialFactExtractor",
    "V03FinancialExtractionResult",
    "V03FinancialFactExtractor",
    "classify_legal_matter_evidence",
]
