import fs from 'node:fs';
import {createHash} from 'node:crypto';
const origin='https://worldatlas-explorer.chengshu-li-2013.chatgpt.site';
if(!process.stdin.isTTY)throw Error('Hidden credential stdin required');
process.stdin.setRawMode(true);
console.log('Ready for hidden private source probe JSON.');
let input='';
const token=await new Promise((resolve,reject)=>process.stdin.on('data',chunk=>{
 input+=chunk.toString();if(input.length>8192)return reject(Error('Input too large'));
 if(!/[\r\n]/.test(input))return;
 process.stdin.pause();process.stdin.setRawMode(false);
 try{const t=JSON.parse(input.trim()).token;input='';if(typeof t!=='string'||!t||/[\r\n]/.test(t))throw Error();resolve(t);}catch{reject(Error('Invalid hidden input'));}
}));
const receipt={version:1,checked_at_utc:new Date().toISOString(),origin,operation:'read-only-private-source-readiness',requests:[],limits:['No complete capture or isolated restore performed.','No maintenance, provider SQL, DDL or publication performed.']};
try{
 for(const route of ['/api/storage/v2/export-marker','/api/storage/capacity']){
  const started=performance.now(),r=await fetch(origin+route,{method:'GET',redirect:'error',signal:AbortSignal.timeout(60000),headers:{'OAI-Sites-Authorization':'Bearer '+token}});
  const item={route,status:r.status};receipt.requests.push(item);
  const chunks=[];let size=0;for await(const chunk of r.body){size+=chunk.length;if(size>4*1024*1024)throw Error('Response too large');chunks.push(chunk);}
  const bytes=Buffer.concat(chunks);item.bytes=size;item.sha256=createHash('sha256').update(bytes).digest('hex');item.duration_ms=Math.round(performance.now()-started);
  if(!r.ok)throw Error('Read-only source rejected');item.body=JSON.parse(bytes);
 }
 receipt.complete=true;
}catch{receipt.complete=false;receipt.failure='Private source readiness failed; categorized route/status receipts retained';process.exitCode=1;}
const output='data/engineering/storage-recovery-20261004-7e91/private-source-readiness-with-proxy.json';
if(fs.existsSync(output))throw Error('Preserve previous probe vintage');
const raw=JSON.stringify(receipt,null,2)+'\n';if(raw.includes(token))throw Error('Unsafe receipt');fs.writeFileSync(output,raw,{mode:0o600});
console.log(JSON.stringify({completed:receipt.complete,requests:receipt.requests.map(({route,status,bytes})=>({route,status,bytes})),output}));process.exit();
