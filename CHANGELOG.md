# Changelog

## v0.2.0-real-document-slice - 2026-08-06

### Added

- PyMuPDF真实PDF解析与关键词Evidence检索；
- 现金和经营现金流确定性提取；
- 现金跑道Calculation、RiskItem及专用Verifier；
- 真实CashRunwayFinancialAgent；
- unavailable专业Agent、市场数据Provider及request IPO Provider；
- Service metadata、持久化往返验证和真实Service级E2E；
- Streamlit安全PDF上传、组件模式及完整证据链展示。

### Validation

- 自动化测试：284 passed；
- PR #17 GitHub Actions：pytest与compileall通过；
- 2410.HK：现金第563页、经营现金流第562页；
- 现金跑道：2.76个月，verified，critical / 90；
- 无真实市场数据时保持90分并明确进入degraded模式；
- 规则评分不输出概率。
- 赛事数据校验、项目校验与编译检查通过；
- 565份招股书manifest、555/10行情覆盖与562/3官方IPO主数据桥接完成。
- 远程main全新克隆、Python 3.12.10虚拟环境安装和完整验收通过；
- 2410.HK第562/563页已完成第二次独立证据复核；
- Streamlit真实场景与Predictor故障降级场景人工验收通过。

### Fixed

- Extractor或Risk Builder异常时刷新Financial Agent结构化失败诊断；
- Streamlit PDF上传增加200 MB显式大小上限。

### Known Limitations

- 真实链路只覆盖现金跑道，Legal、Business和Market Agent仍不可用；
- LLMProvider未进入生产链路，ReportGenerator仍为Mock格式化实现；
- 规则分不是上市后下跌概率；扫描型PDF/OCR和统计预测模型尚未实现。

## v0.3.0-multi-agent-risk-analysis (Planned)

### Scope Frozen

- Financial、Legal、Business三个真实专业Agent；
- 八类证据驱动风险与专用Verifier；
- 五至十份黄金案例、批量评测和`enhanced_v2`工作流；
- 保留`mvp_v1`、Mock模式、v0.2现金跑道回归和无API Key确定性链路；
- 市场标签、Market Agent与预测模型延后至v0.4。

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
