# HK IPO Risk Agents

基于证据驱动多智能体协同的港股IPO招股书解析与上市后风险预警系统。

## 项目状态

当前阶段：

```text
v0.2.0已正式发布；v0.3.0处于Gate A——专业Agent闭环与黄金案例复核
```

稳定版本：[v0.2.0-real-document-slice](https://github.com/richardssheik107-hub/hk-ipo-risk-agents/releases/tag/v0.2.0-real-document-slice)。

v0.2.0完成真实PDF解析、关键词Evidence检索、财务数值提取、现金跑道计算与核验、规则评分、Service级E2E、Streamlit真实模式和赛事数据治理。发布验收为284 passed，完整版本记录见[CHANGELOG](CHANGELOG.md)。

截至`main@f1e792a85dd4266471509c76e0079ed042c1f175`（Merge PR #32），v0.3已合并Retriever查询族泛化、可替换LLMProvider及Legal domain prompt runtime routing、Financial核心与Verifier、standalone Legal Agent及Legal domain Verifiers、standalone `V03BusinessAgent`，以及Catalog Provider与批量评测基础设施。三个专业Agent的standalone core均已存在，但共享`enhanced_v2`工作流和v0.3发布尚未完成。完整进度以[项目主清单](docs/PROJECT_MASTER_CHECKLIST.md)为唯一入口，当前Gate A门槛见[Gate A收口验收表](docs/V03_GATE_A_CLOSEOUT.md)。

## 核心流程

```text
招股书PDF
→ 文档解析
→ 文档检索
→ 财务Agent
→ 法务Agent
→ 业务Agent
→ 市场Agent
→ Verifier Agent
→ Supervisor Agent
→ 风险预测
→ 风险报告
```

## 核心设计原则

1. 采用模块化单体架构；
2. 不将业务逻辑集中在一个Python文件；
3. 所有模块使用统一Pydantic Schema；
4. 精确金融计算由Python Skill完成；
5. 风险结论必须支持Evidence；
6. Mock实现和真实实现使用相同接口；
7. Streamlit只能调用IPOAnalysisService；
8. 新功能必须具有测试；
9. 工作流和模型支持版本管理；
10. 稳定版本必须支持回退。

## 当前实现范围

真实或确定性实现：

- ComponentRegistry 与 DependencyContainer 配置装配；
- PyMuPDF DocumentParser与已泛化到财务、法务、业务查询族的KeywordDocumentRetriever；
- `OpenAICompatibleLLMProvider`、Mock/Unavailable Provider、安全重试与Pydantic结构化校验；
- CashRunwayFinancialAgent，以及独立可调用的`V03FinancialAgent`和`V03FinancialVerifier`；
- 财务事实抽取、Decimal确定性Skills及五类Financial风险核心模块；
- standalone Legal Agent、两类Legal风险链路及Legal domain Verifiers；
- standalone `V03BusinessAgent`及`precommercial_product`确定性规则；
- CashRunwayRiskVerifier、RuleSupervisor和verified-only RuleBasedPredictor；
- RequestIPODataProvider与UnavailableMarketDataProvider；
- JSON Repository、LangGraph工作流、结构化故障降级和Streamlit证据链展示；
- `CatalogIPODataProvider`、565份招股书manifest、固定数据集划分、批量运行与黄金评测基础设施。

当前边界：

- Financial、Legal、Business三个专业Agent的standalone core均已合并，但共享Container尚未装配这些v0.3真实实现；
- Financial共享注册表仍主要使用`cash_runway`，Legal与Business共享注册表仍为`disabled`/Mock；Market Agent也仍为`disabled`/Mock；
- `V03FinancialAgent`与`V03FinancialVerifier`已合并且可独立调用，但尚未注册到共享Container/Workflow/Service；
- `CatalogIPODataProvider`可由批量运行器运行时注册，但尚未进入全局ComponentRegistry；
- LLMProvider基础设施与Legal domain prompt real-provider runtime routing已合并，GATE-A-10为PASS；standalone专业Agent已具备结构化Provider消费或安全降级路径，但外部真实endpoint smoke仍未执行；
- `enhanced_v2`与v0.3多Agent Service/UI尚未完成，当前稳定工作流仍为`mvp_v1`；
- 真实市场数据为`unavailable`，不会使用Mock市场情绪加分；
- ReportGenerator仍为Mock格式化组件；
- 扫描版PDF/OCR、统计预测模型和真实概率尚未实现；
- 页面中的90分是确定性规则分，不是下跌概率，也不构成投资建议。

## 项目文档

请先阅读：

1. [项目规格](docs/PROJECT_SPEC.md)
2. [架构设计](docs/ARCHITECTURE.md)
3. [公共Schema](docs/DATA_SCHEMA.md)
4. [v0.3主计划](docs/PROJECT_MASTER_CHECKLIST.md)
5. [Gate A收口验收表](docs/V03_GATE_A_CLOSEOUT.md)
6. [版本路线](docs/ROADMAP.md)
7. [赛事数据概览](docs/COMPETITION_DATA_OVERVIEW.md)与[数据质量报告](docs/DATA_QUALITY_REPORT.md)
8. [Retriever影子测试基线](docs/V0.2_SHADOW_TEST_REPORT.md)
9. [开发规则](AGENTS.md)

## v0.3.0 目标

v0.3.0命名为`multi-agent-risk-analysis`，目标是在保留v0.2现金跑道回归和Mock模式的前提下，实现Financial、Legal、Business三个真实专业Agent、8类正式风险、5—10份黄金案例与批量评测。详细范围、接力顺序和退出门槛以[项目主计划](docs/PROJECT_MASTER_CHECKLIST.md)为准。

## 开发规范

任何开发任务开始前，应先阅读AGENTS.md。

公共Schema、基础Agent接口、工作流State和AnalysisService属于受保护的公共接口，修改时必须说明影响。

## MVP运行

Mock演示模式默认使用离线组件，不需要真实招股书、市场数据或LLM API。

Windows PowerShell：

    python -m pip install -e ".[dev]"
    $env:PYTHONPATH = "src"
    pytest -q
    python scripts/validate_project.py
    python -m streamlit run app/streamlit_app.py

Unix/Linux/macOS：

    python -m pip install -e '.[dev]'
    export PYTHONPATH=src
    pytest -q
    python scripts/validate_project.py
    python -m streamlit run app/streamlit_app.py

默认配置为 configs/mock.yaml。配置优先级为：环境变量（任意 IPO_RISK_字段名）> YAML（IPO_RISK_CONFIG 可指定文件）> 代码默认值。Mock、真实与unavailable实现均通过同一注册表和公共接口切换。

## Mock与真实PDF模式

Mock演示：

```powershell
$env:IPO_RISK_CONFIG = "configs/mock.yaml"
python -m streamlit run app/streamlit_app.py
```

```bash
export IPO_RISK_CONFIG=configs/mock.yaml
python -m streamlit run app/streamlit_app.py
```

真实PDF模式由页面中的“真实PDF现金跑道分析”场景加载`configs/real_pdf.yaml`。上传文件必须为非空PDF并具有`%PDF-`文件头；系统使用随机临时文件，分析成功或异常后都会删除。

真实案例命令：

```powershell
$env:PYTHONPATH = "src"
$env:IPO_RISK_REAL_CASE_PDF = "data/local/real_case_001/prospectus.pdf"
python scripts/check_real_v02_e2e.py
```

```bash
export PYTHONPATH=src
export IPO_RISK_REAL_CASE_PDF=data/local/real_case_001/prospectus.pdf
python scripts/check_real_v02_e2e.py
```

当前组件注册名称：

- Parser：`mock`、`mock_alt`、`pymupdf`；
- Retriever：`mock`、`keyword`；
- Financial Agent（共享注册表）：`mock`、`cash_runway`；standalone `V03FinancialAgent`尚待共享集成；
- Legal/Business/Market Agent（共享注册表）：`mock`、`disabled`；standalone Legal与Business实现已合并但尚待共享集成；
- LLMProvider：`mock`、`openai_compatible`、`unavailable`；
- MarketDataProvider：`mock`、`unavailable`；
- IPODataProvider（共享注册表）：`mock`、`request`；`catalog`尚待全局注册；
- Verifier/Supervisor：`rule`；Predictor：`rule_based`、`fault`；
- Repository：`json`；ReportGenerator：`mock`。

Windows 可运行 `start.bat`，Unix 可运行 `start.sh`。配置默认读取 `configs/mock.yaml`，环境变量优先于 YAML 配置。

## v0.3 开发契约

v0.3 正式编码前已冻结角色输入输出、8 类启用风险的唯一所有权、诊断通道、Supervisor 扩展、LLM 结构化调用和金标准格式。开发人员必须先阅读：

1. [v0.3 开发契约](docs/V03_DEVELOPMENT_CONTRACT.md)
2. [v0.3 风险规则](docs/V03_RISK_RULES.md)
3. [v0.3 标注指南](docs/V03_ANNOTATION_GUIDE.md)
4. [v0.3 LLMProvider 规范](docs/V03_LLM_PROVIDER_SPEC.md)

`weak_ipo_market` 为 v0.4 兼容而保留，但在 v0.3 禁用。任何真实 LLM 密钥只允许通过环境变量注入；曾出现在聊天或日志中的密钥必须先轮换。

