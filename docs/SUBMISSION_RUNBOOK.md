# v0.4.5 Competition Submission Runbook

本 Runbook 是 A 在最终提交阶段使用的可复现操作手册。它只描述当前仓库已经存在的入口和最终 handoff 契约；任何尚未由 B/D/E 产出的结果都保持 missing，不在本文件中补写。

## 1. 基本原则

- 最终状态以 `docs/V0.4_RELEASE_ACCEPTANCE.md` 与 A 生成的 `submission_readiness.json` 为准。
- `COMPETITION_READY` 只能由实测 Gate 得出，不能手工改字符串。
- 2025 Blind y 未授权前不得访问。
- LLM 只负责语义/综合；精确计算仍由确定性 Skill / Python 完成。
- PR-F authentic handoff 不存在时，Model Channel 保持 `unavailable`，不得重训替代。
- Market 缺失必须显式 missing，不补零、不造 proxy。
- 授权招股书、API Key、本地绝对路径不得进入 Git 或 submission bundle。

## 2. 环境安装与基础校验

建议 Python 3.11：

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

上述步骤不得需要真实 LLM Secret 或授权 PDF。

## 3. Secret 与授权 PDF

参考 `.env.example` 设置本地环境变量，真实值不要写入仓库：

```text
IPO_RISK_LLM_API_KEY
IPO_RISK_LLM_BASE_URL
IPO_RISK_LLM_MODEL
IPO_RISK_PROSPECTUS_ROOT
```

三案例 runner 会根据 frozen prospectus catalog 校验 SHA-256、byte size、physical pages；不匹配即 fail closed。

## 4. 三案例 offline smoke

```bash
python scripts/run_v04_role_e_demo.py \
  --config configs/v045_competition_offline.yaml \
  --prospectus-root <AUTHORIZED_PROSPECTUS_ROOT> \
  --output-dir reports/v045_role_e_offline_final
```

验收：

```text
executed_case_count >= 3
all_prospectus_sha256_verified = true
每个 case overall_traceability = 1.0
structured workflow error = 0
blind_2025_y_accessed = false
outcome_labels_accessed = false
```

Offline fallback 不能计为 Gate E1 的 successful remote arbitration。

## 5. 三案例真实 AI Final Supervisor 验收

先配置本地 LLM 变量，再执行：

```bash
python scripts/run_v04_role_e_demo.py \
  --config configs/v045_competition_ai.yaml \
  --prospectus-root <AUTHORIZED_PROSPECTUS_ROOT> \
  --output-dir reports/v045_role_e_ai_final
```

Gate E1 只有在以下条件同时成立时通过：

```text
real remote provider
+ outcome = accepted
+ provider/model/prompt/request/hash/latency trace 完整
+ scope check passed
+ no out-of-scope Risk/Evidence/Conflict reference
+ deterministic severity floor respected
```

每个 case 应生成：

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

## 6. B — Document benchmark handoff

A 不替 B 生成 benchmark。最终目录默认约定为：

```text
reports/v045_role_b/
  document_benchmark_summary.json
  risk_benchmark.csv
  evidence_benchmark.csv
  ai_vs_offline_report.json   # 可由 B/D 的正式评估链产出；A 只消费
```

已有 evaluator 入口：

```bash
python scripts/run_v045_role_b_real_benchmark.py \
  --development-results <GOVERNED_REAL_LLM_DEVELOPMENT_RESULTS_JSONL> \
  --output-dir reports/v045_role_b
```

该 runner 本身**不会调用 LLM**；它只消费已经治理好的 analysis results。真实 LLM Development results 必须由 B 的正式运行链提前产生。

A Gate 读取 evaluator 的真实字段，不把 demo 成功当成指标成功。最终至少需要：

```text
real_llm_cases > 0
external_llm_called = true
risk_target_at_least_80_percent = true
evidence_target_at_least_85_percent = true
blind_2025_outcome_accessed = false
```

## 7. D — Multi-horizon handoff

A 不为 D 生成或重训预测。D 合并最终实现后，A 只要求 handoff 目录包含：

```text
reports/v045_role_d/
  test_predictions.csv
  multi_horizon_results.csv
  evaluation_summary.json
```

`multi_horizon_results.csv` 必须真实包含：

```text
return_1d
return_5d
return_20d
return_60d
```

`evaluation_summary.json` 必须明确记录 2025 Blind y 未访问。若 authentic frozen PR-F handoff 不可恢复，Model Channel 明确 `unavailable` 即可，不得为了打包补训练。

## 8. A — Readiness / Blind / Provenance / Determinism / Artifact Index

B/D/E handoff 就位后执行：

```bash
python scripts/build_v045_submission_readiness.py \
  --role-b-dir reports/v045_role_b \
  --role-d-dir reports/v045_role_d \
  --role-e-dir reports/v045_role_e_ai_final \
  --output-dir reports/v045_submission \
  --require-ready
```

该命令生成：

```text
submission_readiness.json
blind_audit.json
provenance_audit.json
determinism_audit.json
artifact_index.json
```

如果任何 B/C/D/E/A Gate 不满足，`--require-ready` 返回非零并列出 blocker。

### Determinism 的定义

不声称 remote LLM 文本 byte-for-byte 可复现。A 审计的是：

- prospectus SHA / size / page identity；
- deterministic request id；
- governed deterministic facets；
- workflow / trace / conflict / re-check policy identity；
- remote call 的 provider/model/prompt/request/response hash 可审计。

如果有第二次独立 final run，可增加：

```bash
python scripts/build_v045_submission_readiness.py \
  --role-b-dir reports/v045_role_b \
  --role-d-dir reports/v045_role_d \
  --role-e-dir reports/v045_role_e_ai_final \
  --baseline-role-e-dir reports/v045_role_e_ai_repeat \
  --output-dir reports/v045_submission \
  --require-ready
```

此时额外比较 request identity、prospectus SHA 与 parsed chunk count 等确定性 facets。

## 9. 最终 CI

最终 freeze 必须记录 latest-main GitHub Actions 为 green，并在本地重新执行第 2 节基础校验。A 的 readiness JSON 故意把 GitHub CI 记为 `EXTERNAL_CHECK_REQUIRED_AT_FREEZE`，因为本地脚本不能伪造云端 Actions 状态。

## 10. 生成 submission bundle

只有 `submission_readiness.json` 中 `competition_ready=true` 时才允许打包：

```bash
python scripts/package_v045_submission.py \
  --role-b-dir reports/v045_role_b \
  --role-d-dir reports/v045_role_d \
  --role-e-dir reports/v045_role_e_ai_final \
  --a-output-dir reports/v045_submission \
  --output-zip dist/hk_ipo_risk_agents_v045_submission.zip
```

Packager 使用 allowlist，只收录公开源代码/配置/Runbook 与最终结果 handoff；并主动拒绝：

```text
*.pdf
.env
*.pem / *.key
private-key material
sk-* token-like secret
Windows/macOS/Linux 本地绝对路径
```

ZIP 内写入 `submission_manifest.json`，并输出 bundle SHA-256。

## 11. 最终人工检查

机器 Gate 全绿后，A 仍需做一次只读检查：

```text
[ ] main 无未合并的关键 PR
[ ] latest-main CI green
[ ] B real-LLM benchmark 与指标文件齐全
[ ] D 1D/5D/20D/60D 文件齐全
[ ] C final matrix Market trace/missingness 合法
[ ] E 3/3 real-provider Gate E1 accepted
[ ] traceability 3/3 = 1.0
[ ] Blind / provenance / determinism audit PASS
[ ] bundle 内无 PDF / secret / local path
[ ] case reports / reasoning logs / Evidence / Human Review 可展示
[ ] README / Release Acceptance 与实际结果一致
```

只有这一步完成后，才允许发布 `v0.4.5 COMPETITION_READY`。
