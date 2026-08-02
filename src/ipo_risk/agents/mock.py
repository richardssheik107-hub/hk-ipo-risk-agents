from ipo_risk.schemas import Calculation, DocumentChunk, IPOProfile, MarketSnapshot, RiskCategory, RiskItem, RiskLevel

def _risk(code: str, category: RiskCategory, label: str, score: float, evidence, agent: str) -> RiskItem:
    return RiskItem(risk_code=code, category=category, risk_type=label, level=RiskLevel.HIGH if score >= 70 else RiskLevel.MEDIUM, score=score, conclusion=f"Mock finding: {label}.", evidence=evidence, agent_name=agent, confidence=.8)

class MockFinancialAgent:
    name = "financial"
    def analyze(self, profile: IPOProfile, chunks: list[DocumentChunk], market=None):
        c = next((x for x in chunks if x.chunk_id == "financial-1"), None)
        risk = _risk("continuous_loss", RiskCategory.FINANCIAL, "Continuous loss", 78, [] if c is None else [], self.name)
        return [risk.model_copy(update={"calculation": Calculation(
            skill_name="loss_trend_review",
            formula="latest_loss - prior_loss",
            inputs={"latest_loss": -120.0, "prior_loss": -80.0},
            result=-40.0,
            unit="HKD million",
        )})]

class MockLegalAgent:
    name = "legal"
    def analyze(self, profile: IPOProfile, chunks: list[DocumentChunk], market=None):
        c = next((x for x in chunks if x.chunk_id == "legal-1"), None)
        return [_risk("redemption_rights", RiskCategory.LEGAL, "Redemption rights", 72, [] if c is None else [], self.name)]

class MockBusinessAgent:
    name = "business"
    def analyze(self, profile: IPOProfile, chunks: list[DocumentChunk], market=None):
        return [_risk("precommercial_product", RiskCategory.BUSINESS, "Pre-commercial core product", 66, [], self.name)]

class MockMarketAgent:
    name = "market"
    def analyze(self, profile: IPOProfile, chunks: list[DocumentChunk], market=None):
        return [_risk("weak_ipo_market", RiskCategory.MARKET, "Weak IPO market", 60, [], self.name)]
