# v0.4.5 Competition Submission Runbook

本 Runbook 是最终提交阶段的可复现操作手册。当前状态以 `V0.4_RELEASE_ACCEPTANCE.md` 为准；指标定义以 `COMPETITION_METRIC_PROTOCOL.md` / `configs/v045_competition_metric_protocol.json` 为准。

## 1. 基本原则

- `COMPETITION_READY` 只能由实测 Gate 得出；
- final metric artifact 必须记录 `metric_protocol_version=v045_competition_metric_protocol_v2_existing_gold_only`；
- M1/M2 只允许使用比赛收尾前已经存在并冻结的 Expert Annotation / Oracle Gold；
- 不新增人工 Gold，不修改旧 Gold，不把 `UNJUDGED` 当 negative；
- 2024 Validation 不做 post-hoc tuning；2025 Blind y 未授权前不得访问；
- LLM 只负责语义/综合，精确计算由 deterministic Skill/Python 完成；
- PR-F authentic handoff 不存在时 Model Channel 保持 `unavailable`；
- Market 缺失显式 missing，不补零、不造 proxy；
- 授权 PDF、API Key、本地绝对路径不得进入 Git 或 submission bundle；
- legacy-only `Recall@5` 不得被解释成 Evidence official PASS。

## 2. Metric Protocol freeze check

确认：

```text
docs/COMPETITION_METRIC_PROTOCOL.md
configs/v045_competition_metric_protocol.json
```

Protocol ID：

```text
v045_competition_metric_protocol_v2_existing_gold_only
```

M1/M2 核心：

```text
M1 Existing-Gold Risk Accuracy >=0.80
   project target >=0.85

M2 Existing-Gold Evidence Coverage Recall >=0.85
   project target >=0.88
   Recall@1/@3/@5/@10/@20 diagnostics only
```

## 3. 环境安装与基础校验

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev,retrieval-research]"
pytest -q
python -m compileall -q app src scripts
python scripts/validate_project.py
python scripts/validate_competition_data.py
python scripts/validate_competition_runtime.py
```

真实 AI runtime 当前验证配置：

```text
IPO_RISK_LLM_PROVIDER=openai_responses
IPO_RISK_LLM_MODEL=ark-code-latest
IPO_RISK_LLM_TIMEOUT_SECONDS=300
IPO_RISK_LLM_MAX_RETRIES=0
```

API Key / Base URL 只能来自本地环境变量，不得提交 Git。修改用户级环境变量后必须重启终端/前端进程。

## 4. Existing Expert Gold inventory

项目已有 Gold inventory：

```text
annotation inventory   101
valid annotations      100
official materialized   98
```

只读 audit 已完成：

```text
evaluable Development cases = 79
evaluable Validation cases  = 19
primary positive risk units = 128
primary evidence units      = 217
```

Primary support：

```text
cash_burn_pressure         16
customer_concentration     32
redemption_rights          39
supplier_concentration     41
related_party_transaction   0 -> NOT_EVALUABLE_FROM_EXISTING_GOLD
```

本阶段禁止：

```text
新人工标注
补 risk family
补 negative case
人工重做 Evidence Group
修改专家旧答案
把未标注项当不存在
```

## 5. Role B/A — Existing-Gold coverage audit

标准命令：

```bash
python scripts/audit_v045_existing_gold.py \
  --output-dir reports/v045_role_b
```

当前 frozen audit manifest hash：

```text
fcd12d34fcc64853ed778d0026b1e2c943a863549cd1652c6ced7c6145214d1c
```

输出：

```text
reports/v045_role_b/existing_gold_evaluable_manifest.json
reports/v045_role_b/existing_gold_coverage_summary.json
reports/v045_role_b/existing_gold_risk_units.csv
reports/v045_role_b/existing_gold_evidence_units.csv
```

治理必须保持：

```text
new_manual_annotations_added=false
existing_gold_modified=false
blind_2025_outcome_accessed=false
```

19 个 Validation case 在 audit 中被统计不等于打开 Validation evaluator。

## 6. Role B — fixed-10 real-LLM Development optimization loop

当前快速开发流程已被固定成单脚本，避免 Codex 每轮扫描仓库、读取大日志或自行改变执行步骤。

第一次固定 10 家：

```bash
python scripts/run_v045_role_b_iteration.py --subset-only
```

每轮运行：

```bash
python scripts/run_v045_role_b_iteration.py --iteration auto
```

脚本自动执行：

```text
real-runtime preflight
-> fixed 10 Development cases
-> sequential real-LLM run
-> resume-safe per-case persistence
-> analysis_results.jsonl
-> Existing-Gold evaluator
-> M1 / M2 / Recall@K
-> failure taxonomy
-> previous-iteration delta
```

正常迭代只需要关注：

```text
iteration_summary.json
failure_focus.json
```

大体量 subprocess output 留在 gitignored 本地日志，不应直接输入 Codex 上下文。

建议 Codex Runner 指令：

```text
只执行 python scripts/run_v045_role_b_iteration.py --iteration auto。
不要扫描仓库，不要修改代码，不要分析完整日志。
完成后只读取 iteration_summary.json 和 failure_focus.json。
```

建议 Codex Fixer 指令：

```text
只读取 failure_focus.json。
只处理 dominant failure。
只读直接相关模块和测试。
做一个最小修改 + regression test 后停止。
不要运行 Validation，不要修改 Existing Gold。
```

详细 workflow：

```text
docs/V045_ROLE_B_FIXED10_ITERATION_WORKFLOW.md
```

### 防过拟合节奏

固定 10 家不应无限迭代。建议：

```text
fixed-10 2-4 rounds
-> larger Development checkpoint
-> 若失败模式一致则继续 fixed-10
-> ALL 79 Development
-> freeze
-> one-shot 19 Validation
```

固定 10 家的 `--case-ids` / debug subset 结果永远不能声称正式比赛 PASS。

### M1 required output

`document_benchmark_summary.json` 至少包含：

```text
metric_protocol_version = v045_competition_metric_protocol_v2_existing_gold_only
existing_gold_source
existing_gold_source_hash_or_manifest
real_llm_cases > 0
external_llm_called = true
risk_extraction.evaluable_positive_count
risk_extraction.correct_positive_count
risk_extraction.official_aligned_accuracy
risk_extraction.per_risk
new_manual_annotations_added = false
existing_gold_modified = false
blind_2025_outcome_accessed = false
```

Gate：

```text
official_aligned_accuracy >=0.80
```

Project target：`>=0.85`。

### M2 required output

```text
evidence_coverage.evaluable_existing_gold_count
evidence_coverage.covered_existing_gold_count
evidence_coverage.coverage_recall
retrieval_diagnostics.recall_at_1
retrieval_diagnostics.recall_at_3
retrieval_diagnostics.recall_at_5
retrieval_diagnostics.recall_at_10
retrieval_diagnostics.recall_at_20
```

Gate：

```text
Existing-Gold Evidence Coverage Recall >=0.85
```

Primary 不固定 Top-5。工程诊断目标继续是 Candidate Recall@20 >=0.95、Reranked Recall@10 >=0.90。

### Full Development handoff

固定 10 家稳定后必须跑：

```text
ALL 79 evaluable Existing Development cases
```

最终 B handoff：

```text
reports/v045_role_b/
  existing_gold_evaluable_manifest.json
  document_benchmark_summary.json
  risk_benchmark.csv
  evidence_benchmark.csv
  ai_vs_offline_report.json
```

Full Development 达标后冻结 code / Prompt / evaluator / manifest / runtime，然后才允许 one-shot 19 Validation。

## 7. Role D — M5 Multi-horizon handoff

前置条件：

```text
reports/v04_pr_e/{run_manifest.json,baseline_results.json,value_diagnostic.json}
reports/v04_pr_f/{run_manifest.json,model_results.json,model_comparison.json}
data/cache/{v04_ipo_eod.csv,v04_ipo_eod.manifest.json}
```

PR-E / PR-F runtime 必须逐文件匹配 `reports/frozen/` 中的 SHA-256；EOD 必须由授权的 `data/competition/hkshareeodprices.csv` 经 governed filtered-store builder 生成，不得换成网络代理行情。

若 filtered store 尚未生成：

```bash
python scripts/build_v04_ipo_eod_store.py
```

生成 D handoff：

```bash
python scripts/build_v045_role_d_m5.py
```

输出已存在时，只允许对完全一致的内容恢复：

```bash
python scripts/build_v045_role_d_m5.py --resume
```

脚本 fail-closed 检查 2024 Validation、冻结 PR-E/PR-F 哈希、5D return/label 一致性、最少 60 个有效交易日，以及 `blind_2025_y_accessed=false`；不会训练、调参、校准或读取 2025 Blind y。

D 必须输出：

```text
reports/v045_role_d/
  test_predictions.csv
  multi_horizon_results.csv
  evaluation_summary.json
  ai_vs_offline_report.json
```

必须包含：

```text
return_1d
return_5d
return_20d
return_60d
```

Primary：

```text
significant_drop_5d = (return_5d <= -0.10)
```

## 8. 三案例 offline smoke

```bash
python scripts/run_v04_role_e_demo.py \
  --config configs/v045_competition_offline.yaml \
  --prospectus-root <AUTHORIZED_PROSPECTUS_ROOT> \
  --output-dir reports/v045_role_e_offline_final
```

验收：3 cases executed、PDF integrity PASS、traceability=1.0、Blind=false、outcome labels=false。

## 9. 三案例真实 AI Final Supervisor / M3

1167.HK 单案例 real-provider smoke 已通过，证明 runtime 可用；最终 E1 仍需 2410 / 2460 / 1318 三案 3/3。

```bash
python scripts/run_v04_role_e_demo.py \
  --config configs/v045_competition_ai.yaml \
  --prospectus-root <AUTHORIZED_PROSPECTUS_ROOT> \
  --output-dir reports/v045_role_e_ai_final
```

E1：real remote provider + accepted + complete provider/model/prompt/request/hash/latency + scope PASS + severity floor respected。

M3：final real-provider matrix 每案 `overall_traceability=1.0`。

## 10. Role E — M4 Explanation Quality

沿用当前 E/A final explanation-quality 方案。本次 Existing-Gold-only 变更不增加任何新的 M1/M2 人工标注任务。

## 11. C — final Market trace validation

最终 AI matrix 必须有 explicit market channel state，并且每个 Market event 有 governed namespaced Evidence/Calculation 或 explicit no-evidence reason。真实 missing 合法，zero/proxy 不合法。

## 12. A — final readiness / audit / artifact index

所有 handoff 到齐后：

```bash
python scripts/build_v045_submission_readiness.py \
  --role-b-dir reports/v045_role_b \
  --role-d-dir reports/v045_role_d \
  --role-e-dir reports/v045_role_e_ai_final \
  --output-dir reports/v045_submission \
  --require-ready
```

最终 A review 必须确认：

```text
metric_protocol_version = v045_competition_metric_protocol_v2_existing_gold_only
new_manual_annotations_added = false
existing_gold_modified = false
unjudged_as_negative = false or equivalent auditable proof
M1 >=0.80
M2 >=0.85
```

## 13. Determinism

不要求 remote LLM 文本 byte-for-byte deterministic；要求 prospectus identity、request identity、governed deterministic facets、provider/model/prompt/request/response hash 可审计。

## 14. 最终 CI

最终 freeze 必须 latest-main GitHub Actions green，并重新运行基础 validators。

## 15. 生成 submission bundle

只有 `submission_readiness.json.competition_ready=true` 才允许打包：

```bash
python scripts/package_v045_submission.py \
  --role-b-dir reports/v045_role_b \
  --role-d-dir reports/v045_role_d \
  --role-e-dir reports/v045_role_e_ai_final \
  --a-output-dir reports/v045_submission \
  --output-zip dist/hk_ipo_risk_agents_v045_submission.zip
```

Packager 继续拒绝 PDF、secret/private key、token-like material、本地绝对路径。

## 16. 最终人工检查

```text
[x] Existing Expert Gold 未新增/未修改
[x] Existing-Gold evaluable manifest + source hash 齐全
[x] single-case real-provider runtime smoke PASS
[x] fixed-10 Development iteration tooling available
[ ] fixed-10 baseline produced
[ ] ALL 79 Development benchmark produced
[ ] M1 Existing-Gold Accuracy >=80%
[ ] M2 Existing-Gold Evidence Coverage Recall >=85%
[ ] Recall@K 只作为 diagnostics
[ ] Validation 只做 one-shot，不回头调优
[ ] M3 real final traceability =100%
[ ] M4 current explanation-quality Gate PASS
[ ] M5 1D/5D/20D/60D complete
[ ] C final Market trace 合法
[ ] E real-provider Gate E1 3/3 accepted
[ ] Blind / provenance / determinism PASS
[ ] main CI green
[ ] bundle 无 PDF / secret / local path
[ ] README / Acceptance / Protocol 与真实结果一致
```

只有全部完成后，才允许发布 `v0.4.5 COMPETITION_READY`。
