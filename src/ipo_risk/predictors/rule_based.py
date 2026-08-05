"""Deterministic rule scoring that only consumes verified risks."""

from __future__ import annotations

from ipo_risk.schemas import (
    MarketSnapshot,
    PredictionResult,
    RiskFactor,
    RiskItem,
    RiskLevel,
    VerificationStatus,
)


class RuleBasedPredictor:
    """Score verified risks and explicit market rules without claiming probability."""

    def predict(
        self, risks: list[RiskItem], market: MarketSnapshot | None
    ) -> PredictionResult:
        verified = [
            risk for risk in risks if risk.verification_status == VerificationStatus.VERIFIED
        ]
        excluded_pending = [
            risk for risk in risks if risk.verification_status == VerificationStatus.PENDING
        ]
        excluded_review = [
            risk for risk in risks if risk.verification_status == VerificationStatus.NEEDS_REVIEW
        ]
        excluded_rejected = [
            risk for risk in risks if risk.verification_status == VerificationStatus.REJECTED
        ]

        market_available = market is not None and market.sentiment_score is not None
        market_adjustment = (
            15.0
            if market_available and market is not None and market.sentiment_score < 50
            else 0.0
        )
        base_score = (
            sum(risk.score for risk in verified) / len(verified) if verified else 0.0
        )
        risk_score = min(100.0, base_score + market_adjustment)
        level = (
            RiskLevel.CRITICAL
            if risk_score >= 85
            else RiskLevel.HIGH
            if risk_score >= 70
            else RiskLevel.MEDIUM
            if risk_score >= 40
            else RiskLevel.LOW
        )

        factors = [
            RiskFactor(
                feature_name=risk.risk_code,
                feature_value=risk.score,
                contribution=risk.score / 100,
                direction="increase",
                explanation=risk.conclusion,
                source="verified_risk_item",
            )
            for risk in sorted(verified, key=lambda item: item.score, reverse=True)[:3]
        ]
        if market_adjustment:
            factors.append(
                RiskFactor(
                    feature_name="market_sentiment_below_50",
                    feature_value=market.sentiment_score if market is not None else None,
                    contribution=market_adjustment / 100,
                    direction="increase",
                    explanation="A deterministic weak-market adjustment was applied.",
                    source="market_snapshot_rule",
                )
            )

        available_features = [f"verified_risk:{risk.risk_code}" for risk in verified]
        if market_available:
            available_features.append("market_sentiment_score")
        missing_features = []
        if not verified:
            missing_features.append("verified_risks")
        if not market_available:
            missing_features.append("market_sentiment_score")
        degradation_reasons = []
        if not verified:
            degradation_reasons.append("verified_risks_missing")
        if not market_available:
            degradation_reasons.append("market_sentiment_score_missing")
        degraded_mode = bool(degradation_reasons)
        excluded_count = len(excluded_pending) + len(excluded_review) + len(excluded_rejected)
        explanation = (
            "Deterministic rule score; not a calibrated probability. "
            f"Used {len(verified)} verified risk(s) and excluded {excluded_count} untrusted risk(s). "
            f"Missing features: {', '.join(missing_features) if missing_features else 'none'}."
        )
        return PredictionResult(
            model_name="RuleBasedPredictor",
            model_version="rule_v2",
            target="five_day_significant_decline_risk",
            risk_score=risk_score,
            risk_level=level,
            probabilities={},
            top_factors=factors,
            explanation=explanation,
            feature_snapshot={
                "verified_risk_count": len(verified),
                "market_sentiment_score": (
                    market.sentiment_score if market_available and market is not None else None
                ),
            },
            metadata={
                "scoring_mode": "deterministic_rule",
                "score_is_probability": False,
                "used_verified_risk_ids": [risk.risk_id for risk in verified],
                "excluded_pending_risk_ids": [risk.risk_id for risk in excluded_pending],
                "excluded_needs_review_risk_ids": [risk.risk_id for risk in excluded_review],
                "excluded_rejected_risk_ids": [risk.risk_id for risk in excluded_rejected],
                "available_features": available_features,
                "missing_features": missing_features,
                "degraded_mode": degraded_mode,
                "degradation_reasons": degradation_reasons,
                "market_adjustment_applied": bool(market_adjustment),
                "policy_version": "rule_based_predictor_v2",
            },
        )
