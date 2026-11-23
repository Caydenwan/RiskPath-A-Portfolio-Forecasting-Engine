/* ORBIT Engine v4.0: deterministic, explainable rules; not a proprietary model. */
(function(root,factory){ const e=factory();if(typeof module!=='undefined'&&module.exports)module.exports=e;root.ORBIT_ENGINE=e; })(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const VERSION='4.0.0';
 const n=x=>Number.isFinite(x),sum=a=>a.reduce((v,x)=>v+x,0),mean=a=>a.length?sum(a)/a.length:NaN;
 const quant=(a,p)=>{const s=[...a].filter(n).sort((x,y)=>x-y);if(!s.length)return NaN;const z=(s.length-1)*p,i=Math.floor(z),d=z-i;return s[i]+(s[Math.min(s.length-1,i+1)]-s[i])*d};
 const std=a=>a.length>1?Math.sqrt(sum(a.map(x=>(x-mean(a))**2))/(a.length-1)):NaN;
 const nyDay=ts=>new Intl.DateTimeFormat('en-CA',{timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(ts*1000));
 const nyDayUTC=ts=>{const p=new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date(ts*1000));const v=Object.fromEntries(p.map(x=>[x.type,x.value]));return `${v.year}-${v.month}-${v.day}`};
 function completeDaily(rows,now=Date.now()){
  const parts=new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',hour12:false}).formatToParts(new Date(now));const x=Object.fromEntries(parts.map(y=>[y.type,y.value]));const today=`${x.year}-${x.month}-${x.day}`;const completed=Number(x.hour)>=17;
  return (rows||[]).filter(r=>n(r.c)&&n(r.t)&&((nyDayUTC(r.t)<today)||(nyDayUTC(r.t)===today&&completed)));
 }
 function close(a){return a.filter(x=>n(x.c)).map(x=>x.c)}
 function sma(a,d){return a.length>=d?mean(a.slice(-d)):NaN}
 function rsi(a,p=14){if(a.length<p+1)return NaN;let up=0,down=0;for(let i=a.length-p;i<a.length;i++){const z=a[i]-a[i-1];up+=Math.max(z,0);down+=Math.max(0,-z)}return down===0?(up===0?50:100):100-100/(1+up/down)}
 function atr(rows,p=14){if(rows.length<p+1)return NaN;let t=0;for(let i=rows.length-p;i<rows.length;i++){const q=rows[i],r=rows[i-1];t+=Math.max(q.h-q.l,Math.abs(q.h-r.c),Math.abs(q.l-r.c));}return t/p;}
 function pctReturn(a,p){return a.length>p&&a.at(-p-1)>0?a.at(-1)/a.at(-p-1)-1:NaN}
 function factors(rows,spyRows){let c=close(rows),spy=close(spyRows||[]);if(c.length<205||spy.length<65)return null;
  const last=rows.at(-1),ma20=sma(c,20),ma50=sma(c,50),ma200=sma(c,200),r=rsi(c),a=atr(rows),prior=rows.slice(-21,-1);
  if(!n(a)||a<=0||!n(r)||!prior.length)return null;
  const high20=Math.max(...prior.map(x=>x.h)),low20=Math.min(...prior.map(x=>x.l));
  const r63=pctReturn(c,63),spy63=pctReturn(spy,63),relative=(1+r63)/(1+spy63)-1;
  const vols=rows.slice(-21,-1).map(x=>x.v).filter(x=>n(x)&&x>=0),avgVolume=vols.length>=15?mean(vols):NaN;
  const volRatio=n(avgVolume)&&avgVolume>0&&n(last.v)?last.v/avgVolume:NaN;
  const daily=[];for(let i=c.length-63;i<c.length;i++)daily.push(c[i]/c[i-1]-1);const annVol=std(daily)*Math.sqrt(252);
  const trendParts=[last.c>ma20?8:0,ma20>ma50?8:0,last.c>ma200?8:0,ma50>ma200?6:0];const trend=sum(trendParts);
  const momentum=relative>.10?25:relative>.05?20:relative>0?14:relative>-.05?7:0;
  const closeNear=last.c>=high20?12:last.c>=high20-.5*a?8:last.c>=high20-1*a?4:0;
  const volumeScore=!n(volRatio)?0:volRatio>=1.5?8:volRatio>=1.2?6:volRatio>=1?3:0;
  const breakout=closeNear+volumeScore;
  const volScore=annVol<.25?12:annVol<.4?8:annVol<.6?4:0;
  const rsiScore=r>=45&&r<=65?8:r>=35&&r<=70?4:0;
  const extension=(last.c-ma20)/a;
  const extScore=Math.abs(extension)<1?5:Math.abs(extension)<2?3:0;
  const quality=volScore+rsiScore+extScore;
  const score=trend+momentum+breakout+quality;
  return {score,breakdown:{trend,momentum,breakout,quality},close:last.c,ma20,ma50,ma200,rsi:r,atr:a,high20,low20,volRatio,relative63:relative,annVol,priceDate:nyDayUTC(last.t),lastTime:last.t,volumeConfirmed:volRatio>=1.2,extension};
 }
 function idea(symbol,rows,spyRows,vix){const f=factors(rows,spyRows);if(!f)return null;
  const entry=Math.max(f.high20+.1*f.atr,f.close+.15*f.atr),stop=entry-1.6*f.atr,target=entry+2.4*f.atr;
  const vixOk=n(vix)&&vix<30,vixKnown=n(vix),technical=f.score>=68&&f.close>f.ma50&&f.ma50>f.ma200&&f.rsi<72;
  let action='WAIT',reason='评分或趋势尚未达到候选阈值';if(!vixKnown)reason='VIX 数据缺失，不能放行新交易';else if(vix>=30)reason='VIX ≥ 30，先控制新仓位风险';else if(technical){action='BUY IF';reason='多因子候选；需突破并确认成交量';}else if(f.close<f.ma200&&f.ma20<f.ma50){action='REDUCE IF';reason='跌破长期均线且趋势转弱';}
  const trigger=`突破 $${entry.toFixed(2)} 且量比 ≥ 1.2（完整日线）`;
  return {symbol,...f,entry,stop,target,rr:1.5,action,reason,trigger,techPass:technical,vixPass:vixOk,model:VERSION};
 }
 function weights(level){const t=Math.max(0,Math.min(1,(Number(level)-1)/9));const growth=.05+.90*t,def=1-growth;
  const safe={BIL:.78,IEF:.10,TIP:.07,GLD:.05};const active={SPY:.44,QQQ:.14,EFA:.15,EEM:.06,VNQ:.04,GLD:.13,IEF:.04};
  const all=new Set([...Object.keys(safe),...Object.keys(active)]);const obj={};for(const s of all)obj[s]=def*(safe[s]||0)+growth*(active[s]||0);return obj;
 }
 function monthlyReturns(series,required){const keys=required||Object.keys(series);if(!keys.length)return null;
  const maps={};for(const s of keys){let rows=series[s]||[];const m={};for(const c of rows){const v=n(c.a)?c.a:NaN;if(n(v)&&v>0)m[new Date(c.t*1000).toISOString().slice(0,7)]=v;}maps[s]=m;}
  const months=Object.keys(maps[keys[0]]).filter(m=>keys.every(s=>n(maps[s][m]))).sort();
  // Monthly Yahoo candles include the unfinished current month. Exclude it.
  const today=new Date();const z=new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',month:'2-digit',year:'numeric'}).formatToParts(today),a=Object.fromEntries(z.map(x=>[x.type,x.value])),current=`${a.year}-${a.month}`;
  const done=months.filter(m=>m<current);if(done.length<37)return null;
  const values=[];for(let i=1;i<done.length;i++){const mo=done[i],prev=done[i-1];const ret={};for(const s of keys){ret[s]=maps[s][mo]/maps[s][prev]-1;}values.push(ret)}return {months:done,returns:values,source:'Yahoo adjusted close; dividend/split-adjusted proxy'};
 }
 function rand(seed){let s=seed>>>0;return()=>{s=(1664525*s+1013904223)>>>0;return s/4294967296}}
 function bootstrap({series,level=4,capital=10000,monthly=300,months=60,nPaths=3000,block=3,seed=20261123}){
  const w=weights(level),assets=Object.keys(w).filter(s=>w[s]>.0001),hist=monthlyReturns(series,assets);
  if(!hist)throw Error('需要至少 36 个月完整且含分红调整的 ETF 月度行情');
  const pr=hist.returns.map(r=>assets.reduce((total,s)=>total+w[s]*r[s],0));if(pr.length<36)throw Error('历史月收益不足');
  const n=nPaths, rng=rand(seed),out=[],dd=[],initial=capital+monthly*months;
  for(let i=0;i<n;i++){let v=capital,peak=1,unit=1,maxDD=0,at=0,offset=block;
    for(let j=0;j<months;j++){if(offset>=block){at=Math.floor(rng()*Math.max(1,pr.length-block+1));offset=0;}
      const rr=pr[Math.min(pr.length-1,at+offset++)];v=v*(1+rr)+monthly;
      unit*=Math.max(.01,1+rr);peak=Math.max(peak,unit);maxDD=Math.max(maxDD,1-unit/peak);
    }
    out.push(v);dd.push(maxDD);
  }
  const threshold=quant(pr,.05),tail=pr.filter(x=>x<=threshold);const lossProbability=out.filter(v=>v<initial).length/n;
  return {model:VERSION,weights:w,historicalMonths:pr.length,dates:[hist.months[0],hist.months.at(-1)],nPaths:n,block,
    capital,contributed:initial,p5:quant(out,.05),p50:quant(out,.5),p95:quant(out,.95),lossProbability,
    annVol:std(pr)*Math.sqrt(12),historicalMonthlyCVaR95:mean(tail),historicalMonthlyVaR95:threshold,
    medianMaxDD:quant(dd,.5),p95MaxDD:quant(dd,.95),monthlyMean:mean(pr),source:hist.source};
 }
 function perf(ledger){const history=ledger?.equityHistory||[],trades=(ledger?.trades||[]).filter(x=>x.status==='closed');if(!history.length)return null;
  const first=history[0],last=history.at(-1),equity=last.equity||0,base=Number(ledger.initialCapital)||10000;
  const ret=equity/base-1,sp=first.spyClose>0&&last.spyClose>0?last.spyClose/first.spyClose-1:NaN;
  let peak=base,mdd=0;for(const x of history){peak=Math.max(peak,x.equity);mdd=Math.max(mdd,1-x.equity/peak)}
  return {days:history.length,equity,returnPct:ret*100,benchmarkPct:sp*100,alphaPct:n(sp)?(ret-sp)*100:NaN,maxDDPct:mdd*100,closed:trades.length,wins:trades.filter(x=>x.pnl>0).length,winRate:trades.length?100*trades.filter(x=>x.pnl>0).length/trades.length:null,pnl:equity-base};
 }
 return{VERSION,n,mean,quant,std,nyDayUTC,completeDaily,sma,rsi,atr,factors,idea,weights,monthlyReturns,bootstrap,perf};
});
