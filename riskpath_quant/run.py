"""Run a deterministic benchmark or supply a CSV of monthly decimal returns."""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from engine import ASSETS,synthetic,walk_forward,metrics,weights,bootstrap


def main():
    p=argparse.ArgumentParser(); p.add_argument('--returns-csv'); p.add_argument('--out',default='outputs'); a=p.parse_args()
    r=pd.read_csv(a.returns_csv,index_col=0,parse_dates=True) if a.returns_csv else synthetic()
    if list(r.columns)!=ASSETS: raise ValueError('CSV must use the documented asset columns in order')
    if not r.index.to_period('M').is_unique or not np.all(np.diff(r.index.to_period('M').asi8)==1): raise ValueError('Require consecutive monthly observations')
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
    summary={}; net={}; allocations={}
    for name in ['equal','60_40','minvar','risk_parity','cvar']:
        bt,w=walk_forward(r,name); net[name]=bt.net; allocations[name]=w
        summary[name]=metrics(bt.net.to_numpy(),bt.turnover.to_numpy(),r.BIL.loc[bt.index].to_numpy())
    pd.DataFrame(net).to_csv(out/'monthly_net_returns.csv'); pd.DataFrame(summary).T.to_csv(out/'metrics.csv')
    pd.concat(allocations,names=['method','date']).to_csv(out/'weights.csv')
    # Separate prospective illustration, fitted to last 60 months, no claim of prediction.
    hist=r.iloc[-60:]; w=weights(hist,'risk_parity')
    sim=bootstrap(hist,w,contribution=500)
    forecast={'terminal_nav_quantiles':np.percentile(sim['nav'][:,-1],[5,50,95]).tolist(), 'terminal_wealth_quantiles':np.percentile(sim['terminal_wealth'],[5,50,95]).tolist()}
    report={'data':'user-supplied monthly returns; provenance not verified' if a.returns_csv else 'synthetic asset proxies, not historical ETF performance','months_oos':len(r)-60,'metrics':summary,'simulation':forecast}
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report,indent=2))

if __name__=='__main__': main()
