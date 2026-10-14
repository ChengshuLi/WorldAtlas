// Execute the existing accepted immutable constructor once for two Riau targets.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
const root=fs.realpathSync(process.argv[2]),out=path.resolve(process.argv[3]);
if(process.execArgv.length||process.env.NODE_OPTIONS?.trim()||process.env.NODE_PATH?.trim())throw Error('Require plain Node');
if(fs.lstatSync(out,{throwIfNoEntry:false})||fs.realpathSync(path.dirname(out))!==path.dirname(out))throw Error('Require new ordinary output directory');
const accepted='ecb837c599544ff8462b50f43a678d60c80fa5f6',candidate='ceaebb8c78ec88d9f034577b5d0e7426c72d4585';
process.env.GIT_NO_LAZY_FETCH='1';process.env.GIT_NO_REPLACE_OBJECTS='1';process.env.GIT_TERMINAL_PROMPT='0';
const count=Number(process.env.GIT_CONFIG_COUNT??0);if(!Number.isSafeInteger(count)||count<0)throw Error('Invalid Git config');
process.env.GIT_CONFIG_COUNT=String(count+1);process.env['GIT_CONFIG_KEY_'+count]='protocol.allow';process.env['GIT_CONFIG_VALUE_'+count]='never';
const git=(...args)=>execFileSync('git',['-c','protocol.allow=never','-C',root,...args],{maxBuffer:32*1024*1024});
if(git('rev-parse','HEAD').toString().trim()!==candidate)throw Error('Exact committed input HEAD required');
const sha=b=>createHash('sha256').update(b).digest('hex'),code=[],seen=new Set();
function closure(name){
 if(seen.has(name))return;seen.add(name);const body=fs.readFileSync(path.join(root,name));
 if(!body.equals(git('show',accepted+':'+name)))throw Error('Accepted execution code differs: '+name);
 code.push({commit:accepted,path:name,bytes:body.length,sha256:sha(body)});
 for(const m of body.toString().matchAll(/(?:from\s*|import\s*\()(['"])([^'"]+)\1/g)){
  if(m[2].startsWith('node:'))continue;if(!m[2].startsWith('.'))throw Error('Undeclared installed module');
  const dependency=path.posix.normalize(path.posix.join(path.posix.dirname(name),m[2]));
  if(dependency.startsWith('../')||path.isAbsolute(dependency))throw Error('Import escaped checkout');closure(dependency);
 }
}
closure('scripts/delivery-handoff-advance.mjs');closure('package.json');
const entry=fs.readFileSync(process.argv[1]),executionBytes=entry.length+code.reduce((n,p)=>n+p.bytes,0);
const {ImmutableReader,processingAllowance}=await import(pathToFileURL(path.join(root,'scripts/check-effective-geographic-regression.mjs')).href);
const {constructOriginalAuthority}=await import(pathToFileURL(path.join(root,'scripts/delivery-handoff-advance.mjs')).href);
const observation={availableBytes:process.availableMemory(),currentRssBytes:process.memoryUsage().rss,concurrentReservedBytes:1048576};
const allowance=processingAllowance(observation),reader=new ImmutableReader(root,candidate,{allowance,executionBytes});
const prefix='coordination/engineering/indonesia-riau-current-cells-20261014/';
const inputs={source_evidence:{commit:candidate,path:prefix+'source-evidence.json'},native_patch:{commit:candidate,path:prefix+'candidate-native-patch.json'}};
console.log(JSON.stringify({status:'fresh-admission',accepted,candidate,observation,allowance,executionBytes}));
const started=process.hrtime.bigint(),result=constructOriginalAuthority(reader,inputs);reader.checkMemory();
const products=Object.entries(result.products).map(([name,body])=>({name,body:Buffer.from(body)}));
products.push({name:'qualified-ledger-rows.json',body:Buffer.from(JSON.stringify(result.ledger_rows,null,2)+'\n')});
const cells=result.ledger_rows.reduce((n,row)=>n+row.native_rows.reduce((a,item)=>a+item.runs.reduce((s,run)=>s+run[1]-run[0],0),0),0);
const peak=process.resourceUsage().maxRSS*1024;
const receipt={version:1,kind:'existing-source-target-native-constructor-result',accepted_code:accepted,input_commit:candidate,inputs,observation,allowance,charged_phase_bytes:reader.used,qualified_cells:cells,component_ids:result.component_ids,rule_sha256:result.rule_sha256,elapsed_seconds:Number(process.hrtime.bigint()-started)/1e9,normalized_node_lifetime_peak_rss_bytes:peak,observed_peak_within_allowance:peak<=allowance.rssBytes,entry:{path:process.argv[1],bytes:entry.length,sha256:sha(entry)},code,inventory:[...reader.inventory.values()],limitations:result.limitations,limits:['Existing constructor authenticates original source/physical evidence and derives native coverage; no source/GSHHG producer is replayed.','Empty ownership rows within native-domain qualification do not prove actual current owner zero; actual accepted-selection consumer/conservation remains pending.','The existing reader has its normal phase/RSS checks; no extra supervisor, timeout or process-tree control is introduced.','Physical003 measured RSS overrun remains disclosed in its original receipt; this native call does not relabel that producer as resource-compliant.']};
products.push({name:'receipt.json',body:Buffer.from(JSON.stringify(receipt,null,2)+'\n')});
if(products.some(p=>p.body.length>reader.outputBytes)||products.reduce((n,p)=>n+p.body.length,0)>reader.outputBytes)throw Error('Native complete outputs exceed reserve');
fs.mkdirSync(out);for(const p of products)fs.writeFileSync(path.join(out,p.name),p.body,{flag:'wx'});
console.log(JSON.stringify({status:'native-qualified',qualified_cells:cells,components:result.component_ids.length,charged_phase_bytes:reader.used,allowance,peak_rss_bytes:peak,elapsed_seconds:receipt.elapsed_seconds,out}));
