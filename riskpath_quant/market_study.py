"""Run a real-market-only study. No synthetic fallback; no raw data publication."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import pandas as pd
import numpy as np
from engine import metrics, validate
from institutional import ASSETS, POLICY, METHODS, walk


def evaluate(r, lookbacks=(36,60,120,240), min_oos=12):
    validate(r)
    if list(r.columns)!=ASSETS or np.any(np.diff(r.index.to_period('M').asi8)!=1):
        raise ValueError('Expected complete consecutive monthly returns for the 28-asset universe')
    if min_oos<2 or any(x<12 for x in lookbacks):
        raise ValueError('Invalid study windows')
    rows=[]; coverage=[]
    for lb in lookbacks:
        n=len(r)-lb
        if n<min_oos:
            coverage.append({'lookback':lb,'status':'insufficient_history','oos_months':max(n,0)})
            continue
        coverage.append({'lookback':lb,'status':'evaluated','oos_months':n,'first_test':str(r.index[lb].date()),'last_test':str(r.index[-1].date())})
        for mandate in POLICY:
            for method in METHODS:
                b,w=walk(r,mandate,method,lookback=lb,estimation=str(lb))
                rows.append({'lookback':lb,'mandate':mandate,'method':method,'oos_months':n,
                    **metrics(b.net.to_numpy(),b.turnover.to_numpy(),r.BIL.loc[b.index].to_numpy()),
                    'avg_cash':float(w.BIL.mean())})
    # Adaptive estimation starts with 36 observations; later windows grow using only prior data.
    n=len(r)-36
    if n>=min_oos:
        coverage.append({'lookback':'auto','status':'evaluated','oos_months':n,'first_test':str(r.index[36].date()),'last_test':str(r.index[-1].date())})
        for mandate in POLICY:
            for method in METHODS:
                b,w=walk(r,mandate,method,lookback=36,estimation='auto')
                rows.append({'lookback':'auto','mandate':mandate,'method':method,'oos_months':n,
                    **metrics(b.net.to_numpy(),b.turnover.to_numpy(),r.BIL.loc[b.index].to_numpy()),
                    'avg_cash':float(w.BIL.mean())})
    else:
        coverage.append({'lookback':'auto','status':'insufficient_history','oos_months':max(n,0)})
    if not rows:
        raise ValueError('No eligible estimation window: '+json.dumps(coverage))
    return pd.DataFrame(rows),coverage


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--start',default='2005-01-01')
    p.add_argument('--end',default=str(pd.Timestamp.now(tz='UTC').date()))
    p.add_argument('--out',default='market_study_local')
    p.add_argument('--min-oos',type=int,default=12)
    a=p.parse_args()
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    status=out/'status.json'
    # Remove stale summary files before attempting a fresh run.
    for name in ['metrics.csv','provenance.json']:
        (out/name).unlink(missing_ok=True)
    status.write_text(json.dumps({'status':'running'}))
    try:
        raw=out/'monthly_returns.csv'
        raw.unlink(missing_ok=True)
        raw.with_suffix('.metadata.json').unlink(missing_ok=True)
        subprocess.run([sys.executable,str(Path(__file__).with_name('download_returns.py')),
                        '--start',a.start,'--end',a.end,'--out',str(raw)],check=True)
        r=pd.read_csv(raw,index_col=0,parse_dates=True)
        m,coverage=evaluate(r,min_oos=a.min_oos)
        provenance=json.loads(raw.with_suffix('.metadata.json').read_text())
        provenance.update({'input_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),
                           'lookback_coverage':coverage,'min_oos_months':a.min_oos,
                           'rebalance_months':3,'cost_bps':15,
                           'packages':{x:importlib.metadata.version(x) for x in ['numpy','pandas','scipy','yfinance']},
                           'limitations':['Current-universe selection bias','Adjusted prices may be revised','Short common history for newer ETFs','No actuarial liability series; surplus model excluded']})
        m.to_csv(out/'metrics.csv',index=False)
        (out/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
        status.write_text(json.dumps({'status':'success','coverage':coverage},indent=2))
        print(m.round(4).to_string(index=False))
        print(json.dumps(coverage,indent=2))
    except Exception as exc:
        status.write_text(json.dumps({'status':'failed','reason':str(exc)},indent=2))
        raise


if __name__=='__main__': main()
