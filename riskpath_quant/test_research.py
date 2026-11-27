from pathlib import Path
import pandas as pd
import numpy as np
from research import validation, frontier, diagnostics
from public_research import public_allocate
from institutional import simulate
from personal import personal_allocate

def settings(**kw):
    return dict(dict(profile='personal',risk_score=50,years=1,initial=100000,contribution=500,goal=120000,inflation=2.5,as_of='2026-11-27',lookback='auto',cost=15,scenario='baseline',paths=2000),**kw)

def test_public_frontier_and_shared_validation():
    r=pd.read_csv(Path(__file__).resolve().parents[1]/'web/public-tsp-returns.csv',index_col=0,parse_dates=True)
    p=settings(validate_model=True,compare_scenarios=True)
    w,_,_=public_allocate(r,50,1,'auto')
    f=diagnostics(r,p,w,True)
    assert 0<=f['forecast']['goal_probability']<=1 and len(f['scenarios'])==4
    v=f['validation'];assert v['months']==len(r)-60 and v['first']==str(r.index[60].date())
    assert all(len(nav)==len(v['dates']) for nav in v['navs'])
    assert len(f['frontier']['points'])>=2 and f['frontier']['selected_feasible']
    pts=f['frontier']['points']
    assert all(a['vol']<=b['vol'] and a['ret']<b['ret'] for a,b in zip(pts,pts[1:]))
    assert v['excluded']==[120,240]

def test_advanced_short_history_and_no_lookahead():
    r,_=simulate(months=70)
    p=settings()
    v=validation(r,p)
    assert v['windows']==[36] and v['months']==34 and v['excluded']==[60,120,240]
    # Alter only the final realized return; all earlier test NAVs must be identical.
    r2=r.copy();r2.iloc[-1,1]+=.02
    v2=validation(r2,p)
    for a,b in zip(v['navs'],v2['navs']):np.testing.assert_allclose(a[:-1],b[:-1])
    w,_=personal_allocate(r,50,1,'auto')
    ff=frontier(r,p,w)
    assert ff['selected_feasible'] and len(ff['points'])>=2
