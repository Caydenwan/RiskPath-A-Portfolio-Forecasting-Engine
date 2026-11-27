"""Independent five-fund research model, using government-published TSP net returns."""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from estimation import moments, estimate_meta
from personal import preference
from engine import validate
from forecast import forecast_paths
from crisis import LOG_SHIFT, LOAD

ASSETS=['TSP_G','TSP_F','TSP_C','TSP_S','TSP_I']
# G = special Treasury securities, F = broad US bonds, C/S/I = equity funds.
GROUPS=['cash','rates','equity']
G=np.array([[1,0,0,0,0],[0,1,0,0,0],[0,0,1,1,1]],dtype=float)
CAPS=np.array([1.,.85,.55,.35,.45])
SHOCK_GROUP=np.array([0,2,1,1,1])

def public_shock(x,state,rng):
    out=x.copy(); active=state>0
    if not active.any(): return out
    s=state[active]
    shift=LOG_SHIFT[s][:,SHOCK_GROUP]; load=LOAD[s][:,SHOCK_GROUP]
    common=rng.standard_t(5,size=len(s))*np.sqrt(3/5)
    out[active]=np.expm1(np.clip(np.log1p(x[active])+shift+load*common[:,None],-8,3))
    return out

def public_allocate(r,score,years,selection='auto'):
    validate(r)
    if list(r.columns)!=ASSETS: raise ValueError('Invalid TSP fund columns')
    eff,lam=preference(score,years)
    mu,s=moments(r.to_numpy(),selection)
    # Shrink equity means toward the equally weighted equity group mean.
    mu[2:]=.25*mu[2:]+.75*mu[2:].mean()
    def fun(w): return 100*(.5*lam*(w@s@w)-mu@w)
    def jac(w): return 100*(lam*(s@w)-mu)
    sol=minimize(fun,np.array([1.,0,0,0,0]),jac=jac,method='SLSQP',
      bounds=list(zip(np.zeros(5),CAPS)),constraints=[
        {'type':'eq','fun':lambda w:w.sum()-1,'jac':lambda w:np.ones(5)},
        {'type':'ineq','fun':lambda w:.8-w[2:].sum(),'jac':lambda w:np.array([0,0,-1,-1,-1])}],
      options={'ftol':1e-11,'maxiter':1000})
    if not sol.success or abs(sol.x.sum()-1)>1e-7 or min(sol.x)<-1e-8 or np.any(sol.x>CAPS+1e-7) or sol.x[2:].sum()>.8000001: raise RuntimeError('Public optimizer failed: '+str(sol.message))
    w=np.maximum(sol.x,0); w/=w.sum()
    risk=w*(s@w)/(w@s@w)
    pref={'score':float(score),'effective_score':eff,'lambda':lam,'horizon_cap':{1:30,3:50,5:70,10:100,15:100,20:100,30:100}[years],'estimated_volatility':float(np.sqrt(w@s@w)),'estimated_return':float(w@mu)}
    return w,pref,G@risk

def calculate_public(r,p):
    if p['profile']!='personal' or p['mode']!='forecast': raise ValueError('Public research supports Personal forecasting. Select Advanced ETF data for institutional backtests.')
    if np.any(np.diff(r.index.to_period('M').asi8)!=1) or r.index[-1].to_period('M')>=pd.Timestamp(p['as_of']).to_period('M'): raise ValueError('Require consecutive completed monthly TSP observations')
    selection=p.get('lookback','auto'); meta=estimate_meta(len(r),selection)
    meta.update(first=str(r.index[0].date()),last=str(r.index[-1].date()),training_first=str(r.index[-meta['longest']].date()),provider='USPS Postal Bulletin · TSP five-fund published returns')
    w,pref,risk=public_allocate(r,float(p['risk_score']),int(p['years']),selection)
    from research import diagnostics
    research=diagnostics(r,p,w,public=True)
    stress_scenarios={'equity_crash':[0,.06,-.30],'inflation_rates':[0,-.12,-.15],'credit_crunch':[0,.04,-.18],'liquidity_shock':[0,-.04,-.22]}
    sw=G@w
    return dict(mode='forecast',source='public',**research,sleeves=GROUPS,weights=sw.tolist(),risk=risk.tolist(),stress={k:float(sw@v) for k,v in stress_scenarios.items()},assets=ASSETS,assetWeights=w.tolist(),preference=pref,estimation=meta)
