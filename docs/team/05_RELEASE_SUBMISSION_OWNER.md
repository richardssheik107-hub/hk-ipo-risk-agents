# Person 5 — Final Integration / Release / Submission Owner

> 状态日期：2026-08-29  
> 建议分支：`codex/release-submission`  
> 主优先级：前期 **P1**，进入冻结/提交阶段后升为 **P0**  
> 核心职责：把前四个人的成果变成一个可复现、可审计、可提交、不会泄密的最终版本

## 1. 主目标

这个岗位不负责继续调算法，而负责最终工程闭环：

```text
integration
→ release readiness
→ freeze
→ one-shot Validation
→ audits
→ final artifacts
→ secure submission package
→ fresh-clone verification
```

最终必须做到：

> 一个干净环境只拿最终仓库/提交包，就能按照 Runbook 复现应该复现的内容；所有指标、模型、Market、Evidence、Replay、版本、哈希和限制都能解释清楚。

## 2. 当前稳定基线

当前已经有一个 known-good team-ready baseline：

```text
canonical 3-case replay
Market = 3/3
Model = 3/3
Final Supervisor E1 = 3/3
M3 = 1.0 x 3
recheck = 17/17
budget skipped = 0
seven-stage = 21/21
Evidence screenshots = 17/17 precise
bundle = 66 files
fresh clone = PASS
CI = PASS
```

本岗位必须保护这条稳定基线，不能为了接入新功能破坏最终可用 Demo。

## 3. 当前真正未关闭的 Release 项

以当前 Release Acceptance 为准，主要还有：

```text
Person 1:
ALL79 M1 >= 0.80
ALL79 M2 >= 0.85

Person 3:
Dynamic Market-X historical + fresh path（PR #191 已关闭，持续回归保护）

Person 4:
formal model decision（已关闭）
Dynamic Model / SHAP（PR #197 已关闭，持续回归保护）
capability coverage

Person 2:
final answer-ready frontend

本岗位:
freeze / Validation / audits / package
```

Human Review / M4 已明确：

```text
OPTIONAL
NOT_REQUIRED_FOR_RELEASE
```

不需要 6 份真人 review，不得重新把它加回硬 Gate。

## 4. 负责范围

本岗位负责：

- Release Acceptance 文档；
- Closure Plan / Roadmap / Runbook；
- final status snapshot；
- repository-level integration；
- merge sequencing；
- version / schema / artifact identity；
- latest-main CI；
- fresh-clone verification；
- Blind audit；
- provenance audit；
- determinism audit；
- security / secret / path / licensing audit；
- final artifact index；
- one-shot Validation 的执行治理；
- final submission ZIP；
- submission manifest / SHA-256；
- release note；
- teammate/judge quickstart；
- final source/artifact allowlist。

本岗位**不负责**：

- 为 M1/M2 改 Retriever/Agent；
- 为模型效果重新调参；
- 修改 Market 数值逻辑；
- 为 UI 好看改变 runtime truth；
- 用 Validation 结果反向调系统。

## 5. 前期工作：持续做 Integration Watch

在其他人开发期间，本岗位持续检查每个 PR 是否破坏关键边界。

### Person 1 PR

检查：

```text
Gold unchanged
Validation untouched
Blind untouched
metric definition unchanged
no case/page hardcoding
formal artifacts retained
```

### Person 2 PR

检查：

```text
no fake available
no stale bundle discovery
no provenance loss
no Evidence bbox fabrication
canonical 3-case no regression
```

### Person 3 PR

检查：

```text
PIT strict
no post-listing outcome
no zero-fill
no raw licensed EOD committed
identity/hash/provenance complete
```

### Person 4 PR

检查：

```text
no Validation retuning
no Blind outcome
model hash/manifest bound
runtime inference only
score != probability
SHAP not copied from final-three
```

## 6. Merge / Branch 原则

其他四人尽量独立分支：

```text
codex/role-b-m1-m2
codex/final-product-ui
codex/dynamic-market-x
codex/dynamic-model-runtime
```

本岗位使用：

```text
codex/release-submission
```

每条线进入 main 前至少要求：

```text
targeted tests PASS
relevant integration tests PASS
git diff --check PASS
no security / data-boundary violation
```

高风险功能优先 PR → CI → merge，不用 force push main。

## 7. Freeze 条件

只有当以下条件都满足时才允许进入最终 freeze：

### Document

```text
ALL79 complete
M1 >= 0.80
M2 >= 0.85
real LLM = 79/79
```

### Market

```text
historical universe path audited
Dynamic New-IPO path implemented or external-data boundary formally documented
PIT / missingness PASS
```

### Model

```text
PROMOTE / RETAIN decision complete
final model version frozen
feature manifest frozen
alert policy frozen
Dynamic inference + SHAP governed
```

### Product

```text
canonical 3-case no regression
historical / fresh UI modes truthful
capability cases complete
```

如果任一项仍在开放调参，不能跑最终 one-shot Validation。

## 8. Freeze Manifest

进入 freeze 后生成一个明确 manifest，至少绑定：

```text
main SHA
config SHA
Prompt versions
Schema versions
Retriever version
Verifier version
Market schema/provider version
model version/hash
feature manifest hash
alert policy version
Final Supervisor prompt/version
Evaluator identity
```

Freeze 后任何改变这些内容的 commit 都必须使 Validation 失效并重新评估治理状态。

## 9. One-shot Validation

这是本岗位的核心责任之一。

### 执行前

必须确认：

```text
Development optimization stopped
all relevant code frozen
Validation not previously used for tuning
Blind untouched
```

### 执行

```text
ALL19 Validation
ONE SHOT
```

### 执行后

只允许：

- 记录结果；
- 修复纯包装/非算法错误且明确不使用 Validation 内容做选择；
- 如果出现真正 runtime crash，必须留下治理记录说明为什么重跑以及哪些代码改变。

禁止：

```text
看 Validation 错例
→ 改 Retriever / Prompt / Risk rule / Model
→ 再跑 Validation
```

## 10. Final Audits

### 10.1 Blind Audit

确认：

```text
2025 Blind outcome not accessed
Blind split not selected by runtime
no hidden Blind artifact in package
```

### 10.2 Provenance Audit

至少覆盖：

```text
Role-B Gold manifest/hash
Role-D model/source identity
Role-E PDF/config/code identity
Market PIT provenance
Final Supervisor provider/model/prompt/request/response hash
```

### 10.3 Determinism Audit

需要区分：

```text
deterministic calculation / identity / feature / score
vs
remote LLM prose variance
```

不得虚假声称远程 LLM 文本 byte-for-byte deterministic。

### 10.4 Security Audit

拒绝：

```text
.env
API key
Bearer/token
private key
licensed PDF
raw EOD
raw LLM journal
local absolute path
large unintended artifact
unauthorized model/data
```

## 11. Final Artifact Index

建立单一 artifact index，至少包含：

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

Human Review artifact 若存在：

```text
optional
```

缺失不能阻塞 Release。

## 12. 最终提交物

最终 package 应按比赛实际要求和仓库当前 allowlist 生成，典型包括：

```text
source code
configs
README
TEAM_QUICKSTART / Submission Runbook
metric summary
prediction table
Risk/Evidence benchmark artifacts
Agent Trace / reasoning artifacts
Market / Model governed outputs
case reports
Evidence screenshot manifests/images
canonical demo replay
capability-case evidence
release audits
artifact index
release note
submission_manifest.json
```

明确排除：

```text
original prospectus PDFs
raw licensed EOD
.env / credentials
raw provider journal
cache
failed experiments
local temp paths
Validation private working files
Blind artifacts/outcomes
```

## 13. Canonical Demo / Team Runtime

最终始终维护：

```text
reports/v045_demo_bundle
```

并确保：

```text
bundle verify PASS
TEAM_CLONE_READY PASS
fresh clone PASS
Streamlit smoke PASS
```

如果 Dynamic New-IPO 功能加入，也不要删除 3-case offline replay；它是答辩时最稳定的 fallback/demo baseline。

## 14. Final CI

最终 main 至少检查：

```text
compileall
project validator
competition data validator
competition runtime validator
Role-D receipt
product runtime
team clone ready
full pytest
git diff --check
security scan
```

以及现有 GitHub Actions：

```text
tests
Role D runtime
Team demo runtime
```

新 Dynamic Market / Model 若有独立 contract，应加入相应 CI。

## 15. Fresh Clone 验证

最终必须从远端 `main` 在第二个干净目录 clone。

不能复制：

```text
.env
PDF
raw EOD
local reports
cache
API keys
```

然后执行：

```text
install
validators
product runtime checker
team clone checker
demo bundle verify
frontend smoke
```

只有远端 clone 自己能工作才算真正完成。

## 16. Release 文档口径

所有文档最终必须同步同一个事实源。

禁止出现：

- README 说 PASS、Acceptance 说 FAIL；
- 旧 M4 仍被写成硬 Gate；
- 旧三案例结果被当成 Dynamic New-IPO proof；
- v2 candidate 写成已正式晋升但实际上没有 receipt；
- fixed10 写成 ALL79；
- Demo Replay 写成实时推理。

## 17. Final Status 输出

最终报告至少包含：

```text
FINAL_STATUS
MAIN_SHA
M1 / M2 / split / real LLM count
Validation result
Market coverage
Dynamic New-IPO status
model decision / model hash
M3
Final Supervisor
Evidence coverage
capability cases
CI
fresh clone
security/provenance/determinism
submission ZIP path/hash
known limitations
```

当前 G5/G6 交付已关闭：`product_acceptance.json` 证明 Offline Demo Replay、Historical
Governed IPO、Fresh New-IPO Analysis 三模式；`capability_manifest.json` 证明 8/8
competition capabilities。两者由 `scripts/check_final_product_capabilities.py` 根据当前
artifact/hash 重建校验，均不打开 Validation 或 Blind，且 capability 不计入 M1/M2。

## 18. 禁止事项

禁止：

- 为了让 readiness 绿而删真实 Gate；
- 把 M4 重新加成硬 Gate；
- 用 mock/fallback 冒充 real success；
- 用 Validation 调参；
- 访问 Blind outcome；
- 修改 upstream 算法但不通知 owner；
- 手工改 artifact 指标；
- 手工改 SHA 伪造 provenance；
- 把整个 `reports/` 强行上传；
- 提交受限 PDF / raw EOD / secrets。

## 19. 完成定义

本岗位 DONE 条件：

```text
all true active Gates closed
freeze manifest complete
one-shot Validation governed and recorded
latest-main CI PASS
Blind / provenance / determinism / security PASS
artifact index PASS
canonical demo PASS
fresh clone PASS
final docs consistent
secure submission package generated
submission manifest + SHA-256 complete
```

这个岗位的价值不是“最后压个 ZIP”，而是确保所有前期成果最终真的构成一个可信、可复现、能提交的比赛作品。
