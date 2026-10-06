// Copy already validated immutable products into this isolated offline checkout.
// Every source and destination is read back; this does not approve or publish data.
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {candidateBudget,committedPreparationFiles,requirePlainExecution} from '../../../scripts/native-ownership/native-preparation-guards.mjs';
requirePlainExecution();
const prefix='coordination/engineering/iran-pakistan-offline-integration-991-20261006-local22';
const receipt=prefix+'/offline-product-staging-v1.json';
if(fs.existsSync(receipt))throw Error('Preserve previous installation receipt');
const head=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
const code=committedPreparationFiles(process.cwd(),head,['package.json',prefix+'/stage-offline-products.mjs','scripts/native-ownership/native-preparation-guards.mjs']);
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const plans=[
 ['native-selected-v1','data/native-ownership/repaired-v7'],
 ['repaired-reference-bundle-v1','data/reference-attributes'],
 ['repaired-ownership-history-v1','data/ownership-history'],
 ['repaired-ownership-runtime-v1','data/ownership-runtime'],
 ['successor-release-v1','data/geographic-releases'],
 ['migrated-build-context-v4','data/native-context-migration'],
];
const phases=[];
for(const [vintage,target] of plans){
 const source=prefix+'/'+vintage;
 const files=fs.readdirSync(source,{recursive:true}).filter(f=>fs.statSync(source+'/'+f).isFile()).sort();
 // Fixed, mandatory windows bound copy/readback bookkeeping, not scientific checks.
 // The enclosing receipt retains the complete file inventory; no window is optional.
 for(let start=0;start<files.length;start+=160){
  const budget=candidateBudget(code),products=[];
  for(const file of files.slice(start,start+160)){
   const from=source+'/'+file,to=target+'/'+file;
   const raw=fs.readFileSync(from),pin={path:from,bytes:raw.length,sha256:sha(raw)};
   const immutable=execFileSync('git',['show',head+':'+from],{maxBuffer:32*1024*1024});
   if(!immutable.equals(raw))throw Error('Source product differs from committed bytes: '+from);
   budget.add(pin);
   const previous=fs.existsSync(to)?{path:to,sha256:sha(fs.readFileSync(to))}:null;
   fs.mkdirSync(path.dirname(to),{recursive:true});fs.writeFileSync(to,raw);
   const installed=fs.readFileSync(to);budget.add({bytes:installed.length});
   if(!installed.equals(raw))throw Error('Offline copy readback mismatch');
   products.push({source:pin,destination:to,previous,sha256:sha(installed),bytes:installed.length});
  }
  phases.push({source,target,start,end:Math.min(start+160,files.length),total_files:files.length,products,budget:budget.snapshot()});
 }
}
const budget=candidateBudget(code),products=[];
for(const file of ['part-11.json','part-17.json']){
 const source=prefix+'/results-v2/stage/data/geography/'+file,target='data/geography/'+file;
 const raw=fs.readFileSync(source);budget.add({bytes:raw.length});
 if(!raw.equals(execFileSync('git',['show',head+':'+source],{maxBuffer:32*1024*1024})))throw Error('Geography stage changed');
 const previous={path:target,sha256:sha(fs.readFileSync(target))};fs.writeFileSync(target,raw);
 const after=fs.readFileSync(target);budget.add({bytes:after.length});if(!after.equals(raw))throw Error('Geography readback mismatch');
 products.push({source:{path:source,sha256:sha(raw),bytes:raw.length},destination:target,previous,sha256:sha(after),bytes:after.length});
}
phases.push({source:'validated whole source shards',products,budget:budget.snapshot()});
fs.writeFileSync(receipt,JSON.stringify({version:1,execution_commit:head,code,phases,scope:'isolated offline checkout only',published:false,scientific_approval:false})+'\n',{flag:'wx'});
console.log(JSON.stringify({phases:phases.length,files:phases.reduce((n,p)=>n+p.products.length,0),published:false}));
