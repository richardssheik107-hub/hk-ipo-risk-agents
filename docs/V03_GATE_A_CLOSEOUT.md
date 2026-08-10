---
snapshot_main: 6c7ba02fd18e4ce778f43b1756c9bb11a026f8cc
phase: Gate A — Professional Agent Completion & Golden Review
overall_status: BLOCKED
---

# v0.3 Gate A 收口验收表

本文件是 Gate A 的专项验收入口。项目总体状态仍以
[PROJECT_MASTER_CHECKLIST.md](PROJECT_MASTER_CHECKLIST.md) 为唯一入口。

状态核验基线为 `main@6c7ba02fd18e4ce778f43b1756c9bb11a026f8cc`
（Merge PR #30）。该 SHA 是GATE-A-09执行采用的`main`审计基线，不要求等于
本次变更未来合并后的`main` HEAD。

## 1. 三条专业线冻结状态

### Financial

```text
MERGED
STANDALONE-READY
GOLDEN-SECOND-REVIEW-PENDING
SHARED-INTEGRATION-PENDING
```

Financial Agent 本体不重新实现。后续工作仅包括真实金标独立二审，以及由共享集成
任务完成 Registry、Container、Workflow 和 Service 装配。

### Legal

```text
MERGED
STANDALONE-READY
CONTRACT-APPROVED
SEVERITY-POLICY-FROZEN
RETRIEVER-GAP-CLOSED
RUNTIME-PROMPT-INTEGRATION-PENDING
HUMAN-GOLDEN-REVIEW-PENDING
SHARED-INTEGRATION-PENDING
```

Legal Agent 本体不重新实现。候选字段契约与severity policy已经冻结，Retriever缺口
已经关闭。Gate A剩余工作是domain prompt运行时接入、Legal A—H人工复核与并表。

### Business

```text
MERGED
STANDALONE-READY
GOLDEN-SECOND-REVIEW-PENDING
SHARED-INTEGRATION-PENDING
```

Business Agent 本体已经冻结，不继续扩写 V3-7。后续只进行三条真实Golden记录的
独立二审，以及由共享集成任务完成 Registry、Container、Workflow 和 Service 装配。

## 2. Gate A 退出标准

| ID | Mandatory criterion | Current | 关闭证据或责任 |
| --- | --- | --- | --- |
| GATE-A-01 | Financial、Legal、Business standalone Agents 全部进入 `main` | PASS | PR #22、#26、#28 |
| GATE-A-02 | 三个Agent均保持 `RiskAgent.analyze() -> list[RiskItem]`，且不自行标记 `verified` | PASS | Agent契约测试与合并审核 |
| GATE-A-03 | 真实Financial Golden完成独立second review | FAIL | 组织第二复核、记录分歧与仲裁 |
| GATE-A-04 | Business三条真实Golden完成独立second review | FAIL | 1167.HK两条正例、9633.HK一条负例 |
| GATE-A-05 | Legal A—H完成人工primary review、独立second review及Case C adjudication | FAIL | `V03_LEGAL_GOLDEN_REVIEW_CHECKLIST.md` |
| GATE-A-06 | Reviewed Legal rows并入canonical v0.3 Golden Manifest | FAIL | 仅在人工复核完成后由数据维护者并表 |
| GATE-A-07 | Legal candidate additive contract fields由Member-1明确APPROVE或REJECT | PASS | additive内部候选字段已APPROVE；`V03_LEGAL_CONTRACT_DELTA.md` |
| GATE-A-08 | Legal severity policy冻结 | PASS | 两类Legal风险冻结为provisional `medium / 50`；A/E转人工复核 |
| GATE-A-09 | Legal Retriever alias、lifecycle、status、remediation及licence gap关闭 | PASS | 2020—2023 development draft A—H固定`limit=5`全部命中；`V03_LEGAL_RETRIEVAL_GAP_REPORT.md` |
| GATE-A-10 | Legal domain prompt正式进入real-provider runtime routing | FAIL | `V03_LEGAL_PROMPT_SPEC.md` |
| GATE-A-11 | 2025 blind set未参与开发、检索调优、Prompt调优或规则调参 | PASS | blind guard保持fail-closed |
| GATE-A-12 | Mock、2410.HK与完整回归保持稳定 | PASS | 每个后续Gate任务重新验证 |

## 3. Gate结论

```text
GATE_A_OVERALL_STATUS = BLOCKED
V3-8_START_STATUS = BLOCKED
```

只有全部mandatory Gate A标准转为PASS后，Planner才可以基于届时最新的`main`生成
独立的 `V3-8_SPECIALIZED_VERIFIER_PLAN.md`。当前不得提前编写或执行V3-8。

## 4. 当前收口顺序

```text
Gate A
→ V3-8 Specialized Verifier
→ shared Registry / Container / Workflow / Service integration
→ V3-9 Supervisor / enhanced_v2
→ reviewed real-golden evaluation
→ V3-11 UI / Report
→ V3-12 Hardening / Release
```

`standalone-ready`只表示专业模块可独立调用，不等于共享Container已经装配，也不等于
`enhanced_v2-ready`。当前稳定工作流仍为`mvp_v1`。

## 5. Legal收口文档入口

- 候选字段审批：[V03_LEGAL_CONTRACT_DELTA.md](V03_LEGAL_CONTRACT_DELTA.md)
- 决策字段分类：[V03_LEGAL_FIELD_REQUIREMENT_MATRIX.md](V03_LEGAL_FIELD_REQUIREMENT_MATRIX.md)
- Runtime Prompt接入：[V03_LEGAL_PROMPT_SPEC.md](V03_LEGAL_PROMPT_SPEC.md)
- Retriever缺口：[V03_LEGAL_RETRIEVAL_GAP_REPORT.md](V03_LEGAL_RETRIEVAL_GAP_REPORT.md)
- Verifier规则：[V03_LEGAL_VERIFIER_RULES.md](V03_LEGAL_VERIFIER_RULES.md)
- A—H人工复核：[V03_LEGAL_GOLDEN_REVIEW_CHECKLIST.md](V03_LEGAL_GOLDEN_REVIEW_CHECKLIST.md)

历史实现过程继续由Git历史、Approved Plans和Execution Reports保存，不通过重复的活跃
说明文档继续维护。
