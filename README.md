# HK IPO Risk Agents

基于证据驱动多智能体协同的港股IPO招股书解析与上市后风险预警系统。

## 项目状态

当前阶段：

```text
第一阶段：架构级MVP设计
```

当前目标是建立完整、清晰、可扩展的模块化项目架构，并使用Mock模块跑通端到端流程。

第一阶段不追求完成全部真实金融分析能力。

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

## 第一阶段计划

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

