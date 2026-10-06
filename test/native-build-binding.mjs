// Explicit offline complete-build readback; never runs against a live service.
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {selectBuildOwnership} from '../scripts/select-build-ownership.mjs';
import {loadOwnershipAssets} from '../src/ownership-assets.js';
import {loadNativeLatitudes} from '../src/native-latitudes.js';
import {loadCoverageClassification} from '../src/coverage-classification.js';
import {nativeSourceDigest} from '../src/native-source-digest.js';
const digest=bytes=>createHash('sha256').update(bytes).digest('hex');
const atlasBytes=await fs.readFile('dist/atlas-geography.json'),atlas=JSON.parse(atlasBytes);
const selected=await selectBuildOwnership({
 manifestPath:process.env.ATLAS_NATIVE_GRID_MANIFEST??'coordination/engineering/native-grid-candidate-1010-20261005-local16/candidate-v1/manifest.json',
 expectedSha256:process.env.ATLAS_NATIVE_GRID_SHA256??'efe31373ff6a2c3f4ba5f11f8cbe37b25337778b344d9dbf1d3dfde301e3e722',
 expectedReference:atlas.reference_release,requireNative:true});
assert.deepEqual(atlas.gridVerification,selected.verification);
assert.equal(atlas.nativeContextInputStage.status,'verified');
assert.equal(atlas.nativeContextInputStage.locations,49625);
assert.equal(atlas.nativeContextInputStage.footprints_sha256,selected.manifest.footprints_sha256);
assert.equal(atlas.nativeContextInputStage.scientific_approval,false);
assert.equal(atlas.nativeContextInputStage.manifest_sha256,digest(await fs.readFile(atlas.nativeContextInputStage.manifest_path)));
const fetchFrom=root=>async url=>new Response(await fs.readFile(path.join(root,url.replace(/^\.\//,''))));
const options={requireNative:true,expectedReference:atlas.reference_release};
const original=await loadOwnershipAssets(selected.manifest,fetchFrom(selected.source),options);
const packaged=await loadOwnershipAssets(atlas.pixelMap,fetchFrom('dist'),options);
for(const key of ['rows','runs']){
 assert.equal(packaged[key].length,original[key].length);
 for(let i=0;i<original[key].length;i++)if(packaged[key][i]!==original[key][i])throw Error('Packaged '+key+' word differs at '+i);
}
const latitudes=await loadNativeLatitudes(atlas.pixelMap,atlas.reference_release,fetchFrom('dist'));
const catalog=[];
for(const name of atlas.parts)catalog.push(...JSON.parse(gunzipSync(await fs.readFile('dist/'+name))));
const bounds=JSON.parse(gunzipSync(selected.bounds));
assert.equal(catalog.length,bounds.length);assert.equal(new Set(catalog.map(f=>f.id)).size,catalog.length);
const byId=new Map(catalog.map(f=>[f.id,f]));
for(const owner of bounds){const feature=byId.get(owner.id);assert.ok(feature);assert.equal(feature.pixelIndex,owner.index);assert.equal(feature.properties.parent_id,owner.province_id);}
const geometries=[];
for(const name of atlas.geometryParts)geometries.push(...JSON.parse(gunzipSync(await fs.readFile('dist/'+name))));
assert.equal(geometries.length,catalog.length);
assert.equal(new Set(geometries.map(f=>f.id)).size,catalog.length);
assert.ok(geometries.every(f=>byId.has(f.id)));
const source=await nativeSourceDigest(geometries);
assert.equal(source.sha256,selected.manifest.footprints_sha256);
assert.equal(digest(await fs.readFile('data/hierarchy.json')),atlas.reference_release.hierarchy_sha256);
assert.equal(digest(await fs.readFile('data/prepared-evidence/index.json')),atlas.preparedEvidence.index_sha256);
const physical=JSON.parse(await fs.readFile('data/coverage-classification/manifest.json'));
const {ownership_binding,canonical_grid_sha256,...retained}=atlas.coverageClassification;
const {canonical_grid_sha256:oldGrid,...originalPhysical}=physical;
assert.deepEqual(retained,originalPhysical);
assert.equal(canonical_grid_sha256,selected.sha256);
assert.equal(ownership_binding.original_canonical_grid_sha256,oldGrid);
for(const part of physical.parts)assert.deepEqual(await fs.readFile('dist/'+part.path),await fs.readFile('data/'+part.path));
await loadCoverageClassification(atlas.coverageClassification,{...selected.manifest,release_id:atlas.reference_release.id,canonical_grid_sha256:selected.sha256},fetchFrom('dist'));
const legacy=await selectBuildOwnership();
assert.equal(legacy.sha256,'73899e8581d74634d6304a9e52aa32849dd174730aba2c6cc48db512a985d1f6');
assert.equal(legacy.verification,null);
const result={kind:'complete-offline-native-build-binding',atlas_manifest_sha256:digest(atlasBytes),native_manifest_sha256:selected.sha256,
 verification:selected.verification,checked_rows:packaged.size,checked_row_words:packaged.rows.length,checked_run_words:packaged.runs.length,
 exact_transport_words:true,normative_latitudes:latitudes.length,locations:catalog.length,original_ids_and_parents:true,
 original_native_footprints:source,physical_assets_and_source_limits_unchanged:true,prepared_evidence_index_unchanged:true,
 legacy_recovery_manifest_sha256:legacy.sha256,
 limits:['Offline build only; no live claims/database readback, installation approval or deployment.',
 'Native fidelity and physical class transport do not approve source completeness, water truth or political affiliation.',
 'Recovery preserves legacy assets and selection; no live hosting rollback was performed.']};
const output=process.env.ATLAS_NATIVE_BINDING_RECEIPT??'.cache/native-context-proof/build-binding-result.json';
await fs.mkdir(path.dirname(output),{recursive:true});await fs.writeFile(output,JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result));
