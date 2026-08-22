# v0.4 PR-G Final Supervisor / Market Agent 契约

> Status: **PREPARATION / CONTRACT ONLY — PR-G 仍为 NOT STARTED**
> Owner: **E — Oracle / Product Integration**
> Date: **2026-08-21**
> 当前正式 Gate 仍为 **PR-B Market-X Core（NOT STARTED / NEXT）**
> 代码：[`../src/ipo_risk/schemas/final_supervision.py`](../src/ipo_risk/schemas/final_supervision.py)、[`../src/ipo_risk/agents/final_supervisor.py`](../src/ipo_risk/agents/final_supervisor.py)、[`../src/ipo_risk/agents/market_context.py`](../src/ipo_risk/agents/market_context.py)

本文件只落**接口与不变量**。它对现有任何 workflow **零行为变更**：`V03Supervisor`、`workflows/enhanced_v2.py`、`workflows/mvp_v1.py` 与所有 config 均逐字节未动。

## 1. 关键设计决策：Market context 不复用 `RiskAgent`

当前 registry 里的 `market_agent` 是一个返回 `list[RiskItem]` 的 `RiskAgent`（仅有 `MockMarketAgent` / `DisabledMarketAgent`）。

PR-G 需要的是市场**上下文**——一个解释通道，不是风险生产者。若复用 `RiskAgent`：

> Market Agent 将有能力把未经 Verifier 检验的 `RiskItem` 注入 `verified_risks`。

这正是整套治理边界要防的失效模式。因此本契约新增**独立 Protocol** 与**独立 registry kind**，`market_agent` 原样保留不动：

```python
class MarketContextProvider(Protocol):   # 解释通道
    name: str
    def context(self, profile: IPOProfile) -> MarketContextView: ...

class FinalSupervisor(Protocol):          # 组合层
    name: str
    def finalize(self, inputs: FinalSupervisionInput) -> FinalSupervisionResult: ...
```

## 2. 四条纯度不变量

Final Supervisor 是**纯组合层**。四条不变量各自有对应测试（`tests/contract/test_final_supervisor_contract.py`）：

1. **不造假 evidence / risk** — `referenced_risk_ids` 与 `referenced_evidence_ids` 必须是输入的子集。零 evidence 输入必须产出零 evidence 引用。
2. **不产生新预测** — `FinalSupervisionResult` 与 `ModelPredictionView` 的字段名都不得匹配 `prob|likelihood|forecast`。该断言基于 `model_fields` 内省，因此**无法被日后顺手加回来**。
3. **未校准分数不得表述为概率** — `ModelPredictionView` **刻意没有 `probability` 字段**，只有 `score` + `score_semantics` + 强制的 `calibration_status`。校准概率字段是 PR-F 的交付物，届时再加。`calibration_status="uncalibrated"` 时输出必须携带免责声明。
4. **缺席只改变 channel state** — 缺失通道不得被合成，也不得因其缺席而上调文档结论。`market_context=None, model_prediction=None` 与"输入里干脆没有这两个通道"必须产出**相同的 `content_hash()`**。

## 3. 降级矩阵

四个通道各自独立地处于 `AVAILABLE` / `PENDING_GATE` / `UNAVAILABLE_ERROR` / `DISABLED`。今天的真实状态是：

| 通道 | 今日状态 | 阻塞 Gate | 说明 |
|---|---|---|---|
| `document` | AVAILABLE | — | v0.3 `V03Supervisor` 结果原样透传 |
| `market` | PENDING_GATE | **PR-B** | 受治理的上市前 Market-X 尚未构建 |
| `model` | PENDING_GATE | **PR-F** | 尚无冻结的预测模型 |
| `rule` | AVAILABLE / DISABLED | — | 取决于是否传入 `PredictionResult` |

`GatePendingFinalSupervisor` 就是这一状态的具体参考实现：它组合已有通道，把其余的**点名 Gate 地报为不可用**，而不是静默省略或自行填补。

`uncertainty_statement` 逐条列出被阻塞的通道及其 Gate；`metadata` 钉死：

```python
{"classification": "SUPERVISORY_SYNTHESIS", "creates_no_new_risk": True,
 "probability_claimed": False, "blocking_gates": ["PR-B", "PR-F"]}
```

## 4. 接线边界

registry 已注册两个新 kind：

```python
"market_context":   {"gate_pending": GatePendingMarketContextProvider}
"final_supervisor": {"gate_pending": GatePendingFinalSupervisor}
```

但**刻意不接线**：

- 不改 `create_workflow`；
- **不加 `Settings` 字段**——`load_settings` 只读已声明的 dataclass 字段，悬空 YAML 键会被静默丢弃，因此字段留到 PR-G 真正消费时再加；
- 没有任何 config 指名它们，registry 条目因此是惰性的。

`test_settings_has_no_final_supervisor_field_before_pr_g` 守卫这一点：**它会在有人抢在 PR-G 之前接线时失败**。PR-G 正式启动时，该测试应在加入 `Settings` 字段与 `create_workflow` 接线的**同一次改动**中删除。

## 5. PR-G 正式启动时需要补的东西

- `MarketContextView` 的字段需按 PR-B 实际交付的 Market-X 形状修订（本契约不冻结它）；
- `ModelPredictionView` 在 PR-F 产出校准后，才可增加真正的概率字段，并必须同时填 `calibration_provenance_id`；
- Document Supervisor 的正式命名：今天的 `V03Supervisor` 事实上就是计划文档里的 "Document Supervisor"，PR-G 应在文档与代码中统一这一称谓；
- Final Report 渲染层（PR-H）。

## 6. 边界声明

本契约属于 `V04_FIVE_PERSON_EXECUTION_PLAN.md` §11 允许的**准备性工作**：

- **不声称 PR-G 已启动或已通过**；当前正式 Gate 仍为 PR-B；
- Market 通道只由一个类型与一个状态枚举代表，**不读任何市场数据、不碰 EOD store**；
- 不读 outcome label，不接触 2025 blind cohort；
- 若 PR-B 落地了不同的 Market-X 形状，`MarketContextView` 到 PR-G 再修——这里没有任何东西被冻结。
