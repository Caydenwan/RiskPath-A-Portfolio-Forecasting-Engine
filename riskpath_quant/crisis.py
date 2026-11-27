"""Illustrative crisis overlays, not estimated event probabilities or calibrated forecasts."""
import numpy as np
from institutional import ASSETS, G

SCENARIOS = ('baseline', 'mixed', 'recession', 'black_swan', 'grey_rhino')
# State order: baseline, recession, persistent inflation/credit pressure, sudden jump.
# Monthly transition assumptions; not fitted to data.
TRANSITION = np.array([[.982,.012,.004,.002], [.15,.83,.015,.005],
                       [.08,.025,.89,.005], [.15,.80,.05,0.]])
LOG_SHIFT = np.array([[0,0,0,0,0,0,0], [0,-.025,.005,-.018,-.012,-.003,-.03],
                      [0,-.012,-.010,-.010,.002,-.002,-.018], [0,-.30,.035,-.14,-.14,-.04,-.32]])
# Shared Student-t factor introduces additional state-dependent co-movement.
LOAD = np.array([[0,0,0,0,0,0,0], [0,.030,-.008,.018,.017,.008,.032],
                 [0,.022,.014,.018,.015,.007,.025], [0,.070,-.018,.045,.040,.025,.080]])


def crisis_states(mode, paths, months, rng):
    if mode not in SCENARIOS or paths<1 or months<1:
        raise ValueError('Invalid crisis scenario')
    states=np.zeros((paths,months),dtype=np.int8)
    if mode=='mixed':
        state=np.zeros(paths,dtype=np.int8)
        cdf=np.cumsum(TRANSITION,axis=1)
        for t in range(months):
            state=(rng.random(paths)[:,None]>cdf[state,:-1]).sum(axis=1).astype(np.int8)
            states[:,t]=state
    elif mode=='recession': states[:,:min(6,months)]=1
    elif mode=='grey_rhino': states[:,:min(12,months)]=2
    elif mode=='black_swan':
        states[:,0]=3; states[:,1:min(6,months)]=1
    return states


def apply_crisis(x, state, rng):
    """Add state-specific log shifts and a common thick-tailed innovation to base returns."""
    if x.ndim!=2 or x.shape[1]!=len(ASSETS): raise ValueError('Crisis mode requires the 28-asset universe')
    out=x.copy(); active=state>0
    if not active.any(): return out
    s=state[active]; shift=LOG_SHIFT[s]@G; load=LOAD[s]@G
    # Distinguish illustrative hedges from the generic diversifier sleeve.
    for name, j, k in [('GLD',.015,-.018),('BTAL',.025,-.035),('TAIL',.035,-.045),('UUP',.010,-.012)]:
        col=ASSETS.index(name); scale=np.where(s==3,3.,1.)
        shift[:,col]=j*scale; load[:,col]=k*scale
    common=rng.standard_t(5,size=len(s))*np.sqrt(3/5)
    log=np.log1p(x[active])+shift+load*common[:,None]
    # Explicit numerical safety bound on shocked monthly log return, not a market limit.
    out[active]=np.expm1(np.clip(log,-8,3))
    return out
