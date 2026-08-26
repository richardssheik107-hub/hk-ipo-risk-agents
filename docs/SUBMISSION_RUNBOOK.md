# v0.4.5 Competition Submission Runbook

本 Runbook 是最终提交阶段的可复现操作手册。当前状态以 `V0.4_RELEASE_ACCEPTANCE.md` 为准；指标定义以 `COMPETITION_METRIC_PROTOCOL.md` / `configs/v045_competition_metric_protocol.json` 为准。

## 1. 基本原则

- `COMPETITION_READY` 只能由实测 Gate 得出，不能手工改字符串；
- final metric artifact 必须记录 `metric_protocol_version=v045_competition_metric_protocol_v1`；
- 2024 Validation 不做 post-hoc tuning；2025 Blind y 未授权前不得访问；
- LLM 只负责语义/综合，精确计算由 deterministic Skill/Python 完成；
- PR-F authentic handoff 不存在时 Model Channel 保持 `unavailable`；
- Market 缺失显式 missing，不补零、不造 proxy；
- 授权 PDF、API Key、本地绝对路径不得进入 Git 或 submission bundle；
- legacy-only `Recall@5` 不得被解释成 metric-v1 的 Evidence official PASS。

## 2. Metric Protocol freeze check

提交/评估前先确认：

```text
docs/COMPETITION_METRIC_PROTOCOL.md
configs/v045_competition_metric_protocol.json
```

Protocol ID：

```text
v045_competition_metric_protocol_v1
```

核心口径：

```text
M1 Risk Accuracy >=0.80
   project target >=0.85
   Positive Recall / Macro F1 guardrails >=0.82

M2 Evidence Group Coverage Recall >=0.85
   Recall@1/@3/@5/@10/@20 secondary only

M3 Traceability =1.0

M4 Explanation Quality
   >=2 human reviewers
   mean >=4.0/5 project target
   formal case minimum >=3.0/5

M5 1D/5D/20D/60D
   significant_drop_5d = return_5d <= -0.10
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

基础校验不得需要真实 LLM Secret 或授权 PDF。

## 4. Secret 与授权 PDF

参考 `.env.example` 本地配置：

```text
IPO_RISK_LLM_API_KEY
IPO_RISK_LLM_BASE_URL
IPO_RISK_LLM_MODEL
IPO_RISK_PROSPECTUS_ROOT
```

真实值不得写入仓库。

## 5. Role B — 先跑旧 fixed real-LLM diagnostic

当前旧 10-case benchmark 保留作为 baseline / error taxonomy 输入。已有 evaluator：

```bash
python scripts/run_v045_role_b_real_benchmark.py \
  --development-results <GOVERNED_REAL_LLM_DEVELOPMENT_RESULTS_JSONL> \
  --output-dir reports/v045_role_b
```

该 runner 本身不会调用 LLM；真实 LLM predictions 必须由 B 正式运行链提前产生。

注意：现有旧 evaluator 的 `Evidence Recall@1/@3/@5` 是 legacy ranking/end-to-end diagnostic，不是 metric-v1 M2 primary。

## 6. Role B — metric-v1 Gold / M1 / M2

B 必须在 Development 完成以下步骤：

```text
1. freeze 20-case target allowlist
2. 2+ reviewer Gold annotation
3. freeze Gold before final prediction evaluation
4. real-LLM run first
5. evaluate M1/M2
6. error taxonomy
7. Development-only remediation
8. rerun same protocol
```

### M1 required output

`document_benchmark_summary.json` 至少包含：

```text
metric_protocol_version = v045_competition_metric_protocol_v1
real_llm_cases > 0
external_llm_called = true
risk_extraction.official_aligned_accuracy
risk_extraction.precision
risk_extraction.positive_recall
risk_extraction.macro_f1
risk_extraction.per_risk
blind_2025_outcome_accessed = false
```

Gate：

```text
official_aligned_accuracy >=0.80
positive_recall >=0.82
macro_f1 >=0.82
```

内部目标 Accuracy >=0.85。

Primary families：

```text
redemption_rights
related_party_transaction
customer_concentration
supplier_concentration
cash_burn_pressure
```

### M2 required output

```text
evidence_coverage.group_coverage_recall
evidence_coverage.gold_group_count
evidence_coverage.covered_group_count
retrieval_diagnostics.recall_at_1
retrieval_diagnostics.recall_at_3
retrieval_diagnostics.recall_at_5
retrieval_diagnostics.recall_at_10
retrieval_diagnostics.recall_at_20
```

Gate：

```text
Evidence Group Coverage Recall >=0.85
```

工程诊断目标：Candidate Recall@20 >=0.95，Reranked Recall@10 >=0.90。Primary metric 不固定 Top-5。

最终 B handoff：

```text
reports/v045_role_b/
  document_benchmark_summary.json
  risk_benchmark.csv
  evidence_benchmark.csv
  ai_vs_offline_report.json
```

## 7. Role D — M5 Multi-horizon handoff

D 必须输出：

```text
reports/v045_role_d/
  test_predictions.csv
  multi_horizon_results.csv
  evaluation_summary.json
  ai_vs_offline_report.json
```

`multi_horizon_results.csv` 必须包含：

```text
return_1d
return_5d
return_20d
return_60d
```

Primary 5D label：

```text
significant_drop_5d = (return_5d <= -0.10)
```

`evaluation_summary.json` 至少：

```text
metric_protocol_version
significant_drop_5d_definition = return_5d <= -0.10
five_day_metrics.precision
five_day_metrics.recall
five_day_metrics.f1
five_day_metrics.pr_auc
five_day_metrics.roc_auc
five_day_metrics.top_10pct_hit_rate
five_day_metrics.top_20pct_hit_rate
five_day_metrics.base_prevalence
blind_2025_y_accessed = false
```

Robustness：Development 5D return bottom-20% cutoff，只从 Development 计算一次并冻结。

赛题没有给 5D 绝对及格线，A 不检查一个虚构的“官方 xx%”；D 必须完整、透明、可复现地比较 base-rate / 可用 baselines。

## 8. 三案例 offline smoke

```bash
python scripts/run_v04_role_e_demo.py \
  --config configs/v045_competition_offline.yaml \
  --prospectus-root <AUTHORIZED_PROSPECTUS_ROOT> \
  --output-dir reports/v045_role_e_offline_final
```

验收：

```text
executed_case_count >=3
all_prospectus_sha256_verified = true
each case overall_traceability =1.0
structured workflow error =0
blind_2025_y_accessed = false
outcome_labels_accessed = false
```

Offline fallback 不能计为 E1 successful remote arbitration。

## 9. 三案例真实 AI Final Supervisor / M3 验收

```bash
python scripts/run_v04_role_e_demo.py \
  --config configs/v045_competition_ai.yaml \
  --prospectus-root <AUTHORIZED_PROSPECTUS_ROOT> \
  --output-dir reports/v045_role_e_ai_final
```

E1：

```text
real remote provider
+ outcome = accepted
+ provider/model/prompt/request/hash/latency complete
+ scope check passed
+ no out-of-scope Risk/Evidence/Conflict
+ deterministic severity floor respected
```

M3：final real-provider matrix `overall_traceability=1.0` for all cases。

每案应生成：

```text
analysis_result.json
final_supervision.json
conflicts.json
rechecks.json
trace_sidecar.json
traceability.json
prospectus_verification.json
agent_reasoning_log.json
agent_reasoning_log.md
case_report.md
gate_e1_evidence.json
```

## 10. Role E — M4 Explanation Quality

对 final formal cases 用至少 2 名人类 reviewer 评分：

```text
Evidence grounding
Logical consistency
Conflict handling
Re-check quality
Final conclusion
```

输出：

```text
reports/v045_role_e_ai_final/explanation_quality.json
```

至少含：

```text
metric_protocol_version
human_reviewer_count
mean_score
minimum_case_score
per_case_scores
```

内部 Gate：mean >=4.0/5，formal case minimum >=3.0/5。LLM reviewer 只能辅助。

## 11. C — final Market trace validation

最终 AI matrix 必须有 explicit market channel state，并且每个 Market event 有 governed namespaced Evidence/Calculation 或 explicit no-evidence reason。缺失 source 可以诚实 missing，不得用 zero/proxy 代替。

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

生成：

```text
submission_readiness.json
blind_audit.json
provenance_audit.json
determinism_audit.json
artifact_index.json
```

Final A review 必须确认 B/D/E artifact 使用 metric-v1；legacy-only target fields 不足以证明 M1/M2/M4/M5。

## 13. Determinism 定义

不声称 remote LLM 文本 byte-for-byte deterministic。审计：

- prospectus SHA/size/page；
- deterministic request id；
- governed deterministic facets；
- workflow/trace/conflict/re-check policy identity；
- provider/model/prompt/request/response hash 可审计。

## 14. 最终 CI

最终 freeze 必须记录 latest-main GitHub Actions green，并重新运行第 3 节基础校验。

## 15. 生成 submission bundle

只有 `submission_readiness.json.competition_ready=true` 时运行：

```bash
python scripts/package_v045_submission.py \
  --role-b-dir reports/v045_role_b \
  --role-d-dir reports/v045_role_d \
  --role-e-dir reports/v045_role_e_ai_final \
  --a-output-dir reports/v045_submission \
  --output-zip dist/hk_ipo_risk_agents_v045_submission.zip
```

Packager 使用 allowlist，拒绝：

```text
*.pdf
.env
*.pem / *.key
private-key material
sk-* token-like secret
local absolute paths
```

## 16. 最终人工检查

```text
[ ] Metric Protocol v1 未在 Validation 后被改口径
[ ] M1 Accuracy >=80% + guardrails PASS
[ ] M2 Evidence Group Coverage Recall >=85%
[ ] Recall@K 只作为 diagnostics 展示
[ ] M3 real final traceability =100%
[ ] M4 explanation_quality.json PASS
[ ] M5 1D/5D/20D/60D complete + -10% 5D metrics
[ ] C final Market trace/missingness 合法
[ ] E real-provider Gate E1 3/3 accepted
[ ] Blind / provenance / determinism PASS
[ ] main CI green
[ ] bundle 无 PDF / secret / local path
[ ] README / Acceptance / Protocol 与真实结果一致
```

只有完成后，才允许发布 `v0.4.5 COMPETITION_READY`。
