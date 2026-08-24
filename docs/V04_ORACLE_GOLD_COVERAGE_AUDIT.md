# v0.4 Oracle 覆盖审计与 PR-E 功效复核

> Status: **ADVISORY —— 不要求重开任何已冻结的 Gate**
> Owner: **E — Oracle / Product Integration**
> First audit **2026-08-21**（61 份 pass1）· Re-audit **2026-08-23**（101 份）· **功效复核 2026-08-24**
> 当前正式 Gate: **PR-G — Market Agent + Final Supervisor**
> 复现入口：`scripts/audit_oracle_gold_coverage.py` · `src/ipo_risk/modeling/statistical_power.py`

## 0. 这份文档现在剩下什么

本审计最初提出 8 条发现。随着 Oracle v2、PR-E、PR-F 相继冻结，**其中 7 条已被解决或取代**：

| 首次发现 | 现状 |
|---|---|
| PR-E 的 development CV 是随机分折 | ✅ 已修复 —— main 现为 `evaluate_development_forward_chaining_baselines`，文档明写 *Random or shuffled cross-validation is prohibited* |
| Oracle artifact 身份取自标注 packet | ✅ 已修复 —— `oracle_document_v2` 从 production artifact 读官方身份并 rebind |
| Oracle 可用队列 75 / 17 | ⬆️ 被取代 —— Oracle v2 的 **77 / 19** 为权威口径 |
| Oracle validation 覆盖为 0 | ✅ 已解决（2023/2024 补标注） |
| PR-A 冻结记录与现实不符 | ✅ 政策解决 —— v1 保留为 historical，v2 为当前 Oracle ceiling |
| ROADMAP / README 状态失真 | ✅ 已解决 |
| 缺依赖时 pytest collection 崩溃 | 🟢 非阻塞，仍待 A |

**只剩一条未被处理：统计功效。** 本文档因此瘦身为该主题的复核记录。原先的覆盖审计脚本保留为独立交叉校验（它算出的 98 个可构建 case 与 Oracle v2 冻结的 98 个 feature artifact 一致）。

---

## 1. 复核对象

PR-E 已 **COMPLETE / FROZEN**，其正式结论为：

```text
M  ROC-AUC / PR-AUC   0.5671 / 0.3624
PM ROC-AUC / PR-AUC   0.5513 / 0.3554
PM − M                −0.0157 / −0.0070          （Full Production 2024，n=70）
OM − M                −0.0571 / −0.0618          （Oracle v2 2024 intersection，n=19）
```

> 「The current document classification signal is therefore not robustly validated under the frozen baseline; the small Oracle Validation cohort must not be repeatedly tuned against.」

**本节不质疑 PR-E 的方法论。** 前向分折、同队列同预处理同模型族、fail-closed 漂移检查、拒绝把 score 表述为真实概率 —— 这些都做得比第一次审计时好。本节只补一个 PR-E 报告中没有的量：**这两个差值是否大到该队列能够分辨。**

## 2. 复核结果：两个差值都在器械分辨率以下

用 PR-E 自己的参数（M ROC-AUC = 0.567；PR-AUC ≈ 0.36 对应正样本率约 36%），按 Hanley-McNeil 计算两臂比较的最小可检测差异：

| 队列 | n | 正 / 负 | **最小可检测差异** | PR-E 观测值 | 占门槛 |
|---|---:|---|---:|---:|---:|
| Oracle v2 2024 intersection | 19 | 7 / 12 | **0.391** | −0.0571 | **15%** |
| Full Production 2024 | 70 | 25 / 45 | **0.201** | −0.0157 | **8%** |

> **观测差值分别只有可分辨门槛的 15% 和 8%。在这个量级上，差值的正负号不携带信息。**

这不意味着 PR-E 的结论是错的 —— 它意味着**该结论的强度低于其数值表面所暗示的**。「未观测到增量价值」与「不存在增量价值」在 n=19 上无法区分，同样也无法区分「负增量」与「正增量」。

### 2.1 需要说明的近似

- 用 `sqrt(2) × SE` 把单臂标准误扩成两臂比较，是把两臂当作独立处理。PR-E 的两臂评估在同一批 case 上，属配对比较，真实门槛会低于此值 —— 但不会低到改变上述结论的数量级；
- 假设 AUC 取 PR-E 实测的 0.567；取 0.70 时 Oracle 队列门槛为 0.364，结论不变。

---

## 3. 建议（不要求重开任何 Gate）

PR-E 与 post-PR-F 战略决策均已冻结，本文档**不主张回滚、不要求重跑、不申请解冻**。建议仅限于**后续引用该结论时**：

1. **引用 `PM − M` / `OM − M` / `OM − PM` 时同时给出队列规模与可分辨门槛**，避免读者把 −0.0157 当作方向性证据；
2. **PR-G / PR-H 在 UI 与最终报告中呈现模型驱动因素时**，不要把 PR-E 的负号表述为「文档特征无用」；正确表述是「在当前样本量下未能验证」；
3. **若未来 CH-6 的 benchmark 要重新评估文档信号价值**，先做功效估算再定队列规模 —— 由上表，即使用完整 368 个 development，可分辨门槛也有 0.087，而这类信号的实际量级通常在 0.03–0.10。

工具已提供，可直接复用：

```python
from ipo_risk.modeling.statistical_power import assess_comparison

assess_comparison(-0.0571, positive_count=7, negative_count=12, assumed_auc=0.567).statement()
# "observed gap -0.0571 is 15% of the minimum detectable difference of 0.391
#  for this cohort (7 positive / 12 negative); its sign is not informative at
#  this sample size"
```

`ComparisonPower.statement()` 的输出可直接粘进报告，`resolvable` 可用于让渲染层在差值不可分辨时隐藏正负号。

---

## 4. 保留的覆盖审计

`scripts/audit_oracle_gold_coverage.py` 保留为**独立交叉校验**，只读标注资产与官方 bridge，不运行 production pipeline、不读市场数值或 outcome label、不接触 2025 blind cohort。

当前输出（2026-08-24）：

```text
case packets                101
pass1 盲标                  101
Oracle feature 可构建       100     （real_case_001 schema 非法，非 official IPO）
  └─ official universe 内    98     ← 与 Oracle v2 冻结的 98 个 feature artifact 一致
official 内无 reviewed gold 340
                            ─────
98 + 340 = 438              ✓
```

它与 Oracle v2 的 materialization 相互独立地得出同一个 98，因此可作为 Oracle v2 覆盖数的旁证。

**注意队列口径**：Oracle v2 的权威可建模队列是 **77 development / 19 validation**（outcome-usable 96）。本脚本报的 98 是**可构建**数，不扣除 outcome 与身份筛除；引用时以 Oracle v2 冻结 manifest 为准。

复现：

```bash
.venv/bin/python scripts/audit_oracle_gold_coverage.py --root . --output-dir reports/oracle_gold_audit
```

```bash
.venv/bin/python -m pytest tests/unit/test_oracle_gold_coverage_audit.py tests/unit/test_statistical_power.py -q
```

---

## 5. 边界声明

- 不启动、不声称通过任何正式 Gate；当前正式 Gate 为 **PR-G**；
- **不要求重开 PR-E 或 post-PR-F 战略决策**；
- 不读取市场数据、outcome label 或 2025 blind cohort；
- 不写入 `reports/frozen/`，不修改任何已冻结的模块或 manifest；
- 不产出任何新的模型指标 —— 本文档只对已公开的 PR-E 数值做功效换算。
