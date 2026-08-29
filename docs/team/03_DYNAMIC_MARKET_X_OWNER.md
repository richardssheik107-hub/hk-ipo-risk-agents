# Person 3 — Dynamic Market-X / All-PDF Market Runtime Owner

> 状态日期：2026-08-29  
> 建议分支：`codex/dynamic-market-x`  
> 主优先级：**P0**  
> 核心职责：让 Market-X 不再只对 final-three 好用，而是对历史 universe 和任意合法新 PDF 都有正确、可审计的运行语义

## 1. 主目标

这个岗位的目标不是“所有 PDF 都强制显示一个 Market 数字”，而是：

> **所有 PDF / IPO case 都能进入统一 Market runtime；有数据时真实计算，无数据时明确 PARTIAL / UNAVAILABLE，并给出原因。**

最终希望达到：

```text
Phase 1:
438 historical frozen IPO
→ Market-X available / governed

Phase 2:
arbitrary new IPO
→ Dynamic PIT Market-X
→ Market Skills
→ provenance
→ downstream Model / Supervisor / UI
```

## 2. 当前起点

当前已知：

- final-three Market = `3/3 available`；
- 仓库已有约 438 个 governed frozen Market-X Core artifacts；
- 已存在通用 `build_ipo_market_context(...)` 类 PIT-safe 特征逻辑；
- 当前真正的新 IPO 仍可能返回 `unsupported_new_case` / `dynamic_new_case` 语义；
- raw licensed EOD 不进入 Git；
- missing Market feature 不能补零。

因此这不是从零开发，而是把已有 frozen / builder / provider 路径真正产品化。

## 3. 负责范围

本岗位负责：

- issuer / stock-code / listing-date / industry identity 对齐；
- historical frozen Market-X provider；
- Dynamic Market-X provider；
- PIT market history selection；
- Market feature builder；
- Market observation schema；
- Market Skills；
- market missingness；
- provenance / source hash / cutoff semantics；
- historical-universe coverage audit；
- fresh-case Market integration tests；
- 给 Dynamic Model Owner 的稳定 Market feature handoff。

本岗位**不负责**：

- M1/M2 风险抽取调参；
- LightGBM 训练/晋升；
- SHAP 实现；
- UI 视觉布局；
- 最终 submission ZIP。

## 4. Phase 1 — 438 Historical Frozen Universe

第一阶段优先完成，不要一上来就押注外部实时数据源。

目标：

```text
任意 historical case
→ identity resolve
→ locate governed frozen Market-X artifact
→ validate identity / hash / PIT provenance
→ load MarketContext
→ run Market Skills
→ expose to Supervisor / UI
```

### 4.1 Identity

至少保证：

```text
case_id
stock_code
issuer
listing_date
industry（若有）
```

不能只靠公司名称 fuzzy match 做正式 join。

UI smart-match 可以辅助输入，但正式 Market artifact join 必须依赖 governed identity。

### 4.2 Frozen artifact validation

读取 frozen Market-X 时检查：

```text
case_id match
stock_code match
listing_date match
artifact hash
source provenance
cutoff semantics
schema version
```

任何 identity mismatch 必须 fail closed。

### 4.3 Coverage audit

生成类似：

```text
historical_market_runtime_audit.json
```

至少统计：

```text
total governed historical cases
available
partial
unavailable
identity mismatch
missing artifact
schema/hash failure
PIT/provenance failure
```

不要只抽查三家公司。

## 5. Phase 2 — Arbitrary New IPO Dynamic Market-X

### 5.1 输入 contract

新案例至少需要：

```text
issuer identity
stock code（若已知）
listing date / expected listing date
industry / sector（若可得）
prospectus provenance
```

缺少 listing date 时，不能偷偷使用当前日期作为 PIT cutoff。

### 5.2 PIT history

Market-X 只允许使用：

```text
information timestamp < target listing date
```

禁止：

- 使用目标 IPO 上市后的价格；
- 使用目标 IPO 的 1D/5D/20D/60D outcome；
- 使用未来 IPO 信息；
- 使用 2025 Blind outcome；
- 为了填满 feature 使用 post-listing proxy。

### 5.3 Dynamic features

复用/扩展现有 PIT builder，至少支持当前正式 Market feature contract，例如：

```text
recent IPO counts
recent fundraising amount
recent break-rate / poor-performance context
short-window IPO performance context
industry / peer IPO context
market regime context
```

具体 feature 名以代码当前 schema 为准，不在这里硬编码新的 metric 定义。

每个 observation 必须携带：

```text
name
value OR missing_reason
unit
availability
source
derivation
PIT cutoff
provenance
```

## 6. Derived Market History Pack

如果 Dynamic New-IPO 需要历史数据，优先建立一个**治理后的派生历史层**，而不是把 1GB+ raw EOD 塞进仓库。

建议形状：

```text
case_id
stock_code
listing_date
industry
funds_raised
historical outcome fields needed only for prior-IPO context
source provenance
```

要求：

- 只保存 Dynamic Market-X 真正需要的派生历史；
- 保留 source/hash/provenance；
- 明确授权边界；
- raw licensed EOD 继续留在本地/授权环境；
- 如果派生数据也受授权限制，则 Git 里只提交 builder/schema，不提交受限数据。

## 7. Missingness 是正式产品能力

这是本岗位最重要的原则之一。

如果某个 feature 缺失：

```text
availability = unavailable / partial
missing_reason = explicit
```

禁止：

```text
missing → 0
missing → fake average
missing → final-three old value
missing → unsourced web number
```

因为 `0` 是一个真实数值，不等于“没有数据”。

## 8. Market Skill 输出

所有 Market Skill 只能解释 supplied governed observations。

LLM / Skill 不允许：

- 引入 observation 中不存在的新市场数值；
- 猜测未来走势；
- 把 missing feature 解释成 0；
- 把 score 当概率；
- 使用 target post-listing outcome。

Market interpretation 应绑定 `source_feature_ids`。

## 9. 给 Dynamic Model Owner 的 handoff

Person 4 不应该自己重算 Market-X。

本岗位必须提供 versioned Market feature handoff，例如：

```text
case identity
market feature schema version
feature values
missingness mask
PIT cutoff
source provenance
artifact/content hash
```

需要明确：

```text
available features
missing features
feature order / manifest identity
```

这样 Model owner 才能安全构造 frozen model input。

## 10. 给 Frontend Owner 的 contract

Frontend 只消费：

```text
MarketContext
Market observations
availability
missing reason
provenance
```

不要要求前端读取 raw market history 或内部 builder 中间文件。

## 11. 测试计划

### Test A — final-three no regression

```text
2410 / 2460 / 1318
Market remains 3/3
```

### Test B — historical universe

至少完成全量 automated audit；对非 canonical case 做代表性 runtime test。

### Test C — PIT boundary

构造测试证明：

```text
record at listing_date or later
→ excluded
```

### Test D — missingness

缺行业数据、缺 prior-IPO data、缺 listing date 时，必须得到诚实的 partial/unavailable。

### Test E — identity mismatch

case_id / stock code / listing date 不一致时 fail closed。

### Test F — no zero fill

缺失 feature 不能变成 available zero。

## 12. 赛题展示目标

完成后应该能向评委说明：

```text
三案例是预置完整 Demo
但 Market-X 不是三案例硬编码
historical universe 有 governed runtime
新 IPO 也有 Dynamic PIT path
数据不足时系统会诚实降级
```

## 13. 交付物

最终至少交付：

```text
Dynamic Market provider
historical provider integration
PIT history builder/store contract
Market schema/provenance
historical-universe coverage audit
fresh-case audit
unit/integration tests
handoff contract for Model
known external-data boundary
```

## 14. 禁止事项

禁止：

- case-specific Market hardcoding；
- 读取 target post-listing outcome；
- Blind leakage；
- missing zero-fill；
- 把 raw licensed EOD 提交到 Git；
- 复制 final-three Market JSON 给新公司；
- UI-only fake availability；
- 用公司名称 fuzzy match 替代正式 identity join。

## 15. 完成定义

本岗位 DONE 的最低条件：

```text
final-three Market no regression
historical governed universe has audited Market runtime
new IPO has real Dynamic PIT Market path
missingness truthful
PIT / Blind / licensing boundaries preserved
Market handoff stable for Model
all relevant tests PASS
```

真正的目标是让 Market-X 从“预生成展示资产”升级成“可以泛化的新 IPO 市场上下文服务”。