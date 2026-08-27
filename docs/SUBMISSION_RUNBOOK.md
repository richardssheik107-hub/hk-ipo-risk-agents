# v0.4.5 Competition Submission Runbook

本 Runbook 是最终提交阶段的可复现操作手册。当前状态以 `V0.4_RELEASE_ACCEPTANCE.md` 为准；指标定义以 `COMPETITION_METRIC_PROTOCOL.md` / `configs/v045_competition_metric_protocol.json` 为准；当前操作层顺序以 `V045_CURRENT_EXECUTION_PLAN.md` 为准。

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
- legacy-only `Recall@5` 不得被解释成 Evidence official PASS；
- Role-B 当前只使用 constrained Runner/Fixer 分离，不给 Codex 开放式全仓优化任务。

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

M1/M2：

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

Role-B real-PDF runner 还要求：

```text
IPO_RISK_PROSPECTUS_ROOT=<AUTHORIZED_PROSPECTUS_ROOT>
```

该变量必须指向真实存在的授权招股书根目录。API Key / Base URL / 本机绝对路径只来自本地环境，不得提交 Git。

PowerShell 临时设置示例：

```powershell
$env:IPO_RISK_PROSPECTUS_ROOT="D:\path\to\authorized\prospectus_root"
Test-Path $env:IPO_RISK_PROSPECTUS_ROOT
```

必须返回 `True`。

## 4. Existing Expert Gold inventory

```text
annotation inventory   101
valid annotations      100
official materialized   98

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

禁止：新人工标注、补 risk family、补 negative case、人工重做 Evidence Group、修改专家旧答案、把未标注项当 negative。

## 5. Role B/A — Existing-Gold coverage audit

```bash
python scripts/audit_v045_existing_gold.py --output-dir reports/v045_role_b
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

## 6. Role B — fixed-10 real-LLM Development loop

### 6.1 当前本地状态

2026-08-27 本地 `iter_004` 已完成 frozen fixed-10 10/10 real-LLM 与 Existing-Gold debug 评分：

```text
M1 = 23.33%
M2 = 18.75%
dominant failure = semantic_extraction_miss
Validation opened = false
2025 Blind accessed = false
```

招股书根目录与 governed `case_id` serialization blocker 已解除。该结果未达到 fixed-10 内部目标，也不是 ALL 79 Development 正式 PASS；下一轮仍保持 Runner/Fixer 分离和单一 dominant-failure 归因。

### 6.2 正式 fixed-10 source of truth

```text
reports/v045_role_b/fixed10_development_subset.json
```

第一次且仅第一次需要生成：

```bash
python scripts/run_v045_role_b_iteration.py --subset-only
```

如果 subset JSON 已存在，不重新生成、不重新选择公司。

### 6.3 每轮运行

```bash
python scripts/run_v045_role_b_iteration.py --iteration auto
```

脚本自动执行：

```text
real-runtime preflight
-> fixed 10 Development cases
-> sequential real-LLM run
-> resume-safe persistence
-> analysis_results.jsonl
-> Existing-Gold evaluator
-> M1 / M2 / Recall@K
-> failure taxonomy
-> previous-iteration delta
```

正常只读：

```text
iteration_summary.json
failure_focus.json
```

### 6.4 历史 smoke 参考公司

以下只用于环境 smoke/人工核对，不覆盖当前 Metric-v2 自动生成 subset：

```text
1167.HK 加科思─B
1942.HK MOG Holdings
1961.HK 九尊数字互娱
9600.HK 新纽科技
9633.HK 农夫山泉
9898.HK 微博─SW
6698.HK 星空华文
9863.HK 零跑汽车
2451.HK 绿源集团控股
2517.HK 锅圈
```

完整公司表与行业信息见 `V045_CURRENT_EXECUTION_PLAN.md`。

### 6.5 Runner prompt

Runner 只做执行：

```text
执行现有 fixed-10 runner。
不要扫描仓库，不要修改代码，不要重构，不要自动进入 Fixer。
完成后只读取 iteration_summary.json 和 failure_focus.json。
返回 M1/M2/Recall@K、completed/real_llm/failed、dominant failure 后停止。
如果 BLOCKED，只返回第一个 blocker。
```

完整可复制版本及 `IPO_RISK_PROSPECTUS_ROOT` 恢复 prompt：

```text
docs/V045_ROLE_B_LUNAMAX_AUTOMATION_RUNBOOK.md
```

### 6.6 Runner/Fixer 分离

```text
Runner
-> score
-> dominant failure
-> STOP
-> Fixer: one dominant failure + one minimal patch + regression test
-> STOP
-> next Runner iteration
```

不要在同一长任务里边跑边调。

### 6.7 防过拟合节奏

```text
fixed-10 baseline
-> 2-4 targeted rounds maximum
-> larger Development checkpoint
-> ALL 79 Development
-> freeze
-> one-shot ALL 19 Validation
```

fixed-10 内部目标 M1>=0.80 / M2>=0.85，只是 debug target，不是比赛 PASS。

### 6.8 Full Development handoff

ALL 79 Development 达标后冻结 code / Prompt / evaluator / manifest / runtime，然后才允许 one-shot 19 Validation。

最终 B handoff 至少：

```text
existing_gold_evaluable_manifest.json
document_benchmark_summary.json
risk_benchmark.csv
evidence_benchmark.csv
ai_vs_offline_report.json
```

## 7. Role D — M5 Multi-horizon handoff

前置：

```text
reports/v04_pr_e/{run_manifest.json,baseline_results.json,value_diagnostic.json}
reports/v04_pr_f/{run_manifest.json,model_results.json,model_comparison.json}
data/cache/{v04_ipo_eod.csv,v04_ipo_eod.manifest.json}
```

若 filtered store 尚未生成：

```bash
python scripts/build_v04_ipo_eod_store.py
```

生成：

```bash
python scripts/build_v045_role_d_m5.py
```

输出：

```text
reports/v045_role_d/test_predictions.csv
reports/v045_role_d/multi_horizon_results.csv
reports/v045_role_d/evaluation_summary.json
reports/v045_role_d/ai_vs_offline_report.json
```

必须包含 `return_1d/5d/20d/60d`，primary `significant_drop_5d = return_5d <= -0.10`。

## 8. 三案例 offline smoke

```bash
python scripts/run_v04_role_e_demo.py \
  --config configs/v045_competition_offline.yaml \
  --prospectus-root <AUTHORIZED_PROSPECTUS_ROOT> \
  --output-dir reports/v045_role_e_offline_final
```

验收：3 cases executed、PDF integrity PASS、traceability=1.0、Blind=false、outcome labels=false。

## 9. 三案例真实 AI Final Supervisor / M3

1167.HK 单案例 real-provider smoke 已通过。最终 E1 仍需 2410 / 2460 / 1318 三案 3/3：

```bash
python scripts/run_v04_role_e_demo.py \
  --config configs/v045_competition_ai.yaml \
  --prospectus-root <AUTHORIZED_PROSPECTUS_ROOT> \
  --output-dir reports/v045_role_e_ai_final
```

E1：real remote provider + accepted + complete call trace + scope PASS + severity floor respected。

M3：final real-provider matrix 每案 `overall_traceability=1.0`。

## 10. Role E — M4 Explanation Quality

沿用当前 E/A final explanation-quality 方案，不增加新的 M1/M2 人工标注任务。

## 11. C — final Market trace validation

最终 AI matrix 必须有 explicit market channel state，并且每个 Market event 有 governed namespaced Evidence/Calculation 或 explicit no-evidence reason。真实 missing 合法，zero/proxy 不合法。

## 12. A — final readiness / audit / artifact index

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

`--latest-main-ci-passed` 只能在本节要求的 latest-main CI 与基础 validators 已真实通过后使用；它是显式 freeze attestation，不能用于普通 dry run 或绕过失败测试。

必须确认：

```text
metric_protocol_version = v045_competition_metric_protocol_v2_existing_gold_only
new_manual_annotations_added = false
existing_gold_modified = false
M1 >=0.80
M2 >=0.85
```

## 13. Determinism

不要求 remote LLM 文本 byte-for-byte deterministic；要求 prospectus identity、request identity、governed deterministic facets、provider/model/prompt/request/response hash 可审计。

## 14. 最终 CI

最终 freeze 必须 latest-main GitHub Actions green，并重新运行基础 validators。

## 15. 生成 submission bundle

只有 `submission_readiness.json.competition_ready=true` 才允许：

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
[x] Existing-Gold manifest + source hash 齐全
[x] single-case real-provider smoke PASS
[x] fixed-10 runner available
[x] constrained Runner operating procedure documented

[x] IPO_RISK_PROSPECTUS_ROOT configured for measured fixed-10 run
[x] fixed-10 debug baseline produced
[ ] ALL 79 Development benchmark produced
[ ] M1 >=80%
[ ] M2 >=85%
[ ] Validation one-shot only
[ ] M3 real final traceability =100%
[ ] M4 explanation-quality PASS
[ ] M5 1D/5D/20D/60D complete
[ ] C final Market trace valid
[ ] E real-provider 3/3 accepted
[ ] Blind / provenance / determinism PASS
[ ] main CI green
[ ] bundle contains no PDF / secret / local path
[ ] README / Acceptance / Protocol 与真实结果一致
```

全部完成后才允许发布 `v0.4.5 COMPETITION_READY`。
