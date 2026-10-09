import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {admitPhase,authenticateAdmittedBody,readAdmittedBody} from './phase-admission.mjs';
import {prepareGeometryReceipt} from './geometry-receipt.mjs';
import {continueRelease,hashCompleteMemberships,successorIdentity} from './release-successor.mjs';
const sha=body=>createHash('sha256').update(body).digest('hex');

// One finished full-original validation phase. This emits compact headers and
// the geometry receipt, not a second full copy of the membership ledger.
export async function issueSuccessorRelease(plan,outputValue){
 assert(typeof outputValue==='string'&&!outputValue.split(path.sep).includes('..'));
 const output=path.resolve(outputValue);assert(output.startsWith(path.join(process.cwd(),'.cache')+path.sep));
 for(let current=output;;current=path.dirname(current)){
  try{const stat=fs.lstatSync(current);assert(!stat.isSymbolicLink());assert.notEqual(current,output);assert(stat.isDirectory());}
  catch(error){if(error.code!=='ENOENT')throw error;}if(current===path.dirname(current))break;
 }
 assert.equal(plan.kind,'complete-v8-membership-validation-v9-header-issuance');
 assert.equal(process.execPath,plan.runtime.path);assert.equal(process.version,plan.runtime.version);
 assert.deepEqual(process.execArgv,[]);assert(!process.env.NODE_OPTIONS&&!process.env.NODE_PATH);
 assert.equal(plan.source_head,process.env.WORLDATLAS_SELECTED_NATIVE_HEAD);
 assert.equal(sha(JSON.stringify(plan)),process.env.WORLDATLAS_SELECTED_NATIVE_PLAN_SHA256);
 assert.equal(plan.members.length,340);
 const admission=admitPhase({inputs:plan.inputs,runtime:plan.runtime,outputReserve:plan.output_reserve,metadataBytes:plan.metadata_bytes});
 const sources=plan.code.map(pin=>readAdmittedBody(admission,pin.path).toString());
 const functions=[issueSuccessorRelease,prepareGeometryReceipt,continueRelease,hashCompleteMemberships,successorIdentity,
  admitPhase,authenticateAdmittedBody,readAdmittedBody];
 const fingerprints=functions.map(fn=>Function.prototype.toString.call(fn));
 const guard=()=>{
  assert.deepEqual(functions.map(fn=>Function.prototype.toString.call(fn)),fingerprints);
  for(const body of fingerprints)assert(sources.some(source=>source.includes(body)));
  for(const pin of plan.code)authenticateAdmittedBody(admission,pin.path);
  authenticateAdmittedBody(admission,plan.runtime.path);
 };
 guard();const started=new Date().toISOString();
 const decode=pin=>{
  const encoded=readAdmittedBody(admission,pin.path),decoded=gunzipSync(encoded,{maxOutputLength:pin.decoded_bytes});
  assert.equal(decoded.length,pin.decoded_bytes);assert.equal(sha(decoded),pin.decoded_sha256);return JSON.parse(decoded);
 };
 const memberIndex=JSON.parse(readAdmittedBody(admission,plan.member_index.path));
 assert.equal(memberIndex.files.length,340);assert.equal(memberIndex.issue,1295);
 const registry=decode(plan.registry),old=registry.releases.at(-1),memberships=[];
 const names=new Set();
 for(const pin of plan.members){
  assert(!names.has(pin.relative));names.add(pin.relative);
  const original=memberIndex.files.find(row=>row.path===pin.relative);assert(original);
  assert.equal(original.bytes,pin.bytes);assert.equal(original.sha256,pin.sha256);assert.equal(original.mode,'100644');
  assert.equal(original.original_binding.decoded_bytes,pin.decoded_bytes);
  assert.equal(original.original_binding.decoded_sha256,pin.decoded_sha256);
  const descriptor=registry.batches.find(row=>'data/geographic-releases/'+row.path===pin.relative);assert(descriptor);
  assert.equal(descriptor.sha256,pin.sha256);assert.equal(descriptor.payload_sha256,pin.decoded_sha256);
  const batch=decode(pin);assert.equal(batch.release_id,old.id);assert.equal(batch.memberships.length,original.original_binding.memberships);
  assert(!batch.release&&!batch.changes);memberships.push(...batch.memberships);
 }
 assert.deepEqual([...names].sort(),memberIndex.files.map(pin=>pin.path).sort());
 const changedBatch=decode(plan.changes);assert.equal(changedBatch.release_id,old.id);
 const originalChangePin=registry.batches.find(pin=>pin.path==='8-changes-0.json.gz');
 assert.equal(originalChangePin.sha256,plan.changes.sha256);assert.equal(originalChangePin.payload_sha256,plan.changes.decoded_sha256);
 const owners=plan.owner_structures.flatMap(pin=>JSON.parse(readAdmittedBody(admission,pin.path)).owners);
 const originalContext=decode(plan.original_context);assert.equal(originalContext.length,1500);
 const currentTargets=JSON.parse(readAdmittedBody(admission,plan.current_targets.path));
 const geometryProof=JSON.parse(readAdmittedBody(admission,plan.geometry_proof.path));
 const originalTargets=currentTargets.map(after=>{const found=originalContext.filter(before=>before.id===after.id);assert.equal(found.length,1);return found[0];});
 const receipt=prepareGeometryReceipt({owners,originalTargets,currentTargets,geometryProof,sourceEvidence:plan.source_evidence}),receiptBody=Buffer.from(JSON.stringify(receipt)+'\n');
 const result=await continueRelease({registry,memberships,changes:changedBatch.changes,migrationReceipt:receipt,
  receiptSha:sha(receiptBody),proposalCommit:plan.proposal_commit,predecessorManifestSha:plan.registry.sha256,referenceDate:plan.reference_date});
 assert.equal(result.memberships,memberships);
 const header={version:1,issue:1520,kind:plan.kind,release:result.release,source:result.source,changes:result.changes,
  predecessor_manifest_sha256:plan.registry.sha256,original_membership_sha256:old.membership_sha256,
  original_location_ids_sha256:old.location_ids_sha256,membership_count:memberships.length,
  memberships_reused_as_complete_records:true,history_transferred:false,activated:false,
  complete_member_inputs:plan.members.map(({path,...pin})=>pin),migration_receipt_sha256:sha(receiptBody)};
 const headerBody=Buffer.from(JSON.stringify(header)+'\n');
 for(const pin of plan.inputs)authenticateAdmittedBody(admission,pin.path);guard();
 const executionBody=Buffer.from(JSON.stringify({source_head:plan.source_head,started_at:started,completed_at:new Date().toISOString(),
  complete_phase_bytes:admission.bytes,descriptors:admission.descriptors,scientific_algorithms_rerun:false,activation:false,
  products:[['migration-receipt.json',receiptBody],['release-header.json',headerBody]].map(([path,body])=>({path,bytes:body.length,sha256:sha(body)}))})+'\n');
 assert(receiptBody.length+headerBody.length+executionBody.length<=plan.output_reserve);
 fs.mkdirSync(output,{recursive:true});
 for(const [name,body] of [['migration-receipt.json',receiptBody],['release-header.json',headerBody],['execution.json',executionBody]])
  fs.writeFileSync(path.join(output,name),body,{flag:'wx',mode:0o644});
 return JSON.parse(executionBody);
}
