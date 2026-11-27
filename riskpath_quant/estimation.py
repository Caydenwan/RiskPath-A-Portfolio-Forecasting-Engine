"""Multi-horizon shrinkage estimates; fixed research weights, not an optimized window."""
import numpy as np

WINDOWS=(36,60,120,240)
BASE_WEIGHTS=(.15,.25,.35,.25)

def window_plan(n, selection='auto'):
    if selection=='auto':
        if n<36: raise ValueError('Need at least 36 complete monthly returns')
        windows=[x for x in WINDOWS if x<=n]
        weights=list(BASE_WEIGHTS[:len(windows)])
        longest=min(n,240)
        if longest>windows[-1]:
            windows.append(longest); weights.append(BASE_WEIGHTS[len(weights)])
        weights=np.asarray(weights,dtype=float); weights/=weights.sum()
        return windows,weights
    k=int(selection)
    if k not in WINDOWS or n<k: raise ValueError(f'{k}-month window unavailable: only {n} complete returns')
    return [k],np.array([1.])

def correlation_shrinkage(sample):
    """Ledoit-Wolf intensity on standardized active columns, then restore sample volatilities.
    Unlike shrinkage of raw covariance toward a common variance, this preserves cash/bond/equity scales.
    """
    x=np.asarray(sample,float)
    n,p=x.shape
    if n<2: raise ValueError('At least two rows required')
    centered=x-x.mean(axis=0)
    sd=np.sqrt(np.mean(centered**2,axis=0))
    active=sd>1e-14
    z=centered[:,active]/sd[active]
    q=z.shape[1]
    raw=centered.T@centered/(n-1)
    alpha=0.
    if q>1:
        c=z.T@z/n
        delta=np.sum((c-np.eye(q))**2)/q
        beta=(np.sum((z*z).T@(z*z))/n-np.sum(c*c))/(q*n)
        alpha=float(np.clip(beta/delta,0,1)) if delta>1e-15 else 1.
    return (1-alpha)*raw+alpha*np.diag(np.diag(raw)),alpha

def moments(x,selection='auto'):
    x=np.asarray(x,dtype=float)
    if x.ndim!=2 or not np.isfinite(x).all(): raise ValueError('Invalid estimation sample')
    windows,weights=window_plan(len(x),selection)
    mean=np.zeros(x.shape[1]); cov=np.zeros((x.shape[1],x.shape[1]))
    for n,a in zip(windows,weights):
        sample=x[-n:]; m=sample.mean(axis=0)*12; s,_=correlation_shrinkage(sample)
        mean+=a*m; cov+=a*s*12
    return mean,cov+np.eye(x.shape[1])*1e-7

def estimate_meta(n,selection='auto',returns=None):
    ws,weights=window_plan(n,selection)
    result=dict(selection=str(selection),windows=ws,weights=weights.tolist(),common_months=n,longest=ws[-1],tail_observations=ws[-1]*.05,covariance_method='Ledoit-Wolf correlation shrinkage')
    if returns is not None: result['shrinkage']=[correlation_shrinkage(np.asarray(returns)[-k:])[1] for k in ws]
    return result
