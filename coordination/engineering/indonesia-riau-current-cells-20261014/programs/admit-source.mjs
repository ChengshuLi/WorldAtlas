// One fresh observation through the existing accepted processingAllowance.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
const root=fs.realpathSync(process.argv[2]),prep=fs.realpathSync(process.argv[3]);
if(process.execArgv.length||process.env.NODE_OPTIONS?.trim()||process.env.NODE_PATH?.trim())throw Error('Require plain Node launch');
const base='ecb837c599544ff8462b50f43a678d60c80fa5f6';
const env={...process.env,GIT_NO_LAZY_FETCH:'1',GIT_NO_REPLACE_OBJECTS:'1',GIT_TERMINAL_PROMPT:'0'};
const git=(...args)=>execFileSync('git',['-c','protocol.allow=never','-C',root,...args],{env,maxBuffer:32*1024*1024});
if(git('rev-parse','HEAD').toString().trim()!==base)throw Error('Require actual accepted baseline HEAD');
const sha=b=>createHash('sha256').update(b).digest('hex'),code=[],seen=new Set();
function closure(name){
 if(seen.has(name))return;seen.add(name);
 const body=fs.readFileSync(path.join(root,name));
 if(!body.equals(git('show',base+':'+name)))throw Error('Accepted module drift: '+name);
 code.push({commit:base,path:name,bytes:body.length,sha256:sha(body)});
 for(const m of body.toString().matchAll(/(?:from\s*|import\s*\()(['"])([^'"]+)\1/g)){
  if(m[2].startsWith('node:'))continue;
  if(!m[2].startsWith('.'))throw Error('Undeclared installed module');
  const dependency=path.posix.normalize(path.posix.join(path.posix.dirname(name),m[2]));
  if(dependency.startsWith('../')||path.isAbsolute(dependency))throw Error('Import escapes checkout');
  closure(dependency);
 }
}
closure('scripts/check-effective-geographic-regression.mjs');
closure('package.json');
const {processingAllowance}=await import(pathToFileURL(path.join(root,'scripts/check-effective-geographic-regression.mjs')).href);
const inventory=JSON.parse(fs.readFileSync(path.join(prep,'source-input-inventory.json')));
const runtimeBody=fs.readFileSync(path.join(prep,'python-runtime-inventory.json'));
const runtime=JSON.parse(runtimeBody);
let runtimeBytes=0;
for(const pin of runtime.files){
 const body=fs.readFileSync(pin.path);
 if(body.length!==pin.bytes||sha(body)!==pin.sha256)throw Error('Installed Python runtime drift: '+pin.path);
 runtimeBytes+=body.length;
}
if(runtimeBytes!==inventory.runtime_inventory_bytes||runtimeBytes!==runtime.total_file_bytes)throw Error('Runtime inventory total drift');
const program=fs.readFileSync(path.join(prep,'check-riau-sources.py'));
const observer=fs.readFileSync(path.join(prep,'observe-source.py'));
const executionReserve=inventory.reserve_bytes+program.length+observer.length+runtimeBody.length+fs.statSync(process.argv[1]).size;
const observation={availableBytes:process.availableMemory(),currentRssBytes:process.memoryUsage().rss,concurrentReservedBytes:1048576};
const allowance=processingAllowance({...observation,phaseBytes:512*1024*1024,rssBytes:512*1024*1024});
if(inventory.combined_raw_decoded_input_bytes+inventory.runtime_inventory_bytes+executionReserve>=allowance.phaseBytes)throw Error('Source phase exceeds fresh allowance');
const receipt={version:1,observed_at:new Date().toISOString(),observed_unix_seconds:Date.now()/1000,accepted_base:base,observation,allowance,runtime_inventory_bytes:inventory.runtime_inventory_bytes,execution_reserve_bytes:executionReserve,source_input_bytes:inventory.combined_raw_decoded_input_bytes,program_sha256:sha(program),observer_sha256:sha(observer),helper_code:code,limits:['Existing processingAllowance is invoked unchanged. Source checks operate at code/feature boundaries; no hard deadline, live RSS supervisor, process-tree containment or streaming log enforcement.']};
fs.writeFileSync(path.join(prep,'source-admission-001.json'),JSON.stringify(receipt,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify(receipt));
