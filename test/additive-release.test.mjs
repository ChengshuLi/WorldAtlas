import test from 'node:test';
import assert from 'node:assert/strict';
import {applyAdditiveNativePatch,loadAdditiveNativePatch,footprintValueSha256 as hash,loadedBaseFootprintSha256,additiveReleaseFootprintDigest} from '../src/effective-footprint.js';
import {packOwnership,pickOwnership,samplePackedOwnership} from '../src/pixel-ownership.js';
import {nativeSourceDigest} from '../src/native-source-digest.js';
import {createHash} from 'node:crypto';
import {gzipSync,gunzipSync} from 'node:zlib';
const rectangle=(a,b,c,d)=>({type:'Polygon',coordinates:[[[a,b],[c,b],[c,d],[a,d],[a,b]]]});
function fixture(){
 const rows=Array.from({length:262166},()=>new Uint32Array());rows[3]=Uint32Array.from([1,3,1,8,10,2]);
 const baseReference={id:'geography:base',footprints_sha256:'a'.repeat(64),hierarchy_sha256:'b'.repeat(64)};
 const effectiveReference={...baseReference,id:'geography:effective',footprints_sha256:'c'.repeat(64)};
 const base={...packOwnership({size:262166,rows}),method:'native-linear-evenodd-first-owner-v1',geographic_release:baseReference.id,...baseReference};
 const f={id:'owner1',pixelIndex:1,geometry:rectangle(0,0,1,1),properties:{parent_id:'parent1'}};
 f.additiveFootprint={version:1,kind:'retained-base-plus-additions',baseline_release_sha256:baseReference.footprints_sha256,base_geometry_sha256:hash(f.geometry),ledger_sha256:'d'.repeat(64),rule_sha256:'e'.repeat(64),additions:[{component_id:'gap',geometry:rectangle(1,0,2,1),geometry_sha256:hash(rectangle(1,0,2,1)),source_receipt_sha256:'f'.repeat(64)}]};
 const features=[f,{id:'owner2',pixelIndex:2,geometry:rectangle(2,0,3,1),properties:{parent_id:'parent2'}}];
 base.reference_owner_sha256=createHash('sha256').update(JSON.stringify(features.map(f=>[f.pixelIndex,f.id]))).digest('hex');
 const patch={version:1,kind:'unassigned-native-cells-v1',base_reference:baseReference,effective_reference:effectiveReference,ledger_sha256:'d'.repeat(64),rule_sha256:'e'.repeat(64),rows:[{y:3,runs:[[3,5,1]]}]};
 return{base,patch,options:{baseReference,effectiveReference,features}};
}
test('actual renderer and picker consume identical sparse overlay; all old cells and full source primitives preserved',()=>{
 const {base,patch,options}=fixture(),oldRows=base.rows.slice(),oldRuns=base.runs.slice(),out=applyAdditiveNativePatch(base,patch,options);
 assert.equal(out.additive_added_cells,2);
 for(let x=0;x<20;x++){const old=pickOwnership(base,x,3);if(old)assert.equal(pickOwnership(out,x,3),old);}
 assert.deepEqual([...samplePackedOwnership(out,{x:0,y:3,width:12,height:1})],[0,1,1,1,1,0,0,0,2,2,0,0]);
 assert.deepEqual(base.rows,oldRows);assert.deepEqual(base.runs,oldRuns);assert.equal(applyAdditiveNativePatch(out,patch,options),out);
 out.runs[0]^=1;assert.throws(()=>applyAdditiveNativePatch(out,patch,options),/drifted/);
});
test('assigned cells, conflicts, foreign owner, stale baseline and rule rebind reject without changing base',()=>{
 for(const alter of [p=>p.rows[0].runs=[[2,4,1]],p=>p.rows[0].runs=[[8,9,1]],p=>p.rows[0].runs=[[3,6,1],[5,7,2]],p=>p.rows[0].runs=[[3,5,3]],p=>p.base_reference.footprints_sha256='0'.repeat(64),p=>p.rule_sha256='0'.repeat(64),p=>p.rows.push(p.rows[0])]){
  const {base,patch,options}=fixture(),before=base.runs.slice();alter(patch);assert.throws(()=>applyAdditiveNativePatch(base,patch,options));assert.deepEqual(base.runs,before);
 }
 const {base,patch,options}=fixture();base.additive_patch_sha256=hash(patch);assert.throws(()=>applyAdditiveNativePatch(base,patch,options),/Foreign/);
});
test('real bounded asset load authenticates whole patch and complete effective digest; no silent legacy fallback',async()=>{
 const {base,patch,options}=fixture();
 const baseHash=loadedBaseFootprintSha256(options.features);options.baseReference.footprints_sha256=baseHash;
 base.footprints_sha256=baseHash;patch.base_reference={...options.baseReference};
 const f=options.features[0];f.additiveFootprint.baseline_release_sha256=baseHash;
 const ledger={version:1,kind:'native-additive-repair-ledger-v1',rule_sha256:patch.rule_sha256,base_reference:options.baseReference,
  parent_inventory:{components:95173,report_sha256:'1'.repeat(64),roster_sha256:'2'.repeat(64)},scope_ids:['gap'],assigned_cells:2,
  rows:[{component_id:'gap',disposition:'assigned',target_id:f.id,pixelIndex:f.pixelIndex,base_geometry_sha256:hash(f.geometry),
   geometry:f.additiveFootprint.additions[0].geometry,geometry_sha256:f.additiveFootprint.additions[0].geometry_sha256,
   source_receipt_sha256:'f'.repeat(64),native_cells:2}]};
 const ledgerRaw=Buffer.from(JSON.stringify(ledger)),ledgerHash=createHash('sha256').update(ledgerRaw).digest('hex');
 patch.ledger_sha256=ledgerHash;f.additiveFootprint.ledger_sha256=ledgerHash;
 const digest=(await nativeSourceDigest(options.features,{additiveBaseReference:options.baseReference})).sha256;
 assert.equal(digest,additiveReleaseFootprintDigest(options.baseReference,options.features));
 options.effectiveReference.footprints_sha256=digest;patch.effective_reference={...options.effectiveReference};
 const raw=Buffer.from(JSON.stringify(patch)),rosterRaw=Buffer.from(JSON.stringify(options.features.map(f=>({id:f.id,index:f.pixelIndex,province_id:f.properties.parent_id}))));
 const asset=(path,body)=>({path,bytes:body.length,sha256:createHash('sha256').update(body).digest('hex')});
 const data={reference_release:options.effectiveReference,additiveRelease:{version:1,kind:'retained-native-base-plus-delta-v1',base_reference:options.baseReference,effective_reference:options.effectiveReference,
  patch:asset('additive-repairs/batch1.json',raw),ledger:asset('additive-repairs/ledger1.json',ledgerRaw),owner_roster:{...asset('additive-repairs/owners1.json.gz',gzipSync(rosterRaw)),encoding:'gzip',decoded_bytes:rosterRaw.length,decoded_sha256:createHash('sha256').update(rosterRaw).digest('hex')}}};
 const fetcher=async path=>new Response(path.includes('ledger1')?ledgerRaw:path.includes('owners1')?gzipSync(rosterRaw):raw);
 delete base.reference_owner_sha256; // Real a71 predecessor has no leaf-owner digest.
 const plain=options.features.map(({additiveFootprint,...feature})=>feature),originalBase=plain.map(f=>f.geometry);
 const out=await loadAdditiveNativePatch(data,plain,base,{fetcher});
 assert.ok(plain[0].additiveFootprint);assert.deepEqual(plain.map(f=>f.geometry),originalBase);assert.equal(pickOwnership(out,3,3),1);
 await assert.rejects(loadAdditiveNativePatch(data,options.features,base,{fetcher,effectiveDigest:'0'.repeat(64)}),/digest/);
 await assert.rejects(loadAdditiveNativePatch(data,options.features,base,{fetcher:async path=>path.includes('batch1')?new Response(Buffer.concat([raw,Buffer.from('x')])):fetcher(path),effectiveDigest:digest}),/exceeds/);
 await assert.rejects(loadAdditiveNativePatch(data,options.features,base,{fetcher:async path=>path.includes('batch1')?new Response(Buffer.from('x'.repeat(raw.length))):fetcher(path),effectiveDigest:digest}),/checksum/);
 const changedOwner=structuredClone(options.features);changedOwner[0].pixelIndex=3;
 await assert.rejects(loadAdditiveNativePatch(data,changedOwner,base,{fetcher,effectiveDigest:digest}),/domain/);
 const changedParent=structuredClone(options.features);changedParent[0].properties.parent_id='foreign';
 await assert.rejects(loadAdditiveNativePatch(data,changedParent,base,{fetcher,effectiveDigest:digest}),/owner or parent/);
 const omitted=structuredClone(options.features);omitted[0].additiveFootprint.additions=[];
 await assert.rejects(loadAdditiveNativePatch(data,omitted,base,{fetcher,effectiveDigest:digest}));
 const staleBase=structuredClone(options.features);staleBase[1].geometry=rectangle(2,0,4,1);
 await assert.rejects(loadAdditiveNativePatch(data,staleBase,base,{fetcher,effectiveDigest:digest}),/original base/);
 await assert.rejects(loadAdditiveNativePatch({reference_release:options.baseReference},options.features,base),/explicit/);
});

test('actual frozen add031 full-owner window draws and picks exactly seven gained cells; no other cell changes',async()=>{
 const {default:fs}=await import('node:fs');
 const p='coordination/engineering/additive-native-gap-repair-20261008/add031-release-proposal-v1/';
 const publication=JSON.parse(fs.readFileSync(p+'publication.json'));
 const read=name=>{const descriptor=publication.assets.find(row=>row.path===name),raw=fs.readFileSync(p+name);
  assert.equal(raw.length,descriptor.bytes);assert.equal(createHash('sha256').update(raw).digest('hex'),descriptor.sha256);return JSON.parse(raw);};
 const patch=read('patch-add031.json'),feature=read('feature.json'),window=read('owner-window.json');
 assert.equal(window.length,13);assert.equal(window[0].y,61359);assert.equal(window.at(-1).y,61371);
 const rows=Array.from({length:262166},()=>new Uint32Array());
 for(const row of window)rows[row.y]=Uint32Array.from(row.complete_owner_intervals.flat());
 // This is a declared 13-row view fixture of complete ACTUAL owner rows, not a
 // reconstructed complete world bank. Both renderer/picker are production code.
 const boundsRaw=gunzipSync(fs.readFileSync(p+'owners-add031.json.gz'));
 const boundsDescriptor=publication.assets.find(row=>row.path==='owners-add031.json.gz');
 assert.equal(boundsRaw.length,boundsDescriptor.uncompressed_bytes);assert.equal(createHash('sha256').update(boundsRaw).digest('hex'),boundsDescriptor.uncompressed_sha256);
 const bounds=JSON.parse(boundsRaw),modelGeometry=rectangle(0,0,1,1);
 // Non-target geometry is explicitly a model: only the full authentic owner
 // roster and 13-row native window are under test; no world-geometry claim.
 const ownerFeatures=bounds.map(row=>row.id===feature.id?feature:{id:row.id,pixelIndex:row.index,geometry:modelGeometry});
 const base={...packOwnership({size:262166,rows}),method:'native-linear-evenodd-first-owner-v1',geographic_release:patch.base_reference.id,...patch.base_reference,
  reference_owner_sha256:createHash('sha256').update(JSON.stringify(bounds.map(row=>[row.index,row.id]).sort((a,b)=>a[0]-b[0]))).digest('hex')};
 const out=applyAdditiveNativePatch(base,patch,{baseReference:patch.base_reference,effectiveReference:patch.effective_reference,features:ownerFeatures});
 const before=samplePackedOwnership(base,{x:0,y:61359,width:262166,height:13}),after=samplePackedOwnership(out,{x:0,y:61359,width:262166,height:13});
 let added=0,existing=0;for(let i=0;i<before.length;i++){
  if(before[i]){assert.equal(after[i],before[i]);existing++;}
  else if(after[i]){assert.equal(after[i],6757);added++;}
 }
 assert.equal(added,7);assert.ok(existing>0);
 for(const row of patch.rows)for(const [start,end,owner]of row.runs)for(let x=start;x<end;x++){
  assert.equal(pickOwnership(base,x,row.y),0);assert.equal(pickOwnership(out,x,row.y),owner);
  assert.equal(after[(row.y-61359)*262166+x],pickOwnership(out,x,row.y));
 }
 assert.equal(out.additive_added_cells,7);
 const drift=structuredClone(patch);drift.rows[0].runs[0][0]=window[0].complete_owner_intervals[0][0];drift.rows[0].runs[0][1]=drift.rows[0].runs[0][0]+1;drift.rows[0].y=window[0].y;
 assert.throws(()=>applyAdditiveNativePatch(base,drift,{baseReference:patch.base_reference,effectiveReference:patch.effective_reference,features:ownerFeatures}),/assigned/);
});
