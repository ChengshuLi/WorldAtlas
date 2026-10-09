// Complete legacy release records/batch descriptors remain literal. The caller
// separately authenticates original encoded/decoded bodies and finished output pins.
import assert from 'node:assert/strict';
export const ORIGINAL_REGISTRY_SHA='10052f88a3ecdd42d555f05a2d5672c212d2ca9196cff383f8ce7a4cccd7652e';
const ORIGINAL_RELEASE='geography:review:896bf79dd6e5661dfbbffba60da96fa987b9971af2b884cf52347189861ebe9e';
export function continueReleaseRegistry(original,header,products,{originalSha}){
 assert.equal(originalSha,ORIGINAL_REGISTRY_SHA);assert.equal(original.version,1);
 assert.equal(original.releases.length,8);assert.equal(original.releases.at(-1).id,ORIGINAL_RELEASE);
 assert.equal(original.releases.at(-1).version,8);assert.equal(header.issue,1520);assert.equal(header.activated,false);
 assert.equal(header.header_kind,'committed-receipt-bound-release-header');
 assert.equal(header.release.version,9);assert.equal(header.release.metadata.predecessor_release_id,ORIGINAL_RELEASE);
 assert.equal(header.release.metadata.geometry_migration.commit,header.published_geometry_receipt.commit);
 assert.equal(header.release.metadata.geometry_migration.sha256,header.published_geometry_receipt.sha256);
 assert.equal(header.source.metadata.geometry_migration.sha256,header.published_geometry_receipt.sha256);
 assert.equal(header.source.metadata.source_policy,header.source.metadata.source_limits);
 assert.equal(header.membership_count,84833);assert.equal(header.memberships_reused_as_complete_records,true);
 assert.equal(header.changes.length,2);assert.equal(header.release.source_id,header.source.id);
 assert.equal(header.release.hierarchy_sha256,original.releases.at(-1).hierarchy_sha256);
 assert.equal(header.release.metadata.geometry_migration.before_footprints_sha256,original.releases.at(-1).footprints_sha256);
 assert.equal(header.release.metadata.geometry_migration.after_footprints_sha256,header.release.footprints_sha256);
 assert.equal(header.release.membership_sha256,original.releases.at(-1).membership_sha256);
 assert.equal(header.release.location_ids_sha256,original.releases.at(-1).location_ids_sha256);
 assert.equal(header.release.metadata.geometry_migration.history_transfer,'none');
 assert.deepEqual(header.release.expected_counts,original.releases.at(-1).expected_counts);
 assert.equal(products.length,343);const byName=new Map(products.map(p=>[p.path??p.relative,p]));assert.equal(byName.size,343);
 const names=['sources-9.json.gz','release-9.json.gz',...Array.from({length:340},(_,i)=>`9-memberships-${i*250}.json.gz`),'9-changes-0.json.gz'];
 assert.deepEqual([...byName.keys()].sort(),[...names].sort());
 const previous=new Set(original.batches.map(p=>p.path));assert.equal(previous.size,original.batches.length);
 const additions=names.map(name=>{const p=byName.get(name);assert(!previous.has(name));
  assert(Number.isSafeInteger(p.bytes)&&p.bytes>0&&p.bytes<=32*1024*1024);
  assert(Number.isSafeInteger(p.decoded_bytes)&&p.decoded_bytes>0&&p.decoded_bytes<=1024*1024);
  assert(/^[a-f0-9]{64}$/.test(p.sha256));const payload=p.payload_sha256??p.decoded_sha256;assert(/^[a-f0-9]{64}$/.test(payload));
  assert(p.mode==='100644'||p.mode===0o644);
  return {path:name,route:name==='sources-9.json.gz'?'/api/records/import':'/api/geography/stage',sha256:p.sha256,encoding:'gzip',payload_sha256:payload};});
 assert(Number.isSafeInteger(original.total_memberships)&&original.total_memberships>=84833);
 assert(Number.isSafeInteger(original.changes)&&original.changes>=0);
 assert(Number.isSafeInteger(original.new_entities)&&original.new_entities>=0);
 return {...original,releases:[...original.releases,header.release],batches:[...original.batches,...additions],
  sources_batches:[...original.sources_batches,'sources-9.json.gz'],
  total_memberships:original.total_memberships+84833,changes:original.changes+2};
}
