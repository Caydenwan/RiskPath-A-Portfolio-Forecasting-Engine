"""Goal-first portfolio search, with independent bootstrap simulation checks.

Monthly rebalance to a fixed candidate target. Initial purchase, monthly
rebalances and new contributions pay modeled gross-notional execution fees.
All flows buy target weights after each monthly rebalance; terminal wealth
is therefore exactly affine in initial capital and constant monthly deposits.
Risk is peak-to-trough monthly net investment NAV, excluding external flows
and deposit-specific fees. No guarantee of intramonth or future drawdowns.
"""
import numpy as np
import pandas as pd
from engine import validate
from estimation import window_plan, moments, estimate_meta
from personal import personal_allocate
from institutional import ASSETS, GROUPS, G, stress, risk_contributions
from public_research import ASSETS as P_ASSETS, GROUPS as P_GROUPS, G as P_G, public_allocate, public_shock
from crisis import crisis_states, apply_crisis, SCENARIOS

SCREEN=1000
CHECK=2000
Z=1.6448536269514722  # one-sided 95% binomial Wilson bound
MAX_YEARS=30

def bound(k,n,upper):
    p=np.asarray(k,dtype=float)/n
    center=(p+Z*Z/(2*n))/(1+Z*Z/n)
    radius=Z*np.sqrt(p*(1-p)/n+Z*Z/(4*n*n))/(1+Z*Z/n)
    return np.clip(center+radius if upper else center-radius,0,1)

def candidates(r,public,selection):
    cash=np.zeros(r.shape[1]);cash[0]=1.
    out=[cash]
    failures=0
    for score in range(0,101,10):
        try:
            w=(public_allocate(r,score,30,selection) if public else personal_allocate(r,score,30,selection))[0]
        except RuntimeError:
            failures+=1;continue
        # Also evaluate cash blends of each candidate, preserving long-only caps.
        for v in (w,.5*w+.5*cash):
            if not any(np.max(np.abs(v-z))<1e-4 for z in out):out.append(v)
    return np.asarray(out),failures

def sample(r,weights,selection,paths,seed,cost,scenario,public,max_years):
    x=r.to_numpy();windows,probs=window_plan(len(x),selection)
    rng=np.random.default_rng(seed)
    shape=(paths,int(np.ceil(max_years*12/6)))
    window=rng.choice(windows,size=shape,p=probs)
    starts=len(x)-window+(rng.random(shape)*(window-6+1)).astype(int)
    ids=(starts[:,:,None]+np.arange(6)).reshape(paths,-1)[:,:max_years*12]
    def multiplier(a):
        gross=a@weights.T
        # Sum absolute traded asset fractions after returns, before target rebalance.
        turnover=np.empty_like(gross)
        for i,w in enumerate(weights):
            drift=(1+a)*w/(1+gross[:,i,None])
            turnover[:,i]=np.abs(drift-w).sum(axis=1)
        return (1+gross)*(1-cost*turnover)
    baseline=multiplier(x)
    shock_rng=np.random.default_rng(seed+1)
    states=crisis_states(scenario,paths,max_years*12,shock_rng)
    overlay=public_shock if public else apply_crisis
    shape=(paths,len(weights))
    a=np.full(shape,1-cost);b=np.zeros(shape);peak=np.ones(shape);dd=np.zeros(shape)
    result=[]
    for t in range(max_years*12):
        mult=baseline[ids[:,t]]
        if scenario!='baseline' and np.any(states[:,t]>0):
            active=states[:,t]>0
            # Overlay is evaluated on all paths to retain the same random-stream semantics.
            shifted=overlay(x[ids[:,t]],states[:,t],shock_rng)
            mult=mult.copy();mult[active]=multiplier(shifted[active])
        a*=mult;b=b*mult+1-cost
        peak=np.maximum(peak,a);dd=np.maximum(dd,1-a/peak)
        if (t+1)%12==0:result.append((a.copy(),b.copy(),dd.copy()))
    return result

def calculate_goal(r,p,public=False):
    validate(r)
    if list(r.columns)!=(P_ASSETS if public else ASSETS) or np.any(np.diff(r.index.to_period('M').asi8)!=1):
        raise ValueError('Goal planning requires consecutive monthly returns in the documented asset order')
    selection=p.get('lookback','auto')
    initial=float(p['initial']);goal=float(p['goal']);monthly=float(p['contribution']);years=int(p['years'])
    inflation=float(p.get('inflation',2.5))/100;cost=float(p['cost'])/10000
    dd=float(p['max_drawdown'])/100;limit=float(p['risk_limit'])/100;confidence=float(p['confidence'])/100
    scenario=p.get('scenario','baseline')
    if not np.isfinite([initial,goal,monthly,inflation,cost,dd,limit,confidence]).all() or not (initial>0 and goal>0 and monthly>=0 and 1<=years<=MAX_YEARS and 0<=inflation<=.20 and 0<=cost<=.005 and .05<=dd<=.50 and .05<=limit<=.50 and .50<=confidence<=.95 and scenario in SCENARIOS):
        raise ValueError('Check goal, contribution, horizon and risk constraints')
    if p['source']!='synthetic' and r.index[-1].to_period('M')>=pd.Timestamp(p['as_of']).to_period('M'):
        raise ValueError('Use only completed historical months')
    w,failed=candidates(r,public,selection)
    # Search and confirmation streams are independent; neither is fresh market evidence.
    train=sample(r,w,selection,SCREEN,4201,cost,scenario,public,MAX_YEARS)
    check=sample(r,w,selection,CHECK,9371,cost,scenario,public,MAX_YEARS)
    risk_train=[(d>dd).sum(axis=0) for _,_,d in train]
    risk_check=[(d>dd).sum(axis=0) for _,_,d in check]
    eligible=[bound(k,SCREEN,True)<=limit+1e-12 for k in risk_train]
    targets=[goal*(1+inflation)**h for h in range(1,MAX_YEARS+1)]
    def confirm(h,m,i):
        a,b,_=check[h-1];wealth=initial*a[:,i]+m*b[:,i]
        k=int(np.sum(wealth>=targets[h-1]));q=int(risk_check[h-1][i])
        lower=float(bound(k,CHECK,False));upper=float(bound(q,CHECK,True))
        risk_ok=upper<=limit+1e-12
        return dict(years=h,monthly=float(m),candidate=int(i),success=k/CHECK,success_lower=lower,risk=q/CHECK,risk_upper=upper,risk_ok=bool(risk_ok),goal_ok=bool(lower>=confidence-1e-12),verified=bool(risk_ok and lower>=confidence-1e-12),median=float(np.median(wealth)),wealth_range=np.percentile(wealth,[5,95]).tolist(),target=targets[h-1])
    def best(h,m):
        a,b,_=train[h-1]
        k=(initial*a+m*b>=targets[h-1]).sum(axis=0)
        possible=np.flatnonzero(eligible[h-1])
        if not len(possible):return None
        i=min(possible,key=lambda j:(-k[j],risk_train[h-1][j],j))
        return confirm(h,m,i)
    # Smallest rounded monthly contribution in the candidate grid satisfying
    # the *screening* confidence lower bound. Verify without tuning to check data.
    required_count=next(k for k in range(SCREEN+1) if bound(k,SCREEN,False)>=confidence)
    def required(h):
        a,b,_=train[h-1]
        possible=np.flatnonzero(eligible[h-1])
        if not len(possible):return None
        req=np.maximum(0,(targets[h-1]-initial*a[:,possible])/b[:,possible])
        needed=np.partition(req,required_count-1,axis=0)[required_count-1]
        rounded=np.ceil(needed/50)*50
        j=min(range(len(possible)),key=lambda j:(rounded[j],risk_train[h-1][possible[j]],possible[j]))
        return confirm(h,float(rounded[j]),int(possible[j]))
    current=best(years,monthly)
    same=required(years)
    alternatives=[]
    if same is not None and same['monthly']>=monthly and not (same['monthly']==monthly and current and current['verified']):
        alternatives.append(dict(kind='contribution',**same))
    # Select the first later horizon meeting BOTH SCREEN bounds. Confirm once.
    # Don't choose alternatives based on holdout outcomes.
    for h in range(years+1,MAX_YEARS+1):
        a,b,_=train[h-1]
        k=(initial*a+monthly*b>=targets[h-1]).sum(axis=0)
        eligible_goal=np.flatnonzero(eligible[h-1]&(bound(k,SCREEN,False)>=confidence))
        if len(eligible_goal):
            i=min(eligible_goal,key=lambda j:(-k[j],risk_train[h-1][j],j))
            alternatives.append(dict(kind='timeline',**confirm(h,monthly,i)));break
    # One trade-off: first later horizon with a smaller required increase.
    if same is not None and same['monthly']>monthly:
        for h in range(years+1,MAX_YEARS+1):
            q=required(h)
            if q is not None and monthly<q['monthly']<same['monthly']:
                alternatives.append(dict(kind='combined',**q));break
    # Include the current horizon and nearby longer horizons, within 1–30 years.
    horizons=sorted(set([max(1,years-5),years,min(30,years+1),min(30,years+3),min(30,years+5)]))
    amounts=sorted(set([0,monthly,max(250,np.ceil(monthly*1.5/50)*50),max(500,np.ceil(monthly*2/50)*50),max(1000,np.ceil(monthly*3/50)*50)]+([same['monthly']] if same is not None else [])))
    grid=[[best(h,m) for h in horizons] for m in amounts]
    mat=P_G if public else G;groups=P_GROUPS if public else list(GROUPS)
    meta=estimate_meta(len(r),selection,r.to_numpy())
    meta.update(first=str(r.index[0].date()),last=str(r.index[-1].date()),training_first=str(r.index[-meta['longest']].date()),provider=p.get('provider','Historical monthly returns'))
    result=dict(mode='goal',source=p['source'],current=current,alternatives=alternatives,required_plan=same,horizons=horizons,amounts=amounts,grid=grid,initial=initial,goal=goal,monthly=monthly,years=years,inflation=inflation,max_drawdown=dd,risk_limit=limit,confidence=confidence,screen_paths=SCREEN,check_paths=CHECK,candidate_count=len(w),solver_failures=failed,scenario=scenario,estimation=meta,assets=list(r.columns),sleeves=list(groups))
    # A risk-unverified plan is not offered as an allocation recommendation.
    if current is not None and current['risk_ok']:
        selected=w[current['candidate']]
        _,cov=moments(r.to_numpy(),selection)
        risk=mat@(selected*(cov@selected)/(selected@cov@selected))
        result.update(weights=(mat@selected).tolist(),assetWeights=selected.tolist(),risk=risk.tolist())
    return result
