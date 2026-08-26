# Competition Metric Protocol v2 — Existing-Gold-Only

> Protocol ID: `v045_competition_metric_protocol_v2_existing_gold_only`
>
> Scope: v0.4.5 competition evaluation and final submission
>
> Status: **FROZEN BEFORE ANY NEW 2024 VALIDATION METRIC RE-EVALUATION**
>
> Supersedes: `v045_competition_metric_protocol_v1`

本文件把赛题中未给出完整 evaluator 细节的指标，转换成一套预先声明、可复现、可审计的项目评价协议。v2 的核心变化只有一个：**M1/M2 不再新增任何人工 Gold 标注，不补 risk family，不重新做人类 Evidence Group；只使用项目此前已经完成并冻结的 Expert Annotation / Oracle Gold 作为标准答案来源。**

v1 在任何新的 2024 Validation metric 重评之前被本版本取代；本次调整没有打开新的 Validation 结果，也没有访问 2025 Blind y。

赛题原文件明确要求：

- 关键风险要素抽取准确率 `>= 80%`；
- 关键证据片段召回率 `>= 85%`；
- Agent 推理链路、角色分工、工具调用记录和证据来源可追踪率 `= 100%`；
- 逻辑解释有效性高；
- 用上市首日、5D、20D、60D 真实表现验证预警价值，其中 5D 显著下跌识别给予更高权重。

原文件没有规定 Risk Accuracy 的唯一公式、Evidence 是否采用 Top-K、K 等于多少、5D“显著下跌”的阈值或 Explanation rubric。本协议不冒充官方唯一公式，只定义本项目提交前固定使用的可复现口径。

## 1. 数据与 split 治理

```text
2020–2023  Development
2024       Validation
2025       Blind
```

### 1.1 Existing Gold only

M1/M2 的唯一人工标准答案来源是项目此前已经存在并冻结的 Expert Annotation / Oracle Gold：

```text
annotation inventory   101
valid annotations      100
official materialized   98
```

这些数字描述现有 Gold inventory，不等于 M1/M2 最终可评价单元数量。M1/M2 evaluator 必须通过只读代码审计现有 annotation，统计实际 `evaluable` support。

从本版本开始明确禁止：

- 为比赛指标新增人工标注；
- 为某个低 support risk family 临时补标；
- 看模型错误后修改旧专家答案；
- 把旧 Gold 未标注的风险解释为“明确不存在”；
- 为了满足新协议人工重做 Evidence Group；
- 根据 Validation 结果回头调整 Gold、Prompt、阈值或 metric 公式。

### 1.2 Unjudged semantics

旧 Gold 没有明确判断的 `case × risk` 单元统一视为：

```text
UNJUDGED
```

`UNJUDGED`：

- 不进入 M1 正样本分母；
- 不自动当 negative；
- 不用于制造 false positive / true negative；
- 在最终报告中按 risk family 披露 support。

### 1.3 Anti-tuning

- Development：允许看错误、改代码、Retriever、Prompt、structured extraction、normalization、RiskItem reconciliation、Verifier；
- Validation：系统/Prompt/evaluator 冻结后一次性确认，不作为第二开发集；
- Blind：未正式授权前不读取 2025 outcome/y；
- evaluator version、Gold source hash、evaluable-unit manifest 必须在 Validation 运行前冻结。

## 2. M1 — 关键风险要素抽取

### 2.1 Risk scope

赛题点名“包括但不限于”对赌/赎回、关联交易、客户或供应商集中度、现金流消耗压力。项目仍保留这些 competition-priority 映射：

```text
redemption_rights
related_party_transaction
customer_concentration
supplier_concentration
cash_burn_pressure
```

但 **v2 不要求人为补齐这五类 Gold**。最终可评价范围完全由既有专家 Gold 实际覆盖决定：

```text
existing Gold 有明确 positive judgment -> evaluable
existing Gold 无明确 judgment          -> UNJUDGED
support = 0                             -> NOT_EVALUABLE_FROM_EXISTING_GOLD
```

`related_party_transaction` 如旧 Gold 无有效 support，就明确报告 `NOT_EVALUABLE_FROM_EXISTING_GOLD`，不新增 sidecar 标注来凑指标。`cash_burn_pressure` 仅在旧 annotation 能确定性映射到已有 cash/runway/cash-burn 专家事实时进入评价。

现有 `material_litigation_compliance`、`precommercial_product`、`continuous_loss`、`revenue_growth` 等，如果旧 Gold 已明确标注，可以进入 per-risk diagnostics；不得为了对齐“五类”删除已有可评价事实。

### 2.2 Existing-Gold Risk Unit

M1 evaluator 只从既有 annotation 中确定性提取可评价单元。每个单元至少记录：

```text
case_id
source_annotation_id / hash
risk_family
existing_gold_status
existing_required_attributes
existing_evidence_refs
split
evaluable=true
```

不得新增人工属性或把缺失字段猜出来。

一个正式“正确抽取”要求：

1. risk family 与既有 Gold 一致；
2. 旧 Gold 已明确要求的关键属性满足 deterministic/canonical matching；
3. 若旧 Gold 本身包含支撑 Evidence，则系统至少命中一条可接受的既有 Evidence 依据。

如果某旧 annotation 只有 risk existence、没有足够属性，则 evaluator 只能按其实际已有标注粒度判定，不得为了 metric 临时增加 required attributes。

### 2.3 Primary metric

```text
Official-aligned Existing-Gold Risk Extraction Accuracy
= correct evaluable positive Existing-Gold Risk Units
  / all evaluable positive Existing-Gold Risk Units
```

Official pass line：

```text
>= 0.80
```

Project safety target：

```text
>= 0.85
```

### 2.4 Secondary metrics

必须报告：

```text
evaluable positive support
correct positive count
positive extraction recall / accuracy
per-risk support
per-risk correct / recall
```

`Precision`、`Macro F1` 只有在旧 Gold 对对应风险提供足够明确、近似 exhaustive 的 positive/negative judgment 时才允许正式报告；否则必须写：

```text
NOT_AVAILABLE_FROM_EXISTING_GOLD
```

不再为了得到 Precision/Macro F1 去补标 negative cases，也不设置必须靠新增标注才能满足的内部 guardrail。

## 3. M2 — 关键 Evidence Recall

### 3.1 官方 85% 不是 Recall@5

赛题只要求“关键证据片段召回率 >=85%”，没有规定 Top-K，也没有规定 K=5。

v2 正式拆分为：

```text
Primary official-aligned:
Existing-Gold Evidence Coverage Recall

Secondary diagnostics:
Recall@1 / @3 / @5 / @10 / @20
```

历史 offline `Evidence Recall@5 = 20%` 继续保留为旧 benchmark 诊断事实，不是 real-LLM 指标，也不能直接写成“官方 Evidence Recall 当前为20%”。

### 3.2 Existing-Gold Evidence Unit

M2 只使用旧 annotation 里已经存在的 Evidence/page/span/table/anchor 信息。

一个 `Existing-Gold Evidence Unit` 必须来自比赛收尾之前已经存在的专家标注或有效 audit overlay。允许的处理只有：

- 确定性 schema normalization；
- identity/page 格式标准化；
- 去除完全重复的同一既有 anchor；
- 尊重旧标注本身已有的等价/分组关系。

禁止：

- 新增人工 Evidence；
- 人工把多个旧片段重新解释成新的 semantic group；
- 为模型漏掉的证据临时增加替代页；
- 从 PDF 重新人工寻找“更容易命中”的标准答案。

### 3.3 Primary metric

```text
Existing-Gold Evidence Coverage Recall
= covered evaluable Existing-Gold Evidence Units
  / all evaluable Existing-Gold Evidence Units
```

Official pass line：

```text
>= 0.85
```

Project safety target：

```text
>= 0.88
```

Primary metric 不设置固定 Top-5 上限。

### 3.4 Retrieval diagnostics

为了定位问题，继续报告：

```text
Candidate Retrieval Recall@20
Reranked Recall@10
Recall@1
Recall@3
Recall@5
Recall@10
Recall@20
Final Existing-Gold Evidence Coverage Recall
```

工程目标保留为：

```text
Candidate Retrieval Recall@20 >= 0.95
Reranked Recall@10           >= 0.90
Final Existing-Gold Coverage >= 0.88 project target
```

这些是内部工程目标，不是官方额外阈值。

## 4. B lane 的唯一优化范围

从现在开始 B/A 在 M1/M2 上只做：

```text
existing Gold read-only coverage audit
→ real-LLM Development run
→ evaluate
→ failure taxonomy
→ Development-only code / Retriever / Prompt / extraction / reconciliation / Verifier optimization
→ rerun same evaluator
→ freeze
→ one-shot Validation evaluation
```

Failure taxonomy：

```text
retrieval_candidate_miss
ranking_miss
semantic_extraction_miss
schema_normalization_miss
riskitem_reconciliation_miss
verifier_rejection
existing_gold_unjudged_or_unsupported
```

不新增标注，不扩 Gold universe，不增加新的 risk family 标注任务。

### 4.1 Benchmark scope

不再新建“20-case Gold target”。

允许为了迭代速度从既有 Development Gold 中固定一个小 debug subset，但它只用于快速回归；正式 Development benchmark 使用：

```text
ALL evaluable existing Development Expert Gold
```

Validation 使用：

```text
ALL evaluable existing Validation Expert Gold
```

前提是对应 prediction 在 Gold 评分前冻结，并且 Validation 不用于后续调优。

## 5. M3 — Traceability

Official target：

```text
100%
```

一个 relevant TraceEvent 只有在 actor/action/tool-or-skill identity 完整，且有 Evidence reference、Calculation reference 或 explicit `no_evidence_reason` 时才算 accounted。

远程 LLM 事件还必须保留：

```text
provider
model
prompt_version
request_id
raw_response_hash
latency_ms
```

最终 Gate：

```text
Development real-LLM benchmark traceability = 1.0
AND
final 3-case matrix traceability = 1.0
```

## 6. M4 — Explanation Quality

赛题要求“逻辑解释有效性高”但没有给绝对数值线。现有 5 维 rubric 保持：Evidence grounding、Logical consistency、Conflict handling、Re-check quality、Final conclusion。

该项属于 E/A 最终产品验收，不属于 B 的 Gold 扩标任务。本版本不因 M1/M2 变更增加任何新的 M4 标注工作。

## 7. M5 — 上市后风险预警

必须输出：

```text
return_1d
return_5d
return_20d
return_60d
```

Primary business horizon 仍为 5D。项目预先定义：

```text
significant_drop_5d = (return_5d <= -0.10)
```

并报告 Precision / Recall / F1 / PR-AUC / ROC-AUC / Top-10% / Top-20% hit rate / base prevalence。赛题没有给这些指标绝对及格线，不伪造官方门槛。

## 8. Required M1/M2 artifacts

Role B 最终 `document_benchmark_summary.json` 至少提供：

```text
metric_protocol_version = v045_competition_metric_protocol_v2_existing_gold_only
existing_gold_source
existing_gold_source_hash_or_manifest
evaluable_development_case_count
evaluable_validation_case_count

risk_extraction.evaluable_positive_count
risk_extraction.correct_positive_count
risk_extraction.official_aligned_accuracy
risk_extraction.project_target_met
risk_extraction.per_risk
risk_extraction.precision_status
risk_extraction.macro_f1_status

evidence_coverage.evaluable_existing_gold_count
evidence_coverage.covered_existing_gold_count
evidence_coverage.coverage_recall
evidence_coverage.project_target_met
retrieval_diagnostics.recall_at_1/3/5/10/20

new_manual_annotations_added = false
existing_gold_modified = false
blind_2025_outcome_accessed = false
```

`risk_benchmark.csv` 与 `evidence_benchmark.csv` 必须携带 source annotation identity/hash 或可追溯 manifest key，证明评价来自旧 Gold，而不是比赛收尾阶段新造答案。

## 9. Final acceptance semantics

M1/M2 只有在以下条件同时满足时才可声明达标：

```text
existing Gold source frozen/read-only
+ no new manual annotations
+ no unjudged-as-negative
+ real-LLM Development measurement
+ M1 existing-Gold official-aligned Accuracy >=0.80
+ M2 existing-Gold Evidence Coverage Recall >=0.85
+ per-risk / evidence support disclosed
+ evaluator/version/source manifest frozen
+ Validation one-shot only
+ 2025 Blind untouched
```

项目内部目标仍是 M1 `>=0.85`、M2 `>=0.88`，但当前比赛收尾的优化手段只允许是**代码和真实大模型链路优化**，不再通过增加人工 Gold 改变分母。
