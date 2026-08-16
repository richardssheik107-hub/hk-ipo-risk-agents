"""Train deterministic Oracle Logistic Regression from generic materialised datasets."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from ipo_risk.modeling.oracle_baseline import train_oracle_logistic_regression

def _read(path: Path):
    data=json.loads(path.read_text(encoding='utf-8'))
    return tuple(data['feature_names']), [r['feature_values'] for r in data['records']], [r['target'] for r in data['records']]

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--development',type=Path,required=True); p.add_argument('--validation',type=Path,required=True); p.add_argument('--output-dir',type=Path,required=True); p.add_argument('--group',choices=('document_only','market_only','combined'),action='append'); a=p.parse_args()
    names,x,y=_read(a.development); validation_names,vx,vy=_read(a.validation)
    if names != validation_names: raise ValueError('development/validation feature manifest mismatch')
    a.output_dir.mkdir(parents=True,exist_ok=True); results=[]
    for group in a.group or ('document_only','market_only','combined'):
        result=train_oracle_logistic_regression(development_x=x,development_y=y,validation_x=vx,validation_y=vy,feature_names=names,group=group)
        results.append({'feature_group':result.feature_group,'feature_names':result.feature_names,'metrics':result.metrics})
    (a.output_dir/'metrics.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'groups={len(results)} output={a.output_dir}')
    return 0
if __name__=='__main__': raise SystemExit(main())
