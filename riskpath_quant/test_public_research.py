from pathlib import Path
import pandas as pd
import numpy as np
from public_research import calculate_public, public_allocate, ASSETS
def test_public_snapshot_and_allocation():
    r=pd.read_csv(Path(__file__).resolve().parents[1]/'web/public-tsp-returns.csv',index_col=0,parse_dates=True)
    assert list(r.columns)==ASSETS and len(r)==81
    assert np.all(np.diff(r.index.to_period('M').asi8)==1)
    w,p,risk=public_allocate(r,50,5)
    assert abs(w.sum()-1)<1e-8 and w.min()>=0 and w[2:].sum()<=.800001
    p=dict(profile='personal',mode='forecast',lookback='auto',risk_score=50,years=1,initial=100000,contribution=500,as_of='2026-11-27',cost=15,scenario='mixed')
    result=calculate_public(r,p)
    assert result['source']=='public' and result['forecast']['years']==1 and result['estimation']['common_months']==81
    assert len(result['assets'])==5 and np.isfinite(result['forecast']['wealth_quantiles']).all()
