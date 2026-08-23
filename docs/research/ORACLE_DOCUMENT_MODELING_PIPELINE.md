# Oracle Document Modeling Pipeline

> Status: **MERGED / EVALUATION-ONLY**  
> Documentation review: **2026-08-21**

Oracle 是评测上限 / 错误归因旁路，永远不是 production runtime。

```text
current pass1
+ explicit audit overrides
→ EffectiveRiskGoldView
→ expert_oracle_document_features_v1
→ same Market X / same y / same split / same model family
→ Oracle diagnostic
```

它不读取 PDF，不调用 Retriever、LLM、Agent、Verifier、Supervisor，也不调用 Production `v04_document_features_v1` builder。

Oracle features 只包含结构化风险状态、置信度、Evidence count、Calculation availability 等受控字段；不包含 reasoning、Evidence text、公司文本、Gold page / Evidence ID、虚构 score 或上市后知识。

## 1. Audit precedence

Audit precedence 为 field-level：

- current `pass1` 始终是 base；
- 只有 self-contained、带 explicit `resolved_state` 的 audit entry 才覆盖对应 named risk；
- stale audit 不能恢复历史 pass1；
- artifact 保留 base hash、audit hash、applied risks 和 deterministic effective hash。

## 2. Existing commands

从仓库根目录运行。

### Index

```powershell
python scripts/index_oracle_gold.py --output-dir reports/v04_pr_a/oracle_index
```

输出 Oracle inventory / provenance / failure artifacts，只读取 reviewed annotations。

### Oracle X

```powershell
python scripts/build_oracle_document_features.py `
  --all-eligible `
  --output-dir reports/v04_pr_a/oracle_features `
  --resume
```

每个 case 生成独立 feature artifact 和 failure report；`resume` 只允许复用完全一致的 content / provenance。发生 provenance conflict 时 fail closed，不覆盖。

## 3. Frozen PR-A result

PR-A 已完成：

```text
Oracle inventory
→ Oracle feature materialization
→ Oracle coverage
→ Production ∩ Oracle intersection
→ deterministic rerun
```

冻结结果为 Oracle materialized 60、`no_reviewed_gold` 378、Production ∩ Oracle 60。Oracle 不要求覆盖全部 438 cases；它只覆盖真正具有 reviewed expert Gold 的 eligible case。

PR-A 没有训练 Oracle model，且已经 COMPLETE / FROZEN。Oracle v2 已在
PR-E 中完成正式 M/P/O/PM/OM 比较；当前下一阶段为 PR-F。

## 4. Later modeling role

PR-D / PR-E 才把 Oracle X 放入 canonical modeling comparison。

正式比较冻结为：

```text
M   = Market-only
P   = Production Document-only
O   = Oracle Document-only
PM  = Production Document + Market
OM  = Oracle Document + Market
```

比较必须固定：

```text
same cohort
same chronological split
same target
same preprocessing
same model family
```

目标不是让 Oracle 替代 Production，而是分解：

```text
Document signal ceiling     ≈ OM - M
Production captured signal  ≈ PM - M
Pipeline information gap    ≈ OM - PM
```

这取代旧文档中的“Oracle vs pipeline V1 / V2 / V2+LLM”表述；Retriever 版本比较属于未来 v0.5 研究，不是当前 v0.4 Oracle 主任务。

## 5. Blind protection

2025 blind policy 对 Oracle 同样有效：

- 可以准备 governed Oracle / Production X（若 cohort policy 允许）；
- feature / target / model policy 冻结前不读取 2025 y；
- 不用 2025 选择 Oracle feature、阈值或模型；
- 一旦 2025 outcome 被打开，不能再把同一结果称为 future blind。

## 6. Decision value

PR-E 通过 Oracle diagnostic 决定 v0.5 优化方向：

```text
OM ≈ M
→ 招股书风险信号本身可能较弱，先检查 target / sample / market regime

OM >> M and PM ≈ M
→ Document signal 存在，但 Production Pipeline 丢失信息
→ v0.5 优先 Retriever / LLM / Agent / Verifier

PM > M and PM ≈ OM
→ Production 已捕获大部分可提取文档信号
→ 重点转向 model / Market Agent / productization
```

Oracle 的价值是**研究诊断**，不是产品捷径。
