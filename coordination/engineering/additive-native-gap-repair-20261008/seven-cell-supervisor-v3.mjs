import fs from 'node:fs';
import path from 'node:path';
import {spawn,execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
const repo=process.cwd(),packet='coordination/engineering/additive-native-gap-repair-20261008',head=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
const node='/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node';
const sha=raw=>createHash('sha256').update(raw).digest('hex'),selfSha=sha(fs.readFileSync(import.meta.filename));
const plan=JSON.parse(fs.readFileSync('.cache/additive-native-gap-repair/add031-release-plan-v3.json'));
const jobs=plan.requests.toSorted((a,b)=>a.run-b.run||a.ordinal-b.ordinal),root='.cache/additive-native-gap-repair/add031-release-cold-v3';
fs.mkdirSync(root,{recursive:true});
const journalPath=root+'/journal.json';
const journal=fs.existsSync(journalPath)?JSON.parse(fs.readFileSync(journalPath)):{version:1,execution_commit:head,supervisor_sha256:selfSha,completed:[],limits:{rss_bytes:512*1024*1024,wall_seconds:120}};
if(journal.execution_commit!==head||journal.supervisor_sha256!==selfSha)throw Error('Different execution/supervisor requires fresh journal');
for(const job of jobs){
 const key=job.run+'-'+job.ordinal;
 if(journal.completed.find(row=>row.key===key))continue;
 if(fs.existsSync(job.destination))throw Error('Unqualified or partial existing destination cannot resume');
 const out=fs.openSync(root+'/'+key+'.stdout','wx'),err=fs.openSync(root+'/'+key+'.stderr','wx'),started=Date.now();
 const child=spawn('/usr/bin/time',['-l',node,'scripts/additive-gap-repair.mjs',repo,head,job.path,job.sha256,job.destination],
  {cwd:repo,detached:true,stdio:['ignore',out,err],env:process.env});
 let peak=0,refusal=null;
 const timer=setInterval(()=>{
  try{const rows=execFileSync('ps',['-axo','pid=,pgid=,rss='],{encoding:'utf8'}).trim().split('\n').map(line=>line.trim().split(/\s+/).map(Number));
   const actual=rows.filter(row=>row[1]===child.pid).reduce((sum,row)=>sum+row[2]*1024,0);peak=Math.max(peak,actual);
   if(actual>journal.limits.rss_bytes||Date.now()-started>journal.limits.wall_seconds*1000){refusal=actual>journal.limits.rss_bytes?'sampled process group RSS':'wall time';process.kill(-child.pid,'SIGTERM');}
  }catch(error){if(!refusal)refusal='supervision sample failed: '+error.message;try{process.kill(-child.pid,'SIGTERM');}catch{}}
 },200);
 const result=await new Promise(resolve=>child.once('exit',(code,signal)=>resolve({code,signal})));
 clearInterval(timer);fs.closeSync(out);fs.closeSync(err);
 const stderr=fs.readFileSync(root+'/'+key+'.stderr','utf8'),match=/([0-9]+)\s+maximum resident set size/.exec(stderr);
 const lifetime=match?Number(match[1]):null;
 const remaining=execFileSync('ps',['-axo','pid=,pgid='],{encoding:'utf8'}).trim().split('\n').map(line=>line.trim().split(/\s+/).map(Number)).filter(row=>row[1]===child.pid);
 const operating={version:1,key,execution_commit:head,supervisor_sha256:selfSha,request_path:job.path,request_sha256:job.sha256,
  destination:job.destination,exit:result,elapsed_ms:Date.now()-started,sampled_group_peak_bytes:peak,lifetime_peak_bytes:lifetime,
  owned_processes_remaining:remaining,refusal,qualified:result.code===0&&!result.signal&&!refusal&&lifetime!==null&&lifetime<=journal.limits.rss_bytes&&remaining.length===0};
 fs.writeFileSync(root+'/'+key+'.operating.json',JSON.stringify(operating,null,2)+'\n',{flag:'wx'});
 if(!operating.qualified)throw Error('Cold job not qualified: '+key+' '+JSON.stringify(operating));
 const pub=JSON.parse(fs.readFileSync(job.destination+'/publication.json'));
 const encoded=fs.readFileSync(job.destination+'/inventory.jsonl.gz'),factsBody=fs.readFileSync(job.destination+'/facts.json');
 if(pub.complete!==true||encoded.length!==pub.inventory.bytes||sha(encoded)!==pub.inventory.sha256||sha(factsBody)!==pub.facts.sha256||factsBody.length!==pub.facts.bytes)throw Error('Whole output drift');
 const decoded=gunzipSync(encoded,{maxOutputLength:pub.inventory.uncompressed_bytes+1});
 if(decoded.length!==pub.inventory.uncompressed_bytes||sha(decoded)!==pub.inventory.uncompressed_sha256)throw Error('Whole decoded output drift');
 const facts=JSON.parse(factsBody);if(facts.execution_commit!==head||facts.parent.components!==95173)throw Error('Wrong output execution/parent');
 for(const asset of pub.assets??[]){const raw=fs.readFileSync(job.destination+'/'+asset.path);if(raw.length!==asset.bytes||sha(raw)!==asset.sha256)throw Error('Whole release asset drift');if(asset.uncompressed_bytes!==undefined){const decoded=gunzipSync(raw,{maxOutputLength:asset.uncompressed_bytes+1});if(decoded.length!==asset.uncompressed_bytes||sha(decoded)!==asset.uncompressed_sha256)throw Error('Whole decoded release asset drift');}}
 const previous=journal.completed.find(row=>row.ordinal===job.ordinal);
 if(previous&&JSON.stringify(previous.assets)!==JSON.stringify(pub.assets))throw Error('Two complete release asset rosters not encoded/decoded identical');
 if(previous&&JSON.stringify(previous.inventory)!==JSON.stringify(pub.inventory))throw Error('Two cold inventories not whole encoded/decoded equal');
 journal.completed.push({...operating,run:job.run,ordinal:job.ordinal,components:facts.components,counts:facts.counts,inventory:pub.inventory,assets:pub.assets});
 fs.writeFileSync(journalPath,JSON.stringify(journal,null,2)+'\n');
 console.log(JSON.stringify({completed:journal.completed.length,total:jobs.length,run:job.run,ordinal:job.ordinal,components:facts.components,counts:facts.counts,lifetime_peak_bytes:lifetime}));
}
