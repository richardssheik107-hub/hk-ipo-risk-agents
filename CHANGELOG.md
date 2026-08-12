# Changelog

## Unreleased — v0.3.0-multi-agent-risk-analysis

### Final technical completion (owner-waived human certification)

- integrated real Financial, Legal and Business Agents into the shared registry and container;
- added deterministic `SpecializedVerifierRouter`, `V03Supervisor` and `enhanced_v2`;
- exposed offline and optional AI-enhanced runtime modes through `IPOAnalysisService`;
- added Streamlit domain views and Markdown/JSON downloads;
- added structured v0.3 reporting and explicit evaluation provenance;
- preserved `mvp_v1`, Mock mode and the released v0.2 regression;
- deferred Financial 23-row and Business 3-row independent human second review by explicit owner waiver;
- did not claim formal Financial/Business or combined cross-domain Golden metrics;
- did not access the 2025 blind set or start v0.4 market prediction work.

### Final product completion

- completed the product-first Streamlit experience with IPO Profile, overall rule-score
  dashboard, domain status, risk cards, Supervisor and runtime diagnostics;
- expanded Markdown/JSON downloads to preserve Evidence, Calculation, Verifier and
  structured section metadata;
- froze the deterministic v0.3 report at ten auditable sections;
- added explicit cross-domain supervisory synthesis and rule-score components without
  inventing a new verified risk or probability;
- kept Golden governance `PARTIAL` while classifying it as a research-validation
  limitation rather than a software release blocker;
- preserved public Schema/Protocol boundaries, `mvp_v1`, Mock and v0.2 behavior.

### Human Golden final closeout

- froze `single_named_human_review_v1`, permanently removing independent second
  review as a Financial/Business release requirement;
- promoted 23 Financial and 3 Business named-human primary reviews as
  `first_reviewed`, without populating `second_reviewer`;
- preserved all eight Legal double-reviewed/adjudicated judgments unchanged;
- completed provenance-filtered Financial, Legal, Business and cross-domain evaluation;
- superseded the active Owner waiver while preserving it as historical audit provenance;
- closed all Gate A items without using 2025 blind data or tuning production behavior.

### Merged

- PR #20：新增`CatalogIPODataProvider`、特殊证券治理、批量运行、断点续跑、2025盲测保护和黄金案例评测基础设施；
- PR #21：新增Planner → Executor基础设施，包括`execute-approved-plan` Skill、Plan Validator、Scope Guard和Execution Report工作区；
- PR #23：完成八类v0.3 Retriever查询族、简繁英别名、确定性章节权重和稳定Evidence追溯；
- PR #22：合并Financial v0.3核心链路，包括财务事实抽取、Decimal Skills、`V03FinancialAgent`和`V03FinancialVerifier`；
- PR #24：合并OpenAI-compatible、Mock和Unavailable LLMProvider，配置驱动装配、有限重试、安全异常分类及Pydantic结构化校验。

### Current validation

- 本次技术收口基线：`main@b60570ef0854b198c6e4827336cb4a3b529fe462`；
- 完整自动化测试：893 passed；
- 项目校验、赛事数据校验、Golden manifest integrity、compileall与diff check通过；
- Streamlit Mock与v0.3 offline真实PDF浏览器smoke通过；
- 2410.HK回归：706页、0解析错误、Evidence第563/562页、现金跑道2.76个月、verified、90/critical。

### Remaining limitations

- 正式Golden采用一次具名人工复核政策，不应误称为独立双审评测；
- 真实外部LLM endpoint smoke未执行；
- 1167.HK、9633.HK和Legal真实demo fixture在本次本地执行中不可用；
- PDF报告导出未加入，本版支持Markdown和结构化JSON；
- v0.4 Market Agent、标签、概率模型尚未开始。

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
