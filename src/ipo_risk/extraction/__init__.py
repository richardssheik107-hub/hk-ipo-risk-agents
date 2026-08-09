"""Deterministic extraction of structured values from retrieved evidence."""

from ipo_risk.extraction.financial import (
    FinancialEvidenceExtractor,
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
    "V03FinancialExtractionResult",
    "V03FinancialFactExtractor",
    "classify_legal_matter_evidence",
]
