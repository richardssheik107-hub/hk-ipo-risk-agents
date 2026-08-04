"""Service-only acceptance check for the v0.2 real cash-runway slice."""

from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from ipo_risk.core.config import load_settings
from ipo_risk.schemas import IPOAnalysisRequest, RiskLevel, TaskStatus, VerificationStatus
from ipo_risk.services.analysis_service import IPOAnalysisService


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    pdf_path = Path(
        os.getenv(
            "IPO_RISK_REAL_CASE_PDF",
            "data/local/real_case_001/prospectus.pdf",
        )
    )
    require(pdf_path.exists(), "Real-case PDF does not exist")
    with TemporaryDirectory(prefix="ipo-risk-v02-") as data_dir:
        settings = replace(
            load_settings("configs/real_pdf.yaml"), data_dir=data_dir
        )
        service = IPOAnalysisService(settings=settings)
        result = service.analyze(
            IPOAnalysisRequest(
                company_name="浙江同源康医药股份有限公司",
                stock_code="2410.HK",
                prospectus_path=str(pdf_path),
                use_mock=False,
            )
        )

        require(result.status == TaskStatus.COMPLETED, f"Unexpected status: {result.status}")
        cash_runway = next(
            (risk for risk in result.verified_risks if risk.risk_code == "cash_runway"),
            None,
        )
        require(cash_runway is not None, "Verified cash_runway risk is missing")
        require(
            cash_runway.verification_status == VerificationStatus.VERIFIED,
            "cash_runway is not verified",
        )
        require([item.page for item in cash_runway.evidence] == [563, 562], "Evidence pages changed")
        require(cash_runway.calculation is not None, "Calculation is missing")
        require(cash_runway.calculation.result == "2.76", "Runway result changed")
        require(cash_runway.calculation.unit == "months", "Runway unit changed")
        require(cash_runway.level == RiskLevel.CRITICAL, "Risk level changed")
        require(cash_runway.score == 90, "Rule score changed")
        require(
            cash_runway.metadata.get("canonical_code") == "FIN_CASH_RUNWAY",
            "Canonical code changed",
        )

        prediction = result.prediction
        require(prediction is not None, "Prediction is missing")
        require(prediction.risk_score == 90, "Prediction score changed")
        require(prediction.risk_level == RiskLevel.CRITICAL, "Prediction level changed")
        require(prediction.probabilities == {}, "Rule predictor emitted probabilities")
        require(prediction.metadata.get("score_is_probability") is False, "Score mislabeled")
        require(prediction.metadata.get("degraded_mode") is True, "Missing market data not degraded")
        require(
            "market_sentiment_score_missing"
            in prediction.metadata.get("degradation_reasons", []),
            "Market-data degradation reason is missing",
        )
        require(
            any(factor.feature_name == "cash_runway" for factor in prediction.top_factors),
            "Cash runway is absent from top factors",
        )

        expected_modes = {
            "parser": "real",
            "retriever": "real",
            "financial_agent": "real",
            "legal_agent": "unavailable",
            "business_agent": "unavailable",
            "market_agent": "unavailable",
            "market_data_provider": "unavailable",
            "report_generator": "mock",
        }
        modes = result.metadata.get("component_modes", {})
        require(
            all(modes.get(key) == value for key, value in expected_modes.items()),
            f"Unexpected component modes: {modes}",
        )
        require(
            not any("Mock finding" in risk.conclusion for risk in result.verified_risks),
            "Mock professional risk contaminated real mode",
        )
        repository_logs = [
            log
            for log in result.agent_logs
            if log.agent_name == "analysis_repository" and log.action == "save"
        ]
        require(repository_logs, "Repository save log is missing")
        require(
            repository_logs[-1].metadata.get("round_trip_verified") is True,
            "Repository round-trip was not verified",
        )

        print(f"status={result.status.value}")
        print(f"analysis_id={result.analysis_id}")
        print(f"document={result.metadata.get('document')}")
        print(f"component_modes={modes}")
        print(f"evidence_pages={[item.page for item in cash_runway.evidence]}")
        print(f"calculation_result={cash_runway.calculation.result}")
        print(f"verification_status={cash_runway.verification_status.value}")
        print(f"prediction={prediction.risk_score}/{prediction.risk_level.value}")
        print(f"degradation_reasons={prediction.metadata.get('degradation_reasons')}")
        print(f"agent_log_components={[log.agent_name for log in result.agent_logs]}")
        print("A6 real Service-level E2E acceptance: passed")


if __name__ == "__main__":
    main()
