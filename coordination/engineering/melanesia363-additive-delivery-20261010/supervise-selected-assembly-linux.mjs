// Fixed Linux operating wrapper for the existing selected-release assembler.
// SOURCE/NATIVE evidence and current-rebind certificate limits are unchanged.
import {isDeepStrictEqual} from 'node:util';
import fs from 'node:fs';import path from 'node:path';import {execFileSync} from 'node:child_process';import {createHash} from 'node:crypto';import {fileURLToPath,pathToFileURL} from 'node:url';
const MiB=1048576;
const PREFIX='coordination/engineering/melanesia363-additive-delivery-20261010/';
const SELF=PREFIX+'supervise-selected-assembly-linux.mjs',HELPER=PREFIX+'supervise-source-native-linux.mjs';
const ENTRY=PREFIX+'selected-integration/melanesia-five/assemble-existing-five.mjs';
const ASSEMBLER='coordination/engineering/additive-native-activation-20261009/assemble-supported-activation.mjs';
const ROSTER='coordination/engineering/additive-native-composition-20261009/execution-code-paths.json';
const sha=b=>createHash('sha256').update(b).digest('hex'),demand=(v,m)=>{if(!v)throw Error(m);};
const safe=p=>typeof p==='string'&&!path.isAbsolute(p)&&!p.includes('\\')&&p.split('/').every(x=>x&&x!=='.'&&x!=='..');
function ordinaryAncestors(p){for(let q=p;;q=path.dirname(q)){const s=fs.lstatSync(q);demand(!s.isSymbolicLink(),'Nonordinary path');if(q===path.dirname(q))break;}}
function smallFile(p,max=131072){ordinaryAncestors(p);const s=fs.lstatSync(p);demand(s.isFile()&&s.size<=max,'Ordinary bounded file required');return fs.readFileSync(p);}
function fresh(root,p){demand(path.isAbsolute(p)&&path.resolve(p)===p&&p.startsWith(root+'/.cache/')&&!fs.lstatSync(p,{throwIfNoEntry:false}),'Fresh owned assembly destination required');ordinaryAncestors(path.dirname(p));}
// The current reader is issued separately from historical producer limits.
// Requested values remain bounded by the unchanged actual process-group guard;
// the child also admits them against its fresh observed machine headroom.
export function assemblyProcessingAllowance(value,groupCap){
 demand(Number.isSafeInteger(groupCap)&&groupCap>0,'Explicit assembly group reservation required');
 demand(value&&typeof value==='object'&&!Array.isArray(value)&&Object.keys(value).sort().join(',')==='phaseBytes,rssBytes','Explicit assembly processing allowance required');
 demand([value.phaseBytes,value.rssBytes].every(n=>Number.isSafeInteger(n)&&n>0&&n<=groupCap),'Assembly processing allowance exceeds actual group guard');
 return Object.freeze({phaseBytes:value.phaseBytes,rssBytes:value.rssBytes});
}
export function assemblyStockAdmission(stock,root,growth){
 const integer=n=>Number.isSafeInteger(n)&&n>=0;
 demand(stock&&integer(stock.freeBytes)&&Number.isSafeInteger(stock.limits?.minimumFree)&&stock.limits.minimumFree>0&&Number.isSafeInteger(growth)&&growth>0,'Finite assembly storage admission required');
 const own=stock.entries.filter(e=>e.path===root&&e.slot==='work'&&e.status==='ready');
 demand(own.length===1&&integer(own[0].reservation),'Exact ready owned assembly slot required');
 const actual=stock.worktrees.filter(e=>e.path===root&&e.managed===true);
 demand(actual.length===1&&integer(actual[0].bytes),'Measured owned assembly footprint required');
 let peers=0;for(const entry of stock.entries){if(entry.path===root)continue;const rows=stock.worktrees.filter(e=>e.path===entry.path);demand(integer(entry.reservation)&&rows.length<=1&&(!rows.length||integer(rows[0].bytes)),'Measured peer reservation required');peers+=Math.max(0,entry.reservation-(rows[0]?.bytes??0));}
 const ownRemaining=Math.max(0,own[0].reservation-actual[0].bytes),admitted=Math.max(ownRemaining,growth),residual=stock.freeBytes-peers-admitted;
 demand(Number.isSafeInteger(peers)&&Number.isSafeInteger(residual)&&residual>=stock.limits.minimumFree,'Assembly free space/peer reservation/growth refused');
 return {free_bytes:stock.freeBytes,minimum_free_bytes:stock.limits.minimumFree,own_remaining_reservation_bytes:ownRemaining,peer_remaining_reservation_bytes:peers,issued_growth_bytes:growth,admitted_growth_bytes:admitted,residual_bytes:residual};
}
export function assemblyProducts(output,stdout,head,issuedAllowance,limits){
 const allowance=assemblyProcessingAllowance(issuedAllowance,limits.rss_bytes);
 const summary=JSON.parse(stdout),names=['ledger','patch','envelope','qualification'];
 demand(summary.execution_commit===head&&Array.isArray(summary.products)&&summary.products.length===4,'Assembly stdout identity');
 demand(isDeepStrictEqual(summary.operating_limits,limits),'Assembly summary operating limits differ');
 demand(isDeepStrictEqual(summary.processing_allowance,allowance),'Assembly summary processing allowance differs');
 demand(Number.isSafeInteger(summary.complete_reader_phase_bytes)&&summary.complete_reader_phase_bytes>0&&summary.complete_reader_phase_bytes<=allowance.phaseBytes,'Complete assembly reader phase');
 let total=0;for(const name of names){const raw=smallFile(path.join(output,name+'.json'),limits.output_bytes);total+=raw.length;
  const matches=summary.products.filter(p=>p.path===name+'.json');demand(matches.length===1&&matches[0].bytes===raw.length&&matches[0].sha256===sha(raw),'Assembly product/stdout mismatch');}
 demand(total<=limits.output_bytes,'Assembly product union');demand(isDeepStrictEqual(JSON.parse(smallFile(path.join(output,'qualification.json'),limits.output_bytes)),summary.qualification),'Assembly qualification summary differs');return summary;
}
async function main(){
 demand(process.platform==='linux'&&!process.execArgv.length&&!process.env.NODE_OPTIONS&&!process.env.NODE_PATH,'Plain Linux assembly supervisor required');
 const [name,expected]=process.argv.slice(2);demand(process.argv.length===4&&/^[a-f0-9]{64}$/.test(expected??''),'Whole issued assembly parameters required');
 const repo=fs.realpathSync(process.cwd()),parameterPath=path.resolve(name),raw=smallFile(parameterPath);demand(sha(raw)===expected,'Assembly parameters differ');
 const p=JSON.parse(raw),o=p.operating_runtime;
 const concurrent=process.env.WORLDATLAS_CONCURRENT_RESERVED_BYTES;
 demand(/^(0|[1-9][0-9]*)$/.test(concurrent??'')&&Number.isSafeInteger(Number(concurrent)),'Explicit finite concurrent assembly reservation required');
 demand(p.root===repo&&/^[a-f0-9]{40}$/.test(p.execution_commit??'')&&o?.version===1&&o.platform==='linux','Assembly execution identity');
 fresh(repo,p.destination);const operation=p.destination+'-operating';fresh(repo,operation);
 demand(Array.isArray(o.support_code)&&JSON.stringify(o.support_code.map(x=>x.path))===JSON.stringify([SELF,HELPER,ENTRY,ASSEMBLER]),'Complete fixed assembly wrapper closure');
 const helper=o.support_code[1],helperRaw=smallFile(path.join(repo,HELPER));demand(helper.bytes===helperRaw.length&&helper.sha256===sha(helperRaw),'Assembly helper pre-import binding');
 const {RUNTIME_BODIES,ordinary,scientificEnvironment,freshSupply,supervise,assemblyStorage,assemblyOperatingLimits}=await import(pathToFileURL(path.join(repo,HELPER)));
 const limits=assemblyOperatingLimits(p.operating_limits),allowance=assemblyProcessingAllowance(p.processing_allowance,limits.rss_bytes);
 demand(Array.isArray(o.runtime)&&o.runtime.length===RUNTIME_BODIES.length,'Complete assembly runtime');
 for(let i=0;i<RUNTIME_BODIES.length;i++){const a=o.runtime[i],b=RUNTIME_BODIES[i];demand(a.role===b.role&&a.bytes===b.bytes&&a.sha256===b.sha256&&a.mode===0o755,'Foreign assembly runtime');ordinary(a);}
 const role=r=>o.runtime.find(x=>x.role===r).path;demand(role('node')===process.execPath,'Assembly Node differs');
 const env=scientificEnvironment(o.runtime),git=(...args)=>execFileSync(role('git'),args,{env,maxBuffer:32*MiB});
 const head=p.execution_commit;demand(git('rev-parse','HEAD').toString().trim()===head&&!git('status','--porcelain').length,'Frozen clean assembly head required');
 demand(path.relative(repo,fileURLToPath(import.meta.url))===SELF,'Fixed assembly supervisor path');
 const rosterRaw=smallFile(path.join(repo,ROSTER));demand(git('show',head+':'+ROSTER).equals(rosterRaw),'Executing roster body differs');const roster=JSON.parse(rosterRaw);demand(Array.isArray(o.code)&&JSON.stringify(o.code.map(x=>x.path))===JSON.stringify(roster),'Complete assembly method roster');
 const installed=o.code.filter(x=>x.path.includes('/module-bodies/')).map(x=>({...x,path:path.join(repo,'node_modules/@noble/hashes',path.basename(x.path)),mode:0o644}));demand(installed.length===5,'Complete actual installed module closure');
 const code=[...o.code,...o.support_code];demand(new Set(code.map(x=>x.path)).size===code.length,'Duplicate assembly code body');
 const runtimeBytes=o.runtime.reduce((n,x)=>n+x.bytes,0);
 // Charge issued retained operating growth and receipt metadata separately
 // from the reader's seven-way complete product serialization reserve.
 const executionBytes=2*code.reduce((n,x)=>n+x.bytes,0)+installed.reduce((n,x)=>n+x.bytes,0)+limits.retained_bytes-limits.output_bytes+limits.receipt_bytes;
 demand(Number.isSafeInteger(executionBytes)&&Number.isSafeInteger(7*limits.output_bytes)&&runtimeBytes+executionBytes+8*MiB+2*raw.length+7*limits.output_bytes<=allowance.phaseBytes,'Assembly code/runtime/output union');
 function capture(){
  demand(git('rev-parse','HEAD').toString().trim()===head&&!git('status','--porcelain').length,'Assembly head/worktree changed');
  demand(smallFile(parameterPath).equals(raw),'Assembly parameter body changed');
  for(const pin of [...o.runtime,...installed])ordinary(pin);
  for(const pin of code){demand(safe(pin.path)&&Number.isSafeInteger(pin.bytes)&&pin.bytes>0&&pin.bytes<=32*MiB&&/^[a-f0-9]{64}$/.test(pin.sha256),'Invalid assembly code pin');
   ordinary({...pin,path:path.join(repo,pin.path),mode:0o644});
   const row=git('ls-tree','-z',head,'--',pin.path).toString();demand(/^100644 blob [a-f0-9]{40}\t/.test(row)&&row.endsWith('\t'+pin.path+'\0'),'Assembly code ordinary Git body');
   const body=git('show',head+':'+pin.path);demand(body.length===pin.bytes&&sha(body)===pin.sha256,'Assembly code Git/body mismatch');}
  return {head,processing_allowance:allowance,operating_limits:limits,concurrent_reserved_bytes:Number(concurrent),code:o.code,support_code:o.support_code,runtime:o.runtime,installed,parameters:{path:parameterPath,bytes:raw.length,sha256:expected},runtimeBytes,executionBytes,gitExecutable:role('git')};
 }
 const before=capture(),preUse=JSON.stringify(before);demand(Buffer.byteLength(preUse)<=131072,'Assembly pre-use metadata bound');
 const supply=freshSupply(role('process-inspector'),concurrent,limits.rss_bytes);
 const {workspaceManager}=await import(pathToFileURL(path.join(repo,'scripts/local-workspace.mjs')));
 const storage=assemblyStockAdmission(workspaceManager(repo).check(),repo,limits.retained_bytes);
 const command=[process.execPath,'--expose-gc',path.join(repo,ENTRY),parameterPath,expected];
 const result=await supervise(command,{time:role('time'),ps:role('process-inspector'),operation,env:{...env,WORLDATLAS_ASSEMBLY_PRE_USE:preUse,WORLDATLAS_CONCURRENT_RESERVED_BYTES:concurrent},profile:'selected-assembly-v2',outputDirectory:p.destination,cap:limits.rss_bytes,wall:limits.wall_seconds*1000,operatingLimits:limits});
 let after=null,products=null;try{after=capture();if(result.qualified)products=assemblyProducts(p.destination,smallFile(path.join(operation,'stdout.txt'),limits.log_bytes),head,allowance,limits);}catch(error){result.refusal??=error.message;result.qualified=false;}
 result.peak_supervisor_rss_bytes=Math.max(result.peak_supervisor_rss_bytes,process.memoryUsage().rss);
 result.conservative_lifetime_and_supervisor_bound_bytes=result.time_lifetime_max_rss_bytes===null?null:result.time_lifetime_max_rss_bytes+result.peak_supervisor_rss_bytes;
 if(result.conservative_lifetime_and_supervisor_bound_bytes>limits.rss_bytes){result.refusal??='Assembly post-use lifetime plus supervisor bound';result.qualified=false;}
 Object.assign(result,{profile:'selected-assembly-v2',processing_allowance:allowance,operating_limits:limits,execution_commit:head,parameters_sha256:expected,destination:p.destination,resource_admission:supply,storage_admission:storage,pre_use:before,post_use:after,products});
 let receipt=JSON.stringify(result,null,2)+'\n';demand(Buffer.byteLength(receipt)<=limits.receipt_bytes,'Assembly receipt metadata reserve');
 try{const retained=assemblyStorage(p.destination,operation,0,limits);demand(retained.retainedBytes+Buffer.byteLength(receipt)<=limits.retained_bytes,'Assembly final retained receipt reserve');}catch(error){result.refusal??=error.message;result.qualified=false;receipt=JSON.stringify(result,null,2)+'\n';}
 demand(Buffer.byteLength(receipt)<=limits.receipt_bytes,'Assembly final receipt metadata reserve');
 fs.writeFileSync(path.join(operation,'receipt.json'),receipt,{flag:'wx'});process.stdout.write(JSON.stringify({qualified:result.qualified,execution_commit:head,refusal:result.refusal,operating:operation})+'\n');process.exitCode=result.qualified?0:1;
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(e=>{process.stderr.write(e.stack+'\n');process.exitCode=1;});
