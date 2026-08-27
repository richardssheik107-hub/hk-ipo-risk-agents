# v0.4.5 Role-B Lunamax Fixed-10 Automation Runbook

> Current operating status: 10/10 real-LLM analysis completed; latest observed blocker was Existing-Gold handoff `governed result missing case_id`, now fixed in runner serialization with an offline recovery path.

本文档用于把 Role-B fixed-10 真实 LLM Development 迭代收敛成一个低自由度、低上下文、可恢复的自动执行任务。

目标不是让 Lunamax/Codex 重新设计项目，而是让它只做 Runner：冻结/读取 fixed-10，执行现有 runner，读取两份摘要，返回指标后停止。若真实 LLM 已完成而 evaluator/summary 阶段失败，则只做 offline recovery，不重新跑模型。

完整比赛收尾顺序见 `V045_CURRENT_EXECUTION_PLAN.md`。

## 1. 重要口径

当前 Metric Protocol v2 的正式 fixed-10 权威来源不是人工挑选，而是本地生成的：

```text
reports/v045_role_b/fixed10_development_subset.json
```

如果该文件不存在，必须由当前 `main` 的确定性选择器生成：

```bash
python scripts/run_v045_role_b_iteration.py --subset-only
```

选择器只从 Existing-Gold Development 中取 10 家，并优先平衡：

```text
cash_burn_pressure
customer_concentration
redemption_rights
supplier_concentration
```

生成后保持不变，用于后续纵向比较。Validation 与 2025 Blind 不允许进入该 subset。

## 2. 手工 smoke / 历史 benchmark 参考 10 家

以下 10 家曾用于旧版 Role-B real-LLM Development smoke/benchmark，可用于人工核对、环境 smoke、公司名称映射与历史可比性；它们**不覆盖**当前 Metric-v2 自动生成的正式 fixed-10：

| # | case_id | stock_code | company_name | listed_date | industry |
|---:|---|---|---|---|---|
| 1 | `ipo_2020_01167` | `1167.HK` | 加科思─B | 2020-12-21 | 生物技术 |
| 2 | `ipo_2020_01942` | `1942.HK` | MOG Holdings | 2020-04-15 | 支付服务 |
| 3 | `ipo_2020_01961` | `1961.HK` | 九尊数字互娱 | 2020-03-17 | 游戏软件 |
| 4 | `ipo_2020_09600` | `9600.HK` | 新纽科技 | 2021-01-06 | 应用软件 |
| 5 | `ipo_2020_09633` | `9633.HK` | 农夫山泉 | 2020-09-08 | 非酒精饮料 |
| 6 | `ipo_2021_09898` | `9898.HK` | 微博─SW | 2021-12-08 | 互动媒体及服务 |
| 7 | `ipo_2022_06698` | `6698.HK` | 星空华文 | 2022-12-29 | 影视娱乐 |
| 8 | `ipo_2022_09863` | `9863.HK` | 零跑汽车 | 2022-09-29 | 汽车 |
| 9 | `ipo_2023_02451` | `2451.HK` | 绿源集团控股 | 2023-10-12 | 摩托车及其他 |
| 10 | `ipo_2023_02517` | `2517.HK` | 锅圈 | 2023-11-02 | 包装食品 |

保留这组作为 smoke 参考，是因为它已有历史 benchmark identity，跨 2020–2023 Development cohort，覆盖不同类型招股书，并且 official master bridge 已有稳定身份映射；其中 1167.HK 已存在真实 provider 全流程成功证据。

如果需要展示当前正式 fixed-10 的公司名称，只允许通过已有：

```text
data/catalog/ipo_official_master_bridge.csv
```

做 `case_id -> stock_code -> selected_name` 映射。

## 3. 当前本地执行状态

2026-08-27 最近一轮 constrained Runner 已完成：

```text
real-LLM analysis = 10/10 completed
Validation opened = false
2025 Blind accessed = false
```

随后 Existing-Gold evaluator handoff 返回：

```text
EXECUTION_BLOCKED
ValueError: governed result missing case_id
```

当前已确认根因是 runner serialization，而不是 LLM、Prompt、Retriever、Gold 或 evaluator metric contract。

runner 现在会在 `analysis_results.jsonl` 中显式写入 frozen subset 提供的 canonical `case_id`。如果 `metadata.case_id` 或 top-level `case_id` 已存在但与 expected case 不一致，则 fail closed，不静默覆盖。

对这批已经完成的 10/10 结果，下一步只做 offline recovery：

```bash
python scripts/recover_v045_role_b_iteration.py --iteration <existing_iteration_id>
```

该恢复路径不会重新调用外部 LLM。

## 4. 环境前置条件

新一轮真实 Runner 的最小检查：

```text
1. 当前工作目录是 hk-ipo-risk-agents
2. Python 环境可用
3. scripts/run_v045_role_b_iteration.py 存在
4. configs/v045_competition_ai.yaml 存在
5. IPO_RISK_PROSPECTUS_ROOT 已设置且指向真实目录
6. LLM provider 环境变量存在
```

禁止打印 API Key、Secret、Authorization Header、完整请求 Body。

`IPO_RISK_PROSPECTUS_ROOT` 必须指向真实保存授权招股书 PDF 的根目录。不能指向空目录绕过 preflight，本机绝对路径不得提交 Git。

PowerShell 示例：

```powershell
$env:IPO_RISK_PROSPECTUS_ROOT="D:\path\to\authorized\prospectus_root"
Test-Path $env:IPO_RISK_PROSPECTUS_ROOT
```

必须返回 `True`。

注意：**offline recovery 不需要重新进入 real-LLM preflight**；它只读取已经存在的 iteration artifacts。

## 5. Lunamax/Codex 执行原则

Lunamax/Codex 在本任务中的角色只有一个：**执行器**。

禁止把任务扩展为架构分析、代码重构、模型研究或项目规划。

正常新一轮流程：

```text
检查最小运行条件
-> 冻结/读取 fixed-10
-> 运行一轮真实 LLM
-> Existing-Gold evaluator
-> 读取 iteration_summary.json
-> 读取 failure_focus.json
-> 输出 baseline
-> 停止
```

已经完成 real-LLM、仅 evaluator/summary 失败时：

```text
识别 existing iteration
-> offline recovery
-> Existing-Gold evaluator
-> iteration_summary.json
-> failure_focus.json
-> 输出 baseline
-> 停止
```

本轮不自动进入 Fixer。

## 6. 可直接复制给 Lunamax 的 canonical Runner 提示词

```text
你现在不是架构师，也不是研究员。

你的角色只有一个：执行已有的 fixed-10 Role-B 自动化流程，保存结果，并返回最小必要指标。

不要重新设计项目。
不要主动规划新架构。
不要扩展任务范围。
不要为了“做得更完整”修改无关代码。

=== 一、唯一目标 ===

在当前本地 hk-ipo-risk-agents 仓库和已经跑通的 LLM 环境下：

1. 确认当前 main 已有 fixed-10 runner 可用；
2. 冻结或读取 10 个 Development cases；
3. 顺序运行这 10 家真实 LLM 分析；
4. 自动执行 Existing-Gold evaluator；
5. 得到 M1、M2、Recall@1/@3/@5/@10/@20、case completion、real LLM completion、dominant failure；
6. 保存全部既有 artifact；
7. 输出一个简短总结；
8. 停止。

本任务不进行第二轮优化。

=== 二、严格禁止 ===

- 不扫描整个仓库；
- 不重新理解整个项目；
- 不重构架构；
- 不新增 Agent / Skill；
- 不改 Streamlit / Market Agent / M5；
- 不训练模型；
- 不做超参数搜索；
- 不修改 Existing Gold；
- 不新增人工 Gold；
- 不打开 2024 Validation；
- 不读取 2025 Blind outcome；
- 不自行更换 10 家公司；
- 不自行修改 metric；
- 不放宽 Evidence scope / Verifier；
- 不输出 API Key / Secret / Authorization Header；
- 不读取和总结巨量日志；
- 不主动创建长篇分析文档；
- 本轮不自动进入 Fixer。

除非现有 runner 无法启动，否则不允许修改代码。

=== 三、正式入口 ===

python scripts/run_v045_role_b_iteration.py --subset-only
python scripts/run_v045_role_b_iteration.py --iteration auto

不要重新实现 orchestration。

=== 四、Step 1：最小环境检查 ===

只检查：
1. 当前工作目录正确；
2. Python 可用；
3. runner 存在；
4. AI config 存在；
5. IPO_RISK_PROSPECTUS_ROOT 已设置；
6. LLM provider 所需环境变量存在。

只检查存在性，不输出 secret。
如果环境满足，立即继续，不额外运行大规模测试。

=== 五、Step 2：冻结 fixed-10 ===

检查：
reports/v045_role_b/fixed10_development_subset.json

如果文件已存在：直接读取，不重新生成、不替换、不重新选公司。
如果文件不存在：执行 `python scripts/run_v045_role_b_iteration.py --subset-only` 生成一次。

确认：
case_count = 10
split = development
validation_opened = false
blind_2025_outcome_accessed = false

fixed-10 的唯一权威来源是该 JSON。
禁止根据行业、知名度、PDF 长短、模型表现、Gold 数量或个人判断重新选公司。

=== 六、Step 3：第一轮真实运行 ===

执行：
python scripts/run_v045_role_b_iteration.py --iteration auto

不要人为拆成 10 个开放式任务，不要让多个 Agent 并发重新规划。

现有 runner 已负责：
preflight
-> fixed 10 sequential real LLM
-> artifact persistence
-> resume
-> evaluator
-> metrics
-> failure taxonomy

你只负责执行。

=== 七、运行中规则 ===

单家公司成功：继续下一家，不停下来分析。
单家公司失败：由 runner 记录，若支持 resume 则继续，不立刻改代码。
structured call 失败：本轮只记录，不立刻改 Prompt / Schema / Provider / Parser / Retriever。
程序中断：优先 resume，不删除已有 artifact。

日志只保留在现有本地日志位置。出现错误时最多提取 error category、case_id、component、return code，不总结巨量日志。

=== 八、Step 4：只读两份核心结果 ===

最新 iteration 下正常只读取：
iteration_summary.json
failure_focus.json

提取：
completed_cases
real_llm_cases
failed_cases
M1
M2
Recall@1/@3/@5/@10/@20
per-risk support / score
dominant_failure_reason
failure_count
affected_case_ids
affected_risk_codes

=== 九、停止规则 ===

第一轮完成后立即停止。
不要自动修代码、不要进入第二轮、不要自动优化 Prompt/Retriever。

Gate 只允许：
READY_FOR_FIXER
FIXED10_TARGET_REACHED
EXECUTION_BLOCKED

FIXED10_TARGET_REACHED 仅表示 debug subset M1>=80%、M2>=85%，不代表比赛正式 PASS。
如果 BLOCKED，只返回第一个 blocker。
```

## 7. `governed result missing case_id` 的固定恢复流程

如果真实 LLM 已经完成 10/10，但出现：

```text
EXECUTION_BLOCKED
ValueError: governed result missing case_id
```

不要再次执行：

```bash
python scripts/run_v045_role_b_iteration.py --iteration auto
```

也不要使用 `--force-case-rerun`。

只执行：

```bash
python scripts/recover_v045_role_b_iteration.py --iteration <existing_iteration_id>
```

canonical recovery prompt：

```text
继续上一次 fixed-10 Role-B baseline。

已确认：10/10 real-LLM analysis_result.json 已完成。
当前问题只在 Existing-Gold evaluator handoff / summary 阶段。

不要重新调用 LLM。
不要创建新 iteration。
不要 force rerun。
不要修改 Existing Gold。
不要打开 Validation。
不要访问 2025 Blind。

1. 确认当前 main 已包含 governed result case_id serialization 修复与 recover_v045_role_b_iteration.py。
2. 找到刚才完成 10/10 的 existing iteration id。
3. 执行：
   python scripts/recover_v045_role_b_iteration.py --iteration <existing_iteration_id>
4. 确认 external_llm_calls_added=0。
5. 只读取 iteration_summary.json 和 failure_focus.json。
6. 返回 M1、M2、Recall@1/@3/@5/@10/@20、dominant failure。
7. 停止，不自动进入下一轮优化。
```

recovery 必须 fail closed：

```text
persisted result != 10/10 -> BLOCK
subset hash mismatch -> BLOCK
iteration identity mismatch -> BLOCK
Validation flag != false -> BLOCK
Blind flag != false -> BLOCK
case_id conflict -> BLOCK
```

## 8. `IPO_RISK_PROSPECTUS_ROOT` blocker 恢复提示词

该 blocker 是历史/未来新一轮 Runner 的环境问题，不是当前 10/10 已完成 iteration 的首要问题。

如果新 iteration 输出：

```text
EXECUTION_BLOCKED
IPO_RISK_PROSPECTUS_ROOT is not set
```

直接使用：

```text
继续上一次 fixed-10 Role-B baseline 任务。

当前唯一 blocker 已确认：IPO_RISK_PROSPECTUS_ROOT 未设置。
你的任务仅限于解除这个环境配置 blocker，然后继续原有 runner。

不要修改任何代码。
不要修改 config。
不要重新生成 fixed-10。
不要选择新的公司。
不要扫描整个仓库。
不要开始 Fixer。
不要运行 Validation。
不要访问 2025 Blind。

1. 找到本机已经存在、并用于本项目的授权港股 IPO 招股书数据根目录；只检查现有项目相关位置，不扫描整个磁盘。
2. 确认该目录能够提供当前 fixed-10 所需招股书数据。
3. 在当前 shell/process 中设置 IPO_RISK_PROSPECTUS_ROOT=<实际根目录>。
4. 验证环境变量非空、路径存在、是目录。
5. 不修改 repository 文件，不把本机绝对路径提交 Git。
6. 直接重新执行：python scripts/run_v045_role_b_iteration.py --iteration auto
7. 让 runner 完整执行 fixed-10 real LLM -> evaluator -> iteration_summary.json -> failure_focus.json。
8. 完成后只读两份摘要并按原 Runbook 输出指标，然后停止。
9. 如果仍然 BLOCKED，只返回新的第一个 blocker，不自行修代码。
```

## 9. Runner/Fixer 分离

本 Runbook 只负责 Runner / Offline Recovery。

当 baseline summary 真正生成后，再单独开启一个短上下文 Fixer 任务：

```text
只读取最新 failure_focus.json。
只处理 dominant_failure_reason。
只读与该 failure 直接相关的模块和测试。
做一个最小修改 + regression test 后停止。
不要运行 Validation。
不要修改 Existing Gold。
不要同时处理第二类 failure。
```

推荐节奏：

```text
Runner
-> score
-> dominant failure
-> Fixer
-> next Runner iteration
```

若 Runner 已完成 real-LLM 但 evaluator handoff 失败：

```text
Offline Recovery
-> score
-> dominant failure
-> Fixer
```

不要把 Runner 与 Fixer 合并到一个长上下文任务中。

## 10. fixed-10 目标与正式比赛 Gate

fixed-10 内部调试目标：

```text
M1 >= 0.80
M2 >= 0.85
```

但 fixed-10 永远不是正式比赛 PASS。

达到可接受稳定性后必须转入：

```text
ALL 79 Development
-> freeze code/prompt/evaluator/runtime
-> one-shot ALL 19 Validation
```

正式项目目标继续是：

```text
M1 official >= 0.80
M1 project target >= 0.85
M2 official >= 0.85
M2 project target >= 0.88
```

Validation 不允许用于 post-hoc tuning，2025 Blind outcome 继续禁止访问。
