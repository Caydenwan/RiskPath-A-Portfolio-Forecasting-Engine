import numpy as np
import pandas as pd
import pytest
from institutional import *
from download_returns import monthly_returns

@pytest.mark.parametrize('mandate',list(POLICY))
@pytest.mark.parametrize('method',['policy','minvar','utility','risk_budget','cvar'])
def test_policy_constraints(mandate,method):
    r,l=simulate(months=60); p,ref,cap=spec(mandate)
    assert feasible(allocate(r,mandate,method),p,cap)

def test_surplus():
    r,l=simulate(months=60); p,_,cap=spec('pension')
    w=allocate(r,'pension','surplus',l)
    assert feasible(w,p,cap)
    s=covariance(np.c_[r,l]); f=lambda w:w@s[:-1,:-1]@w-2*w@s[:-1,-1]
    assert f(w)<=f(allocate(r,'pension','policy'))+1e-8

def test_no_lookahead():
    r,l=simulate(months=64); b,w=walk(r,'pension','surplus',l)
    r.iloc[60:]*=.5; l.iloc[60:]*=.5; c,v=walk(r,'pension','surplus',l)
    assert np.allclose(w.iloc[0],v.iloc[0]) and b.net.iloc[0]!=c.net.iloc[0]

def test_risk_and_stress():
    r,_=simulate(months=60); w=allocate(r,'liquid_multi','risk_budget'); s=covariance(r)
    assert np.linalg.eigvalsh(s).min()>0 and risk_contributions(w,s).sum()==pytest.approx(1)
    assert len(stress(w))==4

def test_funding():
    a=pd.Series([.1,-.02]); l=pd.Series([.05,.01]); f=funding(a,l)
    assert f.iloc[-1]==pytest.approx(.9*1.1*.98/(1.05*1.01))

def test_monthly_ingestion():
    p=pd.DataFrame(100.,index=pd.date_range('2023-01-31',periods=5,freq=pd.offsets.MonthEnd()),columns=ASSETS)
    p.iloc[0,-1]=np.nan; p.iloc[2]*=1.1
    r=monthly_returns(p,'2023-05-15'); assert len(r)==2 and r.iloc[0,0]==pytest.approx(.1)
    p.iloc[3,0]=np.nan
    with pytest.raises(ValueError): monthly_returns(p,'2023-05-15')
