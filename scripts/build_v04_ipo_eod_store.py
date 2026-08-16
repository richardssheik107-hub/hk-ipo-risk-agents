"""One-time streaming builder for the governed target-IPO EOD filtered store."""
from __future__ import annotations
import argparse,csv,hashlib,json
from pathlib import Path

VERSION="v04_ipo_eod_filter_v1"; COLS=("S_INFO_WINDCODE","TRADE_DT","S_DQ_OPEN","S_DQ_HIGH","S_DQ_LOW","S_DQ_CLOSE","S_DQ_VOLUME","S_DQ_AMOUNT","S_DQ_PRECLOSE","S_DQ_ADJCLOSE")
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--data-root',type=Path,default=Path('data/competition'));p.add_argument('--catalog-dir',type=Path,default=Path('data/catalog'));p.add_argument('--cache-dir',type=Path,default=Path('data/cache'));p.add_argument('--rebuild',action='store_true');a=p.parse_args()
 bridge=a.catalog_dir/'ipo_official_master_bridge.csv';raw=a.data_root/'hkshareeodprices.csv';out=a.cache_dir/'v04_ipo_eod.csv';manifest=a.cache_dir/'v04_ipo_eod.manifest.json'; bh,rh=sha(bridge),sha(raw)
 if manifest.exists() and out.exists() and not a.rebuild:
  old=json.loads(manifest.read_text(encoding='utf-8'))
  if old.get('raw_eod_sha256')==rh and old.get('bridge_sha256')==bh and old.get('filter_schema_version')==VERSION: print('cache_valid=true');return 0
  raise SystemExit('cache conflict; use --rebuild after reviewing source change')
 with bridge.open(encoding='utf-8-sig',newline='') as f: codes={r['stock_code_wind'] for r in csv.DictReader(f) if r.get('official_match_status')=='matched' and r.get('source_year','').isdigit() and 2020 <= int(r['source_year']) <= 2024}
 a.cache_dir.mkdir(parents=True,exist_ok=True);count=0;dates=[];seen=set()
 with raw.open(encoding='gb18030',newline='') as src, out.open('w',encoding='utf-8',newline='') as dst:
  reader=csv.DictReader(src);w=csv.DictWriter(dst,fieldnames=COLS);w.writeheader()
  for r in reader:
   if r.get('S_INFO_WINDCODE') in codes:
    w.writerow({c:r.get(c,'') for c in COLS});count+=1;seen.add(r['S_INFO_WINDCODE']);dates.append(r.get('TRADE_DT',''))
 manifest.write_text(json.dumps({'filter_schema_version':VERSION,'raw_eod_sha256':rh,'bridge_sha256':bh,'row_count':count,'distinct_target_securities':len(seen),'min_trading_date':min(dates) if dates else None,'max_trading_date':max(dates) if dates else None},indent=2)+'\n',encoding='utf-8');print(f'cache_valid=true rows={count}')
if __name__=='__main__': raise SystemExit(main())
