// Plain cold entry. The independently admitted supervisor whole-authenticates
// this file and its complete code/runtime closure before ANY dynamic import.
import fs from 'node:fs';import path from 'node:path';import {createHash} from 'node:crypto';
const demand=(v,m)=>{if(!v)throw Error(m);},sha=b=>createHash('sha256').update(b).digest('hex');
const head=process.env.WORLDATLAS_REBIND_EXECUTION_COMMIT,serialized=process.env.WORLDATLAS_REBIND_EXECUTION_PRE_USE;
demand(!process.execArgv.length&&!process.env.NODE_OPTIONS&&!process.env.NODE_PATH&&/^[a-f0-9]{40}$/.test(head??'')&&typeof serialized==='string'&&Buffer.byteLength(serialized)<=131072,'Missing/plain bounded actual execution identity');
const input=JSON.parse(serialized),before=input.pre_use,command=input.command;
demand(before&&Array.isArray(command)&&command.length===6&&command[2]===process.execPath&&command[3]===process.argv[1]&&command[4]===process.argv[2]&&command[5]===process.argv[3],'Actual entry command differs from whole executing contract');
const p=before.plan;demand(p&&p.path===command[4]&&Number.isSafeInteger(p.bytes)&&p.bytes>0&&p.bytes<=1048576&&p.mode===420&&/^[a-f0-9]{64}$/.test(p.sha256),'Bounded whole plan identity required');
for(const name of [p.path,command[5]])demand(path.isAbsolute(name)&&path.resolve(name)===name,'Canonical absolute entry paths');
let current=path.parse(p.path).root;for(const part of p.path.slice(current.length).split(path.sep)){current=path.join(current,part);const s=fs.lstatSync(current);demand(!s.isSymbolicLink(),'Ordinary plan ancestors required');}
const stat=fs.lstatSync(p.path);demand(stat.isFile()&&stat.size===p.bytes&&(stat.mode&0o777)===p.mode,'Plan stat differs before read');
const fd=fs.openSync(p.path,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW);let raw;try{raw=fs.readFileSync(fd);const held=fs.fstatSync(fd),end=fs.lstatSync(p.path);for(const k of ['dev','ino','size','mode','mtimeMs','ctimeMs'])demand(stat[k]===held[k]&&held[k]===end[k],'Plan identity drift');}finally{fs.closeSync(fd);}
demand(raw.length===p.bytes&&sha(raw)===p.sha256,'Whole raw plan differs');const plan=JSON.parse(raw);
demand(plan.execution_commit===head&&plan.limits&&Number.isSafeInteger(plan.limits.complete_phase_bytes)&&plan.limits.complete_phase_bytes<=268435456&&Number.isSafeInteger(plan.limits.output_bytes)&&plan.limits.output_bytes<=4194304,'Actual injected plan/head/admission differs before imports');
const root=fs.realpathSync(process.cwd()),prefix='coordination/engineering/additive-native-gap-batch-20261008/composition-v2/';
const {ImmutableReader,loadSelection}=await import('../../../scripts/check-effective-geographic-regression.mjs');
const {prepareCurrentRebindDestination,captureCurrentRebindProducts,validateCurrentRebindPlan}=await import('./capture-current-rebind.mjs');
const {nativeBaseSelection,valueSha,valueBytes,normaliseRetainedRepairLedger}=await import('../selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs');
const token=prepareCurrentRebindDestination(root,command[5]);
const runtimeBytes=before.runtime.filter(p=>['node','git','time'].includes(p.role)).reduce((n,p)=>n+p.bytes,0),executionBytes=before.code.reduce((n,p)=>n+2*p.bytes,0)+before.entry.bytes;
const reader=new ImmutableReader(root,head,{runtimeBytes,executionBytes,metadataBytes:8*1048576+2*(raw.length+Buffer.byteLength(serialized)),outputBytes:4194304,gitExecutable:before.runtime.find(p=>p.role==='git').path});
const registryPin=reader.descriptor(prefix+'original-registry.json'),ledgerPin=reader.descriptor(prefix+'composed-original-ledger.json');reader.admit(registryPin);reader.admit(ledgerPin);
const registry=reader.json(registryPin.path,{expected:plan.authority_registry_sha256}),originalLedger=reader.json(ledgerPin.path);demand(valueSha(registry)===plan.authority_registry_sha256,'Whole original registry differs');
validateCurrentRebindPlan(plan,{executionCommit:head,baseSelection:plan.base_selection,registry,originalRows:[...normaliseRetainedRepairLedger(originalLedger,registry).rows.values()],executedCode:before.code});
// Base acquisition remains a real independently bounded stock helper frame.
// The returned full owner/map/index and phase custody remain charged later.
reader.metadataBytes+=2*(valueBytes(registry).length+valueBytes(originalLedger).length);const snapshot=loadSelection(reader);demand(snapshot,'Missing actual selected native bank');
demand(valueSha(nativeBaseSelection(snapshot.selection))===valueSha(plan.base_selection),'Actual selected native base differs from issued plan');
const result=captureCurrentRebindProducts({destination:token,snapshot,plan,registry,originalLedger,executionCommit:head,executedCode:before.code,executionPreUse:input});
const publication={version:1,kind:'current-rebind-child-publication-v1',execution_commit:head,request_sha256:result.products.request.sha256,publication_sha256:result.products.publication.sha256,result_sha256:result.products.result.sha256};process.stdout.write(JSON.stringify(publication)+'\n');
