import assert from 'node:assert/strict';
import {PIXEL_TARGETS} from './pixel-audit-continuation.mjs';
import {OLD_FOOTPRINT,NEW_FOOTPRINT} from './native-v9-manifest.mjs';
// Structural continuation of the actually qualified complete geometry proof.
// The issuing caller authenticates every whole proof/context/owner source body.
export function prepareGeometryReceipt({owners,originalTargets,currentTargets,geometryProof,sourceEvidence}){
 assert.equal(owners.length,49625);assert.equal(new Set(owners.map(p=>p.id)).size,49625);
 for(let i=0;i<owners.length;i++)assert.equal(owners[i].index,i+1);
 assert.deepEqual(originalTargets.map(p=>p.id),PIXEL_TARGETS);assert.deepEqual(currentTargets.map(p=>p.id),PIXEL_TARGETS);
 assert.equal(geometryProof.issue,1520);assert.equal(geometryProof.world_rows,49625);assert.equal(geometryProof.unchanged_full_rows,49623);
 assert.deepEqual(geometryProof.changed_ids,PIXEL_TARGETS);assert.equal(geometryProof.current_pointers_activated,false);
 assert.equal(geometryProof.before_part29_sha256,'c34114912dc620dce0821e251877470b5a83385ab3bf1284408f077b78bbdec8');
 assert.equal(geometryProof.after_part29_sha256,'4eca02f85d5e3a0974a96a38d59e46b0b71b41d2513dcf20ab27eb17fd5a0b4c');
 assert.equal(geometryProof.exact_constructions.length,2);assert.equal(geometryProof.constructed_components.length,2);assert.equal(geometryProof.construction_failed_components.length,1);assert.equal(geometryProof.source_rule_failed_components.length,4);
 assert(Array.isArray(sourceEvidence)&&sourceEvidence.length>0);for(const p of sourceEvidence){assert(/^https:\/\//.test(p.url));assert(/^[a-f0-9]{64}$/.test(p.source_sha256));}
 const archives=[],relationships=[];
 for(let i=0;i<2;i++){
  const before=originalTargets[i],after=currentTargets[i],construction=geometryProof.exact_constructions.find(p=>p.target_id===before.id);
  assert.equal(before.pixelIndex,[6666,6757][i]);assert.deepEqual({...before,geometry:after.geometry},after);
  assert.deepEqual(construction.before,before.geometry);assert.deepEqual(construction.after,after.geometry);
  assert.equal(construction.loss_empty,true);assert.equal(construction.gain_equals_complete_candidates,true);
  assert.equal(owners[before.pixelIndex-1].id,before.id);
  archives.push({id:before.id,feature:{id:before.id,geometry:before.geometry,properties:{...before.properties,id:before.id}}});
  relationships.push({proposal_id:'arctic-retained-land-1520:'+before.id,kind:'source-backed-retain',before_ids:[before.id],after_ids:[before.id],history_transfer:false,source_components:construction.component_ids});
 }
 return {version:1,issue:1520,geometry_stage_validated:true,historical_claims_transferred:false,
  before_footprints_sha256:OLD_FOOTPRINT,after_footprints_sha256:NEW_FOOTPRINT,
  changed_ids:[...PIXEL_TARGETS],removed_ids:[],added_ids:[],reused_ids:owners.filter(p=>!PIXEL_TARGETS.includes(p.id)).map(p=>p.id),archives,relationships,source_evidence:sourceEvidence,
  source_approval_transferred:false,water_status:'unverified',physical_authority:'unapproved',
  construction_failed_components:geometryProof.construction_failed_components,source_rule_failed_components:geometryProof.source_rule_failed_components,
  limits:geometryProof.limitations,source_proof_kind:geometryProof.stage,full_geographic_audit_claimed:false,history_transfer:'none'};
}
