import numpy as np
import pytest
from crisis import crisis_states, apply_crisis, TRANSITION, ASSETS
from forecast import forecast_paths


def test_transitions():
    assert np.all(TRANSITION>=0) and np.allclose(TRANSITION.sum(axis=1),1)
    s=crisis_states('black_swan',3,12,np.random.default_rng(1))
    assert np.all(s[:,0]==3) and np.all(s[:,1:6]==1) and np.all(s[:,6:]==0)
    s=crisis_states('grey_rhino',3,24,np.random.default_rng(1)); assert np.all(s[:,:12]==2) and np.all(s[:,12:]==0)
    s=crisis_states('recession',3,12,np.random.default_rng(1)); assert np.all(s[:,:6]==1) and np.all(s[:,6:]==0)


def test_cash_and_finite_shocks():
    x=np.zeros((4,28)); out=apply_crisis(x,np.arange(4),np.random.default_rng(1))
    assert np.array_equal(out[0],x[0]) and np.array_equal(out[:,0],x[:,0])
    assert np.isfinite(out).all() and (out>-1).all()


@pytest.mark.parametrize('mode',['baseline','mixed','recession','black_swan','grey_rhino'])
def test_paths(mode):
    r=np.zeros((60,28)); w=np.zeros(28); w[ASSETS.index('VTI')]=1
    a=forecast_paths(r,w,100000,500,1,'2026-11-27',cost_bps=0,paths=100,scenario=mode)
    b=forecast_paths(r,w,100000,0,1,'2026-11-27',cost_bps=0,paths=100,scenario=mode)
    assert a['nav_quantiles']==b['nav_quantiles'] and a['paid_in'][-1]==106000
    assert a['dates'][-1]=='2027-11-27' and a==forecast_paths(r,w,100000,500,1,'2026-11-27',cost_bps=0,paths=100,scenario=mode)
    assert 0<=a['drawdown20']<=1 and np.isfinite(a['tail_return99'])
    if mode=='baseline': assert a['wealth_quantiles'][1][-1]==106000 and a['drawdown20']==0
    if mode=='black_swan': assert a['jump_path_share']==1 and a['nav_quantiles'][1][-1]<1
