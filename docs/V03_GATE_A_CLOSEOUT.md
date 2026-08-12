---
phase: v0.3 Human Golden Final Closeout
software_gate: PASS
human_golden_governance: COMPLETE
---

# v0.3 Gate A 与 Golden 治理收口

本文件维护 Gate A 与人工 Golden 的当前治理状态。项目总体状态以
[PROJECT_MASTER_CHECKLIST.md](PROJECT_MASTER_CHECKLIST.md) 为主入口。

## 1. 当前结论

```text
V03_SOFTWARE_GATE = PASS
V03_TECHNICAL_STATUS = COMPLETE
V03_PRODUCT_STATUS = COMPLETE
V03_DEMO_STATUS = READY
V03_RELEASE_READINESS = READY
V03_RELEASE_STATUS = RELEASED
V03_RELEASE_TAG = v0.3.0-multi-agent-risk-analysis

V03_HUMAN_GOLDEN_GOVERNANCE = COMPLETE
V03_FORMAL_GOLDEN_EVALUATION = COMPLETE
V03_FORMAL_CROSS_DOMAIN_GOLDEN_METRIC = AVAILABLE
OWNER_WAIVER_STATUS = SUPERSEDED_BY_SINGLE_REVIEW_POLICY
```

Owner 于 2026-08-12 永久取消 Financial / Business 独立二审硬门槛。当前冻结政策为
`single_named_human_review_v1`：具名真实人工完成一次复核后即可标记
`first_reviewed`并进入正式 Golden。该政策不把一审描述为双审；已有 Legal
`double_reviewed`与`adjudicated`provenance 原样保留。

## 2. 三条专业线

| 专业线 | 软件状态 | Golden 状态 |
| --- | --- | --- |
| Financial | COMPLETE / INTEGRATED | 23 条 `first_reviewed` canonical Golden |
| Legal | COMPLETE / INTEGRATED | 4 条 `double_reviewed`、4 条 `adjudicated` canonical Golden |
| Business | COMPLETE / INTEGRATED | 3 条 `first_reviewed` canonical Golden |

`second_reviewer`在`first_reviewed`行保持为空，未伪造 reviewer 或 adjudicator。

## 3. Gate 项目

| ID | Criterion | 当前状态 | 说明 |
| --- | --- | --- | --- |
| A01 | 三个真实 Agent 已合并 | PASS | Financial / Legal / Business |
| A02 | 统一 `RiskAgent` 契约 | PASS | 公共接口未变 |
| A03 | Financial 正式人工 Golden | PASS | 23 条具名人工一审，按当前政策正式晋级 |
| A04 | Business 正式人工 Golden | PASS | 3 条具名人工一审，按当前政策正式晋级 |
| A05 | Legal 人工 primary/second/adjudication | PASS | 正式审计保留 |
| A06 | Legal reviewed rows canonical promotion | PASS | provenance 保留 |
| A07 | Legal candidate contract | PASS | additive 内部契约已批准 |
| A08 | Legal severity policy | PASS | provisional medium / 50 |
| A09 | Legal Retriever gap | PASS | development A—H Top-5 8/8；非发布 Recall@3 证明 |
| A10 | Legal runtime Prompt routing | PASS | 精确版本、错配 fail-closed |
| A11 | 2025 blind guard | PASS | 未打开、未用于调优或本次评测 |
| A12 | Mock、v0.2、完整回归 | PASS | 持续验证 |

```text
GATE_A_OVERALL_STATUS = PASS
```

## 4. Owner Waiver

历史 Owner waiver 当时有效，并允许软件在 A03/A04 未关闭时完成技术收口。当前新政策已
取代其发布门槛效力，但历史文件继续保留：

```text
OWNER_WAIVER_STATUS = SUPERSEDED_BY_SINGLE_REVIEW_POLICY
WAIVER_HISTORY_RETAINED = true
```

## 5. 正式评测边界

- 正式评测仅使用真实、具名且状态为`first_reviewed`、`double_reviewed`或
  `adjudicated`的行；
- `draft`、匿名、AI/占位 reviewer 和缺少必要 provenance 的记录自动排除；
- 2025 blind 不属于 v0.3 Golden，未用于调优或本次评测；
- 本次实际指标无论高低均原样报告，不据此修改 Retriever、Agent、Verifier 或阈值；
- 数值抽取指标因 canonical manifest 没有冻结对应字段而保持`NOT_AVAILABLE`。
