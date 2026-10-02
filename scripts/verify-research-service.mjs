import fs from 'node:fs';
import {hydrateMapSnapshotPage} from '../src/map-snapshot-format.js';

const origin=new URL(process.argv[2]??'');
if(origin.protocol!=='https:'||origin.pathname!=='/'||origin.username||origin.password||origin.search||origin.hash)throw Error('Supply the confirmed HTTPS Site origin');
if(!process.stdin.isTTY)throw Error('Use hidden terminal stdin for the private service credential');
process.stdin.setRawMode(true);process.stdout.write('Ready for private read-only service credential on hidden stdin.\n');
const token=await new Promise((resolve,reject)=>{let value='';process.stdin.on('data',chunk=>{if(chunk.includes(3)){process.stdin.setRawMode(false);reject(Error('Cancelled'));return;}value+=chunk.toString();if(!/[\r\n]/.test(value))return;process.stdin.pause();process.stdin.setRawMode(false);try{resolve(JSON.parse(value.trim()).token);}catch{reject(Error('Invalid credential'));}});});
if(typeof token!=='string'||!token)throw Error('Missing credential');
async function get(route){const started=performance.now(),r=await fetch(new URL(route,origin),{headers:{'OAI-Sites-Authorization':`Bearer ${token}`},signal:AbortSignal.timeout(60000)});if(!r.ok)throw Error(`Read-only verification HTTP ${r.status}`);const text=await r.text();return {value:JSON.parse(text),bytes:Buffer.byteLength(text),duration_ms:Math.round(performance.now()-started)};}
const capacity=(await get('/api/storage/capacity')).value;
if(capacity.database.quota_verified!==false)throw Error('Unexpected unverified provider quota claim');
const revisions=new Set([capacity.revision]),catalogs={},maps=[];
for(const kind of ['sources','categories','entities']){const page=(await get(`/api/catalog/${kind}?limit=3`)).value;if(page.collection!==kind||page.records.length>3)throw Error('Invalid catalog page');catalogs[kind]={rows:page.records.length,has_more:Boolean(page.next_cursor)};revisions.add(page.revision);}
for(const year of [2021,2025,-3000]){
 const response=await get(`/api/map/snapshot?year=${year}&limit=1000`),page=hydrateMapSnapshotPage(response.value);
 if(page.year!==year||page.entities.length>1000)throw Error('Invalid compact snapshot page');revisions.add(page.revision);
 maps.push({year,entities:page.entities.length,records:page.records.length,names:page.names.length,withdrawals:page.retirements.length,sources:Object.keys(page.sources).length,has_more:Boolean(page.next_cursor),bytes:response.bytes,duration_ms:response.duration_ms});
}
if(revisions.size!==1)throw Error('Storage changed during read-only verification; retry');
const receipt={version:1,verified_at_utc:new Date().toISOString(),url:origin.origin,read_only:true,facts_mutated:false,revision:capacity.revision,capacity,catalogs,compact_map:maps,scope:'Representative production route and shared browser-format checks; exhaustive existing claim/archive verification is recorded separately.'};
if(process.argv[3])fs.writeFileSync(process.argv[3],JSON.stringify(receipt,null,2)+'\n');
console.log(JSON.stringify(receipt));
