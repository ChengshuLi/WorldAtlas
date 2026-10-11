// Fixed Linux operating wrapper for the existing selected-release assembler.
// SOURCE/NATIVE evidence and current-rebind certificate limits are unchanged.
import {isDeepStrictEqual} from 'node:util';
import fs from 'node:fs';import path from 'node:path';import {execFileSync} from 'node:child_process';import {createHash} from 'node:crypto';import {fileURLToPath,pathToFileURL} from 'node:url';
const MiB=1048576,CAP=1024*MiB,PHASE=256*MiB;
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
export function assemblyProducts(output,stdout,head){
 const summary=JSON.parse(stdout),names=['ledger','patch','envelope','qualification'];
 demand(summary.execution_commit===head&&Array.isArray(summary.products)&&summary.products.length===4,'Assembly stdout identity');
 demand(Number.isSafeInteger(summary.complete_reader_phase_bytes)&&summary.complete_reader_phase_bytes>0&&summary.complete_reader_phase_bytes<=PHASE,'Complete assembly reader phase');
 let total=0;for(const name of names){const raw=smallFile(path.join(output,name+'.json'),4*MiB);total+=raw.length;
  const matches=summary.products.filter(p=>p.path===name+'.json');demand(matches.length===1&&matches[0].bytes===raw.length&&matches[0].sha256===sha(raw),'Assembly product/stdout mismatch');}
 demand(total<=4*MiB,'Assembly product union');demand(isDeepStrictEqual(JSON.parse(smallFile(path.join(output,'qualification.json'),4*MiB)),summary.qualification),'Assembly qualification summary differs');return summary;
}
async function main(){
 demand(process.platform==='linux'&&!process.execArgv.length&&!process.env.NODE_OPTIONS&&!process.env.NODE_PATH,'Plain Linux assembly supervisor required');
 const [name,expected]=process.argv.slice(2);demand(process.argv.length===4&&/^[a-f0-9]{64}$/.test(expected??''),'Whole issued assembly parameters required');
 const repo=fs.realpathSync(process.cwd()),parameterPath=path.resolve(name),raw=smallFile(parameterPath);demand(sha(raw)===expected,'Assembly parameters differ');
 const p=JSON.parse(raw),o=p.operating_runtime;
 demand(p.root===repo&&/^[a-f0-9]{40}$/.test(p.execution_commit??'')&&o?.version===1&&o.platform==='linux','Assembly execution identity');
 fresh(repo,p.destination);const operation=p.destination+'-operating';fresh(repo,operation);
 demand(Array.isArray(o.support_code)&&JSON.stringify(o.support_code.map(x=>x.path))===JSON.stringify([SELF,HELPER,ENTRY,ASSEMBLER]),'Complete fixed assembly wrapper closure');
 const helper=o.support_code[1],helperRaw=smallFile(path.join(repo,HELPER));demand(helper.bytes===helperRaw.length&&helper.sha256===sha(helperRaw),'Assembly helper pre-import binding');
 const {RUNTIME_BODIES,ordinary,scientificEnvironment,freshSupply,supervise,assemblyStorage}=await import(pathToFileURL(path.join(repo,HELPER)));
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
 // Reader already reserves4MiB products. Charge the remaining8MiB operation
 // growth and1MiB metadata, actual auxiliary code and installed modules too.
 const executionBytes=2*code.reduce((n,x)=>n+x.bytes,0)+installed.reduce((n,x)=>n+x.bytes,0)+9*MiB;
 demand(runtimeBytes+executionBytes+8*MiB+2*raw.length+4*MiB<=PHASE,'Assembly code/runtime/output union');
 function capture(){
  demand(git('rev-parse','HEAD').toString().trim()===head&&!git('status','--porcelain').length,'Assembly head/worktree changed');
  demand(smallFile(parameterPath).equals(raw),'Assembly parameter body changed');
  for(const pin of [...o.runtime,...installed])ordinary(pin);
  for(const pin of code){demand(safe(pin.path)&&Number.isSafeInteger(pin.bytes)&&pin.bytes>0&&pin.bytes<=32*MiB&&/^[a-f0-9]{64}$/.test(pin.sha256),'Invalid assembly code pin');
   ordinary({...pin,path:path.join(repo,pin.path),mode:0o644});
   const row=git('ls-tree','-z',head,'--',pin.path).toString();demand(/^100644 blob [a-f0-9]{40}\t/.test(row)&&row.endsWith('\t'+pin.path+'\0'),'Assembly code ordinary Git body');
   const body=git('show',head+':'+pin.path);demand(body.length===pin.bytes&&sha(body)===pin.sha256,'Assembly code Git/body mismatch');}
  return {head,code:o.code,support_code:o.support_code,runtime:o.runtime,installed,parameters:{path:parameterPath,bytes:raw.length,sha256:expected},runtimeBytes,executionBytes,gitExecutable:role('git')};
 }
 const before=capture(),preUse=JSON.stringify(before);demand(Buffer.byteLength(preUse)<=131072,'Assembly pre-use metadata bound');
 const supply=freshSupply(role('process-inspector'),process.env.WORLDATLAS_CONCURRENT_RESERVED_BYTES);
 const command=[process.execPath,'--expose-gc',path.join(repo,ENTRY),parameterPath,expected];
 const result=await supervise(command,{time:role('time'),ps:role('process-inspector'),operation,env:{...env,WORLDATLAS_ASSEMBLY_PRE_USE:preUse},profile:'selected-assembly-v1',outputDirectory:p.destination,cap:CAP,wall:1200000});
 let after=null,products=null;try{after=capture();if(result.qualified)products=assemblyProducts(p.destination,smallFile(path.join(operation,'stdout.txt'),4*MiB),head);}catch(error){result.refusal??=error.message;result.qualified=false;}
 result.peak_supervisor_rss_bytes=Math.max(result.peak_supervisor_rss_bytes,process.memoryUsage().rss);
 result.conservative_lifetime_and_supervisor_bound_bytes=result.time_lifetime_max_rss_bytes===null?null:result.time_lifetime_max_rss_bytes+result.peak_supervisor_rss_bytes;
 if(result.conservative_lifetime_and_supervisor_bound_bytes>CAP){result.refusal??='Assembly post-use lifetime plus supervisor bound';result.qualified=false;}
 Object.assign(result,{profile:'selected-assembly-v1',execution_commit:head,parameters_sha256:expected,destination:p.destination,resource_admission:supply,pre_use:before,post_use:after,products});
 let receipt=JSON.stringify(result,null,2)+'\n';demand(Buffer.byteLength(receipt)<=MiB,'Assembly receipt metadata reserve');
 try{const retained=assemblyStorage(p.destination,operation);demand(retained.retainedBytes+Buffer.byteLength(receipt)<=12*MiB,'Assembly final retained receipt reserve');}catch(error){result.refusal??=error.message;result.qualified=false;receipt=JSON.stringify(result,null,2)+'\n';}
 fs.writeFileSync(path.join(operation,'receipt.json'),receipt,{flag:'wx'});process.stdout.write(JSON.stringify({qualified:result.qualified,execution_commit:head,refusal:result.refusal,operating:operation})+'\n');process.exitCode=result.qualified?0:1;
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(e=>{process.stderr.write(e.stack+'\n');process.exitCode=1;});
