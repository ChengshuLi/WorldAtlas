import test from 'node:test';
import assert from 'node:assert/strict';
import {applyAdditiveNativePatch,loadAdditiveNativePatch,additiveBaseReference,nativeReferenceForData,footprintValueSha256 as hash,loadedBaseFootprintSha256,additiveReleaseFootprintDigest} from '../src/effective-footprint.js';
import {packOwnership,pickOwnership,samplePackedOwnership} from '../src/pixel-ownership.js';
import {nativeSourceDigest} from '../src/native-source-digest.js';
import {createHash} from 'node:crypto';
import {gzipSync,gunzipSync} from 'node:zlib';
import {prepareReferenceMetadataProjection} from '../scripts/selected-reference-metadata.mjs';
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
  rows:[{component_id:'gap',disposition:'assigned',target_id:f.id,pixelIndex:f.pixelIndex,base_geometry:f.geometry,base_geometry_sha256:hash(f.geometry),
   geometry:f.additiveFootprint.additions[0].geometry,geometry_sha256:f.additiveFootprint.additions[0].geometry_sha256,
   source_receipt_sha256:'f'.repeat(64),native_cells:2}]};
 const ledgerRaw=Buffer.from(JSON.stringify(ledger)),ledgerHash=createHash('sha256').update(ledgerRaw).digest('hex');
 patch.ledger_sha256=ledgerHash;f.additiveFootprint.ledger_sha256=ledgerHash;
 const digest=(await nativeSourceDigest(options.features,{additiveBaseReference:options.baseReference})).sha256;
 assert.equal(digest,additiveReleaseFootprintDigest(options.baseReference,options.features));
 options.effectiveReference.footprints_sha256=digest;patch.effective_reference={...options.effectiveReference};
 const raw=Buffer.from(JSON.stringify(patch)),rosterRaw=Buffer.from(JSON.stringify(options.features.map(f=>({id:f.id,index:f.pixelIndex,province_id:f.properties.parent_id,bounds:[0,0,3,3]}))));
 const asset=(path,body)=>({path,bytes:body.length,sha256:createHash('sha256').update(body).digest('hex')});
 const manifestRaw=Buffer.from(JSON.stringify({...options.baseReference,geographic_release:options.baseReference.id,method:base.method,size:base.size,coordinateBits:base.coordinateBits,parts:['rows','runs'].map(kind=>({kind,offset:0,words:base[kind].length,decoded_sha256:createHash('sha256').update(new Uint8Array(base[kind].buffer)).digest('hex')})),original_assets:{bounds:{sha256:createHash('sha256').update(gzipSync(rosterRaw)).digest('hex')}}}));
 const originalManifestSha=createHash('sha256').update(manifestRaw).digest('hex');
 const data={pixelMap:{canonical_grid_sha256:originalManifestSha},reference_release:options.effectiveReference,additiveRelease:{version:1,kind:'retained-native-base-plus-delta-v1',base_reference:options.baseReference,effective_reference:options.effectiveReference,
  base_manifest:asset('additive-repairs/base-native-manifest.json',manifestRaw),patch:asset('additive-repairs/batch1.json',raw),ledger:asset('additive-repairs/ledger1.json',ledgerRaw),owner_roster:{...asset('additive-repairs/owners1.json.gz',gzipSync(rosterRaw)),encoding:'gzip',decoded_bytes:rosterRaw.length,decoded_sha256:createHash('sha256').update(rosterRaw).digest('hex')}}};
 const fetcher=async path=>new Response(path.includes('base-native-manifest')?manifestRaw:path.includes('ledger1')?ledgerRaw:path.includes('owners1')?gzipSync(rosterRaw):raw);
 const corruptNative={...base,runs:base.runs.slice()};corruptNative.runs[0]^=1;
 await assert.rejects(loadAdditiveNativePatch(data,options.features,corruptNative,{fetcher}),/original selected manifest/);
 delete base.reference_owner_sha256; // Real a71 predecessor has no leaf-owner digest.
 const plain=options.features.map(({additiveFootprint,...feature})=>feature),originalBase=plain.map(f=>f.geometry);
 const out=await loadAdditiveNativePatch(data,plain,base,{fetcher});
 assert.ok(plain[0].additiveFootprint);assert.deepEqual(plain.map(f=>f.geometry),originalBase);assert.equal(pickOwnership(out,3,3),1);
 // Real normal loadGeography entry starts with the build's geometry:null catalog
 // and its separately packaged geometryParts. Vite supplies its ordinary env.
 const {createServer}=await import('vite'),{shuffleOwnershipBytes}=await import('../src/ownership-codec.js'),{default:fs}=await import('node:fs');
 const latRaw=fs.readFileSync('coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz');
 const latitude={root:'repository',role:'immutable-normative-rule-input',path:'coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz',commit:'1'.repeat(40),bytes:latRaw.length,sha256:createHash('sha256').update(latRaw).digest('hex'),decoded_bytes:262166*8,decoded_sha256:'66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23',transport_path:'native-v1/native-row-latitudes.f64le.gz'};
 const transports=new Map(),parts=['rows','runs'].map(kind=>{
  const words=base[kind],body=gzipSync(shuffleOwnershipBytes(words)),path='ownership/'+kind+'.gz';transports.set('./'+path,body);
  return {kind,offset:0,words:words.length,path,encoding:'byte-shuffle',sha256:createHash('sha256').update(body).digest('hex'),decoded_sha256:createHash('sha256').update(new Uint8Array(words.buffer)).digest('hex')};
 });
 const units=['province','area','region','subcontinent','continent'].map((level,i)=>({id:level,level,parent_id:i===4?null:['area','region','subcontinent','continent'][i]}));
 const normalFeatures=options.features.map(({additiveFootprint,...f})=>({...f,properties:{...f.properties,id:f.id,parent_id:'province'}}));
 const normalRoster=Buffer.from(JSON.stringify(normalFeatures.map(f=>({id:f.id,index:f.pixelIndex,province_id:'province',bounds:[0,0,3,3]})))),normalRosterEncoded=gzipSync(normalRoster);
 const normalManifest=Buffer.from(JSON.stringify({...JSON.parse(manifestRaw),original_assets:{bounds:{sha256:createHash('sha256').update(normalRosterEncoded).digest('hex')}}}));
 const normalData={...structuredClone(data),units,temporal:{links:[],history:[]},parts:['geography/catalog.json'],geometryParts:['geography/geometries.json'],pixelMap:{...data.pixelMap,...options.baseReference,geographic_release:options.baseReference.id,version:2,size:262166,coordinateBits:19,method:base.method,runWords:base.runs.length,native_latitudes:latitude,parts,canonical_grid_sha256:createHash('sha256').update(normalManifest).digest('hex')}};
 normalData.additiveRelease.base_manifest=asset('additive-repairs/base-native-manifest.json',normalManifest);
 normalData.additiveRelease.owner_roster={...asset('additive-repairs/owners1.json.gz',normalRosterEncoded),encoding:'gzip',decoded_bytes:normalRoster.length,decoded_sha256:createHash('sha256').update(normalRoster).digest('hex')};
 transports.set('./native-v1/native-row-latitudes.f64le.gz',latRaw);
 transports.set('./geography/catalog.json',Buffer.from(JSON.stringify(normalFeatures.map(f=>({...f,geometry:null})))));
 transports.set('./geography/geometries.json',Buffer.from(JSON.stringify(normalFeatures.map(f=>({id:f.id,geometry:f.geometry})))))
 const server=await createServer({configFile:false,server:{middlewareMode:true},define:{'import.meta.env.VITE_STATIC_ATLAS':'"true"','import.meta.env.VITE_HOSTED_DATABASE':'"false"'}}),oldFetch=globalThis.fetch;
 try{
  globalThis.fetch=async path=>path==='./atlas-geography.json'?new Response(JSON.stringify(normalData)):transports.has(path)?new Response(transports.get(path)):path.includes('base-native-manifest')?new Response(normalManifest):path.includes('owners1')?new Response(normalRosterEncoded):fetcher(path);
  let geometryReads=0;const fixtureFetch=globalThis.fetch;globalThis.fetch=async path=>{if(path==='./geography/geometries.json')geometryReads++;return fixtureFetch(path);};
  const client=await server.ssrLoadModule('/src/data-client.js'),loaded=await client.loadGeography();
  assert.equal(geometryReads,0);assert.equal(loaded.features[1].geometry,null);
  assert.equal(loaded.features[0].geometry.type,'Polygon');assert.ok(loaded.features[0].additiveFootprint);
  assert.equal(pickOwnership(loaded.ownership,3,3),1);assert.equal(loaded.ownership.effective_footprint_sha256,digest);
  await client.ensureGeometry(loaded);assert.equal(geometryReads,1);assert.equal(loaded.features[1].geometry.type,'Polygon');
  const originalPart=transports.get('./geography/geometries.json');
  transports.set('./geography/geometries.json',Buffer.from(JSON.stringify([{id:'foreign',geometry:normalFeatures[0].geometry},...normalFeatures.slice(1).map(f=>({id:f.id,geometry:f.geometry}))])));
  const foreign=await client.loadGeography();await assert.rejects(client.ensureGeometry(foreign),/base geometry transport/);transports.set('./geography/geometries.json',originalPart);
 }finally{globalThis.fetch=oldFetch;await server.close();}

 await assert.rejects(loadAdditiveNativePatch(data,options.features,base,{fetcher,effectiveDigest:'0'.repeat(64)}),/digest/);
 await assert.rejects(loadAdditiveNativePatch(data,options.features,base,{fetcher:async path=>path.includes('batch1')?new Response(Buffer.concat([raw,Buffer.from('x')])):fetcher(path),effectiveDigest:digest}),/exceeds/);
 await assert.rejects(loadAdditiveNativePatch(data,options.features,base,{fetcher:async path=>path.includes('batch1')?new Response(Buffer.from('x'.repeat(raw.length))):fetcher(path),effectiveDigest:digest}),/checksum/);
 const coherentData=structuredClone(data),swapped=structuredClone(options.features),coherentRoster=JSON.parse(rosterRaw);
 [swapped[0].pixelIndex,swapped[1].pixelIndex]=[swapped[1].pixelIndex,swapped[0].pixelIndex];
 [coherentRoster[0].index,coherentRoster[1].index]=[coherentRoster[1].index,coherentRoster[0].index];
 const coherentRaw=Buffer.from(JSON.stringify(coherentRoster)),coherentEncoded=gzipSync(coherentRaw);
 coherentData.additiveRelease.owner_roster={...asset('additive-repairs/owners1.json.gz',coherentEncoded),encoding:'gzip',decoded_bytes:coherentRaw.length,decoded_sha256:createHash('sha256').update(coherentRaw).digest('hex')};
 await assert.rejects(loadAdditiveNativePatch(coherentData,swapped,base,{fetcher:async path=>path.includes('owners1')?new Response(coherentEncoded):fetcher(path)}),/original native manifest/);
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
 const p='coordination/engineering/additive-native-gap-repair-20261008/add031-release-proposal-v2/';
 const publication=JSON.parse(fs.readFileSync(p+'publication.json'));
 const read=name=>{const descriptor=publication.assets.find(row=>row.path===name),raw=fs.readFileSync(p+name);
  assert.equal(raw.length,descriptor.bytes);assert.equal(createHash('sha256').update(raw).digest('hex'),descriptor.sha256);return JSON.parse(raw);};
 const patch=read('patch-add031.json'),feature=read('feature.json'),window=read('owner-window.json');
 const {pointInFeature,pointInGeometry}=await import('../src/geometry.js');
 const latitudes=gunzipSync(fs.readFileSync('coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz'));
 assert.equal(createHash('sha256').update(latitudes).digest('hex'),'66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23');
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
  const originalPoint=[(x+.5)/262166*360-180,latitudes.readDoubleLE(row.y*8)];
  assert.equal(pointInGeometry(originalPoint,feature.geometry),false);assert.equal(pointInFeature(originalPoint,feature),true);
  assert.equal(after[(row.y-61359)*262166+x],pickOwnership(out,x,row.y));
 }
 assert.equal(out.additive_added_cells,7);
 const drift=structuredClone(patch);drift.rows[0].runs[0][0]=window[0].complete_owner_intervals[0][0];drift.rows[0].runs[0][1]=drift.rows[0].runs[0][0]+1;drift.rows[0].y=window[0].y;
 assert.throws(()=>applyAdditiveNativePatch(base,drift,{baseReference:patch.base_reference,effectiveReference:patch.effective_reference,features:ownerFeatures}),/assigned/);
});

test('actual shared thirteen-case batch draws and picks all134 new cells with complete125-row old-owner conservation',async()=>{
 const {default:fs}=await import('node:fs'),{pointInFeature}=await import('../src/geometry.js');
 const p='coordination/engineering/additive-native-gap-batch-20261008/',output=p+'batch-proposal-v1-run1/';
 const publication=JSON.parse(fs.readFileSync(output+'publication.json'));
 const read=name=>{const descriptor=publication.assets.find(row=>row.path===name),raw=fs.readFileSync(output+name);
  assert.equal(raw.length,descriptor.bytes);assert.equal(createHash('sha256').update(raw).digest('hex'),descriptor.sha256);return JSON.parse(raw);};
 const patch=read('patch-batch.json'),effective=read('features.json'),ledger=read('ledger-batch.json');
 assert.equal(ledger.scope_ids.length,13);assert.equal(ledger.rows.filter(row=>row.disposition==='assigned').length,11);
 assert.equal(ledger.rows.filter(row=>row.disposition==='rejected').length,2);assert.equal(effective.length,6);
 const originalWindow=JSON.parse(fs.readFileSync(p+'current-v8/complete-owner-rows.json'));
 assert.equal(originalWindow.length,125);const rows=Array(262166).fill(new Uint32Array());
 for(const row of originalWindow)rows[row.y]=Uint32Array.from(row.complete_owner_intervals.flat());
 // Declared complete observed-row VIEW: unobserved world rows are not evidence.
 // Full real owner identities and affected target geometry remain authenticated.
 const rosterRaw=gunzipSync(fs.readFileSync(output+'owners-batch.json.gz')),descriptor=publication.assets.find(row=>row.path==='owners-batch.json.gz');
 assert.equal(rosterRaw.length,descriptor.uncompressed_bytes);assert.equal(createHash('sha256').update(rosterRaw).digest('hex'),descriptor.uncompressed_sha256);
 const bounds=JSON.parse(rosterRaw),byId=new Map(effective.map(feature=>[feature.id,feature])),model=rectangle(0,0,1,1);
 const features=bounds.map(row=>byId.get(row.id)??{id:row.id,pixelIndex:row.index,geometry:model});
 const base={...packOwnership({size:262166,rows}),method:'native-linear-evenodd-first-owner-v1',geographic_release:patch.base_reference.id,...patch.base_reference,
  reference_owner_sha256:createHash('sha256').update(JSON.stringify(bounds.map(row=>[row.index,row.id]).sort((a,b)=>a[0]-b[0]))).digest('hex')};
 const oldRows=base.rows.slice(),oldRuns=base.runs.slice();
 const out=applyAdditiveNativePatch(base,patch,{baseReference:patch.base_reference,effectiveReference:patch.effective_reference,features});
 let added=0,existing=0;for(const row of originalWindow){
  const before=samplePackedOwnership(base,{x:0,y:row.y,width:262166,height:1}),after=samplePackedOwnership(out,{x:0,y:row.y,width:262166,height:1});
  for(let x=0;x<before.length;x++){if(before[x]){assert.equal(after[x],before[x]);existing++;}else if(after[x]){assert.equal(pickOwnership(out,x,row.y),after[x]);added++;}}
 }
 assert.equal(added,134);assert.ok(existing>0);assert.equal(out.additive_added_cells,134);assert.deepEqual(base.rows,oldRows);assert.deepEqual(base.runs,oldRuns);
 const latitudeBody=gunzipSync(fs.readFileSync('coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz'));
 const byOwner=new Map(effective.map(feature=>[feature.pixelIndex,feature]));
 for(const row of patch.rows)for(const [start,end,owner]of row.runs)for(let x=start;x<end;x++){
  assert.equal(pickOwnership(base,x,row.y),0);assert.equal(pickOwnership(out,x,row.y),owner);
  assert.equal(pointInFeature([(x+.5)/262166*360-180,latitudeBody.readDoubleLE(row.y*8)],byOwner.get(owner)),true);
 }
 // More than one original primitive is aggregated under one stable owner.
 assert.ok(effective.some(feature=>feature.additiveFootprint.additions.length>1));
 const drift=structuredClone(patch),occupied=originalWindow.find(row=>row.complete_owner_intervals.length);
 drift.rows=[{y:occupied.y,runs:[[occupied.complete_owner_intervals[0][0],occupied.complete_owner_intervals[0][0]+1,effective[0].pixelIndex]]}];
 assert.throws(()=>applyAdditiveNativePatch(base,drift,{baseReference:patch.base_reference,effectiveReference:patch.effective_reference,features}),/assigned/);
});


// Synthetic source-backed metadata correction, full canonical row dimensions.
// Real loading, picking and sampling exercise the N (native), M (metadata) and
// E (additive) bindings; this fixture makes no real-world scientific claim.
async function metadataRuntimeFixture(){
 const {default:fs}=await import('node:fs'),{shuffleOwnershipBytes}=await import('../src/ownership-codec.js');
 const sha=body=>createHash('sha256').update(body).digest('hex'),json=value=>Buffer.from(JSON.stringify(value)+'\n');
 const asset=(path,body)=>({path,bytes:body.length,sha256:sha(body)}),bodies=new Map();
 let serial=0;
 const pin=(path,value)=>{const body=json(value),descriptor={...asset(path,body),commit:(++serial).toString(16).padStart(40,'0'),mode:'100644',git_blob_oid:createHash('sha1').update('blob '+body.length+'\0').update(body).digest('hex')};bodies.set(descriptor.commit+':'+path,body);return descriptor;};
 const originalFeatures=['owner1','owner2','owner3'].map((id,i)=>({type:'Feature',id,pixelIndex:i+1,geometry:rectangle(i*2,0,i*2+1,1),
  properties:{id,name:id,parent_id:i===2?'new':'old',metadata:{source_id:'original-source',framework_match:{id:'retained-fallback',overlap:.8}}}}));
 const currentFeatures=structuredClone(originalFeatures),before=currentFeatures[0].properties;
 const after={...structuredClone(before),parent_id:'new'};after.metadata.reference_corrections=[{id:before.id,action:'reparent',current_name:before.name,current_parent_id:'old',new_parent_id:'new',rationale:'Exact retained source correspondence; geometry and history unchanged.',evidence:[{url:'https://example.org/source',title:'Retained source',inspected_fact:'The original member belongs to the current named parent.'}]}];
 currentFeatures[0].properties=after;
 const changes=[{location_id:before.id,before_properties:before,after_properties:after}];
 const units=['continent','subcontinent','region','area'].map((level,i,a)=>({id:level,name:level,level,parent_id:i?a[i-1]:null}));
 units.push({id:'old',name:'Old',level:'province',parent_id:'area',metadata:{child_count:2}},
  {id:'new',name:'New',level:'province',parent_id:'area',metadata:{child_count:1}});
 const currentUnits=structuredClone(units);currentUnits[4].metadata.child_count=1;currentUnits[5].metadata.child_count=2;
 const hierarchy={before:pin('data/hierarchy.json',units),after:pin('data/hierarchy.json',currentUnits)};
 const native={id:'geography:original-native',footprints_sha256:loadedBaseFootprintSha256(originalFeatures),hierarchy_sha256:hierarchy.before.sha256};
 const reference={...native,id:'geography:current-metadata',hierarchy_sha256:hierarchy.after.sha256};
 const receipt=pin('data/reference-correction.json',{before_sha256:native.hierarchy_sha256,after_sha256:reference.hierarchy_sha256,footprints_sha256_before:native.footprints_sha256,footprints_sha256_after:native.footprints_sha256,reference_only:true,historical_claims_transferred:false,summary:{geometry_changes:0},relationships:[],before_units:units,retired_units:[],group_changes:[4,5].map(i=>({id:units[i].id,before:units[i],after:currentUnits[i]})),changed_location_properties:changes,source_evidence:[{url:'https://example.org/source',source_sha256:'1'.repeat(64)}]});
 const source_updates=[{logical_path:'data/geography/part-0.json',before:pin('data/geography/part-0.json',{type:'FeatureCollection',features:originalFeatures}),after:pin('data/geography/part-0.json',{type:'FeatureCollection',features:currentFeatures})}];
 const rows=Array(262166).fill(new Uint32Array());rows[3]=Uint32Array.from([1,3,1,8,10,2]);rows[4]=Uint32Array.from([7,8,3]);
 const base={...packOwnership({size:rows.length,rows}),method:'native-linear-evenodd-first-owner-v1',geographic_release:native.id,footprints_sha256:native.footprints_sha256,hierarchy_sha256:native.hierarchy_sha256};
 const transports=new Map(),put=(path,body)=>{transports.set('./'+path,body);return asset(path,body);};
 const parts=['rows','runs'].map(kind=>{const words=base[kind],body=gzipSync(shuffleOwnershipBytes(words));return {...put('ownership/'+kind+'.bin.gz',body),kind,offset:0,words:words.length,encoding:'byte-shuffle',decoded_sha256:sha(new Uint8Array(words.buffer))};});
 const owners=originalFeatures.map(f=>({id:f.id,index:f.pixelIndex,province_id:f.properties.parent_id,province_index:f.properties.parent_id==='new'?1:2,bounds:[0,0,10,10]}));
 const roster=json(owners),rosterAsset={...put('additive-repairs/owners.json.gz',gzipSync(roster)),encoding:'gzip',decoded_bytes:roster.length,decoded_sha256:sha(roster)};
 const manifest={geographic_release:native.id,footprints_sha256:native.footprints_sha256,hierarchy_sha256:native.hierarchy_sha256,method:base.method,size:base.size,coordinateBits:base.coordinateBits,parts,original_assets:{bounds:{sha256:rosterAsset.sha256}}};
 const manifestAsset=put('additive-repairs/base-manifest.json',json(manifest));
 const selection={version:1,method:base.method,manifest_path:'data/native.json',sha256:manifestAsset.sha256,release_id:native.id,artifact_consumption:{certificate:{original:'retained'},review:{original:'retained'}}};
 const projection=prepareReferenceMetadataProjection({selection,manifest,owners,reference,hierarchy,receipts:[receipt],source_updates,read:p=>bodies.get(p.commit+':'+p.path)});
 const referenceMetadata={version:1,asset:put('reference-metadata/current.json',json(projection)),native_reference:native,reference};
 const component={component_id:'gap',disposition:'assigned',native_cells:2,target_id:'owner1',pixelIndex:1,base_geometry:originalFeatures[0].geometry,base_geometry_sha256:hash(originalFeatures[0].geometry),geometry:rectangle(1,0,2,1),geometry_sha256:hash(rectangle(1,0,2,1)),source_receipt_sha256:'2'.repeat(64),authority_sha256:'3'.repeat(64),rule_sha256:'4'.repeat(64)};
 const ledger={version:2,kind:'native-additive-repair-ledger-v2',authority_registry_sha256:'5'.repeat(64),base_reference:reference,parent_inventory:{components:1,report_sha256:'6'.repeat(64),roster_sha256:'7'.repeat(64)},scope_ids:['gap'],rows:[component]};
 const ledgerAsset=put('additive-repairs/ledger.json',json(ledger)),effectiveFeatures=structuredClone(currentFeatures);
 effectiveFeatures[0].additiveFootprint={version:2,kind:'retained-base-plus-additions',baseline_release_sha256:reference.footprints_sha256,base_geometry_sha256:component.base_geometry_sha256,ledger_sha256:ledgerAsset.sha256,authority_registry_sha256:ledger.authority_registry_sha256,components:[component]};
 const effective={...reference,id:'geography:current-effective',footprints_sha256:additiveReleaseFootprintDigest(reference,effectiveFeatures)};
 const patch={version:2,kind:'unassigned-native-cells-v1',base_reference:reference,effective_reference:effective,ledger_sha256:ledgerAsset.sha256,authority_registry_sha256:ledger.authority_registry_sha256,rows:[{y:3,runs:[[3,5,1]]}]};
 const latRaw=fs.readFileSync('coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz');
 put('native-v1/native-row-latitudes.f64le.gz',latRaw);
 const native_latitudes={root:'repository',role:'immutable-normative-rule-input',path:'coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz',commit:'1'.repeat(40),bytes:latRaw.length,sha256:sha(latRaw),decoded_bytes:base.size*8,decoded_sha256:'66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23',transport_path:'native-v1/native-row-latitudes.f64le.gz'};
 const physicalRows=Array(base.size).fill(new Uint32Array());physicalRows[3]=Uint32Array.from([0,12,1]);
 const physical=packOwnership({size:base.size,rows:physicalRows});
 const coverageParts=['rows','runs'].map(kind=>{const words=physical[kind],body=gzipSync(shuffleOwnershipBytes(words));return {...put('coverage-classification/'+kind+'-0.bin.gz',body),kind,offset:0,words:words.length,encoding:'byte-shuffle',compressed_bytes:body.length,decoded_sha256:sha(new Uint8Array(words.buffer))};});
 const data={reference_release:effective,referenceMetadata,units:currentUnits,temporal:{links:[],history:[]},parts:['geography/catalog.json'],geometryParts:['geography/geometries.json'],
  additiveRelease:{version:2,kind:'retained-native-base-plus-delta-v2',base_reference:reference,effective_reference:effective,base_manifest:manifestAsset,owner_roster:rosterAsset,ledger:ledgerAsset,patch:put('additive-repairs/patch.json',json(patch))},
  pixelMap:{...manifest,version:2,runWords:base.runs.length,canonical_grid_sha256:manifestAsset.sha256,native_latitudes},
  coverageClassification:{kind:'physical-reference-classification',classification_version:1,version:2,size:base.size,coordinateBits:base.coordinateBits,runWords:physical.runs.length,release_id:native.id,footprints_sha256:native.footprints_sha256,hierarchy_sha256:native.hierarchy_sha256,canonical_grid_sha256:manifestAsset.sha256,sources:[1,2].map(i=>({name:'Original physical '+i,url:'https://example.org/physical-'+i,original_sha256:String(i).repeat(64)})),parts:coverageParts}};
 put('geography/catalog.json',json(currentFeatures.map(f=>({...f,geometry:null}))));
 put('geography/geometries.json',json(originalFeatures.map(({id,geometry})=>({id,geometry}))));
 return{data,base,originalFeatures,currentFeatures,effectiveFeatures,native,reference,effective,projection,patch,transports,json,asset,
  fetcher:async path=>{assert.ok(transports.has(path),'Unexpected fixture read: '+path);return new Response(transports.get(path));}};
}

test('real geography entry keeps native words, latitudes and physical coverage at N while projecting catalog parents to M and adding E',async()=>{
 const f=await metadataRuntimeFixture(),{createServer}=await import('vite'),oldFetch=globalThis.fetch;
 const server=await createServer({configFile:false,server:{middlewareMode:true},define:{'import.meta.env.VITE_STATIC_ATLAS':'"true"','import.meta.env.VITE_HOSTED_DATABASE':'"false"'}});
 try{
  let geometryReads=0;globalThis.fetch=async path=>{if(path==='./atlas-geography.json')return new Response(f.json(f.data));if(path==='./geography/geometries.json')geometryReads++;return f.fetcher(path);};
  const before=structuredClone(f.base),directFeatures=structuredClone(f.currentFeatures);
  const direct=await loadAdditiveNativePatch(f.data,directFeatures,f.base,{fetcher:f.fetcher});
  assert.notEqual(direct,f.base);assert.deepEqual(f.base,before);
  for(let y=3;y<=4;y++)for(let x=0;x<12;x++){const old=pickOwnership(before,x,y);if(old)assert.equal(pickOwnership(direct,x,y),old);}
  const client=await server.ssrLoadModule('/src/data-client.js'),loaded=await client.loadGeography();
  assert.deepEqual(nativeReferenceForData(loaded),f.native);assert.deepEqual(additiveBaseReference(loaded),f.reference);
  assert.equal(loaded.pixelMap.geographic_release,f.native.id);assert.equal(loaded.pixelMap.hierarchy_sha256,f.native.hierarchy_sha256);
  assert.equal(loaded.coverage.manifest.release_id,f.native.id);assert.equal(loaded.coverage.manifest.hierarchy_sha256,f.native.hierarchy_sha256);
  assert.equal(loaded.nativeLatitudes.length,262166);assert.equal(geometryReads,0);
  assert.deepEqual(loaded.features.map(row=>row.properties.parent_id),['new','old','new']);
  assert.equal(loaded.features[0].properties.metadata.framework_match.id,'retained-fallback');
  assert.equal(loaded.features[0].properties.metadata.reference_corrections.length,1);
  assert.equal(loaded.features[1].geometry,null);assert.ok(loaded.features[0].additiveFootprint);
  assert.equal(loaded.ownership.geographic_release,f.effective.id);assert.equal(loaded.ownership.hierarchy_sha256,f.reference.hierarchy_sha256);
  assert.deepEqual(loaded.ownership.additive_base_reference,f.reference);assert.equal(loaded.ownership.reference_owner_source_sha256,f.data.additiveRelease.owner_roster.sha256);
  assert.equal(pickOwnership(loaded.ownership,3,3),1);assert.equal(pickOwnership(loaded.ownership,8,3),2);assert.equal(pickOwnership(loaded.ownership,7,4),3);
  assert.deepEqual([...samplePackedOwnership(loaded.ownership,{x:0,y:3,width:12,height:1})],[0,1,1,1,1,0,0,0,2,2,0,0]);
  assert.deepEqual(loaded.ownership.rows,direct.rows);assert.deepEqual(loaded.ownership.runs,direct.runs);
  await client.ensureGeometry(loaded);assert.equal(geometryReads,1);
  assert.deepEqual(loaded.features.map(({id,geometry})=>({id,geometry})),f.originalFeatures.map(({id,geometry})=>({id,geometry})));
  assert.equal(loaded.additiveRelease.version,2);assert.deepEqual(Object.keys(loaded.additiveRelease).sort(),['version','kind','base_reference','effective_reference','base_manifest','owner_roster','ledger','patch'].sort());
 }finally{globalThis.fetch=oldFetch;await server.close();}
});

test('metadata runtime rejects malformed transport, unbound projection and every stale or unrelated owner parent',async()=>{
 const f=await metadataRuntimeFixture();
 const rejects=async(change,error)=>{const data=JSON.parse(f.json(f.data)),features=structuredClone(f.currentFeatures),base=structuredClone(f.base),transports=new Map(f.transports);change({data,features,base,transports});const before=structuredClone({features,base});
  await assert.rejects(loadAdditiveNativePatch(data,features,base,{fetcher:async path=>new Response(transports.get(path))}),error);
  assert.deepEqual({features,base},before,'Rejected metadata must not mutate caller ownership or features');};
 const repin=(state,edit)=>{const projection=structuredClone(f.projection);edit(projection);const body=f.json(projection);state.data.referenceMetadata.asset=f.asset('reference-metadata/current.json',body);state.transports.set('./reference-metadata/current.json',body);};
 for(const mutate of [m=>m.foreign=true,m=>m.version=2,m=>m.asset.path='../current.json',m=>m.asset.path='reference-metadata/other.json',m=>m.asset.bytes=0,m=>m.asset.bytes=32*1024*1024+1,m=>m.asset.sha256='broken',m=>m.asset.encoding='gzip',m=>m.native_reference.hierarchy_sha256='0'.repeat(64),m=>m.reference.id='geography:foreign',m=>m.reference.foreign=true])
  await rejects(({data})=>mutate(data.referenceMetadata),/metadata|reference/i);
 await rejects(({data})=>delete data.referenceMetadata,/original native manifest/);
 await rejects(({data})=>delete data.additiveRelease,/explicit selected native asset closure/);
 await rejects(({base})=>base.hierarchy_sha256=f.reference.hierarchy_sha256,/original selected reference/);
 await rejects(({base})=>base.runs[0]^=1,/original selected manifest/);
 await rejects(({transports})=>{const body=Buffer.from(f.transports.get('./reference-metadata/current.json'));body[0]^=1;transports.set('./reference-metadata/current.json',body);},/whole checksum/);
 await rejects(({transports})=>transports.set('./reference-metadata/current.json',Buffer.concat([f.transports.get('./reference-metadata/current.json'),Buffer.from(' ')])),/exceeds/);
 for(const [edit,error]of [
  [p=>p.native_selection.sha256='0'.repeat(64),/selected native manifest/],
  [p=>p.native_reference.id='geography:foreign',/original native selection/],
  [p=>p.reference.hierarchy_sha256='0'.repeat(64),/hierarchy bytes/],
  [p=>p.original_owner_roster_sha256='0'.repeat(64),/owner roster/],
  [p=>p.foreign=true,/Unsupported/],
  [p=>p.location_changes=[],/owner or parent/],
  [p=>p.location_changes.push(p.location_changes[0]),/duplicate/],
  [p=>p.location_changes[0].before_properties.parent_id='foreign',/stale|exact sourced/],
  [p=>p.location_changes[0].after_properties.metadata.framework_match.id='replaced',/Non-parent/],
  [p=>p.location_changes[0].after_properties.metadata.reference_corrections=[],/explicit sourced correction append/],
  [p=>p.provinces.push('unused'),/empty or foreign province/]
 ])await rejects(state=>repin(state,edit),error);
 await rejects(({features})=>features[0].properties.parent_id='old',/complete applied source/);
 for(const mutate of [
  properties=>delete properties.metadata.reference_corrections,
  properties=>properties.metadata.reference_corrections=[],
  properties=>properties.metadata.reference_corrections[0].rationale='replaced correction history',
  properties=>properties.metadata.source_id='different-source',
  properties=>properties.metadata.framework_match.id='different-fallback',
  properties=>properties.metadata.framework_match.overlap=.9,
  properties=>properties.active=0,
  properties=>properties.reference_owner='unrequested-owner'
 ])await rejects(({features})=>mutate(features[0].properties),/complete applied source/);
 await rejects(({features})=>features[1].properties.parent_id='new',/owner or parent/);
 await rejects(({features})=>features[2].pixelIndex=4,/owner or parent/);
 await rejects(({features})=>features[2].geometry=rectangle(30,0,31,1),/original base/);
 await rejects(state=>{const effective={...f.effective,hierarchy_sha256:'0'.repeat(64)},patch={...f.patch,effective_reference:effective},body=f.json(patch);state.data.reference_release=effective;state.data.additiveRelease.effective_reference=effective;state.data.additiveRelease.patch=f.asset('additive-repairs/patch.json',body);state.transports.set('./additive-repairs/patch.json',body);},/cannot change hierarchy/);
});


test('actual native and geography loaders retain generated defaults and reject stale source or correction-history catalog transport',async()=>{
 const f=await metadataRuntimeFixture(),{createServer}=await import('vite'),oldFetch=globalThis.fetch;
 const generated=f.currentFeatures.map(feature=>({...feature,properties:{...structuredClone(feature.properties),active:1,reference_owner:null}}));
 const features=structuredClone(generated),before=structuredClone(f.base);
 const output=await loadAdditiveNativePatch(f.data,features,f.base,{fetcher:f.fetcher});
 assert.equal(pickOwnership(output,3,3),1);assert.deepEqual(f.base,before);
 assert.deepEqual(features[0].properties,generated[0].properties);assert.equal(features[0].properties.metadata.reference_corrections.length,1);
 f.transports.set('./geography/catalog.json',f.json(generated.map(feature=>({...feature,geometry:null}))));
 const server=await createServer({configFile:false,server:{middlewareMode:true},define:{'import.meta.env.VITE_STATIC_ATLAS':'"true"','import.meta.env.VITE_HOSTED_DATABASE':'"false"'}});
 try{
  globalThis.fetch=async path=>path==='./atlas-geography.json'?new Response(f.json(f.data)):f.fetcher(path);
  const client=await server.ssrLoadModule('/src/data-client.js'),loaded=await client.loadGeography();
  assert.deepEqual(loaded.features[0].properties,generated[0].properties);
  assert.equal(loaded.features[0].properties.active,1);assert.equal(loaded.features[0].properties.reference_owner,null);
  assert.equal(pickOwnership(loaded.ownership,3,3),1);assert.equal(pickOwnership(loaded.ownership,8,3),2);
  assert.equal(loaded.ownership.hierarchy_sha256,f.reference.hierarchy_sha256);
  const original=JSON.stringify(loaded.features);
  for(const mutate of [properties=>delete properties.metadata.reference_corrections,properties=>properties.metadata.source_id='different-source',properties=>properties.metadata.framework_match.id='different-fallback']){
   const changed=structuredClone(generated);mutate(changed[0].properties);
   f.transports.set('./geography/catalog.json',f.json(changed.map(feature=>({...feature,geometry:null}))));
   await assert.rejects(client.loadGeography(),/complete applied source/);
   assert.equal(JSON.stringify(loaded.features),original,'A rejected later geography generation must preserve the complete previously loaded features');
  }
 }finally{globalThis.fetch=oldFetch;await server.close();}
});
