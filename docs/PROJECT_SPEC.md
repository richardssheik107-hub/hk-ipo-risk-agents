# 港股IPO多智能体风险预警系统项目规格

## 1. 项目名称

中文名称：

基于证据驱动多智能体协同的港股IPO招股书解析与上市后风险预警系统

英文名称：

Evidence-Driven Multi-Agent Hong Kong IPO Risk Analysis and Early Warning System

项目简称：

HK IPO Risk Agents

## 2. 项目背景

港股IPO招股书通常篇幅较长，包含复杂的财务数据、公司架构、关联交易、股东特殊权利、监管要求、业务模式和风险因素。

传统人工分析方式存在以下问题：

1. 阅读成本高；
2. 风险信息分散；
3. 财务、法务、业务和市场信息难以统一分析；
4. 不同分析人员可能形成不一致结论；
5. 大语言模型直接分析长文档可能产生证据缺失和幻觉；
6. 传统系统通常只分析基本面，缺少对上市时市场环境的结合。

本项目拟构建一个基于多智能体协同的港股IPO风险分析与预警系统。

系统通过文档解析、证据检索、财务分析、法务分析、业务分析、市场分析、证据核验和风险预测，对港股IPO项目进行结构化分析。

## 3. 项目目标

系统输入：

1. 港股IPO招股书PDF；
2. 公司名称；
3. 股票代码；
4. 上市日期；
5. IPO基础信息；
6. 上市前市场数据。

系统输出：

1. 财务风险；
2. 法务合规风险；
3. 业务经营风险；
4. 市场环境风险；
5. 综合风险评分；
6. 上市后五个交易日显著下跌风险评分；
7. 风险对应的招股书页码和原文证据；
8. 风险计算过程；
9. 智能体执行日志；
10. 风险预警报告。

## 4. 稳定架构基线

项目以已发布的架构级MVP为稳定基础。

架构级MVP应满足：

1. 项目具有完整、清晰、可扩展的工程目录；
2. 前端、应用服务、工作流、Agent、Skill、预测模型、数据接口和评测模块相互分离；
3. 所有模块通过统一的数据Schema进行通信；
4. 使用LangGraph建立完整多智能体工作流；
5. 暂未完成的业务模块允许使用Mock或unavailable实现；
6. 使用Mock数据时，端到端流程也必须能够运行；
7. 后续五名成员可以分别替换各自负责的Mock模块；
8. 替换某个Mock模块时，不需要重构其他模块；
9. 项目必须包含测试、配置、日志和开发文档；
10. 项目不能依赖一个大型Python文件运行。

## 5. 最终业务流程

用户上传招股书PDF并填写公司信息后，系统依次执行：

1. 文档解析；
2. 文档切片；
3. 文档索引；
4. 证据检索；
5. 财务Agent分析；
6. 法务Agent分析；
7. 业务Agent分析；
8. 市场Agent分析；
9. Verifier Agent核验证据；
10. Supervisor Agent处理冲突并汇总结论；
11. Predictor输出风险评分；
12. Report Builder生成结构化报告；
13. Streamlit展示风险、证据和执行日志。

## 6. 智能体角色

### 6.1 Financial Agent

负责：

1. 连续亏损识别；
2. 收入增长分析；
3. 毛利率变化分析；
4. 经营现金流分析；
5. 现金跑道计算；
6. 客户集中度分析；
7. 供应商集中度分析；
8. 财务异常识别。

### 6.2 Legal Agent

负责：

1. 对赌和赎回条款；
2. 股东特殊权利；
3. 关联交易；
4. 重大诉讼；
5. 行政处罚；
6. 牌照和监管风险；
7. 公司治理风险；
8. 条款是否仍然有效的判断。

### 6.3 Business Agent

负责：

1. 商业模式分析；
2. 核心产品商业化状态；
3. 单一产品依赖；
4. 客户依赖；
5. 供应商依赖；
6. 行业竞争；
7. 技术和研发风险；
8. 业务可持续性分析。

### 6.4 Market Agent

负责：

1. 恒生指数表现；
2. 行业指数表现；
3. 近期港股IPO破发率；
4. 近期IPO五日收益；
5. 市场成交活跃度；
6. 市场波动率；
7. IPO市场情绪评分。

### 6.5 Verifier Agent

负责：

1. 检查风险是否有原文证据；
2. 检查证据是否支持风险结论；
3. 检查数字是否由Skill计算；
4. 检查不同Agent是否存在冲突；
5. 检查风险等级是否被过度夸大；
6. 将无法核验的风险标记为待人工复核。

### 6.6 Supervisor Agent

负责：

1. 汇总各专业Agent结果；
2. 合并重复风险；
3. 处理Agent冲突；
4. 确定最终风险等级；
5. 生成结构化分析摘要；
6. 组织最终报告内容。

## 7. 风险类型范围

公共Schema和风险注册表支持以下风险类型：

1. 连续亏损；
2. 经营现金流为负；
3. 现金跑道不足；
4. 客户集中度过高；
5. 供应商集中度过高；
6. 对赌或赎回条款；
7. 股东特殊权利；
8. 重大关联交易；
9. 核心产品未商业化；
10. 单一产品依赖；
11. 监管审批风险；
12. IPO市场环境较弱。

真实实现范围按版本逐步扩展，不得为尚未实现的风险生成虚构结论。

## 8. 当前组件状态

真实或确定性实现：

1. PyMuPDF DocumentParser；
2. 已泛化到八类v0.3查询族的KeywordDocumentRetriever；
3. Mock、OpenAI-compatible与Unavailable LLMProvider基础设施；
4. 现金跑道链路，以及独立可调用的`V03FinancialAgent`、`V03FinancialVerifier`、财务事实抽取和Decimal Skills；
5. standalone Legal Agent、两类Legal风险链路及Legal domain Verifiers；
6. standalone `V03BusinessAgent`及`precommercial_product`确定性规则；
7. RuleVerifier、RuleSupervisor和RuleBasedPredictor；
8. `CatalogIPODataProvider`、批量运行和黄金评测基础设施；
9. LangGraph `mvp_v1`、IPOAnalysisService、JSON Repository和Streamlit。

实现与共享集成必须区分：Financial、Legal与Business三个v0.3 standalone核心已经合并，但尚未进入共享Container/Workflow/Service；共享Legal/Business仍使用disabled/Mock。Catalog Provider尚未进入全局ComponentRegistry；Market Agent和真实市场数据Provider仍未真实实现；`enhanced_v2`尚未完成，ReportGenerator仍为Mock格式化组件。所有Mock、真实和unavailable实现必须遵守相同公共接口和Schema。

## 9. 当前范围边界

暂时不实现：

1. 大语言模型微调；
2. 完整GraphRAG；
3. Neo4j知识图谱；
4. 微服务；
5. Kafka；
6. Redis任务队列；
7. Kubernetes；
8. 实时新闻系统；
9. 复杂深度学习预测模型；
10. React前端；
11. 覆盖所有港股行业；
12. 精确股价预测；
13. 高频实时行情系统；
14. 完整企业级权限系统。

## 10. 当前迭代方向

v0.3.0当前处于Gate A，按以下顺序推进：

1. 完成Financial与Business真实Golden独立二审；
2. 完成Legal A—H人工复核、Case C仲裁、canonical并表及contract/severity/Retriever/runtime prompt治理；
3. 达到`V03_GATE_A_CLOSEOUT.md`全部mandatory门槛后建立三专业Verifier体系；
4. 统一集成Financial/Legal/Business、Catalog Provider、Workflow和Service；
5. 建立`enhanced_v2`并运行真实黄金案例批量评测；
6. 保持Mock模式、`mvp_v1`和2410.HK现金跑道回归稳定。

真实市场数据、Market Agent、上市后标签、Logistic、LightGBM和SHAP延后至v0.4及后续版本。

## 11. 当前实施状态

稳定版本为`v0.2.0-real-document-slice`，已经实现真实PDF解析、Evidence检索、现金与经营
现金流提取、现金跑道Calculation、财务风险核验、规则评分、Service级E2E和Streamlit展示。

当前进入v0.3.0真实多Agent文档风险分析。详细范围、任务顺序和退出门槛以
`docs/PROJECT_MASTER_CHECKLIST.md`为准。

截至`main@f9449fc1330404bf5d711d437162bc04baea017b`，V3-3 Retriever、V3-4 LLMProvider及Financial、Legal、Business三个standalone核心均已合并。当前统一阶段仍是Gate A；三个专业模块尚未完成共享Container/Workflow/Service装配，Legal治理门槛、专业Verifier、`enhanced_v2`和v0.3 Release仍未完成。具体PASS/FAIL门槛见`docs/V03_GATE_A_CLOSEOUT.md`。

