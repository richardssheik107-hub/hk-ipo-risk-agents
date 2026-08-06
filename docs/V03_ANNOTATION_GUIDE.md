# v0.3 金标准标注指南

标注契约版本：`v03_annotation_v1`

## 1. 单条记录字段

金标准 CSV 必须包含：

```text
case_id,stock_code,company_name,document_id,risk_code,applicable,
gold_page,exact_text,expected_status,expected_level,reviewer,
second_reviewer,review_status,notes
```

约束：

- `risk_code` 必须是 v0.3 已启用风险码；
- `applicable` 为 `true/false`；不适用时允许页码和原文为空，但须说明原因；
- 适用记录必须给出 PDF 物理页码和可逐字核对的 `exact_text`；
- `expected_status` 仅允许 `verified/needs_review/rejected`；
- `expected_level` 仅允许 `low/medium/high/critical/not_applicable`；
- `review_status` 仅允许 `draft/first_reviewed/double_reviewed/adjudicated`；
- 不同意见不得覆盖原记录，在 `notes` 记录争议并交仲裁。

## 2. 标注单位

一行表示“公司 × 风险码”的判断，不表示一个随意关键词命中。一个风险存在多个主证据页时，使用多行并保持同一 `case_id`、`stock_code`、`risk_code`；在 `notes` 标明 `primary` 或 `cross_check`。

## 3. 风险判定要点

- 财务风险：优先正式财务报表、附注和会计师报告；期间、币种、单位必须可比。
- `redemption_rights`：标注权利主体、触发/终止条件、上市后是否仍有效或可恢复。
- `material_litigation_compliance`：标注事项、对手方/监管机构、当前状态、披露的重大性或潜在影响。
- `precommercial_product`：标注核心产品、开发/审批/上市阶段以及是否已有产品收入。
- 摘要页可作为交叉验证，不得在正式主表存在时替代主证据。

## 4. 双人复核流程

```text
第一标注 → 第一复核 → 第二标注独立复核 → 分歧仲裁 → double_reviewed/adjudicated
```

第二标注不得先看第一标注的结论。页码、原文、适用性、状态和等级任一不同均算分歧。评测集进入黄金回归前必须为 `double_reviewed` 或 `adjudicated`。

## 5. 数据隔离

- 开发集可用于规则编写；验证集只用于版本验收；2025 盲测集不得用于调规则或阈值。
- 仓库只提交脱敏索引、规范和小型合成样例，不提交赛事原始 PDF。
- `exact_text` 仅保留验证所需最短原文，避免复制大段受版权保护内容。

## 6. 校验

样例路径：`tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv`。

```powershell
python scripts/validate_v03_golden_manifest.py tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv
```
