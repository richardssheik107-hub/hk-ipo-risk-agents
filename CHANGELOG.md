# Changelog

## v0.1.0-architecture-mvp

### Added

- Pydantic 公共 Schema 与结构化 AnalysisError；
- 配置驱动的组件装配；
- LangGraph mvp_v1 工作流；
- RuleVerifier、RuleSupervisor 与 RuleBasedPredictor；
- 确定性金融 Skill；
- JSON Repository 与 Streamlit 页面；
- 节点故障降级、契约与端到端测试。

### Validation

- pytest -q：24 passed；
- Mock 健康检查：completed，3 条已核验风险、1 条待核验风险；
- Predictor 故障可降级为 partial。

### Mock Components

- DocumentParser、DocumentRetriever；
- 四类专业 Agent；
- LLM、市场和 IPO 数据 Provider；
- ReportGenerator。
