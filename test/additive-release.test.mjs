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
test('packed replacements preserve every native word against an independent cell-owner oracle',()=>{
 const {base,patch,options}=fixture(),size=base.size,width=128,cellRows=new Map();
 const rows=Array(size).fill(new Uint32Array());
 // Deterministic sparse, dense, adjacent equal/different owners, empty rows and
 // high owner bits exercise both packed words; no random test expectations.
 options.features[1].pixelIndex=2**20+3;
 options.features[1].additiveFootprint={...structuredClone(options.features[0].additiveFootprint),
  base_geometry_sha256:hash(options.features[1].geometry)};
 for(let y=0;y<320;y++){
  const cells=new Uint32Array(width),before=[];
  for(let x=0;x<width;x++)if((x*17+y*13)%7<2)cells[x]=(x+y)%2?1:options.features[1].pixelIndex;
  for(let x=0;x<width;){if(!cells[x]){x++;continue;}let end=x+1;while(end<width&&cells[end]===cells[x])end++;before.push(x,end,cells[x]);x=end;}
  rows[y]=Uint32Array.from(before);cellRows.set(y,cells);
 }
 Object.assign(base,packOwnership({size,rows}));
 base.reference_owner_sha256=createHash('sha256').update(JSON.stringify(options.features.map(f=>[f.pixelIndex,f.id]))).digest('hex');
 patch.rows=[];let added=0;
 for(let y=0;y<320;y++)if(y%3!==2){
  const cells=cellRows.get(y),runs=[];
  for(let x=0;x<width;x++)if(!cells[x]&&(x+y)%4!==0){const owner=(x+y)%2?1:options.features[1].pixelIndex;runs.push([x,x+1,owner]);cells[x]=owner;added++;}
  if(runs.length)patch.rows.push({y,runs});
 }
 const expectedRows=Array(size).fill(new Uint32Array());
 for(const [y,cells] of cellRows){const runs=[];for(let x=0;x<width;){if(!cells[x]){x++;continue;}let end=x+1;while(end<width&&cells[end]===cells[x])end++;runs.push(x,end,cells[x]);x=end;}expectedRows[y]=Uint32Array.from(runs);}
 const expected=packOwnership({size,rows:expectedRows}),originalRows=base.rows.slice(),originalRuns=base.runs.slice(),originalPatch=JSON.stringify(patch);
 const actual=applyAdditiveNativePatch(base,patch,options);
 assert.deepEqual(actual.rows,expected.rows);assert.deepEqual(actual.runs,expected.runs);
 assert.equal(actual.additive_added_cells,added);assert.deepEqual(base.rows,originalRows);assert.deepEqual(base.runs,originalRuns);assert.equal(JSON.stringify(patch),originalPatch);
 assert.equal(applyAdditiveNativePatch(actual,patch,options),actual);
});

test('packed merge preserves seam endpoints, maximum owner bits and two-sided equal-owner coalescing',()=>{
 const {base,patch,options}=fixture(),size=base.size,high=2**26-1;
 options.features[1].pixelIndex=high;
 options.features[1].additiveFootprint={...structuredClone(options.features[0].additiveFootprint),
  base_geometry_sha256:hash(options.features[1].geometry)};
 const rows=Array(size).fill(new Uint32Array());
 rows[0]=Uint32Array.from([0,1,high,5,7,1,size-2,size-1,high]);
 rows[size-1]=Uint32Array.from([1,3,high,4,6,1,7,9,high]);
 Object.assign(base,packOwnership({size,rows}));
 base.reference_owner_sha256=createHash('sha256').update(JSON.stringify(options.features.map(f=>[f.pixelIndex,f.id]))).digest('hex');
 patch.rows=[{y:0,runs:[[1,5,high],[7,8,1],[size-1,size,high]]},
  {y:1,runs:[[0,size,1]]},{y:size-1,runs:[[0,1,high],[3,4,1],[6,7,1],[9,10,high]]}];
 const expectedRows=Array(size).fill(new Uint32Array());
 expectedRows[0]=Uint32Array.from([0,5,high,5,8,1,size-2,size,high]);
 expectedRows[1]=Uint32Array.from([0,size,1]);
 expectedRows[size-1]=Uint32Array.from([0,3,high,3,7,1,7,10,high]);
 const expected=packOwnership({size,rows:expectedRows}),beforeRows=base.rows.slice(),beforeRuns=base.runs.slice(),beforePatch=JSON.stringify(patch);
 const actual=applyAdditiveNativePatch(base,patch,options);
 assert.deepEqual(actual.rows,expected.rows);assert.deepEqual(actual.runs,expected.runs);
 assert.equal(actual.additive_added_cells,size+10);assert.deepEqual(base.rows,beforeRows);assert.deepEqual(base.runs,beforeRuns);assert.equal(JSON.stringify(patch),beforePatch);
});

test('packed merge refuses malformed base rows and later overlap without mutating either input',()=>{
 const cases=[
  [f=>f.base.rows[7]=f.base.runs.length,/Incomplete base native row/],
  [f=>f.base.runs[0]=3,/Invalid\/foreign base ownership run/],
  [f=>f.base.runs[1]=2**19,/Invalid\/foreign base ownership run/],
  [f=>f.base.runs[2]=2**19+2,/Invalid\/foreign base ownership run/],
  [f=>f.base.runs[3]=f.base.size,/Invalid\/foreign base ownership run/],
  [f=>f.patch.rows[0].runs=[[3,5,1],[7,9,1]],/replace an assigned cell/],
  [f=>f.patch.rows[0].runs=[[7,8,1],[3,5,1]],/Conflicting or foreign current additive run/],
  [f=>f.patch.rows[0].runs=[[3,3,1]],/Conflicting or foreign current additive run/],
  [f=>f.patch.rows[0].runs=[[3,f.base.size+1,1]],/Conflicting or foreign current additive run/],
  [f=>f.patch.rows[0].runs=[[3,5,2**26]],/Conflicting or foreign current additive run/],
  [f=>f.patch.rows[0].runs=[[3,5.5,1]],/Conflicting or foreign current additive run/],
  [f=>f.patch.rows.push({...f.patch.rows[0]}),/Duplicate\/unordered\/outside native patch row/]
 ];
 for(const [edit,error] of cases){
  const f=fixture();edit(f);const rows=f.base.rows.slice(),runs=f.base.runs.slice(),patch=JSON.stringify(f.patch);
  assert.throws(()=>applyAdditiveNativePatch(f.base,f.patch,f.options),error);
  assert.deepEqual(f.base.rows,rows);assert.deepEqual(f.base.runs,runs);assert.equal(JSON.stringify(f.patch),patch);
 }
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
  const words=base[kind],body=gzipSync(shuffleOwnershipBytes(words)),path='native-v1/ownership/'+kind+'-0.bin.gz';transports.set('./'+path,body);
  return {kind,offset:0,words:words.length,path,encoding:'byte-shuffle',sha256:createHash('sha256').update(body).digest('hex'),decoded_sha256:createHash('sha256').update(new Uint8Array(words.buffer)).digest('hex')};
 });
 const units=['province','area','region','subcontinent','continent'].map((level,i)=>({id:level,level,parent_id:i===4?null:['area','region','subcontinent','continent'][i]}));
 const normalFeatures=options.features.map(({additiveFootprint,...f})=>({...f,properties:{...f.properties,id:f.id,parent_id:'province'}}));
 const normalRoster=Buffer.from(JSON.stringify(normalFeatures.map(f=>({id:f.id,index:f.pixelIndex,province_id:'province',bounds:[0,0,3,3]})))),normalRosterEncoded=gzipSync(normalRoster);
 const normalManifest=Buffer.from(JSON.stringify({...JSON.parse(manifestRaw),version:2,runWords:base.runs.length,parts,native_latitudes:latitude,original_assets:{bounds:{sha256:createHash('sha256').update(normalRosterEncoded).digest('hex')}}}));
 const normalData={...structuredClone(data),units,temporal:{links:[],history:[]},parts:['geography/catalog.json'],geometryParts:['geography/geometries.json'],pixelMap:{...data.pixelMap,...options.baseReference,geographic_release:options.baseReference.id,version:2,size:262166,coordinateBits:19,method:base.method,runWords:base.runs.length,native_latitudes:latitude,parts,canonical_grid_sha256:createHash('sha256').update(normalManifest).digest('hex')}};
 normalData.additiveRelease.base_manifest=asset('additive-repairs/base-native-manifest.json',normalManifest);
 normalData.additiveRelease.owner_roster={...asset('additive-repairs/owners1.json.gz',normalRosterEncoded),encoding:'gzip',decoded_bytes:normalRoster.length,decoded_sha256:createHash('sha256').update(normalRoster).digest('hex')};
 transports.set('./native-v1/native-row-latitudes.f64le.gz',latRaw);
 transports.set('./geography/catalog.json',Buffer.from(JSON.stringify(normalFeatures.map(f=>({...f,geometry:null})))));
 transports.set('./geography/geometries.json',Buffer.from(JSON.stringify(normalFeatures.map(f=>({id:f.id,geometry:f.geometry})))))
 await prepareBrowserFixture({data:normalData,features:normalFeatures,transports,fetcher:async p=>transports.has(p)?new Response(transports.get(p)):p.includes('base-native-manifest')?new Response(normalManifest):p.includes('owners1')?new Response(normalRosterEncoded):fetcher(p)});
 const server=await createServer({configFile:false,server:{middlewareMode:true,watch:null},define:{'import.meta.env.VITE_STATIC_ATLAS':'"true"','import.meta.env.VITE_HOSTED_DATABASE':'"false"'}}),oldFetch=globalThis.fetch;
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
async function prepareBrowserFixture({data,features,transports,fetcher}){
 const fs=await import('node:fs/promises'),os=await import('node:os'),path=await import('node:path');
 const {packageStartupOwnership,packagePreparedStartupOwnership}=await import('../scripts/package-startup-ownership.mjs');
 const {prepareSelectedStartupOwnership}=await import('../scripts/prepare-startup-ownership.mjs');
 const {scientificNativeSelection}=await import('../src/reference-metadata.js');
 const root=await fs.mkdtemp(path.join(os.tmpdir(),'atlas-prepared-final-'));
 const sha=raw=>createHash('sha256').update(raw).digest('hex'),raws=new Map();
 const pin=(name,raw,extra={})=>{const p={commit:'1'.repeat(40),path:name,mode:'100644',git_blob_oid:createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex'),bytes:raw.length,sha256:sha(raw),...extra};raws.set(name,raw);return p;};
 const write=async(root,name,raw)=>{await fs.mkdir(path.dirname(path.join(root,name)),{recursive:true});await fs.writeFile(path.join(root,name),raw,{flag:'wx'});};
 try{
  const assets={};
  for(const role of ['base_manifest','owner_roster','ledger','patch']){
   const a=data.additiveRelease[role],raw=Buffer.from(await (await fetcher('./'+a.path)).arrayBuffer());
   assets[role]=pin(`coordination/fixture/${role}.json`,raw,a.encoding?{encoding:a.encoding,decoded_bytes:a.decoded_bytes,decoded_sha256:a.decoded_sha256}:{});
  }
  const manifest=JSON.parse(raws.get(assets.base_manifest.path));
  const nativeSource=path.join(root,'source'),bank=path.join(root,'bank'),prefix='ownership-vintages/'+assets.base_manifest.sha256+'/';
  for(const part of manifest.parts)await write(nativeSource,part.path,Buffer.from(await (await fetcher('./'+part.path)).arrayBuffer()));
  const native=await packageStartupOwnership({manifest,source:nativeSource,destination:path.join(bank,prefix)});
  for(const part of manifest.parts.filter(p=>p.kind==='rows'))await write(bank,part.path,await fs.readFile(path.join(nativeSource,part.path)));
  await write(bank,'native-v1/native-row-latitudes.f64le.gz',transports.get('./native-v1/native-row-latitudes.f64le.gz'));
  const nativePixelMap={...native.pixelMap,canonical_grid_sha256:assets.base_manifest.sha256,
    native_latitudes:{...manifest.native_latitudes,transport_path:'native-v1/native-row-latitudes.f64le.gz'},
    parts:native.pixelMap.parts.map(p=>p.kind==='rows'?p:{...p,path:prefix+p.path})};
  let selection={version:1,method:manifest.method,manifest_path:'data/native.json',sha256:assets.base_manifest.sha256,release_id:manifest.geographic_release};
  if(data.referenceMetadata){
   const raw=Buffer.from(await(await fetcher('./'+data.referenceMetadata.asset.path)).arrayBuffer()),projection=JSON.parse(raw);
   selection={...projection.native_selection,reference_projection:pin('coordination/fixture/projection.json',raw)};
  }
  const sidecar={version:2,kind:'retained-native-additive-selection-v2',base_selection:scientificNativeSelection(selection),
   runtime_envelope:pin('coordination/fixture/envelope.json',Buffer.from(JSON.stringify(data.additiveRelease))),logical_asset_map:assets};
  selection.additive_release=pin('coordination/fixture/sidecar.json',Buffer.from(JSON.stringify(sidecar)));
  const selectionBytes=Buffer.from(JSON.stringify(selection));
  const index=await prepareSelectedStartupOwnership({selectionBytes,manifest,previous:{version:1,pixelMap:nativePixelMap,files:await inventory()},readNative:name=>fs.readFile(path.join(bank,name)),
   readPin:p=>raws.get(p.path),destination:bank});
  async function inventory(relative=''){
   const rows=[];for(const e of await fs.readdir(path.join(bank,relative),{withFileTypes:true})){
    const name=relative?relative+'/'+e.name:e.name;
    if(e.isDirectory())rows.push(...await inventory(name));else{const raw=await fs.readFile(path.join(bank,name));rows.push({path:name,bytes:raw.length,sha256:sha(raw)});}
   }return rows.sort((a,b)=>a.path.localeCompare(b.path));
  }
  index.files=await inventory();await write(bank,'index.json',Buffer.from(JSON.stringify(index)));
  const selected={selectionBytes,envelope:data.additiveRelease,base:data.additiveRelease.base_reference,referenceMetadata:data.referenceMetadata};
  const destination=path.join(root,'published');
  const copied=await packagePreparedStartupOwnership({manifest,manifestSha:selection.sha256,source:bank,destination,selected,features});
  for(const p of index.files)transports.set('./'+p.path,await fs.readFile(path.join(destination,p.path)));
  Object.assign(data,copied);
  return {index,manifest,selection,selected,bankBodies:new Map(await Promise.all(index.files.map(async pin=>[pin.path,await fs.readFile(path.join(bank,pin.path))])))};
 }finally{await fs.rm(root,{recursive:true,force:true});}
}

async function metadataRuntimeFixture({ledgerBytes,rosterBytes}={}){
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
 const parts=['rows','runs'].map(kind=>{const words=base[kind],body=gzipSync(shuffleOwnershipBytes(words));return {...put('native-v1/ownership/'+kind+'-0.bin.gz',body),kind,offset:0,words:words.length,encoding:'byte-shuffle',decoded_sha256:sha(new Uint8Array(words.buffer))};});
 const owners=originalFeatures.map(f=>({id:f.id,index:f.pixelIndex,province_id:f.properties.parent_id,province_index:f.properties.parent_id==='new'?1:2,bounds:[0,0,10,10]}));
 const rosterBody=json(owners),roster=rosterBytes===undefined?rosterBody:Buffer.concat([rosterBody,Buffer.alloc(rosterBytes-rosterBody.length,0x20)]);
 const rosterAsset={...put('additive-repairs/owners.json.gz',gzipSync(roster)),encoding:'gzip',decoded_bytes:roster.length,decoded_sha256:sha(roster)};
 const latRaw=fs.readFileSync('coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz');
 put('native-v1/native-row-latitudes.f64le.gz',latRaw);
 const native_latitudes={root:'repository',role:'immutable-normative-rule-input',path:'coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz',commit:'1'.repeat(40),bytes:latRaw.length,sha256:sha(latRaw),decoded_bytes:base.size*8,decoded_sha256:'66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23',transport_path:'native-v1/native-row-latitudes.f64le.gz'};
 const manifest={version:2,runWords:base.runs.length,native_latitudes,geographic_release:native.id,footprints_sha256:native.footprints_sha256,hierarchy_sha256:native.hierarchy_sha256,method:base.method,size:base.size,coordinateBits:base.coordinateBits,parts,original_assets:{bounds:{sha256:rosterAsset.sha256}}};
 const manifestAsset=put('additive-repairs/base-manifest.json',json(manifest));
 const selection={version:1,method:base.method,manifest_path:'data/native.json',sha256:manifestAsset.sha256,release_id:native.id,artifact_consumption:{certificate:{original:'retained'},review:{original:'retained'}}};
 const projection=prepareReferenceMetadataProjection({selection,manifest,owners,reference,hierarchy,receipts:[receipt],source_updates,read:p=>bodies.get(p.commit+':'+p.path)});
 const referenceMetadata={version:1,asset:put('reference-metadata/current.json',json(projection)),native_reference:native,reference};
 const component={component_id:'gap',disposition:'assigned',native_cells:2,target_id:'owner1',pixelIndex:1,base_geometry:originalFeatures[0].geometry,base_geometry_sha256:hash(originalFeatures[0].geometry),geometry:rectangle(1,0,2,1),geometry_sha256:hash(rectangle(1,0,2,1)),source_receipt_sha256:'2'.repeat(64),authority_sha256:'3'.repeat(64),rule_sha256:'4'.repeat(64)};
 const ledger={version:2,kind:'native-additive-repair-ledger-v2',authority_registry_sha256:'5'.repeat(64),base_reference:reference,parent_inventory:{components:1,report_sha256:'6'.repeat(64),roster_sha256:'7'.repeat(64)},scope_ids:['gap'],rows:[component]};
 const ledgerBody=json(ledger),ledgerRaw=ledgerBytes===undefined?ledgerBody:Buffer.concat([ledgerBody,Buffer.alloc(ledgerBytes-ledgerBody.length,0x20)]);
 const ledgerAsset=put('additive-repairs/ledger.json',ledgerRaw),effectiveFeatures=structuredClone(currentFeatures);
 effectiveFeatures[0].additiveFootprint={version:2,kind:'retained-base-plus-additions',baseline_release_sha256:reference.footprints_sha256,base_geometry_sha256:component.base_geometry_sha256,ledger_sha256:ledgerAsset.sha256,authority_registry_sha256:ledger.authority_registry_sha256,components:[component]};
 const effective={...reference,id:'geography:current-effective',footprints_sha256:additiveReleaseFootprintDigest(reference,effectiveFeatures)};
 const patch={version:2,kind:'unassigned-native-cells-v1',base_reference:reference,effective_reference:effective,ledger_sha256:ledgerAsset.sha256,authority_registry_sha256:ledger.authority_registry_sha256,rows:[{y:3,runs:[[3,5,1]]}]};
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

test('real prepared geography serves final E words, with N latitude/physical rules and complete M parents',async()=>{
 const f=await metadataRuntimeFixture(),{createServer}=await import('vite'),oldFetch=globalThis.fetch;
 const server=await createServer({configFile:false,server:{middlewareMode:true,watch:null},define:{'import.meta.env.VITE_STATIC_ATLAS':'"true"','import.meta.env.VITE_HOSTED_DATABASE':'"false"'}});
 try{
  let geometryReads=0;globalThis.fetch=async path=>{if(path==='./atlas-geography.json')return new Response(f.json(f.data));if(path==='./geography/geometries.json')geometryReads++;return f.fetcher(path);};
  const before=structuredClone(f.base),directFeatures=structuredClone(f.currentFeatures);
  const direct=await loadAdditiveNativePatch(f.data,directFeatures,f.base,{fetcher:f.fetcher});
  assert.notEqual(direct,f.base);assert.deepEqual(f.base,before);
  for(let y=3;y<=4;y++)for(let x=0;x<12;x++){const old=pickOwnership(before,x,y);if(old)assert.equal(pickOwnership(direct,x,y),old);}
  await prepareBrowserFixture({data:f.data,features:f.currentFeatures,transports:f.transports,fetcher:f.fetcher});
  const preparedFetch=globalThis.fetch;globalThis.fetch=async p=>{assert.ok(!p.startsWith('./additive-repairs/'),'Browser must not fetch or replay scientific repair products');return preparedFetch(p);};
  const client=await server.ssrLoadModule('/src/data-client.js'),loaded=await client.loadGeography();
  assert.deepEqual(nativeReferenceForData(loaded),f.native);assert.deepEqual(additiveBaseReference(loaded),f.reference);
  assert.equal(loaded.pixelMap.geographic_release,f.effective.id);assert.equal(loaded.pixelMap.hierarchy_sha256,f.reference.hierarchy_sha256);
  assert.equal(loaded.preparedOwnership.native_pixel_map.geographic_release,f.native.id);assert.equal(loaded.preparedOwnership.native_pixel_map.hierarchy_sha256,f.native.hierarchy_sha256);
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


test('finished bank copier rejects stale selection, N/M/E swaps, changed words, latitude and effective context before export',async t=>{
 const f=await metadataRuntimeFixture(),prepared=await prepareBrowserFixture({data:f.data,features:f.currentFeatures,transports:f.transports,fetcher:f.fetcher});
 const {default:fs}=await import('node:fs/promises'),{default:os}=await import('node:os'),{default:path}=await import('node:path');
 const {packagePreparedStartupOwnership}=await import('../scripts/package-startup-ownership.mjs');
 const root=await fs.mkdtemp(path.join(os.tmpdir(),'finished-bank-adverse-'));t.after(()=>fs.rm(root,{recursive:true,force:true}));
 const sha=raw=>createHash('sha256').update(raw).digest('hex');
 const repinContext=(state,edit)=>{const old=state.index.preparedOwnership.context_parts[0],rows=JSON.parse(gunzipSync(state.bodies.get(old.path)));edit(rows);
  const raw=Buffer.from(JSON.stringify(rows)),body=gzipSync(raw,{level:9}),pin={...old,path:`geography/effective-context-${sha(body)}.json.gz`,bytes:body.length,sha256:sha(body),decoded_bytes:raw.length,decoded_sha256:sha(raw)};
  state.bodies.delete(old.path);state.bodies.set(pin.path,body);state.index.files=state.index.files.filter(p=>p.path!==old.path);state.index.files.push({path:pin.path,bytes:pin.bytes,sha256:pin.sha256});state.index.preparedOwnership.context_parts[0]=pin;};
 const cases=[
  x=>x.selected.selectionBytes=Buffer.concat([x.selected.selectionBytes,Buffer.from(' ')]),
  x=>x.index.preparedOwnership.base_reference=x.index.preparedOwnership.effective_reference,
  x=>x.index.preparedOwnership.effective_reference=x.index.preparedOwnership.base_reference,
  x=>x.index.preparedOwnership.native_pixel_map.geographic_release=x.index.release_id,
  x=>x.index.pixelMap.canonical_grid_sha256=x.index.native_manifest_sha256,
  x=>x.index.pixelMap.parts.push(x.index.pixelMap.parts[0]),
  x=>x.index.pixelMap.native_latitudes.decoded_sha256='0'.repeat(64),
  x=>{const pin=x.index.pixelMap.parts.find(p=>p.kind==='runs'),raw=Buffer.from(x.bodies.get(pin.path));raw[raw.length-1]^=1;x.bodies.set(pin.path,raw);},
  x=>{const pin=x.index.preparedOwnership.native_pixel_map.native_latitudes,raw=Buffer.from(x.bodies.get(pin.transport_path));raw[raw.length-1]^=1;x.bodies.set(pin.transport_path,raw);},
  x=>repinContext(x,rows=>rows[1].properties.parent_id='foreign'),
  x=>repinContext(x,rows=>rows[0].geometry.coordinates[0][0][0]+=1),
  x=>repinContext(x,rows=>{const component=rows[0].additiveFootprint.components[0];component.geometry.coordinates[0][1][0]+=.125;component.geometry_sha256=hash(component.geometry);}),
 ];
 for(const [i,edit]of cases.entries()){
  const state={index:structuredClone(prepared.index),selected:{...prepared.selected,selectionBytes:Buffer.from(prepared.selected.selectionBytes)},bodies:new Map(prepared.bankBodies)};edit(state);
  const source=path.join(root,'source-'+i),destination=path.join(root,'output-'+i);await fs.mkdir(source);
  for(const [name,body]of state.bodies){await fs.mkdir(path.dirname(path.join(source,name)),{recursive:true});await fs.writeFile(path.join(source,name),body);}
  await fs.writeFile(path.join(source,'index.json'),JSON.stringify(state.index));
  const before=structuredClone(f.currentFeatures);
  await assert.rejects(packagePreparedStartupOwnership({manifest:prepared.manifest,manifestSha:prepared.selection.sha256,source,destination,selected:state.selected,features:f.currentFeatures}),/prepared|Prepared|Final|native|Native|effective|geometry|source|Source|Original/);
  assert.deepEqual(f.currentFeatures,before);await assert.rejects(fs.lstat(destination),{code:'ENOENT'});
 }
});

test('prepared browser provenance refuses an old-bank fallback and rebound ledger without fetching repair operands',async()=>{
 const f=await metadataRuntimeFixture();await prepareBrowserFixture({data:f.data,features:f.currentFeatures,transports:f.transports,fetcher:f.fetcher});
 const {loadPreparedNativeContext}=await import('../src/effective-footprint.js'),{loadOwnershipAssets}=await import('../src/ownership-assets.js');
 const ownership=await loadOwnershipAssets(f.data.pixelMap,f.fetcher,{requireNative:true,expectedReference:f.data.reference_release});
 for(const change of [d=>delete d.preparedOwnership,d=>d.preparedOwnership.additive_ledger_sha256='0'.repeat(64),d=>d.preparedOwnership.additive_patch_sha256='invalid']){
  const data=structuredClone(f.data),features=structuredClone(f.currentFeatures);change(data);const before=structuredClone(features);
  await assert.rejects(loadPreparedNativeContext(data,features,ownership,{fetcher:async p=>{assert.ok(!p.startsWith('./additive-repairs/'));return f.fetcher(p);}}),/prepared|Prepared/);
  assert.deepEqual(features,before);
 }
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
 await prepareBrowserFixture({data:f.data,features:generated,transports:f.transports,fetcher:f.fetcher});
 const server=await createServer({configFile:false,server:{middlewareMode:true,watch:null},define:{'import.meta.env.VITE_STATIC_ATLAS':'"true"','import.meta.env.VITE_HOSTED_DATABASE':'"false"'}});
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


test('emitted metadata reader authenticates only the explicitly bound database revision',async()=>{
 const f=await metadataRuntimeFixture(),revision='a'.repeat(64),features=structuredClone(f.currentFeatures);
 for(const feature of features)feature.properties.metadata.reference_revision=revision;
 f.data.referenceMetadata.application_reference_revision=revision;
 const effective=await loadAdditiveNativePatch(f.data,features,f.base,{fetcher:f.fetcher});
 assert.equal(pickOwnership(effective,3,3),1);
 for(const referenceRevision of [undefined,'b'.repeat(64),'invalid']){
  const data=structuredClone(f.data);if(referenceRevision===undefined)delete data.referenceMetadata.application_reference_revision;else data.referenceMetadata.application_reference_revision=referenceRevision;
  await assert.rejects(loadAdditiveNativePatch(data,structuredClone(features),f.base,{fetcher:f.fetcher}),/reference revision/);
 }
 for(const mutate of [p=>delete p.metadata.reference_corrections,p=>p.metadata.source_id='changed',p=>p.metadata.framework_match.id='changed',p=>p.name='changed',p=>p.parent_id='old']){
  const bad=structuredClone(features);mutate(bad[0].properties);
  await assert.rejects(loadAdditiveNativePatch(f.data,bad,f.base,{fetcher:f.fetcher}),/complete applied source/);
 }
});

// Exercise the shared streamed consumer at the actual rejected transport size,
// then keep the same native scope while testing its authenticated body boundary.
test('streamed additive consumer accepts exact 34920857-byte ledger and decoded roster',async()=>{
 const f=await metadataRuntimeFixture({ledgerBytes:34920857,rosterBytes:34920857});
 const baseRows=f.base.rows.slice(),baseRuns=f.base.runs.slice();
 assert.deepEqual(additiveBaseReference(f.data),f.reference);
 const output=await loadAdditiveNativePatch(f.data,structuredClone(f.currentFeatures),f.base,{fetcher:f.fetcher});
 assert.equal(pickOwnership(output,3,3),1);assert.deepEqual([...samplePackedOwnership(output,{x:3,y:3,width:1,height:1})],[1]);
 assert.deepEqual(f.base.rows,baseRows);assert.deepEqual(f.base.runs,baseRuns);
 const {createServer}=await import('vite'),oldFetch=globalThis.fetch;
 const scientificData=f.data;f.data=structuredClone(f.data);
 await prepareBrowserFixture({data:f.data,features:f.currentFeatures,transports:f.transports,fetcher:f.fetcher});
 const server=await createServer({configFile:false,server:{middlewareMode:true,watch:null},define:{'import.meta.env.VITE_STATIC_ATLAS':'"true"','import.meta.env.VITE_HOSTED_DATABASE':'"false"'}});
 try{
  globalThis.fetch=async name=>name==='./atlas-geography.json'?new Response(f.json(f.data)):f.fetcher(name);
  const client=await server.ssrLoadModule('/src/data-client.js'),loaded=await client.loadGeography();
  assert.equal(loaded.ownership.additive_added_cells,2);assert.equal(pickOwnership(loaded.ownership,3,3),1);
 }finally{globalThis.fetch=oldFetch;await server.close();}
 f.data=scientificData;
 const key='./'+f.data.additiveRelease.ledger.path,raw=f.transports.get(key);
 assert.equal(raw.length,34920857);
 for(const [body,error] of [[raw.subarray(0,-1),/Incomplete Native ledger/],[Buffer.concat([raw,Buffer.from(' ')]),/exceeds declared whole bytes/]]){
  await assert.rejects(loadAdditiveNativePatch(f.data,structuredClone(f.currentFeatures),f.base,{fetcher:async name=>name===key?new Response(body):f.fetcher(name)}),error);
 }
 const corrupted=Buffer.from(raw);corrupted[corrupted.length-1]=0x09;
 await assert.rejects(loadAdditiveNativePatch(f.data,structuredClone(f.currentFeatures),f.base,{fetcher:async name=>name===key?new Response(corrupted):f.fetcher(name)}),/whole checksum/);
 const broken=structuredClone(f.data);broken.additiveRelease.owner_roster.decoded_bytes--;
 await assert.rejects(loadAdditiveNativePatch(broken,structuredClone(f.currentFeatures),f.base,{fetcher:f.fetcher}),/exceeds declared whole decoded bytes/);
});

test('additive asset descriptors reject unsafe identities and precision limits before reads',async()=>{
 const f=await metadataRuntimeFixture();let reads=0;
 for(const role of ['patch','ledger','owner_roster','base_manifest']){
  const large=structuredClone(f.data);large.additiveRelease[role].bytes=34920857;
  assert.deepEqual(additiveBaseReference(large),f.reference);
  for(const [field,value] of [['bytes',0],['bytes',-1],['bytes',1.5],['bytes',NaN],['bytes',Infinity],['bytes',Number.MAX_SAFE_INTEGER+1],['path','../escape.json'],['path','https://example.invalid/asset.json'],['sha256','bad']]){
   const bad=structuredClone(f.data);bad.additiveRelease[role][field]=value;
   await assert.rejects(loadAdditiveNativePatch(bad,structuredClone(f.currentFeatures),f.base,{fetcher:async()=>{reads++;throw Error('must not fetch');}}),/Unsafe native additive asset/);
  }
 }
 for(const value of [0,-1,1.5,Infinity,Number.MAX_SAFE_INTEGER+1]){
  const bad=structuredClone(f.data);bad.additiveRelease.owner_roster.decoded_bytes=value;
  assert.throws(()=>additiveBaseReference(bad),/whole decoded native additive asset/);
 }
 assert.equal(reads,0);
 // Real runtime/resource errors remain failures, without fabricated success or
 // mutation. Inject that platform failure instead of allocating until OOM.
 const before=structuredClone(f.currentFeatures),failure=new RangeError('Array buffer allocation failed');
 await assert.rejects(loadAdditiveNativePatch(f.data,before,f.base,{fetcher:async()=>{throw failure;}}),error=>error===failure);
 assert.deepEqual(before,f.currentFeatures);
});

function encodeFixtureLedgerPatch(f){
 for(const role of ['ledger','patch']){
  const original=f.data.additiveRelease[role],key='./'+original.path,body=f.transports.get(key),encoded=gzipSync(body);
  const descriptor={...f.asset(original.path+'.gz',encoded),encoding:'gzip',decoded_bytes:body.length,decoded_sha256:createHash('sha256').update(body).digest('hex')};
  f.data.additiveRelease[role]=descriptor;f.transports.delete(key);f.transports.set('./'+descriptor.path,encoded);
 }
}

test('gzip ledger and patch preserve complete native words and science identities through the real geography entry',async()=>{
 const f=await metadataRuntimeFixture(),originalLedger=f.data.additiveRelease.ledger.sha256;
 const plain=await loadAdditiveNativePatch(f.data,structuredClone(f.currentFeatures),f.base,{fetcher:f.fetcher});
 const rows=f.base.rows.slice(),runs=f.base.runs.slice();encodeFixtureLedgerPatch(f);
 const features=structuredClone(f.currentFeatures),encoded=await loadAdditiveNativePatch(f.data,features,f.base,{fetcher:f.fetcher});
 assert.deepEqual(encoded.rows,plain.rows);assert.deepEqual(encoded.runs,plain.runs);assert.deepEqual(f.base.rows,rows);assert.deepEqual(f.base.runs,runs);
 assert.equal(encoded.additive_ledger_sha256,originalLedger);assert.equal(features[0].additiveFootprint.ledger_sha256,originalLedger);
 assert.equal(additiveReleaseFootprintDigest(f.reference,features),f.effective.footprints_sha256);
 const {createServer}=await import('vite'),oldFetch=globalThis.fetch;
 await prepareBrowserFixture({data:f.data,features:f.currentFeatures,transports:f.transports,fetcher:f.fetcher});
 const server=await createServer({configFile:false,server:{middlewareMode:true,watch:null},define:{'import.meta.env.VITE_STATIC_ATLAS':'"true"','import.meta.env.VITE_HOSTED_DATABASE':'"false"'}});
 try{
  globalThis.fetch=async name=>name==='./atlas-geography.json'?new Response(f.json(f.data)):f.fetcher(name);
  const client=await server.ssrLoadModule('/src/data-client.js'),loaded=await client.loadGeography();
  assert.deepEqual(loaded.ownership.rows,plain.rows);assert.deepEqual(loaded.ownership.runs,plain.runs);
  assert.equal(loaded.features[0].additiveFootprint.ledger_sha256,originalLedger);assert.equal(loaded.ownership.additive_added_cells,2);
 }finally{globalThis.fetch=oldFetch;await server.close();}
});

test('gzip ledger and patch reject malformed descriptors, encoded and decoded drift, and a rebound ledger',async()=>{
 const f=await metadataRuntimeFixture();encodeFixtureLedgerPatch(f);let reads=0;
 for(const role of ['ledger','patch']){
  for(const change of [x=>delete x.decoded_sha256,x=>delete x.encoding,x=>x.encoding='br',x=>x.decoded_bytes=0,x=>x.decoded_bytes=1.5,x=>x.decoded_sha256='bad']){
   const data=structuredClone(f.data);change(data.additiveRelease[role]);
   await assert.rejects(loadAdditiveNativePatch(data,structuredClone(f.currentFeatures),f.base,{fetcher:async()=>{reads++;throw Error('must not fetch');}}),/missing\/foreign|whole decoded/);
  }
  for(const [field,value,error] of [['bytes',f.data.additiveRelease[role].bytes-1,/exceeds declared whole bytes/],['bytes',f.data.additiveRelease[role].bytes+1,/Incomplete Native/],['sha256','0'.repeat(64),/whole checksum/],['decoded_bytes',f.data.additiveRelease[role].decoded_bytes-1,/exceeds declared whole decoded bytes/],['decoded_bytes',f.data.additiveRelease[role].decoded_bytes+1,/Incomplete decoded/],['decoded_sha256','0'.repeat(64),/whole decoded checksum/]]){
   const data=structuredClone(f.data);data.additiveRelease[role][field]=value;
   await assert.rejects(loadAdditiveNativePatch(data,structuredClone(f.currentFeatures),f.base,{fetcher:f.fetcher}),error);
  }
 }
 assert.equal(reads,0);
 const data=structuredClone(f.data),patch={...f.patch,ledger_sha256:data.additiveRelease.ledger.sha256},body=f.json(patch),raw=gzipSync(body),name=data.additiveRelease.patch.path;
 data.additiveRelease.patch={...f.asset(name,raw),encoding:'gzip',decoded_bytes:body.length,decoded_sha256:createHash('sha256').update(body).digest('hex')};
 await assert.rejects(loadAdditiveNativePatch(data,structuredClone(f.currentFeatures),f.base,{fetcher:async key=>key==='./'+name?new Response(raw):f.fetcher(key)}),/differs from selected whole ledger/);
});
