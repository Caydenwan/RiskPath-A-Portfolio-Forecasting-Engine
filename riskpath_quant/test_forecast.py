import numpy as np
from forecast import forecast_paths

def test_forward_dates_and_paid_in():
    a=forecast_paths(np.zeros((12,2)),[.5,.5],100000,500,1,'2026-11-27',cost_bps=0,paths=20)
    assert a['dates'][0]=='2026-11-27' and a['dates'][-1]=='2027-11-27'
    assert a['wealth_quantiles'][1][-1]==106000 and a['paid_in'][-1]==106000
    assert a['nav_quantiles'][1][-1]==1

def test_reproducibility_and_cashflow_separation():
    r=np.random.default_rng(3).normal(.003,.02,(36,2))
    a=forecast_paths(r,[.5,.5],100000,500,5,'2026-11-27',paths=30)
    b=forecast_paths(r,[.5,.5],100000,0,5,'2026-11-27',paths=30)
    assert a['nav_quantiles']==b['nav_quantiles']
    assert a['paid_in'][-1]==130000
    assert a==forecast_paths(r,[.5,.5],100000,500,5,'2026-11-27',paths=30)
