"""Point-in-time available IPO market-context X, without HSI or market-turnover proxies."""
from __future__ import annotations
import hashlib, json, math
from datetime import date, timedelta
from typing import Any

IPO_MARKET_CONTEXT_FEATURE_SCHEMA_VERSION="v04_ipo_market_context_features_v1"
IPO_MARKET_CONTEXT_FEATURE_POLICY_VERSION="ipo_market_context_policy_v1"
_RAW=("ipo_count_30d","ipo_count_60d","log_prior_ipo_funds_raised_30d","log_prior_ipo_funds_raised_60d","prior_ipo_funds_raised_30d_sample_count","prior_ipo_funds_raised_60d_sample_count","recent_ipo_break_rate","recent_ipo_return_5d","recent_ipo_1d_sample_count","recent_ipo_5d_sample_count","same_industry_ipo_count_180d","same_industry_recent_break_rate","same_industry_recent_return_5d","same_industry_recent_1d_sample_count","same_industry_recent_5d_sample_count")
def _hash(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest()
IPO_MARKET_CONTEXT_FEATURE_MANIFEST={"version":IPO_MARKET_CONTEXT_FEATURE_SCHEMA_VERSION,"policy_version":IPO_MARKET_CONTEXT_FEATURE_POLICY_VERSION,"features":[{"index":i*2,"name":n,"dtype":"float64"} for i,n in enumerate(_RAW)]+[{"index":i*2+1,"name":n+"__missing","dtype":"int8"} for i,n in enumerate(_RAW)]}
IPO_MARKET_CONTEXT_FEATURE_MANIFEST["features"].sort(key=lambda x:x["index"]); IPO_MARKET_CONTEXT_FEATURE_MANIFEST_HASH=_hash(IPO_MARKET_CONTEXT_FEATURE_MANIFEST)

def build_ipo_market_context(*, listing_date:date, industry:str|None, prior_ipos:list[dict[str,Any]]) -> dict[str,float|int|None]:
    prior=sorted((x for x in prior_ipos if x.get("listing_date") and x["listing_date"] < listing_date), key=lambda x:x["listing_date"])
    def window(days): return [x for x in prior if x["listing_date"] >= listing_date-timedelta(days=days)]
    def aggregate(rows, prefix):
        amounts=[x["funds_raised"] for x in rows if x.get("funds_raised") is not None]
        return {f"log_prior_ipo_funds_raised_{prefix}":math.log1p(sum(amounts)) if amounts else None, f"prior_ipo_funds_raised_{prefix}_sample_count":len(amounts)}
    def outcomes(rows):
        one=[x["return_1d"] for x in rows if x.get("target_1d") and x["target_1d"] < listing_date and x.get("return_1d") is not None]
        five=[x["return_5d"] for x in rows if x.get("target_5d") and x["target_5d"] < listing_date and x.get("return_5d") is not None]
        return (sum(v<0 for v in one)/len(one) if one else None, sum(five)/len(five) if five else None, len(one), len(five))
    r30,r60=window(30),window(60); recent=window(60)[-20:]; same=[x for x in window(180) if industry and x.get("industry")==industry]
    br,ret,n1,n5=outcomes(recent); sbr,sret,s1,s5=outcomes(same)
    v={"ipo_count_30d":len(r30),"ipo_count_60d":len(r60),**aggregate(r30,"30d"),**aggregate(r60,"60d"),"recent_ipo_break_rate":br,"recent_ipo_return_5d":ret,"recent_ipo_1d_sample_count":n1,"recent_ipo_5d_sample_count":n5,"same_industry_ipo_count_180d":len(same),"same_industry_recent_break_rate":sbr,"same_industry_recent_return_5d":sret,"same_industry_recent_1d_sample_count":s1,"same_industry_recent_5d_sample_count":s5}
    return v
