import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {prepareCurrentSelectedAdditive} from '../scripts/package-current-additive.mjs';
import {readGeographicReleaseManifest} from '../scripts/read-geographic-release-manifest.mjs';
const root=process.cwd(),sha=raw=>createHash('sha256').update(raw).digest('hex');
const selection=JSON.parse(await fs.readFile('data/ownership-selection.json'));
const sidecar=JSON.parse(await fs.readFile(selection.additive_release.path));
const bounds=await fs.readFile('data/canonical-grid/bounds.json.gz'),owners=new Map(JSON.parse(gunzipSync(bounds)).map(row=>[row.id,row]));
const features=(await Promise.all(JSON.parse(await fs.readFile('data/world-index.json')).parts.map(async name=>JSON.parse(await fs.readFile('data/'+name)).features))).flat().map(feature=>({...feature,pixelIndex:owners.get(feature.id)?.index}));
const selectedGrid={manifest:JSON.parse(await fs.readFile(selection.manifest_path)),sha256:selection.sha256,bounds};
const geographicRelease=readGeographicReleaseManifest().releases.at(-1);
const args={root,selectedGrid,geographicRelease,features};
async function fixture(t){
 const temp=await fs.mkdtemp(path.join(os.tmpdir(),'atlas-current-additive-'));t.after(()=>fs.rm(temp,{recursive:true,force:true}));
 const names=['.github/package-inputs.json','data/ownership-selection.json',selection.additive_release.path,sidecar.runtime_envelope.path,...Object.values(sidecar.logical_asset_map).map(pin=>pin.path)];
 for(const name of names){await fs.mkdir(path.dirname(path.join(temp,name)),{recursive:true});await fs.copyFile(name,path.join(temp,name));}
 return{...args,root:temp};
}

test('ordinary current additive consumption emits the exact four selected assets and effective reference',async t=>{
 const f=await fixture(t),result=await prepareCurrentSelectedAdditive(f),out=path.join(f.root,'out');
 assert.deepEqual(result.reference_release,result.additiveRelease.effective_reference);
 assert.equal(result.additiveRelease.base_manifest.sha256,selectedGrid.sha256);
 assert.equal(result.additiveRelease.base_reference.footprints_sha256,selectedGrid.manifest.footprints_sha256);
 await result.publish(out);
 for(const [role,pin]of Object.entries(sidecar.logical_asset_map))assert.equal(sha(await fs.readFile(path.join(out,result.additiveRelease[role].path))),pin.sha256);
 await assert.rejects(result.publish(out),/already exists/);
});

test('ordinary current additive consumption rejects stale base, actual parent drift and missing whole input',async t=>{
 const f=await fixture(t);
 await assert.rejects(prepareCurrentSelectedAdditive({...f,selectedGrid:{...selectedGrid,sha256:'a'.repeat(64)}}),/native selection differs/);
 const changed=features.map((feature,i)=>i===0?{...feature,properties:{...feature.properties,parent_id:'foreign-parent'}}:feature);
 await assert.rejects(prepareCurrentSelectedAdditive({...f,features:changed}),/owner identity or parent/);
 const ledger=JSON.parse(await fs.readFile(sidecar.logical_asset_map.ledger.path)),target=ledger.current_targets[0].target_id;
 const drift=features.map(feature=>feature.id===target?{...feature,geometry:{type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,0]]]}}:feature);
 await assert.rejects(prepareCurrentSelectedAdditive({...f,features:drift}),/Current target differs/);
 await fs.unlink(path.join(f.root,sidecar.logical_asset_map.patch.path));
 await assert.rejects(prepareCurrentSelectedAdditive(f),{code:'ENOENT'});
});

test('ordinary current additive consumption rejects coherently repinned invalid rows and preserves linked output',async t=>{
 const f=await fixture(t),current=structuredClone(selection),hook=structuredClone(sidecar);
 const patchPin=hook.logical_asset_map.patch,patch=JSON.parse(await fs.readFile(path.join(f.root,patchPin.path)));
 patch.rows[0].runs[0][2]=0;
 async function write(name,value){const raw=Buffer.from(JSON.stringify(value));await fs.writeFile(path.join(f.root,name),raw);return{bytes:raw.length,sha256:sha(raw),git_blob_oid:createHash('sha1').update('blob '+raw.length+'\0').update(raw).digest('hex')};}
 Object.assign(patchPin,await write(patchPin.path,patch));
 const wrapped=JSON.parse(await fs.readFile(path.join(f.root,hook.runtime_envelope.path))),envelope=wrapped.additiveRelease??wrapped;
 Object.assign(envelope.patch,{bytes:patchPin.bytes,sha256:patchPin.sha256});Object.assign(hook.runtime_envelope,await write(hook.runtime_envelope.path,wrapped));
 Object.assign(current.additive_release,await write(current.additive_release.path,hook));delete current.additive_release.git_blob_oid;
 await write('data/ownership-selection.json',current);
 await assert.rejects(prepareCurrentSelectedAdditive(f),/Conflicting or foreign current additive run/);
 const clean=await prepareCurrentSelectedAdditive(args),sentinel=path.join(f.root,'sentinel');await fs.mkdir(sentinel);await fs.writeFile(path.join(sentinel,'retained'),'original');
 const out=path.join(f.root,'out');await fs.mkdir(out);await fs.symlink(sentinel,path.join(out,'additive-repairs'));
 await assert.rejects(clean.publish(out),/destination must be ordinary/);assert.equal(await fs.readFile(path.join(sentinel,'retained'),'utf8'),'original');
});
