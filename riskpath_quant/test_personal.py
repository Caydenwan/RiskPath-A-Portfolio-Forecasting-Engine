import numpy as np
import pytest
from institutional import simulate, G
from personal import personal_allocate, preference, SLEEVE_CAPS, ASSET_CAPS

@pytest.mark.parametrize('score',[0,25,50,75,100])
def test_feasible(score):
    r,_=simulate(); w,p=personal_allocate(r.iloc[-60:],score,10)
    assert w.sum()==pytest.approx(1) and min(w)>=0
    assert np.all(w<=ASSET_CAPS+1e-7) and np.all(G@w<=SLEEVE_CAPS+1e-7)


def test_ordered_risk():
    r,_=simulate(); v=[personal_allocate(r.iloc[-60:],s,10)[1]['estimated_volatility'] for s in range(0,101,10)]
    assert np.min(np.diff(v))>=-1e-7
    assert v[-1]>v[0]+.001


def test_horizon_limit():
    r,_=simulate(); a,p=personal_allocate(r.iloc[-60:],100,1); b,q=personal_allocate(r.iloc[-60:],30,10)
    assert p['effective_score']==30 and np.allclose(a,b)
    assert preference(0,10)[1]>preference(100,10)[1]


def test_invalid():
    with pytest.raises(ValueError): preference(101,10)
