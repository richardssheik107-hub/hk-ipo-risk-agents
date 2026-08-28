# v0.4.5 Current Execution Plan — Competition Closure

> Status date: `2026-08-28`
>
> Competition runtime: `v0.4.5`
>
> Metric protocol: `v045_competition_metric_protocol_v2_existing_gold_only`
>
> Current verdict: **NOT YET COMPETITION_READY**

本文件定义当前操作顺序。Gate 唯一状态源是 `V0.4_RELEASE_ACCEPTANCE.md`；指标定义以 `COMPETITION_METRIC_PROTOCOL.md` 为准。

## 1. 当前快照

```text
B fixed-10 iter_004 = 10/10 real-LLM
B M1 = 23.33%
B M2 = 18.75%
B dominant failure = semantic_extraction_miss

D 70-case M5 materialization = PASS recorded
D strict checker / product handoff = PASS implementation
D current-main release revalidation = pending local immutable inputs
D→E final-three package = pending materialization

E1 accepted = 2/3; 2460 scope-blocked
C1 strict observation contract = 1/3
M3 traceability = 3/3 exactly 1.0
M4 human reviews = 0/6
```

当前主顺序：

```text
B: one dominant-failure Fixer → bounded fixed-10 rerun → ALL 79 Development
D: no new modeling；restore immutable inputs → strict current-main revalidation → final-three handoff
C/E: close strict C1, E1 and M4 without weakening contracts
A: rerun readiness/audits → package only when every hard Gate passes
```

## 2. Role B — constrained Runner / Fixer

### 2.1 frozen fixed-10 source

```text
reports/v045_role_b/fixed10_development_subset.json
```

不存在时只生成一次：

```bash
python scripts/run_v045_role_b_iteration.py --subset-only
```

正常一轮：

```bash
python scripts/run_v045_role_b_iteration.py --iteration auto
```

已经完成 10/10 real-LLM、仅 evaluator/summary 失败时：

```bash
python scripts/recover_v045_role_b_iteration.py --iteration <existing_iteration_id>
```

恢复不得增加外部 LLM 调用，期望：

```text
external_llm_calls_added = 0
```

完整 Runner prompt 与历史 smoke 参考公司见：

```text
docs/V045_ROLE_B_LUNAMAX_AUTOMATION_RUNBOOK.md
```

### 2.2 唯一允许的优化循环

```text
Runner
→ score
→ dominant failure
→ STOP
→ one short Fixer
→ one minimal patch + regression test
→ STOP
→ next Runner
```

固定要求：

- 不新增 Gold；
- 不修改旧专家答案；
- 不把 `UNJUDGED` 当 negative；
- 不同时修多类 failure；
- 不打开 2024 Validation；
- 不访问 2025 Blind outcome；
- 不做 broad Retriever rewrite。

### 2.3 B closure

```text
fixed-10 internal target:
M1 >=0.80
M2 >=0.85

formal Development:
ALL 79 evaluable cases
M1 official >=0.80; target >=0.85
M2 official >=0.85; target >=0.88
```

完成 ALL 79 后冻结 code、Prompt、Retriever config、schema、Verifier、evaluator、Existing-Gold manifest、provider/model settings；随后只允许一次 ALL 19 Validation。

## 3. Role D — release revalidation, not model development

### 3.1 已完成

PR #141 在 2026-08-27 记录：

```text
2024 Validation = 70 IPOs
governed EOD = 433,776 rows / 438 target IPOs
D1_multi_horizon_evaluation = PASS
blind_2025_y_accessed = false
deterministic --resume = PASS
```

正式四文件：

```text
test_predictions.csv
multi_horizon_results.csv
evaluation_summary.json
ai_vs_offline_report.json
```

记录哈希：

```text
8521dabe3f976e5c532f55fe1571294eb9555ae644a32d524233680af74fa93a
f2d3382f2618e3d328155e9a37e81cd01a156cfc0787c8bc42320237dbb56725
6d542b025e5a9c52285a80fcdde198282c389ebc55773b40b644ccf0b74f7a63
3aab6fc39f75f1c350f92ab329df97c97ca48105235d906f5ef213731f180c94
```

当前 main 已有：

```text
M5 builder
strict read-only acceptance checker
exact-four-file / exact-70-case validation
independent return / label / metric recomputation
source provenance validation
complete label-free PR-F product package validator
A readiness four-file contract
```

### 3.2 当前唯一执行路径

在持有完整不可变输入的环境中：

```bash
python scripts/build_v045_role_d_m5.py \
  --pr-f-run-dir reports/v04_pr_f \
  --pr-e-run-dir reports/v04_pr_e \
  --filtered-eod-store data/cache/v04_ipo_eod.csv \
  --filtered-eod-manifest data/cache/v04_ipo_eod.manifest.json \
  --catalog-dir data/catalog \
  --output-dir reports/v045_role_d

python scripts/check_v045_role_d_m5.py \
  --role-d-dir reports/v045_role_d \
  --pr-f-run-dir reports/v04_pr_f \
  --pr-e-run-dir reports/v04_pr_e \
  --filtered-eod-store data/cache/v04_ipo_eod.csv \
  --filtered-eod-manifest data/cache/v04_ipo_eod.manifest.json \
  --catalog-dir data/catalog \
  --output reports/v045_role_d_acceptance/acceptance.json
```

验收必须读取 JSON verdict，不能只看文件存在或 builder 退出码。

随后执行两次确定性复验：

```text
same-directory --resume byte-identical
fresh-directory rebuild byte-identical
```

### 3.3 D→E final-three handoff

脚本可直接读取 canonical demo manifest：

```bash
python scripts/build_v04_pr_f_product_handoff.py \
  --source-pr-f-dir reports/v04_pr_f \
  --case-list configs/v045_demo_cases.json \
  --output-dir reports/v045_pr_f_product_handoff_final3
```

必须恰好包含：

```text
ipo_2024_02410
ipo_2024_02460
ipo_2024_01318
```

Package 只允许 frozen score、case identity 与 frozen SHAP drivers；不得含 `raw_return_5d`、`poor_performer_5d`、actual return/label 或 2025 Blind outcome。

若完整 PR-E / PR-F runtime 或授权 EOD 不可恢复：

```text
BLOCKED_EXTERNAL_IMMUTABLE_INPUTS
```

不得重训、重建、联网替代行情、改 frozen manifest 或 fake-fill。

### 3.4 v2 candidate

Role-D v2 high-recall output 仍是 research candidate，等待 A 治理决策。它不能静默替换 frozen PR-F，也不影响当前 D1 记录口径。

## 4. Role C / E final matrix

### C

只关闭 final-three strict Market contract：

- explicit market state；
- governed trace；
- unavailable observation 仍有完整 unit / derivation；
- Market LLM 不造数字；
- 不新增不可证明 PIT 的 proxy。

### E

最终要求：

```text
2410.HK / 2460.HK / 1318.HK
real provider
accepted 3/3
gate_e1.satisfied = true 3/3
scope PASS
severity floor preserved
provider/model/prompt/request/hash/latency complete
M3 = 1.0 3/3
M4 human review PASS
```

当前 2460 两次 scope violation 后 honest fallback，不计 E1 success。

## 5. Role A final integration

只有以下全部满足后才运行 final package：

```text
B ALL 79 M1/M2 PASS
D strict current-main revalidation PASS
D→E final-three package PASS
C1 3/3
E1 3/3
M3 3/3 = 1.0
M4 PASS
latest-main CI green
Blind / provenance / determinism PASS
artifact index / security audit PASS
```

A 不得因 D 已有历史 PASS 记录而跳过 current-main release revalidation，也不得因其他 lane 未完成而把 D 重新描述成“实现缺失”。

## 6. 当前 hard Gate

```text
B0 Existing-Gold audit              PASS
B1 M1 real-LLM Development          OPEN / P0
B2 M2 Evidence Coverage             OPEN / P0
D1 M5 materialization               PASS RECORDED
D1 current-main release revalidation PENDING LOCAL IMMUTABLE INPUTS
D→E final-three product package     PENDING LOCAL IMMUTABLE INPUTS
C1 final Market validation          OPEN / P1
E1 final 3-case real provider       OPEN / P1
E2 explanation quality              OPEN / P1
A1 final readiness/package          OPEN / P1
```

## 7. 明确不做

```text
任何新的 M1/M2 人工 Gold
Gold 修改或补 negative
Validation tuning
2025 Blind outcome access
full 438-case LLM run
broad model search
PR-F replacement training
score inversion or calibration
ComparableIPOSkill
presentation-only expansion
无 PIT 证据的 market proxy
```
