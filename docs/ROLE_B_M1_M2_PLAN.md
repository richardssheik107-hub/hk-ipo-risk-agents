# Role-B M1/M2 Plan — 从失分取证到 Full Development

> 状态日期：`2026-08-28`
>
> 当前 fixed-10：M1 `23.33%`，M2 `18.75%`
>
> 当前工作轨：v0.4.6 forensic / offline-shadow-gated ablation

本文档取代旧的 fixed-10 workflow 与 Lunamax Runner-only 手册。fixed-10 是快速诊断集，不是最终成绩集。

## 1. 为什么当前分类不足

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

因此本轮第一目标是找到每个 Risk Unit 与 Evidence Unit 的最早可证明失败阶段。

## 2. 工作包

### B0 — 身份与评测输入审计

校验：

- fixed-10 subset hash；
- Existing-Gold manifest hash；
- code fingerprint；
- provider / model / transport；
- Prompt / Schema hash；
- journal identity；
- Validation=false / Blind=false。

不同身份的结果不得放进同一 A/B 表。

### B1 — Parser 与页码保真

对每个 Gold Evidence Unit 做 post-run 只读检查：

- 指定 physical page 是否保留 anchor；
- ±1 / ±2 页是否存在系统偏移；
- 全文是否存在；
- 表格、断行、短 anchor、多重匹配是否造成不可判定。

Gold 只用于 evaluator-side join，不反馈 runtime。

### B2 — Retrieval 与 Agent 消费

逐 Evidence Unit 记录：

```text
candidate count
first Gold page rank
first exact anchor rank
top1 / 3 / 5 / 10 / 20
actual Agent topK
Agent consumed
snippet truncation
```

必须区分：candidate miss、ranking/topK miss、page hit but anchor truncated、consumed but later dropped。

### B3 — LLM 调用质量

按 task 统计：

- expected / invoked；
- transport / auth / request failure；
- structured validation；
- scope validation；
- retry / correction；
- applicable / abstain / candidate produced。

先通过 matching provider/model/Prompt/Schema 的 synthetic smoke，再运行真实 fixed-10。

### B4 — Candidate 生命周期

逐 Risk Unit 记录：

```text
deterministic candidate
LLM candidate
extraction status
builder status
normalization
reconciliation
verifier outcome
final bucket
status / level / calculation
```

Financial 额外拆分：period、percentage scale、table row/column、latest-period selection、complete/incomplete candidate。

Redemption Rights 额外拆分：权利存在、持有人、上市终止、失败/撤回后恢复、一般法定权利、证据充分性。

### B5 — Final Evidence binding

建立漏斗：

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

同时报告 M2 overall、conditional on final-positive、conditional on Agent consumed。

### B6 — 修复、消融与扩展

修复顺序按：

```text
影响单元数
× 同时影响 M1/M2
× 可恢复比例
÷ 实施复杂度与回归风险
```

每个修复包必须：

- 对应一个被证明的根因假设；
- 有单元/契约/回归测试；
- 有修复前后消融；
- 不含公司、股票、case_id、页码或 Gold 原句特判；
- 一个主指标提升时另一个不得退化。

fixed-10 达标后运行 ALL 79 Development，达到门槛后冻结，再由人工授权 one-shot ALL 19 Validation。

## 3. v0.4.6 推荐运行顺序

```bash
# 1. Existing-Gold / subset identity
python scripts/audit_v045_existing_gold.py --output-dir reports/v045_role_b
python scripts/run_v046_role_b_ablation.py --subset-only

# 2. provider/model/structured contract
python scripts/check_v046_role_b_structured_smoke.py

# 3. same-run offline / shadow / gated
python scripts/run_v046_role_b_ablation.py \
  --run-id <RUN_ID> \
  --modes all \
  --execute
```

若真实凭证或授权 PDF 缺失，保持 `EXECUTION_BLOCKED`；不得切换 mock 冒充真实测量。

## 4. 必须生成的诊断产物

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

下一步应补齐：

```text
parser_preservation.json
risk_root_cause_matrix.csv
evidence_root_cause_matrix.csv
m1_decomposition.json
m2_decomposition.json
fix_priority.json
```

每个根因必须标记 `PROVEN`、`INFERRED` 或 `UNAVAILABLE`。

## 5. 允许的优化

Development-only 且可审计时，允许：

- Parser page/text preservation 修复；
- query family、alias、context、BM25/lexical hybrid、reranker；
- topK 与 snippet/context 策略；
- provider/model/transport 对照；
- Prompt、Schema、bounded retry/correction；
- deterministic / LLM non-destructive merge；
- normalization、period/value reconciliation；
- Verifier 实现缺陷修复；
- Evidence retention 与 binding 修复。

不再规定固定 2–4 轮，也不再要求 Runner-only。迭代由证据覆盖、指标增益和停止条件控制。

## 6. 不可越过的边界

- 不修改 Existing Gold、Evaluator、fixed-10 identity；
- 不把 Gold 输入 runtime；
- 不用 Validation 调参；
- 不访问 Blind outcome；
- 不接受越界 Evidence；
- 不按公司或页码硬编码；
- 不用 fallback 冒充 real LLM；
- 不为提分删除失败案例；
- 不提交 PDF、Secret、raw journal 或绝对路径。

## 7. 阶段 Gate

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
Blind=false
```

## 8. 停止条件

停止并保留最佳 commit，当：

- 连续两个修复包无净增益；
- fixed-10 提升但较大 Development 回归；
- 需要修改 Gold / evaluator；
- 需要查看 Validation 才能选择参数；
- transport 结构化成功率无法在有界预算内稳定；
- 诊断覆盖不足以证明下一个修复点。
