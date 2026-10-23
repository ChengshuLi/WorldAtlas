import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {DatabaseSync} from 'node:sqlite';
import {decodeDerived} from '../src/derived-records.js';
import {decodeReferences} from '../src/reference-records.js';
import {snapshot} from '../database.mjs';
import {temporalCatalog} from '../temporal.mjs';
import {readCurrentSelectedAdditive} from '../scripts/package-current-additive.mjs';
import {loadOwnershipAssets} from '../src/ownership-assets.js';
import {loadAdditiveNativePatch,loadPreparedNativeContext,nativeReferenceForData} from '../src/effective-footprint.js';
import {runtimeOwnershipBucket,runtimeOwnershipData} from '../src/runtime-ownership.js';

const root=path.resolve(import.meta.dirname,'..');
const read=file=>JSON.parse(file.endsWith('.gz')?gunzipSync(fs.readFileSync(file)):fs.readFileSync(file,'utf8'));
function canonical(value){
 if(Array.isArray(value))return value.map(canonical);
 if(value&&typeof value==='object')return Object.fromEntries(Object.keys(value).sort().filter(k=>value[k]!==undefined).map(k=>[k,canonical(value[k])]));
 return value;
}
function fingerprint(rows){
 const hash=createHash('sha256');
 for(const row of [...rows].sort((a,b)=>String(a.id??a.location_id).localeCompare(String(b.id??b.location_id))))hash.update(JSON.stringify(canonical(row))).update('\n');
 return hash.digest('hex');
}
function prepared(directory,kind){
 if(kind==='reference'&&!fs.existsSync(path.join(directory,'index.json'))){
  const atlas=read(path.join(directory,'..','atlas-geography.json')),descriptor=atlas.referenceAttributes;
  assert.equal(descriptor.version,1);
  const bytes=fs.readFileSync(path.join(directory,'..',descriptor.path));
  assert.equal(createHash('sha256').update(bytes).digest('hex'),descriptor.sha256);
  const raw=gunzipSync(bytes);
  assert.equal(createHash('sha256').update(raw).digest('hex'),descriptor.decoded_sha256);
  const bundle=JSON.parse(raw),original=prepared(path.join(root,'data/reference-attributes'),'reference');
  assert.equal(bundle.index_sha256,descriptor.index_sha256);
  assert.deepEqual(bundle.index,original.index);
  assert.deepEqual(bundle.parts,original.parts);
  return {index:bundle.index,parts:bundle.parts};
 }
 const index=read(path.join(directory,'index.json'));
 const parts=index.parts.map(p=>read(path.join(directory,typeof p==='string'?p:p.path)));
 if(kind==='owner'&&index.evidence_parts)index.evidence=index.evidence_parts.flatMap(p=>read(path.join(directory,p.path)));
 return {index,parts};
}

// Interpret the on-disk tables independently of the production codecs. Checking
// only two callers of the same codec could conceal a corrupted compact table.
function expectedReferences({index,parts},year){
 if(index.version===1)return parts.flat().filter(r=>r.valid_from<=year&&year<r.valid_to);
 return parts.flatMap(part=>part.flatMap(([location_id,values])=>values.flatMap(([type,value,share,coverage])=>{
  const t=index.types[type];
  return t.valid_from<=year&&year<t.valid_to?[{...t,id:`reference:${location_id}:${t.attribute}:${t.valid_from}`,location_id,value:index.values[value],metadata:{...t.metadata,share,coverage}}]:[];
 })));
}
function expectedOwners({index,parts},year){
 const records=[];
 for(const [location_id,intervals] of parts.flat()){
  const row=intervals.find(r=>r[0]<=year&&year<r[1]);if(!row)continue;
  const [valid_from,valid_to,owner,status,evidence]=row;
  let category_id=owner,metadata=evidence,resolvedStatus=status;
  if(index.version===2){
   category_id=owner==null?null:index.owner_ids[owner];resolvedStatus=index.statuses_order[status];
   index.parityMetadata ||= new Map();metadata=index.parityMetadata.get(evidence);
   if(!metadata){const [name,share,coverage,candidates,sources,dated]=index.evidence[evidence];metadata={owner_name:name==null?null:index.labels[name],share,coverage,candidates:candidates.map(([i,s])=>[index.owner_ids[i],s]),source_record_ids:sources.map(i=>index.source_ids[i]),footprint:dated?'dated':'reference'};index.parityMetadata.set(evidence,metadata);}
  }
  records.push({valid_from,valid_to,category_id,status:resolvedStatus,metadata,id:`ownership:${location_id}:${valid_from}`,location_id,attribute:'owner',value:category_id?(metadata.owner_name||index.entities[category_id].name):null,method:'majority-area',source:index.source,source_url:index.source_url});
 }
 return records;
}
function ownershipSnapshots(directory,years){
 const index=read(path.join(directory,'index.json')),selected=new Map(years.map(year=>[year,[]])),needed=new Set();
 for(const p of index.parts)for(const [id,intervals] of read(path.join(directory,p.path)))for(const year of years){
  let left=0,right=intervals.length;
  while(left<right){const mid=(left+right)>>>1;if(intervals[mid][0]<=year)left=mid+1;else right=mid;}
  const row=intervals[left-1];if(row&&row[1]>year){selected.get(year).push([id,[row]]);if(index.version===2)needed.add(row[4]);}
 }
 if(index.version===2){
  const evidence=new Map();let offset=0;
  for(const p of index.evidence_parts){const rows=read(path.join(directory,p.path));for(let i=0;i<rows.length;i++)if(needed.has(offset+i))evidence.set(offset+i,rows[i]);offset+=rows.length;}
  assert.equal(evidence.size,needed.size);index.evidence=new Proxy({}, {get:(_,key)=>evidence.get(Number(key))});
 }
 const output=new Map();
 for(const [year,rows] of selected)output.set(year,expectedOwners({index,parts:[rows]},year));
 return output;
}
function selectedStates(records,year,examples){
 const locations=new Map();
 for(const r of records)if(r.valid_from<=year&&r.valid_to>year&&(!r.is_example||examples)){
  const old=locations.get(r.location_id);if(!old||old.is_example>r.is_example)locations.set(r.location_id,r);
 }
 return [...locations.values()];
}

test('ownership codecs preserve identity, dated labels, competing evidence and the BC/AD edge',()=>{
 const source='Explicit majority fixture',source_url='https://example.org/fixture';
 const entities={'owner:fixed':{name:'Reference label'}};
 const metadata=(name,share,coverage,candidates,ids,footprint='reference')=>({owner_name:name,share,coverage,candidates,source_record_ids:ids,footprint});
 const rows=[[-1,1,null,'no-majority',metadata(null,.45,.45,[['owner:fixed',.45]],['partial'])],[1,1000,'owner:fixed','derived',metadata('Old label',.7,.7,[['owner:fixed',.7]],['early'])],[1000,1100,'owner:fixed','derived',metadata('New label',.8,.8,[['owner:fixed',.8]],['late'],'dated')],[1100,1200,null,'disputed',metadata(null,.8,1,[['owner:fixed',.8]],['claim-a','claim-b'])]];
 const v1={index:{version:1,source,source_url,entities},parts:[[['location:fixture',rows]]]};
 const v2={index:{version:2,source,source_url,entities,owner_ids:['owner:fixed'],labels:['Old label','New label'],source_ids:['partial','early','late','claim-a','claim-b'],statuses_order:['derived','disputed','no-majority','unknown'],evidence:[[null,.45,.45,[[0,.45]],[0],0],[0,.7,.7,[[0,.7]],[1],0],[1,.8,.8,[[0,.8]],[2],1],[null,.8,1,[[0,.8]],[3,4],0]]},parts:[[['location:fixture',[[-1,1,null,2,0],[1,1000,0,0,1],[1000,1100,0,0,2],[1100,1200,null,1,3]]]]]};
 for(const year of [-2,-1,1,999,1000,1099,1100,1199,1200]){
  const expected=expectedOwners(v1,year);
  assert.deepEqual(decodeDerived(v1.parts,v1.index,year),expected);
  assert.deepEqual(decodeDerived(v2.parts,v2.index,year),expected);
 }
 const old=decodeDerived(v2.parts,v2.index,999)[0],renamed=decodeDerived(v2.parts,v2.index,1000)[0];
 assert.equal(old.category_id,renamed.category_id);assert.equal(old.value,'Old label');assert.equal(renamed.value,'New label');
 assert.equal(renamed.metadata.footprint,'dated');assert.equal(decodeDerived(v2.parts,v2.index,1100)[0].value,null);
});

test('reference codecs preserve supported precision and do not bridge unsupported intervals',()=>{
 const type={attribute:'population',valid_from:1900,valid_to:1901,method:'estimate',status:'estimate',source:'Dated census fixture',metadata:{precision:'hundreds',source_year:1900}};
 const record={...type,id:'reference:l:population:1900',location_id:'l',value:1200,metadata:{...type.metadata,share:null,coverage:null}};
 const v1={version:1},v2={version:2,types:[type],values:[1200]};
 for(const year of [1899,1900,1901,2026]){
  const expected=year===1900?[record]:[];
  assert.deepEqual(decodeReferences([[record]],v1,year),expected);
  assert.deepEqual(decodeReferences([[['l',[[0,0,null,null]]]]],v2,year),expected);
 }
});

const ownerPath=path.join(root,'data/ownership-history/index.json');
const staticRoot=fs.existsSync(path.join(root,'dist/client/atlas-geography.json'))?path.join(root,'dist/client'):path.join(root,'dist');
const haveStatic=fs.existsSync(path.join(staticRoot,'atlas-geography.json'))&&fs.existsSync(path.join(staticRoot,'ownership-runtime/index.json'));
test('default-map static and server exports preserve complete state and attribute inputs, with examples on and off',{skip:!haveStatic&&!process.env.ATLAS_REQUIRE_STATIC?'full static export not built':false},()=>{
 assert.ok(haveStatic,'A complete static build is required for publication');
 const manifest=read(path.join(staticRoot,'atlas-geography.json'));
 const reference={...manifest,features:manifest.parts.flatMap(p=>read(path.join(staticRoot,p))),temporal:{...manifest.temporal,entities:manifest.entityParts.flatMap(p=>read(path.join(staticRoot,p))),history:manifest.temporalHistoryParts.flatMap(p=>read(path.join(staticRoot,p)))}};
 const history=read(path.join(staticRoot,'atlas-history.json.gz'));
 // Date boundaries and year changes are exercised by the focused runtime, codec and browser tests.
 const years=[1444],owners=ownershipSnapshots(path.join(root,'data/ownership-history'),years),references=prepared(path.join(staticRoot,'reference-attributes'),'reference');
 const runtime=read(path.join(staticRoot,'ownership-runtime/index.json')),buckets=new Map();
 assert.equal(runtime.source_index_sha256,createHash('sha256').update(fs.readFileSync(ownerPath)).digest('hex'),'Static ownership is derived from the current prepared source');
 const db=new DatabaseSync(path.join(root,'.cache/package-atlas.sqlite'),{readOnly:true});
 try{
  const serverFeatures=db.prepare('SELECT id,name,parent_id,reference_owner,metadata,active FROM locations WHERE active=1 ORDER BY id').all().map(({metadata,...properties})=>({id:properties.id,properties:{...properties,metadata:JSON.parse(metadata)}}));
  const serverUnits=db.prepare('WITH RECURSIVE used(id) AS (SELECT parent_id FROM locations WHERE active=1 UNION SELECT u.parent_id FROM units u JOIN used x ON u.id=x.id WHERE u.parent_id IS NOT NULL) SELECT * FROM units WHERE id IN (SELECT id FROM used)').all().map(u=>({...u,metadata:JSON.parse(u.metadata)}));
  const serverReference={features:serverFeatures,units:serverUnits,temporal:temporalCatalog(db)};
  assert.equal(fingerprint(reference.units),fingerprint(serverUnits),'Static geographic tiers and parent memberships match the database');
  assert.equal(reference.features.length,serverFeatures.length);
  assert.equal(fingerprint(reference.features.map(f=>({id:f.id,properties:f.properties}))),fingerprint(serverFeatures.map(f=>({id:f.id,properties:f.properties}))), 'Static location catalog matches the database');
  assert.equal(fingerprint(reference.temporal.entities),fingerprint(serverReference.temporal.entities),'Static identity catalog preserves archived entities');
  assert.equal(fingerprint(reference.temporal.history),fingerprint(serverReference.temporal.history),'Static dated identity records match the database');
  for(const year of years){
   const selected=runtimeOwnershipBucket(runtime,year);let staticOwners=[];
   if(selected){if(!buckets.has(selected.path)){buckets.set(selected.path,read(path.join(staticRoot,'ownership-runtime',selected.path)));while(buckets.size>2)buckets.delete(buckets.keys().next().value);}const data=runtimeOwnershipData(runtime,buckets.get(selected.path),year);staticOwners=decodeDerived(data.parts,data.index,year);}
   const staticOwnerFingerprint=fingerprint(staticOwners),preparedOwnerFingerprint=fingerprint(owners.get(year)),referenceRecords=expectedReferences(references,year);
   for(const examples of [false,true]){
    const server=snapshot(db,year,examples);
    assert.equal(staticOwnerFingerprint,preparedOwnerFingerprint,`Actual static temporal transport preserves prepared source values at ${year}`);
    const exported={states:selectedStates(history.states,year,examples),attributes:[...staticOwners,...referenceRecords,...(history.attributes||[]).filter(r=>r.valid_from<=year&&r.valid_to>year&&(!r.is_example||examples))]};
    assert.deepEqual(server.polities,[],'Normal Political mode has no independent source polygon layer');
    // Catalog inputs were compared above. Compare the remaining complete inputs
    // instead of running the same resolvers twice and hiding lower-priority drift.
    assert.equal(fingerprint(server.states),fingerprint(exported.states),`all snapshot states/provenance at ${year}/${examples}`);
    assert.equal(fingerprint(server.attributes),fingerprint(exported.attributes),`all snapshot attributes/provenance at ${year}/${examples}`);
   }
  }
 }finally{db.close();}
});

// These controls consume the actual package's current import closure. Keep them
// in the existing packaged-asset boundary so even a minimal reviewed roster
// derives its real inputs from the package definition and retains the build.
import os from 'node:os';
import {inspectPackageExecutionInputs} from '../scripts/package-build.mjs';
import {loadPackageInputs, containsPackagePath} from '../scripts/package-inputs.mjs';
const closureKinds=['static','hosted','cloudflare'];
let baselineClosures;
function actualBuilderClosures(){
 // Only this unchanged checkout shares results. Mutated fixture roots below
 // always pass through the real inspector again, without this cache.
 if(!baselineClosures){
  const root=fs.realpathSync(process.cwd()),definition=loadPackageInputs(root);
  const entries=new Map(closureKinds.map(kind=>[kind,inspectPackageExecutionInputs(root,definition,kind)]));
  baselineClosures={root,definition,entries};
 }
 return baselineClosures;
}
test('all actual builders declare their complete current closure without checkpoint-only methods',()=>{
 const {definition,entries}=actualBuilderClosures();
 const prefix='coordination/engineering/selected-geography-effective-prevention-20261009/';
 const excluded=['scripts/check-effective-geographic-regression.mjs','scripts/selected-checkpoint-native.mjs',
  'scripts/run-geographic-check.py',prefix+'selected-checkpoint.mjs',prefix+'selected-joint-entry.mjs',
  'test/fixtures/selected-checkpoint.mjs','scripts/visible-gap-eligibility.mjs',
  'scripts/native-ownership/validate-build-context-stage.mjs','scripts/package-output-artifact.mjs'];
 for(const [kind,actual]of entries){
  assert.deepEqual(actual.errors,[],'Actual '+kind+' preflight must include its complete current import closure');
  for(const name of [`scripts/build-${kind}-inner.mjs`,'scripts/package-build.mjs',
   'scripts/package-current-additive.mjs','src/native-grid.js'])assert(actual.files.includes(name),name);
  for(const name of excluded)assert(!actual.files.includes(name),kind+' now executes '+name);
  assert.deepEqual(actual.files,[...new Set(actual.files)].sort());
  for(const name of actual.files)assert(containsPackagePath(definition.inputs,name),name);
 }
});
test('actual current package import closure rejects an undeclared new helper before image creation',()=>{
 const {root,definition,entries}=actualBuilderClosures();
 // Preserve the public omitted-kind/default-cloudflare route independently.
 const actual=inspectPackageExecutionInputs(root,definition);
 assert.deepEqual(actual,entries.get('cloudflare'));
 assert.equal(actual.errors.length,0,JSON.stringify(actual.errors));
 assert(actual.files.includes('scripts/package-build.mjs'));
 const missing=inspectPackageExecutionInputs(root,{...definition,inputs:definition.inputs.filter(x=>x!=='scripts/package-inputs.mjs')});
 assert(missing.errors.some(x=>x.kind==='execution-declaration'&&x.path==='scripts/package-inputs.mjs'));
});
test('an undeclared import in the actual current consumer fails current-input preflight',t=>{
 const {root:source,definition,entries}=actualBuilderClosures(),actual=entries.get('static');
 assert.deepEqual(actual.errors,[]);
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-joint-package-boundary-'));
 t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 for(const name of actual.files){const target=path.join(root,name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.copyFileSync(path.join(source,name),target,fs.constants.COPYFILE_EXCL);}
 const undeclared='coordination/undeclared-acceptance-probe.mjs';
 fs.mkdirSync(path.dirname(path.join(root,undeclared)),{recursive:true});
 fs.writeFileSync(path.join(root,undeclared),'export const current = true;\n',{flag:'wx'});
 fs.appendFileSync(path.join(root,'scripts/package-current-additive.mjs'),"\nawait import('../"+undeclared+"');\n");
 const rejected=inspectPackageExecutionInputs(root,definition,'static');
 assert(rejected.files.includes(undeclared));
 assert(rejected.errors.some(e=>e.kind==='execution-declaration'&&e.path===undeclared));
});
test('shared selected-input admission covers actual builders and refuses undeclared imports',t=>{
 const {root,definition,entries}=actualBuilderClosures(),files=new Set();
 for(const actual of entries.values()){
  assert.deepEqual(actual.errors,[]);
  for(const name of actual.files)files.add(name);
 }
 const fixture=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'atlas-output-role-closure-')));
 t.after(()=>fs.rmSync(fixture,{recursive:true,force:true}));
 for(const name of files){const dest=path.join(fixture,name);fs.mkdirSync(path.dirname(dest),{recursive:true});
  fs.copyFileSync(path.join(root,name),dest,fs.constants.COPYFILE_EXCL);}
 fs.writeFileSync(path.join(fixture,'undeclared-fixture.mjs'),'export const fixture=true;\n');
 fs.appendFileSync(path.join(fixture,'scripts/package-current-additive.mjs'),"\nimport '../undeclared-fixture.mjs';\n");
 for(const kind of closureKinds){
  const rejected=inspectPackageExecutionInputs(fixture,definition,kind);
  assert(rejected.files.includes('undeclared-fixture.mjs'));
  assert(rejected.errors.some(error=>error.kind==='execution-declaration'&&error.path==='undeclared-fixture.mjs'),
   'The real '+kind+' entry must refuse undeclared imports');
 }
});

// Independently decode the served final words and compare the complete arrays
// with the unchanged scientific N+patch consumer. This is publication parity,
// not browser startup or a second source qualification.
test('finished static native bank preserves every accepted word, owner and effective feature context',{skip:!haveStatic&&!process.env.ATLAS_REQUIRE_STATIC?'full static export not built':false},async()=>{
 assert.ok(haveStatic,'A complete static build is required for publication');
 const data=read(path.join(staticRoot,'atlas-geography.json'));
 const selection=read(path.join(root,'data/ownership-selection.json'));
 if(selection.version===2){const {checkEmittedSelectedDelivery}=await import('../scripts/selected-delivery-smoke.mjs');
  const report=await checkEmittedSelectedDelivery({root,emittedDirectory:staticRoot});assert.equal(report.kind,'actual-emitted-final-bank-consumer');assert(report.complete_run_words>0);return;}
 const native=read(path.join(root,selection.manifest_path));
 const selected=await readCurrentSelectedAdditive({root,selectedGrid:{manifest:native,sha256:selection.sha256},
   geographicRelease:data.preparedOwnership?.base_reference??data.reference_release,referenceRevision:data.referenceMetadata?.application_reference_revision});
 if(!selected){assert.equal(data.preparedOwnership,undefined);return;}
 assert.deepEqual(data.additiveRelease,selected.envelope);
 assert.equal(data.preparedOwnership.selection_sha256,createHash('sha256').update(selected.selectionBytes).digest('hex'));
 const features=data.parts.flatMap(p=>read(path.join(staticRoot,p))),expectedFeatures=structuredClone(features),actualFeatures=structuredClone(features);
 const original={...data,pixelMap:data.preparedOwnership.native_pixel_map};delete original.preparedOwnership;
 const pins=new Map(Object.entries(selected.sidecar.logical_asset_map).map(([role,pin])=>[selected.envelope[role].path,pin]));
 async function fetcher(input){
  const name=String(input).replace(/^\.\//,'');
  const raw=pins.has(name)?await selected.read(pins.get(name)):fs.readFileSync(path.join(staticRoot,name));
  return new Response(raw);
 }
 const base=await loadOwnershipAssets(original.pixelMap,fetcher,{requireNative:true,expectedReference:nativeReferenceForData(original)});
 const expected=await loadAdditiveNativePatch(original,expectedFeatures,base,{fetcher});
 const final=await loadOwnershipAssets(data.pixelMap,fetcher,{requireNative:true,expectedReference:data.reference_release});
 const actual=await loadPreparedNativeContext(data,actualFeatures,final,{fetcher});
 assert.deepEqual(actual.rows,expected.rows,'Every final row word equals the accepted scientific composition');
 assert.deepEqual(actual.runs,expected.runs,'Every final run word, including held/unchanged owners, is preserved');
 for(const key of ['size','coordinateBits','method','geographic_release','hierarchy_sha256','footprints_sha256','reference_owner_sha256',
  'effective_footprint_sha256','effective_footprint_domain','additive_base_reference','additive_patch_sha256','additive_ledger_sha256',
  'additive_added_cells','reference_owner_source_sha256','additive_authority_registry_sha256','additive_rule_sha256'])assert.deepEqual(actual[key],expected[key],key);
 assert.deepEqual(actualFeatures,expectedFeatures,'Complete parent, camera, base geometry and effective-footprint context is preserved');
 for(const [key,words] of [['rows_sha256',actual.rows],['runs_word_stream_sha256',actual.runs]])assert.equal(
  createHash('sha256').update(Buffer.from(words.buffer,words.byteOffset,words.byteLength)).digest('hex'),data.preparedOwnership[key]);
});
