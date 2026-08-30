# Final Submission Status — 2026-08-30

> Runtime freeze main SHA: `ab3390cc548f3d4ec7f08d5d39350a3c1baf1f0a`  
> Role-B benchmark SHA: `dcc36abd30ec42cd1d6b83bc6d70b2d1aa74f61b`  
> Current repository conclusion: **SUBMISSION CLOSEOUT / NOT COMPETITION_READY UNDER THE SELF-DEFINED G2 GATE**

本文档用于最后提交收口。它不替代 Metric Protocol，也不把未达标的 G2 改写成 PASS。

## 1. Final Development truth

最终 ALL79 Development 结果：

| 模式 | Cases | M1 | M2 | 口径 |
|---|---:|---:|---:|---|
| Best offline | 79/79 | **70/102 = 68.63%** | **103/191 = 53.93%** | 最佳离线工程参考 |
| Real LLM gated | 79/79 | **61/102 = 59.80%** | **93/191 = 48.69%** | 正式 provider-backed Development 结果 |

正式 G2 门槛仍是 M1 `>=80%`、M2 `>=85%`、real LLM `79/79`。因此 G2 诚实标记为 **BLOCKED**；不能用较高的 offline 结果替代 real-LLM gated 结果。

## 2. 已冻结且可提交的能力

- Financial / Legal / Business 多智能体 Document pipeline；
- real PDF parsing、physical-page Evidence、Calculation、specialized Verifier；
- Final Supervisor 与 conflict / re-check；
- governed Dynamic Market-X，缺失不补 0；
- frozen Role-D V2 runtime inference + native SHAP；
- `uncalibrated_model_score` 语义；
- Offline Demo Replay；
- Historical Governed IPO；
- Fresh New-IPO Analysis；
- Judge-facing Streamlit UI；
- Evidence screenshot / trace / single-case report / batch report；
- G5 product acceptance PASS；
- G6 capability manifest 8/8 PASS；
- latest integrated main CI 已通过 tests / Role D runtime / Team demo runtime。

## 3. 当前 Gate 状态

| Gate | 状态 | 说明 |
|---|---|---|
| G0 Runtime / contracts / CI | PASS | `main@ab3390cc` 三条主 CI 已通过 |
| G1 Stable final-three baseline | PASS | replay / E1 / M3 / Market / Model / Evidence 基线受回归保护 |
| G2 ALL79 Document Intelligence | **BLOCKED** | real LLM M1 59.80%，M2 48.69%，低于 80% / 85% |
| G3 Dynamic Market-X | PASS | governed historical + dynamic PIT runtime 已关闭 |
| G4 Dynamic Model / SHAP | PASS | frozen V2 inference + native SHAP 已关闭 |
| G5 Final Frontend / Product | PASS | 三种产品模式、truthful channel states |
| G6 Capability demonstrations | PASS | 8/8 hash-bound capability proofs |
| G7 Freeze / Validation / package | **PARTIAL** | runtime freeze 已记录；one-shot Validation 与最终安全封包仍待完成 |

## 4. 已完成的最终收口动作

- Role-B freeze `dcc36ab` 已合入最新 main；
- final runtime identity 冻结在 `ab3390cc`；
- Role-B 核心 runtime identity 已做 hash 等价核对；
- 正式 `reports/v045_role_b/document_benchmark_summary.json` 已生成；
- `reports/final_status/final_freeze_manifest.json` 已生成；
- G5/G6 当前 artifact 保持 PASS；
- 旧分支保留作历史，不要求删除。

## 5. 仍需人工/本地执行的硬任务

这些任务依赖授权数据、干净环境或比赛提交平台，无法只靠仓库远程编辑替代：

1. **One-shot Validation**：在 frozen identity 下运行唯一一次 ALL19 2024 Existing-Gold Validation；之后禁止根据结果调参。
2. **生成 Validation receipt**：`reports/final_status/one_shot_validation_receipt.json`，记录 one-shot、post_hoc_tuning=false、Blind untouched。
3. **最终 capability rehash**：在最终提交 commit 上运行 `python scripts/check_final_product_capabilities.py`，确保 G5/G6 hashes 绑定最终树。
4. **Fresh-clone verification**：第二个干净目录从远端 `main` clone，安装并跑 validators / demo bundle verify / frontend smoke。
5. **安全与授权审计**：确认无 `.env`、token、licensed PDF、raw EOD、raw provider journal、绝对本地路径、未授权数据。
6. **最终 artifact index**：列出逻辑路径、gate、owner、required/optional、size、SHA-256、是否允许进入 submission。
7. **最终 package**：按比赛实际上传要求生成 secure ZIP / source bundle / SHA256SUMS；不要把 preflight evidence ZIP 冒充 final package。
8. **答辩材料**：最终 PPT、演讲稿、演示脚本、备用录屏/截图、现场启动说明需与本仓库 Final Truth 保持一致。
9. **GitHub Release**：若坚持仓库自定义 G2 必须 PASS 才叫正式 1.0，则当前应使用 release candidate；不要把 `COMPETITION_READY` 改成 true。

## 6. 建议的最终提交材料包

### A. 比赛核心材料

- 项目源代码 / 允许提交的配置；
- README / TEAM_QUICKSTART / Submission Runbook；
- 项目说明书或技术方案；
- 最终 PPT；
- 5–10 分钟演示或比赛要求的视频（若平台要求）；
- 答辩讲稿 / Q&A 备忘；
- 启动脚本：Windows 与 macOS/Linux；
- canonical offline demo replay，作为现场网络/provider 失败时 fallback。

### B. 技术与指标证明

- `reports/v045_role_b/document_benchmark_summary.json`；
- `reports/final_status/final_freeze_manifest.json`；
- one-shot Validation receipt（运行后补）；
- G5 `product_acceptance.json`；
- G6 `capability_manifest.json`；
- Market-X strict audit；
- Dynamic Model / SHAP strict audit；
- Role-D frozen model / feature / alert manifests；
- Evidence screenshot manifests / sample images；
- final-three replay / team clone-ready evidence；
- latest-main CI links / results；
- final artifact index + SHA256SUMS。

### C. 评委展示材料

答辩只讲清楚四件事：

1. **有什么风险**；
2. **为什么判断为风险**；
3. **证据在哪里**；
4. **系统为什么可信、边界在哪里**。

避免在主界面展示内部状态码、未经解释的英文工程字段和无法核验的模型结论。Evidence 原文保持原始语言；正文与解释默认简体中文。

## 7. Known limitations — 提交时应主动说明

- self-defined G2 target 未达到；
- real LLM gated 低于 best offline，说明 LLM augmentation 在当前严格 scope/schema contract 下存在负增益与结构化失败风险；
- source-edition / exact-anchor provenance 对部分 M2 仍有约束；
- Dynamic Market-X 对超出受治理历史边界的新案例会诚实 `PARTIAL / UNAVAILABLE`；
- model score 未校准，不是概率，不预测上市后价格；
- remote LLM prose 不是 byte-for-byte deterministic；
- 授权数据/PDF 不随公开仓库分发。

## 8. Release decision

当前可以做的是：**完成比赛提交包并按真实能力参赛**。

当前不应做的是：

- 把 G2 写成 PASS；
- 把 offline 70/102、103/191 冒充 real-LLM 成绩；
- 宣称 `COMPETITION_READY=true`；
- 为了让 Release Gate 变绿而修改门槛或评测口径；
- 继续打开 Development/Validation 做临门调参。

若比赛平台本身并不要求仓库内部 G2 门槛，项目仍可提交；仓库只需把“内部自定义 readiness gate 未达标”与“作品可交付参赛”清楚区分。
