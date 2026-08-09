# v0.3 Legal Verifier 专业规则

规则版本：`v03_legal_verifier_rules_v1`

实现文件：`src/ipo_risk/domain/legal_verifiers.py`

责任边界：法务成员提供 `LegalRightsVerifier`、`LitigationComplianceVerifier` 及专业测试；1号技术负责人负责把专用规则注册到公共 `RuleVerifier`、传入完整候选Evidence并维护公共 `VerificationResult` 路由。本实现不修改公共Verifier接口。

## 1. 通用核验原则

两个法律Verifier均接收一个候选`RiskItem`和`Mapping[evidence_id, Evidence]`，返回`LegalVerificationResult`。公共框架可根据其中的`status`路由：

- `verified`：Evidence身份、正文、来源和专业事实均一致；
- `rejected`：Evidence明确证明候选把负例、历史事项、普通章程权利或已解决事项误作当前风险；
- `needs_review`：确有相关事实，但上下文、状态、主体、重大性、影响或冲突无法确定；
- `pending`：候选没有Evidence或本次未能取得对应Evidence，禁止核验通过。

共同硬性检查包括风险码、Legal类别、Agent名称、canonical code、Evidence ID和正文一致性、招股书来源及同一文档。任何Verifier都不得因为Agent已有结论而跳过原始Evidence，也不得自动把缺失Evidence解释为无风险。

## 2. LegalRightsVerifier

只处理`redemption_rights`。完整核验顺序如下：

1. Evidence是否确实披露特殊股东权利；
2. 是否同时包含上市时点和生命周期上下文；
3. 是否检查了后文的终止、豁免、失效及恢复条款；
4. 权利是历史权利还是当前权利；
5. 是上市前或上市时终止，还是上市后继续存在；
6. `holder`是否能在Evidence中得到支持；
7. 是否存在Pre-IPO投资者、优先股股东或特定投资者语境；
8. 是否把公司章程、全体股东或普通股东的一般权利误判为特殊投资者权利；
9. 不同Evidence是否对终止、继续有效或恢复状态互相冲突；
10. Extractor或Builder是否已经记录需人工法律判断的不确定性。

确定性结果：

- 完整特殊投资者条款明确上市后仍有效，且holder和Evidence一致，可`verified`；
- 普通章程权利被误判，或历史权利已豁免/终止且明确不恢复，应`rejected`；
- 生命周期上下文不完整、漏掉恢复条款、holder无支持或Evidence互相冲突，应`needs_review`；
- Verifier不会仅凭“redemption right”等权利名称通过核验。

“检查后文”要求1号在集成时传入Retriever取得的完整候选Evidence，包括相邻页或同一条款的续页。专业Verifier只能检查收到的Evidence，不能推断未传入页面不存在终止、豁免或恢复条款。

## 3. LitigationComplianceVerifier

只处理`material_litigation_compliance`，复用L6的否定和模板分类结果，并按以下顺序核验：

1. 是实际案件、处罚、调查或牌照事项，还是一般风险提示、模板声明或明确否定；
2. Evidence中是否同时存在实际事项和否定声明；
3. 当前状态是否为未决、进行中、已结案、已和解或已整改；
4. 是否为历史事项；
5. 管理层是否明确判断为不重大；
6. 处罚或合规事项是否已经完成整改；
7. 牌照/许可证是否尚未续期、影响经营，或影响已经消除；
8. Builder记录的`is_pending/is_resolved/is_remediated`是否与Evidence一致；
9. `management_materiality`和`potential_impact`是否有Evidence支持；
10. 是否在无证据情况下推断重大影响、经营中断或牌照影响。

确定性结果：

- 重大未决真实事项、未消除的监管或核心牌照影响，且状态和影响均有Evidence支持，可`verified`；
- 只有未来风险提示、明确不存在实际事项、已结案/和解/整改且无持续影响、管理层明确不重大且无相反影响证据，应`rejected`；
- 实际事项与否定声明冲突、结案或整改状态不清、管理层重大性与影响披露冲突、牌照影响不清或重大影响缺少原文支持，应`needs_review`；
- 处罚事项没有整改状态，不能仅凭处罚关键词核验通过。

## 4. 交给公共Verifier的集成要求

1号接入时建议按风险码分派：

```text
redemption_rights
→ LegalRightsVerifier.verify(risk, available_evidence)

material_litigation_compliance
→ LitigationComplianceVerifier.verify(risk, available_evidence)
```

公共框架负责把`verified_risk`或`reviewed_risk`放入`VerificationResult`对应列表。不得在专业Verifier之后再次用“Evidence非空、score不大于95”之类通用条件覆盖法律核验结果。

集成测试必须覆盖：后页终止/豁免/恢复、普通章程权利、实际事项与否定冲突、未来风险提示、历史已结案事项、处罚已整改与整改不清、牌照未续期与已续期，以及无Evidence时不得`verified`。
