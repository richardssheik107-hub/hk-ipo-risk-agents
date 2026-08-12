# v0.3 A03/A04 独立人工二审盲审包

状态核验基线：`main@885afe7b6584886433f5ed584aa85f2a805f270e`。

本文件是独立人工二审的证据定位工具，不是Golden答案。下表只提供定位字段和候选物理PDF页，不公开primary的适用性、原文、状态、等级、理由、备注或结论。复核人必须打开原始招股书并自行判断。

```text
development_review_material = true
primary_answers_exposed = false
human_second_review_complete = false
codex_is_reviewer = false
2025_blind_accessed = false
```

## 1. 通用盲审流程

1. 独立复核人只能先查看本盲审包和原始招股书PDF，不得先查看canonical manifest中的primary判断字段。
2. 从候选物理页开始，检查上下段和必要的相邻页；候选页只是定位提示，不是预先确认的Golden页。
3. 在对应空白CSV中独立填写适用性、最终物理页、最短可核对原文、预期核验状态、风险等级、理由、真实复核人和时间。
4. 独立决定完成后，才由数据治理人员与primary结果做机械比较。
5. 完全一致且校验通过时，记录为`double_reviewed`。
6. 任一判断不一致时，保留分歧并交给不同于primary和second reviewer的真实第三人仲裁。
7. 仲裁完成后才记录为`adjudicated`。

Codex/AI可以检查CSV结构、空值和两次结果差异，但不得填写人工判断，不得充当reviewer或adjudicator。

权威规则入口：

- 标注字段与独立性：[V03_ANNOTATION_GUIDE.md](../V03_ANNOTATION_GUIDE.md)
- 风险所有权、Evidence/Calculation要求：[V03_RISK_RULES.md](../V03_RISK_RULES.md)
- 冻结开发契约：[V03_DEVELOPMENT_CONTRACT.md](../V03_DEVELOPMENT_CONTRACT.md)

## 2. A03 Financial

### 2.1 复核人资格与输出

Financial primary为`member-3`。本节必须由与`member-3`不同的真实独立人工复核人完成；仓库当前不指定具体人选。

使用空白模板：[templates/v03_financial_second_review.csv](templates/v03_financial_second_review.csv)。

每个风险结论必须结合完整证据束判断，不能把每一行候选证据误当成独立风险结论。尤其：

- `cash_runway`必须联合现金Evidence、经营现金流Evidence和Calculation；核对输入、公式、结果、单位及Evidence引用。
- 同一公司、同一风险的多个候选页属于一个证据束；必须结合相邻页和表格标题确认字段含义。
- 对数值风险核对原始值、正负号、币种、单位、报告期、期间长度与可比性。
- 对集中度风险确认客户/供应商口径、单一或前五口径、比例、期间及是否确为发行人数据。
- 阈值和Calculation要求只按`V03_RISK_RULES.md`及当前配置执行，不在本盲审包另造规则。

### 2.2 五类风险独立核对项

| 风险码 | 必须独立核对 |
| --- | --- |
| `cash_runway` | 现金、经营现金流、正负号、币种、单位、期间、期间可比性、Calculation输入/公式/结果、适用性、状态、等级 |
| `continuous_loss` | 正式损益口径、报告期、亏损连续性、是否为公司拥有人应占口径、适用性、状态、等级 |
| `revenue_growth` | 收入口径、比较期、期间长度、增长计算、Calculation引用、适用性、状态、等级 |
| `customer_concentration` | 客户口径、单一/前五比例、期间、单位、Calculation引用、适用性、状态、等级 |
| `supplier_concentration` | 供应商口径、单一/前五比例、期间、单位、Calculation引用、适用性、状态、等级 |

### 2.3 候选证据定位（23行）

| # | case_id | 股票 | 公司 | document_id | risk_code | 候选物理PDF页 |
| ---: | --- | --- | --- | --- | --- | ---: |
| 1 | `ipo_2020_01167` | `1167.HK` | 加科思－Ｂ | `ipo_2020_01167` | `continuous_loss` | 416 |
| 2 | `ipo_2020_01167` | `1167.HK` | 加科思－Ｂ | `ipo_2020_01167` | `supplier_concentration` | 287 |
| 3 | `ipo_2020_08489` | `8489.HK` | 裕程物流 | `ipo_2020_08489` | `revenue_growth` | 299 |
| 4 | `ipo_2020_08489` | `8489.HK` | 裕程物流 | `ipo_2020_08489` | `continuous_loss` | 299 |
| 5 | `ipo_2020_08489` | `8489.HK` | 裕程物流 | `ipo_2020_08489` | `customer_concentration` | 142 |
| 6 | `ipo_2020_08489` | `8489.HK` | 裕程物流 | `ipo_2020_08489` | `supplier_concentration` | 152 |
| 7 | `ipo_2023_01541` | `1541.HK` | 宜明昂科－Ｂ | `ipo_2023_01541` | `continuous_loss` | 384 |
| 8 | `ipo_2023_01541` | `1541.HK` | 宜明昂科－Ｂ | `ipo_2023_01541` | `revenue_growth` | 384 |
| 9 | `ipo_2023_01541` | `1541.HK` | 宜明昂科－Ｂ | `ipo_2023_01541` | `customer_concentration` | 331 |
| 10 | `ipo_2023_01541` | `1541.HK` | 宜明昂科－Ｂ | `ipo_2023_01541` | `supplier_concentration` | 329 |
| 11 | `ipo_2023_02503` | `2503.HK` | 中深建業 | `ipo_2023_02503` | `continuous_loss` | 250 |
| 12 | `ipo_2023_02503` | `2503.HK` | 中深建業 | `ipo_2023_02503` | `revenue_growth` | 250 |
| 13 | `ipo_2023_02503` | `2503.HK` | 中深建業 | `ipo_2023_02503` | `customer_concentration` | 165 |
| 14 | `ipo_2023_02503` | `2503.HK` | 中深建業 | `ipo_2023_02503` | `customer_concentration` | 164 |
| 15 | `ipo_2023_02503` | `2503.HK` | 中深建業 | `ipo_2023_02503` | `supplier_concentration` | 12 |
| 16 | `ipo_2020_09633` | `9633.HK` | 農夫山泉 | `ipo_2020_09633` | `continuous_loss` | 313 |
| 17 | `ipo_2020_09633` | `9633.HK` | 農夫山泉 | `ipo_2020_09633` | `revenue_growth` | 313 |
| 18 | `ipo_2020_09633` | `9633.HK` | 農夫山泉 | `ipo_2020_09633` | `customer_concentration` | 116 |
| 19 | `ipo_2020_09633` | `9633.HK` | 農夫山泉 | `ipo_2020_09633` | `supplier_concentration` | 141 |
| 20 | `real_case_001` | `2410.HK` | 同源康醫藥－Ｂ | `real_case_001` | `cash_runway` | 562 |
| 21 | `real_case_001` | `2410.HK` | 同源康醫藥－Ｂ | `real_case_001` | `cash_runway` | 563 |
| 22 | `real_case_001` | `2410.HK` | 同源康醫藥－Ｂ | `real_case_001` | `continuous_loss` | 558 |
| 23 | `real_case_001` | `2410.HK` | 同源康醫藥－Ｂ | `real_case_001` | `revenue_growth` | 558 |

`real_case_001 / cash_runway`的562页与563页必须作为同一证据束复核，并检查Calculation，不得分别作出两个风险判断。`2503.HK / customer_concentration`的164页与165页也必须结合上下文判断是否属于同一口径或互为主证据/交叉证据。

## 3. A04 Business

### 3.1 复核人资格与冻结规则

Business primary为`member-5`。本节必须由与`member-5`不同的真实独立人工复核人完成；仓库当前不指定具体人选。

使用空白模板：[templates/v03_business_second_review.csv](templates/v03_business_second_review.csv)。

冻结判定规则：

```text
core product not commercialized
AND
no direct product-sales revenue
```

复核人必须独立判断核心产品身份、研发阶段、商业化状态，以及是否存在直接产品销售收入。授权、里程碑、研发服务、合作或特许权收入不能自动视为核心产品已经商业化，也不能自动视为直接产品销售收入。若证据冲突或不能确定，应独立记录不确定性，不得被候选页暗示为既定结论。

### 3.2 候选证据定位（恰好3行）

| # | case_id | 股票 | 公司 | document_id | risk_code | 候选物理PDF页 |
| ---: | --- | --- | --- | --- | --- | ---: |
| 1 | `ipo_2020_01167` | `1167.HK` | 加科思－Ｂ | `ipo_2020_01167` | `precommercial_product` | 13 |
| 2 | `ipo_2020_01167` | `1167.HK` | 加科思－Ｂ | `ipo_2020_01167` | `precommercial_product` | 17 |
| 3 | `ipo_2020_09633` | `9633.HK` | 農夫山泉 | `ipo_2020_09633` | `precommercial_product` | 107 |

1167.HK的13页与17页属于同一公司的完整业务证据束，不能把两行机械解释成两个风险。9633.HK必须独立核对实际产品、销售与商业化事实，不能仅因其作为对照候选而预设结论。

## 4. 复核完成后的交接

数据治理人员只能在收到真实人工完成的CSV后执行：

1. 校验所有必填判断字段、reviewer身份和时间；
2. 机械比较primary与second review；
3. 一致项准备`double_reviewed`并表；
4. 分歧项生成仲裁清单，不得由AI裁决；
5. 仲裁完成后准备`adjudicated`并表；
6. 重新运行Golden schema/integrity、blind guard及完整回归；
7. 只有A03/A04均转为PASS后，才进行Gate A最终审计。

本盲审包本身不改变任何Golden判断，也不解除Gate A或V3-8阻塞。
