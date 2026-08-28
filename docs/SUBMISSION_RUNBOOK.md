# v0.4.5 Competition Submission Runbook

> Status date: `2026-08-28`

本 Runbook 是最终提交阶段的可复现操作手册。当前状态以 `V0.4_RELEASE_ACCEPTANCE.md` 为准；指标定义以 `COMPETITION_METRIC_PROTOCOL.md` 与 `configs/v045_competition_metric_protocol.json` 为准；操作顺序以 `V045_CURRENT_EXECUTION_PLAN.md` 为准。

## 1. 基本原则

- `COMPETITION_READY` 只能由实测 Gate 得出；
- final metric artifact 必须绑定 Metric-v2；
- M1/M2 只使用收尾前已存在并冻结的 Expert Annotation / Oracle Gold；
- 不新增/修改 Gold，不把 `UNJUDGED` 当 negative；
- 2024 Validation 不做 post-hoc tuning；2025 Blind y 未授权前不得访问；
- uncalibrated model score 不称为 probability；
- PR-F authentic runtime 不存在时 Model Channel = unavailable；
- Market missing 不补零、不造 proxy；
- 授权 PDF、raw EOD、model/cache、API Key、本地绝对路径不得进入 Git 或 bundle；
- Role-B 保持 Runner/Fixer 分离；
- Role-D 保持 frozen PR-E/PR-F、无重训、无 score inversion。

## 2. 安装与基础校验

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
python scripts/validate_v045_role_d_receipt.py
```

最后一条命令是网络无关的 Role-D 历史物化凭据校验：它验证已记录结果与 frozen manifests / Metric Protocol 未漂移，但不替代需要授权 EOD 与完整 frozen runtime 的 live strict rerun。

真实 AI runtime：

```text
IPO_RISK_LLM_PROVIDER=openai_responses
IPO_RISK_LLM_MODEL=ark-code-latest
IPO_RISK_LLM_TIMEOUT_SECONDS=300
IPO_RISK_LLM_MAX_RETRIES=0
IPO_RISK_PROSPECTUS_ROOT=<AUTHORIZED_PROSPECTUS_ROOT>
```

Secret 与绝对路径只存在本地环境。

## 3. Metric Protocol freeze

```text
protocol = v045_competition_metric_protocol_v2_existing_gold_only
M1 >=0.80; target >=0.85
M2 >=0.85; target >=0.88
M3 =1.0
M4 human-review rubric
M5 =1D/5D/20D/60D
significant_drop_5d = return_5d <= -0.10
```

确认：

```text
docs/COMPETITION_METRIC_PROTOCOL.md
configs/v045_competition_metric_protocol.json
```

## 4. Existing-Gold audit

```bash
python scripts/audit_v045_existing_gold.py --output-dir reports/v045_role_b
```

当前 frozen inventory：

```text
101 annotations / 100 valid / 98 official
79 evaluable Development / 19 Validation
128 primary Risk Units / 217 Evidence Units
manifest_hash = fcd12d34fcc64853ed778d0026b1e2c943a863549cd1652c6ced7c6145214d1c
```

必须保持：

```text
new_manual_annotations_added=false
existing_gold_modified=false
blind_2025_outcome_accessed=false
```

## 5. Role B — Development loop

Frozen fixed-10：

```text
reports/v045_role_b/fixed10_development_subset.json
```

不存在时只生成一次：

```bash
python scripts/run_v045_role_b_iteration.py --subset-only
```

每轮：

```bash
python scripts/run_v045_role_b_iteration.py --iteration auto
```

已有 10/10 persisted results、仅 evaluator/summary 失败时：

```bash
python scripts/recover_v045_role_b_iteration.py --iteration <existing_iteration_id>
```

Recovery 必须 `external_llm_calls_added=0`。

当前 debug baseline：

```text
iter_004 = 10/10 real-LLM
M1 = 23.33%
M2 = 18.75%
dominant failure = semantic_extraction_miss
```

执行：Runner → dominant failure → STOP → one short Fixer → one minimal patch/test → STOP → next Runner。达到 fixed-10 内部目标后进入 larger Development、ALL 79、freeze、one-shot ALL 19 Validation。

完整 prompt：`V045_ROLE_B_LUNAMAX_AUTOMATION_RUNBOOK.md`。

## 6. Role D — current-main M5 release revalidation

### 6.1 历史证据边界

PR #141 已记录 2026-08-27 的 70-case M5 PASS、四文件 hashes 与 deterministic resume PASS。该记录证明正式物化曾完成；它不代替 current-main release 环境的 strict revalidation，因为完整 runtime 与授权行情未提交 Git。

提交内的 hash-bound receipt 与校验命令：

```text
reports/frozen/v045_role_d_m5_materialization_receipt.json
docs/V045_ROLE_D_FINAL_CLOSURE.md
```

```bash
python scripts/validate_v045_role_d_receipt.py
```

必须看到 `passed=true` / `verdict=PASS`。Receipt validator 会绑定 frozen PR-E/PR-F hashes、Metric Protocol、四个正式 artifact hashes、70-case/horizon/metric scope 与治理标志，并拒绝本地绝对路径或 secret-like values。它仍不能证明当前机器拥有原始不可变输入，也不能代替本节后续 live build/check。

### 6.2 必需不可变输入

```text
reports/v04_pr_e/run_manifest.json
reports/v04_pr_e/baseline_results.json
reports/v04_pr_e/value_diagnostic.json

reports/v04_pr_f/run_manifest.json
reports/v04_pr_f/model_results.json
reports/v04_pr_f/model_comparison.json

data/cache/v04_ipo_eod.csv
data/cache/v04_ipo_eod.manifest.json
```

每个 runtime 文件必须与 `reports/frozen/` manifest SHA 完全一致。不得通过重训恢复。

若合法 filtered EOD 尚未生成，但存在 catalog-bound 授权 raw EOD：

```bash
python scripts/build_v04_ipo_eod_store.py
```

缺授权输入时停止为 `BLOCKED_EXTERNAL_IMMUTABLE_INPUTS`，不得联网替代。

### 6.3 构建 canonical four-file handoff

```bash
python scripts/build_v045_role_d_m5.py \
  --pr-f-run-dir reports/v04_pr_f \
  --pr-e-run-dir reports/v04_pr_e \
  --filtered-eod-store data/cache/v04_ipo_eod.csv \
  --filtered-eod-manifest data/cache/v04_ipo_eod.manifest.json \
  --catalog-dir data/catalog \
  --output-dir reports/v045_role_d
```

Canonical 目录必须恰好包含：

```text
test_predictions.csv
multi_horizon_results.csv
evaluation_summary.json
ai_vs_offline_report.json
```

### 6.4 严格验收

```bash
python scripts/check_v045_role_d_m5.py \
  --role-d-dir reports/v045_role_d \
  --pr-f-run-dir reports/v04_pr_f \
  --pr-e-run-dir reports/v04_pr_e \
  --filtered-eod-store data/cache/v04_ipo_eod.csv \
  --filtered-eod-manifest data/cache/v04_ipo_eod.manifest.json \
  --catalog-dir data/catalog \
  --output reports/v045_role_d_acceptance/acceptance.json
```

必须确认：

```text
verdict = PASS
passed = true
expected_validation_count = 70
Blind = false
validation_retuning = false
score_direction_inverted = false
```

不能只看 builder exit code、文件存在或 CSV 非空。

### 6.5 Determinism

同一目录：

```bash
python scripts/build_v045_role_d_m5.py --output-dir reports/v045_role_d --resume
```

随后在一个新的空目录用同一输入重建。两次的四文件必须 byte-identical；记录 SHA，不把 runtime bulk 提交 Git。

### 6.6 D→E final-three label-free package

CLI 可直接读取 canonical demo manifest：

```bash
python scripts/build_v04_pr_f_product_handoff.py \
  --source-pr-f-dir reports/v04_pr_f \
  --case-list configs/v045_demo_cases.json \
  --output-dir reports/v045_pr_f_product_handoff_final3
```

必须恰好含：

```text
ipo_2024_02410
ipo_2024_02460
ipo_2024_01318
```

Package 必须只有 case identity、frozen uncalibrated score、frozen SHAP drivers；不得含 actual return、label、`poor_performer_5d` 或 Blind outcome。E 本地运行时将 `IPO_RISK_PR_F_RUN_DIR` 指向该 package。

Role-D v2 high-recall output 仍是 research candidate，未经 A 审批不得替换 frozen PR-F。

## 7. 三案例 offline smoke

```bash
python scripts/run_v04_role_e_demo.py \
  --config configs/v045_competition_offline.yaml \
  --prospectus-root <AUTHORIZED_PROSPECTUS_ROOT> \
  --output-dir reports/v045_role_e_offline_final
```

验收：3 cases executed、PDF integrity 3/3、traceability=1.0、Blind=false、outcome labels=false。

## 8. 三案例真实 AI Final Supervisor / M3

```bash
python scripts/run_v04_role_e_demo.py \
  --config configs/v045_competition_ai.yaml \
  --prospectus-root <AUTHORIZED_PROSPECTUS_ROOT> \
  --output-dir reports/v045_role_e_ai_final
```

E1：real remote provider + accepted + complete call trace + scope PASS + severity floor respected，3/3。Fallback 不计 success。

M3：每案 `overall_traceability=1.0`。

## 9. M4 Explanation Quality

每案至少两名独立 human reviewer；当前 0/6。LLM reviewer 只能 advisory。

## 10. C final Market validation

每个 Market event 必须有 governed namespaced Evidence/Calculation 或 explicit no-evidence reason；unavailable observation 仍需完整 unit / derivation。真实 missing 合法，zero/proxy 不合法。

## 11. A final readiness

所有 handoff 到齐后：

```bash
python scripts/build_v045_submission_readiness.py \
  --role-b-dir reports/v045_role_b \
  --role-d-dir reports/v045_role_d \
  --role-e-dir reports/v045_role_e_ai_final \
  --baseline-role-e-dir reports/v045_role_e_offline_final \
  --output-dir reports/v045_submission \
  --latest-main-ci-passed \
  --require-ready
```

`--latest-main-ci-passed` 只能在 latest-main CI 与 validators 实际通过后使用。

A 在 final package review 中还必须检查 D 的 strict acceptance JSON 与 final-three product package；通用 readiness 的结构检查不能替代 D 的独立 raw-input revalidation。

## 12. Final CI / package

```bash
pytest -q
python -m compileall -q app src scripts
python scripts/validate_project.py
python scripts/validate_competition_data.py
python scripts/validate_competition_runtime.py
python scripts/validate_v045_role_d_receipt.py
```

只有 `submission_readiness.json.competition_ready=true` 才允许：

```bash
python scripts/package_v045_submission.py \
  --role-b-dir reports/v045_role_b \
  --role-d-dir reports/v045_role_d \
  --role-e-dir reports/v045_role_e_ai_final \
  --a-output-dir reports/v045_submission \
  --output-zip dist/hk_ipo_risk_agents_v045_submission.zip
```

Packager 必须拒绝 PDF、secret/private key、token-like material、licensed raw data、本地绝对路径。

## 13. Final checklist

```text
[x] Existing Expert Gold frozen
[x] Existing-Gold audit/evaluator
[x] Role-D M5 implementation / strict checker / product handoff
[x] Role-D 70-case formal materialization recorded
[x] Role-D hash-bound receipt / validator / CI
[x] M3 offline/final traceability evidence =1.0

[ ] B ALL 79 Development
[ ] M1 >=80%
[ ] M2 >=85%
[ ] Validation one-shot only
[ ] D current-main strict revalidation PASS
[ ] D resume + fresh-directory byte-identical
[ ] D→E final-three package PASS
[ ] C strict final Market validation 3/3
[ ] E real-provider 3/3 accepted
[ ] M4 human review PASS
[ ] Blind / provenance / determinism PASS
[ ] latest-main CI green
[ ] bundle contains no PDF / secret / licensed raw data / local path
[ ] README / Acceptance / Protocol 与真实结果一致
```

全部完成后才允许发布 `v0.4.5 COMPETITION_READY`。
