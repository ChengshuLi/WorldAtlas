import test, {after} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {selectBuildOwnership,readBuildOwnershipSelection} from '../scripts/select-build-ownership.mjs';
const candidate = 'coordination/engineering/native-grid-candidate-1010-20261005-local16/candidate-v1/manifest.json';
const bytes = await fs.readFile(candidate), manifest = JSON.parse(bytes);
const sha256 = createHash('sha256').update(bytes).digest('hex');
const reference = {id: manifest.geographic_release, footprints_sha256: manifest.footprints_sha256, hierarchy_sha256: manifest.hierarchy_sha256};
const scratch = fileURLToPath(new URL('../.cache/build-selection-controls/', import.meta.url));
await fs.mkdir(scratch, {recursive: true});
const root = await fs.mkdtemp(path.join(scratch, 'run-'));
after(() => fs.rm(root, {recursive: true}));

test('explicit reviewed candidate preserves metadata and retrieves immutable original bounds', async () => {
  const selected = await selectBuildOwnership({manifestPath: candidate, expectedSha256: sha256, expectedReference: reference});
  assert.equal(selected.sha256, sha256);
  assert.equal(selected.metadata.method, manifest.method);
  assert.equal(selected.source, path.dirname(candidate));
  assert.equal(createHash('sha256').update(selected.bounds).digest('hex'), manifest.bounds.sha256);
  assert.equal(selected.manifest.installation_ready, false);
  assert.equal(selected.verification.manifest_sha256, sha256);
  assert.equal(selected.verification.installation_approval, false);
});

test('native selection rejects unpinned, altered and wrong-release candidates', async () => {
  await assert.rejects(selectBuildOwnership({manifestPath: candidate, expectedReference: reference}), /reviewed manifest/);
  await assert.rejects(selectBuildOwnership({manifestPath: candidate, expectedSha256: '0'.repeat(64), expectedReference: reference}), /manifest checksum/);
  await assert.rejects(selectBuildOwnership({manifestPath: candidate, expectedSha256: sha256,
    expectedReference: {...reference, id: 'geography:different'}}), /reference release/);
  const changed = {...manifest, original_assets: {...manifest.original_assets, bounds: {...manifest.original_assets.bounds, path: '../wrong'}}};
  const altered = Buffer.from(JSON.stringify(changed)), file = path.join(root, 'bad.json');
  await fs.writeFile(file, altered);
  await assert.rejects(selectBuildOwnership({manifestPath: file,
    expectedSha256: createHash('sha256').update(altered).digest('hex'), expectedReference: reference}), /original bounds/);
});


test('legacy recovery selection retains original grid bytes and does not reinterpret old releases as native',async()=>{
  const selected=await selectBuildOwnership();
  assert.equal(selected.sha256,'73899e8581d74634d6304a9e52aa32849dd174730aba2c6cc48db512a985d1f6');
  assert.equal(selected.manifest.method,undefined);
  assert.equal(selected.verification,null);
  assert.equal(selected.source,'data/canonical-grid');
  await assert.rejects(selectBuildOwnership({requireNative:true}),/cannot select legacy/);
});

test('ordinary build selects its committed release, while explicit candidates remain checksum pinned',async()=>{
  assert.deepEqual(await readBuildOwnershipSelection({root,env:{}}),{manifestPath:'data/canonical-grid/manifest.json',requireNative:false});
  await fs.mkdir(path.join(root,'data'));
  const selection={version:1,method:manifest.method,manifest_path:candidate,sha256,release_id:reference.id};
  await fs.writeFile(path.join(root,'data/ownership-selection.json'),JSON.stringify(selection));
  assert.deepEqual(await readBuildOwnershipSelection({root,env:{}}),{manifestPath:candidate,expectedSha256:sha256,requireNative:true,releaseId:reference.id});
  await assert.rejects(readBuildOwnershipSelection({root,env:{ATLAS_NATIVE_GRID_MANIFEST:candidate}}),/both manifest and checksum/);
  assert.equal((await readBuildOwnershipSelection({root,env:{ATLAS_NATIVE_GRID_MANIFEST:candidate,ATLAS_NATIVE_GRID_SHA256:sha256}})).requireNative,true);
  await fs.writeFile(path.join(root,'data/ownership-selection.json'),JSON.stringify({...selection,manifest_path:'../escape.json'}));
  await assert.rejects(readBuildOwnershipSelection({root,env:{}}),/Invalid committed/);
});

test('offline native selection keeps original qualified N and binds a pinned current metadata M separately',async()=>{
  const selector={version:1,method:manifest.method,manifest_path:candidate,sha256,release_id:reference.id};
  const current={...reference,id:'geography:review:current-metadata',hierarchy_sha256:'f'.repeat(64)};
  const pin=(name,hash)=>({commit:'1'.repeat(40),path:name,mode:'100644',git_blob_oid:'2'.repeat(40),bytes:1,sha256:hash});
  const projection={version:1,kind:'native-reference-metadata-projection-v1',native_selection:selector,native_reference:reference,reference:current,
    original_owner_roster_sha256:manifest.original_assets.bounds.sha256,
    hierarchy:{before:pin('data/hierarchy.json',reference.hierarchy_sha256),after:pin('data/hierarchy.json',current.hierarchy_sha256)},
    receipts:[pin('data/receipt.json','3'.repeat(64))],source_updates:[],location_changes:[],group_changes:[],provinces:['fixture:province']};
  const raw=Buffer.from(JSON.stringify(projection)),name='metadata-application.json',pointer={path:name,bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex')};
  await fs.writeFile(path.join(root,name),raw);
  const selected={...selector,reference_projection:pointer};
  const input={root,manifestPath:candidate,expectedSha256:sha256,expectedReference:current,requireNative:true,referenceSelection:selected,referenceProjection:pointer};
  const before=await selectBuildOwnership({manifestPath:candidate,expectedSha256:sha256,expectedReference:reference,requireNative:true}),after=await selectBuildOwnership(input);
  assert.deepEqual(after.manifest,before.manifest);assert.deepEqual(after.bounds,before.bounds);assert.deepEqual(after.verification,before.verification);
  assert.deepEqual(after.metadata,before.metadata);assert.deepEqual(after.nativeReference,reference);assert.deepEqual(after.applicationReference,current);
  await assert.rejects(selectBuildOwnership({...input,expectedReference:{...current,id:'geography:foreign'}}),/current selected release/);
  await assert.rejects(selectBuildOwnership({...input,referenceProjection:{...pointer,sha256:'0'.repeat(64)},referenceSelection:{...selected,reference_projection:{...pointer,sha256:'0'.repeat(64)}}}),/checksum differs/);
  await assert.rejects(selectBuildOwnership({...input,referenceProjection:{...pointer,extra:true},referenceSelection:{...selected,reference_projection:{...pointer,extra:true}}}),/pointer/);
  await fs.writeFile(path.join(root,'data/ownership-selection.json'),JSON.stringify(selected));
  const option=await readBuildOwnershipSelection({root,env:{}});assert.deepEqual(option.referenceProjection,pointer);assert.deepEqual(option.referenceSelection,selected);
});
