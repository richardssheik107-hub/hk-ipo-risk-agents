# Competition Submission Runbook — Final Closeout

> 状态日期：`2026-08-30`  
> Metric protocol：`v045_competition_metric_protocol_v2_existing_gold_only`  
> Runtime freeze main：`ab3390cc548f3d4ec7f08d5d39350a3c1baf1f0a`

本 Runbook 只描述最后提交步骤。当前实时状态见 `V0.4_RELEASE_ACCEPTANCE.md`，材料清单见 `FINAL_SUBMISSION_STATUS.md`。

## 1. 不可变原则

- Existing Gold immutable；
- `UNJUDGED != negative`；
- real-provider 与 offline 指标分开；
- Validation 只允许 freeze 后 one-shot；
- 2025 Blind outcome 不用于优化；
- fallback 不冒充 real-provider success；
- Market missing 不补 0；
- `uncalibrated_model_score` 不称概率；
- PDF、raw EOD/CSMAR、Secret、raw provider journal、绝对路径不进入 Git/bundle；
- Human Review 是 optional，不是 Release Gate。

## 2. Final Development truth

```text
Best offline ALL79:
M1 = 70/102 = 68.63%
M2 = 103/191 = 53.93%

Real LLM gated ALL79:
M1 = 61/102 = 59.80%
M2 = 93/191 = 48.69%
real_llm_cases = 79/79
```

G2 自定义门槛 M1 `>=80%`、M2 `>=85%` 未达到，因此仓库 `COMPETITION_READY` 仍为 false。不要用 offline 结果替代 real-LLM gated 结果。

## 3. Frozen identity

机器事实源：

```text
reports/v045_role_b/document_benchmark_summary.json
reports/final_status/final_freeze_manifest.json
```

冻结：

```text
main SHA = ab3390cc548f3d4ec7f08d5d39350a3c1baf1f0a
Role-B benchmark SHA = dcc36abd30ec42cd1d6b83bc6d70b2d1aa74f61b
Development tuning = STOP
Validation opened at freeze = false
Blind outcome accessed = false
```

## 4. 基础安装与验证

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev,retrieval-research]"

python -m compileall -q app src scripts
pytest -q
python scripts/validate_project.py
python scripts/validate_competition_data.py
python scripts/validate_competition_runtime.py
python scripts/validate_v045_role_d_receipt.py
python scripts/check_v045_product_runtime.py
python scripts/check_v045_team_clone_ready.py
python scripts/run_market_runtime_audit.py --strict --no-write
python scripts/run_dynamic_model_runtime_audit.py --strict --no-write
python scripts/check_final_product_capabilities.py
```

任何命令失败都先修复非算法/包装问题；不得借机重新打开 Development 调参。

## 5. One-shot Validation

唯一一次执行：

```text
ALL19 2024 Existing-Gold Validation
ONE SHOT
```

执行前确认：

```text
Development optimization stopped
runtime identity frozen
Validation not previously used for tuning
Blind outcome untouched
```

执行后必须写：

```text
reports/final_status/one_shot_validation_receipt.json
```

至少包含：

```text
status
one_shot = true
post_hoc_tuning = false
blind_2025_y_accessed = false
freeze SHA
case count / metric summary
```

执行后禁止根据 Validation 修改 Retriever、Prompt、Agent、Verifier、threshold、model、evaluator。

## 6. Market / Model 授权数据边界

公开仓库只提交 builder / schema / frozen governed artifacts；授权 EOD / CSMAR / prospectus PDF 留在本地。

### Dynamic Market outcome pack

如演示环境有授权 EOD，可本地物化：

```bash
python scripts/build_prior_ipo_outcome_pack.py \
  --data-root <AUTHORIZED_COMPETITION_DATA_ROOT>
```

输出位于 ignored 本地目录，不允许强行 git add。

### Extended Market-X

若使用授权 Extended 数据：

```bash
export IPO_RISK_MARKET_DYNAMIC_EXTENDED_HSI_CSV=<AUTHORIZED_NORMALIZED_HSI>
export IPO_RISK_MARKET_DYNAMIC_EXTENDED_TURNOVER_CSV=<AUTHORIZED_NORMALIZED_TURNOVER>
```

缺少时诚实 `PARTIAL / UNAVAILABLE`，不影响仓库安全边界。

## 7. Final product / capability rehash

最终提交 commit 上运行：

```bash
python scripts/check_final_product_capabilities.py
```

核对：

```text
reports/final_status/product_acceptance.json
reports/final_status/capability_manifest.json
```

禁止手工改两份文件的 hash 或 PASS 状态。

## 8. Canonical demo

始终保留：

```text
reports/v045_demo_bundle
```

核对：

```bash
python scripts/check_v045_product_runtime.py
python scripts/check_v045_team_clone_ready.py
python scripts/build_v045_demo_bundle.py \
  --output-dir reports/v045_demo_bundle \
  --verify
```

现场 provider/网络失败时使用 Offline Demo Replay；Replay 必须明确标注 recorded，不冒充 live inference。

## 9. Evidence screenshot

如需为新案例导出：

```bash
python scripts/build_v045_evidence_screenshots.py \
  --input-dir <RUN_DIR> \
  --prospectus-root <AUTHORIZED_ROOT>
```

必须绑定 PDF SHA、physical page、bbox source、match count、image SHA。多重/无匹配明确 unavailable，不画假框。

## 10. Fresh clone

在第二个干净目录：

```bash
git clone <REPO>
cd hk-ipo-risk-agents
python -m venv .venv
# activate
pip install -e ".[dev,retrieval-research]"
```

不要复制：

```text
.env
PDF
raw EOD / CSMAR
local reports
cache
API key / token
```

然后执行第 4 节的 validators、demo bundle verify 和前端 smoke。

## 11. Final audits

### Blind

```text
2025 Blind outcome not accessed
no Blind outcome in package
no Blind-driven optimization
```

### Provenance

至少覆盖：

```text
Role-B benchmark / Gold / evaluator
Market PIT identity
Role-D model / feature / alert
Final Supervisor provider/model/prompt identity
Demo replay recorded provenance
```

### Determinism

明确区分 deterministic calculation / score / identity 与 remote LLM variance。远程 LLM 不得宣称 byte-for-byte deterministic。

### Security / licensing / path

拒绝：

```text
.env
API key / Bearer / token / private key
licensed prospectus PDF
raw licensed EOD / CSMAR
raw provider journal
absolute local path
cache / temp / failed experiment payload
unauthorized model/data
Validation private working files
Blind outcome artifact
```

## 12. Artifact index

最终建立：

```text
logical path
owner
gate
required / optional
exists
size
SHA-256
allowed_in_submission
rejection reason
```

推荐纳入：

```text
source code / allowed configs
README / FINAL_SUBMISSION_STATUS / TEAM_QUICKSTART / Runbook
Role-B benchmark summary
freeze manifest
Validation receipt
Market / Model audits
G5/G6 manifests
Role-D frozen manifests
case reports / trace
Evidence screenshot manifests / selected images
canonical replay
artifact index
release note
submission manifest
SHA256SUMS
```

## 13. Final acceptance preflight

```bash
python scripts/run_final_acceptance.py \
  --ci-status pass \
  --ci-evidence-url <LATEST_MAIN_CI_URL> \
  --package-preflight
```

如果 G2 仍 BLOCKED，该命令应继续 fail-closed；带 `README_NOT_FINAL.txt` 的 ZIP 只是 preflight evidence，不得改名冒充 `COMPETITION_READY` final bundle。

## 14. 比赛平台实际提交包

仓库自定义 G2 未达标不等于平台禁止上传作品。若比赛平台只要求作品/代码/说明/演示，可按真实状态提交，但必须保留 known limitation。

准备：

- 源码/允许配置；
- 项目说明书；
- 最终 PPT；
- 演示视频/录屏（若平台要求）；
- 答辩讲稿与 Q&A；
- offline replay fallback；
- 关键 Evidence 截图；
- 指标与 known limitations 一页说明。

## 15. 现场启动

| 入口 | Windows | macOS / Linux |
|---|---|---|
| 标准工作台 | `START_DEMO.bat` | `./start_demo.sh` |
| 评委界面 | `START_JUDGE_DEMO.bat` | `./start_judge_demo.sh` |

先现场演示 Offline Replay，确保评委在 30 秒内看到“风险—原因—证据—可信边界”；再按网络/provider 情况展示 live/fresh 分析。

## 16. Final docs truth

提交前再次核对：

```text
README
FINAL_SUBMISSION_STATUS
V0.4_RELEASE_ACCEPTANCE
COMPETITION_CLOSURE_PLAN
SUBMISSION_RUNBOOK
```

必须使用同一 M1/M2、同一 freeze SHA、同一 Gate 状态。禁止 README 说 PASS 而 Acceptance 说 BLOCKED。
