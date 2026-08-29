# 批量风险报告 — Batch risk report

- 运行配置 config: `configs/v045_competition_ai.yaml`
- 代码版本 code_base_sha: `3d81e5d0d71aeb5ffc76e3f123e8eecb5c75af8d`
- 案例清单 cases_manifest_sha256: `e07b8ff5fc64da01c82641b513949938147bd8089ff06f0642da13523eea3659` · config_sha256: `eb5ad1034dadff08274227bd844c7c6444cbeb73d0a0d7f19aabbb0547a221d8`
- 案例数: 声明 3 · 实际执行 3
- 招股书 SHA-256 全部符合冻结目录: `True` · 读取上市后 outcome: `False` · 触碰 2025 Blind: `False`

## 排查顺序 Triage order

> ordered by the number of verified risks at each severity, critical first, then high, medium, low; ties broken by pending-risk count and then by case_id. This orders recorded risk counts. It is not a score, not a probability and not a prediction of post-listing performance.

| # | 案例 | 股票 | 已验证风险 | critical/high/medium/low | 待复核 | 冲突 | Final Supervisor | 可追溯 | Evidence | 截图 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 浙江同源康医药股份有限公司<br>`ipo_2024_02410` | 2410.HK | 1 | 1/0/0/0 | 2 | 7 | accepted · real provider | 1.0 | 8 | 8（精确 8） |
| 2 | 毛戈平化妆品股份有限公司<br>`ipo_2024_01318` | 1318.HK | 0 | 0/0/0/0 | 2 | 5 | accepted · real provider | 1.0 | 6 | 6（精确 6） |
| 3 | 华润饮料控股有限公司<br>`ipo_2024_02460` | 2460.HK | 0 | 0/0/0/0 | 2 | 5 | accepted · real provider | 1.0 | 3 | 3（精确 3） |

## 逐案摘要 Per-case detail

### 浙江同源康医药股份有限公司 · 2410.HK

- case_id `ipo_2024_02410` · 上市日 `2024-08-20` · 运行状态 `completed`
- 招股书 SHA-256 `6c8179a58ac265d5a729895ef30db910dc15cee0a53ce653e866d487d29655cb`
- 已验证风险：
  - **cash_runway** · critical · agent `financial` · 2 条 Evidence（含确定性 Calculation）
- 待复核：redemption_rights（medium）、material_litigation_compliance（medium）
- 通道状态：`document`=available、`market`=available、`model`=available、`rule`=available
- Final Supervisor：`available` / `accepted` — grounded supervisory synthesis available；确定性下限 `critical`；Gate E1 satisfied
- 冲突 7（partially_resolved 5、unresolved 2）· 定向复核 7 次 · 可追溯 1.0
- 人工复核：0 条（未复核 ≠ 已认可）

### 毛戈平化妆品股份有限公司 · 1318.HK

- case_id `ipo_2024_01318` · 上市日 `2024-12-10` · 运行状态 `completed`
- 招股书 SHA-256 `751fbe516187b926f4292e7c2251812a173b053f53c56d5657e4789c6e5f79a3`
- 已验证风险：
  - 本次运行文档通道未提出正式风险；此处不代填。
- 待复核：customer_concentration（medium）、material_litigation_compliance（medium）
- 通道状态：`document`=available、`market`=available、`model`=available、`rule`=available
- Final Supervisor：`available` / `accepted` — grounded supervisory synthesis available；确定性下限 `low`；Gate E1 satisfied
- 冲突 5（partially_resolved 4、unresolved 1）· 定向复核 5 次 · 可追溯 1.0
- 人工复核：0 条（未复核 ≠ 已认可）

### 华润饮料控股有限公司 · 2460.HK

- case_id `ipo_2024_02460` · 上市日 `2024-10-23` · 运行状态 `completed`
- 招股书 SHA-256 `036c61af76dc6e9e4aad070e8643e9c735c020f514cd3a3682ad2e6a43346485`
- 已验证风险：
  - 本次运行文档通道未提出正式风险；此处不代填。
- 待复核：redemption_rights（medium）、material_litigation_compliance（medium）
- 通道状态：`document`=available、`market`=available、`model`=available、`rule`=available
- Final Supervisor：`available` / `accepted` — grounded supervisory synthesis available；确定性下限 `low`；Gate E1 satisfied
- 冲突 5（partially_resolved 4、unresolved 1）· 定向复核 5 次 · 可追溯 1.0
- 人工复核：0 条（未复核 ≠ 已认可）

## 汇总 Aggregate

- 已验证风险合计 1 条（critical 1 · high 0 · medium 0 · low 0）；待复核 6 条
- 跨案例风险码频次：cash_runway ×1
- real-provider 仲裁 3/3 · 确定性降级 0 · Gate E1 满足 3
- 可追溯率最低 1.0 · 达到 1.0 的案例 3/3
- Evidence 行合计 17 · 截图 17（精确定位 17）
- 人工复核合计 0 条，覆盖 0/3 个案例

## 这份报告不支持什么 Limitations

- 3 case(s) carry no human review. That is an absence of review, not an approval.
- The ordering below ranks recorded risk counts. No post-listing outcome was read for any case in this batch, so nothing here is a claim about how these companies will perform.
