# v0.4.5 Current Execution Plan — Fixed-10 to Competition Closure

> Status date: 2026-08-27
>
> Competition runtime: `v0.4.5`
>
> Metric protocol: `v045_competition_metric_protocol_v2_existing_gold_only`
>
> Current verdict: **NOT YET COMPETITION_READY**

本文件把当前比赛收尾计划、Role-B fixed-10 公司口径、Lunamax/Codex 自动执行方式、已知 blocker 与后续 Gate 顺序收敛为一个操作层计划。Gate 的唯一状态源仍是 `V0.4_RELEASE_ACCEPTANCE.md`；指标定义仍以 `COMPETITION_METRIC_PROTOCOL.md` 为准。

## 1. 当前执行状态

当前 Role-B 策略已经从“让 Codex 自由分析仓库”切换为“Runner only”。本地 constrained Lunamax/Codex 已经完成最近一轮 fixed-10 的 10/10 真实 LLM 分析，并保持：

```text
Validation opened = false
2025 Blind accessed = false
```

当前 blocker 已从此前的本地 PDF 根目录环境问题推进到 evaluator handoff：

```text
EXECUTION_BLOCKED
ValueError: governed result missing case_id
```

这不是 LLM、Prompt、Retriever、Gold 或 evaluator metric 定义问题。根因是 runner 汇总 `analysis_results.jsonl` 时没有把外层已知的 canonical `case_id` 写入 governed row。

当前代码已修复该 serialization contract：

```text
- JSONL row 始终携带 canonical case_id；
- metadata.case_id / top-level case_id 如已存在，必须与 expected case_id 一致；
- 不一致时 fail closed；
- 不修改原始 analysis_result.json；
- evaluator contract 不放宽。
```

因为这 10 家真实 LLM 已经完成，当前立即动作不是重新跑模型，而是离线恢复评分：

```bash
python scripts/recover_v045_role_b_iteration.py --iteration <existing_iteration_id>
```

恢复脚本只复用当前 iteration 下既有：

```text
run/<case_id>/analysis_result.json
```

并重建：

```text
analysis_results.jsonl
iteration_summary.json
failure_focus.json
```

恢复路径约束：

```text
external_llm_calls_added = 0
Validation = false
2025 Blind = false
```

当前操作顺序：

```text
pull latest main
-> identify completed fixed-10 iteration id
-> offline recover Existing-Gold score
-> read M1/M2/Recall@K + failure_focus
-> stop
```

在 recovery summary 真正生成前，不对 M1/M2 数值做任何宣称。

## 2. fixed-10 的两个口径必须分开

### 2.1 Metric-v2 正式 debug subset

当前 Metric-v2 fixed-10 的唯一权威来源是本地生成文件：

```text
reports/v045_role_b/fixed10_development_subset.json
```

若不存在，由当前 `main` 的确定性选择器生成：

```bash
python scripts/run_v045_role_b_iteration.py --subset-only
```

选择器只从 Existing-Gold Development 中选择 10 家，并优先平衡：

```text
cash_burn_pressure
customer_concentration
redemption_rights
supplier_concentration
```

生成后不再重选。Validation 与 2025 Blind 不允许进入该 subset。

### 2.2 手工 smoke / 历史 benchmark 参考 10 家

下列 10 家是此前 Role-B real-LLM Development benchmark 已冻结使用过的参考集合。它们用于环境 smoke、人工核对、公司名映射和历史可比性；**不覆盖**当前 Metric-v2 本地自动生成的 fixed-10。

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

保留它们作为 smoke 参考的理由是：

```text
- 已存在历史 frozen benchmark identity；
- 跨 2020–2023 Development cohort；
- 覆盖软件、生物科技、消费、媒体、汽车等不同招股书形态；
- official master bridge 已有稳定 case_id / stock_code / company_name 映射；
- 1167.HK 已有真实 provider 全流程成功证据。
```

再次强调：正式 fixed-10 仍以本地 `fixed10_development_subset.json` 为准。

## 3. canonical Lunamax/Codex Runner 提示词

以下提示词是当前默认 Runner prompt。它的设计目标不是“让模型更聪明”，而是降低自由度，让模型只执行已有自动化。

```text
你现在不是架构师，也不是研究员。

你的角色只有一个：执行已有的 fixed-10 Role-B 自动化流程，保存结果，并返回最小必要指标。

不要重新设计项目。
不要主动规划新架构。
不要扩展任务范围。
不要为了“做得更完整”修改无关代码。

唯一目标：
1. 确认当前 main 已有 fixed-10 runner 可用；
2. 冻结或读取 10 个 Development cases；
3. 顺序运行这 10 家真实 LLM 分析；
4. 自动执行 Existing-Gold evaluator；
5. 输出 M1、M2、Recall@1/@3/@5/@10/@20、case completion、real-LLM completion、dominant failure；
6. 保存已有 artifact；
7. 输出简短总结；
8. 停止。

严格禁止：
- 不扫描整个仓库；
- 不重构架构；
- 不新增 Agent / Skill；
- 不改 Streamlit / Market / M5；
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
- 本轮不自动进入 Fixer。

正式入口：
python scripts/run_v045_role_b_iteration.py --subset-only
python scripts/run_v045_role_b_iteration.py --iteration auto

最小环境检查只包括：
1. 当前目录正确；
2. Python 可用；
3. runner 存在；
4. AI config 存在；
5. IPO_RISK_PROSPECTUS_ROOT 已设置；
6. LLM provider 所需环境变量存在。

fixed-10 唯一权威来源：
reports/v045_role_b/fixed10_development_subset.json

如文件存在，直接读取，不重新生成、不重新选择公司。
如文件不存在，执行 --subset-only 生成一次。

第一轮执行：
python scripts/run_v045_role_b_iteration.py --iteration auto

runner 已负责：
preflight
-> fixed 10 sequential real LLM
-> artifact persistence
-> resume
-> evaluator
-> metrics
-> failure taxonomy

你只负责执行。

运行后只读取：
iteration_summary.json
failure_focus.json

最终只输出：
Fixed-10 company table
completed_cases / real_llm_cases / failed_cases
M1 / M2 / Recall@1/@3/@5/@10/@20
dominant_failure_reason / affected_cases / affected_risks / failure_count

Gate 只允许：
READY_FOR_FIXER
FIXED10_TARGET_REACHED
EXECUTION_BLOCKED

如果 BLOCKED，只返回第一个 blocker。
如果 baseline 正常产生，本轮立即停止，不自动修代码。
```

## 4. 当前 blocker：case identity handoff 与离线恢复

### 4.1 已修复的 runner contract

`run_v045_role_b_iteration.py` 在写 `analysis_results.jsonl` 时，现在使用外层 frozen subset 的 canonical `case_id` 作为权威 identity。

规则：

```text
expected_case_id = current fixed-10 case id

if metadata.case_id exists:
    require metadata.case_id == expected_case_id

if top-level case_id exists:
    require top-level case_id == expected_case_id

output JSONL row.case_id = expected_case_id
```

任何冲突都 fail closed，不做静默覆盖。

### 4.2 已完成 10/10 时的 recovery

如果某个 existing iteration 已经有 10/10 `analysis_result.json`，但 evaluator/summary 阶段失败，禁止重新调用真实 LLM。

只执行：

```bash
python scripts/recover_v045_role_b_iteration.py --iteration <existing_iteration_id>
```

该命令会：

```text
verify existing iteration context
verify frozen subset hash
verify Validation=false / Blind=false
verify persisted result count = 10/10
rebuild governed analysis_results.jsonl with canonical case_id
run Existing-Gold evaluator
write iteration_summary.json
write failure_focus.json
```

该命令不会调用：

```text
run_v04_role_e_demo.py
external LLM provider
new fixed-10 selection
Validation
2025 Blind outcome
```

期望输出明确包含：

```text
external_llm_calls_added=0
```

### 4.3 历史 `IPO_RISK_PROSPECTUS_ROOT` blocker

此前曾出现：

```text
EXECUTION_BLOCKED
IPO_RISK_PROSPECTUS_ROOT is not set
```

该环境 blocker 已不再是当前首要问题，因为最近一轮 10/10 real-LLM analysis 已经完成。未来新 iteration 若再次遇到该问题，仍只修环境、不修代码。

## 5. Runner / Fixer 必须分离

第一轮 baseline 只测量，不边跑边修。

```text
Runner
-> score
-> dominant failure
-> STOP
```

如果 Runner 的 real-LLM analysis 已经完成、仅 evaluator handoff 失败：

```text
Offline Recovery
-> score
-> dominant failure
-> STOP
```

下一次单独启动短上下文 Fixer：

```text
只读取最新 failure_focus.json。
只处理 dominant_failure_reason。
只读与该 failure 直接相关的模块和测试。
做一个最小修改 + regression test 后停止。
不要运行 Validation。
不要修改 Existing Gold。
不要同时修第二类问题。
```

之后再进入下一 Runner iteration。

## 6. 当前比赛收尾顺序

### Phase B1 — fixed-10 baseline（当前）

```text
10/10 real-LLM analysis 已完成
-> offline recover Existing-Gold evaluator handoff
-> M1/M2/Recall@K baseline
-> failure taxonomy
```

### Phase B2 — fixed-10 targeted optimization

最多快速迭代 2–4 轮：

```text
Runner
-> dominant failure
-> one minimal Fixer
-> Runner
```

fixed-10 内部目标：

```text
M1 >=0.80
M2 >=0.85
```

达到目标只表示 debug subset 稳定，不表示比赛 PASS。

### Phase B3 — Full Development

```text
ALL 79 evaluable Existing Development cases
```

正式 Development 目标：

```text
M1 official >=0.80
M1 project target >=0.85
M2 official >=0.85
M2 project target >=0.88
```

Full Development 后冻结：

```text
code SHA
Prompt version
Retriever config
schema / normalization
Verifier rules
evaluator version
Existing-Gold manifest hash
provider / model runtime settings
```

### Phase B4 — Validation one-shot

冻结后仅允许：

```text
ALL 19 evaluable Existing Validation cases
```

Validation 结果不得用于回头调 Prompt、Retriever、Verifier 或 metric。

### Parallel P0 — Role D M5

必须物化：

```text
return_1d
return_5d
return_20d
return_60d
test_predictions.csv
multi_horizon_results.csv
evaluation_summary.json
ai_vs_offline_report.json
```

### P1 — C/E final matrix

完成：

```text
C: final governed Market trace
E: 2410.HK / 2460.HK / 1318.HK real-provider 3/3 accepted
M3 final traceability =1.0
M4 current explanation-quality Gate
```

### Final — A readiness / package

```text
latest-main CI
Blind / provenance / determinism
metric dashboard
artifact index
security audit
submission bundle
release freeze
-> COMPETITION_READY
```

## 7. 当前明确不做

```text
任何新的 M1/M2 人工 Gold
Gold 修改或补 negative
Validation tuning
2025 Blind outcome access
full 438-case LLM run
broad model search
full Retriever rewrite
PR-F replacement training
ComparableIPOSkill
presentation-only UI expansion
无 PIT 证据的 market proxy
```

## 8. 当前 hard Gate 摘要

```text
B0 Existing-Gold audit              PASS
B1 M1 real-LLM Development          OPEN / P0
B2 M2 Evidence Coverage             OPEN / P0
D1 M5 multi-horizon                 OPEN / P0
C1 final Market validation          OPEN / P1
E1 final 3-case real provider       OPEN / P1
E2 explanation quality              OPEN / P1
A1 final readiness/package          OPEN / P1
```

当前最重要的不是增加新功能，也不是重新跑已经完成的 10 家，而是先离线恢复这批 persisted results 的 M1/M2/Recall@K 与 `failure_focus.json`，然后再依据 dominant failure 做最小闭环。
