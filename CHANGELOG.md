# Changelog

## Unreleased — v0.3 development

### Merged

- PR #20：新增`CatalogIPODataProvider`、特殊证券治理、批量运行、断点续跑、2025盲测保护和黄金案例评测基础设施；
- PR #21：新增Planner → Executor基础设施，包括`execute-approved-plan` Skill、Plan Validator、Scope Guard和Execution Report工作区；
- PR #23：完成八类v0.3 Retriever查询族、简繁英别名、确定性章节权重和稳定Evidence追溯；
- PR #22：合并Financial v0.3核心链路，包括财务事实抽取、Decimal Skills、`V03FinancialAgent`和`V03FinancialVerifier`；
- PR #24：合并OpenAI-compatible、Mock和Unavailable LLMProvider，配置驱动装配、有限重试、安全异常分类及Pydantic结构化校验。

### Current validation

- 本次状态对齐基线：`main@affaa28c03c22590ffc36cf34595b635357bf8ee`；
- 完整自动化测试：625 passed；
- 2410.HK回归：706页、0解析错误、Evidence第563/562页、现金跑道2.76个月、verified、90/critical。

### Remaining limitations

- Legal与Business真实Agent尚未进入main；
- Financial v0.3核心模块尚待共享Container、Workflow和Service集成；
- `CatalogIPODataProvider`尚待全局ComponentRegistry注册；
- LLMProvider尚未被真实Legal/Business Agent消费，真实外部endpoint smoke未执行；
- `enhanced_v2`、完整黄金案例双人复核、真实批量评测和v0.3 Release尚未完成。

本节是开发中状态，不代表已创建v0.3 Release。

## v0.2.0-real-document-slice - 2026-08-06

Release: https://github.com/richardssheik107-hub/hk-ipo-risk-agents/releases/tag/v0.2.0-real-document-slice

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
