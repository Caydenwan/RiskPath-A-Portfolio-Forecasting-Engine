from pathlib import Path
import numpy as np
import pandas as pd
from goal_planner import bound,sample,calculate_goal,SCREEN,CHECK
from public_research import ASSETS
from institutional import simulate

def config(**kw):
    return dict(dict(profile='personal',planner=True,source='public',initial=100000,goal=250000,contribution=500,years=10,inflation=2.5,cost=15,max_drawdown=20,risk_limit=10,confidence=80,scenario='baseline',as_of='2026-11-27',lookback='auto'),**kw)

def test_wilson_bounds_and_costed_affine_execution():
    r=pd.DataFrame(np.zeros((36,5)),columns=ASSETS,index=pd.date_range('2020-01-31',periods=36,freq='ME'))
    w=np.array([[1.,0,0,0,0],[.5,.5,0,0,0]])
    results=sample(r,w,'auto',50,7,.0015,'baseline',True,1)
    a,b,d=results[-1]
    np.testing.assert_allclose(a,.9985)
    np.testing.assert_allclose(b,12*.9985)
    np.testing.assert_allclose(d,.0015)
    assert bound(100,100,False)<1 and bound(0,100,True)>0
    assert bound(800,1000,False)<.8 and bound(100,1000,True)>.1

def check_result(v):
    assert v['mode']=='goal' and v['screen_paths']==SCREEN and v['check_paths']==CHECK
    assert v['candidate_count']>=1 and len(v['grid'])==len(v['amounts'])
    assert v['years'] in v['horizons'] and v['monthly'] in v['amounts']
    for q in [v['current'],v['required_plan'],*v['alternatives'],*[x for row in v['grid'] for x in row]]:
        if q is None:continue
        assert 0<=q['success_lower']<=q['success']+1e-12<=1+1e-12
        assert q['risk']<=q['risk_upper']+1e-12
        assert q['verified']==(q['risk_upper']<=v['risk_limit']+1e-12 and q['success_lower']>=v['confidence']-1e-12)
        assert q['target']>=v['goal']
    if 'weights' in v:
        assert v['current']['risk_ok']
        assert np.isclose(sum(v['weights']),1) and np.isclose(sum(v['assetWeights']),1)
    else:assert v['current'] is None or not v['current']['risk_ok']

def test_public_goal_planner_and_interactive_cell():
    r=pd.read_csv(Path(__file__).resolve().parents[1]/'web/public-tsp-returns.csv',index_col=0,parse_dates=True)
    p=config()
    v=calculate_goal(r,p,True);check_result(v)
    assert v['current']==v['grid'][v['amounts'].index(500)][v['horizons'].index(10)]
    assert v['required_plan'] is not None
    assert v['required_plan']['monthly']%50==0
    q=v['required_plan']; assert q==v['grid'][v['amounts'].index(q['monthly'])][v['horizons'].index(10)]
    assert v['estimation']['common_months']==81

def test_private_universe_and_tighter_risk():
    r,_=simulate(months=70)
    v=calculate_goal(r,config(source='synthetic',years=20,contribution=1000,max_drawdown=5,risk_limit=5),False)
    check_result(v)
    assert v['estimation']['common_months']==70
    assert len(v['assets'])==28
    assert v['max_drawdown']==.05 and v['risk_limit']==.05
