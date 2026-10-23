// Plain cold entry; no Node flags or preload variables. The supervisor whole-authenticates
// this file and its complete code/runtime closure before ANY dynamic import.
import fs from 'node:fs';import path from 'node:path';import {createHash} from 'node:crypto';
const demand=(v,m)=>{if(!v)throw Error(m);},sha=b=>createHash('sha256').update(b).digest('hex');
const head=process.env.WORLDATLAS_REBIND_EXECUTION_COMMIT,serialized=process.env.WORLDATLAS_REBIND_EXECUTION_PRE_USE;
demand(process.execArgv.length===0&&!process.env.NODE_OPTIONS&&!process.env.NODE_PATH&&/^[a-f0-9]{40}$/.test(head??'')&&typeof serialized==='string','Missing/plain actual execution identity');
const input=JSON.parse(serialized),before=input.pre_use,command=input.command;
demand(before&&Array.isArray(command)&&command.length===4&&command[0]===process.execPath&&command[1]===process.argv[1]&&command[2]===process.argv[2]&&command[3]===process.argv[3],'Actual entry command differs from whole executing contract');
const p=before.plan;demand(p&&p.path===command[2]&&Number.isSafeInteger(p.bytes)&&p.bytes>0&&p.mode===420&&/^[a-f0-9]{64}$/.test(p.sha256),'Whole plan identity required');
for(const name of [p.path,command[3]])demand(path.isAbsolute(name)&&path.resolve(name)===name,'Canonical absolute entry paths');
let current=path.parse(p.path).root;for(const part of p.path.slice(current.length).split(path.sep)){current=path.join(current,part);const s=fs.lstatSync(current);demand(!s.isSymbolicLink(),'Ordinary plan ancestors required');}
const stat=fs.lstatSync(p.path);demand(stat.isFile()&&stat.size===p.bytes&&(stat.mode&0o777)===p.mode,'Plan stat differs before read');
const fd=fs.openSync(p.path,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW);let raw;try{raw=fs.readFileSync(fd);const held=fs.fstatSync(fd),end=fs.lstatSync(p.path);for(const k of ['dev','ino','size','mode','mtimeMs','ctimeMs'])demand(stat[k]===held[k]&&held[k]===end[k],'Plan identity drift');}finally{fs.closeSync(fd);}
demand(raw.length===p.bytes&&sha(raw)===p.sha256,'Whole raw plan differs');const plan=JSON.parse(raw);
demand(plan.execution_commit===head,'Actual injected plan/head differs before imports');
const root=fs.realpathSync(process.cwd()),prefix='coordination/engineering/additive-native-gap-batch-20261008/composition-v2/';
const {ImmutableReader,loadSelection,loadBaseSelection}=await import('../../../scripts/check-effective-geographic-regression.mjs');
const {prepareCurrentRebindDestination,captureCurrentRebindProducts,validateCurrentRebindPlan,completePriorConservationFrame}=await import('./capture-current-rebind.mjs');
const {nativeBaseSelection,valueSha,normaliseRetainedRepairLedger}=await import('../selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs');
const token=prepareCurrentRebindDestination(root,command[3]);
const invocation=Object.freeze({});
function completedPriorFrame(){
const reader=new ImmutableReader(root,head,{gitExecutable:before.runtime.find(p=>p.role==='git').path,invocation});
// Explicit original products are whole immutable plan operands. Historical
// plans retain their literal original paths and default selected revision.
// Future composition inputs are not needed to authenticate the selected bank.
// Authenticate the selected bank before opening the immutable registry/ledger
// needed by conservation below.
const priorSnapshot=loadSelection(reader);demand(priorSnapshot,'Missing actual selected native bank');
let registry,originalLedger;
if(Object.hasOwn(plan,'original_inputs')){
 demand(Array.isArray(plan.original_inputs)&&plan.original_inputs.length===2,'Require complete original registry/ledger descriptors');
 [registry,originalLedger]=plan.original_inputs.map(pin=>{
  demand(pin&&Object.keys(pin).sort().join(',')==='bytes,commit,git_blob_oid,mode,path,sha256'&&pin.mode==='100644'&&/^[a-f0-9]{40}$/.test(pin.commit)&&/^[a-f0-9]{40}$/.test(pin.git_blob_oid)&&Number.isSafeInteger(pin.bytes)&&pin.bytes>0&&/^[a-f0-9]{64}$/.test(pin.sha256),'Incomplete original operand');
  const actual=reader.descriptor(pin.path,pin.commit);
  demand(actual.mode===pin.mode&&actual.git_blob_oid===pin.git_blob_oid&&actual.bytes===pin.bytes,'Original operand mode/OID/bytes differ');
  return reader.json(pin.path,{version:pin.commit,expected:pin.sha256});
 });
}else{
 const registryPin=reader.descriptor(prefix+'original-registry.json'),ledgerPin=reader.descriptor(prefix+'composed-original-ledger.json');
 registry=reader.json(registryPin.path,{expected:plan.authority_registry_sha256});originalLedger=reader.json(ledgerPin.path);
}
demand(valueSha(registry)===plan.authority_registry_sha256,'Whole original registry differs');
validateCurrentRebindPlan(plan,{executionCommit:head,baseSelection:plan.base_selection,registry,originalRows:[...normaliseRetainedRepairLedger(originalLedger,registry).rows.values()],executedCode:before.code});
// Base acquisition retains its actual complete input and conservation custody.
const marker=completePriorConservationFrame(priorSnapshot,registry,originalLedger);
return {registry,originalLedger,marker};
}
const {registry,originalLedger,marker:priorMarker}=completedPriorFrame();
const freshReader=new ImmutableReader(root,head,{gitExecutable:before.runtime.find(p=>p.role==='git').path,invocation});
const snapshot=loadBaseSelection(freshReader);demand(snapshot,'Missing actual fresh base bank');
const basePhase={kind:'complete-selected-base-acquisition-v1',inputs:structuredClone([...freshReader.inventory.values()].filter(pin=>pin.whole_body_consumed===true))};
snapshot.acquisitionPhases=[basePhase];
demand(valueSha(nativeBaseSelection(snapshot.selection))===valueSha(plan.base_selection),'Actual selected native base differs from issued plan');
const result=captureCurrentRebindProducts({destination:token,snapshot,plan,registry,originalLedger,executionCommit:head,executedCode:before.code,executionPreUse:input,priorMarker});
const publication={version:1,kind:'current-rebind-child-publication-v1',execution_commit:head,request_sha256:result.products.request.sha256,publication_sha256:result.products.publication.sha256,result_sha256:result.products.result.sha256};process.stdout.write(JSON.stringify(publication)+'\n');
