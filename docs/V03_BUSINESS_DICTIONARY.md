# v0.3 业务词典交接文档（5号 → 1号）

> 按分工矩阵：Retriever 框架归 1号，词典由 3/4/5号提供。
> 本文档是 5号的业务词典交付物，**不直接修改 `query_families.py`**，
> 由 1号评审后集成。集成时需要 1号同步处理的三件事见文末清单。

## 一、现有覆盖核对（2026-08-10）

任务书 5号关键词清单 vs 当前 `query_families.py`：

| 任务书关键词 | 状态 |
| --- | --- |
| 核心产品、核心管线、候选药物、商业化、尚未产生收入、产品销售收入 | 已覆盖（简/繁/英） |
| 业务概览 | **缺失** |
| 临床试验、监管批准 | 仅在 positive_context，未进 aliases |
| 合作伙伴、授权引进、授权输出、单一产品依赖、研发失败 | **完全缺失** |

## 二、建议新增查询族：`partner_collaboration_dependency`

```python
QueryFamily(
    name="partner_collaboration_dependency",
    aliases=(
        "合作伙伴", "合作夥伴", "合作方", "合作协议", "合作協議",
        "collaboration partner", "collaboration partners", "collaboration agreement",
        "授权引进", "授權引進", "引进授权", "引進授權", "license-in",
        "in-license", "in-licensing", "licensed in",
        "授权输出", "授權輸出", "对外授权", "對外授權", "license-out",
        "out-license", "out-licensing", "licensed out",
        "许可协议", "許可協議", "license agreement", "licensing agreement",
        "授权收入", "授權收入", "licensing revenue", "licence revenue",
        "依赖合作方", "依賴合作方", "partner dependency", "reliance on partners",
        "单一产品依赖", "單一產品依賴", "依赖单一产品", "依賴單一產品",
        "single product dependency", "reliance on a single product",
        "研发失败", "研發失敗", "临床试验失败", "臨床試驗失敗",
        "development failure", "clinical trial failure",
    ),
    positive_context=(
        "独家", "獨家", "里程碑", "商业化权利", "商業化權利", "大中华区",
        "大中華區", "特许权使用费", "特許權使用費", "首付款",
        "exclusive", "milestone", "commercialization rights", "greater china",
        "royalty", "royalties", "upfront payment", "territory",
        "核心产品", "核心產品", "core product", "管线", "管線", "pipeline",
    ),
    negative_context=(
        "行业概览", "行業概覽", "监管概览", "監管概覽", "释义", "釋義",
        "industry overview", "regulatory overview", "glossary",
    ),
    preferred_sections=("business", "products", "业务", "業務", "核心产品", "核心產品"),
    discouraged_sections=("definitions", "释义", "釋義", "risk factors", "风险因素", "風險因素"),
)
```

## 三、建议补充到现有业务族的 aliases

- `commercialization_status` 增加：`"业务概览", "業務概覽", "business overview", "监管批准", "監管批准", "regulatory approval"`
- `core_product_pipeline` 增加：`"临床试验", "臨床試驗", "clinical trial", "clinical trials"`

## 四、建议补充的检索召回用例（`business_recall_cases.json`）

```json
[
  {
    "case_id": "partner_dependency_simplified",
    "family": "partner_collaboration_dependency",
    "section": "unknown",
    "text": "业务：我们高度依赖合作方推进核心产品的商业化，授权引进协议约定里程碑付款。",
    "expected_terms": ["依赖合作方", "授权引进"]
  },
  {
    "case_id": "partner_dependency_traditional",
    "family": "partner_collaboration_dependency",
    "section": "unknown",
    "text": "業務：我們與合作夥伴訂立合作協議，並就核心產品授權輸出收取特許權使用費。",
    "expected_terms": ["合作夥伴", "授權輸出"]
  },
  {
    "case_id": "partner_dependency_english",
    "family": "partner_collaboration_dependency",
    "section": "unknown",
    "text": "Business: We rely on our collaboration partner under an exclusive license agreement for the commercialization rights of our core product, with milestone and royalty payments.",
    "expected_terms": ["collaboration partner", "license agreement"]
  },
  {
    "case_id": "single_product_dependency_simplified",
    "family": "partner_collaboration_dependency",
    "section": "unknown",
    "text": "业务：我们存在单一产品依赖，收入主要来自唯一核心产品，研发失败将产生重大影响。",
    "expected_terms": ["单一产品依赖", "研发失败"]
  },
  {
    "case_id": "clinical_trial_failure_english",
    "family": "partner_collaboration_dependency",
    "section": "unknown",
    "text": "Business: Our business depends on a single core product and any clinical trial failure would materially affect our pipeline.",
    "expected_terms": ["clinical trial failure"]
  }
]
```

## 五、集成时 1号需要同步的三件事

1. `query_families.py`：加入上文查询族与 aliases；
2. `tests/contract/test_v03_retriever_query_families.py`：查询族目录契约
   （`test_v03_query_family_catalog_and_public_signature_are_stable`）登记
   `partner_collaboration_dependency`；
3. `business_v03.py`：`BUSINESS_EVIDENCE_QUERIES` 追加
   `"partner_collaboration_dependency"`，使合作方证据参与业务风险判断。

以上词条均已在 5号本地环境用简/繁/英真实词条实测命中。

## 六、转 4号复核的法律词典缺口（不属于 5号范围，仅记录）

任务书 4号清单中的 **社保公积金**（社保 / 社会保险 / 社會保險 / 公积金 /
住房公積金 / social insurance / housing provident fund）在
`material_litigation_compliance` 查询族和 `legal_matter_classifier.py`
结构化分类规则中均未覆盖。社保公积金欠缴是港股招股书高频不合规事项，
建议 4号在词典和分类器中同步补充。
