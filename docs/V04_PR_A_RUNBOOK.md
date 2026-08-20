# v0.4 PR-A — Pipeline Lead Execution Runbook

> Owner: **A — Tech Lead / Pipeline**  
> Status: **WEB IMPLEMENTATION READY / LOCAL MATERIALIZATION PENDING**  
> Scope: `PR-A — Document + Oracle Materialization & Coverage`

本文件是 A 负责人执行 PR-A 的操作手册。它不替代 `END_TO_END_CLOSED_LOOP_MASTER_PLAN.md`，而是把 PR-A 的工程步骤、命令、产物和验收条件固定下来。

## 1. A 的目标

A 的任务不是继续优化 Retriever 或 Agent，而是把已经冻结的 Document Intelligence 变成可审计、可复现的建模数据资产：

```text
Official 2020–2024 IPO universe
→ Production batch analysis
→ authoritative V03DocumentRiskSnapshot
→ Production Document Feature Vector
→ Oracle Feature inventory/materialization
→ unified coverage.csv
→ determinism audit
```

最终必须回答：

1. 438 个 official IPO 中 Production Document X 成功多少；
2. 每个失败 case 在哪个 stage 失败、为什么；
3. Oracle Gold 可 materialize 多少；
4. Production ∩ Oracle 的公平交集有多少；
5. 同一输入重跑后 artifact / hash 是否稳定。

## 2. 已在 GitHub 分支完成的工程基础

当前分支已经提供：

```text
scripts/run_v04_pr_a.py
tests/unit/test_v04_pr_a_orchestration.py
tests/unit/test_v04_pr_a_determinism.py
```

`run_v04_pr_a.py` 是薄 orchestration CLI，复用：

```text
ipo_risk.evaluation.batch.run_batch
V04DocumentSnapshotMaterializer
DOCUMENT_FEATURE_MANIFEST_V1
vectorize_document_snapshot(...)
build_oracle_document_features(...)
CompetitionCSVMarketDataProvider.iter_listing_metadata()
```

它不复制 Parser / Retriever / Agent 业务逻辑，也不修改受保护公共 Schema。

## 3. Official cohort 口径

PR-A 必须使用 **official listing year**，不能直接使用旧 document corpus 的 `source_year` / `dataset_split`。

正式口径：

```text
2020–2023 official listing year → development
2024 official listing year      → validation
2025 official listing year      → excluded from PR-A
```

完整 Production 运行时，CLI 会检查 official cohort 数量必须为：

```text
438
```

如果数量漂移，full run fail closed；pilot / diagnostic 可以显式使用 `--limit` 或 `--case-ids`。

## 4. A0 — Freeze execution context

CLI 在任何 Production / Oracle 工作前先生成：

```text
execution_context.json
```

记录：

- git revision；
- PR-A / Document pipeline version；
- `configs/v03_offline.yaml` checksum；
- official bridge checksum；
- prospectus manifest checksum；
- source manifest checksum（如存在）；
- Production Document Feature Manifest hash；
- Oracle Feature Manifest hash；
- Python /关键 package version；
- selected case IDs 与 selection hash；
- `blind_outcomes_included=false`。

本地绝对路径不得写入 artifact。

同一 output directory 的 execution context 如果内容变化，即使使用 `--resume` 也必须 fail closed，不能覆盖旧 provenance。

## 5. 本地运行前置条件

A2 / A3 的 Production 路径需要真实招股书 PDF，因此必须在有本地赛事数据的机器上运行。

运行前确认：

```text
1. repository checkout 位于要执行的固定 commit
2. data/catalog/ipo_official_master_bridge.csv 存在
3. data/catalog/ipo_prospectus_manifest.csv 存在
4. 438 target prospectus PDF 可通过 manifest.relative_path 在 data-root 下找到
5. configs/v03_offline.yaml 未被本地临时修改
6. Python 环境安装项目依赖
7. 2025 blind outcome 不参与 PR-A
```

推荐环境：

### Windows PowerShell

```powershell
python -m pip install -e ".[dev,retrieval-research]"
$env:PYTHONPATH = "src"
```

### Linux / macOS

```bash
python -m pip install -e '.[dev,retrieval-research]'
export PYTHONPATH=src
```

## 6. A1 — CLI 功能

正式入口：

```text
scripts/run_v04_pr_a.py
```

主要参数：

```text
--repo-root
--catalog-dir
--data-root
--output-dir
--config
--limit
--case-ids
--resume
--production-only
--oracle-only
--verify-determinism
```

安全规则：

- official 2025 cohort 不进入 selection；
- Production 只使用 `enhanced_v2` authoritative real result；
- Mock / mvp_v1 / non-real component result 由 Materializer fail closed；
- 一只 IPO 失败不阻断其它 case；
- 所有失败写入 status / coverage；
- existing different content / provenance 永远不能静默覆盖；
- missing Oracle Gold 显式记为 `no_reviewed_gold`，不能从 coverage 消失。

## 7. A2 — 5-case deterministic pilot

不要先跑 438 个。

### Windows PowerShell

```powershell
python scripts/run_v04_pr_a.py `
  --config configs/v03_offline.yaml `
  --data-root "<LOCAL_PROSPECTUS_ROOT>" `
  --output-dir reports/v04_pr_a_pilot `
  --limit 5
```

### Linux / macOS

```bash
python scripts/run_v04_pr_a.py \
  --config configs/v03_offline.yaml \
  --data-root "<LOCAL_PROSPECTUS_ROOT>" \
  --output-dir reports/v04_pr_a_pilot \
  --limit 5
```

Pilot 只验证工程正确性，不根据 5 个 case 修改风险规则、Prompt 或 Retriever。

### Pilot 检查项

至少确认：

```text
execution_context.json             exists
production_analysis/               exists
production_document/snapshots/     created for eligible successful cases
production_features/               created for materialized snapshots
production_status.json             exists
oracle_status.json                 exists
coverage.csv                       one row per selected case
coverage_summary.json              exists
```

允许 partial / failed case，但必须有明确 stage / reason。

## 8. Pilot 第二次运行 / A6 预演

在完全不修改输入和代码的情况下：

```powershell
python scripts/run_v04_pr_a.py `
  --config configs/v03_offline.yaml `
  --data-root "<LOCAL_PROSPECTUS_ROOT>" `
  --output-dir reports/v04_pr_a_pilot `
  --limit 5 `
  --resume `
  --verify-determinism
```

预期：

- existing authoritative snapshot 被 `reused`；
- Production feature artifact 内容不变；
- Oracle content hash 不变；
- coverage hash 可稳定 round-trip；
- `determinism_report.json.passed = true`；
- mismatch count = 0。

如果发生 provenance drift，应失败而不是覆盖。

## 9. A3 — 438-case Production full materialization

只有 Pilot + CI + deterministic rerun 通过后，执行全量：

### Windows PowerShell

```powershell
python scripts/run_v04_pr_a.py `
  --config configs/v03_offline.yaml `
  --data-root "<LOCAL_PROSPECTUS_ROOT>" `
  --output-dir reports/v04_pr_a
```

### Linux / macOS

```bash
python scripts/run_v04_pr_a.py \
  --config configs/v03_offline.yaml \
  --data-root "<LOCAL_PROSPECTUS_ROOT>" \
  --output-dir reports/v04_pr_a
```

Full run 在未提供 `--limit` / `--case-ids` 时会要求 official cohort 正好为 438。

### 运行原则

- 不因单 case 失败中断 batch；
- 不临时修改 Agent / Gold / Feature policy 来“提高成功率”；
- 不把 partial 标成 completed；
- 不删除 failed case；
- 不读取 2025 blind outcome；
- 运行中断后用 `--resume` 继续，不手工覆盖 artifact。

## 10. A4 — Oracle

默认完整命令会同时执行 Oracle。

如果只想先检查 Oracle、且当前 checkout 已包含 `expert_results`：

```powershell
python scripts/run_v04_pr_a.py `
  --output-dir reports/v04_pr_a_oracle_check `
  --oracle-only `
  --limit 5
```

Oracle 不要求覆盖 438。没有 reviewed Gold 的 official case 会明确记录：

```text
oracle_document_available = false
oracle_failure_reason = no_reviewed_gold
```

Oracle 永远不能进入 Production runtime。

## 11. A5 — unified coverage

正式输出：

```text
coverage.csv
coverage_summary.json
```

Coverage 至少包含：

```text
case_id
stock_code
source_year
official_listing_year
dataset_split
production_analysis_status
production_snapshot_status
production_document_available
production_failure_stage
production_failure_reason
production_snapshot_hash
production_feature_hash
production_feature_manifest_hash
oracle_document_available
oracle_failure_reason
oracle_feature_hash
oracle_feature_manifest_hash
oracle_effective_annotation_hash
```

Full run Gate 要求：

```text
coverage rows = 438
case_id unique = true
all selected cases accounted for = true
2025 official cohort rows = 0
silent missing cases = 0
```

成功率不是 PR-A 的硬目标；**可审计覆盖率 100%** 才是硬目标。

## 12. A6 — Full determinism audit

全量完成后在相同 commit / config / input 下重跑：

```powershell
python scripts/run_v04_pr_a.py `
  --config configs/v03_offline.yaml `
  --data-root "<LOCAL_PROSPECTUS_ROOT>" `
  --output-dir reports/v04_pr_a `
  --resume `
  --verify-determinism
```

验收：

```text
Production feature mismatches = 0
Oracle content-hash mismatches = 0
Coverage hash mismatch = 0
Unexpected provenance overwrite = 0
determinism_report.passed = true
```

如果 LLM / nondeterministic path 导致真实 source result 漂移，不能偷偷接受；需要单独记录并决定是否能作为冻结 Production X。

## 13. 输出目录建议

```text
reports/v04_pr_a/
├── execution_context.json
├── production_analysis/
│   ├── cases/
│   ├── run_manifest.json
│   ├── case_summary.csv
│   └── failure_report.csv
├── production_document/
│   └── snapshots/
├── production_features/
│   └── <case_id>.json
├── production_status.json
├── oracle_features/
│   └── <case_id>.json
├── oracle_status.json
├── coverage.csv
├── coverage_summary.json
└── determinism_report.json
```

大型运行结果是否进入 Git，必须遵守 `.gitignore`、数据许可和仓库 artifact policy；默认不要把本地原始 PDF 或大型生成缓存提交进 Git。

## 14. A 与其他成员的接口

### 给 B — Document / Agent

A 提供：

- Production failure stage / reason；
- failing case IDs；
- authoritative result / snapshot provenance。

B 负责判断是否属于 Document Pipeline 真正 bug。除阻断正确性问题外，不在 PR-A 中重新调 Retriever / Agent。

### 给 C — Market Data / PIT

A 提供：

- official case identity；
- official listing year / split；
- Production coverage cohort。

C 不依赖 Production feature 内容即可并行开发 Market-X。

### 给 D — Quant / ML

PR-A PASS 后提供：

- Production Document X；
- Oracle coverage/intersection；
- feature manifest hash；
- failure / missingness semantics。

D 在 PR-D 前不能把缺失 Production feature 当成“风险为零”。

### 给 E — Oracle / Product

A 提供统一 coverage；E 对 Oracle 异常、最终产品集成负责进一步解释。Oracle Gold 不能回流 Production X。

## 15. PR-A PASS Checklist

只有以下条件全部满足，A 才能建议进入 PR-B / PR-D 依赖链：

- [ ] CI 全绿；
- [ ] A0 execution context 已冻结；
- [ ] 5-case Production pilot 已真实运行；
- [ ] Pilot deterministic rerun PASS；
- [ ] official full cohort = 438；
- [ ] 438 cases 全部出现在 coverage；
- [ ] 每个 Production failure 有 stage / reason；
- [ ] Production feature manifest hash 一致；
- [ ] Oracle missing / failed / materialized 状态明确；
- [ ] Production ∩ Oracle intersection count 已冻结；
- [ ] Full determinism report PASS；
- [ ] 2025 blind outcome 未被读取或用于调优。

## 16. 网页端与本地端边界

### GitHub 网页端可以完成

- A0/A1 编排代码；
- official cohort selection governance；
- authoritative Snapshot / Feature 串联；
- Oracle 串联；
- A5 Coverage Builder；
- A6 determinism checker；
- unit / integration-style tests；
- CI；
- Runbook / PR 描述 / code review。

### 必须在有本地数据的环境完成

- A2 真实 5-case PDF pilot；
- A3 真实 438-case Production materialization；
- A6 基于真实生成 artifact 的第二次运行；
- 对本地 PDF 缺失、性能、磁盘与运行时异常的实际排查。

因此网页端代码完成不等于 PR-A 已 PASS。PR-A 的最终 Gate 必须等真实 PDF materialization 结果回来后才能关闭。
