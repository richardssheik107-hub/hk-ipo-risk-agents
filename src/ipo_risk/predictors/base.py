from typing import Protocol
from ipo_risk.schemas import MarketSnapshot, PredictionResult, RiskItem
class RiskPredictor(Protocol):
    def predict(self, risks: list[RiskItem], market: MarketSnapshot | None) -> PredictionResult: ...
