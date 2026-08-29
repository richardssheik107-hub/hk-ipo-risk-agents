"""Deterministic v0.3 retriever query-family definitions.

The vocabulary is prospectus-domain terminology only.  It deliberately contains
no issuer identity, security code, case identifier, or page-specific rule.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QueryFamily:
    """Aliases and contextual ranking signals for one retrieval intent."""

    name: str
    aliases: tuple[str, ...]
    positive_context: tuple[str, ...]
    negative_context: tuple[str, ...]
    preferred_sections: tuple[str, ...]
    discouraged_sections: tuple[str, ...]
    financial_table_weight: bool = False


QUERY_FAMILIES: tuple[QueryFamily, ...] = (
    QueryFamily(
        name="revenue",
        aliases=(
            "收入", "营业收入", "營業收入", "收益", "收入增长", "收入增長",
            "收益增长", "收益增長", "revenue", "turnover", "revenue growth",
        ),
        positive_context=(
            "综合损益表", "綜合損益表", "损益及其他全面收益表",
            "損益及其他全面收益表", "历史财务资料", "歷史財務資料",
            "分部资料", "分部資料", "业绩记录期", "業績記錄期",
            "statement of profit or loss", "historical financial information",
            "segment information", "revenue by",
        ),
        negative_context=(
            "释义", "釋義", "行业概览", "行業概覽", "监管概览", "監管概覽",
            "glossary", "industry overview", "regulatory overview",
        ),
        preferred_sections=(
            "financial", "财务资料", "財務資料", "accountants report",
            "historical financial information",
        ),
        discouraged_sections=(
            "summary", "概要", "risk factors", "风险因素", "風險因素",
            "industry overview", "行业概览", "行業概覽",
        ),
        financial_table_weight=True,
    ),
    QueryFamily(
        name="continuous_loss",
        aliases=(
            "持续亏损", "持續虧損", "连续亏损", "連續虧損", "持续录得亏损",
            "持續錄得虧損", "净亏损", "淨虧損", "continuous loss",
            "continued losses", "history of losses", "net loss", "loss for the year",
        ),
        positive_context=(
            "综合损益表", "綜合損益表", "年内亏损", "年內虧損", "期内亏损",
            "期內虧損", "累计亏损", "累計虧損", "历史财务资料", "歷史財務資料",
            "statement of profit or loss", "loss for the year", "loss for the period",
            "accumulated losses", "historical financial information",
        ),
        negative_context=(
            "释义", "釋義", "行业概览", "行業概覽", "前瞻性陈述", "前瞻性陳述",
            "glossary", "industry overview", "forward-looking statements",
        ),
        preferred_sections=(
            "financial", "财务资料", "財務資料", "accountants report",
            "historical financial information",
        ),
        discouraged_sections=("summary", "概要", "risk factors", "风险因素", "風險因素"),
        financial_table_weight=True,
    ),
    QueryFamily(
        name="customer_concentration",
        aliases=(
            "客户集中度", "客戶集中度", "五大客户", "五大客戶", "最大客户",
            "最大客戶", "主要客户", "主要客戶", "customer concentration",
            "top five customers", "largest customer", "major customers",
            "来自五大客户的收入", "來自五大客戶的收入",
            "五大客户应占收入", "五大客戶應佔收入",
            "向五大客户作出的销售", "向五大客戶作出的銷售",
            "单一最大客户的收入", "單一最大客戶的收入",
        ),
        positive_context=(
            "来自五大客户", "來自五大客戶", "占总收入", "佔總收入", "销售额",
            "銷售額", "客户依赖", "客戶依賴", "revenue attributable to",
            "percentage of total revenue", "sales to", "customer dependency",
        ),
        negative_context=(
            "五大供应商", "五大供應商", "采购额", "採購額", "供应商集中度",
            "供應商集中度", "top five suppliers", "purchases from", "supplier concentration",
        ),
        preferred_sections=("business", "customers", "客户", "客戶", "financial"),
        discouraged_sections=("definitions", "释义", "釋義", "regulatory overview", "监管概览", "監管概覽"),
        financial_table_weight=True,
    ),
    QueryFamily(
        name="supplier_concentration",
        aliases=(
            "供应商集中度", "供應商集中度", "五大供应商", "五大供應商",
            "前五大供应商", "前五大供應商",
            "最大供应商", "最大供應商", "主要供应商", "主要供應商",
            "supplier concentration", "top five suppliers", "largest supplier", "major suppliers",
            "向前五大供应商采购", "向前五大供應商採購",
            "前五大供应商采购额", "前五大供應商採購額",
            "单一最大供应商采购", "單一最大供應商採購",
        ),
        positive_context=(
            "向五大供应商采购", "向五大供應商採購", "占总采购额", "佔總採購額",
            "采购额", "採購額", "供应商依赖", "供應商依賴",
            "占销售成本", "佔銷售成本", "占收入成本", "佔收入成本",
            "purchases from", "percentage of total purchases", "procurement", "supplier dependency",
        ),
        negative_context=(
            "五大客户", "五大客戶", "销售额", "銷售額", "客户集中度",
            "客戶集中度", "top five customers", "sales to", "customer concentration",
        ),
        preferred_sections=("business", "suppliers", "供应商", "供應商", "financial"),
        discouraged_sections=("definitions", "释义", "釋義", "regulatory overview", "监管概览", "監管概覽"),
        financial_table_weight=True,
    ),
    QueryFamily(
        name="redemption_rights",
        aliases=(
            "赎回权", "贖回權", "赎回权利", "贖回權利", "特殊股东权利",
            "特殊股東權利", "可赎回优先股", "可贖回優先股", "redemption rights",
            "right of redemption", "special shareholder rights", "redeemable preferred shares",
            "特殊权利", "特殊權利", "特别权利", "特別權利",
            "清算优先权", "清算優先權", "liquidation preference", "liquidation preferences",
            "反摊薄", "反攤薄", "反摊薄权", "反攤薄權", "anti-dilution right", "anti-dilution rights",
            "优先认购权", "優先認購權", "pre-emptive right", "pre-emptive rights",
            "pre-emption right", "pre-emption rights", "preemption rights",
            "回购权", "回購權", "repurchase right", "repurchase rights", "buyback rights",
            "否决权", "否決權", "一票否决权", "一票否決權", "veto right", "veto rights",
            "董事提名权", "董事提名權", "director nomination right", "director nomination rights",
            "对赌安排", "對賭安排", "估值调整机制", "估值調整機制",
            "valuation adjustment mechanism", "vam", "vam agreement", "vam arrangement",
        ),
        positive_context=(
            "投资协议", "投資協議", "股东协议", "股東協議", "优先股", "優先股",
            "上市时终止", "上市時終止", "恢复效力", "恢復效力", "重组", "重組",
            "investment agreement", "shareholders agreement", "preferred shares",
            "terminate upon listing", "restored", "reorganisation",
            "终止", "終止", "失效", "停止生效", "豁免", "恢复", "恢復", "重新生效",
            "上市申请撤回", "上市申請撤回", "上市申请被拒绝", "上市申請被拒絕",
            "上市申请拒绝", "上市申請拒絕",
            "首次公开发售未完成", "首次公開發售未完成",
            "terminate", "terminated", "termination", "cease", "ceased", "lapse", "lapsed",
            "expire", "expired", "waive", "waived", "waiver", "restore", "restorable",
            "revive", "revived", "reinstate", "reinstated", "resume", "resumed",
            "listing application withdrawn", "listing application is withdrawn",
            "listing application rejected", "listing application is rejected",
            "ipo not completed", "ipo is not completed",
            "initial public offering not completed", "initial public offering is not completed",
        ),
        negative_context=(
            "公司条例", "公司條例", "组织章程细则概要", "組織章程細則概要",
            "一般股东权利", "一般股東權利", "companies ordinance",
            "summary of articles", "general shareholder rights",
            "普通股份回购", "普通股份回購", "法定赎回", "法定贖回",
            "雇员购股权", "僱員購股權", "员工购股权", "僱員股份期权",
            "ordinary share buyback", "statutory redemption", "employee share options",
            "rights of all shareholders", "general rights of shareholders",
        ),
        preferred_sections=(
            "history", "reorganisation", "corporate information", "股本", "历史及重组",
            "歷史及重組", "主要股东", "主要股東",
        ),
        discouraged_sections=("statutory", "法定及一般资料", "法定及一般資料", "definitions", "释义", "釋義"),
    ),
    QueryFamily(
        name="material_litigation_compliance",
        aliases=(
            "重大诉讼", "重大訴訟", "诉讼及合规", "訴訟及合規", "法律程序",
            "行政处罚", "行政處罰", "监管不合规", "監管不合規",
            "material litigation", "legal proceedings", "regulatory non-compliance",
            "administrative penalty", "material legal proceedings",
            "合规与诉讼", "合規與訴訟", "合规及诉讼", "合規及訴訟",
            "诉讼", "訴訟", "法律诉讼", "法律訴訟", "litigation",
            "仲裁", "arbitration",
            "监管调查", "監管調查", "regulatory investigation",
            "牌照", "许可", "許可", "licence", "license", "permit",
            "税务", "稅務", "tax",
            "社会保险", "社會保險", "社保", "住房公积金", "住房公積金", "公积金", "公積金",
            "social insurance", "housing provident fund", "provident fund contribution",
            "环境处罚", "環境處罰", "environmental penalty",
            "数据隐私", "數據隱私", "data privacy",
        ),
        positive_context=(
            "未决诉讼", "未決訴訟", "仲裁", "监管调查", "監管調查", "罚款", "罰款",
            "处罚决定", "處罰決定", "整改", "重大不利影响", "重大不利影響",
            "pending litigation", "arbitration", "regulatory investigation", "fine",
            "penalty decision", "rectification", "material adverse effect",
            "索赔金额", "索賠金額", "担任被告", "擔任被告", "提起诉讼", "提起訴訟",
            "法律申索", "合约申索", "合約申索", "产品责任申索", "產品責任申索",
            "潜在第三方纠纷", "潛在第三方糾紛", "legal claim", "legal claims",
            "claims amount", "named as defendant", "brought proceedings",
            "尚未解决", "尚未解決", "仍在进行", "仍在進行", "正在进行", "正在進行",
            "未解决", "未解決", "未结案", "未結案", "已结案", "已結案", "已和解",
            "整改完成", "已整改", "已续期", "已續期", "未续期", "未續期",
            "暂停营业", "暫停營業", "停止营业", "停止營業", "牌照暂停", "牌照暫停",
            "许可证暂停", "許可證暫停", "许可被暂停", "許可被暫停",
            "pending", "ongoing", "unresolved", "resolved", "settled", "closed",
            "remediated", "rectified", "renewed", "not renewed", "suspended operations",
            "licence suspended", "license suspended", "permit suspended",
        ),
        negative_context=(
            "可能受到监管", "可能受到監管", "一般监管规定", "一般監管規定",
            "概不知悉任何", "no material litigation", "may be subject to regulation",
            "general regulatory requirements",
            "不存在重大诉讼", "不存在重大訴訟", "并无重大诉讼", "並無重大訴訟",
            "没有重大诉讼", "沒有重大訴訟",
            "未来可能", "未來可能", "一般性风险", "一般性風險",
            "ordinary course of business", "future exposure", "general risk disclosure",
            "may become subject to", "could be subject to",
        ),
        preferred_sections=("legal", "litigation", "regulatory", "业务", "業務"),
        discouraged_sections=("risk factors", "风险因素", "風險因素", "regulatory overview", "监管概览", "監管概覽"),
    ),
    QueryFamily(
        name="commercialization_status",
        aliases=(
            "商业化状态", "商業化狀態", "尚未商业化", "尚未商業化", "未商业化",
            "未商業化", "无商业化产品", "無商業化產品", "commercialization status",
            "not yet commercialized", "no commercialized products", "pre-commercial",
            "尚未获准进行商业销售", "尚未獲准進行商業銷售", "尚未获准商业销售",
            "尚未獲准商業銷售", "尚未从产品销售产生任何收入",
            "尚未從產品銷售產生任何收入", "产品销售收入", "產品銷售收入",
            "生产及商业化", "生產及商業化", "商业规模生产", "商業規模生產",
            "商业化团队", "商業化團隊", "产品商业化", "產品商業化",
            "生产及销售", "生產及銷售", "制造及销售", "製造及銷售",
            "产品所产生的收益", "產品所產生的收益", "产品销售收益", "產品銷售收益",
            "no products approved for commercial sale", "not approved for commercial sale",
            "have not generated revenue from product sales", "no product sales revenue",
            "products have not commenced commercial sales", "not commenced commercial sales",
            "manufacture and sell", "manufactured and sold", "products we manufacture and sell",
            "revenue generated from product sales", "revenue from product sales",
            "commercial product sales", "commercial launch", "launched products",
            "licensing agreement", "licence agreement", "collaboration agreement",
            "strategic partnership", "milestone payment", "research and development services",
        ),
        positive_context=(
            "核心产品", "核心產品", "产品销售收入", "產品銷售收入", "商业销售", "商業銷售",
            "上市批准", "药品批准", "藥品批准", "临床阶段", "臨床階段",
            "core product", "product sales revenue", "commercial sales", "marketing approval",
            "clinical stage", "commercial production", "主要产品类别", "主要產品類別",
            "主要产品", "主要產品", "产品收益", "產品收益", "产品所产生的收益",
            "產品所產生的收益", "向市场推出", "向市場推出", "销售网络", "銷售網絡",
            "principal products", "main products", "product revenue", "sales network",
            "licensing revenue", "licence revenue", "milestone revenue",
            "collaboration revenue", "research and development service revenue",
        ),
        negative_context=(
            "行业概览", "行業概覽", "监管概览", "監管概覽", "一般药品", "一般藥品",
            "industry overview", "regulatory overview", "pharmaceutical products generally",
        ),
        preferred_sections=("business", "products", "业务", "業務", "核心产品", "核心產品"),
        discouraged_sections=("definitions", "释义", "釋義", "risk factors", "风险因素", "風險因素"),
    ),
    QueryFamily(
        name="core_product_pipeline",
        aliases=(
            "核心产品管线", "核心產品管線", "产品管线", "產品管線", "研发管线",
            "研發管線", "核心产品", "核心產品", "候选药物", "候選藥物",
            "core product pipeline", "product pipeline", "core products", "drug candidates",
            "clinical pipeline", "临床阶段候选药物", "臨床階段候選藥物",
            "研发状态", "研發狀態", "主要产品类别", "主要產品類別",
            "主要产品", "主要產品", "产品类别", "產品類別", "产品组合", "產品組合",
            "principal products", "main products", "product categories", "product portfolio",
        ),
        positive_context=(
            "临床前", "臨床前", "临床一期", "臨床一期", "临床二期", "臨床二期",
            "临床三期", "臨床三期", "适应症", "適應症", "研发进度", "研發進度",
            "preclinical", "phase i", "phase ii", "phase iii", "indication",
            "clinical trial", "development status", "ind application",
            "investigational new drug", "nda application", "new drug application",
            "研发状态", "研發狀態", "ind批准", "ind 批准", "商业权利", "商業權利",
            "生产及销售", "生產及銷售", "制造及销售", "製造及銷售",
            "产品所产生的收益", "產品所產生的收益", "向市场推出", "向市場推出",
            "manufacture and sell", "manufactured and sold", "product revenue",
            "commercial launch", "launched products",
        ),
        negative_context=(
            "释义", "釋義", "行业概览", "行業概覽", "监管概览", "監管概覽",
            "glossary", "industry overview", "regulatory overview",
        ),
        preferred_sections=("business", "products", "pipeline", "业务", "業務", "核心产品", "核心產品"),
        discouraged_sections=("definitions", "释义", "釋義", "industry overview", "行业概览", "行業概覽"),
    ),
)


QUERY_FAMILY_BY_NAME: dict[str, QueryFamily] = {
    family.name: family for family in QUERY_FAMILIES
}
