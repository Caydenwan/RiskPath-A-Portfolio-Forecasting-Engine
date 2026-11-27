"""Research diagnostics: same-period validation, constrained mean-variance frontier, goal scenarios."""
import numpy as np
from scipy.optimize import minimize
from engine import metrics,validate
from estimation import moments,window_plan
from forecast import forecast_paths
from personal import personal_allocate,ASSET_CAPS,SLEEVE_CAPS
from institutional import ASSETS,G,spec,allocate
from public_research import ASSETS as PUB_ASSETS, CAPS as PUB_CAPS, G as PUB_G, public_allocate,public_shock

def forecast_options(p,r,w,public=False):
    selection=p.get('lookback','auto')
    windows,probs=window_plan(len(r),selection)
    paths=int(p.get('paths',2000))
    if paths not in (2000,10000): raise ValueError('Use 2,000 or 10,000 simulation paths')
    goal=float(p.get('goal',0) or 0)
    inflation=float(p.get('inflation',0))/100
    return dict(r=r.iloc[-windows[-1]:].to_numpy(),w=w,initial=float(p['initial']),contribution=float(p['contribution']),years=int(p['years']),as_of=p['as_of'],cost_bps=float(p['cost']),paths=paths,windows=windows,window_weights=probs,goal=goal or None,inflation=inflation,crisis_overlay=public_shock if public else None)

def benchmark_weights(r):
    public=list(r.columns)==PUB_ASSETS
    n=r.shape[1]; eq=np.zeros(n); bond=np.zeros(n)
    eq[r.columns.get_loc('TSP_C' if public else 'VTI')]=1
    bond[r.columns.get_loc('TSP_F' if public else 'IEF')]=1
    return {'US equity proxy':eq,'60/40':.6*eq+.4*bond,'Equal weight':np.ones(n)/n}

def frontier(r,p,w,public=False):
    avg,s=moments(r.to_numpy(),p.get('lookback','auto'))
    if public:
        mu=avg.copy();mu[2:]=.25*avg[2:]+.75*avg[2:].mean()
        cap=PUB_CAPS; a=PUB_G; lo=np.zeros(3);hi=np.array([1.,.85,.8])
    else:
        mu=.25*avg+.75*(G.T@((G@avg)/G.sum(axis=1)))
        a=G
        if p.get('profile')=='personal': cap=ASSET_CAPS;lo=np.zeros(len(G));hi=SLEEVE_CAPS
        else:
            policy,_,cap=spec(p['mandate']);lo=np.asarray(policy['lo']);hi=np.asarray(policy['hi'])
    n=len(mu)
    def point(v):return {'vol':float(np.sqrt(max(0,v@s@v))),'ret':float(v@mu)}
    def feasible(v):
        return abs(v.sum()-1)<1e-6 and np.all(v>=-1e-7) and np.all(v<=cap+1e-7) and np.all(a@v>=lo-1e-7) and np.all(a@v<=hi+1e-7)
    start=w if feasible(w) else (spec(p['mandate'])[1] if not public and p.get('profile')!='personal' else np.eye(n)[0])
    cons=[{'type':'eq','fun':lambda v:v.sum()-1,'jac':lambda v:np.ones(n)},{'type':'ineq','fun':lambda v:np.r_[a@v-lo,hi-a@v],'jac':lambda v:np.r_[a,-a]}]
    points=[]
    for lam in [None,*np.geomspace(1e5,.001,28),0.]:
        def obj(v):return 100*(v@s@v if lam is None else .5*lam*(v@s@v)-v@mu)
        def jac(v):return 100*(2*s@v if lam is None else lam*s@v-mu)
        sol=minimize(obj,start,jac=jac,bounds=list(zip(np.zeros(n),cap)),constraints=cons,method='SLSQP',options={'ftol':1e-10,'maxiter':500})
        if sol.success and feasible(sol.x):
            start=sol.x;points.append(point(start))
    points.sort(key=lambda q:q['vol'])
    efficient=[]
    for q in points:
        if not efficient or q['ret']>efficient[-1]['ret']+1e-8: efficient.append(q)
    return {'points':efficient,'selected':point(w),'benchmarks':[dict(name=k,**point(v),feasible=bool(feasible(v))) for k,v in benchmark_weights(r).items()],'selected_feasible':bool(feasible(w)),'solver_points':len(points),'requested_points':30}

def validation(r,p,public=False):
    validate(r); n=len(r); cost=float(p['cost'])/10000
    eligible=[k for k in (36,60,120,240) if n-k>=12]
    if not eligible:return {'rows':[],'reason':'Need at least 48 monthly observations for a 36-month training window and 12-month test.'}
    # All strategies are measured from the same month, with the same costs and rebalance dates.
    start=max(eligible)
    cash=r.iloc[start:,0].to_numpy()
    methods={**{str(k)+' mo':str(k) for k in eligible},'Adaptive':'auto'}
    benchmarks=benchmark_weights(r); rows=[]; navs=[]
    for name,sel in [*methods.items(),*[(k,None) for k in benchmarks]]:
        w=np.zeros(r.shape[1]); nets=[]; turns=[]
        for i in range(start,n):
            t=0.
            if (i-start)%3==0:
                train=r.iloc[:i]
                if sel is None:target=benchmarks[name]
                elif public:target=public_allocate(train,float(p['risk_score']),int(p['years']),selection=sel)[0]
                elif p.get('profile')=='personal':target=personal_allocate(train,float(p['risk_score']),int(p['years']),estimation=sel)[0]
                else:target=allocate(train,p['mandate'],p['method'],estimation=sel)
                t=float(np.abs(target-w).sum());w=target.copy()
            realized=r.iloc[i].to_numpy();gross=float(w@realized)
            nets.append((1-t*cost)*(1+gross)-1);turns.append(t)
            w=w*(1+realized)/(1+gross)
        m=metrics(np.asarray(nets),np.asarray(turns),cash)
        rows.append(dict(name=name,**m))
        navs.append(np.r_[1.,np.cumprod(1+np.asarray(nets))].tolist())
    return dict(rows=rows,navs=navs,dates=['Start',*[str(d.date()) for d in r.index[start:]]],months=n-start,first=str(r.index[start].date()),last=str(r.index[-1].date()),windows=eligible,excluded=[k for k in (36,60,120,240) if k not in eligible])

def diagnostics(r,p,w,public=False):
    opts=forecast_options(p,r,w,public)
    scenario=p.get('scenario','baseline')
    f=forecast_paths(**opts,scenario=scenario)
    result={'forecast':f,'frontier':frontier(r,p,w,public)}
    if p.get('validate_model'):
        if p.get('profile')!='personal' and p.get('method')=='surplus':result['validation']={'rows':[],'reason':'Liability-aware validation requires aligned liability history.'}
        else:result['validation']=validation(r,p,public)
    if p.get('compare_scenarios'):
        # Common random numbers reduce comparison noise. Limit the secondary experiment to 2,000 paths.
        opts['paths']=2000;cases=[]
        for sc in ('baseline','recession','grey_rhino','black_swan'):
            v=forecast_paths(**opts,scenario=sc)
            cases.append(dict(scenario=sc,median=v['wealth_quantiles'][1][-1],loss=v['loss_probability'],goal=v['goal_probability'],drawdown20=v['drawdown20']))
        result['scenarios']=cases
    return result
