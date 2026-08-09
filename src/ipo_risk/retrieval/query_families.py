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
            "最大供应商", "最大供應商", "主要供应商", "主要供應商",
            "supplier concentration", "top five suppliers", "largest supplier", "major suppliers",
        ),
        positive_context=(
            "向五大供应商采购", "向五大供應商採購", "占总采购额", "佔總採購額",
            "采购额", "採購額", "供应商依赖", "供應商依賴",
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
        ),
        positive_context=(
            "投资协议", "投資協議", "股东协议", "股東協議", "优先股", "優先股",
            "上市时终止", "上市時終止", "恢复效力", "恢復效力", "重组", "重組",
            "investment agreement", "shareholders agreement", "preferred shares",
            "terminate upon listing", "restored", "reorganisation",
        ),
        negative_context=(
            "公司条例", "公司條例", "组织章程细则概要", "組織章程細則概要",
            "一般股东权利", "一般股東權利", "companies ordinance",
            "summary of articles", "general shareholder rights",
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
        ),
        positive_context=(
            "未决诉讼", "未決訴訟", "仲裁", "监管调查", "監管調查", "罚款", "罰款",
            "处罚决定", "處罰決定", "整改", "重大不利影响", "重大不利影響",
            "pending litigation", "arbitration", "regulatory investigation", "fine",
            "penalty decision", "rectification", "material adverse effect",
        ),
        negative_context=(
            "可能受到监管", "可能受到監管", "一般监管规定", "一般監管規定",
            "概不知悉任何", "no material litigation", "may be subject to regulation",
            "general regulatory requirements",
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
        ),
        positive_context=(
            "核心产品", "核心產品", "产品销售收入", "產品銷售收入", "商业销售", "商業銷售",
            "上市批准", "药品批准", "藥品批准", "临床阶段", "臨床階段",
            "core product", "product sales revenue", "commercial sales", "marketing approval",
            "clinical stage", "commercial production", "主要产品类别", "主要產品類別",
            "主要产品", "主要產品", "产品收益", "產品收益", "产品所产生的收益",
            "產品所產生的收益", "向市场推出", "向市場推出", "销售网络", "銷售網絡",
            "principal products", "main products", "product revenue", "sales network",
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
