# Person 1 — M1 / M2 Document Intelligence Owner — CLOSED

> 状态日期：`2026-08-30`  
> Runtime freeze main：`ab3390cc548f3d4ec7f08d5d39350a3c1baf1f0a`  
> Benchmark SHA：`dcc36abd30ec42cd1d6b83bc6d70b2d1aa74f61b`  
> 当前状态：**DEVELOPMENT CLOSED / G2 BELOW SELF-DEFINED TARGET**

## 1. Final ALL79 result

| 模式 | Cases | M1 | M2 |
|---|---:|---:|---:|
| Best offline | 79/79 | **70/102 = 68.63%** | **103/191 = 53.93%** |
| Real LLM gated | 79/79 | **61/102 = 59.80%** | **93/191 = 48.69%** |

正式目标仍为：

```text
M1 >= 0.80
M2 >= 0.85
real_llm_cases = 79/79
```

因此：

```text
real LLM 79/79 = PASS
M1 = BLOCKED
M2 = BLOCKED
G2 = BLOCKED
```

机器事实源：`reports/v045_role_b/document_benchmark_summary.json`。

## 2. 当前决定

比赛提交时间已进入最后收口，Person 1 不再继续 Development 优化。

```text
AUTO_CONTINUE = FALSE
DEVELOPMENT_TUNING = STOP
VALIDATION_DRIVEN_TUNING = FORBIDDEN
```

较高的 offline 指标作为工程参考保留，但不能替代 real-provider gated 指标。

## 3. 最终保留的工程收益

最终 main 已吸收本轮 Role-B 的通用修复与治理增强，包括：

- concentration track-record lifecycle / companion-period binding；
- cash conflict 与 bounded concentration reconciliation；
- supplier deeper Evidence retention；
- fail-closed redemption / granted pre-IPO special-rights recognition；
- structured smoke 从 3-task 升级到冻结 profile 的完整 4-task identity；
- full-Development evaluator / subset provenance 文案修复；
- runtime/evaluator 对 full Development 与 debug subset 的边界区分；
- Existing Gold、Validation、Blind 治理保持不变。

这些改动继续进入 regression protection，不再继续微调。

## 4. 最终解释

当前差距不再解释为单一实现 bug。剩余问题主要来自：

```text
retrieval / Evidence exact binding residual
source-edition / exact-anchor provenance gap
complex Business structured-schema / Evidence-scope failure
real-LLM augmentation variance / negative transfer
remaining deterministic extraction conflicts
```

其中 source edition 和 exact-anchor 问题已经证明不能通过简单扩大 TopK 或替换英文版来安全解决；Business LLM 的真实复杂样本也暴露出严格 schema 与“事实不足时不能编造”之间的张力。

## 5. Release handoff

Person 1 交付给 Release owner：

```text
final benchmark SHA
offline M1/M2
real-LLM gated M1/M2
real_llm_cases = 79
formal benchmark summary
runtime/config/prompt/provider/evaluator identity
known limitations
```

后续只允许：

- 回归修复；
- provenance / hash / packaging；
- one-shot Validation 结果记录；
- 文档 truth alignment。

禁止：

```text
根据 Validation 错例继续优化
按 case/company/page/Gold 特判
降低正式 G2 门槛来制造 PASS
把 offline 结果冒充 real LLM
```

## 6. 历史追溯

历史 Batch / Bundle 仍通过：

```text
docs/V046_ROLE_B_EXPERIMENT_LEDGER.md
reports/v046_role_b/
Git history
```

追溯；本文件只保留 final truth，不再作为新的优化指令。
