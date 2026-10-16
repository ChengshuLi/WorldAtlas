// Cold producer API. A separate launcher authenticates its
// complete import/runtime closure before import and records external operation.
// This module cannot issue an operating certificate or select a release.
import fs from 'node:fs';import path from 'node:path';
import {ImmutableReader} from '../../../scripts/check-effective-geographic-regression.mjs';
import {currentRebindCodePaths,normaliseRetainedRepairLedger,nativeBaseSelection,requirePriorAdditiveConservation,readRetainedRegistryAuthority,acquireCurrentRebindOperands,currentRebindSourceView,valueBytes,valueSha} from '../selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const prepared=new WeakSet(),completedPrior=new WeakMap();
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
 demand(plan&&Object.keys(plan).filter(k=>!['original_inputs','limits'].includes(k)).sort().join(',')==='authority_registry_sha256,base_selection,executed_code,execution_commit,kind,original_patch_sha256s,original_rows_sha256,predecessor_proof,target_sources,version','Foreign actual issued rebind plan');
 if(explicit)demand(Array.isArray(plan.original_inputs)&&plan.original_inputs.length===2&&new Set(plan.original_inputs.map(p=>p?.path)).size===2&&plan.original_inputs.every(p=>p&&Object.keys(p).sort().join(',')==='bytes,commit,git_blob_oid,mode,path,sha256'&&p.mode==='100644'&&typeof p.path==='string'&&!p.path.includes('\\')&&!p.path.split('/').some(s=>!s||s==='.'||s==='..')&&/^[a-f0-9]{40}$/.test(p.commit)&&/^[a-f0-9]{40}$/.test(p.git_blob_oid)&&Number.isSafeInteger(p.bytes)&&p.bytes>0&&/^[a-f0-9]{64}$/.test(p.sha256)),'Missing complete original input descriptors');
 currentRebindCodePaths(executedCode,{requireCurrent:true});
 demand(plan.version===1&&plan.kind==='issued-current-rebind-acquisition-plan-v1'&&plan.execution_commit===executionCommit&&/^[a-f0-9]{40}$/.test(executionCommit)&&same(plan.base_selection,baseSelection)&&plan.authority_registry_sha256===valueSha(registry)&&plan.original_rows_sha256===valueSha(originalRows)&&same(plan.executed_code,executedCode),'Actual planned source/method/selected identity differs');
 demand(Array.isArray(plan.target_sources)&&plan.target_sources.length>0&&Array.isArray(plan.original_patch_sha256s)&&plan.original_patch_sha256s.length===registry.entries.length,'Missing complete planned input roster');return plan;
}
// Encode complete canonical products before creating the destination. The
// publication is written last, so interrupted output cannot appear complete.
export function writeCurrentRebindProducts(destination,bodies){
 demand(prepared.has(destination)&&bodies&&Object.keys(bodies).sort().join(',')==='facts,publication,request,result','Complete prepared product writer required');
 const encoded=['request','result','facts','publication'].map(name=>({name,raw:valueBytes(bodies[name])}));
 demand(!exists(destination.destination),'Destination appeared during source acquisition');ordinaryAncestors(path.dirname(destination.destination));fs.mkdirSync(destination.destination,{mode:0o700});
 for(const {name,raw}of encoded){const fd=fs.openSync(path.join(destination.destination,name+'.json'),fs.constants.O_WRONLY|fs.constants.O_CREAT|fs.constants.O_EXCL|fs.constants.O_NOFOLLOW,0o644);try{fs.writeFileSync(fd,raw);}finally{fs.closeSync(fd);}}
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
function originalOperands(reader,registry,ledger){
 const normalized=normaliseRetainedRepairLedger(ledger,registry),proofs=[];
 for(const entry of registry.entries){
  proofs.push(completedOriginalAuthority(reader,entry));
 }
 const expected=new Map();for(const proof of proofs)for(const row of proof.original_ledger.rows){demand(!expected.has(row.component_id),'Repeated original complete authority component');expected.set(row.component_id,{row,proof});}
 demand(ledger.rows.length===expected.size&&ledger.rows.every(row=>{const prior=expected.get(row.component_id);if(!prior)return false;const {authority_sha256,rule_sha256,...literal}=row;return authority_sha256===prior.proof.authority_sha256&&rule_sha256===prior.proof.rule_sha256&&same(literal,prior.row); }),'Composed ledger changes original scope/exception/primitive authority');
 // Complete ledger/patch authentication above has finished. Duplicate original
 // ledgers and native presentation graphs do not escape this helper frame.
 return {rows:[...normalized.rows.values()],patches:proofs.flatMap(p=>p.native_proof.native_patches)};
}
// Ephemeral private completion evidence; never a persisted certificate or
// caller-authored approval. No snapshot/reader/owner/source graph escapes.
const priorOwnerIdentity=snapshot=>({bounds:snapshot.manifest.bounds,original_bounds:snapshot.manifest.original_assets.bounds,owners:snapshot.owners.length});
export function completePriorConservationFrame(snapshot,registry,originalLedger){
 demand(snapshot?.reader instanceof ImmutableReader,'Require genuine completed prior reader');
 currentRebindSourceView(snapshot);
 requirePriorAdditiveConservation(snapshot,registry,originalLedger);
 const reader=snapshot.reader;
 const record={repo:reader.repo,commit:reader.version,selection_sha256:valueSha(snapshot.selection),manifest_sha256:valueSha(snapshot.manifest),owner_identity:priorOwnerIdentity(snapshot),registry_sha256:valueSha(registry),ledger_sha256:valueSha(originalLedger),prior_phases:structuredClone(snapshot.acquisitionPhases),prior_inventory:[...reader.inventory.values()].filter(pin=>pin.whole_body_consumed===true).map(pin=>({...pin}))};
 const freeze=v=>{if(v&&typeof v==='object'){for(const child of Object.values(v))freeze(child);Object.freeze(v);}return v;};freeze(record);
 const token=Object.freeze({});completedPrior.set(token,{record,sha256:valueSha(record),invocation:reader.invocation});return token;
}
function consumeCompletedPrior(token,snapshot,registry,originalLedger){
 const completed=completedPrior.get(token);demand(completed&&completed.invocation===snapshot.reader.invocation&&valueSha(completed.record)===completed.sha256,'Require unchanged privately completed prior conservation');
 currentRebindSourceView(snapshot);
 const p=completed.record;
 demand(snapshot.reader.repo===p.repo&&snapshot.reader.version===p.commit&&valueSha(snapshot.selection)===p.selection_sha256&&valueSha(snapshot.manifest)===p.manifest_sha256&&same(priorOwnerIdentity(snapshot),p.owner_identity)&&valueSha(registry)===p.registry_sha256&&valueSha(originalLedger)===p.ledger_sha256,'Fresh base differs from completed prior conservation');
 for(const pin of p.prior_inventory){
  const key=pin.commit+':'+pin.path,prior=snapshot.reader.inventory.get(key);
  demand(pin.whole_body_consumed===true&&(!prior||['commit','path','mode','git_blob_oid','bytes'].every(field=>prior[field]===pin[field])
   &&(prior.sha256===undefined||prior.sha256===pin.sha256)),'Prior consumed-input custody differs');
  snapshot.reader.inventory.set(key,{...pin});
 }
 return p;
}

export function captureCurrentRebindProducts({destination,snapshot,plan,registry,originalLedger,executionCommit,executedCode,executionPreUse,priorMarker}){
 demand(prepared.has(destination)&&snapshot?.reader instanceof ImmutableReader,'Require prepared owned destination and actual immutable reader');
 if(priorMarker===undefined)requirePriorAdditiveConservation(snapshot,registry,originalLedger);
 else consumeCompletedPrior(priorMarker,snapshot,registry,originalLedger);
 const plannedRows=[...normaliseRetainedRepairLedger(originalLedger,registry).rows.values()];
 validateCurrentRebindPlan(plan,{executionCommit,baseSelection:nativeBaseSelection(snapshot.selection),registry,originalRows:plannedRows,executedCode});
 // Reuse the stock privately registered source view before original authority
 // bodies can be opened.
 currentRebindSourceView(snapshot);
 const {rows,patches}=originalOperands(snapshot.reader,registry,originalLedger);
 demand(same(rows,plannedRows),'Original authenticated authority rows differ from issued plan');
 demand(same(plan.original_patch_sha256s,patches.map(valueSha)),'Cold plan changes complete original native output roster');
 const acquired=acquireCurrentRebindOperands(snapshot,registry,rows,patches,{targetSources:plan.target_sources,predecessorProof:plan.predecessor_proof});
 const request={version:1,kind:'issued-native-additive-current-bank-rebind-v1',execution_commit:executionCommit,executed_code:executedCode,base_selection:nativeBaseSelection(snapshot.selection),authority_registry_sha256:valueSha(registry),original_rows:rows,original_patch_sha256s:patches.map(valueSha),current_targets:acquired.current_targets,current_rows:acquired.current_rows,acquisition:acquired.acquisition,execution:{command:executionPreUse.command,pre_use:executionPreUse.pre_use},size:snapshot.manifest.size};
 const result=acquired.result;
 const facts={version:1,kind:'native-additive-current-bank-rebind-facts-v1',execution_commit:executionCommit,request_sha256:valueSha(request),result_sha256:valueSha(result),acquisition_sha256:valueSha(acquired.acquisition),acquisition_phases:acquired.acquisition_phases};
 // These local output pins deliberately omit commit/OID: publication custody
 // is bound in a separate finished step after genuine Git retention. No future
 // or fabricated publication commit is claimed by a cold producer.
 const pin=(name,body)=>({path:name+'.json',bytes:valueBytes(body).length,sha256:valueSha(body)});
 const publication={version:1,kind:'native-additive-current-bank-rebind-publication-v1',execution_commit:executionCommit,request_sha256:valueSha(request),outputs:{facts:pin('facts',facts),result:pin('result',result)}};
 const bodies={request,result,facts,publication};writeCurrentRebindProducts(destination,bodies);
 return {execution_commit:executionCommit,output_directory:destination.destination,products:Object.fromEntries(Object.entries(bodies).map(([name,b])=>[name,pin(name,b)])),acquisition_phases:acquired.acquisition_phases,source_inventory:acquired.input_inventory,limits:['Actual cold data acquisition/output only. External operating qualification, two-run equality and genuine immutable publication binding remain required. No selection or physical approval.']};
}
