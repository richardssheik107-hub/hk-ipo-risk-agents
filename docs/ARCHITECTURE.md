# 港股IPO风险预警系统架构设计

## 1. 架构形式

本项目采用模块化单体架构。

基本原则：

1. 使用一个Git仓库；
2. 使用一个主要Python应用；
3. 各模块具有清晰边界；
4. 各模块通过固定Schema和接口连接；
5. 不使用微服务；
6. 不引入不必要的分布式基础设施；
7. 支持五名成员并行开发；
8. 支持Mock实现逐步替换为真实实现。

## 2. 整体调用链路

系统调用方向必须为：

Streamlit UI
→ IPOAnalysisService
→ LangGraph Workflow
→ Agents
→ Skills、Parser、Retriever、Predictor和Providers
→ Repositories

禁止反向依赖。

## 3. 推荐项目结构

项目后续应形成以下结构：

```text
hk-ipo-risk-agents/
├── app/
│   ├── streamlit_app.py
│   ├── pages/
│   └── components/
├── src/
│   └── ipo_risk/
│       ├── core/
│       ├── schemas/
│       ├── domain/
│       ├── parsers/
│       ├── retrieval/
│       ├── agents/
│       ├── skills/
│       ├── workflows/
│       ├── predictors/
│       ├── providers/
│       ├── repositories/
│       ├── services/
│       ├── evaluation/
│       └── reporting/
├── prompts/
├── configs/
├── data/
├── models/
├── tests/
│   ├── unit/
│   ├── contract/
│   ├── integration/
│   ├── regression/
│   └── golden_cases/
├── scripts/
├── docs/
├── AGENTS.md
├── .env.example
├── pyproject.toml
├── start.bat
├── start.sh
└── README.md
```

## 4. 各层职责

### 4.1 展示层

目录：

```text
app/
```

职责：

1. 文件上传；
2. 公司信息输入；
3. 风险结果展示；
4. Evidence展示；
5. Agent日志展示；
6. 错误信息展示；
7. 报告下载入口。

限制：

Streamlit只能调用IPOAnalysisService。

禁止：

1. 直接调用LLM；
2. 直接调用Agent；
3. 直接解析PDF；
4. 直接访问数据库；
5. 直接运行预测模型；
6. 直接进行金融计算。

### 4.2 应用服务层

目录：

```text
src/ipo_risk/services/
```

核心服务：

```text
IPOAnalysisService
DocumentService
PredictionService
ReportService
```

职责：

1. 接收分析请求；
2. 选择工作流；
3. 调用文档处理；
4. 调用Agent工作流；
5. 调用预测模型；
6. 保存结果；
7. 返回IPOAnalysisResult。

### 4.3 工作流层

目录：

```text
src/ipo_risk/workflows/
```

职责：

1. 定义LangGraph State；
2. 定义工作流节点；
3. 定义节点之间的边；
4. 定义条件路由；
5. 管理Agent失败后的处理；
6. 保存执行日志；
7. 支持不同工作流版本。

第一阶段至少预留：

```text
mvp_v1
enhanced_v2
```

第一阶段只要求完整实现mvp_v1。

### 4.4 Agent层

目录：

```text
src/ipo_risk/agents/
```

Agent包括：

1. Financial Agent；
2. Legal Agent；
3. Business Agent；
4. Market Agent；
5. Verifier Agent；
6. Supervisor Agent。

所有专业Agent必须实现统一RiskAgent接口。

所有专业Agent必须返回：

```text
list[RiskItem]
```

Agent不得：

1. 操作Streamlit；
2. 修改数据库结构；
3. 自行定义公共输出格式；
4. 使用LLM完成精确金融计算；
5. 绕过Evidence机制直接生成正式风险。

### 4.5 Skill层

目录：

```text
src/ipo_risk/skills/
```

职责：

1. 现金跑道计算；
2. 财务增长率计算；
3. 客户集中度计算；
4. 供应商集中度计算；
5. 收益率计算；
6. 市场热度计算；
7. 条款关键词检索；
8. 同行比较。

Skill必须：

1. 使用确定性Python代码；
2. 可独立测试；
3. 输入和输出明确；
4. 不直接调用前端；
5. 不依赖大语言模型完成数学计算。

### 4.6 文档解析层

目录：

```text
src/ipo_risk/parsers/
```

职责：

1. PDF解析；
2. 页码保留；
3. 文本块提取；
4. 表格识别；
5. 标题识别；
6. 页面坐标保存。

所有Parser必须实现统一DocumentParser接口，并返回：

```text
list[DocumentChunk]
```

### 4.7 文档检索层

目录：

```text
src/ipo_risk/retrieval/
```

职责：

1. 文档切片；
2. 文档索引；
3. 关键词检索；
4. 语义检索；
5. 结果重排；
6. Evidence定位；
7. 页码和原文返回。

### 4.8 预测层

目录：

```text
src/ipo_risk/predictors/
```

预测器包括：

1. RuleBasedPredictor；
2. LogisticPredictor；
3. LightGBMPredictor；
4. EnsemblePredictor。

第一阶段只实现RuleBasedPredictor。

所有Predictor必须实现统一RiskPredictor接口并返回：

```text
PredictionResult
```

### 4.9 Provider层

目录：

```text
src/ipo_risk/providers/
```

职责：

1. 大模型调用；
2. 市场数据获取；
3. IPO基础信息获取；
4. 外部数据格式转换。

Provider不得将外部数据格式直接传给上层，必须转换为内部Schema。

### 4.10 Repository层

目录：

```text
src/ipo_risk/repositories/
```

职责：

1. 保存解析结果；
2. 保存Agent日志；
3. 保存风险结果；
4. 保存分析任务；
5. 保存模型输出；
6. 读取缓存结果。

第一阶段可以使用JSON、SQLite或内存Repository。

### 4.11 评测层

目录：

```text
src/ipo_risk/evaluation/
```

职责：

1. 风险抽取Precision；
2. 风险抽取Recall；
3. 风险抽取F1；
4. Evidence Recall；
5. Evidence Precision；
6. 幻觉率；
7. 预测模型指标；
8. 回归测试结果。

### 4.12 报告层

目录：

```text
src/ipo_risk/reporting/
```

职责：

1. 组织最终报告；
2. 生成HTML报告；
3. 生成PDF报告；
4. 生成结构化JSON；
5. 支持报告模板版本管理。

## 5. 公共依赖规则

允许：

```text
app → services
services → workflows
workflows → agents
agents → skills
agents → retrieval
services → predictors
services → repositories
```

禁止：

```text
skills → agents
agents → app
repositories → app
predictors → app
parsers → workflows
schemas → 业务模块
```

schemas和core应处于依赖关系的底层。

## 6. 可替换接口

以下组件必须通过接口或抽象类创建：

1. DocumentParser；
2. DocumentRetriever；
3. RiskAgent；
4. RiskPredictor；
5. LLMProvider；
6. MarketDataProvider；
7. IPODataProvider；
8. Repository；
9. ReportGenerator。

Mock实现和真实实现必须返回相同Schema。

## 7. 配置管理

通过YAML配置文件和环境变量管理：

1. workflow版本；
2. parser实现；
3. retriever实现；
4. predictor实现；
5. LLM Provider；
6. LLM模型名称；
7. 是否启用Verifier；
8. 是否启用真实市场数据；
9. 是否启用报告导出；
10. 数据存储位置；
11. 日志级别。

禁止在业务代码中硬编码：

1. API Key；
2. Token；
3. 密码；
4. 模型名称；
5. 数据库密码；
6. 用户本地路径。

## 8. Agent日志

每个Agent和Skill运行时必须记录：

1. task_id；
2. step；
3. agent_name；
4. action；
5. tool_name；
6. status；
7. input_summary；
8. output_summary；
9. evidence_ids；
10. error；
11. started_at；
12. finished_at。

日志中不保存完整API Key或其他敏感信息。

## 9. Evidence规则

所有正式RiskItem必须具有Evidence。

没有Evidence的风险：

1. verification_status设置为pending；
2. 不进入verified_risks；
3. 进入pending_risks；
4. 提示人工复核。

包含数字的结论必须同时具有：

1. 原始数据Evidence；
2. Calculation；
3. 使用的Skill；
4. 计算结果。

## 10. 异常处理

单个Agent失败时：

1. 记录AgentLog；
2. 将错误写入IPOAnalysisResult.errors；
3. 尽量继续执行其他独立Agent；
4. 不应导致Streamlit程序整体崩溃；
5. Supervisor应明确说明哪些模块未完成。

## 11. 版本设计

工作流版本：

```text
mvp_v1
enhanced_v2
competition_v3
```

Schema版本：

```text
1.0
```

Prompt版本：

```text
financial_v1
legal_v1
business_v1
verifier_v1
supervisor_v1
```

模型版本：

```text
rule_v1
logistic_v1
lightgbm_v1
```

## 12. 架构原则

所有版本必须坚持：

1. 架构完整；
2. 实现简化；
3. 接口稳定；
4. Mock可替换；
5. 测试可执行；
6. 版本可回退；
7. 不过度设计；
8. 不引入与当前规模不匹配的基础设施。

## 13. 已确认公共契约补充

1. DocumentParser接收独立的DocumentParseRequest；
2. IPODataProvider统一返回IPOProfile；
3. ReportGenerator只接收ReportContext，不依赖IPOAnalysisResult；
4. Verifier和Supervisor使用确定性规则实现；
5. WorkflowState对日志、错误和风险列表定义追加或去重Reducer；
6. 工作流内执行Predictor和ReportGenerator，Service负责装配依赖和保存结果。

## 14. 加固迭代约束

1. 组件由YAML、环境变量和默认值驱动的注册表装配；
2. Service不直接获取IPO或市场数据，工作流准备节点负责获取；
3. 组件失败统一写入AnalysisError和AgentLog，并尽可能返回partial结果；
4. Verifier和Supervisor使用独立Protocol及结构化结果；
5. 风险是否需要Evidence或Calculation由domain风险注册表决定。

## 15. 当前实现基线

当前稳定版本`v0.2.0-real-document-slice`沿用该架构。组件由 ComponentRegistry 和
DependencyContainer 装配，优先级为环境变量 > YAML > 代码默认值。

实际工作流为：

```text
load_ipo_profile
→ load_market_snapshot
→ document
→ financial
→ legal
→ business
→ market
→ verifier
→ supervisor
→ predictor
→ report
```

IPOAnalysisService 仅负责读取配置、装配依赖、选择并执行工作流、持久化和返回结果；
IPO 数据、市场快照、Predictor 与 ReportGenerator 均在工作流内执行一次。
ReportGenerator 接收 ReportContext，避免对 IPOAnalysisResult 的循环依赖。

RiskVerifier 和 RiskSupervisor 是独立接口，分别返回 VerificationResult 和
SupervisionResult。统一节点包装器将组件异常记录为 AgentLog 与 AnalysisError，
并尽可能保留已有结果，使分析进入 partial 而非中断。WorkflowState 对风险、日志和
错误使用追加或去重 Reducer，防止节点结果覆盖先前状态。

Verifier和Supervisor使用确定性规则实现，以自动验证Evidence、Calculation及风险去重规则。

### v0.3实现状态（截至`main@f9449fc`）

- Retriever查询族已泛化并合并；
- Mock、OpenAI-compatible与Unavailable LLMProvider已注册，Settings与Container支持运行时配置、安全重试和缺配置降级；
- `V03FinancialAgent`与`V03FinancialVerifier`核心模块已合并并可独立调用，但尚未加入共享Container、Workflow或Service；
- standalone Legal Agent、Legal domain Verifiers与standalone `V03BusinessAgent`已合并，但尚未加入共享Container、Workflow或Service；
- `CatalogIPODataProvider`与批量评测基础设施已合并，但Catalog目前只由批量运行器运行时注册，尚未进入全局ComponentRegistry；
- 共享Legal与Business仍使用disabled/Mock实现；这不等于standalone模块尚未实现；
- 稳定工作流仍为`mvp_v1`，`enhanced_v2`尚未实现。

因此“模块已实现”不等同于“共享工作流已集成”。后续由技术负责人统一完成受保护的Container、Workflow和Service装配，避免专业成员并行修改共享边界。

## v0.3 契约冻结边界

v0.3 继续使用统一 `RiskAgent.analyze(...) -> list[RiskItem]`，不为三类专业 Agent 建立不兼容的公共返回类型。结构化候选模型保留在各 Agent 内部；`DiagnosticSource.last_diagnostics` 是不改变风险返回类型的旁路诊断接口。

风险所有权为 Financial 5 类、Legal 2 类、Business 1 类。Market 节点在 `enhanced_v2` 中保留，但 v0.3 数据不可用时必须记录 skipped/unavailable，禁止生成 Mock 市场风险。阈值由 `configs/v03_risk_rules.yaml` 版本化管理，完整边界见 `V03_DEVELOPMENT_CONTRACT.md`。

