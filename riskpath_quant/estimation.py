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

def moments(x,selection='auto'):
    x=np.asarray(x,dtype=float)
    if x.ndim!=2 or not np.isfinite(x).all(): raise ValueError('Invalid estimation sample')
    windows,weights=window_plan(len(x),selection)
    mean=np.zeros(x.shape[1]); cov=np.zeros((x.shape[1],x.shape[1]))
    for n,a in zip(windows,weights):
        sample=x[-n:]; m=sample.mean(axis=0)*12; s=np.atleast_2d(np.cov(sample,rowvar=False))*12
        # Increase diagonal shrinkage when sample size is small relative to dimension.
        alpha=min(.65,max(.20,x.shape[1]/(n-1)))
        mean+=a*m; cov+=a*((1-alpha)*s+alpha*np.diag(np.diag(s)))
    return mean,cov+np.eye(x.shape[1])*1e-7

def estimate_meta(n,selection='auto'):
    ws,weights=window_plan(n,selection)
    return dict(selection=str(selection),windows=ws,weights=weights.tolist(),common_months=n,longest=ws[-1],tail_observations=ws[-1]*.05)
