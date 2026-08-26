# Competition Hardening and Submission Plan

本文件把赛题要求映射到当前系统能力与验收产物。它不重复 Roadmap；**状态以 `V0.4_RELEASE_ACCEPTANCE.md` 为准**。

## 1. 赛题核心验收维度

系统最终必须用实测材料证明：

- 关键风险抽取质量；
- 关键 Evidence 召回与可定位性；
- Agent / Tool / Evidence 全链路可追溯；
- Financial / Legal / Business / Market / Supervisor 的真实协同；
- 冲突 → 定向复核 → Verifier → 仲裁；
- 基本面 + 市场环境融合；
- 上市后 1D / 5D / 20D / 60D 验证；
- 5D 显著下跌识别作为高权重分析；
- 可运行原型、结果表、推理日志、Evidence、典型案例与人机复核。

内部目标继续采用：

```text
Risk extraction target     >= 80%
Key Evidence Recall target >= 85%
Traceability target        = 100%
```

这些指标必须由 evaluator 实测，不得从 demo 成功推断。

## 2. CH-1 — Multi-horizon validation

**Owner：D；Status：OPEN**

已有 outcome foundation 支持 1D / 5D / 20D / 60D，但 final competition package 尚未闭合。

最低交付：

```text
return_1d
return_5d
return_20d
return_60d
significant_drop_5d (如采用，必须固定定义)
```

结果文件：

```text
test_predictions.csv
multi_horizon_results.csv
evaluation_summary.json
```

规则：

- frozen 5D research policy 不原地改写；
- 2020–2023 Development / 2024 Validation / 2025 Blind 隔离；
- 2024 不做 post-hoc tuning；
- 2025 y 在正式授权前不访问；
- uncalibrated score 不叫 probability。

## 3. CH-2 — Document Intelligence benchmark

**Owner：B；Status：MEASURED FAIL / OPEN**

当前 10-case governed offline baseline：

```text
Risk Precision / Recall / F1    0 / 0 / 0
Evidence Recall@5               20%
Physical-page correctness       100%
Real LLM cases                  0
```

这已经关闭“有没有 benchmark harness”的问题，但暴露了真正质量瓶颈。

下一阶段固定相同 Development cases / Gold / evaluator：

```text
offline prediction
vs
real-LLM prediction
```

至少报告：

- Risk Precision / Recall / F1；
- Evidence Recall@1/@3/@5；
- extraction_failed / needs_review / verifier mismatch；
- Legal semantic accuracy；
- Business semantic accuracy；
- per-risk breakdown；
- failure taxonomy。

只有在 real-LLM measurement 后才允许做 Development-only targeted remediation。

## 4. CH-3 — Market Intelligence

**Owner：C；Status：IMPLEMENTATION CLOSED / FINAL-MATRIX VALIDATION REMAINS**

已经实现：

```text
governed MarketContext
→ IPOHeatSkill
→ MarketRegimeSkill
→ bounded Market LLM interpretation
→ traceable handoff
```

并且 Market real-provider path 已在两只真实 IPO 上验证。

最终只需要确认：

- final 3-case environment 的 PR-B Core 可读取；
- Core-only 不 crash；
- Extended 只有真实 governed artifact 才启用；
- industry mapping 缺失继续 PIT-blocked；
- Market LLM 不生成输入中不存在的数字。

`ComparableIPOSkill` 继续 deferred，不为故事完整而仓促定义。

## 5. CH-4 — Multi-Agent conflict / arbitration / trace

**Owner：E；Status：IMPLEMENTATION CLOSED**

已实现：

```text
Agent outputs
→ deterministic conflict detection
→ one bounded targeted re-check
→ retriever / verifier challenge
→ resolved / partially_resolved / unresolved
→ LLM Final Supervisor
→ deterministic fallback
→ TraceEvent
```

3 个真实 PDF 离线案例全部产生真实 conflict/re-check，measured traceability 均为 1.0。

剩余验收：同一 final matrix 上 real-provider Final Supervisor synthesis 成功。

## 6. CH-5 — Product / Evidence / Human Review

**Owner：E；Status：CLOSED AS PRODUCT IMPLEMENTATION**

五个比赛工作区：

```text
风险指挥中心
Evidence 与 AI 分析
市场与模型
Agent 协作轨迹
人机复核与最终报告
```

Human Review：Accept / Reject / Needs Follow-up + reviewer note，写 sidecar，不修改机器事实。

Evidence Viewer 当前有真实 physical-page grounding；parser 暂无 bbox。若需要精确框选，由 B + A 做 versioned parser/Evidence 改动，UI 不得自己生成坐标。

## 7. CH-6 — Formal competition evaluation / freeze

**Owner：A + B/C/D/E；Status：OPEN**

进入 CH-6 前必须具备：

- B real-LLM benchmark；
- D multi-horizon artifact；
- E final-matrix real-provider synthesis；
- final case Market behavior；
- current main CI green。

CH-6 输出：

```text
risk_benchmark.csv / json
evidence_benchmark.csv / json
ai_vs_offline_report.json
test_predictions.csv
multi_horizon_results.csv
evaluation_summary.json
agent_reasoning_logs
Evidence / Human Review exports
3 case reports
blind_audit.json (or equivalent auditable statement)
provenance / determinism evidence
RUNBOOK
submission artifact index
```

## 8. Current real-case evidence

Offline final matrix：

```text
2410.HK  706 pages  completed  6 conflicts  3 re-checks  traceability 1.0
2460.HK  579 pages  completed  7 conflicts  3 re-checks  traceability 1.0
1318.HK  617 pages  completed  7 conflicts  3 re-checks  traceability 1.0
```

三份 PDF 全部通过 catalog-bound SHA-256 / size / page verification；未读取 outcome labels。

这个矩阵证明工程稳定性和 Multi-Agent trace，不证明 B 的风险抽取质量或 D 的预测效果。

## 9. Submission story 必须与事实一致

允许强调：

- Evidence-first；
- structured LLM；
- deterministic calculations；
- PIT Market facts；
- explicit missingness；
- real conflict / re-check；
- measured traceability；
- Human Review；
- graceful degradation。

禁止宣称：

- 当前 Risk/Evidence 指标已达到 80%/85%，除非 final evaluator 真正证明；
- uncalibrated score 是概率；
- model channel 可用但没有 authentic handoff；
- unavailable industry return 有可靠代理；
- offline Final Supervisor fallback 是成功的 remote LLM arbitration；
- 3-case E2E 成功等于预测准确。

## 10. Scope freeze

提交前明确不再做：

- broad model search；
- large Retriever rewrite；
- broad feature exploration；
- historical industry mapping research；
- full 438-case LLM execution；
- presentation-only feature expansion；
- 为补 UI 重训 frozen PR-F。

任何新增代码必须能直接关闭 `V0.4_RELEASE_ACCEPTANCE.md` 的一个 measured blocker。
