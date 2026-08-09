# v0.3 Legal 黄金案例预选与复核说明

状态：`draft`
契约：`v03_annotation_v1`
数据文件：`tests/fixtures/v03_golden_cases/v03_legal_golden_case_manifest.csv`

## 1. 目的与边界

本清单在 Legal 正式规则开发前建立，用于降低“根据既有规则反向挑案例”的确认偏误。它只覆盖 Legal Agent 拥有的两个风险码：

- `redemption_rights`
- `material_litigation_compliance`

本阶段没有修改 Retriever、Legal Agent、Verifier、LLM Provider 或冻结规则。所有案例均来自 `development` 集；2024 `validation` 集和 2025 盲测集均不进入本开发黄金清单。

## 2. 预选方法

1. 在 2020—2023 开发集招股书中，以简体、繁体和英文的法律事项词及状态词生成候选，不使用尚未开发的正式规则输出。
2. 对权利类同时检查权利主体、终止条件、恢复条件和上市后状态；对诉讼类同时检查当事方、当前状态、金额或程序细节以及披露的重大性。
3. 排除目录页、仅有章节标题的页面、一般性风险因素、明确“不存在重大诉讼”的确认和监管模板声明。
4. 对最终 A—H 页逐一渲染，按 PDF 物理页码核对版面与原文；CSV 仅保留验证所需的最短原文。
5. 本轮仅完成机器辅助预选和单人视觉核验，`review_status` 保持 `draft`，不得作为正式黄金回归数据使用。

## 3. A—H 覆盖矩阵

| 案例 | 风险码 | 公司 | 预期结论 | 关键区别 |
|---|---|---|---|---|
| A | `redemption_rights` | 微博－ＳＷ | draft `verified / high` | 上市后持续；`high`尚无冻结severity policy |
| B | `redemption_rights` | 零跑汽車 | `rejected / not_applicable` | 历史特殊权利在最后实际可行日期前已失效并终止 |
| C | `redemption_rights` | 鍋圈 | draft `needs_review / medium` | 明确恢复条件按冻结规则进入Verifier；draft状态待人工仲裁 |
| D | `redemption_rights` | 九尊數字互娛 | `needs_review / medium` | 披露提早赎回权，但具体行使方式外引至债券工具，终止状态不完整 |
| E | `material_litigation_compliance` | 星空華文 | draft `verified / high` | 重大未决；`high`尚无冻结severity policy |
| F | `material_litigation_compliance` | 綠源集團控股 | `rejected / not_applicable` | 历史案件已结案、判决已支付，未披露持续重大影响 |
| G | `material_litigation_compliance` | 新紐科技 | `rejected / not_applicable` | 董事明确确认不存在可能产生重大不利影响的未决或潜在重大诉讼 |
| H | `material_litigation_compliance` | MOG HOLDINGS | `rejected / not_applicable` | 风险因素仅描述未来可能发生的诉讼，没有实际已发生事项 |

其中 A 和 E 是明确正例；B、F、G、H 是误报控制负例；C、D 是状态推理边界例。`expected_level` 是首轮标注建议，第二标注人必须独立判断，不得以本表作为答案提示。

## 4. 独立复核流程

第二标注人应先阅读对应 PDF 页及必要的相邻页，再独立记录以下五项：

1. 风险是否适用；
2. 主证据物理页码；
3. 最短逐字原文；
4. 标准核验状态；
5. 标准等级。

第二标注完成前不应查看 CSV 中的 `expected_status`、`expected_level` 和 `notes`。完成后再比对；页码、原文、适用性、状态或等级任一不一致均需记录分歧并仲裁。只有达到 `double_reviewed` 或 `adjudicated` 后，才可并入正式黄金回归。

## 5. 使用限制

- `draft` 行可以用于讨论检索需求和设计测试边界，但不能用于宣称模型准确率。
- C 只表示存在恢复条件，需要结合上市结果和条款条件核验；它不等于权利当前持续有效。
- C的`needs_review`与Builder的`BUILT + PENDING`差异等待独立人工仲裁，不得反向修改冻结规则。
- A和E的`high`仅为draft建议；正式Legal severity policy尚未冻结。
- D 的“证据不足”不等于“不存在风险”；Retriever 应尝试获取完整工具条款，未取得时保持 `needs_review`。
- F、G、H 分别代表已结案、明确否认和一般性未来风险，Legal Agent 必须将三者与实际未决事项区分。
