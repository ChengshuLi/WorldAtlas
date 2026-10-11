// Bounded cold producer API. A separately admitted launcher authenticates its
// complete import/runtime closure before import and records external operation.
// This module cannot issue an operating certificate or select a release.
import fs from 'node:fs';import path from 'node:path';
import {ImmutableReader} from '../../../scripts/check-effective-geographic-regression.mjs';
import {CURRENT_REBIND_CODE,normaliseRetainedRepairLedger,nativeBaseSelection,requirePriorAdditiveConservation,readRetainedRegistryAuthority,acquireCurrentRebindOperands,currentRebindSourceView,reclaimCompletedRebindFrame,valueBytes,valueSha} from '../selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const FILE=33554432,PHASE=268435456,prepared=new WeakSet(),completedPrior=new WeakMap();
const demand=(v,m)=>{if(!v)throw Error(m);},same=(a,b)=>valueBytes(a).equals(valueBytes(b));
const exists=p=>{try{return fs.lstatSync(p);}catch(e){if(e.code==='ENOENT')return null;throw e;}};
const ordinaryAncestors=p=>{let current=path.parse(p).root;for(const part of p.slice(current.length).split(path.sep)){if(!part)continue;current=path.join(current,part);const s=exists(current);demand(s&&s.isDirectory()&&!s.isSymbolicLink(),'Require ordinary existing output ancestor');}};
export function prepareCurrentRebindDestination(root,destination){
 demand(typeof root==='string'&&path.isAbsolute(root)&&path.resolve(root)===root&&typeof destination==='string'&&path.isAbsolute(destination)&&path.resolve(destination)===destination,'Require canonical absolute owned output paths');
 const base=path.join(root,'.cache'),relative=path.relative(base,destination);demand(relative&&!relative.startsWith('..')&&!path.isAbsolute(relative)&&!exists(destination),'Require fresh owned output destination');ordinaryAncestors(path.dirname(destination));
 const token=Object.freeze({root,destination});prepared.add(token);return token;
}
export function validateCurrentRebindPlan(plan,{executionCommit,baseSelection,registry,originalRows,executedCode}){
 const explicit=plan&&Object.hasOwn(plan,'original_inputs');
 demand(plan&&Object.keys(plan).filter(k=>k!=='original_inputs').sort().join(',')==='authority_registry_sha256,base_selection,executed_code,execution_commit,kind,limits,original_patch_sha256s,original_rows_sha256,predecessor_proof,target_sources,version','Foreign actual issued rebind plan');
 if(explicit)demand(Array.isArray(plan.original_inputs)&&plan.original_inputs.length===2&&new Set(plan.original_inputs.map(p=>p?.path)).size===2&&plan.original_inputs.every(p=>p&&Object.keys(p).sort().join(',')==='bytes,commit,git_blob_oid,mode,path,sha256'&&p.mode==='100644'&&typeof p.path==='string'&&!p.path.includes('\\')&&!p.path.split('/').some(s=>!s||s==='.'||s==='..')&&/^[a-f0-9]{40}$/.test(p.commit)&&/^[a-f0-9]{40}$/.test(p.git_blob_oid)&&Number.isSafeInteger(p.bytes)&&p.bytes>0&&p.bytes<=FILE&&/^[a-f0-9]{64}$/.test(p.sha256)),'Missing complete original input descriptors');
 demand(plan.version===1&&plan.kind==='issued-current-rebind-acquisition-plan-v1'&&plan.execution_commit===executionCommit&&/^[a-f0-9]{40}$/.test(executionCommit)&&same(plan.base_selection,baseSelection)&&plan.authority_registry_sha256===valueSha(registry)&&plan.original_rows_sha256===valueSha(originalRows)&&same(plan.executed_code,executedCode)&&same(executedCode.map(p=>p.path),CURRENT_REBIND_CODE),'Actual planned source/method/selected identity differs');
 demand(plan.limits&&Object.keys(plan.limits).sort().join(',')==='complete_phase_bytes,descriptors,output_bytes,rss_bytes,sampled_stop_bytes,wall_seconds'&&Object.values(plan.limits).every(n=>Number.isSafeInteger(n)&&n>0)&&plan.limits.complete_phase_bytes<=PHASE&&plan.limits.descriptors<=512&&plan.limits.output_bytes<=4194304&&plan.limits.rss_bytes<=536870912&&plan.limits.sampled_stop_bytes<=402653184&&plan.limits.sampled_stop_bytes<=plan.limits.rss_bytes,'Planned complete phase/operating/output bounds differ');
 demand(Array.isArray(plan.target_sources)&&plan.target_sources.length>0&&Array.isArray(plan.original_patch_sha256s)&&plan.original_patch_sha256s.length===registry.entries.length,'Missing complete planned input roster');return plan;
}
// The complete source/native authority is authenticated before projection.
// Only the already-proven selected-hook custody fields escape this completed
// frame; source rows/programme presentation are not used by capture/rebind.
function completedOriginalAuthority(reader,entry){
 const proof=readRetainedRegistryAuthority(reader,entry);
 return Object.freeze({authority_sha256:proof.authority_sha256,rule_sha256:proof.rule_sha256,
  source_scope_ids:proof.source_scope_ids,native_proof:proof.native_proof,
  original_ledger:proof.original_ledger,pins:proof.pins,original_pins:proof.original_pins});
}
function originalOperands(reader,registry,ledger,snapshot,executionMetadata){
 const normalized=normaliseRetainedRepairLedger(ledger,registry),proofs=[];
 for(const entry of registry.entries){
  // All already returned source/authority/owner values remain charged while
  // another whole original authority frame is opened by the trusted reader.
  reader.metadataBytes=(executionMetadata.priorCarryBytes??0)+8*1048576+2*(snapshot.metadataBytes+valueBytes({registry,ledger,proofs,executionMetadata,reader_inventory:[...reader.inventory]}).length)+(snapshot.acquisition_buffer_bytes??0);reader.outputBytes=4194304;reader.phase();
  proofs.push(completedOriginalAuthority(reader,entry));
  demand(valueBytes(proofs).length<=2097152,'Complete returned original authority views exceed prospective carry bound');
  // The authority call and carry measurement have returned; proofs stay live.
  reclaimCompletedRebindFrame();
 }
 const expected=new Map();for(const proof of proofs)for(const row of proof.original_ledger.rows){demand(!expected.has(row.component_id),'Repeated original complete authority component');expected.set(row.component_id,{row,proof});}
 demand(ledger.rows.length===expected.size&&ledger.rows.every(row=>{const prior=expected.get(row.component_id);if(!prior)return false;const {authority_sha256,rule_sha256,...literal}=row;return authority_sha256===prior.proof.authority_sha256&&rule_sha256===prior.proof.rule_sha256&&same(literal,prior.row); }),'Composed ledger changes original scope/exception/primitive authority');
 // Complete ledger/patch authentication above has finished. Duplicate original
 // ledgers and native presentation graphs do not escape this helper frame.
 return {rows:[...normalized.rows.values()],patches:proofs.flatMap(p=>p.native_proof.native_patches),proofs:proofs.map(proof=>Object.freeze({authority_sha256:proof.authority_sha256,rule_sha256:proof.rule_sha256,source_scope_ids:proof.source_scope_ids,pins:proof.pins,original_pins:proof.original_pins}))};
}
// Ephemeral private completion evidence; never a persisted certificate or
// caller-authored approval. No snapshot/reader/owner/source graph escapes.
const PRIOR_MARKER_MAX=1048576;
const priorOwnerIdentity=snapshot=>({bounds:snapshot.manifest.bounds,original_bounds:snapshot.manifest.original_assets.bounds,owners:snapshot.owners.length});
export function completePriorConservationFrame(snapshot,registry,originalLedger,executionMetadata){
 demand(snapshot?.reader instanceof ImmutableReader,'Require genuine completed prior reader');
 currentRebindSourceView(snapshot);
 requirePriorAdditiveConservation(snapshot,registry,originalLedger);
 const reader=snapshot.reader;
 // The prior load helper has returned. Full parsed prior graphs are still live
 // during these identities; small complete marker/canonical scratch is reserved.
 reader.metadataBytes=8*1048576+2*snapshot.metadataBytes+2*valueBytes({registry,originalLedger,executionMetadata,inventory:[...reader.inventory],phases:snapshot.acquisitionPhases}).length+4*PRIOR_MARKER_MAX+(snapshot.acquisition_buffer_bytes??0);reader.phase();
 const record={repo:reader.repo,commit:reader.version,selection_sha256:valueSha(snapshot.selection),manifest_sha256:valueSha(snapshot.manifest),owner_identity:priorOwnerIdentity(snapshot),registry_sha256:valueSha(registry),ledger_sha256:valueSha(originalLedger),prior_phases:structuredClone(snapshot.acquisitionPhases),prior_inventory:[...reader.inventory.values()].map(pin=>({...pin})),completion_phase_bytes:reader.used};
 const limit=executionMetadata.plan.limits.complete_phase_bytes;
 demand(Number.isSafeInteger(limit)&&limit>0&&limit<=PHASE&&record.prior_phases.length>0&&record.prior_phases.every(p=>Number.isSafeInteger(p.complete_phase_bytes)&&p.complete_phase_bytes>0&&p.complete_phase_bytes<=limit)&&record.completion_phase_bytes<=limit,'Completed prior phase exceeds issued child bound: '+JSON.stringify({limit,completion_phase_bytes:record.completion_phase_bytes,phases:record.prior_phases.map((p,index)=>({index,kind:p.kind,complete_phase_bytes:p.complete_phase_bytes}))}));
 const raw=valueBytes(record);demand(raw.length<=PRIOR_MARKER_MAX,'Complete private prior marker exceeds bound');
 const freeze=v=>{if(v&&typeof v==='object'){for(const child of Object.values(v))freeze(child);Object.freeze(v);}return v;};freeze(record);
 const token=Object.freeze({});completedPrior.set(token,{record,sha256:valueSha(record),bytes:raw.length});return token;
}
function consumeCompletedPrior(token,snapshot,registry,originalLedger,plan){
 const completed=completedPrior.get(token);demand(completed&&completed.bytes<=PRIOR_MARKER_MAX&&valueSha(completed.record)===completed.sha256,'Require unchanged privately completed prior conservation');
 currentRebindSourceView(snapshot);
 const p=completed.record;
 const limit=plan?.limits?.complete_phase_bytes;demand(Number.isSafeInteger(limit)&&limit>0&&limit<=PHASE&&p.prior_phases.every(p=>p.complete_phase_bytes<=limit)&&p.completion_phase_bytes<=limit,'Completed prior phase exceeds current issued child bound');
 demand(snapshot.reader.repo===p.repo&&snapshot.reader.version===p.commit&&valueSha(snapshot.selection)===p.selection_sha256&&valueSha(snapshot.manifest)===p.manifest_sha256&&same(priorOwnerIdentity(snapshot),p.owner_identity)&&valueSha(registry)===p.registry_sha256&&valueSha(originalLedger)===p.ledger_sha256,'Fresh base differs from completed prior conservation');
 return {record:p,carriedBytes:2*completed.bytes};
}

export function captureCurrentRebindProducts({destination,snapshot,plan,registry,originalLedger,executionCommit,executedCode,executionPreUse,priorMarker}){
 demand(prepared.has(destination)&&snapshot?.reader instanceof ImmutableReader,'Require prepared owned destination and actual immutable reader');
 let priorCarryBytes=0,priorCompletion=null;
 if(priorMarker===undefined)requirePriorAdditiveConservation(snapshot,registry,originalLedger);
 else{const prior=consumeCompletedPrior(priorMarker,snapshot,registry,originalLedger,plan);priorCarryBytes=prior.carriedBytes;priorCompletion=prior.record;}
 const plannedRows=[...normaliseRetainedRepairLedger(originalLedger,registry).rows.values()];
 validateCurrentRebindPlan(plan,{executionCommit,baseSelection:nativeBaseSelection(snapshot.selection),registry,originalRows:plannedRows,executedCode});
 // Reuse the stock privately registered source view before original authority
 // bodies can be opened; its complete selected metadata remains carried.
 currentRebindSourceView(snapshot);
 const {rows,patches,proofs}=originalOperands(snapshot.reader,registry,originalLedger,snapshot,{plan,executionPreUse,executedCode,priorCarryBytes,priorCompletion});
 demand(same(rows,plannedRows),'Original authenticated authority rows differ from admitted plan');
 demand(same(plan.original_patch_sha256s,patches.map(valueSha)),'Cold plan changes complete original native output roster');
 // The original-authority frame and complete row/patch checks have returned;
 // only needed rows, patches and compact custody remain live and charged.
 reclaimCompletedRebindFrame();
 const acquired=acquireCurrentRebindOperands(snapshot,registry,rows,patches,{targetSources:plan.target_sources,predecessorProof:plan.predecessor_proof,carriedMetadataBytes:priorCarryBytes+2*valueBytes({plan,proofs,originalLedger,executedCode,executionPreUse}).length});
 demand(acquired.acquisition_phases.every(p=>p.complete_phase_bytes<=plan.limits.complete_phase_bytes&&p.descriptors<=plan.limits.descriptors),'Actual acquisition exceeds admitted planned phase: '+JSON.stringify({limits:{complete_phase_bytes:plan.limits.complete_phase_bytes,descriptors:plan.limits.descriptors},phases:acquired.acquisition_phases.flatMap((p,index)=>p.complete_phase_bytes>plan.limits.complete_phase_bytes||p.descriptors>plan.limits.descriptors?[{index,kind:p.kind,complete_phase_bytes:p.complete_phase_bytes,descriptors:p.descriptors}]:[])}));
 // The complete acquisition/result helper has returned. Its table/group and
 // canonical scratch may be reclaimed; acquired proofs/snapshot stay live and charged.
 reclaimCompletedRebindFrame();
 const request={version:1,kind:'issued-native-additive-current-bank-rebind-v1',execution_commit:executionCommit,executed_code:executedCode,base_selection:nativeBaseSelection(snapshot.selection),authority_registry_sha256:valueSha(registry),original_rows:rows,original_patch_sha256s:patches.map(valueSha),current_targets:acquired.current_targets,current_rows:acquired.current_rows,acquisition:acquired.acquisition,execution:{command:executionPreUse.command,pre_use:executionPreUse.pre_use},size:snapshot.manifest.size,limits:plan.limits};
 const result=acquired.result,facts={version:1,kind:'native-additive-current-bank-rebind-facts-v1',execution_commit:executionCommit,request_sha256:valueSha(request),result_sha256:valueSha(result),complete_phase_bytes:Math.max(...acquired.acquisition_phases.map(p=>p.complete_phase_bytes)),descriptors:Math.max(...acquired.acquisition_phases.map(p=>p.descriptors)),acquisition_sha256:valueSha(acquired.acquisition),acquisition_phases:acquired.acquisition_phases};
 // These local output pins deliberately omit commit/OID: publication custody
 // is bound in a separate finished step after genuine Git retention. No future
 // or fabricated publication commit is claimed by a cold producer.
 const pin=(name,body)=>({path:name+'.json',bytes:valueBytes(body).length,sha256:valueSha(body)});
 const publication={version:1,kind:'native-additive-current-bank-rebind-publication-v1',execution_commit:executionCommit,request_sha256:valueSha(request),outputs:{facts:pin('facts',facts),result:pin('result',result)}};
 const bodies={request,result,facts,publication},encoded=Object.entries(bodies).map(([name,b])=>({name,raw:valueBytes(b)})),combined=encoded.reduce((n,p)=>n+p.raw.length,0);
 demand(encoded.every(p=>p.raw.length<=FILE)&&combined<=plan.limits.output_bytes,'Complete cold products exceed prospective output bound before writes');
 demand(!exists(destination.destination),'Destination appeared during source acquisition');ordinaryAncestors(path.dirname(destination.destination));fs.mkdirSync(destination.destination,{mode:0o700});
 for(const {name,raw}of encoded){const fd=fs.openSync(path.join(destination.destination,name+'.json'),fs.constants.O_WRONLY|fs.constants.O_CREAT|fs.constants.O_EXCL|fs.constants.O_NOFOLLOW,0o644);try{fs.writeFileSync(fd,raw);}finally{fs.closeSync(fd);}}
 return {execution_commit:executionCommit,output_directory:destination.destination,products:Object.fromEntries(Object.entries(bodies).map(([name,b])=>[name,pin(name,b)])),combined_bytes:combined,acquisition_phases:acquired.acquisition_phases,source_inventory:acquired.input_inventory,limits:['Actual cold data acquisition/output only. External operating qualification, two-run equality and genuine immutable publication binding remain required. No selection or physical approval.']};
}
