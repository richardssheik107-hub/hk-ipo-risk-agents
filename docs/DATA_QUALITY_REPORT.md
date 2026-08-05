# 赛事数据质量报告

> 本文件由 `scripts/build_competition_manifest.py` 生成。详细逐项记录见
> `data/catalog/data_quality_issues.csv`。

## 结论

赛事数据可以支持v0.2文档链路和影子测试，但尚不能直接支持正式上市后风险标签或市场模型。
证券主表在补齐前必须隔离；成交金额单位在确认前不得进入特征工程；无行情样本只能用于降级测试。

## 问题汇总

| 问题代码 | 数量 | 最高严重度 | 当前处理 |
|---|---:|---|---|
| EOD_AMOUNT_UNIT_UNCONFIRMED | 1 | warning | open |
| EOD_NOT_AVAILABLE | 10 | warning | accepted_degradation |
| OFFICIAL_IPO_INSTITUTION_INFO_MISSING | 4 | warning | accepted_degradation |
| OFFICIAL_IPO_MASTER_MATCH_MISSING | 3 | warning | open |
| SECURITY_MASTER_TRUNCATED | 1 | critical | quarantined |


## 使用限制

1. 2025年116份招股书是盲测集，不得用于调试Retriever、构造规则或模型调参。
2. `hksharedescription.csv`处于`quarantined`状态，不得据此生成上市日期和发行价。
3. 招股书披露日期不是上市日期。
4. `S_DQ_AMOUNT`单位确认前，不构造成交金额类特征。
5. 无行情覆盖的样本不构造价格标签，只用于文档链路及降级测试。
6. 所有未匹配、坏行和缺失值必须保留问题记录，不得人工猜测后回填。
