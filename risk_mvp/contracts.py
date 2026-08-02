"""团队共享的数据契约：后续成员只能扩展，避免随意改字段。"""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class Evidence:
    evidence_id: str
    source: str
    page: int
    claim: str
    risk_type: str
    severity: int
    confidence: float
    owner: str


@dataclass
class RiskReport:
    company_id: str
    company_name: str
    as_of_date: str
    fundamental_score: float
    market_score: float
    governance_score: float
    risk_probability_5d: float
    risk_level: str
    review_required: bool
    evidence: list[Evidence]
    assumptions: list[str]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["evidence_count"] = len(self.evidence)
        return result
