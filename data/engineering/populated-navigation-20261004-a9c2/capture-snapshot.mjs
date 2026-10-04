import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {performance} from 'node:perf_hooks';
const origin='https://worldatlas-explorer.chengshu-li-2013.chatgpt.site';
const directory=process.argv[2];
if(!directory||!process.stdin.isTTY)throw Error('Supply an output directory and hidden credential stdin');
process.stdin.setRawMode(true);
console.log('Ready for read-only private verification credential on hidden stdin.');
const token=await new Promise((resolve,reject)=>{let input='';process.stdin.on('data',chunk=>{input+=chunk;if(!/[\r\n]/.test(input))return;process.stdin.pause();process.stdin.setRawMode(false);try{const {token}=JSON.parse(input.trim());if(typeof token!=='string'||!token||/[\r\n]/.test(token))throw Error();resolve(token);}catch{reject(Error('Invalid hidden credential input'));}});});
fs.mkdirSync(directory,{recursive:true});
const rows=[];
for(const year of [2020,2021,1900]){
 const route='/api/map/snapshot?'+new URLSearchParams({year:String(year),limit:'4096',evidence_only:'1',include_temporal:'1',examples:'0'});
 const row={year,route,started_at_utc:new Date().toISOString(),read_only:true};rows.push(row);
 try{
  const start=performance.now(),response=await fetch(origin+route,{headers:{'OAI-Sites-Authorization':'Bearer '+token},redirect:'error',signal:AbortSignal.timeout(60000)});
  row.status=response.status;row.headers_ms=performance.now()-start;
  const bytes=Buffer.from(await response.arrayBuffer());row.total_ms=performance.now()-start;
  if(bytes.length>8*1024*1024)throw Error('Snapshot exceeds existing response budget');
  row.bytes=bytes.length;row.sha256=createHash('sha256').update(bytes).digest('hex');
  if(!response.ok)throw Error('Snapshot HTTP failure');
  const parseStart=performance.now(),page=JSON.parse(bytes);row.parse_ms=performance.now()-parseStart;
  row.revision=page.revision;row.next_cursor=page.next_cursor;row.records=page.records.length;row.names=page.names.length;row.retirements=page.retirements.length;
  row.temporal_release=page.temporal_geography?.records?.release_id??null;
  row.path='snapshot-'+year+'.json';fs.writeFileSync(path.join(directory,row.path),bytes);row.completed=true;
 }catch(error){row.completed=false;row.failure=error.name;row.transport_code=error.cause?.code??null;}
 fs.writeFileSync(path.join(directory,'capture-receipt.json'),JSON.stringify({version:1,origin,read_only:true,production_mutation:false,provider_wake_state:'unmeasured',rows},null,2)+'\n');
 console.log(JSON.stringify(row));if(!row.completed){process.exitCode=1;break;}
}
