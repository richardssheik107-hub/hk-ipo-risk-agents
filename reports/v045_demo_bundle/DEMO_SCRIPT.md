# 演示脚本 — 三案例静态备份

- 来源运行：`v045_role_e_ai_v3_final` · config `configs/v045_competition_ai.yaml`
- 代码版本 `3d81e5d0d71aeb5ffc76e3f123e8eecb5c75af8d`
- 可回放案例 3/3 · 文件 66 个
- **本备份不需要网络、不需要模型凭证、不需要招股书 PDF**：所有内容都是那次运行写下的产物。

> 演示时请始终说明这是**已记录运行的回放**。回放不会重新分析，也不会产生那次运行没有产生的结论。

## 开场（约 1 分钟）

1. 打开界面，选择「演示备份」并载入案例；顶部会显示回放标识、来源运行 config 与代码版本。
2. 说明产品链路：文档解析 → 文档风险特征 → 市场特征 → 预测 → Evidence/可解释 → Final Supervisor → 最终报告；缺失的可选通道会在页面内如实显示。

## 案例 1：毛戈平化妆品股份有限公司（1318.HK）

- 载入 `ipo_2024_01318`；招股书 SHA-256 `751fbe516187b926f4292e7c2251812a173b053f53c56d5657e4789c6e5f79a3`（617 页）
- 分析标识 `27c0728f-2ab6-41a1-93d0-da29a65ef409` · workflow `enhanced_v2`

**要展示的**：
- 本案文档通道**没有**提出正式风险。这一条要照实说：系统不会为了好看补一个风险。
- 待复核：customer_concentration（medium）、material_litigation_compliance（medium），说明证据不足以定案，进入人工复核而不是被强行下结论。
- Evidence 截图 6 张（精确定位 6）：红框来自 PyMuPDF 在原页上的真实坐标，页级回退会在图注中标明。

**要照实说的**：
- 通道缺失：无。
- Final Supervisor：real provider 仲裁成功，Gate E1 满足。
- 人工复核 0 条：未复核不等于已认可，这一条不要略过。

## 案例 2：浙江同源康医药股份有限公司（2410.HK）

- 载入 `ipo_2024_02410`；招股书 SHA-256 `6c8179a58ac265d5a729895ef30db910dc15cee0a53ce653e866d487d29655cb`（706 页）
- 分析标识 `c67f05f0-f72b-4e5f-9e3c-31c2972021fa` · workflow `enhanced_v2`

**要展示的**：
- 已验证风险 **cash_runway**（critical）：2 条 Evidence，原文页 562、563；有确定性 Calculation 支撑数值
- 待复核：redemption_rights（medium）、material_litigation_compliance（medium），说明证据不足以定案，进入人工复核而不是被强行下结论。
- Evidence 截图 8 张（精确定位 8）：红框来自 PyMuPDF 在原页上的真实坐标，页级回退会在图注中标明。

**要照实说的**：
- 通道缺失：无。
- Final Supervisor：real provider 仲裁成功，Gate E1 满足。
- 人工复核 0 条：未复核不等于已认可，这一条不要略过。

## 案例 3：华润饮料控股有限公司（2460.HK）

- 载入 `ipo_2024_02460`；招股书 SHA-256 `036c61af76dc6e9e4aad070e8643e9c735c020f514cd3a3682ad2e6a43346485`（579 页）
- 分析标识 `a8b0f43e-e2a1-4265-9fc8-b28976d0eef3` · workflow `enhanced_v2`

**要展示的**：
- 本案文档通道**没有**提出正式风险。这一条要照实说：系统不会为了好看补一个风险。
- 待复核：redemption_rights（medium）、material_litigation_compliance（medium），说明证据不足以定案，进入人工复核而不是被强行下结论。
- Evidence 截图 3 张（精确定位 3）：红框来自 PyMuPDF 在原页上的真实坐标，页级回退会在图注中标明。

**要照实说的**：
- 通道缺失：无。
- Final Supervisor：real provider 仲裁成功，Gate E1 满足。
- 人工复核 0 条：未复核不等于已认可，这一条不要略过。

## 收尾

- 批量报告页展示跨案例排查顺序，并当场读出排序规则：**这是对已记录风险计数的排序，不是分数、不是概率、不是上市后表现预测**。
- 如被问到指标：M1/M2/M4、模型晋升与 one-shot Validation 尚未关闭，以 `docs/V0.4_RELEASE_ACCEPTANCE.md` 为准，不在演示中宣称 COMPETITION_READY。
