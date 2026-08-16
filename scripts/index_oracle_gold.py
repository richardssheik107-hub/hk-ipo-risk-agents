"""Index effective Oracle Gold eligibility without invoking the production pipeline."""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path
from ipo_risk.modeling.oracle_document import load_risk_gold

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--root',type=Path,default=Path('.')); p.add_argument('--output-dir',type=Path,default=Path('reports/oracle_gold_index')); a=p.parse_args()
    rows=[]; failures=[]
    for f in sorted((a.root/'expert_results').glob('*/pass1/expert_annotation_v1.json')):
        case_id=f.parents[1].name
        try:
            v=load_risk_gold(a.root,case_id)
            rows.append({'case_id':case_id,'source_kind':v.source_kind,'audit_status':v.audit_status,'base_pass_hash':v.base_pass_hash,'audit_hash':v.audit_hash or '', 'audit_source_pass_hash':v.audit_source_pass_hash or '', 'audit_applied_risks':','.join(v.audit_applied_risks),'effective_annotation_hash':v.effective_annotation_hash})
        except Exception as e: failures.append({'case_id':case_id,'error':f'{type(e).__name__}: {e}'})
    a.output_dir.mkdir(parents=True,exist_ok=True)
    (a.output_dir/'oracle_gold_inventory.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (a.output_dir/'oracle_gold_inventory.csv').open('w',encoding='utf-8',newline='') as h:
        w=csv.DictWriter(h,fieldnames=list(rows[0]) if rows else ['case_id']); w.writeheader(); w.writerows(rows)
    with (a.output_dir/'failure_report.csv').open('w',encoding='utf-8',newline='') as h:
        w=csv.DictWriter(h,fieldnames=['case_id','error']); w.writeheader(); w.writerows(failures)
    print(f'indexed={len(rows)} failed={len(failures)} output={a.output_dir}')
    return 1 if failures else 0
if __name__=='__main__': raise SystemExit(main())
