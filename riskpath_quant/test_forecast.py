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
    assert a['wealth_quantiles'][1][-1]>b['wealth_quantiles'][1][-1]
    # Contributions can change drift weights, so investment TWR need not match the no-flow portfolio.
    assert a['paid_in'][-1]==130000
    assert a==forecast_paths(r,[.5,.5],100000,500,5,'2026-11-27',paths=30)

def test_deposit_cost_and_goal():
    a=forecast_paths(np.zeros((36,2)),[.5,.5],100000,500,1,'2026-11-27',cost_bps=15,paths=20,windows=[36],window_weights=[1.],goal=100000,inflation=.02)
    # Initial entry fee and fee on each monthly purchase. Quarterly rebalance has zero turnover.
    assert np.isclose(a['wealth_quantiles'][1][-1],100000*.9985+12*500*.9985)
    assert np.isclose(a['nav_quantiles'][1][-1],.9985)
    assert a['goal_probability']==1 and np.isclose(a['nominal_goal'],102000)
    assert np.isclose(a['real_median'],a['wealth_quantiles'][1][-1]/1.02)

def test_contribution_allocation_and_nav():
    # Constant +10% / 0% monthly returns: deposits buy the 50/50 target and dilute drift.
    r=np.tile([.10,0.],(36,1))
    a=forecast_paths(r,[.5,.5],100,50,1,'2026-11-27',cost_bps=0,paths=5)
    assert np.isclose(a['wealth_quantiles'][1][1],155.)
    assert np.isclose(a['wealth_quantiles'][1][2],213.)
    assert np.isclose(a['nav_quantiles'][1][2],1.05*(1+8/155))
