# Roadmap

| 版本 | 目标 | 状态 |
| --- | --- | --- |
| v0.1.0 | 架构级 MVP | 已完成并发布 |
| v0.2.0 | 真实文档纵向闭环与赛事数据治理 | 已完成并发布 |
| v0.3.0 | Financial、Legal、Business 多 Agent 招股书风险分析产品 | 已完成并发布 |
| v0.3.5 | Expert Golden 重建与 Evidence Intelligence | 研究中（Phase 0.6B） |
| v0.4.0 | 市场数据、收益标签与预测模型 | NOT STARTED |
| v0.5.0 | 扩展人工标注与正式评测 | 计划中 |
| v1.0.0 | 正式参赛版本 | 计划中 |

## v0.3 已完成范围

| Workstream | 状态 | 说明 |
| --- | --- | --- |
| Golden governance | COMPLETE | Financial/Business具名一审正式晋级；Legal双审/仲裁保持；正式评测完成 |
| Catalog Provider | COMPLETE | 已注册；单文档配置可选 request/catalog |
| Shared Retriever | COMPLETE | 财务、法务、业务简繁英查询族 |
| LLMProvider | COMPLETE | Mock/OpenAI-compatible/Unavailable；外部 smoke 可选且尚未执行 |
| Financial Agent | COMPLETE / INTEGRATED | 五类风险、确定性抽取/计算、Verifier |
| Legal Agent | COMPLETE / INTEGRATED | 两类风险、Prompt routing、Verifier、Legal formal Golden |
| Business Agent | COMPLETE / INTEGRATED | `precommercial_product`、正负例语义、Verifier |
| Specialized Verifier | COMPLETE | 按 domain/risk_code 路由，失败隔离 |
| Supervisor / `enhanced_v2` | COMPLETE | 去重、冲突、跨域观察、规则分构成 |
| Batch/evaluation infrastructure | COMPLETE | 保留正式/开发 provenance 边界 |
| Streamlit / Report | COMPLETE | Service-only UI、十章报告、Markdown/JSON |
| Hardening | PASS | Mock、mvp_v1、v0.2 与真实 2410.HK 回归保留 |

## 当前边界

- `mvp_v1` 是兼容工作流；`enhanced_v2` 是 v0.3 共享多 Agent 工作流；
- Golden 人工治理按`single_named_human_review_v1`完成；不将一审表述为独立双审；
- 不把规则分描述为概率，不提供市场收益预测；
- 2025 blind 数据未参与开发调优；
- v0.4 Market Agent、市场标签、统计/机器学习模型尚未开始。

详细状态以 [PROJECT_MASTER_CHECKLIST.md](PROJECT_MASTER_CHECKLIST.md) 为准，
Golden/waiver 语义见 [V03_GATE_A_CLOSEOUT.md](V03_GATE_A_CLOSEOUT.md)。

## v0.3.5 研究路线

| Phase | 内容 | 状态 |
|---|---|---|
| 0.5 | Real LLM Baseline、2410 gate、14-case A/B | COMPLETED |
| 0.6A | Expert blind packet、schema、validator、importer | COMPLETED |
| 0.6B | Protocol v1.1 hardening 与团队协作目录 | CURRENT |
| 0.6C | 2410/2517/1167 三案例 Expert Pilot | NOT STARTED |
| 0.6D | Expert Golden v2 | NOT STARTED |
| 0.7 | Evidence Intelligence Architecture | NOT STARTED |
| 0.8 | v0.3 static/shared vs v0.3.5 domain-specific A/B | NOT STARTED |
| 0.9 | Retriever / ranking algorithm optimization | NOT STARTED |

直接 Retriever 调优在 Expert Golden v2 与架构 A/B 之前暂停。Hybrid、Embedding、
Reranker 与 table-aware 算法选择延后到 Phase 0.9。v0.4 必须经过 v0.3.5 Gate。
