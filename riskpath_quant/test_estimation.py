import numpy as np
import pytest
from estimation import window_plan,moments,estimate_meta
from institutional import simulate,allocate,walk,feasible,spec
from personal import personal_allocate

def test_windows():
    assert window_plan(70)[0]==[36,60,70]
    assert window_plan(240)[0]==[36,60,120,240]
    assert window_plan(60)[0]==[36,60]
    with pytest.raises(ValueError): window_plan(70,'120')
    with pytest.raises(ValueError): window_plan(35)

def test_cov():
    r,_=simulate(); m,s=moments(r.to_numpy())
    assert m.shape==(28,) and np.linalg.eigvalsh(s).min()>0
    assert sum(estimate_meta(70)['weights'])==pytest.approx(1)

def test_models():
    r,l=simulate(); r=r.iloc[-70:]; l=l.loc[r.index]; p,_,cap=spec('pension')
    for method in ['minvar','utility','risk_budget','cvar','surplus']:
        assert feasible(allocate(r,'pension',method,l,estimation='auto'),p,cap)
    w,_=personal_allocate(r,50,5,estimation='auto'); assert sum(w)==pytest.approx(1)

def test_no_future():
    r,l=simulate(); r=r.iloc[:55].copy(); b,w=walk(r,'pension','minvar',lookback=36,estimation='auto'); r.iloc[40:]*=1.1
    b2,w2=walk(r,'pension','minvar',lookback=36,estimation='auto'); assert np.allclose(w.iloc[:5],w2.iloc[:5])
