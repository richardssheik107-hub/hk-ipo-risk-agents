# Codex 与团队开发规则

## 1. 当前项目目标

本项目构建一个**证据驱动、多智能体协同、可审计**的港股 IPO 招股书解析与上市后风险预警系统。

当前稳定基线是 `v0.3.0-multi-agent-risk-analysis`；当前开发主线是 **v0.4 End-to-End Closed Loop**：

```text
Document Intelligence
→ IPO-level Document Features
→ Pre-IPO Market Features
→ Outcome
→ Model-ready Dataset
→ Baseline / LightGBM
→ Market Agent
→ Final Supervisor
→ Full E2E Demo
```

Retriever V3 等研究成果已冻结并归档，当前不作为 v0.4 前置条件。历史 Retriever Locked 10 已消费，不得继续用其调参后重新描述为 blind。

## 2. 开始任务前

执行代码任务前必须先：

1. 阅读 `docs/README.md`；
2. 阅读 `docs/PROJECT_SPEC.md`；
3. 阅读 `docs/ARCHITECTURE.md`；
4. 阅读 `docs/DATA_SCHEMA.md`；
5. 阅读本 `AGENTS.md`；
6. 涉及路线 / 数据 / 建模时，再读 `docs/END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`、`docs/ROADMAP.md` 和对应 `docs/research/V04_*.md`；
7. 若任务涉及已冻结 PR-B 的审计，再读 `docs/V04_PR_B_COMPLETION_REPORT.md`、`docs/research/V04_PR_B_INTEGRATION_ACCEPTANCE.md`；Role A preparation / handoff 仅作为历史完成记录；
8. 检查仓库结构与现有测试；
9. 说明准备修改的文件及是否影响公共接口。

面对较大任务，先给出实施计划，再开始编码。

## 3. 架构规则

1. 保持模块化单体架构；
2. 当前阶段不引入与闭环无关的微服务、Kafka、Redis 队列、Neo4j、Kubernetes；
3. 业务逻辑不得集中在 `streamlit_app.py`；
4. Streamlit 只能通过 `IPOAnalysisService` 访问业务能力；
5. Agent 不直接操作前端或 Repository；
6. Parser 不依赖 Agent；
7. Skill 不依赖 Agent；
8. Schema 不依赖具体业务实现；
9. Mock 与真实实现必须可配置替换。

## 4. 受保护公共接口

以下路径属于公共接口 / 核心架构边界，修改前必须明确说明影响并补充测试：

```text
src/ipo_risk/schemas/
src/ipo_risk/agents/base.py
src/ipo_risk/parsers/base.py
src/ipo_risk/retrieval/base.py
src/ipo_risk/predictors/base.py
src/ipo_risk/providers/
src/ipo_risk/workflows/state.py
src/ipo_risk/services/analysis_service.py
src/ipo_risk/core/container.py
src/ipo_risk/domain/risk_codes.py
```

未经明确任务要求，不得随意重命名 / 删除公共字段、改变字段含义、改变统一返回类型或破坏兼容工作流。

## 5. Schema / Agent / Skill 规则

- 跨模块公共数据使用 Pydantic 模型；
- Parser 返回 `list[DocumentChunk]`；
- Retriever 返回稳定 Evidence / DocumentChunk 契约；
- 专业 Agent 返回 `list[RiskItem]`；
- Predictor 返回 `PredictionResult`；
- AnalysisService 返回 `IPOAnalysisResult`；
- Skill 返回明确的 Pydantic / versioned 结果；
- 精确金融计算必须由 deterministic Skill 完成，不能交给 LLM；
- Agent 不得自行创建公共 Schema；
- 新 Agent / Skill / Provider 必须增加契约或单元测试。

## 6. Evidence 与 Verification 规则

1. 所有正式风险必须有 Evidence；
2. Evidence 必须保留真实页码和原文；
3. 含具体数字的结论必须有 Calculation；
4. Calculation 必须记录 inputs、formula、result、unit、evidence IDs；
5. 无法核验的风险进入 `pending` / `needs_review`；
6. 不得虚构页码、原文、市场数据或模型输入；
7. LLM 不得绕过 Specialized Verifier / Supervisor 直接制造 `verified` 结论。

## 7. v0.4 数据与建模规则

当前 v0.4 必须严格遵守 point-in-time 与 no-leakage：

```text
2020–2023  Development / Training
2024       Validation
2025       Blind Test
```

- 所有 X 特征必须在上市前可获得；
- 2025 不得用于选特征、阈值、规则或超参数；
- classification threshold 只能由 Development 数据决定；
- 数据缺失必须显式记录，不得猜测或静默填补；
- provenance、source version、feature version、model version 必须可追踪；
- Market-only / Document-only / Combined 必须使用相同切分公平比较；
- 未经校准的 score 不得表述为真实概率。

Retriever 历史 Locked 10 只保留为历史评测，未来优化 Retriever 必须建立新的 unseen holdout。

## 8. 前端规则

Streamlit 只能：

1. 构造请求；
2. 调用 `IPOAnalysisService` / 受控上层 service；
3. 展示结构化结果；
4. 展示错误和 provenance。

Streamlit 不得直接调用 LLM、Agent、Parser、Repository 或执行金融计算。

## 9. 配置与敏感信息

- API Key / Token / 密码只从环境变量读取；
- 不提交 `.env`；
- 不提交本地绝对路径；
- 模型名和 Provider 通过配置管理；
- Mock / real / unavailable 实现通过注册与配置切换；
- 日志不得泄漏凭证或敏感内容。

## 10. 代码质量

- 使用类型标注；
- 公共函数有简短 docstring；
- 避免循环依赖；
- 文件 / 模型 / 网络调用必须有明确异常处理；
- 不得通过宽泛异常静默吞错；
- 避免导入阶段执行耗时逻辑；
- 保持函数和模块职责单一。

## 11. 测试要求

提交前运行相关测试；能运行完整 CI 时优先运行完整测试。

完整测试环境：

```bash
pip install -e '.[dev,retrieval-research]'
pytest -q
```

不得：

- 删除有效测试；
- 弱化断言以掩盖问题；
- 修改期望结果迁就错误实现；
- 未运行测试却声称测试通过。

新功能不得破坏 Mock E2E、v0.2 现金跑道回归、v0.3 Multi-Agent 回归及当前数据治理检查。

## 12. 标准任务流程

1. 阅读当前活文档；
2. 检查实现与测试；
3. 列出修改范围 / 公共接口影响；
4. 实现最小必要修改；
5. 增加或更新测试；
6. 运行测试并修复失败；
7. 汇报变更、测试、限制和下一步。

## 13. Git 规则

1. 不直接向 `main` 提交未经测试的代码；
2. 每个功能使用独立分支；当前若用户明确要求“不要新增分支”，继续使用已指定的现有工作分支；
3. Commit 信息说明真实修改内容；
4. PR 说明测试结果与剩余限制；
5. 公共 Schema 修改必须明确审核；
6. 不提交大型原始 PDF、模型缓存、临时文件或敏感数据；
7. 只有用户明确要求时才执行 push / PR / merge 等写操作。

## 14. 组件替换规则

- 新真实实现先通过现有公共接口契约测试；
- 不删除仍承担降级 / 测试职责的 Mock；
- Service 不硬编码真实实现；
- 新组件注册到 ComponentRegistry；
- 真实模块失败时返回结构化错误；
- 替换某个模块不能要求无关模块一起重构。

## 15. 当前优先级

CL-1、PR-A、PR-B、PR-C 与 PR-D 均已完成并冻结。下一正式里程碑是：

> **PR-F — LightGBM + Explainability / READY / FORMAL RUN NEXT**

PR-C 已完成 governed 438-case coverage、Development-only q25 threshold、resume、determinism 与 Blind Gate，并冻结在 `docs/V04_PR_C_COMPLETION_REPORT.md` 和 `reports/frozen/v04_pr_c_5d_outcome_manifest.json`。不要重新执行或重新设计 PR-C，也不要在没有独立任务授权时启动 PR-D。

### 15.1 PR-B Market-X Core — COMPLETE / FROZEN

当前 Core 契约：

```text
schema:  v04_ipo_market_context_features_v1
policy:  ipo_market_context_policy_v1
15 raw prior-IPO context features
+ 15 adjacent missing indicators
= 30 positions
```

当前实现入口：

```text
src/ipo_risk/market/ipo_market_context_features.py
scripts/build_v04_ipo_eod_store.py
scripts/run_v04_pr_b.py
```

Core 使用当前已治理的 authoritative IPO metadata、prior-IPO offer/context facts、governed IPO EOD，以及在目标 IPO 上市前已经成为历史事实的 prior-IPO 1D/5D outcomes。

硬规则：

- EOD official cohort 按 `official_listed_date.year`，不得按 document `source_year`；
- target IPO 自身上市日 / 上市后数据不得进入 target X；
- prior outcome 的 target trading date 必须严格早于 target listing date；
- 2025 blind y 不得访问；
- `S_DQ_AMOUNT` 仅是单证券成交额，不是全市场 turnover；
- resume 不得静默覆盖不同 provenance；
- every official case 必须在 coverage 中有显式状态。

### 15.2 Market-X Extended

已有的 Extended 契约继续冻结，不被 PR-B Core 重写：

```text
v04_prelisting_market_features_v1
v04_market_features_v1
10 raw features + 10 missing indicators
= 20 positions
```

当前真实 Extended 数据缺口仍包括：

```text
HSI history
Authoritative industry benchmark mapping
Industry-index history
HKEX total-market turnover
```

这些缺口必须显式保留，但**不是 PR-B Core 必须伪造或用 proxy 补齐的输入**。禁止使用 Hang Seng Bank 代替 HSI、用公司/行业文本猜 benchmark、用 `S_DQ_AMOUNT` 代替 total-market turnover、或用 0 静默填补。

### 15.3 当前 Codex / 本地执行边界

当前状态：

```text
PR-A  COMPLETE / FROZEN
PR-B  COMPLETE / FROZEN
PR-C  COMPLETE / FROZEN
PR-D  COMPLETE / FROZEN
PR-E  COMPLETE / FROZEN
PR-F  READY / FORMAL RUN NEXT
```

PR-B 的 targeted tests、full pytest、5-case pilot、438-case materialization 与 deterministic resume 均已完成。冻结证据：

```text
docs/V04_PR_B_COMPLETION_REPORT.md
reports/frozen/v04_pr_b_market_x_core_manifest.json
```

当前不得重新选择 5D threshold、读取 2025 y、训练模型或启动 PR-E。PR-D 必须由独立任务消费冻结的 PR-C contract，完成 canonical model-ready dataset 的正式 materialization 与验收。

后续正式 Gate / merge 顺序仍为：

```text
PR-C → PR-D → PR-E → PR-F → PR-G → PR-H
```
