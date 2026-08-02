from typing import Protocol
from ipo_risk.schemas import ReportContext, ReportSection
class ReportGenerator(Protocol):
    def generate(self, context: ReportContext) -> list[ReportSection]: ...
