"""Research-only IPO Structure X; separate from frozen v04_market_features_v1."""
from __future__ import annotations
import hashlib, json, math
from datetime import date
from typing import Any

IPO_STRUCTURE_FEATURE_SCHEMA_VERSION = "v04_ipo_structure_features_v1"
IPO_STRUCTURE_FEATURE_POLICY_VERSION = "ipo_structure_policy_v1"
_RAW = ("offer_range_width", "offer_price_position", "log_market_cap", "log_funds_raised", "net_proceeds_ratio", "offer_float_ratio", "new_issue_ratio", "price_to_adj_nta", "log_board_lot_value", "lockup_days", "main_board_flag")

def _canon(v: Any) -> str: return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def _hash(v: Any) -> str: return hashlib.sha256(_canon(v).encode()).hexdigest()
IPO_STRUCTURE_FEATURE_MANIFEST = {"version": IPO_STRUCTURE_FEATURE_SCHEMA_VERSION, "policy_version": IPO_STRUCTURE_FEATURE_POLICY_VERSION,
 "features": [{"index": i*2, "name": n, "dtype": "float64", "missing_semantics": "null if unavailable"} if not n.endswith("flag") else {"index": i*2,"name":n,"dtype":"int8","missing_semantics":"null if board unavailable"} for i,n in enumerate(_RAW)] + [{"index":i*2+1,"name":n+"__missing","dtype":"int8","missing_semantics":"1 exactly when raw unavailable"} for i,n in enumerate(_RAW)]}
IPO_STRUCTURE_FEATURE_MANIFEST["features"].sort(key=lambda x:x["index"])
IPO_STRUCTURE_FEATURE_MANIFEST_HASH = _hash(IPO_STRUCTURE_FEATURE_MANIFEST)

def _num(row: dict[str, Any], key: str) -> float | None:
    try:
        value=row.get(key); return float(str(value).replace(",", "")) if value not in (None, "") else None
    except (TypeError, ValueError): return None

def build_ipo_structure_values(row: dict[str, Any]) -> tuple[dict[str, float|int|None], list[str]]:
    low, high, price = _num(row,"LowOfferPrice"), _num(row,"HighOfferPrice"), _num(row,"IPOPrice") or _num(row,"OfferPrice")
    cap, raised, proceeds = _num(row,"MarketCap"), _num(row,"FundsRaised"), _num(row,"NetProceed")
    total, issue, share_cap = _num(row,"TotalShareAmt"), _num(row,"NewIssueAmt"), _num(row,"IssueCap")
    nta, lot = _num(row,"AdjNTA"), _num(row,"BoardLot")
    listing, lockup = row.get("ListedDate"), row.get("LockUpEndDate")
    try:
        listing_date = listing if isinstance(listing, date) else date.fromisoformat(str(listing)[:10])
        lockup_date = lockup if isinstance(lockup, date) else date.fromisoformat(str(lockup)[:10])
        lockup_days = (lockup_date - listing_date).days
    except (TypeError, ValueError): lockup_days = None
    values={"offer_range_width":(high-low)/low if low and low>0 and high is not None and high>=low else None,
      "offer_price_position":(price-low)/(high-low) if price is not None and low is not None and high is not None and high>low else None,
      "log_market_cap":math.log1p(cap) if cap is not None and cap>=0 else None,
      "log_funds_raised":math.log1p(raised) if raised is not None and raised>=0 else None,
      "net_proceeds_ratio":proceeds/raised if proceeds is not None and raised is not None and raised>0 else None,
      "offer_float_ratio":total/share_cap if total is not None and share_cap is not None and share_cap>0 else None,
      "new_issue_ratio":issue/total if issue is not None and total is not None and total>0 else None,
      "price_to_adj_nta":price/nta if price is not None and nta is not None and nta>0 else None,
      "log_board_lot_value":math.log1p(price*lot) if price is not None and lot is not None and lot>=0 else None,
      "lockup_days":lockup_days if lockup_days is not None and lockup_days >= 0 else None, "main_board_flag":1 if row.get("ListingBoardID")=="P3401" else 0 if row.get("ListingBoardID") else None}
    diagnostics=[]
    if high is not None and low is not None and price is not None and (price < low or price > high): diagnostics.append("offer_price_outside_range")
    if lockup_days is not None and lockup_days < 0: diagnostics.append("lockup_before_listing")
    return values, diagnostics
