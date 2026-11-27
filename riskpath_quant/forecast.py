"""Conditional block-bootstrap forecasts with optional illustrative crisis overlays."""
import numpy as np
import pandas as pd
from crisis import SCENARIOS, crisis_states, apply_crisis


def forecast_paths(r, w, initial, contribution, years, as_of, cost_bps=15, paths=2000, seed=42, block=6, scenario='baseline', crisis_overlay=None, windows=None, window_weights=None, goal=None, inflation=0.):
    x=np.asarray(r,dtype=float); w=np.asarray(w,dtype=float)
    if x.ndim!=2 or len(x)<block or not np.isfinite(x).all() or (x<=-1).any():
        raise ValueError('Invalid training returns')
    if w.shape!=(x.shape[1],) or not np.isfinite(w).all() or (w<-1e-8).any() or not np.isclose(w.sum(),1):
        raise ValueError('Invalid target weights')
    if not np.isfinite([initial,contribution,cost_bps]).all() or initial<=0 or contribution<0 or not 0<=cost_bps<=50 or years not in (1,3,5,10,15,20,30) or scenario not in SCENARIOS or paths<1:
        raise ValueError('Invalid forecast settings')
    w=np.maximum(w,0); w/=w.sum(); months=years*12
    if not np.isfinite(inflation) or not 0<=inflation<=.20 or (goal is not None and (not np.isfinite(goal) or goal<=0)): raise ValueError('Invalid goal or inflation')
    rng=np.random.default_rng(seed)
    shape=(paths,int(np.ceil(months/block)))
    if windows is None:
        starts=rng.integers(len(x),size=shape)
    else:
        windows=np.asarray(windows,dtype=int); probs=np.asarray(window_weights,dtype=float)
        if windows.ndim!=1 or len(windows)!=len(probs) or np.any(windows<block) or np.any(windows>len(x)) or not np.isfinite(probs).all() or np.any(probs<0) or not np.isclose(probs.sum(),1): raise ValueError('Invalid forecast window mixture')
        chosen=rng.choice(windows,size=shape,p=probs)
        # Choose contiguous blocks within each selected trailing window, without wrapping the history.
        starts=len(x)-chosen+(rng.random(shape)*(chosen-block+1)).astype(int)
    ids=(starts[:,:,None]+np.arange(block)).reshape(paths,-1)[:,:months]%len(x)
    shock_rng=np.random.default_rng(seed+1)
    states=crisis_states(scenario,paths,months,shock_rng)
    weights=np.tile(w,(paths,1)); nav=np.ones(paths); wealth=np.full(paths,float(initial))
    peak=np.ones(paths); max_dd=np.zeros(paths); underwater=np.zeros(paths,dtype=int); longest=np.zeros(paths,dtype=int)
    wealth_q=[np.percentile(wealth,[5,50,95]).tolist()]; nav_q=[[1.,1.,1.]]
    for t in range(months):
        if t==0: turnover=np.ones(paths)
        elif t%3==0:
            turnover=np.abs(weights-w).sum(axis=1); weights[:]=w
        else: turnover=np.zeros(paths)
        realized=x[ids[:,t]]
        if scenario!='baseline': realized=(crisis_overlay or apply_crisis)(realized,states[:,t],shock_rng)
        gross=np.sum(weights*realized,axis=1)
        multiplier=(1-turnover*cost_bps/10000)*(1+gross)
        nav*=multiplier
        # Rebalance fees reduce existing capital; monthly deposits buy target weights and incur their own fee.
        grown=wealth*multiplier
        weights*=1+realized; weights/=(1+gross)[:,None]
        net_deposit=contribution*(1-cost_bps/10000)
        wealth=grown+net_deposit
        weights=(grown[:,None]*weights+net_deposit*w)/wealth[:,None]
        peak=np.maximum(peak,nav); dd=1-nav/peak; max_dd=np.maximum(max_dd,dd)
        underwater=np.where(dd>1e-10,underwater+1,0); longest=np.maximum(longest,underwater)
        wealth_q.append(np.percentile(wealth,[5,50,95]).tolist())
        nav_q.append(np.percentile(nav,[5,50,95]).tolist())
    start=pd.Timestamp(as_of).normalize()
    dates=[str((start+pd.DateOffset(months=i)).date()) for i in range(months+1)]
    worst=np.sort(nav-1)[:max(1,int(np.ceil(.01*paths)))]
    nominal_goal=None if goal is None else goal*(1+inflation)**years
    goal_probability=None if goal is None else float(np.mean(wealth>=nominal_goal))
    real_median=float(np.median(wealth)/(1+inflation)**years)
    return dict(dates=dates,wealth_quantiles=np.asarray(wealth_q).T.tolist(),nav_quantiles=np.asarray(nav_q).T.tolist(),
                paid_in=(initial+contribution*np.arange(months+1)).tolist(),loss_probability=float(np.mean(nav<1)),
                paths=paths,years=years,as_of=str(start.date()),scenario=scenario,goal=goal,nominal_goal=nominal_goal,goal_probability=goal_probability,inflation=inflation,real_median=real_median,
                crisis_path_share=float(np.mean((states>0).any(axis=1))),jump_path_share=float(np.mean((states==3).any(axis=1))),
                drawdown20=float(np.mean(max_dd>=.20)),median_max_drawdown=float(np.median(max_dd)),
                tail_return99=float(worst.mean()),median_longest_underwater_months=float(np.median(longest)))
