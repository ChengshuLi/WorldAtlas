// Preserve original pending certificates and explicitly mark their v8 limitation.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {footprintHash} from '../../../scripts/check-prepared.mjs';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {immutableReader,BEFORE,AFTER,TARGETS} from './native-producer.mjs';
import {assertResearchImportsReady} from '../../../src/regional-import-gate.js';
import {prepareReferenceMacroBinding} from '../../../scripts/prepare-reference-macro-binding.mjs';
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const json=value=>Buffer.from(JSON.stringify(value)+'\n');
export function disposeCertificates(repo,baseline,{hierarchy,before,after,release}) {
  const reader=immutableReader(repo,baseline),prefix='data/macro-foundation/eastern-two-gap-repair-20261006/';
  const certificate=reader.object('data/macro-foundation/macro-certificate.json');
  const handoffs=reader.object('data/macro-foundation/regional-handoffs.json.gz');
  const gate=reader.object('data/research-geography-gate.json');
  assert.equal(certificate.status,'reference-compatible-pending-publication');
  assert.equal(certificate.release.version,6);
  for(const flag of ['publication_verified','regional_interiors_approved','new_approval_created'])assert.equal(certificate[flag],false);
  assert.equal(gate.ready_for_location_attributes,false);assert.deepEqual(gate.regions,[]);
  assert.equal(release.footprints_sha256,AFTER);assert.equal(release.version,8);
  assert.equal(before.length,49625);assert.equal(after.length,49625);
  assert.equal(footprintHash(before),BEFORE);assert.equal(footprintHash(after),AFTER);
  assert.deepEqual(hierarchy,reader.object('data/hierarchy.json'));
  const byId=new Map(hierarchy.map(row=>[row.id,row])),locations=new Map(after.map(row=>[row.id,row]));
  const ancestors=new Set(),macros=new Set();
  for(const id of TARGETS){let parent=locations.get(id).properties.parent_id,seen=new Set();while(parent){assert(!seen.has(parent)&&byId.has(parent));seen.add(parent);ancestors.add(parent);const unit=byId.get(parent);if(['region','subcontinent','continent'].includes(unit.level))macros.add(parent);parent=unit.parent_id;}}
  assert.equal(macros.size,3,'Complete shared affected macro ancestry required');
  const disposition={issue:1295,kind:'retained-pending-certificate-reference-invalidation',original_certificate_release:certificate.release,
    before_footprints_sha256:BEFORE,after_release:Object.fromEntries(['id','version','footprints_sha256','hierarchy_sha256'].map(k=>[k,release[k]])),
    changed_subject_ids:[...TARGETS],all_affected_ancestor_ids:[...ancestors].sort(),affected_macro_ids:[...macros].sort(),
    original_certificate_sha256:sha(reader.read('data/macro-foundation/macro-certificate.json')),
    original_handoffs_sha256:sha(reader.read('data/macro-foundation/regional-handoffs.json.gz')),
    reference_compatibility_verified:false,source_coverage_approved:false,publication_verified:false,
    new_approval_created:false,regional_interiors_approved:false,location_attribute_imports_ready:false,
    limits:['Original pending v6 certificate and its full approval/source scope are preserved, not promoted to v8.',
      'The complete v8 reference has changed descendant geometries; old envelope compatibility is not a v8 certificate.',
      'Existing absent regional approvals and location-attribute import restrictions remain closed.']};
  const nextCertificate={...certificate,reference_invalidation:disposition};
  const nextHandoffs={...handoffs,reference_invalidation:disposition};
  const nextGate={...gate,reason:'The two reviewed physical reference corrections are staged in v8. Original pending v6 macro certificates have no verified v8 envelope compatibility; no complete regional branches are approved and location-attribute imports remain closed.',
    macro_boundaries:{...gate.macro_boundaries,pending_macro_certificate_sha256:sha(json(nextCertificate))},reference_correction_disposition:disposition};
  // Actual canonical consumers must reject both existing and falsely opened gates.
  assert.throws(()=>assertResearchImportsReady(nextGate,{regionIds:[...macros]}),/Research imports are paused/);
  assert.throws(()=>assertResearchImportsReady({...nextGate,ready_for_location_attributes:true},{regionIds:[...macros]}),/not approved for location research imports/);
  const negativeRoot=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'1295-original-pending-macro-')));
  try {
    fs.mkdirSync(negativeRoot+'/macro-foundation');
    for(const name of ['macro-certificate.json','approved-boundary-decisions.json','review-index.json','regional-handoffs.json.gz'])
      fs.writeFileSync(negativeRoot+'/macro-foundation/'+name,reader.read('data/macro-foundation/'+name),{flag:'wx'});
    assert.throws(()=>prepareReferenceMacroBinding({data:negativeRoot,before:{proof:{footprints_sha256:BEFORE,hierarchy_sha256:release.hierarchy_sha256}},after:{proof:{footprints_sha256:AFTER,hierarchy_sha256:release.hierarchy_sha256}},release,receiptSha256:'0'.repeat(64)}),/exact prior approved\/published/);
  } finally {fs.rmSync(negativeRoot,{recursive:true,force:true});} 
  const files=new Map([
    [prefix+'original-macro-certificate.json',reader.read('data/macro-foundation/macro-certificate.json')],
    [prefix+'original-regional-handoffs.json.gz',reader.read('data/macro-foundation/regional-handoffs.json.gz')],
    [prefix+'original-research-geography-gate.json',reader.read('data/research-geography-gate.json')],
    [prefix+'reference-invalidation.json',json(disposition)],
    ['data/macro-foundation/macro-certificate.json',json(nextCertificate)],
    ['data/macro-foundation/regional-handoffs.json.gz',gzipSync(json(nextHandoffs),{level:9})],
    ['data/research-geography-gate.json',json(nextGate)]
  ]);
  return {files,disposition,input_pins:reader.pins(),closed_consumer_controls:3};
}
