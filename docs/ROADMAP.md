# Roadmap — Competition Closure Only

本 Roadmap 只记录**尚未完成的工作**。已完成能力不再重复规划；当前 Gate 状态以 `V0.4_RELEASE_ACCEPTANCE.md` 为准。

## 已关闭，不再扩展

- competition runtime contracts / CI gate；
- governed MarketContext；
- IPOHeatSkill / MarketRegimeSkill；
- Market Intelligence AI runtime wiring；
- bounded Market LLM interpretation；
- LLM Final Supervisor implementation；
- deterministic conflict detection；
- one bounded targeted re-check；
- Agent / Tool / Evidence Trace；
- Human Review；
- 五个 Streamlit competition workspaces；
- 3 个真实招股书 offline E2E matrix；
- 三案例 measured traceability = 1.0。

除非出现回归或直接影响比赛 Gate，不再对这些模块做架构探索。

## P0 — B：Document quality closure

当前 measured offline governed baseline：

```text
10 Development PDFs      10/10 完整性验证并完成分析
Risk Precision           0.0%
Risk Recall              0.0%
Risk F1                  0.0%
Evidence Recall@5        20.0%
Real LLM cases           0
```

下一步必须固定同一 Development benchmark：

```text
same cases / same Gold / same evaluator
→ real provider Legal + Business
→ freeze prediction first
→ evaluate
→ classify failure:
   retrieval miss
   structured semantic miss
   candidate conflict
   verifier mismatch
   evidence ranking miss
→ only Development-only targeted remediation
→ rerun same protocol
```

禁止：

- 为指标调 2024 Validation；
- 修改 Gold 迎合预测；
- 把无风险输出当 true negative 除非 evaluator 明确定义；
- 让 LLM 直接做权威数值计算；
- 为提高 recall 放松 Evidence scope。

2460/1318 是重要失败案例：已有 Evidence，但没有形成正式风险项，应优先检查 `Evidence → candidate → RiskItem / Verifier`。

## P0 — D：Multi-horizon submission package

D 直接使用已有 outcome foundation，补齐比赛最小结果包：

```text
return_1d
return_5d
return_20d
return_60d
```

输出：

```text
test_predictions.csv
multi_horizon_results.csv
evaluation_summary.json
ai_vs_offline_report.json
```

要求：

- 保留 2020–2023 Development / 2024 Validation / 2025 Blind 隔离；
- frozen 5D policy 不重写；
- 5D significant-drop 作为高权重分析项，但其他 horizon 也必须输出；
- PR-F authentic per-case signal 若存在则 hash-bound 消费；若不存在，写 `unavailable`；
- 不因旧 PR-F AUC 弱而重训/反转分数。

## P1 — E：Final matrix real-provider acceptance

对已经完成 offline 的同一 3-case matrix：

```text
2410.HK
2460.HK
1318.HK
```

在最终 AI config + real provider 下验证：

- Final Supervisor structured synthesis 成功；
- provider/model/prompt/request/hash/latency trace 完整；
- synthesis 只能引用 in-scope Risk/Evidence/Conflict；
- deterministic severity floor 不被降低；
- provider 失败仍正确 fallback，但失败 run 不计 successful LLM arbitration。

E 不修 B 的风险抽取，也不补 D 的模型/Outcome。

## P1 — C：Final case Market validation

C 主体代码已完成，只需确保最终案例环境中：

- PR-B Core materialization 可解析；
- Core-only 时不 crash；
- Extended 有真实 governed artifact 才启用；
- industry return 不可用时保留 PIT missing reason；
- Market LLM 不生成输入里没有的数字；
- Market trace 的 namespaced evidence/accounting 完整。

不再新增 ComparableIPOSkill，除非上述 P0/P1 全关闭且还有明确时间与 PIT-safe 定义。

## P1 — A：Integration / Release / Submission

A 不再开发新的业务 Agent。A 的剩余任务：

1. 审 B/C/D/E 的小 PR，保护公共 contract；
2. 每次合并后运行 CI / contract gate / relevant real-case smoke；
3. 保持 `V0.4_RELEASE_ACCEPTANCE.md` 与 main 同步；
4. 最终关闭：
   - full CI；
   - blind audit；
   - provenance / determinism；
   - artifact completeness；
   - runbook；
   - submission archive；
   - release note；
5. 只有 hard Gate 真实通过后打 `COMPETITION_READY`。

## P2 — Evidence bbox grounding

当前 page grounding 已可用，但 parser 不产出 bbox。若最终 demo 需要精确高亮：

- B 负责 parser/Evidence grounding；
- A 审核 schema/version/hash/provenance 影响；
- UI 禁止自己猜 bbox；
- frozen PR-G/PR-H 不直接原地重写。

它低于 B real-LLM benchmark、D multi-horizon、E final remote validation 的优先级。

## 明确停止的工作

比赛提交前不做：

- broad model tuning / new model families；
- full Retriever redesign；
- historical industry PIT research；
- broad new market acquisition；
- full 438-case LLM run；
- 大规模 feature search；
- 纯故事/装饰型 UI；
- 用 proxy/zero 填 unavailable market facts。

## Completion condition

Roadmap 结束条件不是“代码功能足够多”，而是：

```text
B quality evidence closed
+ D multi-horizon artifacts closed
+ E real-provider final matrix closed
+ A final release/submission gate closed
= v0.4.5 COMPETITION_READY
```
