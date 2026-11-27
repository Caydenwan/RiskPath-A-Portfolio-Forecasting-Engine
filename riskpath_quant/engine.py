"""Long-only portfolio research with chronological execution and explicit costs."""
import numpy as np
import pandas as pd
from scipy.optimize import minimize, linprog

ASSETS = ['BIL','IEF','TLT','LQD','TIP','SPY','QQQ','EFA','EEM','GLD','VNQ']


def validate(r):
    if r.empty or not r.index.is_monotonic_increasing or not r.index.is_unique or not r.columns.is_unique:
        raise ValueError('Require unique chronological returns and assets')
    if not np.isfinite(r.to_numpy()).all() or (r <= -1).any().any():
        raise ValueError('Require finite simple returns greater than -1')


def weights(r, method):
    validate(r)
    x = r.to_numpy(); n = x.shape[1]; w0 = np.ones(n)/n
    if method == 'equal': return w0
    if method == '60_40':
        w = np.zeros(n); w[r.columns.get_loc('SPY')] = .6; w[r.columns.get_loc('IEF')] = .4
        return w
    s = np.atleast_2d(np.cov(x, rowvar=False))
    s = .75*s + .25*np.diag(np.diag(s)) + np.eye(n)*1e-8
    if method == 'minvar':
        f = lambda w: 1e4*w@s@w
    elif method == 'risk_parity':
        def f(w):
            rc = w*(s@w)/(w@s@w)
            return np.sum((rc-1/n)**2)
    elif method == 'cvar':
        # Rockafellar-Uryasev empirical 95% expected shortfall minimization.
        m = len(x); c = np.r_[np.zeros(n),1,np.full(m,1/(.05*m))]
        a = np.c_[-x,-np.ones(m),-np.eye(m)]
        sol = linprog(c,A_ub=a,b_ub=np.zeros(m),A_eq=[np.r_[np.ones(n),0,np.zeros(m)]],b_eq=[1],bounds=[(0,1)]*n+[(None,None)]+[(0,None)]*m,method='highs')
        if not sol.success: raise RuntimeError(sol.message)
        return sol.x[:n]
    else: raise ValueError('Unknown method')
    sol = minimize(f,w0,method='SLSQP',bounds=[(0,1)]*n,constraints=[{'type':'eq','fun':lambda w:w.sum()-1}],options={'ftol':1e-12,'maxiter':1000})
    if not sol.success: raise RuntimeError(sol.message)
    return sol.x


def walk_forward(r, method, lookback=60, rebalance=3, cost_bps=10):
    """Train strictly before month t, trade at start of t, drift weights thereafter.
    Cost is bps per dollar of gross absolute traded notional. Initial entry is charged.
    """
    validate(r)
    if lookback < 2 or len(r) <= lookback or rebalance < 1 or cost_bps < 0: raise ValueError('Invalid backtest settings')
    w = np.zeros(r.shape[1]); rows=[]; allocations=[]
    for i in range(lookback,len(r)):
        turnover = 0.
        if (i-lookback)%rebalance==0:
            target = weights(r.iloc[i-lookback:i],method)
            turnover = np.abs(target-w).sum(); w = target
        allocations.append(w.copy())
        realized = r.iloc[i].to_numpy(); gross = float(w@realized)
        cost = turnover*cost_bps/10000
        if cost >= 1: raise ValueError('Cost exceeds capital')
        net = (1-cost)*(1+gross)-1
        rows.append((gross,net,turnover))
        w = w*(1+realized)/(1+gross)
    idx = r.index[lookback:]
    return pd.DataFrame(rows,index=idx,columns=['gross','net','turnover']),pd.DataFrame(allocations,index=idx,columns=r.columns)


def metrics(net, turnover, cash):
    """Monthly arithmetic excess Sharpe; ES reports mean worst ceil(5% n) losses."""
    nav = np.r_[1.,np.cumprod(1+net)]
    excess = np.asarray(net)-np.asarray(cash)
    tail = max(1,int(np.ceil(.05*len(net))))
    sd = excess.std(ddof=1)
    return {'cagr':float(nav[-1]**(12/len(net))-1),'vol':float(np.std(net,ddof=1)*np.sqrt(12)),
            'sharpe':float(excess.mean()/sd*np.sqrt(12)) if sd>1e-12 else None,
            'max_drawdown':float((nav/np.maximum.accumulate(nav)-1).min()),
            'es95_monthly':float(-np.sort(net)[:tail].mean()),'annual_turnover':float(np.mean(turnover)*12)}


def bootstrap(r,w,months=120,paths=2000,block=6,seed=42,initial=100000,contribution=0):
    """Joint circular block bootstrap; monthly constant weights, no costs.
    NAV excludes external cash flows; wealth includes end-of-month contributions.
    """
    validate(r); w=np.asarray(w,float)
    if len(w)!=r.shape[1] or np.any(w<0) or not np.isclose(w.sum(),1) or min(months,paths,block,initial)<=0 or contribution<0: raise ValueError('Invalid simulation inputs')
    rng=np.random.default_rng(seed); n=len(r)
    starts=rng.integers(n,size=(paths,int(np.ceil(months/block))))
    ids=((starts[:,:,None]+np.arange(block))%n).reshape(paths,-1)[:,:months]
    p=(r.to_numpy()[ids]@w)
    nav=np.cumprod(1+p,axis=1); wealth=np.full(paths,float(initial))
    for t in range(months): wealth=wealth*(1+p[:,t])+contribution
    return {'nav':nav,'terminal_wealth':wealth}


def synthetic(seed=7):
    """Artificial monthly returns; asset labels are proxies, not observed ETF prices."""
    rng=np.random.default_rng(seed); n=240
    f=rng.normal(size=(n,3)); f[95:101,0]-=1.7; f[180:188,:2]-=1.4
    load=np.array([[.0005,0,0],[.002,.017,0],[.005,.035,0],[.012,.014,0],[.005,.013,.006],[.038,0,0],[.052,-.004,0],[.041,0,.005],[.052,0,.012],[.003,-.004,.036],[.034,.009,.010]])
    mu=np.array([.002,.003,.003,.004,.003,.007,.008,.006,.006,.004,.006])
    noise=rng.normal(size=(n,len(mu)))*np.array([.0005,.004,.009,.008,.006,.012,.018,.015,.025,.015,.022])
    return pd.DataFrame(mu+f@load.T+noise,index=pd.date_range('2006-01-31',periods=n,freq=pd.offsets.MonthEnd()),columns=ASSETS)
