# HK IPO Risk Agents

面向港股 IPO 招股书风险识别、市场环境解释与可审计多 Agent 决策的比赛型原型系统。

> 当前 package checkpoint：`v0.4.0`
>
> 当前比赛 runtime：`v0.4.5`
>
> 当前状态：**Competition closure in progress — 尚未标记 `COMPETITION_READY`**

## 当前能力

主链已经从单纯离线规则系统推进为：

```text
Prospectus PDF
→ Parser / Retriever / Evidence
→ Financial deterministic analysis
→ Legal / Business structured LLM analysis
→ Verifier / Document Supervisor
→ governed Market-X
→ IPOHeatSkill / MarketRegimeSkill
→ bounded Market LLM interpretation
→ Rule / optional frozen Model signal
→ Conflict detection
→ one bounded targeted re-check
→ LLM Final Supervisor with deterministic fallback
→ Agent / Tool / Evidence Trace
→ Human Review
→ Streamlit / report / submission artifacts
→ A-owned readiness / Blind / provenance / determinism / package gate
```

核心治理原则不变：

- LLM 负责语义理解与综合，不负责权威数值计算；
- 精确计算由 Python `Calculation` 完成；
- 正式 `RiskItem` 必须有真实 `Evidence`；
- LLM 只能引用输入作用域内的 Evidence / Risk / Conflict；
- 市场事实必须来自 PIT-governed Market-X，缺失不得补零或造代理值；
- 未校准模型分数只能称 `uncalibrated_model_score`，不能称概率；
- 2025 Blind outcome 在正式授权前保持未访问；
- frozen PR-A–PR-G 结果不因比赛展示需要而重写。

## 最新实测状态

### 1. 三个真实招股书案例已完成 offline E2E

冻结 catalog 驱动的真实 PDF runner 已验证并执行：

| Case | Stock | Pages | Status | Conflicts | Re-checks | Traceability |
|---|---|---:|---|---:|---:|---:|
| `ipo_2024_02410` | `2410.HK` | 706 | completed | 6 | 3 | 1.0 |
| `ipo_2024_02460` | `2460.HK` | 579 | completed | 7 | 3 | 1.0 |
| `ipo_2024_01318` | `1318.HK` | 617 | completed | 7 | 3 | 1.0 |

三份 PDF 均通过 SHA-256、字节数和物理页数校验；结构化 workflow error 为 0；运行没有读取任何 outcome label，也没有访问 2025 Blind y。

这关闭了“至少 3 个真实 PDF 案例能否跑通”的工程 Gate，但**不等于最终比赛质量 Gate 已关闭**。

### 2. Role B 文档智能当前是主要质量 blocker

10 个 2020–2023 Development 真实 PDF 的 governed offline benchmark 已完成：

```text
Risk Precision / Recall / F1      0% / 0% / 0%
Evidence Recall@1 / @3 / @5       20% / 20% / 20%
Physical-page correctness         100%
Real LLM cases                    0
```

因此比赛要求的风险抽取与 Evidence 指标目前**没有被证明达标**。这个结果是离线基线，不是 real-LLM benchmark；B 下一步必须先用真实 provider 在固定 Development benchmark 上测量，再按错误归因做最小修复。

2460.HK 和 1318.HK 的离线三案例运行进一步说明了问题位置：多个 risk code 已检索到 Evidence，但没有形成正式风险项，缺口主要落在 `Evidence → structured extraction → RiskItem / Verifier`。

### 3. Market Intelligence 主体已实现

已实现并接入正式 AI runtime：

- governed `MarketContext`；
- `IPOHeatSkill`；
- `MarketRegimeSkill`；
- bounded structured Market LLM interpretation；
- 显式 missingness / PIT provenance；
- Market Trace 与 Final Supervisor handoff。

真实 Volcengine/OpenAI-compatible provider 已在两只真实 IPO 上验证 Market LLM 路径。`ComparableIPOSkill` 与 PIT-safe industry return 不是当前提交 blocker；没有可靠数据时保持 unavailable。

最终只剩同一 3-case submission matrix 上的 Market state / trace accounting 验收。

### 4. LLM Final Supervisor / Multi-Agent / Product 已实现

已实现：

- deterministic conflict detection；
- 每个冲突最多一次 targeted re-check，并有总预算；
- Verifier challenge；
- LLM Final Supervisor；
- deterministic fail-closed fallback；
- Agent / Tool / Evidence trace；
- Evidence Viewer；
- Human Review sidecar；
- 五个 Streamlit 比赛工作区；
- per-case `agent_reasoning_log.json/.md`；
- `case_report.md`；
- machine-checked `gate_e1_evidence.json`。

三案例 offline matrix 的 measured traceability 均为 1.0。Gate E1 现在只在真实远端 provider 成功输出、scope check 通过且 call trace 完整时才接受；offline/mock/fallback 均不会被误记为成功仲裁。

当前 measured offline matrix 仍是 **0/3 successful LLM arbitration**，因此最终还需要在同一案例矩阵上完成 real-provider Final Supervisor 验收。

### 5. Outcome / Model 最终比赛包仍未闭合

仓库已有 1D / 5D / 20D / 60D outcome foundation；正式 frozen PR-C 仍是 5D 研究结果。比赛提交还需要 D 产出可复现的最小多周期结果包：

```text
return_1d
return_5d
return_20d
return_60d

test_predictions.csv
multi_horizon_results.csv
evaluation_summary.json
ai_vs_offline_report.json
```

原始 frozen PR-F per-case runtime / sanitized handoff 若仍不可恢复，Model Channel 必须继续明确 `unavailable`；禁止为了前端完整而重训、重构或反转分数。

### 6. A 的最终提交工具已实现，真实 freeze 仍等待 B/C/D/E handoff

A 已实现：

```text
submission_readiness.json
blind_audit.json
provenance_audit.json
determinism_audit.json
artifact_index.json
SUBMISSION_RUNBOOK.md
COMPETITION_READY-only submission packager
```

Readiness 是 fail closed：missing handoff 不会被推断成 PASS；packager 只有在全部 measured Gate 真正通过时才允许生成 ZIP，并拒绝 PDF、secret-bearing file、token/private key 与本地绝对路径。

## 当前比赛 Gate

| Gate | Status |
|---|---|
| 公共 competition runtime contracts | PASS |
| Main CI / integration gate | PASS baseline |
| Legal / Business LLM runtime path | IMPLEMENTED，需 final real-LLM benchmark |
| Market Intelligence implementation + AI wiring | PASS |
| 3 个真实 PDF offline E2E | PASS |
| Conflict / bounded re-check / Trace / Human Review | PASS implementation |
| 3-case measured traceability | PASS = 1.0 |
| E reasoning log / case report / machine Gate-E1 | PASS implementation |
| A readiness / audit / Runbook / packager tooling | PASS implementation |
| B Risk / Evidence benchmark | **FAIL / OPEN** |
| C final-matrix Market validation | **OPEN** |
| D 1D/5D/20D/60D submission artifacts | **OPEN** |
| Real-provider Final Supervisor on final matrix | **OPEN** |
| Evidence bbox upstream grounding | OPEN quality gap；page grounding 已可用 |
| Authentic frozen PR-F per-case handoff | OPTIONAL for competition UI / still missing for historical PR-H closure |
| Final real audits / bundle / release freeze | **OPEN** |

详细且唯一的当前 Gate 状态见 `docs/V0.4_RELEASE_ACCEPTANCE.md`。

## 五人职责

- **A — Tech Lead / Integration / Release / Submission**：公共契约、集成 Gate、PR/CI、readiness/audit/Runbook/package 与最终 release freeze。
- **B — LLM Document Intelligence**：Legal / Business 语义抽取、Risk/Evidence benchmark、Evidence grounding。
- **C — Market Intelligence**：PIT MarketContext、Skills、Market LLM interpretation。
- **D — Outcome / Model / Evaluation**：1D/5D/20D/60D、最终结果文件、authentic PR-F signal if available。
- **E — LLM Final Supervisor / Multi-Agent / Product**：冲突、复核、Supervisor、Trace、Human Review、Streamlit、submission case artifacts。

具体交接与文件边界见 `docs/V04_FIVE_PERSON_EXECUTION_PLAN.md`。

## 文档入口

- 当前 Gate：`docs/V0.4_RELEASE_ACCEPTANCE.md`
- 最终提交 Runbook：`docs/SUBMISSION_RUNBOOK.md`
- 剩余路线：`docs/ROADMAP.md`
- 五人执行：`docs/V04_FIVE_PERSON_EXECUTION_PLAN.md`
- 赛题映射：`docs/COMPETITION_HARDENING_AND_SUBMISSION_PLAN.md`
- 架构：`docs/ARCHITECTURE.md`
- Schema：`docs/DATA_SCHEMA.md`
- 数据：`docs/COMPETITION_DATA_OVERVIEW.md`
- B 当前实测：`docs/V045_ROLE_B_REAL_BENCHMARK_REPORT.md`
- E 当前实测：`docs/V04_ROLE_E_COMPLETION_REPORT.md`

冻结 completion reports、`reports/frozen/*` 和 research 文档属于历史/研究证据，不作为“当前 Gate”来源。

## 快速运行

安装：

```bash
pip install -e ".[dev,retrieval-research]"
```

离线比赛 runtime：

```bash
IPO_RISK_CONFIG=configs/v045_competition_offline.yaml streamlit run app/streamlit_app.py
```

AI 比赛 runtime 需要本地提供 provider secrets；不要把密钥写入 Git：

```bash
IPO_RISK_CONFIG=configs/v045_competition_ai.yaml streamlit run app/streamlit_app.py
```

A-owned network-free integration gate：

```bash
python scripts/validate_competition_runtime.py
```

A-owned final submission readiness：

```bash
python scripts/build_v045_submission_readiness.py \
  --role-b-dir reports/v045_role_b \
  --role-d-dir reports/v045_role_d \
  --role-e-dir reports/v045_role_e_ai_final \
  --output-dir reports/v045_submission \
  --require-ready
```

最终 `COMPETITION_READY` 只能在 `docs/V0.4_RELEASE_ACCEPTANCE.md` 的开放 Gate 被实测关闭之后使用。
