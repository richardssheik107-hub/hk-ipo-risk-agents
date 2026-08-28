# Roadmap — Competition Closure Only

> Status date: `2026-08-28`

本 Roadmap 只记录尚未完成的工作。当前 Gate 状态以 `V0.4_RELEASE_ACCEPTANCE.md` 为准，指标定义以 `COMPETITION_METRIC_PROTOCOL.md` 为准，操作顺序以 `V045_CURRENT_EXECUTION_PLAN.md` 为准。

## 当前立即动作

```text
B: one dominant-failure Fixer → bounded fixed-10 rerun → ALL 79 Development
D: restore immutable inputs → current-main strict revalidation → final-three label-free handoff
C: complete unavailable-observation unit / derivation metadata
E: restore 3/3 accepted real-provider output and collect 6 human reviews
A: rerun readiness/audits; package only after every Gate passes
```

当前 measured status：

```text
B fixed-10 = 10/10 real-LLM; M1 23.33%; M2 18.75%
D M5 70-case formal materialization = PASS recorded
D strict checker / product handoff = PASS implementation
D release revalidation / final-three package = pending local immutable inputs
C1 strict contract = 1/3
E1 accepted = 2/3
M3 = 3/3 exactly 1.0
M4 = 0/6 human reviews
```

## 已关闭，不再扩展

- competition runtime contracts / CI gate；
- governed MarketContext；
- IPOHeatSkill / MarketRegimeSkill；
- bounded Market LLM wiring；
- LLM Final Supervisor implementation；
- deterministic conflict detection；
- one bounded targeted re-check；
- Agent / Tool / Evidence Trace implementation；
- Human Review / Streamlit workspaces；
- 3 real prospectus offline E2E；
- 3-case measured traceability = 1.0；
- A readiness / Blind / provenance / determinism / artifact index / packager；
- Existing Expert Gold inventory 与 Metric-v2；
- Existing-Gold read-only evaluator；
- Role-B constrained Runner/Fixer tooling；
- Role-D governed M5 builder；
- Role-D strict read-only acceptance checker；
- Role-D exact-four-file / exact-70-case / independent metric validation；
- Role-D label-free PR-F product handoff 与 package validator；
- Role-D 70-case formal materialization evidence record。

除非出现回归或直接影响 hard Gate，不再扩架构。

## P0 — B/A：M1/M2 Existing-Gold closure

### Scope freeze

```text
Existing Expert Annotation / Oracle Gold only
+ read-only deterministic normalization
+ real-LLM/code optimization
```

禁止新增 annotation、补 negative、人工重组 Evidence、修改旧 Gold、把未标注项当 negative。

### Gate

```text
M1 official >=0.80; target >=0.85
M2 official >=0.85; target >=0.88
```

### 执行顺序

```text
1. read iter_004 failure_focus
2. one minimal semantic-extraction Fixer
3. bounded fixed-10 rerun
4. max 2-4 targeted rounds
5. larger Development checkpoint
6. ALL 79 Development
7. freeze code / Prompt / evaluator / runtime
8. one-shot ALL 19 Validation
```

详细操作：

```text
docs/V045_ROLE_B_LUNAMAX_AUTOMATION_RUNBOOK.md
docs/V045_CURRENT_EXECUTION_PLAN.md
```

## Release evidence — D：bounded revalidation only

D 不再承担新模型开发。PR #141 已记录 70 个 2024 Validation IPO 的正式 M5 PASS、四个 artifact hashes 与 deterministic resume PASS。

发布前剩余：

```text
1. restore exact frozen PR-E runtime
2. restore exact frozen PR-F runtime
3. restore authorized governed EOD
4. rebuild Role-D artifacts on current main
5. strict checker PASS
6. resume byte-identical
7. fresh-directory byte-identical
8. build final-three package from configs/v045_demo_cases.json
9. validate package and hand off to E/A
```

输入缺失时状态为：

```text
BLOCKED_EXTERNAL_IMMUTABLE_INPUTS
```

不得：

- 重训或重建 PR-F；
- 使用替代行情；
- 反转 score；
- 改 threshold；
- calibration；
- 把 score 称为 probability；
- 访问 2025 Blind outcome。

Role-D v2 high-recall output 仍是 research candidate，等待 A 决议。

## P1 — C：Final Market validation

Final-three 只验证：

```text
explicit governed Market state
complete unavailable-observation metadata
no fabricated numbers
trace accounting
Core-only no crash
```

不新增 ComparableIPOSkill，不补造 industry/PIT proxy。

## P1 — E：Real-provider Final Supervisor / M4

```text
2410.HK / 2460.HK / 1318.HK
accepted real-provider arbitration = 3/3
scope PASS
severity floor preserved
provider call trace complete
M3 =1.0
M4 two independent human reviewers per case
```

当前 2460 honest fallback 不算 accepted；M4 仍为 0/6。

## P1 — A：Integration / release freeze

A 剩余：

1. review B/C/D/E final evidence；
2. verify D strict acceptance and final-three package；
3. latest-main full CI；
4. final-three AI smoke；
5. Blind / provenance / determinism actual PASS；
6. metric dashboard / artifact index；
7. submission ZIP security audit；
8. hard Gate 全绿后 `COMPETITION_READY`。

## P2 — Evidence bbox

保持 optional。只有在不影响 P0/P1 时处理。

## 明确停止的工作

- 新的 M1/M2 人工 Gold；
- broad model tuning / new model families；
- PR-F replacement training；
- score inversion / Validation retuning；
- full Retriever redesign；
- historical industry PIT research；
- broad new market acquisition；
- full 438-case LLM；
- presentation-only expansion；
- proxy/zero fill unavailable market facts。

## Completion condition

```text
M1 >=80%
+ M2 >=85%
+ M3 =100%
+ M4 PASS
+ D current-main strict M5 revalidation PASS
+ D→E final-three label-free package PASS
+ C final Market validation PASS
+ E final real-provider acceptance PASS
+ A final readiness/audit/CI/package PASS
= v0.4.5 COMPETITION_READY
```
