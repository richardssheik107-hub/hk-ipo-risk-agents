# HK IPO Risk Agents

基于证据驱动多智能体协同的港股IPO招股书解析与上市后风险预警系统。

## 项目状态

当前阶段：

```text
v0.1.0：架构级MVP已完成
```

稳定版本：[v0.1.0-architecture-mvp](https://github.com/richardssheik107-hub/hk-ipo-risk-agents/releases/tag/v0.1.0-architecture-mvp)。

已完成配置驱动装配、LangGraph mvp_v1 工作流、规则核验与预测、故障降级、Streamlit 原型和自动化验收（24 passed）。第一阶段不追求完成全部真实金融分析能力。

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

## 第一阶段已完成

第一阶段将完成：

1. 完整工程目录；
2. 公共Schema；
3. Parser、Retriever、Agent和Predictor接口；
4. Mock Parser；
5. Mock Retriever；
6. Mock专业Agent；
7. Verifier和Supervisor；
8. RuleBasedPredictor；
9. LangGraph工作流；
10. IPOAnalysisService；
11. Streamlit页面；
12. 单元测试、契约测试和端到端测试；
13. 一键启动脚本。

## 当前实现范围

已真实实现：

- ComponentRegistry 与 DependencyContainer 配置装配；
- RuleVerifier、RuleSupervisor、RuleBasedPredictor 与确定性金融 Skill；
- JSON Repository、LangGraph 工作流、故障降级与 Streamlit 展示；
- Schema、契约、工作流、集成、端到端与黄金案例测试。

当前仍为 Mock：

- DocumentParser、DocumentRetriever；
- Financial、Legal、Business、Market Agent；
- LLMProvider、MarketDataProvider、IPODataProvider；
- ReportGenerator。

## v0.2.0 目标

只实现一条可验证的真实纵向闭环：

```text
真实港股招股书 PDF
→ PDF 解析
→ Evidence 检索
→ 现金与经营现金流提取
→ 现金跑道计算
→ 财务风险核验
→ 前端展示
```

## 项目文档

请先阅读：

1. docs/PROJECT_SPEC.md
2. docs/ARCHITECTURE.md
3. docs/DATA_SCHEMA.md
4. AGENTS.md

## 开发规范

任何开发任务开始前，应先阅读AGENTS.md。

公共Schema、基础Agent接口、工作流State和AnalysisService属于受保护的公共接口，修改时必须说明影响。

## 后续开发方向

1. 真实PDF解析；
2. 招股书证据检索；
3. 财务风险分析；
4. 法务条款分析；
5. 业务经营分析；
6. 港股IPO市场数据；
7. 人工标注和评测；
8. Logistic和LightGBM模型；
9. SHAP解释；
10. 证据截图和自动报告。

## 团队分工方向

* 文档解析与证据定位；
* 财务与经营风险；
* 法务合规与评测；
* 市场数据与预测模型；
* 工作流、前端与系统集成。

## MVP运行

第一阶段默认使用离线 Mock 组件；不需要真实招股书、市场数据或 LLM API。

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

默认配置为 configs/mock.yaml。配置优先级为：环境变量（任意 IPO_RISK_字段名）> YAML（IPO_RISK_CONFIG 可指定文件）> 代码默认值。Mock 与未来真实实现均通过同一注册表和公共接口切换；当前注册名称：mock（Parser、Retriever、专业 Agent、Provider、ReportGenerator）、mock_alt（Parser 验证实现）、rule（Verifier、Supervisor）、rule_based（Predictor）、json（Repository）。

Windows 可运行 `start.bat`，Unix 可运行 `start.sh`。配置默认读取 `configs/mock.yaml`，环境变量优先于 YAML 配置。

