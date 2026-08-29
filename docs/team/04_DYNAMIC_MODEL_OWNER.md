# Person 4 — Dynamic Model / Prediction / SHAP Owner

> 状态日期：2026-08-29  
> 建议分支：`codex/dynamic-model-runtime`  
> 主优先级：**P0**  
> 核心职责：把模型从 final-three per-case handoff 升级为真正可泛化的 frozen-model inference runtime，并完成 D 线正式模型决议

## 1. 主目标

当前 final-three 已有 Model `3/3 available`，但这主要依赖 receipt-bound per-case handoff。这个岗位要解决的是：

```text
valid case features
→ frozen model inference
→ score
→ alert / classification
→ SHAP / signed drivers
→ ModelSignal
→ Final Supervisor / UI
```

最终不能再是：

```text
case_id 在 final-three handoff 里 → 有模型
其他 case → unavailable
```

而要做到：

```text
只要满足 frozen feature contract
→ 就可以真实 inference
```

## 2. 当前模型状态

当前有两个需要正式处理的 track：

### Frozen PR-F

```text
Precision = 0.3333
Recall = 0.0435
F1 = 0.0769
PR-AUC = 0.3364
ROC-AUC = 0.4246
Alert count = 3
```

### v2 candidate

```text
Precision = 0.3529
Recall = 0.5217
F1 = 0.4211
PR-AUC = 0.3812
ROC-AUC = 0.4875
Alert count = 34
```

v2 candidate 是 Development-selected、2024 one-shot evaluated 的候选版本，但尚未完成正式 A-owned promote/retain 决议。

## 3. 第一任务：完成 Promote / Retain 决议

在做 dynamic runtime 前，必须明确最终产品到底加载哪个 frozen model identity。

### 3.1 审核内容

检查：

```text
training split
Development selection process
2024 validation one-shot semantics
feature schema
model params
threshold / alert policy
source hashes
leakage boundary
determinism
artifact identity
```

### 3.2 决策只能是

```text
PROMOTE_V2
或
RETAIN_FROZEN_PR_F
```

不要长期保持“正式模型一个、产品逻辑暗中用另一个”的状态。

### 3.3 如果 Promote

必须新建版本化资产：

```text
new model version
new model hash
new feature manifest
new alert policy identity
new receipt
new handoff
new revalidation artifact
```

禁止覆盖旧 PR-F 的历史身份。

### 3.4 如果 Retain

必须明确记录：

- 为什么保留；
- v2 为什么不晋升；
- 产品能力和性能局限；
- 后续不再根据 2024 继续调参。

## 4. 第二任务：提交/挂载真正的 Frozen Model Runtime Artifact

当前产品层不能只保存 per-case prediction。

需要形成明确的 runtime model package，例如：

```text
model artifact / model text
model_manifest.json
feature_manifest.json
alert_policy.json
hash / receipt
```

具体文件格式以现有 LightGBM implementation 和安全策略为准。

必须确保：

```text
model identity immutable after freeze
feature order explicit
missingness policy explicit
model hash verified
runtime can load without training
```

Runtime 只能 inference，不能现场 retrain。

## 5. 第三任务：Dynamic Feature Vector

模型输入必须来自正式 upstream contract。

### 来自 Person 3

```text
Market-X feature values
missingness mask
PIT cutoff
market schema / artifact hash
```

### 来自 Person 1（若正式模型使用 Document features）

```text
Document feature vector
Document feature schema
risk/evidence-derived provenance
```

禁止从 Gold / evaluator artifact 生成 runtime feature。

## 6. Feature Manifest

每次 inference 前必须验证：

```text
feature schema version
feature names
feature order
numeric dtype
missingness policy
model expected dimension
manifest hash
```

出现 mismatch：

```text
→ UNAVAILABLE / FAIL CLOSED
```

不能：

```text
缺 feature → 默认为 0
字段顺序不同 → 猜着喂模型
未知字段 → 自动吞掉且不记录
```

除非 frozen training contract 明确规定某个 feature 的缺失处理方式。

## 7. Frozen Model Inference

使用现有 LightGBM runtime 能力：

```text
load frozen booster
predict feature vector
produce model score
produce classification / alert under frozen policy
```

必须记录：

```text
case_id
model version
model hash
feature manifest hash
input feature hash
inference timestamp / run id
score
score semantics
classification threshold / alert policy identity
```

## 8. Score 语义

这是硬规则：

```text
score_semantics = uncalibrated_model_score_not_probability
```

对外禁止使用：

- probability；
- likelihood；
- “下跌概率”；
- “上涨概率”；
- “有 X% 可能破发”。

除非未来另有正式 calibration proof 并重新治理。

当前模型更适合定位为：

> 风险排序 / 风险筛查信号，而不是精确股价概率预测器。

## 9. SHAP / Driver Runtime

动态 case 必须真正从当前 inference 产生 drivers。

优先复用 LightGBM native：

```text
pred_contrib=True
```

输出：

```text
driver id / feature
signed contribution
feature value
rank
source feature provenance
```

禁止把 final-three 的 SHAP drivers 复制给新 case。

## 10. Phase 1 — Historical Universe Dynamic Inference

在 Person 3 historical Market-X 覆盖可用后：

```text
438 historical governed cases
→ feature construction
→ frozen model inference
→ score
→ SHAP
→ ModelSignal
```

建立全量 audit：

```text
total cases
inference available
partial/unavailable
feature mismatch
missing upstream Market
missing Document features
model load failure
SHAP failure
identity/hash failure
```

对于 final-three：

- 如果使用相同 frozen model + 相同 feature input，动态 inference 应可解释地复现已有 handoff；
- 如果不一致，先审计 model/feature identity，不能为了“对上旧数”手工改输出。

## 11. Phase 2 — Fresh New IPO

Person 3 提供 Dynamic Market-X 后：

```text
Fresh PDF
→ Document features
→ Dynamic Market-X
→ frozen feature vector
→ frozen model
→ SHAP
→ Final Supervisor
→ Report
```

如果 upstream feature 不足：

```text
Model = PARTIAL / UNAVAILABLE
missing_reason = explicit
```

不能伪造完整模型结果。

## 12. 与 Final Supervisor 的接口

Final Supervisor 只应消费 governed ModelSignal：

```text
score
score semantics
classification/alert
signed drivers
model identity
availability / missingness
```

不得让 Supervisor看到训练标签、Validation outcome、Blind outcome。

Final Supervisor v3 vocabulary / severity / scope guard 不属于本岗位修改范围，除非接口字段导致明确兼容 bug。

## 13. 赛题特色能力协同责任

除了模型主线，本岗位兼任**特色能力 coverage coordinator**，确保以下能力最终至少各有一个真实可审计案例：

```text
text embellishment
related-party transaction
comparable IPO valuation
```

注意：不是要求本岗位独自写完所有代码。

协作关系：

```text
text embellishment / related-party
→ 与 Person 1 协作 Document extraction / Evidence

comparable IPO valuation
→ 与 Person 3 协作 Market / comparable data

最终 UI 展示
→ Person 2

最终验收和打包
→ Person 5
```

本岗位负责确认这些能力不是 PPT 空标题，而是有：

```text
input
Evidence/source
Agent/Skill/calculation
output
Trace/provenance
report/UI proof
```

如果 Existing Gold 不覆盖这些能力，明确标记为：

```text
QUALITATIVE DEMONSTRATION
```

不得混入 M1/M2 分母。

## 14. 测试要求

至少包括：

### Model load

- hash mismatch fail closed；
- wrong feature manifest fail closed；
- clean checkout 可以加载正式 runtime artifact。

### Feature input

- order / dtype / dimension；
- missingness；
- no Gold/Blind fields。

### Inference

- deterministic input → stable deterministic score；
- threshold policy 固定；
- no retraining in runtime。

### SHAP

- driver length / ordering；
- signed contributions；
- no stale per-case drivers。

### Integration

- final-three no regression；
- historical non-canonical cases；
- fresh case partial/full path；
- Final Supervisor consumes ModelSignal correctly。

## 15. 交付物

最终交付：

```text
formal promote/retain decision
frozen model artifact
model manifest
feature manifest
alert policy identity
receipt/hash
Dynamic Model provider
Dynamic SHAP output
historical inference audit
fresh-case inference audit
capability-case coverage matrix
unit/integration tests
```

## 16. 禁止事项

禁止：

- 根据 2024 Validation 继续调参；
- 访问 2025 Blind outcome；
- runtime retraining；
- 使用 Gold 生成 model input；
- 把 score 称 probability；
- missing feature 自动补 0（除非 frozen contract 明确如此）；
- 复制 final-three prediction / SHAP 给新 case；
- 覆盖旧 frozen model identity；
- 为提高前端观感伪造 available。

## 17. 完成定义

本岗位 DONE 条件：

```text
formal model promote/retain decision complete
final frozen model identity locked
runtime can load model without retraining
valid historical case can dynamically infer
SHAP generated dynamically
final-three no regression
fresh case supports governed full/partial model path
score semantics correct
no Validation retuning / Blind leakage
capability coverage matrix complete
all relevant tests PASS
```

最终目标是把 Model 从“三个案例的预生成结果”升级为真正可复用的受治理 inference service。