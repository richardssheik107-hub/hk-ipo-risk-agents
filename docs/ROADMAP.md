# Roadmap

> 当前执行策略：**End-to-End Closed Loop First**。先完成 PDF → Multi-Agent → Document Features → Market Model → Final Report 的完整闭环，再进入 Retriever / LLM / Agent 的研究级优化。
>
> 后续总计划见：[END_TO_END_CLOSED_LOOP_MASTER_PLAN.md](END_TO_END_CLOSED_LOOP_MASTER_PLAN.md)。

| 版本 | 目标 | 状态 |
| --- | --- | --- |
| v0.1.0 | 架构级 MVP | 已完成并发布 |
| v0.2.0 | 真实文档纵向闭环与赛事数据治理 | 已完成并发布 |
| v0.3.0 | Financial、Legal、Business 多 Agent 招股书风险分析产品 | 已完成并发布 |
| v0.4-MVP | 完整端到端闭环：Document Risk → Market Outcome | NEXT |
| v0.4.1 | LightGBM + Explainability | 计划中 |
| v0.4.2 | Market Agent + Final Supervisor | 计划中 |
| v0.4.3 | Streamlit Full E2E Demo | 计划中 |
| v0.5.0 | Retriever / LLM / Agent / Verifier 研究级优化 | 闭环完成后启动 |
| v0.6.0 | 正式评测、消融、失败分析与 Blind Test | 计划中 |
| v1.0.0 | 正式参赛 / 作品集版本 | 计划中 |

## v0.3 已完成范围

| Workstream | 状态 | 说明 |
| --- | --- | --- |
| Golden governance | COMPLETE | Financial/Business具名一审正式晋级；Legal双审/仲裁保持；正式评测完成 |
| Catalog Provider | COMPLETE | 已注册；单文档配置可选 request/catalog |
| Shared Retriever | COMPLETE | 财务、法务、业务简繁英查询族 |
| LLMProvider | COMPLETE | Mock/OpenAI-compatible/Unavailable；真实 provider 可配置接入 |
| Financial Agent | COMPLETE / INTEGRATED | 五类风险、确定性抽取/计算、Verifier |
| Legal Agent | COMPLETE / INTEGRATED | 两类风险、Prompt routing、Verifier、Legal formal Golden |
| Business Agent | COMPLETE / INTEGRATED | `precommercial_product`、正负例语义、Verifier |
| Specialized Verifier | COMPLETE | 按 domain/risk_code 路由，失败隔离 |
| Supervisor / `enhanced_v2` | COMPLETE | 去重、冲突、跨域观察、规则分构成 |
| Batch/evaluation infrastructure | COMPLETE | 保留正式/开发 provenance 边界 |
| Streamlit / Report | COMPLETE | Service-only UI、Markdown/JSON 报告 |
| Hardening | PASS | Mock、mvp_v1、v0.2 与真实 2410.HK 回归保留 |

## 当前边界

- `mvp_v1` 是兼容工作流；`enhanced_v2` 是 v0.3 共享多 Agent 工作流；
- Golden 人工治理继续保持现有审计口径；
- 不把规则分描述为真实下跌概率；
- 2025 blind 数据不得用于开发调优；
- v0.4 已有 Market Foundation、Document Risk Feature Contract、Pre-IPO Market Feature Contract 与 Data Readiness 基础；
- 当前第一优先级不是继续提高 Retriever 指标，而是完成 model-ready dataset 与第一版市场预测闭环。

详细历史状态仍以 [PROJECT_MASTER_CHECKLIST.md](PROJECT_MASTER_CHECKLIST.md) 为权威进度入口；后续执行路线以 [END_TO_END_CLOSED_LOOP_MASTER_PLAN.md](END_TO_END_CLOSED_LOOP_MASTER_PLAN.md) 为主。

## v0.4 Closed Loop 路线

| Phase | 内容 | 状态 |
| --- | --- | --- |
| CL-1 | Freeze current Document Intelligence | NEXT |
| CL-2 | Build IPO-level Document Risk Features | NEXT |
| CL-3 | Close minimum Market Data | NOT STARTED |
| CL-4 | Freeze 5D Outcome / Target Policy | NOT STARTED |
| CL-5 | Build Model-ready Dataset | NOT STARTED |
| CL-6 | Logistic / Linear Baseline | NOT STARTED |
| CL-7 | LightGBM + Explainability | NOT STARTED |
| CL-8 | Market Agent MVP | NOT STARTED |
| CL-9 | Final Supervisor | NOT STARTED |
| CL-10 | Streamlit Full E2E + 3–5 Real IPO Demo | NOT STARTED |

v0.4-MVP 的成功标准首先是：完整闭环可运行、可重建、无未来信息泄漏、可解释，而不是单一模型指标达到某个任意高值。

## v0.5 Research Optimization

只有 v0.4 完整闭环冻结后，重新打开：

- Retriever V3 / hybrid / BM25 / table-aware / dense；
- Learning-to-Rank；
- LLM Reranker；
- Financial / Legal / Business Agent VNext；
- Semantic Verifier；
- Supervisor 深化；
- Fine-tuning 可行性评估。

原则是先知道完整系统的真实瓶颈，再对瓶颈进行研究级优化。

## v0.6 Formal Evaluation

正式评测阶段至少包含：

- Market-only vs Document-only vs Combined；
- Baseline vs improved retrieval vs LLM vs Agent VNext vs full system；
- Risk / Evidence / Grounding / Market prediction 多层指标；
- 失败案例分析；
- 2024 validation；
- 模型冻结后一次性 2025 blind evaluation。
