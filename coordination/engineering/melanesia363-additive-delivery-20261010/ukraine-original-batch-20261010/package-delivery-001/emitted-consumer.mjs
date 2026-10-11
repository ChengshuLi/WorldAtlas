import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
const root=process.cwd(), output=path.join(root,'dist/client');
const {loadOwnershipAssets}=await import(path.join(root,'src/ownership-assets.js'));
const {loadAdditiveNativePatch,effectivePrimitiveGeometries}=await import(path.join(root,'src/effective-footprint.js'));
const {pickOwnership,samplePackedOwnership}=await import(path.join(root,'src/pixel-ownership.js'));
const sha=b=>createHash('sha256').update(b).digest('hex');
const whole=(base,p)=>{const f=path.resolve(base,p.path);assert(f.startsWith(base+path.sep));const b=fs.readFileSync(f);assert.equal(b.length,p.bytes);assert.equal(sha(b),p.sha256);return b;};
const selection=JSON.parse(fs.readFileSync('data/ownership-selection.json')),sidecar=JSON.parse(whole(root,selection.additive_release));
const atlas=JSON.parse(fs.readFileSync(path.join(output,'atlas-geography.json'))),envelope=JSON.parse(whole(root,sidecar.runtime_envelope));assert.deepEqual(atlas.additiveRelease,envelope);
const ledger=JSON.parse(whole(output,envelope.ledger)),patch=JSON.parse(whole(output,envelope.patch));
const certificate=JSON.parse(whole(root,ledger.current_rebind)),request=JSON.parse(whole(root,certificate.request)),result=JSON.parse(whole(root,certificate.result));
const fetcher=async p=>{const f=path.resolve(output,p);assert(f.startsWith(output+path.sep));const b=fs.readFileSync(f);return new Response(b,{status:200,headers:{'Content-Length':String(b.length)}});};
const base=await loadOwnershipAssets(atlas.pixelMap,fetcher);
const features=atlas.parts.flatMap(p=>JSON.parse(gunzipSync(fs.readFileSync(path.join(output,p)))));
const effective=await loadAdditiveNativePatch(atlas,features,base,{fetcher});
let added=0,stable=0;
for(const row of patch.rows)for(const [a,b,id] of row.runs)for(let x=a;x<b;x++){
 assert.equal(pickOwnership(base,x,row.y),0);assert.equal(pickOwnership(effective,x,row.y),id);
 assert.equal(samplePackedOwnership(effective,{x,y:row.y,width:1,height:1})[0],id);added++;
}
const observed=new Map();for(const row of [...request.current_rows,...request.acquisition.predecessor_rows]){
 if(observed.has(row.y))assert.deepEqual(observed.get(row.y),row);else observed.set(row.y,row);
}
for(const row of observed.values()){
 const [x,,id]=row.runs.find(([a,b])=>a<b);assert.equal(pickOwnership(base,x,row.y),id);assert.equal(pickOwnership(effective,x,row.y),id);
 assert.equal(samplePackedOwnership(effective,{x,y:row.y,width:1,height:1})[0],id);stable++;
}
assert.equal(added,result.native.assigned_cells);assert.equal(added,353);
const cid='physical-component:6fd25496ae4a7635eef229d0cfd1eb8dc7d9c10c252d3255fe8d42d186e706d1';
const expected=ledger.rows.find(r=>r.component_id===cid);assert.equal(expected.disposition,'zero-cell');
const target=features.find(f=>f.id==='gb:UKR:ADM2:74538382B77535249747568');
assert.deepEqual(target.additiveFootprint.components.find(r=>r.component_id===cid),expected);assert(effectivePrimitiveGeometries(target).length>1);
const report={version:1,kind:'actual-emitted-selected-consumer',passed:true,feature_count:features.length,selected_ledger_sha256:envelope.ledger.sha256,selected_patch_sha256:envelope.patch.sha256,prior_selected_cells_picked_and_sampled:added,stable_owner_controls:stable,ukr_component:cid,ukr_disposition:expected.disposition,ukr_primitive_in_loaded_effective_view:true,limitation:'Production Node-compatible asset loader, effective primitive, picker and renderer-sampler entry points on actual emitted assets. GPU and Canvas execution remains the required hosted browser test; zero UKR native cells are not visible-pixel gain.'};
fs.writeFileSync(process.argv[2],JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(report));
