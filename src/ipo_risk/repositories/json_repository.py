import json
from pathlib import Path
from ipo_risk.schemas import IPOAnalysisResult
class JsonAnalysisRepository:
    def __init__(self, directory: str = "data/results"): self.directory = Path(directory); self.directory.mkdir(parents=True, exist_ok=True)
    def save(self, result: IPOAnalysisResult) -> None: (self.directory / f"{result.analysis_id}.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    def get(self, analysis_id: str) -> IPOAnalysisResult | None:
        path = self.directory / f"{analysis_id}.json"
        return IPOAnalysisResult.model_validate_json(path.read_text(encoding="utf-8")) if path.exists() else None
