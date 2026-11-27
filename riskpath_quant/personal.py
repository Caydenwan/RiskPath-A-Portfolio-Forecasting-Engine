"""Illustrative personal risk preference mapping; not a suitability assessment."""
import numpy as np
from scipy.optimize import minimize
from institutional import ASSETS, GROUPS, G, covariance
from engine import validate
from estimation import moments

HORIZON_CAPS = {1:30, 3:50, 5:70, 10:100, 15:100, 20:100, 30:100}
SLEEVE_CAPS = np.array([1., .80, .85, .35, .35, .35, .10])
ASSET_CAPS = np.array([1. if a == 'BIL' else .25 for a in ASSETS])


def preference(score, years):
    if not np.isfinite(score) or not 0 <= score <= 100 or years not in HORIZON_CAPS:
        raise ValueError('Risk score must be 0–100 and horizon must be supported')
    effective = min(float(score), HORIZON_CAPS[years])
    return effective, float(1000 * (0.0005 ** (effective / 100)))


def personal_allocate(r, score, years, estimation=None):
    validate(r)
    if list(r.columns) != ASSETS or len(r) < 12:
        raise ValueError('Require ordered 28-asset history and at least 12 months')
    effective, lam = preference(score, years)
    x = r.to_numpy()
    if estimation is None: avg,s=12*x.mean(axis=0),covariance(x)
    else: avg,s=moments(x,estimation)
    mu = .25*avg + .75*(G.T @ ((G@avg)/G.sum(axis=1)))
    # Fixed feasible set across scores: higher risk aversion penalizes variance more.
    def obj(w): return 100*(.5*lam*(w@s@w) - mu@w)
    def jac(w): return 100*(lam*(s@w) - mu)
    w0 = np.zeros(len(ASSETS)); w0[0] = 1
    sol = minimize(obj,w0,jac=jac,method='SLSQP',bounds=list(zip(np.zeros(len(w0)),ASSET_CAPS)),
                   constraints=[{'type':'eq','fun':lambda w:w.sum()-1,'jac':lambda w:np.ones(len(w))},
                                {'type':'ineq','fun':lambda w:SLEEVE_CAPS-G@w,'jac':lambda w:-G}],
                   options={'ftol':1e-11,'maxiter':1000})
    w = sol.x
    if not sol.success or abs(w.sum()-1)>1e-7 or np.any(w < -1e-8) or np.any(w>ASSET_CAPS+1e-7) or np.any(G@w>SLEEVE_CAPS+1e-7):
        raise RuntimeError('Personal optimization failed: '+str(sol.message))
    w = np.maximum(w,0); w/=w.sum()
    return w, {'score':float(score),'effective_score':effective,'lambda':lam,
               'horizon_cap':HORIZON_CAPS[years], 'estimated_volatility':float(np.sqrt(w@s@w)),
               'estimated_return':float(w@mu)}
