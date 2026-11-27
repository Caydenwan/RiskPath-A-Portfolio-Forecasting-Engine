import numpy as np
import pytest
from engine import *

@pytest.mark.parametrize('method',['equal','60_40','minvar','risk_parity','cvar'])
def test_weights(method):
    w=weights(synthetic().iloc[:60],method)
    assert w.sum()==pytest.approx(1) and min(w)>=-1e-10

@pytest.mark.parametrize('method',['minvar','risk_parity','cvar'])
def test_no_lookahead(method):
    r=synthetic(); a,w=walk_forward(r,method); r.iloc[60:]=r.iloc[60:]*.5
    b,v=walk_forward(r,method)
    assert np.allclose(w.iloc[0],v.iloc[0])
    assert not np.isclose(a.net.iloc[0],b.net.iloc[0])

def test_initial_cost_and_drift():
    r=synthetic(); b,w=walk_forward(r,'equal',cost_bps=10)
    assert b.turnover.iloc[0]==pytest.approx(1)
    assert b.turnover.iloc[1]==0
    assert 1+b.net.iloc[0]==pytest.approx(.999*(1+b.gross.iloc[0]))
    expected=w.iloc[0]*(1+r.iloc[60])/(1+b.gross.iloc[0])
    assert np.allclose(w.iloc[1],expected)

def test_bootstrap_reproducible_and_cashflow():
    r=synthetic().iloc[:60]; w=weights(r,'equal')
    a=bootstrap(r,w,months=12,paths=20); b=bootstrap(r,w,months=12,paths=20,contribution=500)
    assert np.array_equal(a['nav'],b['nav'])
    assert np.allclose(a['terminal_wealth'],100000*a['nav'][:,-1])
    assert np.all(b['terminal_wealth']>a['terminal_wealth'])

def test_drawdown_includes_initial_nav():
    m=metrics(np.array([-.1,.01]),np.zeros(2),np.zeros(2))
    assert m['max_drawdown']==pytest.approx(-.1)

def test_invalid():
    r=synthetic(); r.iloc[0,0]=-1
    with pytest.raises(ValueError): weights(r,'equal')

def test_minvar_objective():
    r=synthetic().iloc[:60]; s=np.cov(r,rowvar=False); s=.75*s+.25*np.diag(np.diag(s))+np.eye(len(s))*1e-8
    w=weights(r,'minvar'); e=weights(r,'equal'); assert w@s@w <= e@s@e+1e-12

def test_cvar_objective():
    r=synthetic().iloc[:60]; loss=lambda w: -np.sort(r.to_numpy()@w)[:3].mean()
    assert loss(weights(r,'cvar')) <= loss(weights(r,'equal'))+1e-9
