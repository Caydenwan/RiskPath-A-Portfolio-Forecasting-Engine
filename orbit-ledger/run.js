#!/usr/bin/env node
/* ORBIT model-only paper ledger. No brokerage, real money, secret credentials, paid models.
   AM: snapshot completed previous-session factors. PM: verify today's daily close/volume,
   fill yesterday's confirmed signal at NEXT OPEN, mark-to-market, append audit entries.
   Yahoo Finance is unofficial; missing data -> no synthetic fills. */
'use strict';
const fs=require('node:fs');const path=require('node:path');
const E=require('./engine.js');
const DATA=path.resolve(__dirname,'data/ledger.json');
const CANDIDATES=['MSFT','NVDA','AMZN','GOOGL','AAPL','JPM','SMH'];
const INITIAL=10000,SLIPPAGE=.0005,MAX_POSITIONS=3,MODEL=E.VERSION;
const n=Number.isFinite;
function nowNY(date=new Date()){
 const parts=new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',weekday:'short',hour12:false}).formatToParts(date);
 const d=Object.fromEntries(parts.map(x=>[x.type,x.value]));return {date:`${d.year}-${d.month}-${d.day}`,hour:Number(d.hour),minute:Number(d.minute),weekday:d.weekday};
}
function empty(){return {schemaVersion:2,modelVersion:MODEL,status:'not_started',initialCapital:INITIAL,slippageBps:5,executionModel:'Close confirmation -> following session open; OHLC stop first when ambiguous',riskPerTradePct:.5,maxPositionPct:20,maxPositions:MAX_POSITIONS,startDate:null,updatedAt:null,cash:INITIAL,positions:[],orders:[],signals:[],trades:[],equityHistory:[],lastSnapshotDate:null,lastMarkDate:null,warnings:[]};}
function load(){return fs.existsSync(DATA)?JSON.parse(fs.readFileSync(DATA,'utf8')):empty()}
function persist(d){fs.mkdirSync(path.dirname(DATA),{recursive:true});fs.writeFileSync(DATA,JSON.stringify(d,null,2)+'\n');}
async function chart(symbol,range='1y'){
 let last='Unavailable';for(const host of ['query1.finance.yahoo.com','query2.finance.yahoo.com']){
  try{const r=await fetch(`https://${host}/v8/finance/chart/${encodeURIComponent(symbol)}?range=${range}&interval=1d`,{headers:{'User-Agent':'Mozilla/5.0 (compatible; ORBITPaperLedger/4.0)','Accept':'application/json'},signal:AbortSignal.timeout(8000)});
   if(!r.ok){last='Yahoo HTTP '+r.status;continue;}
   const d=(await r.json())?.chart?.result?.[0];if(!d?.timestamp?.length)throw Error('No bars');const q=d.indicators?.quote?.[0]||{},adj=d.indicators?.adjclose?.[0]?.adjclose||[];
   const candles=d.timestamp.map((t,i)=>({t,o:q.open?.[i],h:q.high?.[i],l:q.low?.[i],c:q.close?.[i],a:Number.isFinite(adj[i])?adj[i]:null,v:q.volume?.[i]})).filter(x=>n(x.t)&&n(x.c)&&n(x.o)&&n(x.h)&&n(x.l));
   if(candles.length<210)throw Error('Insufficient data');return {candles,meta:d.meta};
  }catch(e){last=e.message||'Fetch error';}}
 throw Error(symbol+': '+last);
}
async function vix(){let error='Unavailable';for(const host of ['query1.finance.yahoo.com','query2.finance.yahoo.com']){
 try{const r=await fetch(`https://${host}/v8/finance/chart/%5EVIX?range=5d&interval=1d`,{headers:{'User-Agent':'Mozilla/5.0','Accept':'application/json'},signal:AbortSignal.timeout(8000)});
  if(!r.ok){error='HTTP '+r.status;continue;}const d=(await r.json())?.chart?.result?.[0];const v=d?.meta?.regularMarketPrice;if(!n(v))throw Error('No VIX');return v;
 }catch(e){error=e.message||'Provider failed'}}throw Error('VIX '+error);
}
async function universe(){const assets=[...new Set(['SPY',...CANDIDATES])],data={};let k=0;const errors=[];
 async function run(){while(k<assets.length){const s=assets[k++];try{data[s]=await chart(s)}catch(e){errors.push(String(e.message||e));}}}
 await Promise.all(Array.from({length:Math.min(4,assets.length)},run));if(errors.length)throw Error('Incomplete OHLC universe: '+errors.join('; '));return data;
}
const lastCompleted=(raw,at)=>E.completeDaily(raw,at).at(-1);
function scoreIdeas(data,vol,at){const spy=E.completeDaily(data.SPY.candles,at);return CANDIDATES.map(s=>E.idea(s,E.completeDaily(data[s].candles,at),spy,vol)).filter(Boolean).sort((a,b)=>b.score-a.score||a.symbol.localeCompare(b.symbol)).slice(0,3);}
function warn(d,message){d.warnings.push({date:new Date().toISOString(),message});d.warnings=d.warnings.slice(-50);}
async function morning(d,clock,at){if(d.lastSnapshotDate===clock.date)return false;
 const vol=await vix(),data=await universe();const spy=lastCompleted(data.SPY.candles,at);
 if(!spy||E.nyDayUTC(spy.t)>=clock.date)throw Error('Morning snapshot must use prior completed bar');
 const scores=scoreIdeas(data,vol,at);if(!scores.length)throw Error('No factors verified: snapshot withheld');
 const snap=scores.map(x=>({id:clock.date+'-'+x.symbol,date:clock.date,symbol:x.symbol,model:MODEL,action:x.action,score:x.score,entry:+x.entry.toFixed(4),stop:+x.stop.toFixed(4),target:+x.target.toFixed(4),atr:+x.atr.toFixed(4),priceDate:x.priceDate,volumeRatio:Number.isFinite(x.volRatio)?+x.volRatio.toFixed(3):null,breakdown:x.breakdown,status:'published',generatedAt:new Date(at).toISOString()}));
 d.signals.push(...snap);d.lastSnapshotDate=clock.date;d.startDate=d.startDate||clock.date;d.status='active';d.updatedAt=new Date(at).toISOString();
 console.log('Morning snapshot',clock.date,snap.map(s=>s.symbol+':'+s.action).join(','));return true;
}
function addTrade(d,t){d.trades.push(t)}
function exit(d,pos,fill,date,reason){const exitPrice=Math.max(.01,fill)*(1-SLIPPAGE),net=pos.qty*exitPrice;
 d.cash+=net;const pnl=net-pos.qty*pos.entryPaid;
 const trade=d.trades.find(t=>t.id===pos.id);if(trade){trade.exitPrice=exitPrice;trade.exitDate=date;trade.status='closed';trade.closedAt=date;trade.reason=reason;trade.pnl=+pnl.toFixed(4);}
 d.positions=d.positions.filter(p=>p.id!==pos.id);console.log('Exit',pos.symbol,reason,'pnl',pnl.toFixed(2));
}
function mark(d,date,spy,prices){let value=d.cash;for(const p of d.positions){const px=prices[p.symbol];if(!n(px))throw Error('Cannot value '+p.symbol);value+=p.qty*px;}
 if(!n(value)||value<=0)throw Error('Invalid equity');
 if(d.equityHistory.some(r=>r.date===date))throw Error('This date already marked, ledger is append-only');
 d.equityHistory.push({date,equity:+value.toFixed(4),cash:+d.cash.toFixed(4),openPositions:d.positions.length,spyClose:spy});d.lastMarkDate=date;d.updatedAt=new Date().toISOString();
}
async function closing(d,clock,at){if(d.lastMarkDate===clock.date)return false;
 const data=await universe(),today=clock.date,bars={};for(const [s,item] of Object.entries(data))bars[s]=lastCompleted(item.candles,at);
 // Also read any positions outside the fixed universe (defensive; no missing prices invented).
 for(const p of d.positions)if(!bars[p.symbol])bars[p.symbol]=lastCompleted((await chart(p.symbol)).candles,at);
 if(!bars.SPY||E.nyDayUTC(bars.SPY.t)!==today){console.log('No completed SPY market bar for',today,'— possible holiday or data delay');return false;}
 const market={};for(const [s,bar] of Object.entries(bars))if(bar&&E.nyDayUTC(bar.t)===today)market[s]=bar;
 if(d.positions.some(p=>!market[p.symbol]))throw Error('Held security missing complete EOD bar');
 // First, open orders confirmed from a PRIOR trading day, fill at today's open.
 const pending=[...d.orders];d.orders=[];
 for(const o of pending){const bar=market[o.symbol];if(!bar){d.orders.push(o);continue;}if(o.confirmedAt>=today){d.orders.push(o);continue;}
  if(d.positions.length>=MAX_POSITIONS||d.positions.some(p=>p.symbol===o.symbol))continue;
  const open=bar.o;if(!n(open)||open<=o.stop||open>o.entry+o.atr)continue; // no fill if overnight gap destroys planned R/R
  const paid=open*(1+SLIPPAGE),riskUnit=paid-o.stop,budget=(d.initialCapital*.005);
  const shares=Math.max(0,Math.min(Math.floor(budget/riskUnit),Math.floor(d.initialCapital*.20/paid),Math.floor(d.cash/paid)));
  if(!shares)continue;const entryPaid=paid,stop=o.stop,target=paid+1.5*(paid-stop);
  const id=o.signalId+'-'+today;d.cash-=shares*entryPaid;
  d.positions.push({id,symbol:o.symbol,qty:shares,entryPaid,entryDate:today,stop,target,signalId:o.signalId});
  addTrade(d,{id,signalId:o.signalId,date:today,symbol:o.symbol,status:'open',entry:entryPaid,qty:shares,stop,target,model:MODEL,slippageBps:5});
  console.log('Enter',o.symbol,'shares',shares,'at next open',paid.toFixed(2));
 }
 // Exits use OHLC; stop takes priority if stop+target both touched (pessimistic).
 for(const p of [...d.positions]){const bar=market[p.symbol];if(!bar)throw Error('No bar for '+p.symbol);
  const stopHit=bar.l<=p.stop,targetHit=bar.h>=p.target;
  if(stopHit){exit(d,p,Math.min(p.stop,bar.o),today,'stop / conservative OHLC ordering');}
  else if(targetHit){exit(d,p,Math.min(p.target,bar.o>p.target?bar.o:p.target),today,'target');}
 }
 // At close, confirm prior morning BUY IF signals only if intraday close/volume data meet rules.
 const same=d.signals.filter(x=>x.date===today&&x.action==='BUY IF');for(const sig of same){
  const bar=market[sig.symbol],prev=data[sig.symbol]?.candles;if(!bar||!prev)continue;
  const old=E.completeDaily(prev.filter(x=>E.nyDayUTC(x.t)<today),at),trailing=old.slice(-20).map(x=>x.v).filter(n);const ratio=trailing.length>=15&&E.mean(trailing)>0?bar.v/E.mean(trailing):NaN;
  sig.verifiedAtClose=ratio>=1.2&&bar.c>=sig.entry&&bar.h>=sig.entry;
  sig.sessionVolumeRatio=n(ratio)?+ratio.toFixed(3):null;
  if(!sig.verifiedAtClose){sig.status='not_triggered';continue;}
  if(d.positions.some(p=>p.symbol===sig.symbol)||d.orders.some(o=>o.symbol===sig.symbol)){sig.status='duplicate_skipped';continue;}
  sig.status='confirmed_for_next_open';d.orders.push({signalId:sig.id,symbol:sig.symbol,confirmedAt:today,entry:sig.entry,stop:sig.stop,atr:sig.atr});
 }
 // No mark on missing or stale EOD quotes.
 const prices={};for(const [s,bar] of Object.entries(market))prices[s]=bar.c;
 mark(d,today,bars.SPY.c,prices);d.status='active';if(!d.startDate)d.startDate=today;
 console.log('Marked equity',d.equityHistory.at(-1).equity,'orders for next session',d.orders.length);return true;
}
async function main(){const at=Date.now(),clock=nowNY(new Date(at)),manual=process.argv.find(x=>x.startsWith('--mode='))?.split('=')[1]||'auto';
 if(!['Mon','Tue','Wed','Thu','Fri'].includes(clock.weekday)){console.log('Weekend, no run');return;}
 const isMorning=clock.hour===8||clock.hour===9&&clock.minute<25,isClose=clock.hour>=17&&clock.hour<20;
 const mode=manual!=='auto'?manual:isMorning?'scan':isClose?'close':'skip';
 if(mode==='skip'){console.log('Outside tracked ET session',clock);return}
 if(mode==='scan'&&!isMorning||mode==='close'&&!isClose){console.log('Not inside authorized time for',mode);return}
 const d=load();if(d.modelVersion!==MODEL)throw Error('Immutable ledger model mismatch; migration required');
 const did=mode==='scan'?await morning(d,clock,at):await closing(d,clock,at);
 if(did)persist(d);else console.log('No update required');
}
main().catch(e=>{console.error('Paper ledger data integrity guard:',e.message);process.exitCode=1});
