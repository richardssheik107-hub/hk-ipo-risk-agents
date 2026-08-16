# Retriever V3 — Frozen Research Decisions

Status: **MERGED / FROZEN / DEFERRED UNTIL v0.5**

本文件只保留 Retriever 研究对未来仍有约束力的结论，不再作为当前 v0.4 执行计划。

## 1. 数据治理状态

Retriever V3 使用的研究集为：

```text
60 total cases
50 development cases
10 locked cases
```

历史 Locked 10 已经在最终验证中正式打开并消费。

因此从现在开始：

- Locked 10 只作为历史评测结果；
- 不允许根据其结果调参后再次把它称为 blind / locked；
- v0.5 如果重启 Retriever 优化，只能在 development 上开发；
- 新版本需要新的 unseen / external / temporal holdout 才能做独立验证。

## 2. 已冻结的 Retriever V3 方向

当前研究成果已经验证并进入仓库历史的主要组成包括：

```text
V1 / V2 / V2.1 deterministic retrieval lanes
+ BM25 candidate lane
+ table-aware candidate lane
+ deterministic feature builder
+ LambdaMART LTR
```

Development OOF 中选定的主要 ranking baseline 为 LTR-C。它相对于 equal-weight RRF 明显改善整体早排指标，但不是所有 risk 都单调提升。

冻结研究结果中需要保留的事实：

- LTR 整体 ranking quality 有明显提升；
- `customer_concentration` 存在局部 regression 风险；
- Locked evaluation 中 `material_litigation_compliance` 也出现局部 regression；
- `precommercial_product` 仍是弱项，天然更依赖跨 section / semantic evidence；
- candidate generation 的 ceiling 仍高于最终 ranking，说明未来还有排序空间；
- 非 Gold candidate 不能自动当作 true negative。

因此最终研究结论应理解为：

> Candidate generation generalizes; ranking improvement is meaningful overall but mixed by risk.

不能包装成“所有风险均 FULL PASS”。

## 3. 风险类型差异

Gold / evidence 结构表明，不同风险不应强行使用同一种 recall 策略：

- Financial / concentration 类风险高度 table-like，适合 table-aware / numeric features；
- Legal 风险更依赖 authority、status、conditional language 与 lexical/semantic coverage；
- `precommercial_product` 更容易跨 section，需要 multi-evidence / semantic reasoning。

未来 v0.5 若继续优化，优先考虑 risk-aware routing / feature interaction，而不是简单继续叠加统一检索通道。

## 4. LLM Reranker V1.1 冻结设计

历史 pilot 证明 LLM semantic reranking 有价值，但 batch-atomic structured output 的 fallback 可靠性不足。

未来如果重启，推荐固定为：

```text
Frozen Stage-1 Top20
→ stable candidate IDs
→ deterministic micro-batches
→ independent candidate validation
→ keep valid judgments
→ per-candidate fallback
→ Python final ordering
```

必须同时报告两类指标：

### Semantic value

- Required Recall@K
- MRR
- NDCG
- completion

### Engineering reliability

- candidate success rate
- candidate fallback rate
- retry rate
- schema failure rate
- latency
- token / cost telemetry

目标是把 fallback 压到低个位数，同时保留语义收益。

## 5. 当前项目优先级

Retriever V3 不再是当前主线。

当前执行顺序以：

- `../END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`
- `../ROADMAP.md`

为准。

在 v0.4 End-to-End Closed Loop 冻结前，不继续为了提高几个百分点的 Retriever 指标而阻断 Document Features → Market Dataset → Prediction → Final Report 的完整链路。

## 6. v0.5 重新打开 Retriever 的前置条件

只有满足以下条件才重新进入 Retriever / LLM Reranker 研究：

1. v0.4 完整闭环已经冻结；
2. 端到端失败分析证明 retrieval / ranking 是主要瓶颈之一；
3. 新的 development experiment plan 预先冻结；
4. 新的独立 unseen holdout 已定义；
5. 不重新使用历史 Locked 10 进行“二次 blind”。

这样才能保证 Retriever 优化继续具有研究可信度。