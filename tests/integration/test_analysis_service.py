from ipo_risk.services.analysis_service import IPOAnalysisService
from ipo_risk.core.config import Settings
from ipo_risk.core.container import DependencyContainer, default_registry
from ipo_risk.reporting.mock import MockReportGenerator
from ipo_risk.repositories.json_repository import JsonAnalysisRepository
from ipo_risk.schemas import IPOAnalysisRequest, LogStatus, TaskStatus


class _TupleMetadataReportGenerator(MockReportGenerator):
    def generate(self, context):
        sections = super().generate(context)
        return [
            section.model_copy(
                update={"metadata": {"source": {"bbox": (1, 2, 3, 4)}}}
            )
            for section in sections
        ]


def _tuple_metadata_service(tmp_path, repository=None):
    settings = Settings(data_dir=str(tmp_path))
    registry = default_registry()
    registry.register("report_generator", "mock", _TupleMetadataReportGenerator)
    return IPOAnalysisService(
        settings=settings,
        container=DependencyContainer(settings, registry),
        repository=repository or JsonAnalysisRepository(tmp_path),
    )

def test_mock_analysis_runs_end_to_end(tmp_path):
    from ipo_risk.repositories.json_repository import JsonAnalysisRepository
    result = IPOAnalysisService(JsonAnalysisRepository(tmp_path)).analyze(IPOAnalysisRequest(company_name="Demo"))
    assert result.status is TaskStatus.COMPLETED
    assert result.prediction is not None
    assert result.verified_risks and result.pending_risks and result.report_sections and result.agent_logs


def test_mock_analysis_round_trip_accepts_tuple_metadata(tmp_path):
    service = _tuple_metadata_service(tmp_path)
    result = service.analyze(IPOAnalysisRequest(company_name="Demo"))
    persisted = service.repository.get(result.analysis_id)

    assert result.status is TaskStatus.COMPLETED, result.errors
    assert result.prediction is not None
    assert result.verified_risks and result.pending_risks
    assert result.report_sections[0].metadata["source"]["bbox"] == (1, 2, 3, 4)
    assert persisted.report_sections[0].metadata["source"]["bbox"] == [1, 2, 3, 4]
    assert persisted.model_dump(mode="json") == result.model_dump(mode="json")
    assert result.agent_logs[-1].status is LogStatus.SUCCESS
    assert result.agent_logs[-1].metadata["round_trip_verified"] is True


def test_mock_analysis_round_trip_rejects_changed_metadata(tmp_path):
    import json

    class TamperingRepository(JsonAnalysisRepository):
        def save(self, result):
            super().save(result)
            path = self.directory / f"{result.analysis_id}.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["report_sections"][0]["metadata"]["source"]["bbox"][0] = 99
            path.write_text(json.dumps(payload), encoding="utf-8")

    repository = TamperingRepository(tmp_path)
    result = _tuple_metadata_service(tmp_path, repository).analyze(
        IPOAnalysisRequest(company_name="Demo")
    )

    assert result.status is TaskStatus.PARTIAL
    assert result.prediction is not None
    assert result.report_sections[0].metadata["source"]["bbox"] == (1, 2, 3, 4)
    assert result.errors[-1].code == "save_failure"
    assert "round-trip verification" in result.errors[-1].message
    save_logs = [log for log in result.agent_logs if log.agent_name == "analysis_repository"]
    assert len(save_logs) == 1
    assert save_logs[0].status is LogStatus.FAILED
