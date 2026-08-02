from ipo_risk.schemas import MarketSnapshot, PredictionResult, RiskFactor, RiskItem, RiskLevel
class RuleBasedPredictor:
    def predict(self, risks: list[RiskItem], market: MarketSnapshot | None) -> PredictionResult:
        risk_score = min(100, sum(r.score for r in risks) / max(1, len(risks)) + (15 if market and (market.sentiment_score or 100) < 50 else 0))
        factors = [RiskFactor(feature_name=r.risk_code, feature_value=r.score, contribution=r.score / 100, direction="increase", explanation=r.conclusion, source="risk_item") for r in sorted(risks, key=lambda r: r.score, reverse=True)[:3]]
        level = RiskLevel.CRITICAL if risk_score >= 85 else RiskLevel.HIGH if risk_score >= 70 else RiskLevel.MEDIUM if risk_score >= 40 else RiskLevel.LOW
        return PredictionResult(model_name="RuleBasedPredictor", risk_score=risk_score, risk_level=level, top_factors=factors, explanation="Deterministic MVP score; not a calibrated probability.")
