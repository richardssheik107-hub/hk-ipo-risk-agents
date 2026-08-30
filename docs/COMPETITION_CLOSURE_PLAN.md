# Competition Closure Plan — Final Submission Closeout

> 状态日期：`2026-08-30`  
> Runtime freeze main：`ab3390cc548f3d4ec7f08d5d39350a3c1baf1f0a`  
> Role-B benchmark SHA：`dcc36abd30ec42cd1d6b83bc6d70b2d1aa74f61b`  
> 当前结论：**SUBMISSION CLOSEOUT / G2 BELOW SELF-DEFINED TARGET**  
> 实时 Gate：`V0.4_RELEASE_ACCEPTANCE.md`  
> 最终状态：`FINAL_SUBMISSION_STATUS.md`

本文档不再是研发 Roadmap，而是最后提交执行顺序。Document / Market / Model / Frontend 的功能开发已经停止；后续只做治理、验证、文档、打包与现场材料。

## 1. Final Development truth

| 模式 | Cases | M1 | M2 |
|---|---:|---:|---:|
| Best offline | 79/79 | **70/102 = 68.63%** | **103/191 = 53.93%** |
| Real LLM gated | 79/79 | **61/102 = 59.80%** | **93/191 = 48.69%** |

正式 G2 门槛：

```text
M1 >= 0.80
M2 >= 0.85
real_llm_cases = 79/79
```

结论：real LLM 覆盖 79/79，但 M1/M2 未达门槛，因此 G2 保持 **BLOCKED**。当前决定是停止 Development 调参，保留真实结果并进入 submission closeout。

## 2. Track 状态

| Track | 状态 | 后续 |
|---|---|---|
| A — Document Intelligence | **FROZEN / BELOW TARGET** | 不再调参；只维护 benchmark/provenance |
| B — Frontend / Product | PASS | 回归保护；准备现场演示 |
| C — Dynamic Market-X | PASS | 回归保护 |
| D — Dynamic Model / SHAP | PASS | 回归保护 |
| E — Release / Submission | **P0 / ACTIVE** | Validation、audits、fresh clone、package、材料 |

## 3. 已关闭稳定基线

```text
Final Supervisor E1 = 3/3
M3 = 1.0 x 3
Market final-three = 3/3
Model final-three = 3/3
recheck = 17/17
seven-stage = 21/21
Evidence screenshots = 17/17 precise
canonical replay = 3 cases / 66 files
G3 Dynamic Market-X = PASS
G4 Dynamic Model / SHAP = PASS
G5 Product = PASS
G6 Capabilities = PASS
main tests / Role D runtime / Team demo runtime = PASS
```

这些项只允许回归保护，不再进行能力扩张。

## 4. 已完成的 Release 收口

- Role-B `dcc36ab` 已合入最新 main；
- runtime freeze main 固定为 `ab3390cc`；
- 正式 ALL79 summary 已写入 `reports/v045_role_b/document_benchmark_summary.json`；
- freeze manifest 已写入 `reports/final_status/final_freeze_manifest.json`；
- Role-B benchmark 与 promoted main 的核心 config / runner / prompt / provider / extractor / evaluator blob identity 已核对一致；
- G5/G6 机器清单当前保持 PASS；
- 旧 feature/release 分支作为历史保留，不要求删除。

## 5. 现在唯一执行队列

### P0-1 — One-shot Validation

在 frozen runtime identity 下执行唯一一次：

```text
ALL19 2024 Existing-Gold Validation
ONE SHOT
```

执行后只允许记录，不得根据 Validation 修改 Retriever、Prompt、Agent、Verifier、threshold、model、evaluator。

输出：

```text
reports/final_status/one_shot_validation_receipt.json
```

必须明确：

```text
status
one_shot = true
post_hoc_tuning = false
blind_2025_y_accessed = false
freeze SHA / config identity
```

### P0-2 — Final G5/G6 rehash

在最终提交 commit 上运行：

```bash
python scripts/check_final_product_capabilities.py
```

重新绑定：

```text
reports/final_status/product_acceptance.json
reports/final_status/capability_manifest.json
```

禁止手工改 hash。

### P0-3 — Final CI / fresh clone

最终 main 重新通过：

```text
pytest / compileall
project / competition-data / runtime validators
Role-D strict checker
Market strict audit
Model/SHAP strict audit
product runtime
team clone ready
git diff --check
GitHub Actions: tests / Role D runtime / Team demo runtime
```

随后从第二个干净目录 clone 远端 main，不复制 `.env`、PDF、licensed EOD、cache、local reports、API key，按 Runbook 完成安装、validator、demo verify、frontend smoke。

### P0-4 — Security / licensing / provenance / path audit

拒绝进入 Git 或 submission：

```text
.env
API key / token / private key
licensed prospectus PDFs
raw EOD / CSMAR licensed data
raw LLM/provider journal
absolute local paths
cache / temp / failed experiment payloads
Validation working files
Blind outcomes
```

### P0-5 — Artifact index / final package

生成单一 artifact index：

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

随后生成 secure submission package + `SHA256SUMS.txt`。若 `run_final_acceptance.py` 仍因 G2 BLOCKED 生成带 `README_NOT_FINAL.txt` 的 preflight ZIP，该 ZIP 只能作证据，不可冒充仓库定义的 COMPETITION_READY final package。

### P0-6 — 答辩与平台材料

最终准备：

- 项目技术说明 / 作品说明；
- 最终 PPT；
- 答辩讲稿与 Q&A；
- 演示视频或录屏（如果平台要求）；
- Windows 与 macOS/Linux 启动说明；
- canonical offline replay 作为 provider/网络失败的现场 fallback；
- 关键 Evidence 截图；
- 一页指标与 known limitations 说明。

## 6. 展示口径

评委侧优先回答：

```text
有什么风险
为什么是风险
证据在哪里
系统为什么可信、边界在哪里
```

正文与解释默认简体中文；Evidence 原文保持原始语言。不要把内部状态码、未经解释的 snake_case、provider 错误栈或未校准 score 当成主叙事。

## 7. Known limitations 必须主动披露

- G2 self-defined target 未达到；
- real-LLM gated 低于 best offline；
- strict Evidence scope / structured schema 下 Business LLM 存在失败或负增益风险；
- source edition / exact-anchor provenance 对部分 M2 有约束；
- Market-X 超出治理覆盖边界会 `PARTIAL / UNAVAILABLE`；
- model score 未校准，不是概率；
- remote LLM prose 不是 byte-for-byte deterministic；
- licensed PDF / EOD / CSMAR 不随公开仓库分发。

## 8. Competition Ready 与“可以参赛提交”必须分开

仓库自己的 `COMPETITION_READY` 定义仍要求：

```text
ALL79 M1 >=80%
ALL79 M2 >=85%
M3 =100%
G3/G4/G5/G6 PASS
one-shot Validation complete
latest-main CI / Blind / provenance / determinism / security / licensing PASS
fresh clone PASS
secure package PASS
```

当前 G2 不满足，因此不能把 `COMPETITION_READY` 改成 true。

但如果比赛平台本身并不把仓库自定义 G2 门槛作为硬性上传条件，作品仍可按真实状态完成提交。最终材料应明确区分：

```text
submission deliverable is complete
!=
self-defined research quality gate passed
```

## 9. 停止规则

从本文件更新起：

```text
DEVELOPMENT_TUNING = STOP
MARKET_FEATURE_DEVELOPMENT = STOP
MODEL_TUNING = STOP
FRONTEND_FEATURE_EXPANSION = STOP
RELEASE_CLOSEOUT = ACTIVE
```

只允许：验证、非算法 bugfix、文档 truth alignment、hash/manifest、包装、安全审计、现场材料。
