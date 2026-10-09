import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
const PATH='coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/migration-receipt.json';
const COMMIT='9b212c585583dc218a961b4c7ee1056a64b54726';
// Caller independently authenticates the actual immutable Git body/mode/OID.
// A proposal commit is source provenance; it is not a later output locator.
export function bindPublishedGeometryReceipt(header,raw,binding){
 assert.equal(binding.path,PATH);assert.equal(binding.commit,COMMIT);assert.equal(binding.mode,'100644');
 assert(/^[a-f0-9]{40}$/.test(binding.oid));assert.equal(binding.bytes,raw.length);
 const digest=createHash('sha256').update(raw).digest('hex');assert.equal(binding.sha256,digest);
 assert.equal(header.issue,1520);assert.equal(header.activated,false);assert.equal(header.membership_count,84833);
 assert.equal(header.migration_receipt_sha256,digest);
 const previous=header.release.metadata.geometry_migration;
 assert.equal(previous.commit,'859ca4643d61d472650dbda5a7c3682556ab78a4');
 assert.equal(previous.path,PATH);assert.equal(previous.sha256,digest);assert.equal(previous.history_transfer,'none');
 assert.equal(previous.before_footprints_sha256,'b9a3c8bf375217dba3a50d1a022ec7e4ac6c6f1cdedff22845da953c805b7433');
 assert.equal(previous.after_footprints_sha256,'2deeff1457ff9238cb3dbe599e9a858dcce29d8ba88e2a66abe2785ddec0aed9');
 assert.equal(header.source.metadata.proposal_commit,previous.commit);
 assert.equal(header.source.metadata.migration_sha256,digest);
 const receipt=JSON.parse(raw);assert.equal(receipt.issue,1520);assert.equal(receipt.geometry_stage_validated,true);
 assert.equal(receipt.historical_claims_transferred,false);assert.equal(receipt.reused_ids.length,49623);
 assert.deepEqual(receipt.changed_ids,['atlas:physical:CAN-15:NWT','atlas:physical:CAN-25:NUN']);
 assert.equal(receipt.limits,header.source.metadata.source_limits);
 assert.equal(receipt.source_approval_transferred,false);
 assert.equal(receipt.before_footprints_sha256,previous.before_footprints_sha256);
 assert.equal(receipt.after_footprints_sha256,previous.after_footprints_sha256);
 return {...header,source:{...header.source,metadata:{...header.source.metadata,
  source_policy:receipt.limits,geometry_migration:{...previous,commit:binding.commit}}},release:{...header.release,metadata:{...header.release.metadata,
  geometry_migration:{...previous,commit:binding.commit},original_geometry_proposal_commit:previous.commit}},
  published_geometry_receipt:{...binding},header_kind:'committed-receipt-bound-release-header'};
}
