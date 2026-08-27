# v0.4.5 Role-B Lunamax Fixed-10 Automation Runbook

本文档用于把 Role-B fixed-10 真实 LLM Development 迭代收敛成一个低自由度、低上下文、可恢复的自动执行任务。

目标不是让 Lunamax/Codex 重新设计项目，而是让它只做 Runner：冻结/读取 fixed-10，执行现有 runner，读取两份摘要，返回指标后停止。

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

## 2. 手工 smoke 参考 10 家

以下 10 家曾用于旧版 Role-B real-LLM Development smoke/benchmark，可用于人工核对、环境 smoke 或公司名称映射参考；它们**不覆盖**当前 Metric-v2 自动生成的正式 fixed-10：

| # | case_id | stock_code | company_name |
|---:|---|---|---|
| 1 | `ipo_2020_01167` | `1167.HK` | 加科思─B |
| 2 | `ipo_2020_01942` | `1942.HK` | MOG Holdings |
| 3 | `ipo_2020_01961` | `1961.HK` | 九尊数字互娱 |
| 4 | `ipo_2020_09600` | `9600.HK` | 新纽科技 |
| 5 | `ipo_2020_09633` | `9633.HK` | 农夫山泉 |
| 6 | `ipo_2021_09898` | `9898.HK` | 微博─SW |
| 7 | `ipo_2022_06698` | `6698.HK` | 星空华文 |
| 8 | `ipo_2022_09863` | `9863.HK` | 零跑汽车 |
| 9 | `ipo_2023_02451` | `2451.HK` | 绿源集团控股 |
| 10 | `ipo_2023_02517` | `2517.HK` | 锅圈 |

如果需要展示当前正式 fixed-10 的公司名称，只允许通过已有：

```text
data/catalog/ipo_official_master_bridge.csv
```

做 `case_id -> stock_code -> selected_name` 映射。

## 3. Lunamax/Codex 执行原则

Lunamax/Codex 在本任务中的角色只有一个：**执行器**。

禁止把任务扩展为架构分析、代码重构、模型研究或项目规划。

本轮唯一流程：

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

本轮不自动进入 Fixer。

## 4. 可直接复制给 Lunamax 的提示词

```text
你现在不是架构师，也不是研究员。

你的角色只有一个：
执行已有的 fixed-10 Role-B 自动化流程，保存结果，并返回最小必要指标。

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
5. 得到：
   - M1
   - M2
   - Recall@1
   - Recall@3
   - Recall@5
   - Recall@10
   - Recall@20
   - case completion
   - real LLM completion
   - dominant failure
6. 保存全部既有 artifact；
7. 输出一个简短总结；
8. 停止。

本任务不进行第二轮优化。

=== 二、严格禁止 ===

- 不要扫描整个仓库；
- 不要重新理解整个项目；
- 不要重构架构；
- 不要新增 Agent；
- 不要新增 Skill；
- 不要改 Streamlit；
- 不要改 Market Agent；
- 不要改 M5；
- 不要训练任何模型；
- 不要做超参数搜索；
- 不要修改 Existing Gold；
- 不要新增人工 Gold；
- 不要打开 2024 Validation；
- 不要读取 2025 Blind outcome；
- 不要自行更换 10 家公司；
- 不要自行修改 metric 定义；
- 不要为了提高成绩放宽 Evidence scope；
- 不要为了提高成绩放宽 Verifier；
- 不要输出 API Key；
- 不要读取和总结巨量日志；
- 不要主动创建长篇分析文档。

除非现有 runner 无法启动，否则不允许修改代码。

=== 三、正式入口 ===

优先使用现有脚本，不要重新实现 orchestration：

python scripts/run_v045_role_b_iteration.py --subset-only

python scripts/run_v045_role_b_iteration.py --iteration auto

=== 四、Step 1：最小环境检查 ===

只检查：

1. 当前工作目录是 hk-ipo-risk-agents；
2. Python 环境可用；
3. scripts/run_v045_role_b_iteration.py 存在；
4. configs/v045_competition_ai.yaml 存在；
5. IPO_RISK_PROSPECTUS_ROOT 已设置；
6. LLM provider 所需环境变量已存在。

只检查“是否存在”。
禁止打印 API Key、Secret、Authorization Header、完整请求 Body。

如果环境满足，立即继续。
不要额外运行大规模测试。

=== 五、Step 2：冻结 fixed-10 ===

检查：
reports/v045_role_b/fixed10_development_subset.json

如果文件已经存在：
- 直接读取；
- 不要重新生成；
- 不要替换；
- 不要重新选择公司。

如果文件不存在：
执行：
python scripts/run_v045_role_b_iteration.py --subset-only

然后读取：
reports/v045_role_b/fixed10_development_subset.json

确认：
case_count = 10
split = development
validation_opened = false
blind_2025_outcome_accessed = false

从现在开始整个任务只处理这 10 家。

fixed-10 的唯一权威来源是：
reports/v045_role_b/fixed10_development_subset.json

禁止根据行业、公司知名度、PDF 长短、模型表现、Gold 数量或个人判断重新选择公司。

如需公司名称，只通过：
data/catalog/ipo_official_master_bridge.csv
做 case_id -> stock_code -> selected_name 映射。

=== 六、Step 3：第一轮真实运行 ===

执行：
python scripts/run_v045_role_b_iteration.py --iteration auto

让命令自身完成。
不要人为拆成 10 个开放式任务。
不要让多个 Agent 并发重新规划。

现有 runner 已负责：
preflight
-> fixed 10 cases
-> sequential real LLM
-> artifact persistence
-> resume
-> evaluator
-> metrics
-> failure taxonomy

你只负责执行。

=== 七、运行过程处理规则 ===

单家公司成功：继续下一家，不停下来分析。

单家公司失败：如果 runner 已支持 fail-closed / resume，记录失败并继续，不要立刻改代码。

LLM structured call 失败：本轮只记录。不要立即改 Prompt、Schema、Provider、Parser、Retriever。

程序中断：优先使用现有 resume 机制继续。不要删除已有 iteration artifact。除非 runner 明确要求，不要从第一家全部重跑。

=== 八、日志规则 ===

不要把完整 stdout/stderr 加入上下文。
日志保持在 runner 原本指定的位置。

如发生错误，只提取：
- error category
- affected case_id
- affected component
- return code

最多查看错误附近必要的少量内容。
不要总结几千行日志。

=== 九、Step 4：只读两份核心结果 ===

找到最新 iteration，例如：
reports/v045_role_b/iterations/iter_001/

正常情况下只读取：
iteration_summary.json
failure_focus.json

除非这两个文件缺少关键字段，否则不要继续打开大量 artifact。

从 iteration_summary.json 提取：
- iteration_id
- 10 家公司完成数
- 真实 LLM 成功 case 数
- M1 official-aligned accuracy
- M2 Evidence Coverage Recall
- Recall@1
- Recall@3
- Recall@5
- Recall@10
- Recall@20
- per-risk support
- per-risk score
- 与上一轮 delta（如有）

从 failure_focus.json 提取：
- dominant_failure_reason
- failure_count
- affected_case_ids
- affected_risk_codes

=== 十、不要自动进入 Fixer ===

第一轮完成后停止。

不要看到 M1/M2 不达标后自动修改代码。
不要继续第二轮。
不要自己开始优化 Prompt。
不要自己修 Retriever。

这一轮唯一任务是：
fixed-10
-> 真实运行
-> evaluator
-> baseline
-> failure 分类
-> 停止

=== 十一、最终输出格式 ===

Fixed-10：
case_id | stock_code | company_name
共 10 行。

Runtime：
completed_cases = x/10
real_llm_cases = x/10
failed_cases = x

Metrics：
M1 = xx.xx%
M2 = xx.xx%
Recall@1  = xx.xx%
Recall@3  = xx.xx%
Recall@5  = xx.xx%
Recall@10 = xx.xx%
Recall@20 = xx.xx%

Main failure：
dominant_failure_reason =
affected_cases =
affected_risks =
failure_count =

Gate 只允许以下三种：

READY_FOR_FIXER
- baseline 正常产生，但指标仍需优化。

FIXED10_TARGET_REACHED
- fixed-10 M1 >= 80% 且 M2 >= 85%。
- 这只代表 debug subset 达标，不代表比赛正式 PASS。

EXECUTION_BLOCKED
- runner 未能产生有效 baseline。
- 如果 BLOCKED，只额外输出一个最主要 blocker。

=== 十二、成功条件 ===

本任务成功条件只有：
- fixed-10 成功冻结/读取；
- 10 家自动化流程执行完成或被 runner 正确记录失败；
- 真实 LLM 状态被正确记录；
- Existing-Gold evaluator 执行完成；
- iteration_summary.json 存在；
- failure_focus.json 存在；
- M1/M2/Recall@K 被输出；
- 没有访问 Validation；
- 没有访问 Blind；
- 没有修改 Gold；
- 没有进行无关重构。

做到这些立即停止。
不要继续思考还能做什么。
不要提出新的架构方案。
不要开始下一阶段工作。
```

## 5. Runner/Fixer 分离

本 Runbook 只负责 Runner。

当一轮 baseline 完成后，再单独开启一个短上下文 Fixer 任务。Fixer 只能读取本轮 `failure_focus.json`，只处理 `dominant_failure_reason`，做一个最小修改和 regression test 后停止。

推荐节奏：

```text
Runner
-> score
-> dominant failure
-> Fixer
-> next Runner iteration
```

不要把 Runner 与 Fixer 合并到一个长上下文任务中。

## 6. fixed-10 目标与正式比赛 Gate

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
