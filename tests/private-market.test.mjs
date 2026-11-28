import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {test} from 'node:test';

// Isolated storage mock: never touches production or the market provider.
let source=await readFile(new URL('../web/api/private-market.mjs',import.meta.url),'utf8');
source=source.replace("import { get, put } from '@vercel/blob';",'const get=async()=>null; const put=async()=>{throw Error("Unexpected write")};');
const {default:handler}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
process.env.RISKPATH_OWNER_TOKEN='local-test-owner-secret-not-real';
process.env.CRON_SECRET='local-test-cron-secret-not-real';
const origin='https://riskpath.example';
async function request(method='GET',headers={},body){
  const result={headers:{}};
  const res={setHeader(k,v){result.headers[k]=v},status(n){result.status=n;return this},json(data){result.data=data;return this}};
  await handler({method,headers:{host:'riskpath.example',origin,...headers},body},res);
  return result;
}
test('anonymous cannot read or trigger refresh',async()=>{
  assert.equal((await request()).status,401);
  assert.equal((await request('POST',{}, {action:'refresh'})).status,401);
});
test('owner session is persistent, private, and read-only for refresh',async()=>{
  const login=await request('POST',{authorization:'Bearer '+process.env.RISKPATH_OWNER_TOKEN},{action:'login'});
  assert.equal(login.status,200);
  const cookie=login.headers['Set-Cookie'];
  for(const attribute of ['HttpOnly','Secure','SameSite=Strict','Max-Age=2592000'])assert.ok(cookie.includes(attribute));
  assert.ok(!cookie.includes(process.env.RISKPATH_OWNER_TOKEN));
  const headers={cookie:cookie.split(';')[0]};
  const read=await request('GET',headers);assert.equal(read.status,200);assert.equal(read.headers['Cache-Control'],'private, no-store');
  assert.equal((await request('POST',headers,{action:'refresh'})).status,405);
  const logout=await request('POST',headers,{action:'logout'});assert.equal(logout.status,200);assert.ok(logout.headers['Set-Cookie'].includes('Max-Age=0'));
});
