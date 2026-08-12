---
phase: v0.3 Final Product Completion — Owner Waiver
software_gate: PASS
human_golden_governance: PARTIAL
---

# v0.3 Gate A 与 Golden 治理收口

本文件只维护 Gate A 与人工 Golden 的真实治理状态。项目总体状态以
[PROJECT_MASTER_CHECKLIST.md](PROJECT_MASTER_CHECKLIST.md) 为唯一主入口。

## 1. 软件与研究验证分离

```text
V03_SOFTWARE_GATE = PASS
V03_TECHNICAL_STATUS = COMPLETE
V03_PRODUCT_STATUS = COMPLETE
V03_DEMO_STATUS = READY
V03_RELEASE_READINESS = READY

V03_HUMAN_GOLDEN_GOVERNANCE = PARTIAL
V03_FORMAL_CROSS_DOMAIN_GOLDEN_METRIC = NOT_AVAILABLE
```

Financial/Business 独立人工二审按 Owner waiver 延期。该事实必须保留，也禁止伪造
reviewer 或正式指标；但它被分类为 `RESEARCH_VALIDATION_LIMITATION`，不再是
`SOFTWARE_RELEASE_BLOCKER`。

## 2. 三条专业线

| 专业线 | 软件状态 | Golden 状态 |
| --- | --- | --- |
| Financial | COMPLETE / INTEGRATED | 23 条 primary-only，second review deferred |
| Legal | COMPLETE / INTEGRATED | 8 条 human-reviewed/adjudicated canonical Golden |
| Business | COMPLETE / INTEGRATED | 3 条 primary-only，second review deferred |

三个 Agent 均已进入 Registry、Container、`enhanced_v2`、Service、UI 与报告。

## 3. Gate 项目

| ID | Criterion | 当前状态 | 说明 |
| --- | --- | --- | --- |
| A01 | 三个真实 Agent 已合并 | PASS | Financial / Legal / Business |
| A02 | 统一 `RiskAgent` 契约 | PASS | 公共接口未变 |
| A03 | Financial 独立人工二审 | DEFERRED_BY_OWNER_WAIVER | 不伪造二审 |
| A04 | Business 独立人工二审 | DEFERRED_BY_OWNER_WAIVER | 不伪造二审 |
| A05 | Legal 人工 primary/second/adjudication | PASS | 正式审计保留 |
| A06 | Legal reviewed rows canonical promotion | PASS | provenance 保留 |
| A07 | Legal candidate contract | PASS | additive 内部契约已批准 |
| A08 | Legal severity policy | PASS | provisional medium / 50 |
| A09 | Legal Retriever gap | PASS | development A—H Top-5 8/8；非发布 Recall@3 证明 |
| A10 | Legal runtime Prompt routing | PASS | 精确版本、错配 fail-closed |
| A11 | 2025 blind guard | PASS | 未用于调优 |
| A12 | Mock、v0.2、完整回归 | PASS | 持续验证 |

## 4. Owner Waiver

Owner waiver 只改变软件版本门槛，不改变数据事实：

- A03/A04 仍不是 PASS；
- Financial/Business 不能进入正式 reviewed Golden 指标；
- 不生成正式跨域准确率；
- 后续真实人工二审完成后，可另行晋级，而不需要重写 v0.3 软件。

```text
OWNER_WAIVER_STATUS = ACTIVE_FOR_RELEASE_GATING
V3-8_TECHNICAL_IMPLEMENTATION = COMPLETE
SHARED_RUNTIME = COMPLETE
V3-8_START_STATUS = NOT_APPLICABLE_IMPLEMENTATION_COMPLETE
```

## 5. 剩余研究验证项

1. Financial 23 条由与 primary 不同的真实人员盲审；
2. Business 3 条由与 primary 不同的真实人员盲审；
3. 人工处理分歧并保留 adjudication；
4. 仅对正式 reviewed/adjudicated rows 计算跨域 Golden 指标。

Codex/AI 不得作为 reviewer 或 adjudicator。Owner waiver 文档必须保留为历史治理记录。
