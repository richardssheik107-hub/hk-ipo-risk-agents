"""Train deterministic baselines over PR-D canonical model matrices.

Consumes matrices already projected by ``project_model_matrix`` (one per
M / P / O / PM / OM group), so this CLI performs no column selection of its own.

  --protocol holdout                        fit on development, evaluate on validation
  --protocol development_only_time_aware_cv forward-chaining folds inside development

The CV protocol exists because the Oracle arms have no validation coverage; its
numbers are not comparable to holdout numbers and are labelled as such in the output.
See docs/V04_ORACLE_GOLD_COVERAGE_AUDIT.md section 4.
"""
from __future__ import annotations
import argparse, json
from dataclasses import asdict
from pathlib import Path
from ipo_risk.schemas.canonical_modeling import V04CanonicalModelMatrix
from ipo_risk.modeling.oracle_baseline import (
    CV_PROTOCOL, HOLDOUT_PROTOCOL, IncomparableMatrixError, InsufficientCohortError,
    InsufficientValidationSplitError, train_holdout, train_time_aware_cv,
)

def _matrix(path: Path) -> V04CanonicalModelMatrix:
    return V04CanonicalModelMatrix.model_validate(json.loads(path.read_text(encoding='utf-8')))

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--development',type=Path,required=True,action='append',help='canonical model matrix JSON; repeat per arm')
    p.add_argument('--validation',type=Path,action='append')
    p.add_argument('--cohort-years',type=Path,help='JSON mapping case_id -> cohort_year; required for the CV protocol')
    p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--protocol',choices=(HOLDOUT_PROTOCOL,CV_PROTOCOL),default=HOLDOUT_PROTOCOL)
    a=p.parse_args()
    development=[_matrix(path) for path in a.development]
    if a.protocol==HOLDOUT_PROTOCOL:
        if not a.validation or len(a.validation)!=len(a.development):
            p.error('the holdout protocol needs one --validation matrix per --development matrix')
        validation=[_matrix(path) for path in a.validation]
    else:
        if not a.cohort_years: p.error('the time-aware CV protocol needs --cohort-years')
        cohort_years={str(k):int(v) for k,v in json.loads(a.cohort_years.read_text(encoding='utf-8')).items()}
    a.output_dir.mkdir(parents=True,exist_ok=True); results=[]
    for index,matrix in enumerate(development):
        arm=matrix.feature_group.value
        try:
            if a.protocol==HOLDOUT_PROTOCOL:
                r=train_holdout(development=matrix,validation=validation[index])
                results.append({'arm':r.arm,'protocol':r.protocol,'cohort':r.cohort,'metrics':r.metrics})
            else:
                r=train_time_aware_cv(development=matrix,cohort_years=cohort_years)
                results.append({'arm':r.arm,'protocol':r.protocol,'cohort':r.cohort,
                                'folds':[asdict(f) for f in r.folds],'metrics':r.pooled_metrics,
                                'minimum_detectable_auc_difference':r.minimum_detectable_auc_difference,
                                'comparability_warning':r.comparability_warning})
        except (InsufficientValidationSplitError, InsufficientCohortError, IncomparableMatrixError) as exc:
            # An arm the data cannot support is reported explicitly, never silently skipped.
            results.append({'arm':arm,'protocol':a.protocol,'metrics':None,'not_evaluable':f'{type(exc).__name__}: {exc}'})
    (a.output_dir/'metrics.json').write_text(json.dumps({'protocol':a.protocol,'arms':results},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"protocol={a.protocol} arms={len(results)} evaluated={sum(r['metrics'] is not None for r in results)} output={a.output_dir}")
    return 0
if __name__=='__main__': raise SystemExit(main())
