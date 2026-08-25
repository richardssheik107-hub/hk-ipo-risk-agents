# v0.4.5 Role E 完成报告 —— LLM Final Supervisor / Conflict / Trace / Product

> Date: **2026-08-25**
> Owner: **E —— LLM Final Supervisor / Multi-Agent / Trace / Product**
> Baseline: `origin/main` @ `9e0793e`
> 2025 Blind y accessed: **NO** · upstream PR-A–PR-F rerun: **NO** · frozen manifest changed: **NO**

## 1. Verdict

```text
LLM Final Supervisor              IMPLEMENTED
Conflict detection                IMPLEMENTED
Targeted re-check (bounded)       IMPLEMENTED
Agent / Tool / Evidence trace     IMPLEMENTED, measured 1.0 on the real case
Evidence Viewer (page + bbox)     IMPLEMENTED
Human Review                      IMPLEMENTED
Final Streamlit workspaces        IMPLEMENTED (5 workspaces)
3–5 stable real demo cases        BLOCKED —— 本机只有 1 份受治理招股书 PDF
```

E lane 的代码路径全部完成并有回归测试；唯一未达标项是 demo case 数量，其原因是本地缺少另外两份 licensed PDF，**不通过 mock / 复制 / 伪造案例来凑数**。

## 2. 交付链路

```text
composed governed channels
→ deterministic conflict detection      v04_e_conflict_policy_v1
→ one bounded targeted re-check         v04_e_recheck_policy_v1
→ LLM Final Supervisor synthesis        v04_final_supervision_v1
→ Agent / Tool / Evidence trace sidecar v04_e_agent_trace_v1
→ Evidence Viewer / Human Review / Report
```

### 2.1 LLM Final Supervisor

`V04FinalSupervisor` 的 PR-G 纯组合层**逐字保留**为主干，LLM 只在其之上做一次受约束综合，输出
`overall_risk / overall_risk_rationale / key_findings / conflict_assessments / uncertainties /
recheck_required / recheck_targets / final_explanation`，写入 `FinalSupervisionResult.metadata`，
**不改动任何 public Pydantic schema**。

四条不变量（各有测试）：

1. 引用的 `risk_id` / `evidence_id` / `conflict_id` 必须来自输入；越界即整份判断作废；
2. `overall_risk` 不得低于由已验证文档风险推出的 `deterministic_severity_floor`——可以升级，不能把已验证风险讲低；
3. 叙述中不得出现输入 payload 里没有的数字，也不得出现 `probability / likelihood / forecast / 概率` 等预测词汇；
4. provider 缺失、失败或越界时，返回**与 PR-G 完全相同**的确定性组合，并写明原因。

### 2.2 Conflict / Re-check

冲突是**两个具名产出方之间的分歧**，不是单个 Agent 的自我不确定。检出规则（确定性、可复现 id）：

```text
agent_verifier_disagreement        Agent 断言了 Verifier 未予验证的风险
unresolved_agent_claim             Agent 持有 bounded Evidence，但文档通道对该 risk_code 一无所述
document_internal_conflict         Document Supervisor 冲突原样上抬为跨 lane 契约
document_rule_severity_divergence  已验证 high/critical vs 规则 low
document_market_divergence         受治理市场侧风险与文档侧方向相反
document_model_divergence          冻结模型最强 signed SHAP driver 与文档侧方向相反
```

定向复核每个冲突**最多一次**（`RecheckRequest.max_attempts` 由 schema 钉死为 1），且整轮有受控预算（默认 3）；超预算的冲突显式记为 `not attempted`，不静默丢弃。

复核结论区分三态：

```text
resolved             重新检索 + Verifier challenge 后全部被裁定
partially_resolved   出现新的 in-scope Evidence，或只有部分被裁定
unresolved           无新 Evidence 且判定未变，或该冲突跨越文档以外通道
```

对 `unresolved_agent_claim`，复核额外区分 **retrieval gap**（存在 Agent 未用到的 in-scope Evidence）与
**extraction gap**（检索无新增，缺口在抽取）——这是投研人员真正需要的诊断，而不是一句 unresolved。

### 2.3 Agent Trace

每个事件记录 `agent_name / action / tool_or_skill / provider / model / prompt_version /
evidence_ids / calculation_ids / conflict_id / recheck_id / latency / status`。没有 Evidence 的步骤
**必须写明 `no_evidence_reason`**，否则计入不可追溯。可追溯率是**度量出来的**：

```text
agent_traceability      有具名 actor 的事件占比
tool_traceability       有具名 tool/skill 的事件占比
evidence_traceability   有 Evidence/Calculation 或明确原因的事件占比
evidence 引用解析率      被引用 Evidence 中能回溯到本次运行的占比
overall_traceability    以上四项取最小值
```

`test_an_unaccounted_step_lowers_the_measured_traceability` 证明该指标会因真实缺口下降，不是硬编码 100%。

### 2.4 Product

Streamlit 收敛为 5 个工作区：**风险指挥中心 / Evidence 与 AI 分析 / 市场与模型 / Agent 协作轨迹 / 人机复核与最终报告**。

- Evidence Viewer：左侧用 PyMuPDF 渲染招股书原页并绘制 bbox 高亮，右侧是风险结论、结构化事实、
  确定性 Calculation 与 Verifier 判定。页码 / bbox 一律来自解析器；缺页或缺 bbox 明确说明，UI 不修补。
- Human Review：Accept / Reject / Needs Follow-up + 复核人 + 备注，写入独立 reviewer sidecar
  (`data/human_review/<analysis_id>.json`)，**不修改任何 RiskItem、Evidence 或分析结果文件**；
  界面并排展示机器结论与人工结论。
- UI 仍只经由 service 边界访问后端（新增 `HumanReviewService`），`test_ui_import_boundary_and_gitignore` 保持通过。

## 3. 真实案例证据

`configs/v045_competition_offline.yaml` + `data/local/real_case_001/prospectus.pdf`：

```text
case_id                         ipo_2024_02410 / 2410.HK / 2024-08-20
deterministic request id        8b7ac065-d42c-5d64-a180-2bfe10f41900
analysis status                 completed
report sections                 13
verified risks                  1 (cash_runway, critical, verified, 2 evidence)
conflicts detected              6  (partially_resolved 2 / unresolved 4)
targeted re-checks executed     3  (预算 3；其余 3 个显式记为未执行)
new evidence surfaced           5  (continuous_loss 4 / customer_concentration 1)
trace events                    22
overall traceability            1.0   (83/83 Evidence 引用全部可解析)
final supervision content hash  4722d2ce3613711d9f6b7e912d525c5352c381d74b2e9277802f1966461aa79e
determinism                     两次独立运行 content hash 一致
probability claimed             false
creates new risk                false
2025 Blind y accessed           false
```

这是一条**真实发生的受控协作轨迹**：Legal 的 `redemption_rights` / `material_litigation_compliance`
与 Business 的 `precommercial_product` 都持有 bounded Evidence 却未能形成风险项，被检出为覆盖冲突；
Financial 的 `continuous_loss` / `customer_concentration` 经定向复核确认为 retrieval gap 并产出新 Evidence，
`precommercial_product` 被确认为 extraction gap。

## 4. 未达标项与 blocker

```text
1. >=3 real demo cases
   本机仅 1 份受治理招股书 PDF。configs/v045_demo_cases.json 已声明 3 个 catalog 内真实案例
   (ipo_2024_02410 / ipo_2024_02460 / ipo_2024_01318)，缺失的两个在 summary.json 中显式记为
   unavailable_prospectus，不做替代。补齐 PDF 后重跑同一脚本即可。

2. Market 通道在本机为 unavailable_error
   reports/v04_pr_b/core_features 在本 workspace 不存在（reports/* 未入库）。E 不重跑 frozen PR-B。
   A / B 在本地物化该产物后，Market 通道即自动可用，Market Intelligence 与市场侧冲突规则随之生效。

3. LLM Final Supervisor 在离线配置下 status=unavailable
   这是设计中的诚实降级。configs/v045_competition_ai.yaml 配好远端 provider 凭证后即为 available；
   接线与越界校验已由 contract / integration 测试覆盖。

4. Model 通道 disabled
   仍受 PR-H 的 frozen PR-F handoff blocker 约束，属 D lane，未在本轮触碰。
```

## 5. 安全与边界审计

```text
2025 Blind y accessed                 false
upstream PR-A–PR-F rerun              false
frozen manifest / completion report   unchanged
public Pydantic schema changed        false（综合结论走 metadata，非新字段）
frozen v04_* configs changed          false（新增 v045_* 配置，PR-H 运行身份不变）
component Protocol changed            false（finalize(inputs) 签名不变，supervise() 为可选扩展）
mock / fake data in any channel       false
absolute local path or secret committed  false
reviewer notes committed              false（data/human_review/* 已 gitignore）
```

`WorkflowState` 未新增字段：`finalize → report` 的交接走 workflow 实例属性，trace sidecar 经
`component_diagnostics` 输出。

## 6. 变更清单

新增：

```text
src/ipo_risk/agents/conflict_detection.py
src/ipo_risk/agents/targeted_recheck.py
src/ipo_risk/agents/final_supervision_llm.py
src/ipo_risk/runtime/__init__.py
src/ipo_risk/runtime/competition_trace.py
src/ipo_risk/repositories/human_review.py
src/ipo_risk/services/human_review_service.py
src/ipo_risk/workflows/v04_competition.py
app/competition_runtime_view.py
app/evidence_viewer.py
app/human_review_ui.py
configs/v045_competition_offline.yaml
configs/v045_competition_ai.yaml
configs/v045_demo_cases.json
scripts/run_v04_role_e_demo.py
tests/contract/test_v045_llm_final_supervisor.py
tests/unit/test_v045_conflict_and_recheck.py
tests/unit/test_v045_competition_trace.py
tests/unit/test_v045_human_review.py
tests/unit/test_v045_competition_runtime_view.py
tests/integration/test_v045_competition_workflow.py
```

修改：

```text
src/ipo_risk/core/container.py            注册 final_supervisor=llm 与 V04CompetitionWorkflow 选择
src/ipo_risk/providers/prompt_registry.py 注册 final_supervision_synthesis / v04_final_supervision_v1
app/streamlit_app.py                      5 工作区重构、比赛场景、Evidence Viewer / Human Review 接入
scripts/validate_competition_runtime.py   把 v045_competition_ai.yaml 纳入 A 的 provider 接线校验
.gitignore                                data/human_review/* 不入库
```

## 7. 复现

```bash
python -m pytest -q
python scripts/validate_competition_runtime.py
python scripts/run_v04_role_e_demo.py
streamlit run app/streamlit_app.py   # 选择「v0.4.5 比赛版（离线）」并上传招股书 PDF
```

测试基线：`1783 passed`（本轮新增 86 项）。
