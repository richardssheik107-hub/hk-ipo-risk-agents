# Person 5 — Final Integration / Release / Submission Owner — P0 ACTIVE

> 状态日期：`2026-08-30`  
> Runtime freeze main：`ab3390cc548f3d4ec7f08d5d39350a3c1baf1f0a`  
> 当前状态：**FINAL SUBMISSION CLOSEOUT**

## 1. 主目标

算法与产品功能已经冻结。本岗位现在是唯一 active P0：

```text
final truth alignment
→ one-shot Validation
→ final hashes / CI
→ audits
→ fresh clone
→ artifact index
→ secure submission package
→ presentation materials
```

## 2. Final truth

```text
Best offline ALL79:
M1 = 70/102 = 68.63%
M2 = 103/191 = 53.93%

Real LLM gated ALL79:
M1 = 61/102 = 59.80%
M2 = 93/191 = 48.69%
real_llm_cases = 79/79
```

正式 G2 自定义门槛 M1 `>=80%`、M2 `>=85%` 未达到，因此 G2 必须继续 BLOCKED。Release owner 的责任是记录真实结果，不是把 Gate 改绿。

## 3. 当前 Gate

```text
G0 Runtime / CI                 PASS
G1 Stable final-three           PASS
G2 Document Intelligence        BLOCKED
G3 Dynamic Market-X             PASS
G4 Dynamic Model / SHAP         PASS
G5 Final Frontend / Product     PASS
G6 Capability demonstrations    PASS
G7 Freeze / Validation / package PARTIAL
```

机器事实源：

```text
reports/v045_role_b/document_benchmark_summary.json
reports/final_status/final_freeze_manifest.json
reports/final_status/product_acceptance.json
reports/final_status/capability_manifest.json
```

## 4. Runtime freeze

Runtime freeze 已记录：

```text
main = ab3390cc548f3d4ec7f08d5d39350a3c1baf1f0a
Role-B benchmark = dcc36abd30ec42cd1d6b83bc6d70b2d1aa74f61b
Development tuning = STOP
Validation opened at freeze = false
Blind outcome accessed = false
```

Release-document / packaging metadata 可以继续修改，但不能改变 frozen runtime identity。

## 5. One-shot Validation

下一硬任务：

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

执行后生成：

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
metric summary
```

禁止：

```text
看 Validation 错例
→ 改 Retriever / Prompt / Risk rule / Verifier / Model
→ 再跑 Validation
```

## 6. Final G5/G6 rehash

最终提交 commit 上运行：

```bash
python scripts/check_final_product_capabilities.py
```

重新生成/核对：

```text
reports/final_status/product_acceptance.json
reports/final_status/capability_manifest.json
```

禁止手工修改 hash。

## 7. Final CI

最终 main 至少必须通过：

```text
pytest
compileall
project validator
competition data validator
competition runtime validator
Role-D receipt / strict release checker
Market strict audit
Dynamic Model / SHAP strict audit
product runtime
team clone ready
git diff --check
```

GitHub Actions：

```text
tests
Role D runtime
Team demo runtime
```

## 8. Fresh clone

第二个干净目录只从远端 `main` clone。

禁止复制：

```text
.env
PDF
raw EOD / CSMAR
local reports
cache
API key / token
```

然后执行安装、validators、product runtime、team clone checker、demo bundle verify、frontend smoke。

## 9. Final audits

### Blind

```text
2025 Blind outcome not accessed
no Blind outcome artifact in package
no Blind-driven optimization
```

### Provenance

覆盖：

```text
Role-B benchmark / Gold / evaluator identity
Market PIT identity
Role-D model / feature / alert identity
Final Supervisor provider/model/prompt identity
Demo replay recorded provenance
```

### Determinism

明确区分 deterministic calculation / identity / feature / score 与 remote LLM variance。不得声称远程 LLM byte-for-byte deterministic。

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
```

## 10. Artifact index

建立单一 index：

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

Human Review artifact 仍是 optional，缺失不能阻塞。

## 11. 最终提交材料

建议 package 至少包含：

```text
source code / allowed configs
README / FINAL_SUBMISSION_STATUS / TEAM_QUICKSTART / Runbook
Role-B final benchmark summary
freeze manifest
Validation receipt
Market / Model governed audits
G5/G6 acceptance artifacts
Role-D frozen manifests
case reports / trace
Evidence screenshot manifests / selected images
canonical demo replay
artifact index
release note
submission manifest
SHA256SUMS
```

明确排除：

```text
original prospectus PDFs
raw licensed market data
.env / credentials
raw provider journal
cache / temp
failed experiments
Validation working files
Blind outcomes
```

## 12. 答辩材料

还需准备：

- 最终 PPT；
- 讲稿；
- Q&A 备忘；
- 演示视频/录屏（若平台要求）；
- 现场 Demo 步骤；
- offline replay fallback；
- 关键 Evidence 截图；
- 一页 known limitations / metric truth。

评委叙事只回答：有什么风险、为什么、证据在哪、为什么可信。正文默认简体中文，Evidence 原文不改写。

## 13. Release 命名

当前仓库自定义 G2 未通过，因此：

```text
COMPETITION_READY = false
```

如果 GitHub 版本号需要在提交前冻结，优先考虑 release candidate；不要仅为了“正式 1.0”修改 readiness 真相。比赛平台若不以仓库自定义 G2 为上传条件，作品本身仍可按真实状态提交。

## 14. DONE 定义

本岗位可完成的最终闭环：

```text
one-shot Validation recorded
final G5/G6 rehash
latest-main CI PASS
Blind / provenance / determinism / security / licensing / path audits PASS
artifact index complete
fresh clone PASS
canonical demo PASS
final docs consistent
secure submission package generated
submission manifest + SHA-256 complete
presentation materials ready
```

即使最终 G2 仍 BLOCKED，也不能通过改门槛消除它；最终提交材料应诚实携带这个 known limitation。
