import { get, put } from '@vercel/blob';
import { createHash, timingSafeEqual } from 'node:crypto';
const ASSETS=["BIL","VTI","IWM","QQQ","VTV","VEA","VWO","SHY","IEF","TLT","TIP","BNDX","LQD","HYG","EMB","BKLN","GLD","DBC","VNQ","IGF","DBMF","KMLM","BTAL","QAI","UUP","TAIL","PSP","BIZD"];
const PATH='riskpath/monthly/latest.json';
const delay=ms=>new Promise(r=>setTimeout(r,ms));
function sameSecret(actual,expected){
  if(typeof expected!=='string'||expected.length<24||typeof actual!=='string'||actual.length>512)return false;
  const digest=s=>createHash('sha256').update(s).digest();
  return timingSafeEqual(digest(actual),digest(expected));
}
function monthNo(s){const a=s.match(/^(\d{4})-(0[1-9]|1[0-2])/);if(!a)throw Error('Invalid monthly date');return +a[1]*12+(+a[2]-1)}
function monthEnd(n){return new Date(Date.UTC(Math.floor(n/12),n%12+1,0)).toISOString().slice(0,10)}
function alignMarket(series,assets,cutoff){
  const end=monthNo(cutoff)-1,issues=[],maps=assets.map(a=>{
    const m=new Map(),bad=new Set();
    for(const v of series[a]||[]){
      let n;try{n=monthNo(String(v.datetime||''))}catch(e){issues.push({asset:a,month:'unknown',reason:'invalid date'});continue}
      if(n>end)continue;
      const p=Number(v.close);
      if(v.close==null||String(v.close).trim()===''||!Number.isFinite(p)||p<=0){issues.push({asset:a,month:monthEnd(n),reason:'invalid price'});continue}
      if(bad.has(n))continue;
      if(m.has(n)){
        if(Math.abs(m.get(n)-p)<=1e-10*Math.max(1,Math.abs(p),Math.abs(m.get(n)))){issues.push({asset:a,month:monthEnd(n),reason:'identical duplicate removed'});continue}
        m.delete(n);bad.add(n);issues.push({asset:a,month:monthEnd(n),reason:'conflicting prices excluded'});continue
      }
      m.set(n,p);
    }
    if(!m.size)throw Error(a+' has no valid completed monthly adjusted prices. Try reconnecting or import a verified CSV.');
    return m
  });
  const missing=n=>assets.filter((a,i)=>!maps[i].has(n));
  const latestMissing=missing(end);
  if(latestMissing.length)throw Error('Latest completed month '+monthEnd(end)+' unavailable for '+latestMissing.join(', ')+'. No prices filled or substituted.');
  let start=end;while(missing(start-1).length===0)start--;
  const count=end-start,stopping=missing(start-1),oldestCommon=Math.max(...maps.map(m=>Math.min(...m.keys())));
  if(count<36)throw Error('Only '+count+' consecutive common returns through '+monthEnd(end)+'. Missing/conflicting data for '+stopping.join(', ')+' at '+monthEnd(start-1)+'. Need at least 36; reconnect or import verified CSV.');
  const rows=['date,'+assets.join(',')];
  for(let n=start+1;n<=end;n++){const vals=maps.map(m=>m.get(n)/m.get(n-1)-1);if(vals.some(v=>!Number.isFinite(v)||v<=-1))throw Error('Invalid return at '+monthEnd(n));rows.push(monthEnd(n)+','+vals.join(','))}
  return {csv:rows.join('\n')+'\n',count,first:monthEnd(start+1),last:monthEnd(end),cutoff,issues,shortened:start>oldestCommon,stopping,stopMonth:monthEnd(start-1)};
}

function cutoff(){return new Date().toISOString().slice(0,7)}
async function readHistory(){
  const blob=await get(PATH,{access:'private',useCache:false});
  if(!blob)return null;
  if(blob.statusCode!==200||!blob.stream)throw Error('Private storage unavailable');
  const data=await new Response(blob.stream).json();
  if(typeof data.csv!=='string'||!Number.isInteger(data.count)||data.count<36||!Array.isArray(data.issues))throw Error('Stored dataset failed validation');
  return data;
}
async function requestSeries(symbol,key){
  const u=new URL('https://api.twelvedata.com/time_series');
  for(const [k,v] of Object.entries({symbol,interval:'1month',outputsize:'360',adjust:'all',country:'United States',apikey:key}))u.searchParams.set(k,v);
  let d;
  try{
    const r=await fetch(u,{signal:AbortSignal.timeout(15000),cache:'no-store'});
    d=await r.json();
    if(r.status===429||Number(d.code)===429)throw Error('rate limit');
    if(!r.ok||d.status!=='ok'||!Array.isArray(d.values)||d.meta?.symbol!==symbol||d.meta?.currency!=='USD'||d.meta?.interval!=='1month')throw Error('invalid response');
  }catch(e){throw Error(symbol+' market history unavailable or rate limited. Previous snapshot retained.')}
  return d.values;
}
function validateImport(data){
  if(!data||typeof data.csv!=='string'||data.csv.length>500000)throw Error('Invalid private CSV');
  const rows=data.csv.trim().split(/\r?\n/),header=rows.shift();
  if(header!=='date,'+ASSETS.join(',')||rows.length<36||rows.length>360)throw Error('Invalid private CSV columns or sample length');
  let prev=null;const current=monthNo(cutoff());
  for(const line of rows){const cols=line.split(','),date=cols.shift(),n=monthNo(date);
    if(cols.length!==ASSETS.length||date!==monthEnd(n)||n>=current||(prev!==null&&n!==prev+1)||cols.some(v=>v.trim()===''||!Number.isFinite(Number(v))||Number(v)<=-1))throw Error('Invalid private CSV month or return');
    prev=n;
  }
  const last=rows.at(-1).split(',')[0],first=rows[0].split(',')[0],c=new Date(Date.UTC(Math.floor((prev+1)/12),(prev+1)%12,1)).toISOString().slice(0,7);
  return {csv:[header,...rows].join('\n')+'\n',count:rows.length,first,last,cutoff:c,issues:[],shortened:false,source:'User-imported private browser dataset; provenance not independently verified',retrievedAt:new Date().toISOString(),cloud:true};
}
async function saveSnapshot(data){
  const payload=JSON.stringify(data);
  await put('riskpath/monthly/'+data.cutoff+'.json',payload,{access:'private',allowOverwrite:true,contentType:'application/json',cacheControlMaxAge:60});
  await put(PATH,payload,{access:'private',allowOverwrite:true,contentType:'application/json',cacheControlMaxAge:60});
}

async function refresh(existing){
  const month=cutoff();
  if(existing?.cutoff===month)return {data:existing,updated:false};
  const key=process.env.RISKPATH_TWELVE_DATA_KEY;
  if(!key)throw Error('Private market API credential not configured');
  const series={};
  for(let i=0;i<ASSETS.length;i+=7){
    if(i)await delay(62000);
    const batch=ASSETS.slice(i,i+7);
    const rows=await Promise.all(batch.map(a=>requestSeries(a,key)));
    batch.forEach((a,j)=>series[a]=rows[j]);
  }
  const data={...alignMarket(series,ASSETS,month),retrievedAt:new Date().toISOString(),source:'Twelve Data · private server snapshot',cloud:true};
  // Archive each successful monthly snapshot, then replace the latest pointer. No public redistribution.
  await saveSnapshot(data);
  return {data,updated:true};
}
export default async function handler(req,res){
  res.setHeader('Cache-Control','private, no-store');
  res.setHeader('X-Content-Type-Options','nosniff');
  const token=String(req.headers.authorization||'').replace(/^Bearer /,'');
  const cron=sameSecret(token,process.env.CRON_SECRET);
  if(!cron&&!sameSecret(token,process.env.RISKPATH_OWNER_TOKEN))return res.status(401).json({error:'Private access not configured or unauthorized'});
  if((cron&&req.method!=='GET')||(!cron&&!['GET','POST'].includes(req.method)))return res.status(405).json({error:'Method not allowed'});
  try{
    const existing=await readHistory();
    if(!cron&&req.method==='GET')return res.status(200).json({data:existing,needsUpdate:existing?.cutoff!==cutoff()});
    if(!cron&&req.method==='POST'&&req.body?.action==='import'){
      const imported=validateImport(req.body.data);
      if(existing&&existing.cutoff>=imported.cutoff)return res.status(200).json({data:existing,updated:false});
      await saveSnapshot(imported);return res.status(200).json({data:imported,updated:true});
    }
    const result=await refresh(existing);
    if(cron)return res.status(200).json({updated:result.updated,coverage:result.data.last});
    return res.status(200).json(result);
  }catch(e){
    // Never return provider URLs, tokens, headers or raw exceptions.
    const m=String(e?.message||'');
    const safe=/^(Invalid private CSV|Private market API credential not configured|[A-Z]{2,5} market history unavailable or rate limited\. Previous snapshot retained\.|Latest completed month |Only \d+ consecutive common returns|[A-Z]{2,5} has no valid completed monthly adjusted prices)/.test(m)?m:'Private refresh failed. Previous snapshot retained.';
    return res.status(503).json({error:safe});
  }
}
