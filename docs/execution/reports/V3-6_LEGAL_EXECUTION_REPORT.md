# V3-6 Legal Execution Report

本文件记录`feat/legal-domain-dictionary`上的真实执行结果。仓库中没有已批准的V3-6实施计划，因此本报告不声称对应任何approved plan。

# Baseline

- branch start SHA: `ff7ff53d4b7cb372266f73c3664d294f860a1848`
- hardening commit: `fe18fed37c93f938e7bd85c5f58d22c9c030c460`
- merged `origin/main`: `da317612768828a27e37da679e2205625164a1f4`
- merge/validated code commit: `21cfef5c8292b51543e283ca668a0f20f9f38e71`
- final relation after this report-only commit: ahead 6 / behind 0

Git commit无法在自身正文中稳定记录自己的SHA；本文件记录已验证代码和merge SHA，最终report-only commit SHA记录在交付汇报中。

# Scope

仅覆盖V3-6 Legal Agent：`redemption_rights`和`material_litigation_compliance`。本轮未修改Workflow、Service、Container、Supervisor、公共Schema、公共Verifier路由、LLMProvider、Retriever query families或configs。

# Implemented

- `ShareholderRightsExtractor`与`LitigationComplianceExtractor`结构化事实抽取；
- `RedemptionRightsRiskBuilder`与`MaterialLitigationComplianceRiskBuilder`确定性规则；
- 否定、未来风险和模板文本识别；
- 两个风险的失败隔离和`ComponentDiagnostic`；
- `LegalRightsVerifier`与`LitigationComplianceVerifier`领域规则；
- A–H development-only Legal draft cases；
- 真实V3-3 Retriever、Mock/Unavailable V3-4 Provider、Builder和Verifier组合测试。

# Reconciliation

- Legal Agent只调用正式`redemption_rights`和`material_litigation_compliance` query families；
- 复用V3-4公共`UnavailableLLMProvider`与`LLMProviderError`；
- 已删除重复YAML runtime dictionary；
- 已删除Legal私有unavailable provider和多关键词Retriever循环。

# Litigation Decision Hardening

事项类型现在进入互斥decision families：

- proceeding/status：`litigation`、`arbitration`、`tax`、`regulatory_investigation`；
- remediation：`administrative_penalty`、`non_compliance`、`environmental_penalty`、`data_privacy`；
- licence：`license_permit`。

未整改处罚/合规事项不会再被`management_materiality=not_material`提前短路。已解决处罚但整改不清进入`needs_review`；已整改且无持续影响为`not_applicable`；未决或明确未整改进入Verifier candidate。

# Contract Delta

- 两个Candidate上的`extra="forbid"`已经移除，恢复Pydantic默认额外字段兼容行为；
- 剩余delta只有带默认值的additive candidate fields；
- termination timing、restoration condition、remediation和license impact等字段仍需Member-1批准；
- 本报告不宣称frozen contract已经更新。

# Prompt Status

`ShareholderRightsExtractor`使用`shareholder_rights_extract / legal_shareholder_rights_v1`，`LitigationComplianceExtractor`使用`litigation_compliance_extract / legal_litigation_compliance_v1`，并有防漂移契约测试。

`LEGAL_DOMAIN_PROMPT_RUNTIME_STATUS = NOT_INTEGRATED`。当前real Provider没有加载Legal domain instruction，仍需Member-1实现prompt registry/resolver。

# Retriever Gap

Legal Agent没有第二套Retriever。仍缺的aliases、lifecycle、status、negative/template context记录在`docs/V03_LEGAL_RETRIEVAL_GAP_REPORT.md`，正式patch由Member-1维护。

# Golden Status

- A–H仍为`draft`，全部来自development，不含2025 blind；
- 未填写`second_reviewer`，未标记`double_reviewed/adjudicated`；
- 这些案例不是正式accuracy evidence；
- Case C仍为`LEGAL_GOLDEN_ADJUDICATION_REQUIRED`；
- A/E仍等待`MEMBER_1_LEGAL_SEVERITY_POLICY_QUESTION`。

# Validation

真实执行结果：

- 8组Legal focused tests：`9 + 8 + 20 + 20 + 27 + 18 + 16 + 6 passed`；
- 7组既有Legal contract tests：`1 + 4 + 2 + 4 + 3 + 2 + 4 passed`；
- Legal prompt identity contract：`2 passed`；
- V3-3 Retriever contract：`40 passed`；
- V3-4 LLMProvider contract：`22 passed`；
- Financial v0.3 tests：`207 passed`；
- full suite：`771 passed in 64.85s`；
- `python scripts/validate_project.py`：`status=completed verified=3 pending=1`；
- `python scripts/validate_competition_data.py`：`competition_data_validation=passed`；
- `python -m compileall -q app src scripts`：passed；
- `git diff --check`：passed；
- `python scripts/check_real_v02_e2e.py`：passed，2410.HK cash runway=`2.76 months`，Evidence pages=`563, 562`。

`scripts/evaluate_v03_golden_cases.py`存在，但本地没有可用的`analysis_results.jsonl`输入，因此未伪造评测运行，也未把Legal draft cases用作正式accuracy结果。

# Known Limitations

- real Legal domain prompt尚未接入；
- Retriever仍缺部分法律aliases和生命周期/状态上下文；
- Candidate additive fields尚未获得公共契约批准；
- 跨页条款、OCR和模糊termination/restoration仍可能需要人工判断；
- Legal severity policy未冻结；
- Legal golden cases未完成双人复核；
- Legal standalone core尚未注册到共享Container/Workflow；该集成由Member-1后续完成。

# Member-1 Handoff

- candidate contract approval；
- prompt registry integration；
- Retriever gap patch；
- Legal severity policy；
- Container registration；
- specialized Verifier routing；
- `enhanced_v2` integration。

# Member-2 / Human Handoff

- Legal golden second review；
- Case C adjudication；
- reviewed cases向canonical manifest并表。

# PR Readiness

`STANDALONE-READY / PR-READY`。Hardening已提交，最新main已普通merge，全部要求的回归通过。Candidate approval、Prompt registry、Retriever gap、severity policy、共享注册与黄金二审均作为明确的PR review item或后续handoff，不是PR opening blocker。
