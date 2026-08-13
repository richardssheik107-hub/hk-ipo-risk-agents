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

## 4. 人工复核与正式晋级流程

Owner 于 2026-08-12 冻结 `single_named_human_review_v1`：具名真实人工完成一次复核即可
使用`first_reviewed`进入正式 Golden。`second_reviewer`必须保持为空，不得把一审写成
`double_reviewed`。若自愿开展第二复核，则仍需盲审、人员独立；一致时使用
`double_reviewed`，有分歧且完成人工仲裁时使用`adjudicated`。

Codex、ChatGPT、AI、LLM、自动生成或占位身份不得成为 reviewer。`draft`和缺少具名
人工 reviewer 的记录不能进入正式评测。

## 5. 数据隔离

- 开发集可用于规则编写；验证集只用于版本验收；2025 盲测集不得用于调规则或阈值。
- 仓库只提交脱敏索引、规范和小型合成样例，不提交赛事原始 PDF。
- `exact_text` 仅保留验证所需最短原文，避免复制大段受版权保护内容。

## 6. 校验

样例路径：`tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv`。

```powershell
python scripts/validate_v03_golden_manifest.py tests/fixtures/v03_golden_cases/v03_golden_case_manifest.csv
```

## 7. Expert Golden v1.1 research track

现有 `v03_annotation_v1` Human Golden 是历史正式评测资产，不在 Phase 0.6B 修改。
新的 Expert Golden 使用独立 evaluation-only `gpt_expert_v1.1` 协议，支持一个
risk instance 对应多条 Evidence，并显式记录 role、required/alternative/
supporting-only、confidence 和 Calculation inputs。

新方法不是 pure human annotation，也不是 GPT output = gold，而是：Blind GPT
investigation、deterministic validation、independent GPT audit、conflict detection
和 selective human adjudication。第一轮 2410 GPT 输出仅为诊断材料。

Protocol v1.1 已冻结现金口径、negative status、Calculation 要求和 dash/blank
语义；zero-revenue concentration、`precommercial_product` severity 与 Fact/Label
分层仍是 open policy。协作材料见
[annotation/gpt_expert_v1_1/README.md](annotation/gpt_expert_v1_1/README.md)。
