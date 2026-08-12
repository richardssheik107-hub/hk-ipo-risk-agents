# v0.3 Owner Waiver for Final Technical Completion

状态：`AUTHORIZED_BY_OWNER_WAIVER`

功能基线：`main@b60570ef0854b198c6e4827336cb4a3b529fe462`（PR #37 合并后）

## 决策

仓库所有者明确允许 v0.3 在不完成剩余 Financial / Business 独立人工二审的情况下继续技术收口。该决定只解除发布流程阻塞，不把未完成的人工工作转换为 PASS，也不改变 Golden 数据事实。

```text
GATE_A_03 = DEFERRED_BY_OWNER_WAIVER
GATE_A_04 = DEFERRED_BY_OWNER_WAIVER
GATE_A_TECHNICAL_CONTINUATION = AUTHORIZED_BY_OWNER_WAIVER
V3_8_START_STATUS = AUTHORIZED_BY_OWNER_WAIVER

FORMAL_FINANCIAL_GOLDEN_CERTIFIED = false
FORMAL_BUSINESS_GOLDEN_CERTIFIED = false
FORMAL_LEGAL_GOLDEN_CERTIFIED = true
```

## 数据真实性边界

- Financial 23 条真实记录仍没有独立 second review；
- Business 3 条真实记录仍没有独立 second review；
- Legal 8 条真实记录保持正式人工复核状态；
- 不填写或伪造 `second_reviewer`；
- 不把 Codex、AI 或自动测试记录为人工 reviewer；
- 不把 Financial / Business draft 行改为 `double_reviewed` 或 `adjudicated`；
- 现有 primary 判断不因技术验收而改写。

未完成二审的 Financial / Business 数据只能用于 development regression，任何由其产生的指标必须标记：

```text
formal_reviewed_metric = false
human_second_review_deferred = true
```

它们不得与正式 reviewed Legal 数据混合后对外宣称“正式跨域准确率”。

## 安全边界

2025 blind 数据继续禁止用于打开、解析、检索、调参、Prompt 调优或评测。本 waiver 不授权 v0.4 市场预测、概率模型或投资建议功能。

## 允许的版本语义

v0.3 可以在工程验收完成后表述为：

```text
TECHNICALLY COMPLETE
DEMO READY
OWNER-WAIVED HUMAN-GOLDEN CERTIFICATION
```

不得表述为“全部 Golden 已完成人工双审”“Financial / Business 正式精度已证明”或“上市后下跌概率模型已完成”。
