# v0.4.5 Role-B Fixed-10 Development Iteration Workflow

本文件定义 Role B 在 Metric Protocol v2 下的固定 10 家 Development 快速迭代流程。目标是把长时间的真实 LLM 执行从 Codex 的开放式任务，收敛成一个可重复、可恢复、低上下文消耗的脚本任务。

当前操作层总计划见 `V045_CURRENT_EXECUTION_PLAN.md`，Lunamax/Codex 直接执行模板见 `V045_ROLE_B_LUNAMAX_AUTOMATION_RUNBOOK.md`。

## 1. 适用范围

本流程只用于 Development 调试与优化，不是最终比赛 PASS 范围。

```text
Existing Expert Gold official cases = 98
Development evaluable cases         = 79
Validation evaluable cases          = 19
```

Existing-Gold coverage audit：

```text
manifest_hash = fcd12d34fcc64853ed778d0026b1e2c943a863549cd1652c6ced7c6145214d1c
primary positive risk units = 128
primary evidence units      = 217
```

Primary risk support：

```text
cash_burn_pressure         16
customer_concentration     32
redemption_rights          39
supplier_concentration     41
related_party_transaction   0 -> NOT_EVALUABLE_FROM_EXISTING_GOLD
```

## 2. 真实 LLM runtime 前提

当前已验证真实 runtime：

```text
provider = openai_responses
model = ark-code-latest
llm_timeout_seconds = 300
llm_max_retries = 0
```

1167.HK (`ipo_2020_01167`) 已完成真实 PDF 全流程 smoke：

```text
status = completed
Final Supervisor = available / accepted
deterministic fallback = false
scope guard = PASS
Validation accessed = false
2025 Blind accessed = false
```

该单案例只证明 runtime 可用，不关闭 M1/M2 或最终 E1 3-case Gate。

## 3. 当前本地执行状态

2026-08-27 本地 constrained Lunamax/Codex Runner 已能够正确进入现有脚本，并在缺失环境前置条件时 fail-closed，而没有擅自改代码。

最近一次状态：

```text
EXECUTION_BLOCKED
blocker = IPO_RISK_PROSPECTUS_ROOT is not set
```

该 blocker 只需要设置本地授权招股书根目录，不需要修改代码。`IPO_RISK_PROSPECTUS_ROOT` 必须指向真实存在的 PDF 数据根目录；本机绝对路径不得提交 Git。

PowerShell 示例：

```powershell
$env:IPO_RISK_PROSPECTUS_ROOT="D:\path\to\authorized\prospectus_root"
Test-Path $env:IPO_RISK_PROSPECTUS_ROOT
```

返回 `True` 后继续原 runner。

## 4. fixed-10 的权威来源

第一次运行：

```bash
python scripts/run_v045_role_b_iteration.py --subset-only
```

脚本从 Existing-Gold Development 中确定性选择 10 家，优先覆盖：

```text
cash_burn_pressure
customer_concentration
redemption_rights
supplier_concentration
```

并将 subset 与 Existing-Gold coverage manifest hash 绑定。Validation 和 2025 Blind 不允许进入 subset。

当前 Metric-v2 fixed-10 唯一权威来源：

```text
reports/v045_role_b/fixed10_development_subset.json
```

如果该文件已经存在，不重新生成、不重新选择公司。

## 5. 手工 smoke / 历史 benchmark 参考 10 家

下列 10 家是历史 Role-B real-LLM Development benchmark 参考集合，用于环境 smoke、人工核对、公司名映射与历史比较；**它们不覆盖当前自动生成的 Metric-v2 fixed-10**。

| # | case_id | stock_code | company_name | industry |
|---:|---|---|---|---|
| 1 | `ipo_2020_01167` | `1167.HK` | 加科思─B | 生物技术 |
| 2 | `ipo_2020_01942` | `1942.HK` | MOG Holdings | 支付服务 |
| 3 | `ipo_2020_01961` | `1961.HK` | 九尊数字互娱 | 游戏软件 |
| 4 | `ipo_2020_09600` | `9600.HK` | 新纽科技 | 应用软件 |
| 5 | `ipo_2020_09633` | `9633.HK` | 农夫山泉 | 非酒精饮料 |
| 6 | `ipo_2021_09898` | `9898.HK` | 微博─SW | 互动媒体及服务 |
| 7 | `ipo_2022_06698` | `6698.HK` | 星空华文 | 影视娱乐 |
| 8 | `ipo_2022_09863` | `9863.HK` | 零跑汽车 | 汽车 |
| 9 | `ipo_2023_02451` | `2451.HK` | 绿源集团控股 | 摩托车及其他 |
| 10 | `ipo_2023_02517` | `2517.HK` | 锅圈 | 包装食品 |

需要展示当前正式 fixed-10 公司名称时，只通过：

```text
data/catalog/ipo_official_master_bridge.csv
```

做 `case_id -> stock_code -> selected_name` 映射。

## 6. 每一轮运行

直接执行：

```bash
python scripts/run_v045_role_b_iteration.py --iteration auto
```

脚本自动完成：

```text
runtime preflight
-> fixed 10 cases sequential real-LLM run
-> per-case artifact persistence
-> resume-safe collection
-> analysis_results.jsonl
-> Existing-Gold evaluator
-> M1 / M2 / Recall@K
-> failure taxonomy
-> previous-iteration comparison
```

每轮使用新的 iteration id，例如 `iter_001`、`iter_002`。代码 fingerprint 改变后，不允许静默复用旧 iteration 结果。

## 7. 本地输出

正常迭代只关注：

```text
iteration_summary.json
failure_focus.json
```

`iteration_summary.json`：

```text
case completion
real-LLM count
M1
M2
Recall@1/@3/@5/@10/@20
per-risk support / score
previous iteration delta
```

`failure_focus.json`：

```text
dominant_failure_reason
affected_case_ids
risk_codes
failure counts
```

大体量 stdout/stderr 留在 gitignored 本地日志，不应输入 Codex/Lunamax 上下文。

## 8. Runner 模式

Runner 只执行，不开放式推理：

```text
执行 python scripts/run_v045_role_b_iteration.py --iteration auto。
不要扫描仓库。
不要修改代码。
不要分析完整日志。
完成后只读取 iteration_summary.json 和 failure_focus.json，返回核心指标并停止。
```

完整 canonical prompt 见 `V045_ROLE_B_LUNAMAX_AUTOMATION_RUNBOOK.md`。

如果 preflight 返回 `IPO_RISK_PROSPECTUS_ROOT` blocker，只设置环境变量后重试，不改代码。

## 9. Fixer 模式

Fixer 必须单独开短任务：

```text
只读取最新 failure_focus.json。
只处理 dominant_failure_reason。
只读直接相关模块和测试。
做一个最小修改 + regression test 后停止。
不要运行 Validation。
不要修改 Existing Gold。
不要同时处理第二类 failure。
```

循环：

```text
Runner
-> score
-> dominant failure
-> STOP
-> Fixer
-> STOP
-> next Runner iteration
```

## 10. 防过拟合规则

建议节奏：

```text
fixed-10 baseline
-> 2-4 rounds targeted iteration at most
-> larger Development checkpoint
-> ALL 79 Development
-> freeze
-> one-shot ALL 19 Validation
```

固定 10 家只用于 debug，永远不能声称正式比赛 PASS。

## 11. 正式 Full Development

```text
ALL evaluable Existing Development Gold = 79 cases
```

正式 evaluator 需满足：

```text
M1 official >= 0.80
M1 project target >= 0.85
M2 official >= 0.85
M2 project target >= 0.88
```

Full Development 完成后冻结：

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

之后只允许一次性打开全部 19 个 Existing Validation cases，禁止根据 Validation 结果回头调参。

## 12. 治理约束

```text
new_manual_annotations_added = false
existing_gold_modified = false
Validation tuning = forbidden
2025 Blind access = forbidden
mock/fallback cannot count as real-LLM measurement
unjudged != negative
```

禁止为了 fixed-10 分数：

- 修改 Expert Gold；
- 新增 negative Gold；
- 人工重组 Evidence；
- 对 Validation 做试跑；
- 伪造 Evidence；
- 放宽 Schema / Verifier 来掩盖非法输出；
- 将 debug subset 成绩包装成正式比赛 PASS。
