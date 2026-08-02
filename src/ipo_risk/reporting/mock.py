from ipo_risk.schemas import ReportContext, ReportSection
class MockReportGenerator:
    def generate(self, context: ReportContext) -> list[ReportSection]:
        risks = context.verified_risks + context.pending_risks
        return [ReportSection(title="Risk Summary", summary=f"{context.profile.company_name}: {len(context.verified_risks)} verified and {len(context.pending_risks)} pending risks.", risks=risks, evidence_ids=[e.evidence_id for r in risks for e in r.evidence], order=1)]
