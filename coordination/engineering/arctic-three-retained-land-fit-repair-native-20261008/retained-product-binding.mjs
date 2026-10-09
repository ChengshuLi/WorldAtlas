import assert from 'node:assert/strict';
import {requireValidatedGeometryMigrations} from '../../../scripts/prepare-geographic-release.mjs';
import {requireConsumedArcticArtifacts} from './qualified-artifact-consumer.mjs';
const BEFORE='b9a3c8bf375217dba3a50d1a022ec7e4ac6c6f1cdedff22845da953c805b7433';
const AFTER='2deeff1457ff9238cb3dbe599e9a858dcce29d8ba88e2a66abe2785ddec0aed9';
// Retained same-identity factual products do not inherit a new historical claim.
// Their original inputs, payloads, sources and dispositions remain literal.
export function continueRetainedProductIndex(index,{context,kind}){
 assert(['prepared-evidence','reference-attributes','ownership-history'].includes(kind));
 const artifact=context.kind==='authenticated-qualified-artifact-consumption-v1';
 if(artifact)requireConsumedArcticArtifacts(context);
 const step=artifact?context.steps.at(-1):null;
 const proof=artifact?{changedIds:new Set(step.receipt.changed_ids),retiredIds:new Set(step.receipt.removed_ids),addedIds:new Set(step.receipt.added_ids),proofs:[{receipt:step.receipt,receipt_sha256:step.receipt_sha256}],pairs:step.receipt.relationships.flatMap(r=>(r.identity_pairs??r.before_ids.map(id=>({before_id:id,after_id:id}))).map(p=>({old_entity_id:p.before_id,new_entity_id:p.after_id,change_type:'retain',history_transfer:'none'})))}:context.geometryValidation;
 if(!artifact)requireValidatedGeometryMigrations(proof);
 assert.equal(index.footprints_sha256,BEFORE);assert.deepEqual([...proof.changedIds].sort(),['atlas:physical:CAN-15:NWT','atlas:physical:CAN-25:NUN']);
 assert.equal(proof.retiredIds.size,0);assert.equal(proof.addedIds.size,0);assert.equal(proof.proofs.length,1);
 const receipt=proof.proofs[0].receipt;assert.equal(receipt.before_footprints_sha256,BEFORE);assert.equal(receipt.after_footprints_sha256,AFTER);assert.equal(receipt.history_transfer,'none');
 assert.equal(proof.pairs.length,2);assert(proof.pairs.every(p=>p.old_entity_id===p.new_entity_id&&p.change_type==='retain'&&p.history_transfer==='none'));
 const next=structuredClone(index);next.footprints_sha256=AFTER;
 next.physical_association_continuation={version:1,issue:1520,kind,receipt_sha256:proof.proofs[0].receipt_sha256,predecessor_footprints_sha256:BEFORE,successor_footprints_sha256:AFTER,changed_ids:[...proof.changedIds].sort(),history_transfer:'none',payloads_and_original_inputs_unchanged:true,new_factual_import:false};
 const preserved=structuredClone(next);delete preserved.physical_association_continuation;preserved.footprints_sha256=BEFORE;assert.deepEqual(preserved,index);
 return next;
}
