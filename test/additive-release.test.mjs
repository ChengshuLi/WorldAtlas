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
