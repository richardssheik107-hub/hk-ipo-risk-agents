# Role-B M1/M2 Plan — 从失分取证到 Full Development

> 状态日期：`2026-08-28`
>
> 当前 fixed-10：M1 `23.33%`，M2 `18.75%`
>
> 当前工作轨：v0.4.6 forensic / offline-shadow-gated ablation

本文档取代旧的 fixed-10 workflow 与 Runner-only 手册。fixed-10 是快速诊断集，不是最终成绩集。

## 1. 当前已经具备的工具

- Existing-Gold audit / evaluator；
- v0.4.6 structured smoke；
- offline / shadow / gated same-run harness；
- immutable local LLM journal；
- Financial high-recall adapter；
- retrieval / risk waterfall；
- monotonicity report；
- `audit_v04_pr_h_document_evidence.py` read-only Evidence auditor。

Evidence auditor 可检查 persisted result 中的 Evidence ID 唯一性、Risk/Evidence/Calculation linkage、physical page、bounded text match、bbox、Evidence Index、Supervisor invention、Agent/Verifier provenance、leakage 和 deterministic signature。它不调用 Agent、Retriever 或模型。

仍缺：Parser preservation 对 Gold anchor 的 evaluator-side audit，以及 Candidate→LLM→Builder→Normalization→Reconciliation→Verifier 的完整生命周期 Trace。

## 2. 为什么当前分类不足

当前 evaluator 在最终结果没有对应 `risk_code` 时，会归为 `semantic_extraction_miss`。这个标签只能说明最终风险缺失，不能区分：

```text
Parser 丢失
Retriever 未召回
正确 Evidence 排名过低
LLM 未调用 / transport 失败 / schema 失败 / scope 拒绝
LLM 错误 abstain
Builder NOT_APPLICABLE
Normalization / reconciliation 删除
Verifier 拒绝
Final bucket 或 Evidence binding 丢失
```

因此第一目标是找到每个 Risk Unit 与 Evidence Unit 的最早可证明失败阶段。

## 3. 工作包

### B0 — 身份与评测输入审计

校验 fixed-10 subset、Existing-Gold、code fingerprint、provider/model/transport、Prompt/Schema、journal、Validation/Blind 标志。不同身份的结果不得同表比较。

### B1 — Parser 与页码保真

对每个 Gold Evidence Unit 做 post-run evaluator-side 检查：指定页、±1/±2、全文 anchor、短 anchor、表格和多重匹配。Gold 不反馈 runtime。

同时对 final persisted result 运行 read-only Evidence auditor：

```bash
python scripts/audit_v04_pr_h_document_evidence.py \
  --analysis-json <analysis_result.json> \
  --case-id <case_id> \
  --stock-code <stock_code> \
  --pdf <authorized.pdf> \
  --expected-pdf-sha256 <sha256> \
  --output <evidence_audit.json>
```

### B2 — Retrieval 与 Agent 消费

逐 Evidence Unit 记录 candidate count、Gold page/anchor rank、topK、Agent consumed、snippet truncation，并区分 candidate miss、ranking miss、page hit but anchor truncated、consumed but later dropped。

### B3 — LLM 调用质量

按 task 统计 expected/invoked、transport/auth/request、structured validation、scope、retry/correction、applicable/abstain/candidate。

### B4 — Candidate 生命周期

逐 Risk Unit 记录 deterministic/LLM candidate、extraction、builder、normalization、reconciliation、verifier、final bucket、status/level/calculation。

Financial 额外拆分 period、percentage scale、table row/column、latest-period、complete/incomplete candidate。

Redemption Rights 额外拆分权利存在、持有人、上市终止、失败/撤回后恢复、一般法定权利、证据充分性。

### B5 — Final Evidence binding

```text
Gold Evidence
→ Parser preserved
→ candidate top20
→ Agent consumed
→ candidate risk created
→ final-positive retained
→ Evidence retained
→ page matched
→ anchor matched
→ M2 covered
```

报告 M2 overall、conditional on final-positive、conditional on Agent consumed。

### B6 — 修复、消融与扩展

修复优先级：影响单元数 × 同时影响 M1/M2 × 可恢复比例 ÷ 实施复杂度和回归风险。

每个修复包有 proven hypothesis、测试、前后消融、无 case/company/page/Gold 特判；一个主指标提升时另一个不得退化。

fixed-10 达标后运行 ALL 79 Development，达到门槛后冻结，再由 A 授权 one-shot ALL 19 Validation。

## 4. 推荐运行顺序

```bash
python scripts/audit_v045_existing_gold.py --output-dir reports/v045_role_b
python scripts/run_v046_role_b_ablation.py --subset-only
python scripts/check_v046_role_b_structured_smoke.py
python scripts/run_v046_role_b_ablation.py \
  --run-id <RUN_ID> \
  --modes all \
  --execute
```

随后逐 case 运行 read-only Evidence audit，并将其结果并入 Root-cause matrix。

若真实凭证或授权 PDF 缺失，保持 `EXECUTION_BLOCKED`；不得切换 mock 冒充真实测量。

## 5. 必须生成的诊断产物

现有 runner：

```text
baseline_manifest.json
ablation_summary.json
llm_call_quality.json
retrieval_waterfall.json
risk_pipeline_waterfall.json
monotonicity_report.json
failure_focus.json
best_iteration.json
```

下一步补齐：

```text
evidence_audit/<case>.json
parser_preservation.json
risk_root_cause_matrix.csv
evidence_root_cause_matrix.csv
m1_decomposition.json
m2_decomposition.json
fix_priority.json
```

每个根因标记 `PROVEN`、`INFERRED` 或 `UNAVAILABLE`。

## 6. 允许的优化

Development-only 且可审计时，允许 Parser preservation、query/alias/context、BM25/lexical hybrid、reranker、topK/snippet、provider/model/transport、Prompt/Schema/retry、non-destructive merge、normalization/reconciliation、Verifier 和 Evidence binding 修复。

不再规定固定 2–4 轮，也不再要求 Runner-only。迭代由证据覆盖、指标增益和停止条件控制。

## 7. 不可越过的边界

- 不修改 Gold、Evaluator、fixed-10 identity；
- 不把 Gold 输入 runtime；
- 不用 Validation 调参；
- 不使用 Blind 输入或 outcome 优化；
- 不接受越界 Evidence；
- 不按公司或页码硬编码；
- 不用 fallback 冒充 real LLM；
- 不为提分删除失败案例；
- 不提交 PDF、Secret、raw journal 或绝对路径。

## 8. 阶段 Gate

### Forensic Gate

```text
>=90% Risk Units 有最早可证明失败阶段
>=90% Evidence Units 有最早可证明失败阶段
shadow canonical result == offline
gated no extra network calls
```

### Fixed-10 Gate

```text
M1 >=0.80
M2 >=0.85
gated M1/M2 >= offline
real structured-valid rate 目标 >=0.95
```

### Full Development Gate

```text
case_count = 79
M1 >=0.80（目标 >=0.85）
M2 >=0.85（目标 >=0.88）
real_llm_cases = 79
Validation=false
Blind input/outcome not used for optimization
```

## 9. 停止条件

停止并保留最佳 commit，当连续两个修复包无净增益、fixed-10 提升但较大 Development 回归、需要修改 Gold/evaluator、需要查看 Validation/Blind 才能选择参数、transport 无法稳定，或诊断覆盖不足以证明下一个修复点。
