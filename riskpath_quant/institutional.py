"""Institutional allocation laboratory: liquid proxies, explicit mandates, no leverage."""
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize, linprog
from engine import validate, metrics
from estimation import moments, window_plan

GROUPS = {
    'cash': ['BIL'],
    'equity': ['VTI','IWM','QQQ','VTV','VEA','VWO'],
    'rates': ['SHY','IEF','TLT','TIP','BNDX'],
    'credit': ['LQD','HYG','EMB','BKLN'],
    'real': ['GLD','DBC','VNQ','IGF'],
    'diversifiers': ['DBMF','KMLM','BTAL','QAI','UUP','TAIL'],
    'listed_private': ['PSP','BIZD'],
}
ASSETS = [a for names in GROUPS.values() for a in names]
G = np.array([[float(a in names) for a in ASSETS] for names in GROUPS.values()])
# Illustrative policy ranges and risk targets; not copied from any institution.
POLICY = {
 'pension': {'ref':[.05,.35,.25,.12,.12,.06,.05], 'lo':[.03,.25,.15,.05,.05,.02,0], 'hi':[.12,.45,.40,.22,.22,.20,.10], 'risk':[0,.45,.20,.10,.12,.08,.05]},
 'liquid_multi': {'ref':[.10,.25,.15,.15,.15,.15,.05], 'lo':[.05,.10,.10,.05,.05,.10,0], 'hi':[.20,.35,.35,.25,.25,.35,.10], 'risk':[0,.30,.20,.15,.15,.15,.05]},
}
METHODS = ['policy','60_40','minvar','utility','risk_budget','cvar']


def spec(mandate):
    p = POLICY[mandate]
    ref = G.T @ (np.array(p['ref']) / G.sum(axis=1))
    cap = np.array([p['hi'][0] if a == 'BIL' else .18 for a in ASSETS])
    return p, ref, cap


def covariance(x):
    s = np.cov(x, rowvar=False) * 12
    return .8*s + .2*np.diag(np.diag(s)) + np.eye(len(s))*1e-7


def risk_contributions(w,s):
    return G @ (w*(s@w)/(w@s@w))


def feasible(w,p,cap,tol=2e-6):
    return abs(w.sum()-1)<=tol and np.all(w>=-tol) and np.all(w<=cap+tol) and np.all(G@w>=np.array(p['lo'])-tol) and np.all(G@w<=np.array(p['hi'])+tol)


def allocate(r,mandate,method,liability=None,estimation=None):
    validate(r)
    if list(r.columns)!=ASSETS or len(r)<12: raise ValueError('Need ordered universe and at least 12 months')
    p,ref,cap=spec(mandate); x=r.to_numpy(); n=len(ref); m=len(x)
    if method=='policy': return ref
    if method=='60_40':
        w=np.zeros(n); w[ASSETS.index('VTI')]=.6; w[ASSETS.index('IEF')]=.4; return w
    if estimation is not None:
        avg,s=moments(x,estimation)
        if method=='cvar':
            x=x[-window_plan(len(x),estimation)[0][-1]:]; m=len(x)
    else:
        s=covariance(x); avg=x.mean(axis=0)*12
    # shrink trailing means 75% toward their within-sleeve means; no future returns.
    mu=.25*avg+.75*(G.T @ ((G@avg)/G.sum(axis=1)))
    a=np.r_[G,-G]; b=np.r_[p['hi'],-np.array(p['lo'])]
    if method=='cvar':
        c=np.r_[np.zeros(n),1,np.full(m,1/(.05*m))]
        A=np.vstack([np.c_[-x,-np.ones(m),-np.eye(m)],np.c_[a,np.zeros((len(a),m+1))]])
        sol=linprog(c,A_ub=A,b_ub=np.r_[np.zeros(m),b],A_eq=[np.r_[np.ones(n),np.zeros(m+1)]],b_eq=[1],bounds=list(zip(np.zeros(n),cap))+[(None,None)]+[(0,None)]*m,method='highs')
    else:
        if method=='minvar': f=lambda w:100*(w@s@w)
        elif method=='utility': f=lambda w:100*(2.5*w@s@w-mu@w)
        elif method=='risk_budget': f=lambda w:np.sum((risk_contributions(w,s)-p['risk'])**2)
        elif method=='surplus':
            if liability is None or not liability.index.equals(r.index) or not np.isfinite(liability).all(): raise ValueError('Aligned liability returns required')
            joint=covariance(np.c_[x,liability.to_numpy()]) if estimation is None else moments(np.c_[x,liability.to_numpy()],estimation)[1]
            if estimation is not None: s=joint[:-1,:-1]
            cross=joint[:-1,-1]
            f=lambda w:100*(w@s@w-2*w@cross)
        else: raise ValueError(method)
        sol=minimize(f,ref,method='SLSQP',bounds=list(zip(np.zeros(n),cap)),constraints=[{'type':'eq','fun':lambda w:w.sum()-1},{'type':'ineq','fun':lambda w:b-a@w}],options={'ftol':1e-10,'maxiter':500})
    w=sol.x[:n] if sol.x is not None else np.full(n,np.nan)
    if not sol.success or not feasible(w,p,cap): raise RuntimeError(f'{method}: {sol.message}')
    return w


def simulate(seed=27,months=240):
    """Synthetic monthly factor returns and stylized liability mark-to-market."""
    rng=np.random.default_rng(seed); z=rng.normal(size=(months,6))
    z[95:101,0]-=1.8; z[180:188,1]-=1.8; z[180:188,3]+=1.2
    # Factors: equity, duration, credit, inflation, trend, USD. Parameters illustrative.
    pars={'cash':(.002,[0,.001,0,0,0,0],.0005), 'equity':(.006,[.04,-.003,.006,0,0,-.005],.018), 'rates':(.003,[0,.020,0,-.005,0,.002],.006), 'credit':(.004,[.012,.010,.017,0,0,-.004],.009), 'real':(.005,[.012,-.006,.003,.029,0,-.006],.020), 'diversifiers':(.003,[0,0,0,.003,.022,.006],.018), 'listed_private':(.006,[.036,-.003,.013,.003,0,-.004],.025)}
    data={}
    for group,names in GROUPS.items():
        mu,beta,noise=pars[group]
        for i,name in enumerate(names):
            beta_i=np.array(beta)*(0.65+.7*i/max(1,len(names)-1))
            if name=='BTAL': beta_i=np.array([-.025,0,0,0,.005,0])
            if name=='TAIL': beta_i=np.array([-.025,.012,0,0,0,0]); mu_i=-.001
            else: mu_i=mu
            if name=='UUP': beta_i=np.array([0,0,0,0,0,.024])
            if name=='GLD': beta_i=np.array([0,-.006,0,.023,0,-.008])
            data[name]=mu_i+z@beta_i+rng.normal(0,noise,months)
    idx=pd.date_range('2006-01-31',periods=months,freq=pd.offsets.MonthEnd())
    return pd.DataFrame(data,index=idx),pd.Series(.003+.035*z[:,1]+.006*z[:,3],index=idx,name='liability_return')


def walk(r,mandate,method,liability=None,lookback=60,cost_bps=15,estimation=None):
    validate(r)
    if lookback<12 or len(r)<=lookback or cost_bps<0: raise ValueError('Invalid backtest inputs')
    w=np.zeros(len(ASSETS)); records=[]; allocations=[]
    for i in range(lookback,len(r)):
        t=0.
        if (i-lookback)%3==0:
            start=0 if estimation=='auto' else i-lookback
            target=allocate(r.iloc[start:i],mandate,method,None if liability is None else liability.iloc[start:i],estimation=estimation)
            t=np.abs(target-w).sum(); w=target
        allocations.append(w.copy()); x=r.iloc[i].to_numpy(); gross=w@x
        if t*cost_bps/10000>=1: raise ValueError('Costs exceed assets')
        records.append(((1-t*cost_bps/10000)*(1+gross)-1,t))
        w=w*(1+x)/(1+gross)
    idx=r.index[lookback:]
    return pd.DataFrame(records,index=idx,columns=['net','turnover']),pd.DataFrame(allocations,index=idx,columns=ASSETS)


def stress(w):
    # One-period sleeve shocks, not historical events or maximum possible losses.
    scenarios={'equity_crash':[0,-.30,.06,-.12,-.15,.03,-.35], 'inflation_rates':[0,-.15,-.12,-.08,.12,.06,-.20], 'credit_crunch':[0,-.18,.04,-.22,-.12,.01,-.30], 'liquidity_shock':[0,-.22,-.04,-.15,-.18,-.08,-.30]}
    return {k:float((G@w)@v) for k,v in scenarios.items()}


def funding(asset_returns,liability_returns,initial=.90):
    """Marked funding ratio, zero external flows; no actuarial cash-flow model."""
    if not asset_returns.index.equals(liability_returns.index) or initial<=0 or (liability_returns<=-1).any(): raise ValueError('Invalid funding inputs')
    return initial*((1+asset_returns)/(1+liability_returns)).cumprod()


def main():
    p=argparse.ArgumentParser(); p.add_argument('--returns-csv'); p.add_argument('--liability-csv'); p.add_argument('--out',default='institutional_outputs'); a=p.parse_args()
    if a.returns_csv:
        r=pd.read_csv(a.returns_csv,index_col=0,parse_dates=True); l=None
        if a.liability_csv: l=pd.read_csv(a.liability_csv,index_col=0,parse_dates=True)['liability_return']
    else: r,l=simulate()
    validate(r)
    if list(r.columns)!=ASSETS or len(r)<=60 or np.any(np.diff(r.index.to_period('M').asi8)!=1): raise ValueError('Need consecutive monthly returns in documented column order, >60 months')
    if l is not None and (not l.index.equals(r.index) or not np.isfinite(l).all() or (l<=-1).any()): raise ValueError('Invalid liability series')
    out=Path(a.out); out.mkdir(parents=True,exist_ok=True); rows=[]; groups=[]; scenarios=[]; nets={}
    for mandate in POLICY:
        methods=METHODS+(['surplus'] if mandate=='pension' and l is not None else [])
        for method in methods:
            b,w=walk(r,mandate,method,l); name=mandate+'/'+method; nets[name]=b.net
            row={'mandate':mandate,'method':method,**metrics(b.net,b.turnover,r.BIL.loc[b.index])}
            if l is not None and mandate=='pension':
                fund=funding(b.net,l.loc[b.index]); row.update(funding_end=float(fund.iloc[-1]),funding_min=float(min(.90,fund.min())),surplus_vol=float((b.net-l.loc[b.index]).std()*np.sqrt(12)))
            latest=allocate(r.iloc[-60:],mandate,method,None if l is None else l.iloc[-60:]); rc=risk_contributions(latest,covariance(r.iloc[-60:].to_numpy()))
            row['avg_cash']=float(w.BIL.mean()); rows.append(row)
            for g,v,rr in zip(GROUPS,G@latest,rc): groups.append({'mandate':mandate,'method':method,'sleeve':g,'weight':v,'risk_share':rr})
            scenarios.append({'mandate':mandate,'method':method,**stress(latest)})
    pd.DataFrame(rows).to_csv(out/'metrics.csv',index=False); pd.DataFrame(groups).to_csv(out/'allocation.csv',index=False); pd.DataFrame(scenarios).to_csv(out/'stress.csv',index=False); pd.DataFrame(nets).to_csv(out/'net_returns.csv')
    (out/'metadata.json').write_text(json.dumps({'source':'external user-supplied returns, unverified' if a.returns_csv else 'seeded synthetic asset and liability proxies; not historical','assets':len(ASSETS),'sleeves':list(GROUPS),'oos_months':len(r)-60,'cost_bps':15,'rebalance_months':3,'lookback_months':60},indent=2)+'\n')
    print(pd.DataFrame(rows).round(4).to_string(index=False))

if __name__=='__main__': main()
