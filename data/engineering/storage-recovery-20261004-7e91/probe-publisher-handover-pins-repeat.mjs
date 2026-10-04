import fs from 'node:fs';
import {createHash} from 'node:crypto';
const origin='https://worldatlas-explorer.chengshu-li-2013.chatgpt.site';
import {readHiddenPrivateToken} from '../../../scripts/verify-retained-object-recovery.mjs';
console.log('Ready for hidden private source probe JSON.');
const token=await readHiddenPrivateToken();
const receipt={version:1,checked_at_utc:new Date().toISOString(),origin,operation:'read-only-current-served-publisher-handover-pins',requests:[],limits:['No complete capture or isolated restore performed.','No maintenance, provider SQL, DDL or publication performed.']};
try{
 for(const route of ['/api/geography/release','/atlas-geography.json']){
  const started=performance.now(),r=await fetch(origin+route,{method:'GET',redirect:'error',signal:AbortSignal.timeout(60000),headers:{'OAI-Sites-Authorization':'Bearer '+token}});
  const item={route,status:r.status};receipt.requests.push(item);
  const chunks=[];let size=0;for await(const chunk of r.body){size+=chunk.length;if(size>32*1024*1024)throw Error('Response too large');chunks.push(chunk);}
  const bytes=Buffer.concat(chunks);item.bytes=size;item.sha256=createHash('sha256').update(bytes).digest('hex');item.duration_ms=Math.round(performance.now()-started);
  if(!r.ok)throw Error('Read-only source rejected');const body=JSON.parse(bytes);item.body=route==='/atlas-geography.json'?{reference_release:body.reference_release,contentCapabilities:body.contentCapabilities}:body;if(route==='/atlas-geography.json')item.body_retention='Exact response bytes/hash recorded; selected release/capability metadata only; original full asset retained in Site source2326792';
 }
 receipt.complete=true;
}catch{receipt.complete=false;receipt.failure='Private source readiness failed; categorized route/status receipts retained';process.exitCode=1;}
const output='data/engineering/storage-recovery-20261004-7e91/publisher-handover-served-pins-repeat.json';
if(fs.existsSync(output))throw Error('Preserve previous probe vintage');
const raw=JSON.stringify(receipt,null,2)+'\n';if(raw.includes(token))throw Error('Unsafe receipt');fs.writeFileSync(output,raw,{mode:0o600});
console.log(JSON.stringify({completed:receipt.complete,requests:receipt.requests.map(({route,status,bytes})=>({route,status,bytes})),output}));process.exit();
