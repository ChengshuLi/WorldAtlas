import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {storageExportV2Contract,storageExportV2Collections} from '../hosted/storage-export-v2-contract.js';
import {storageExportV3Contract,storageExportV3Collections} from '../hosted/storage-export-v3-contract.js';
import {membershipStoragePins} from '../hosted/membership-storage-pins.js';
import {v4MarkerIdentity} from '../hosted/storage-export-v4-contract.js';
import {compactRecoveryProfile,compactRecoveryProfileV3,compactRecoveryTables,recoveryProfileForMarker,compactPhysicalReadSQL,compactPhysicalDigestSQL,verifyCompactRecoveryRegistry} from '../scripts/compact-recovery-profile.mjs';
const sha=value=>createHash('sha256').update(value).digest('hex');
function marker(version=2){const value={version:4,backend:'postgres',read_only:true,revision:3051,counts:Object.fromEntries((version===3?storageExportV3Collections:storageExportV2Collections).map(key=>[key,0])),catalog_sha256:'a'.repeat(64),geographic_releases_sha256:'b'.repeat(64),footprint_versions_sha256:'c'.repeat(64),contract:{version:4,base_contract:version===3?storageExportV3Contract:storageExportV2Contract,membership_storage:'compact-membership-v1',profile:'compact-only',...membershipStoragePins[version]['compact-only']}};value.fingerprint=sha(JSON.stringify(v4MarkerIdentity(value)));return value;}
for(const version of [2,3])test('reviewed compact-only base'+version+' marker is accepted',()=>assert.equal(recoveryProfileForMarker(marker(version)),version===3?compactRecoveryProfileV3:compactRecoveryProfile));
for(const [label,mutate] of [
 ['retained original',m=>{m.contract.profile='retained-original';Object.assign(m.contract,membershipStoragePins[2]['retained-original']);}],
 ['unknown profile',m=>m.contract.profile='new'],['extra contract field',m=>m.contract.ignore=true],['private catalog drift',m=>m.contract.private_sha256='d'.repeat(64)],
 ['base contract drift',m=>m.contract.base_contract={...storageExportV2Contract,version:3}],['extra count',m=>m.counts.other=1],['missing count',m=>delete m.counts.sources],
 ['fractional count',m=>m.counts.sources=.5],['negative count',m=>m.counts.sources=-1],['missing catalog hash',m=>delete m.catalog_sha256],['changed revision',m=>m.revision++],
 ['writable source',m=>m.read_only=false],['legacy projection',m=>m.legacy_projection=true],['other backend',m=>m.backend='d1'],['unknown marker',m=>m.version=5],
])test('compact source rejects '+label,()=>{const value=marker();mutate(value);assert.throws(()=>recoveryProfileForMarker(value));});
test('physical reads include verbatim evidence, BYTEA digest, numeric keys and all seven compact row fields',()=>{
 assert.match(compactPhysicalReadSQL('worldatlas_membership_evidence'),/"key","digest","raw"/);
 assert.match(compactPhysicalReadSQL('worldatlas_membership_rows'),/"release_key","entity_key","parent_key","reference_name","active","source_key","evidence_key"/);
 for(const table of Object.keys(compactRecoveryTables)){assert.match(compactPhysicalDigestSQL(table),/row_to_json\(q\)::text/);assert.doesNotMatch(compactPhysicalDigestSQL(table),/jsonb|COLLATE/);}
 assert.throws(()=>compactPhysicalReadSQL('worldatlas_membership_rows; DROP TABLE atlas_sources'));
});
test('unknown/transitional migration inventories fail before DDL reads',async()=>{
 for(const registry of [[],[{migration_id:'synthetic-fixture'}],[{migration_id:'0001_temporal_geography'},{migration_id:'0002_footprint_versions'},{migration_id:'0003_typed_observations'}]])await assert.rejects(()=>verifyCompactRecoveryRegistry(()=>{throw Error('must not query');},registry),/unsupported-compact-migration-registry/);
});

for(const mutation of [m=>delete m.counts.typed_observations,m=>m.counts.typed_observations=-1,m=>m.counts.extra=0,m=>m.contract.base_contract={...m.contract.base_contract,version:9}])test('base3 counts and contract remain closed',()=>{const m=marker(3);mutation(m);assert.throws(()=>recoveryProfileForMarker(m));});
