"""Optional public ETF data ingestion; no fabricated pre-inception returns."""
import argparse, json
from pathlib import Path
import pandas as pd
from institutional import ASSETS


def monthly_returns(prices, end):
    p=prices.reindex(columns=ASSETS).sort_index()
    cutoff=pd.Timestamp(end).to_period('M').to_timestamp()
    if p.index.tz is not None: p.index=p.index.tz_localize(None)
    p=p.loc[p.index<cutoff]
    # Require an observation for every asset on the final observed trading date of each month.
    p=p.groupby(p.index.to_period('M')).tail(1)
    p.index=p.index.to_period('M').to_timestamp('M')
    p=p.asfreq(pd.offsets.MonthEnd())
    p=p.where(p>0)
    r=p.pct_change(fill_method=None)
    complete=r.notna().all(axis=1)
    if not complete.any(): raise ValueError('No common complete return history')
    r=r.loc[complete.idxmax():]
    if r.isna().any().any(): raise ValueError('Missing data after common start; investigate, do not fill')
    return r


def main():
    import yfinance as yf
    p=argparse.ArgumentParser(); p.add_argument('--start',default='2005-01-01'); p.add_argument('--end',default=str(pd.Timestamp.now(tz='UTC').date())); p.add_argument('--out',default='monthly_returns.csv'); a=p.parse_args()
    end=str(pd.Timestamp(a.end).to_period('M').to_timestamp().date())
    raw=yf.download(ASSETS,start=a.start,end=end,auto_adjust=True,progress=False)['Close']
    r=monthly_returns(raw,end); out=Path(a.out); r.to_csv(out)
    out.with_suffix('.metadata.json').write_text(json.dumps({'provider':'Yahoo Finance via yfinance; third-party adjusted close, verify and check terms before use','retrieved_utc':pd.Timestamp.now(tz='UTC').isoformat(),'start_requested':a.start,'end_exclusive':end,'first_return':str(r.index[0].date()),'last_return':str(r.index[-1].date()),'observations':len(r),'assets':ASSETS,'method':'monthly adjusted-close simple return; common post-inception dates, no forward fill, incomplete month excluded'},indent=2)+'\n')
    print(f'{len(r)} common monthly observations; 60-month lookback leaves {max(0,len(r)-60)} test months. Short history limits inference.')

if __name__=='__main__': main()
