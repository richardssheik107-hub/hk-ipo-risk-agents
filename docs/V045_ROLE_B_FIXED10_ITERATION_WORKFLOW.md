# v0.4.5 Role-B Fixed-10 Development Iteration Workflow

本文件定义 Role B 在 Metric Protocol v2 下的固定 10 家 Development 快速迭代流程。目标是把长时间的真实 LLM 执行从 Codex 的开放式任务，收敛成一个可重复、可恢复、低上下文消耗的脚本任务。

## 1. 适用范围

本流程只用于 Development 调试与优化，不是最终比赛 PASS 范围。

```text
Existing Expert Gold official cases = 98
Development evaluable cases         = 79
Validation evaluable cases          = 19
```

Existing-Gold coverage audit 已完成：

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
related_party_transaction   0  -> NOT_EVALUABLE_FROM_EXISTING_GOLD
```

这些总量覆盖 Development + Validation；固定 10 家和正式 Full Development 的分母均由 evaluator 按实际 scope 自动计算。

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
Gate E1 for this smoke case = PASS
deterministic fallback = false
scope guard = PASS
Validation accessed = false
2025 Blind accessed = false
```

该单案例 smoke 只证明 runtime 可用，不关闭最终 E1 3-case Gate，也不证明 M1/M2 已达标。

## 3. 第一次固定 10 家

运行：

```bash
python scripts/run_v045_role_b_iteration.py --subset-only
```

脚本会从 Existing-Gold Development 中确定性选择 10 家，优先覆盖：

```text
cash_burn_pressure
customer_concentration
redemption_rights
supplier_concentration
```

并将 subset 与 Existing-Gold coverage manifest hash 绑定。Validation 和 2025 Blind 不允许进入 subset。

首次生成的固定 subset 之后保持不变，用于纵向比较不同代码版本。

## 4. 每一轮运行

直接运行：

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

每轮使用新的 iteration id，例如：

```text
iter_001
iter_002
iter_003
```

如果代码 fingerprint 已改变，旧 iteration 结果不能被静默复用。

## 5. 本地输出

详细产物位于 gitignored `reports/` 下。正常迭代只需要关注：

```text
iteration_summary.json
failure_focus.json
```

`iteration_summary.json` 负责：

```text
case completion
real-LLM count
M1
M2
Recall@1/@3/@5/@10/@20
per-risk support / score
与上一轮 delta
```

`failure_focus.json` 负责给下一轮优化提供最小失败面，例如：

```text
dominant_failure_reason
affected_case_ids
risk_codes
failure counts
```

大体量 subprocess stdout/stderr 保存为本地日志，不应直接灌入 Codex 上下文。

## 6. Codex 低 Token 使用方式

### Runner 模式

给 Codex 的指令只需要：

```text
执行：
python scripts/run_v045_role_b_iteration.py --iteration auto

不要扫描仓库。
不要修改代码。
不要分析完整日志。
完成后只读取 iteration_summary.json 和 failure_focus.json，返回核心指标。
```

Runner 的职责只是执行，不做开放式推理。

### Fixer 模式

单独开启一个新的短上下文任务：

```text
只读取本轮 failure_focus.json。
只处理 dominant failure。
只读与该 failure 直接相关的模块和测试。
做一个最小修改 + regression test 后停止。
不要运行 Validation。
不要修改 Existing Gold。
```

建议循环：

```text
Runner
-> score
-> dominant failure
-> Fixer
-> next Runner iteration
```

## 7. 防过拟合规则

固定 10 家只用于快速开发。不要无限对这 10 家调优。

建议节奏：

```text
固定 10 家快速迭代 2-4 轮
-> 做一次更大 Development checkpoint
-> 若失败模式一致，再回固定 10 家优化
-> 最后跑 ALL 79 Development
-> freeze
-> one-shot 19 Validation
```

正式比赛 PASS 只能由 full-split evaluator 判定；`--case-ids` / fixed-10 debug subset 永远不能声称正式 PASS。

## 8. 正式 Full Development

固定 10 家达到可接受稳定性后，转为：

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

## 9. 治理约束

固定 10 家 workflow 继承 Metric Protocol v2 的全部限制：

```text
new_manual_annotations_added = false
existing_gold_modified = false
Validation tuning = forbidden
2025 Blind access = forbidden
mock/fallback cannot count as real-LLM measurement
unjudged != negative
```

禁止为了提升 fixed-10 分数：

- 修改 Expert Gold；
- 新增 negative Gold；
- 人工重组 Evidence；
- 对 Validation 做试跑；
- 伪造 Evidence；
- 放宽 Schema / Verifier 来掩盖非法输出；
- 将 debug-subset 成绩包装成正式比赛 PASS。
