# v0.3 Legal Retriever Gap Report

```text
STATUS = RESOLVED
EXECUTION_BASE = main@6c7ba02fd18e4ce778f43b1756c9bb11a026f8cc
ACCEPTANCE = 2020—2023 DEVELOPMENT DRAFT CASES, NOT FORMAL GOLDEN RECALL
```

GATE-A-09 已在不修改 Retriever 接口、排序实现或 Evidence Schema 的前提下关闭。
正式 `redemption_rights` 与 `material_litigation_compliance` 查询族已补齐本报告列出的
简体、繁体、英文 alias，以及权利生命周期、事项状态、整改和牌照影响上下文。

基准：`src/ipo_risk/retrieval/query_families.py`

本报告是成员4向成员1提交的领域词表差异，不是第二套运行时Retriever配置。Legal Agent只调用正式查询族`redemption_rights`和`material_litigation_compliance`，不复制排序、章节权重或Evidence ID逻辑。

## redemption_rights

| 类型 | main尚缺内容 | 为什么需要 | 最小修改建议 |
|---|---|---|---|
| alias | 清算优先权／清算優先權／liquidation preference | 特殊投资者权利不一定使用redemption名称 | 加入aliases |
| alias | 反摊薄／反攤薄／anti-dilution rights | 识别上市前投资者保护条款 | 加入aliases |
| alias | 优先认购权／優先認購權／pre-emptive、pre-emption rights | 与普通章程权利区分后仍可能是特殊投资权利 | 加入aliases |
| alias | 回购权／回購權／repurchase、buyback rights | 可能承担与赎回相同的退出经济效果 | 加入aliases |
| alias | 否决权／否決權／veto rights | 特定投资者控制权 | 加入aliases |
| alias | 董事提名权／董事提名權／director nomination rights | 特定投资者董事席位权 | 加入aliases |
| alias | 对赌安排／對賭安排／valuation adjustment mechanism／VAM | 常见上市前估值调整安排 | 加入aliases，VAM按完整缩写匹配 |
| lifecycle | terminate/terminated/termination、cease、lapse、expire及简繁“终止/失效” | 防止只召回权利名称而漏掉后文终止状态 | 加入positive_context，不应作为排除词 |
| lifecycle | waive/waived/waiver、豁免 | 防止把已豁免权利当作当前权利 | 加入positive_context |
| lifecycle | restore/restorable/revive/reinstate/resume及“恢复/重新生效” | 冻结规则要求识别恢复条件 | 扩展positive_context |
| lifecycle | listing application、上市申请撤回/拒绝、IPO未完成 | 恢复条件常以申请失败或延迟触发 | 扩展positive_context |
| negative context | 普通股份回购、法定赎回、雇员购股权、全体股东一般权利 | 降低普通公司法/章程权利误召回 | 最小增加对应negative_context；不要过滤原文 |

## material_litigation_compliance

| 类型 | main尚缺内容 | 为什么需要 | 最小修改建议 |
|---|---|---|---|
| alias | litigation／诉讼／訴訟、arbitration／仲裁 | 正文可能不带“重大”标题 | 扩展aliases，依赖上下文排序控制宽词噪声 |
| alias | regulatory investigation／监管调查／監管調查 | 冻结规则覆盖监管事项 | 加入aliases |
| alias | licence/license/permit、牌照/许可/許可 | 核心许可影响属于正式风险路径 | 加入aliases |
| alias | tax／税务／稅務 | 税务争议可能构成重大未决事项 | 加入aliases |
| alias | environmental penalty、环境处罚／環境處罰 | 行政合规事项 | 加入aliases |
| alias | data privacy、数据隐私／數據隱私 | 数据监管合规事项 | 加入aliases |
| status context | pending/ongoing/unresolved及“尚未解决/仍在进行” | 判断当前未决 | 扩展positive_context |
| status context | resolved/settled/closed、已结案/已和解 | 防止历史事项误报 | 加入positive_context，保留为负证据而非过滤 |
| remediation context | remediated/rectified、已整改/整改完成 | 冻结规则要求确认监管影响是否消除 | 加入positive_context |
| licence context | renewed/not renewed/suspended operations | 判断许可影响是否消除 | 加入positive_context |
| negative context | 明确“不存在重大诉讼”的多语表达 | 防止否定句误报 | 扩展negative_context，但仍召回供Extractor判断 |
| negative context | ordinary course、future exposure、一般性风险因素模板 | 区分实际事项与未来可能性 | 扩展negative_context和discouraged_sections |

## Member-1 handoff

建议成员1只修改正式`QueryFamily`的aliases/context，不改Retriever接口、不加入发行人或页码特例。修改后应补充query-family契约测试，确认稳定Evidence ID、物理页码、负面文本仍可召回、排序可重复。

## Gate A关闭约束

关闭本报告所列缺口时必须同时满足：

1. aliases覆盖简体、繁体与英文，并兼容大小写、连字符、换行和PDF空格差异；
2. 权利生命周期、事项状态、整改状态和牌照影响上下文参与排序，不能只按宽泛事项词命中；
3. 已终止、已结案、已整改、明确否定等negative Evidence仍应召回供Agent与Verifier判断，不得因其可能是负例而过滤；
4. Evidence继续保留稳定`evidence_id`、`document_id`、`chunk_id`、物理页码及连续原文；
5. 不加入发行人、股票代码、文档ID、已知页码或Evidence ID特判；
6. 每个query family只返回小规模Top-N候选集，不得通过无限扩大`limit`伪造召回改善；
7. 使用2020—2023 development-set正例、负例和边界例验证真实召回及排序，并保持现金跑道等既有Retriever回归；
8. 2025 blind set不得用于词表、权重、Prompt或排序调优。

本报告只描述Retriever领域缺口，不复制Agent、Builder或Verifier实现说明。实际修改必须由独立Approved Plan授权，并在修改后以query-family契约测试和真实development-set召回结果关闭`GATE-A-09`。

## GATE-A-09关闭结果

修改前八份 development draft 案例的 Top-5 命中为 4/8；整改后在固定
`limit=5` 下为：

| 案例 | 股票代码 | 查询族 | 目标物理页 | 最终排名 | Top-5 |
|---|---|---|---:|---:|---|
| A | 9898.HK | `redemption_rights` | 300 | 4 | HIT |
| B | 9863.HK | `redemption_rights` | 207 | 4 | HIT |
| C | 2517.HK | `redemption_rights` | 152 | 2 | HIT |
| D | 1961.HK | `redemption_rights` | 78 | 3 | HIT |
| E | 6698.HK | `material_litigation_compliance` | 26 | 2 | HIT |
| F | 2451.HK | `material_litigation_compliance` | 298 | 2 | HIT |
| G | 9600.HK | `material_litigation_compliance` | 222 | 2 | HIT |
| H | 1942.HK | `material_litigation_compliance` | 44 | 1 | HIT |

汇总：Top-1 1/8、Top-3 6/8、Top-5 8/8。以上仅为 2020—2023 开发集
验收，不代表经过人工 primary/second review 的正式 Golden Recall。A—H 的 Golden
治理状态没有因此改变。

验证结果：Legal 查询族契约 71 passed、既有 Keyword Retriever 契约 28 passed、
全量测试 849 passed；2410.HK 现金及现金流主证据页、现金跑道 2.76 个月、
verified 与 90/critical 回归保持稳定。未访问 2025 blind set。
