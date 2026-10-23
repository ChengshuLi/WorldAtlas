import {omitFixtureObjects} from './helpers/git-object-fixture.mjs';
import {checkpointTestAPI} from './helpers/native-literal.mjs';
import {nativeLiteral} from './helpers/native-literal.mjs';
import {oldBank,writeFinal} from './fixtures/final-bank.mjs';
import {finishEffectiveFootprint} from '../src/native-grid.js';
import test, {after} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import childProcess, {execFileSync} from 'node:child_process';
import {gzipSync,gunzipSync,crc32,deflateRawSync} from 'node:zlib';
import {trustedFixture as trustedNativeFixture} from './helpers/selected-joint-fixture.mjs';
import {trustedFixture as appendedFixture,appendNativeAuthority} from './fixtures/selected-checkpoint.mjs';
import {ACCEPTED_CHECKPOINT_CODE} from '../scripts/accepted-selected-checkpoint.mjs';
import {renderWorkerResult} from '../scripts/worker-result.mjs';
import crypto, {createHash} from 'node:crypto';
import {syncBuiltinESMExports} from 'node:module';
import {shuffleOwnershipBytes} from '../src/ownership-codec.js';
import {valueBytes,valueSha,coordinateBounds,normaliseRetainedRepairLedger,mergeCompletedNativePatches} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
import {deriveCoordinateDelta,projectSourceFeatures,projectNativeRows,qualifyTransition} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint.mjs';
const MODULE='coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint.mjs';
const PROGRAMME='coordination/engineering/selected-geography-effective-prevention-20261009/supported-programs.json';
const CATALOGUE='coordination/engineering/selected-checkpoint-reuse-20261012/accepted-checkpoints.json';
const CODE=[MODULE,'coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs','scripts/native-word-store.mjs','scripts/native-patch-store.mjs','scripts/check-effective-geographic-regression.mjs',
  'scripts/selected-reference-metadata.mjs','src/reference-metadata.js','src/native-grid.js','src/ownership-codec.js','scripts/package-startup-ownership.mjs','src/ownership-assets.js','src/ownership-method.js'];
const sha=b=>createHash('sha256').update(b).digest('hex');
const polygon=(x,y=0)=>({type:'Polygon',coordinates:[[[x,y],[x+.2,y],[x+.2,y+.2],[x,y+.2],[x,y]]]});
const feature=(id,x)=>({type:'Feature',id,properties:{id,parent_id:'parent'},geometry:polygon(x)});
function fixtures(sourcePaths){
 const features=sourcePaths?sourcePaths.map((_,i)=>feature(String.fromCharCode(65+i),i*2)):[feature('A',0),feature('B',1),feature('C',5)];
 const rows=features.map((f,i)=>[f.id,i+1,'parent',1,sourcePaths?.[i]??'data/source.json',sourcePaths?0:i,valueSha(f),valueSha(f.geometry),valueSha({base_geometry_sha256:valueSha(f.geometry),additions:[]}),coordinateBounds(f.geometry)]);
 return {features,certificate:{version:2,kind:'selected-coordinate-neighbor-certificate-v2',entry_fields:['id','index','parent_id','parent_index','source','ordinal','whole_feature_sha256','geometry_sha256','effective_geometry_sha256','boxes'],binding:{selection:{old:true},sources:[],owners_sha256:valueSha(rows.map(r=>r.slice(0,4)))},entries:rows,inputs:[]}};
}
function addition(id,target,index,base,x){const geometry=polygon(x);return {component_id:id,target_id:target,pixelIndex:index,base_geometry_sha256:base,geometry,geometry_sha256:valueSha(geometry)};}

// Each case owns its physical repository, mutable operands and private modules.
function fixtureRepository(root){
 const git=(...a)=>execFileSync('git',['-c','core.hooksPath=/dev/null','-c','user.name=Checkpoint fixture','-c','user.email=checkpoint@example.invalid','-C',root,...a],{env:{...process.env,GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:'/dev/null',GIT_NO_LAZY_FETCH:'1'},stdio:['ignore','pipe','pipe']});
 const save=(name,value)=>{const f=path.join(root,name);fs.mkdirSync(path.dirname(f),{recursive:true});fs.writeFileSync(f,Buffer.isBuffer(value)?value:valueBytes(value));};
 const commit=()=>{git('add','.');git('commit','-qm','Checkpoint fixture');return git('rev-parse','HEAD').toString().trim();};
 const pin=(name,at=git('rev-parse','HEAD').toString().trim())=>{const body=git('show',at+':'+name),tree=git('ls-tree',at,'--',name).toString().split(/\s+/);return {commit:at,path:name,mode:tree[0],git_blob_oid:tree[2],bytes:body.length,sha256:sha(body)};};
 return {root,git,save,commit,pin};
}

// Only the default miniature history is reused, as ordinary bytes. No seed
// module is imported, and no reader, qualification result or capability is kept.
let trustedDefaultSeed;
after(()=>{if(trustedDefaultSeed)fs.rmSync(trustedDefaultSeed.root,{recursive:true,force:true});});
function buildTrustedFixture(root,{incompleteNative,sourcePaths,sourceOverride,physicalLogicalSource,inheritedCode,wireProducts}){
 const {git,save,commit,pin}=fixtureRepository(root);
 git('init','-q');save(PROGRAMME,fs.readFileSync(PROGRAMME));for(const name of CODE)save(name,fs.readFileSync(name));save('package.json',{type:'module'});
 const inheritedName='fixture/historical-execution.json';
 if(inheritedCode)save(inheritedName,{original:'executed configuration'});
 const {features,certificate}=fixtures(sourcePaths), paths=sourcePaths??['data/source.json'];
 for(const name of paths){
  const source={type:'FeatureCollection',features:features.filter((_,i)=>certificate.entries[i][4]===name)};
  save(name,source);if(sourceOverride)save(name+'.gz',gzipSync(valueBytes(source)));
 }
 const reference={id:'geography:fixture',hierarchy_sha256:'a'.repeat(64),footprints_sha256:'b'.repeat(64)};
 const encode=(name,kind,values)=>{const words=Uint32Array.from(values),canonical=Buffer.from(words.buffer),encoded=gzipSync(shuffleOwnershipBytes(words));save('data/'+name,encoded);return {path:name,kind,offset:0,bytes:encoded.length,sha256:sha(encoded),decoded_bytes:canonical.length,decoded_sha256:sha(canonical),words:words.length,encoding:'byte-shuffle'};};
 const parts=[encode('native/rows.bin.gz','rows',[0,1,incompleteNative?2:1,1,2,1,3,0]),encode('native/runs.bin.gz','runs',[4,0,8,0,13,1])];
 const compressedParts=parts.map(p=>fs.readFileSync(path.join(root,'data',p.path))),whole=Buffer.concat(compressedParts),fragment=gzipSync(whole);
 save('data/transport/fragment.gz',fragment);
 const index={version:1,kind:'ordered-exact-original-byte-fragments',whole_bytes:whole.length,whole_sha256:sha(whole),files:parts.map((p,i)=>({path:p.path,mode:'100644',offset:i?parts[0].bytes:0,bytes:p.bytes,sha256:p.sha256})),parts:[{path:'fragment.gz',offset:0,bytes:fragment.length,sha256:sha(fragment),decoded_bytes:whole.length,decoded_sha256:sha(whole)}]};save('data/transport/index.json',index);
 const manifest={version:1,size:4,coordinateBits:2,method:'native-linear-evenodd-first-owner-v1',native_latitudes:[],hierarchy_sha256:reference.hierarchy_sha256,original_assets:{},parts,runWords:6,native_asset_transport:{version:1,kind:index.kind,index:{path:'data/transport/index.json',bytes:valueBytes(index).length,sha256:valueSha(index)},logical_assets:2,original_compressed_bytes:whole.length}};
 save('data/manifest.json',manifest);save('data/owners.json',features.map((f,i)=>({id:f.id,index:i+1})));
 const primitive=addition('old','A',1,certificate.entries[0][7],.3);
 const literal={...primitive,base_geometry:features[0].geometry,disposition:'assigned',native_cells:1,source_receipt_sha256:'c'.repeat(64)};
 const originalPatch={version:1,kind:'unassigned-native-cells-v1',rows:[{y:1,runs:[[2,3,1]]}]};
 save('original/patch-one.json',originalPatch);save('original/rule.json',{version:1});const one=commit();
 const inherited=inheritedCode?pin(inheritedName,one):null;
 if(inherited){
  const {bytes,sha256}=inherited,role={path:inherited.path,bytes,sha256};
  const policy=JSON.parse(fs.readFileSync(path.join(root,PROGRAMME)));
  policy.programs.push({preimage_version:3,source_profile:'fixture-inherited-role',accepted_head:one,
   independent_review_comment:1,source_executed_code:[role],native_executed_code:[role]});save(PROGRAMME,policy);
 }
 save('original/publication.json',{assets:[{path:'patch-one.json',bytes:pin('original/patch-one.json').bytes,sha256:pin('original/patch-one.json').sha256}]});
 const two=commit();save('original/binding.json',{native_proof:{publication:pin('original/publication.json'),assets:[pin('original/patch-one.json',one)]}});const three=commit();
 const entry={policy_id:'retained-source-literal-additions',policy_version:1,rule_preimage:pin('original/rule.json',one),rule_sha256:pin('original/rule.json',one).sha256,source_authority:pin('original/binding.json',three)};entry.authority_sha256=valueSha(entry);
 const registry={version:1,kind:'retained-rule-authority-registry-v1',entries:[entry]};save('data/registry.json',registry);
 const baseSelection={version:1,method:manifest.method,manifest_path:'data/manifest.json',sha256:pin('data/manifest.json',one).sha256,release_id:reference.id,selected_geography:{version:1,kind:'complete-world-index-with-exact-encoded-overrides',path:'data/bank.json',bytes:1,sha256:'d'.repeat(64)}};
 const target={target_id:'A',pixelIndex:1,geometry:features[0].geometry,geometry_sha256:valueSha(features[0].geometry)};
 const currentRows=[{y:1,runs:[[0,1,2]]}];
 const request={...(inherited?{execution_commit:inheritedCode==='wrong-commit'?'a'.repeat(40):one,executed_code:inheritedCode==='no-role'?[]:[{path:inherited.path,bytes:inherited.bytes,sha256:inheritedCode==='wrong-hash'?'f'.repeat(64):inherited.sha256}]}:{}),base_selection:baseSelection,authority_registry_sha256:valueSha(registry),current_targets:[target],current_rows:currentRows,original_patch_sha256s:[valueSha(originalPatch)],acquisition:{predecessor_rows:[],predecessor_proof:null,native_inputs:[]}};
 const rebind={request,result:{native:{rows:originalPatch.rows}},facts:{acquisition_phases:[]},publication:{},operating:{}};
 for(const [name,body]of Object.entries(rebind))save('accepted-rebind/'+name+'.json',body);const four=commit();
 const rc={version:1,kind:'qualified-native-additive-current-bank-rebind-v1',execution_commit:one,base_selection:baseSelection,authority_registry_sha256:valueSha(registry),...Object.fromEntries(Object.keys(rebind).map(name=>[name,pin('accepted-rebind/'+name+'.json',four)]))};save('accepted-rebind/certificate.json',rc);const five=commit();
 const ledger={version:2,kind:'native-additive-repair-ledger-v2',authority_registry_sha256:valueSha(registry),scope_ids:['old','rejected'],rows:[{...literal,authority_sha256:entry.authority_sha256},{component_id:'rejected',disposition:'rejected',reason:'complete original exception',authority_sha256:entry.authority_sha256}],parent_inventory:{components:2,roster_sha256:'e'.repeat(64)},current_rebind:pin('accepted-rebind/certificate.json',five),current_targets:[target]};save('data/ledger.json',wireProducts?Buffer.from('{ "rows":[{"ignored":1e400}], '+JSON.stringify(ledger).slice(1).replace('[0,0]','[-0e0,0.00]')+' \n'):ledger);const six=commit();
 const normalized=[{...literal,authority_sha256:entry.authority_sha256,rule_sha256:entry.rule_sha256}];
 const effective={...reference,footprints_sha256:valueSha({domain:'worldatlas-effective-native-footprints:v2',base_reference:reference,authority_registry_sha256:valueSha(registry),ledger_sha256:pin('data/ledger.json',six).sha256,components:normalized})};
 const patch={version:2,kind:'unassigned-native-cells-v1',authority_registry_sha256:valueSha(registry),ledger_sha256:pin('data/ledger.json',six).sha256,base_reference:reference,effective_reference:effective,rows:originalPatch.rows};save('data/patch.json',wireProducts?Buffer.from('{ "rows":false, '+JSON.stringify(patch,null,2).slice(1)+' \n'):patch);const seven=commit();
 const assets={base_manifest:pin('data/manifest.json',one),owner_roster:pin('data/owners.json',one),ledger:pin('data/ledger.json',six),patch:pin('data/patch.json',seven)};
 const envelope={version:2,kind:'retained-native-base-plus-delta-v2',base_reference:reference,effective_reference:effective,...assets};save('data/envelope.json',envelope);const eight=commit();
 const sidecar={version:2,kind:'retained-native-additive-selection-v2',base_selection:baseSelection,authority_registry:pin('data/registry.json',four),logical_asset_map:assets,runtime_envelope:pin('data/envelope.json',eight)};save('data/sidecar.json',sidecar);const nine=commit();
 const selection={...baseSelection,additive_release:{path:'data/sidecar.json',bytes:pin('data/sidecar.json',nine).bytes,sha256:pin('data/sidecar.json',nine).sha256}};save('data/ownership-selection.json',selection);const selected=commit();
 const sourcePins=paths.map(name=>sourceOverride?{...pin(name+'.gz',one),kind:'selected-exact-encoded-override',
  logical_path:name,encoding:'gzip',decoded_bytes:pin(name,one).bytes,decoded_sha256:pin(name,one).sha256}
  :{...pin(name,one),kind:'ordinary-immutable-git-source'});
 const additions=normalized.map(row=>({...row,base_geometry:target.geometry,base_geometry_sha256:target.geometry_sha256}));
 const derived=deriveCoordinateDelta({certificate,oldAdditions:[],additions,selection}).certificate;
 const full={...derived,binding:{...derived.binding,release:reference,sources:sourcePins},inputs:sourcePins.map((source,i)=>({path:paths[i],source,whole_body_sha256:source.decoded_sha256??source.sha256,bytes:source.decoded_bytes??source.bytes}))};
 const execution_code=CODE.map(name=>pin(name,one)),runtime=[{path:process.execPath,bytes:fs.statSync(process.execPath).size,sha256:'f'.repeat(64)}];
 const facts={version:1,kind:'trusted-selected-coordinate-stage-v1',candidate_code_executed:false,selected_commit:selected,executing_commit:one,execution_code,runtime,binding:full.binding,complete_owners:features.length,complete_sources:paths.length};
 const compressed=gzipSync(valueBytes(full));save('accepted/certificate.json.gz',compressed);save('accepted/facts.json',facts);
 const publication={version:1,kind:facts.kind,complete:true,facts:{path:'facts.json',bytes:valueBytes(facts).length,sha256:valueSha(facts)},certificate:{path:'certificate.json.gz',bytes:compressed.length,sha256:sha(compressed),decoded_bytes:valueBytes(full).length,decoded_sha256:valueSha(full)}};save('accepted/publication.json',publication);
 const inventory=[PROGRAMME,...(inherited?[inherited.path]:[]),...sourcePins.map(p=>p.path),...(sourceOverride&&physicalLogicalSource?paths:[]),'data/manifest.json','data/owners.json','data/registry.json','data/ledger.json','data/patch.json','data/sidecar.json','data/envelope.json','data/native/rows.bin.gz','data/native/runs.bin.gz'].map(name=>pin(name,selected));
 save('accepted/custody.json',{complete_cold_custody:[{facts,publication,effective_additions:additions,inventory}]});
 save('accepted/routes.json',[...new Set([...inventory.map(p=>p.path),...paths])].sort().map(name=>({path:name,tree:git('ls-tree','-z',selected,'--',name).toString()})));const accepted=commit();
 const rootRow={id:'fixture',accepted_head:accepted,selected_commit:selected,selection_sha256:valueSha(selection),execution_commit:one,execution_code_sha256:valueSha(execution_code),runtime_sha256:valueSha(runtime),facts:pin('accepted/facts.json'),certificate:{...pin('accepted/certificate.json.gz'),decoded_bytes:valueBytes(full).length,decoded_sha256:valueSha(full)},publication:pin('accepted/publication.json'),custody:pin('accepted/custody.json'),routes:pin('accepted/routes.json')};
 save(CATALOGUE,{version:1,kind:'accepted-selected-checkpoints-v1',checkpoints:[rootRow]});commit();
 return {selected,ledger,patch,sidecar,envelope,selection,rootRow,inherited};
}

// Real admission reads each copy's committed catalogue. Nondefault fixtures are
// constructed afresh; current modules, readers and admission always stay fresh.
async function trustedFixture(t,{incompleteNative=false,sourcePaths,sourceOverride=false,physicalLogicalSource=false,inheritedCode=false,wireProducts=false}={}){
 const options={incompleteNative,sourcePaths,sourceOverride,physicalLogicalSource,inheritedCode,wireProducts};
 const useDefault=incompleteNative===false&&sourcePaths===undefined&&sourceOverride===false
  &&physicalLogicalSource===false&&inheritedCode===false&&wireProducts===false;
 if(useDefault&&!trustedDefaultSeed){
  const root=fs.mkdtempSync(path.join(process.cwd(),'.checkpoint-seed-'));
  try{trustedDefaultSeed={root,data:buildTrustedFixture(root,options)};}
  catch(error){fs.rmSync(root,{recursive:true,force:true});throw error;}
 }
 const root=fs.mkdtempSync(path.join(process.cwd(),'.checkpoint-test-'));
 t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 let data;
 if(useDefault){fs.cpSync(trustedDefaultSeed.root,root,{recursive:true});data=structuredClone(trustedDefaultSeed.data);}
 else data=buildTrustedFixture(root,options);
 const api=checkpointTestAPI(t,await import(pathToFileURL(path.join(root,MODULE)))),native=await import(pathToFileURL(path.join(root,'scripts/check-effective-geographic-regression.mjs')));
 const reader=new native.ImmutableReader(root,data.selected);
 return {...data,...fixtureRepository(root),api,native,reader};
}

async function countFixtureHistory(action){
 const original=childProcess.execFileSync,counts={init:0,add:0,commit:0};
 childProcess.execFileSync=function(command,args,...rest){
  if(command==='git')for(const name of Object.keys(counts))if(args.includes(name))counts[name]++;
  return original.call(this,command,args,...rest);
 };syncBuiltinESMExports();
 try{return {value:await action(),counts};}finally{childProcess.execFileSync=original;syncBuiltinESMExports();}
}

test('default accepted fixture copies history but isolates bytes, private state and cleanup',async t=>{
 const first=await trustedFixture(t);
 const {value:second,counts}=await countFixtureHistory(()=>trustedFixture(t));
 assert.deepEqual(counts,{init:0,add:0,commit:0},'A second default must copy history rather than rebuild it');
 assert.notEqual(first.root,second.root);assert.equal(first.selected,second.selected);
 assert.notEqual(first.native.ImmutableReader,second.native.ImmutableReader);
 assert.notEqual(first.api.qualifyTransition,second.api.qualifyTransition);
 const originalLedger=structuredClone(second.ledger),originalHead=second.git('rev-parse','HEAD').toString();
 for(const f of [first,second]){
  assert(fs.lstatSync(path.join(f.root,'.git')).isDirectory());
  assert.equal(f.git('remote').toString(),'');
  assert.equal(fs.existsSync(path.join(f.root,'.git/objects/info/alternates')),false);
  assert.equal(fs.existsSync(path.join(f.root,'node_modules')),false);
  assert.equal(fs.existsSync(path.join(f.root,'.cache')),false);
  assert.equal(Number(f.git('rev-list','--count','HEAD')),12);
 }
 const original=first.pin('data/source.json',first.selected),relative=path.join('.git/objects',original.git_blob_oid.slice(0,2),original.git_blob_oid.slice(2));
 const files=root=>fs.readdirSync(path.join(root,'.git/objects'),{recursive:true,withFileTypes:true}).filter(e=>e.isFile()).map(e=>path.relative(root,path.join(e.parentPath,e.name))).sort();
 const physical=files(first.root);assert.deepEqual(physical,files(second.root));assert(physical.length>0);
 for(const name of physical){const a=fs.statSync(path.join(first.root,name)),b=fs.statSync(path.join(second.root,name));assert(a.dev!==b.dev||a.ino!==b.ino,'Copied Git objects must not be hard-linked');}
 const admitted=await first.api.qualifyCheckpoint({reader:first.reader});assert.equal(admitted.available,true);
 assert.throws(()=>second.api.releaseCheckpoint(admitted.state),/foreign/);
 first.api.releaseCheckpoint(admitted.state);
 first.ledger.rows[0].target_id='mutated returned row';
 first.save('data/source.json',{changed:'committed mutation'});first.commit();
 omitFixtureObjects(t,first.root,[original.git_blob_oid]);fs.mkdirSync(path.dirname(path.join(first.root,relative)),{recursive:true});fs.writeFileSync(path.join(first.root,relative),'corrupted only in first copy');
 assert.deepEqual(second.ledger,originalLedger);assert.equal(second.git('rev-parse','HEAD').toString(),originalHead);
 assert.equal(second.pin('data/source.json',second.selected).sha256,original.sha256);
 fs.rmSync(first.root,{recursive:true,force:true});
 const next=await second.api.qualifyCheckpoint({reader:second.reader});assert.equal(next.available,true);
 assert.deepEqual(second.api.projectSourceFeatures({state:next.state,ids:['A']}).features.map(f=>f.id),['A']);
 second.api.releaseCheckpoint(next.state);
});

test('parameterized accepted fixtures still construct fresh histories and preserve literal wire inputs',async t=>{
 const {value:fixtures,counts}=await countFixtureHistory(async()=>[
  await trustedFixture(t,{wireProducts:true}),await trustedFixture(t,{wireProducts:true})]);
 assert.deepEqual(counts,{init:2,add:24,commit:24});assert.notEqual(fixtures[0].root,fixtures[1].root);
 for(const f of fixtures){
  const wire=f.git('show',f.selected+':data/ledger.json').toString();
  assert(wire.startsWith('{ "rows":[{"ignored":1e400}], '));
  const decoded=JSON.parse(wire);assert.equal(valueSha(decoded),valueSha(f.ledger));
  assert(wire.includes('[-0e0,0.00]'));
  const result=await f.api.qualifyCheckpoint({reader:f.reader});assert.equal(result.available,true);
  f.api.releaseCheckpoint(result.state);
 }
});

function zipMembers(members, {descriptor = false, method = 8} = {}) {
  const locals = [], centrals = []; let offset = 0;
  for (const [name, body] of members) {
    const filename = Buffer.from(name), packed = method === 8 ? deflateRawSync(body) : body;
    const crc = crc32(body), local = Buffer.alloc(30), central = Buffer.alloc(46);
    local.writeUInt32LE(0x04034b50); local.writeUInt16LE(20, 4); local.writeUInt16LE(descriptor ? 8 : 0, 6);
    local.writeUInt16LE(method, 8); local.writeUInt16LE(filename.length, 26);
    if (!descriptor) { local.writeUInt32LE(crc, 14); local.writeUInt32LE(packed.length, 18); local.writeUInt32LE(body.length, 22); }
    const data = descriptor ? Buffer.alloc(16) : Buffer.alloc(0);
    if (descriptor) { data.writeUInt32LE(0x08074b50); data.writeUInt32LE(crc, 4); data.writeUInt32LE(packed.length, 8); data.writeUInt32LE(body.length, 12); }
    central.writeUInt32LE(0x02014b50); central.writeUInt16LE(0x0314, 4); central.writeUInt16LE(20, 6);
    central.writeUInt16LE(descriptor ? 8 : 0, 8); central.writeUInt16LE(method, 10);
    central.writeUInt32LE(crc, 16); central.writeUInt32LE(packed.length, 20); central.writeUInt32LE(body.length, 24);
    central.writeUInt16LE(filename.length, 28); central.writeUInt32LE(offset, 42);
    locals.push(local, filename, packed, data); centrals.push(central, filename);
    offset += local.length + filename.length + packed.length + data.length;
  }
  const central = Buffer.concat(centrals), end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50); end.writeUInt16LE(members.length, 8); end.writeUInt16LE(members.length, 10);
  end.writeUInt32LE(central.length, 12); end.writeUInt32LE(offset, 16);
  return Buffer.concat([...locals, central, end]);
}

// Consumed result fields extracted verbatim from retained clean004 at 45390281e441a56736c43fa5f4962832e5db18c7.
// Source: coordination/engineering/selected-zero-load-joint-20261012/retained-proof-004/
// joint-result.json SHA256 5c1d76bd09e2819d5f2f76e2f830b0f770856cac78e3f1b07a53f589e4ed5682;
// operating.json SHA256 25c5642327c49cddfa55e522c9acf4585691da2d78265c4cde45da8e622b8bf3.
// Only fixture-specific selected identities, empty row/owner scopes and status
// are rebound below. Large unused gained-coverage geometry is not copied.
const REAL004={
  "native": {
    "affected_rows": 18,
    "candidate_code_executed": false,
    "intervals": [],
    "lost_or_reassigned_cells": 0,
    "method": "selected-native-owner-conservation-v1",
    "native_row_scope": {
      "changed_rows": [
        138227,
        138418,
        138419,
        138420,
        138421,
        138424,
        138425,
        139996,
        139997,
        139998,
        140068,
        140069,
        143396,
        143397,
        148366,
        153495,
        153496,
        153497
      ],
      "proof": "shared-qualified-complete-base-and-cumulative-patch",
      "shared_base_acquired_rows": [],
      "shared_base_reused_rows": [
        138227,
        138418,
        138419,
        138420,
        138421,
        138424,
        138425,
        139996,
        139997,
        139998,
        140068,
        140069,
        143396,
        143397,
        148366,
        153495,
        153496,
        153497
      ]
    },
    "status": "no-new-native-loss",
    "version": 1
  },
  "operating": {
    "cleanup_group_scan": {
      "command": [
        "ps",
        "-eo",
        "pid=,ppid=,pgid=,rss=,args="
      ],
      "members": [],
      "observed_monotonic_seconds": 24.328938291997474
    },
    "complete": true,
    "errors": [],
    "failure": null,
    "returncode": 0,
    "terminal_group_scan": {
      "command": [
        "ps",
        "-eo",
        "pid=,ppid=,pgid=,rss=,args="
      ],
      "members": [],
      "observed_monotonic_seconds": 24.32478002899734
    }
  },
  "strict": {
    "changed_location_ids": [
      "gb:AUS:ADM2:25037944B11916296746250",
      "gb:AUS:ADM2:25037944B17338277063313",
      "gb:AUS:ADM2:25037944B43303794043608",
      "gb:AUS:ADM2:25037944B47305351718046",
      "gb:AUS:ADM2:25037944B73531494726593",
      "gb:AUS:ADM2:25037944B91391383703186",
      "gb:AUS:ADM2:25037944B95382354250521"
    ],
    "changed_primitive_ids": [
      "[\"gb:AUS:ADM2:25037944B11916296746250\",\"physical-component:ee9d9768fca9795b3d5be1b865c72fe5e9cd2fba30b7b670a4efced1d23c8c74\"]",
      "[\"gb:AUS:ADM2:25037944B17338277063313\",\"physical-component:9d53e507a92cc13f65caf2dc51679708b3fee6e5b87a670c5d5179e40019dbbe\"]",
      "[\"gb:AUS:ADM2:25037944B43303794043608\",\"physical-component:0f132f659a1cd02c13cddb383b2d39a40134e249c0771a9b3dfc42b488755f35\"]",
      "[\"gb:AUS:ADM2:25037944B43303794043608\",\"physical-component:19f523ffe4951aaa8802fe1731f7befd6f48acda3d3d313fcaa31281e304374e\"]",
      "[\"gb:AUS:ADM2:25037944B43303794043608\",\"physical-component:ae546e54d7ddf21a006459eeec529ac90f1b030b9797bed032d21f5885126a7d\"]",
      "[\"gb:AUS:ADM2:25037944B47305351718046\",\"physical-component:693f67a95c8dc115e9a678b873cf00272dca011feb1e980233100e32dd4e5d60\"]",
      "[\"gb:AUS:ADM2:25037944B47305351718046\",\"physical-component:a02d1bc4b12eaeb786305a63ee523a14fb785ff72e1263d0ce3399b42d38568d\"]",
      "[\"gb:AUS:ADM2:25037944B47305351718046\",\"physical-component:c24dc1abe05ff8e61e1a6246bf0d7dd15b1201152989b26e80c6854b30abbae2\"]",
      "[\"gb:AUS:ADM2:25037944B47305351718046\",\"physical-component:ea41656ef57f6a294406dba881c7d63e70460c1c060147692992137380cf7c8b\"]",
      "[\"gb:AUS:ADM2:25037944B73531494726593\",\"physical-component:64efd5aee39eeef3fd2373469acb69007b90bf8532265298ea247da595a05d99\"]",
      "[\"gb:AUS:ADM2:25037944B91391383703186\",\"physical-component:6aeef9d450464698868d758f9032b7bf4d17b17813e931e380a08cbff1a95a3c\"]",
      "[\"gb:AUS:ADM2:25037944B91391383703186\",\"physical-component:6e05d606a5ac09942295520893df259382c0634574213b6caea9c782076dae94\"]",
      "[\"gb:AUS:ADM2:25037944B95382354250521\",\"physical-component:dc85692f522c0fedaaacd434b39520bb84001ba0355441458cbc3b82e6c38a0a\"]"
    ],
    "effective_set_domain": "literal-base-or-complete-additions:v2",
    "findings": {
      "features": [],
      "type": "FeatureCollection"
    },
    "geometry_domain": "worldatlas-prepared-antimeridian-cut-v1",
    "geometry_errors": [],
    "regressions": 0,
    "status": "no-new-regression"
  }
};
const JSON_BODY=valueBytes;
const P='coordination/engineering/selected-geography-effective-prevention-20261009/';
const {JOINT_CODE:JOINT}=await import('../coordination/engineering/selected-geography-effective-prevention-20261009/selected-joint-entry.mjs');
const MEMBERS=['derived-certificate.json.gz','derived-facts.json','derived-publication.json','checkpoint-routes.json'];
async function acceptedProducts(t,{sourcePaths,actualProducer=false,nativeOnly=false,nativeAppend=false,sourceOverride=false,physicalLogicalSource=false,inheritedCode=false,wireProducts=false,completedNative=false,finalBank=false}={}) {
  const f=nativeAppend||completedNative||finalBank?await appendedFixture(t,{nativeAppend:true,finalBank}):nativeOnly?await trustedNativeFixture(t,{nativeOnly:true}):await trustedFixture(t,{sourcePaths,sourceOverride,physicalLogicalSource,inheritedCode,wireProducts});
  let prepared;
  if(finalBank){const admitted=await f.api.qualifyCheckpoint({reader:f.reader});assert.equal(admitted.available,true);
    prepared=await oldBank(f,admitted.state);f.api.releaseCheckpoint(admitted.state);}
  for(const name of [...JOINT,...(actualProducer?['scripts/check-geographic-regression.py','scripts/evidence/immutable.py','scripts/evidence/geometry.py','scripts/ellipsoidal_area.py','requirements.txt','.github/evidence-policy.json']:[])])f.save(name,fs.readFileSync(name));
  f.save(CATALOGUE,{version:1,kind:'accepted-selected-checkpoints-v1',checkpoints:[f.rootRow]});
  if(f.inherited)f.save(f.inherited.path,{reviewed:'successor configuration'});
  const trusted=f.commit();
  const reader=new f.native.ImmutableReader(f.root,trusted);
  const {state}=(await f.api.qualifyCheckpoint({reader}));
  const afterReader=new f.native.ImmutableReader(f.root,trusted,{invocation:reader.invocation});
  const transition=(await f.api.qualifyTransition({state,reader:afterReader}));
  const census=f.api.checkpointRouteCensus({transition});
  const certificate=transition.candidate.certificate;
  const inventory=r=>[...r.inventory.values()].sort((a,b)=>(a.commit+':'+a.path).localeCompare(b.commit+':'+b.path));
  const runtime=[0,1,2].map(i=>({path:'/fixture/runtime-'+i,mode:493,bytes:100+i,sha256:String(i+1).repeat(64),version:null}));
  const native={...structuredClone(REAL004.native),baseline_selection:state.selection,candidate_selection:state.selection,
    affected_rows:0,native_row_scope:{...REAL004.native.native_row_scope,changed_rows:[],shared_base_acquired_rows:[],shared_base_reused_rows:[]}};
  const facts={version:1,kind:'derived-selected-checkpoint-candidate-v1',validation_stage:'native-passed',
    accepted_checkpoint:false,executing_commit:trusted,execution_code:JOINT.map(name=>f.pin(name,trusted)),runtime,
    baseline_accepted_execution:state.accepted_execution,executing_authority_pins:[PROGRAMME,CATALOGUE]
      .map(name=>({...f.pin(name,trusted),whole_body_consumed:true})),
    actual_reader_inventories:{baseline:inventory(reader),candidate:inventory(afterReader)},
    baseline_commit:trusted,candidate_commit:trusted,baseline_selection:state.selection,candidate_selection:state.selection,
    candidate_bindings:{ledger_sha256:valueSha(nativeLiteral(state.ledger)),registry_sha256:valueSha(state.registry),
      patch_sha256:valueSha(nativeLiteral(state.patch)),manifest_sha256:valueSha(state.manifest)},
    native_result_sha256:valueSha(native),candidate_code_executed:false,executing_policy:f.api.checkpointExecutingPolicy({transition})};
  const products=structuredClone({facts,certificate,census,native});
  f.api.releaseCheckpoint(state);
  const transport=await import(pathToFileURL(path.join(f.root,'scripts/accepted-selected-checkpoint.mjs')));
  if(actualProducer){
    let candidate=trusted;
    if(finalBank){const final=await writeFinal(f,prepared.index,prepared.features.map(p=>finishEffectiveFootprint(p,valueSha)),prepared.ownership);candidate=final.commit;}

    if(completedNative){
      Object.assign(f,await appendNativeAuthority(f,{name:'completed',completedConstructor:true}));
      Object.assign(f,await appendNativeAuthority(f,{name:'unfinished',owner:1,mutatePatch:patch=>{
        patch.rows=mergeCompletedNativePatches(patch.rows.map(row=>({rows:[row]})),f.manifest.size);
      }}));
      candidate=f.candidate;
    }
    const destination=path.join(f.root,'actual-native-products');fs.mkdirSync(destination);
    const driver="import importlib.util,json,pathlib,sys\nrepo=pathlib.Path(sys.argv[1]);s=importlib.util.spec_from_file_location('native_parent',repo/'scripts/run-geographic-check.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\nprint(json.dumps(m.selected_joint(repo,sys.argv[2],sys.argv[4],trusted=sys.argv[2],checkpoint_destination=pathlib.Path(sys.argv[3]))))";
    if(candidate!==trusted)f.git('checkout','--detach',trusted);
    const issued=JSON.parse(execFileSync(process.env.PYTHON??'python3',['-I','-B','-c',driver,f.root,trusted,destination,candidate],{env:{...process.env,NODE:process.execPath},encoding:'utf8'}));
    if(candidate!==trusted)f.git('checkout','--detach',candidate);
    const produced=new Map(MEMBERS.map(name=>[name,fs.readFileSync(path.join(destination,name))]));
    assert.deepEqual(issued.checkpoint.members.map(p=>p.name).sort(),[...MEMBERS].sort());
    return {...f,trusted:candidate,acceptedBaseline:trusted,transport,produced,products:{native:issued.native,
      facts:JSON.parse(produced.get('derived-facts.json')),certificate:JSON.parse(gunzipSync(produced.get('derived-certificate.json.gz'))),
      census:JSON.parse(produced.get('checkpoint-routes.json'))}};
  }
  return {...f,trusted,transport,products};
}
function pack(f,mutate=()=>{}) {
  const p=structuredClone(f.products);mutate(p);
  const bodies=new Map(f.produced);
  const put=(name,value)=>{const decoded=valueBytes(value),encoded=name.endsWith('.gz')?gzipSync(decoded):decoded;
    bodies.set(name,encoded);return {path:name,bytes:encoded.length,sha256:sha(encoded),
      ...(name.endsWith('.gz')?{decoded_bytes:decoded.length,decoded_sha256:sha(decoded)}:{})};};
  if(!f.produced){
  const certificate=put('derived-certificate.json.gz',p.certificate),routes=put('checkpoint-routes.json',p.census);
  const {runtime,caller_runtime,execution_runtimes,execution_code_inventory,...nativeInverse}=p.native;
  Object.assign(p.facts,{certificate,checkpoint_routes:routes,native_result_sha256:valueSha(nativeInverse)});
  const df=put('derived-facts.json',p.facts);
  put('derived-publication.json',{version:1,kind:p.facts.kind,complete:true,accepted_checkpoint:false,
    validation_stage:p.facts.validation_stage,certificate,facts:df,routes});
  }
  const report={version:1,method_id:'worldatlas-trusted-geography-check-v1',baseline_commit:f.acceptedBaseline??f.trusted,
    candidate_commit:f.trusted,trusted_code_commit:f.acceptedBaseline??f.trusted,candidate_code_executed:false,published:false,
    source_approval:false,gate_status:'passed',status:'no-new-native-loss',validation_scope:'selected-native-map-cells',regressions:0,selected_native_report:p.native,
    checkpoint:{version:1,kind:'selected-checkpoint-products-v1',members:MEMBERS.map(name=>{
      const raw=bodies.get(name),decoded=name.endsWith('.gz')?valueBytes(p.certificate):null;
      return {name,bytes:raw.length,sha256:sha(raw),...(decoded?{decoded_bytes:decoded.length,decoded_sha256:sha(decoded)}:{})};})}};
  const raw=valueBytes(report);return {report,raw,zip:zipMembers([['geography-check.json',raw],...MEMBERS.map(name=>[name,bodies.get(name)])])};
}
async function acquire(f,mutate,{merged=f.trusted,tree=f.git('rev-parse',f.trusted+'^{tree}').toString().trim()}={}) {
  const p=pack(f,mutate), request='01234567-abcd-4321-aaaa-123456789012',head=f.trusted,baseline=f.acceptedBaseline??f.trusted,
    candidate=f.trusted,workflowHead=baseline;
  const source={run_id:12,run_attempt:2,job_id:34,tree,head,baseline,candidate_commit:candidate,
    workflow_path:'.github/workflows/worker-merge.yml',event:'workflow_dispatch',workflow_head:workflowHead,
    artifact_id:56,artifact_name:`geography-${request}-2`,artifact_digest:sha(p.zip),artifact_bytes:p.zip.length,
    report_sha256:sha(p.raw),report_bytes:p.raw.length};
  const receipt={accepted:true,status:'merged',request_id:request,pr_number:7,merge_commit:merged,reviewed_head:head,
    tested_base:baseline,tested_candidate:candidate,geography:{status:'passed',trusted_code_commit:baseline,candidate_commit:candidate,
      report_sha256:source.report_sha256,source}};
  const run={id:12,run_attempt:2,head_sha:workflowHead,event:'workflow_dispatch',path:source.workflow_path,
    repository:{full_name:'owner/repo'},head_repository:{full_name:'owner/repo'},status:'completed'};
  const job={id:34,name:'geography',run_id:12,run_attempt:2,head_sha:workflowHead,status:'completed',conclusion:'success',steps:[
    'Checkout trusted geographic checker','Install trusted geographic dependencies','Check exact combined geography with trusted baseline code',
    'Run actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02'].map(name=>({name,status:'completed',conclusion:'success'}))};
  const api=async route=>{
    if(route==='/repos/owner/repo/issues')return [];
    if(route.endsWith('/comments?per_page=100&page=1'))return [{id:11,user:{login:'github-actions[bot]'},body:renderWorkerResult('merge',receipt)}];
    if(route.endsWith('/pulls/7'))return {number:7,merged:true,head:{sha:head,repo:{full_name:'owner/repo'}},base:{ref:'main',repo:{full_name:'owner/repo'}},merge_commit_sha:merged};
    if(route.endsWith('/attempts/2'))return run;
    if(route.endsWith('/attempts/2/jobs?per_page=100&page=1'))return {jobs:[job]};
    if(route.includes('/git/commits/'))return {sha:route.split('/').at(-1),tree:{sha:tree}};
    if(route.endsWith('/artifacts?per_page=100&page=1'))return {total_count:1,artifacts:[{id:56,name:source.artifact_name,expired:false,
      size_in_bytes:p.zip.length,digest:'sha256:'+sha(p.zip),workflow_run:{id:12,head_sha:workflowHead}}]};
    throw Error('Unexpected fixture route '+route);
  };
  api.artifactRedirect=async()=>new Response(null,{status:302,headers:{location:'https://fixtures.blob.core.windows.net/zip'}});
  const result=await f.transport.acquireAcceptedCheckpoint({api,repo:'owner/repo',locator:{pr_number:7,request_id:request,head},
    token:'fixture',fetchImpl:async()=>new Response(p.zip)});
  assert.equal(result.available,true);
  const reader=new f.native.ImmutableReader(f.root,f.trusted);
  return {handle:result.handle,reader,fixture:{api,archive:p.zip,locator:{version:1,kind:'accepted-selected-checkpoint-locator-v1',acceptance:{pr_number:7,request_id:request,head}}}};
}
async function qualify(f,a) {return f.api.qualifyAcceptedCheckpoint({reader:a.reader,acceptedHandle:a.handle});}

test('accepted derived inventory recovers inherited executed roles from the original rebind commit',async t=>{
 const f=await acceptedProducts(t,{inheritedCode:true});
 assert(!Object.values(f.products.facts.actual_reader_inventories).flat().some(p=>p.path===f.inherited.path));
 const a=await acquire(f),result=await qualify(f,a);assert.equal(result.available,true,result.reason);
 const pin=a.reader.inventory.get(f.inherited.commit+':'+f.inherited.path);
 assert.deepEqual(pin,{...f.inherited,whole_body_consumed:true});
 assert.notEqual(pin.git_blob_oid,f.pin(f.inherited.path,f.trusted).git_blob_oid);
 assert(!f.products.facts.execution_code.some(p=>p.path===f.inherited.path));
 const candidate=new f.native.ImmutableReader(f.root,f.trusted,{invocation:a.reader.invocation});
 const transition=(await f.api.qualifyTransition({state:result.state,reader:candidate}));assert.equal(transition.available,true);
 assert.equal(f.api.checkpointRouteCensus({transition}).routes.find(p=>p.path===f.inherited.path).tree,
  f.git('ls-tree','-z',f.inherited.commit,'--',f.inherited.path).toString());
 fs.appendFileSync(path.join(f.root,'src/native-grid.js'),'\n// Uncommitted actual execution drift.\n');
 await assert.rejects(()=>qualify(f,a),/changed executing checkpoint method/);
 f.api.releaseCheckpoint(result.state);f.transport.releaseAcceptedCheckpoint(a.handle);
});

test('inherited role recovery refuses a different original route and unknown code role',async t=>{
 const f=await acceptedProducts(t,{inheritedCode:true});
 const a=await acquire(f,p=>{p.census.routes.find(p=>p.path===f.inherited.path).tree=
  f.git('ls-tree','-z',f.trusted,'--',f.inherited.path).toString();});
 await assert.rejects(()=>qualify(f,a),/inherited code route differs/);f.transport.releaseAcceptedCheckpoint(a.handle);
 const b=await acquire(f,p=>{
  const policy=JSON.parse(p.facts.executing_policy.body);policy.programs=policy.programs.filter(p=>p.source_profile!=='fixture-inherited-role');
  const body=valueBytes(policy);p.facts.executing_policy.body=body.toString();
  const changed={...p.facts.executing_policy.pin,bytes:body.length,sha256:sha(body)};
  p.facts.executing_policy.pin=changed;p.facts.executing_authority_pins[0]=changed;
  const i=p.facts.actual_reader_inventories.baseline.findIndex(p=>p.commit===changed.commit&&p.path===changed.path);
  p.facts.actual_reader_inventories.baseline[i]=changed;
 });
 const refused=await qualify(f,b);assert.equal(refused.available,false);assert.match(refused.reason,/routing alternative changed/);
 f.transport.releaseAcceptedCheckpoint(b.handle);
});

for(const inheritedCode of ['wrong-commit','no-role','wrong-hash'])test(`inherited recovery refuses ${inheritedCode} original rebind custody`,async t=>{
 const f=await acceptedProducts(t,{inheritedCode}),a=await acquire(f);
 if(inheritedCode==='wrong-commit')await assert.rejects(()=>qualify(f,a),/rebind execution identity differs/);
 else {const result=await qualify(f,a);assert.equal(result.available,false);assert.match(result.reason,/routing alternative changed/);}
 f.transport.releaseAcceptedCheckpoint(a.handle);
});

test('inherited recovery still authenticates the original whole body and ordinary mode',async t=>{
 const f=await acceptedProducts(t,{inheritedCode:true});
 const a=await acquire(f),readGit=a.reader.git.bind(a.reader);
 a.reader.git=(...args)=>{const raw=readGit(...args);if(args[0]==='cat-file'&&args[1]==='blob'&&args[2]===f.inherited.git_blob_oid){const bad=Buffer.from(raw);bad[0]^=1;return bad;}return raw;};
 await assert.rejects(()=>qualify(f,a),/Whole immutable input differs/);f.transport.releaseAcceptedCheckpoint(a.handle);
 const b=await acquire(f),descriptor=b.reader.descriptor.bind(b.reader);
 b.reader.descriptor=(name,version)=>{const pin=descriptor(name,version);return name===f.inherited.path&&version===f.inherited.commit?{...pin,mode:'100755'}:pin;};
 await assert.rejects(()=>qualify(f,b),/inherited code route differs/);f.transport.releaseAcceptedCheckpoint(b.handle);
});

test('a present non-code consumed role cannot inherit a historical code exemption',async t=>{
 const f=await acceptedProducts(t,{inheritedCode:true});
 const a=await acquire(f,p=>p.facts.actual_reader_inventories.candidate.push({...f.pin(f.inherited.path,f.trusted),whole_body_consumed:true}));
 const result=await qualify(f,a);assert.equal(result.available,false);assert.match(result.reason,/routing alternative changed/);
 f.transport.releaseAcceptedCheckpoint(a.handle);
});

test('accepted original archive admits a private successor without a catalogue row for that selector',async t=>{
  const f=await acceptedProducts(t),a=await acquire(f);
  // Remove all static roots. Only current method authentication remains.
  f.save(CATALOGUE,{version:1,kind:'accepted-selected-checkpoints-v1',checkpoints:[]});f.commit();
  const result=await qualify(f,a);assert.equal(result.available,true);
  assert.equal(result.state.accepted_execution.kind,'accepted-selected-checkpoint-artifact-v1');
  assert.equal(result.state.ledger.rows.length,2);assert.equal(result.state.ledger.rows.at(1).disposition,'rejected');
  assert.deepEqual(nativeLiteral(f.api.projectNativeRows({state:result.state,rows:[1]}).rows),[{y:1,runs:[[0,1,2]]}]);
  assert.equal(f.api.projectSourceFeatures({state:result.state,ids:['A']}).features[0].id,'A');
  const candidateReader=new f.native.ImmutableReader(f.root,f.trusted,{invocation:a.reader.invocation});
  const transition=(await f.api.qualifyTransition({state:result.state,reader:candidateReader}));assert.equal(transition.available,true);
  assert.deepEqual(f.api.checkpointRouteCensus({transition}).routes,f.products.census.routes);
  f.api.releaseCheckpoint(result.state);f.transport.releaseAcceptedCheckpoint(a.handle);
});
test('actual joint producer and Python retention feed archive transport and next checkpoint admission',async t=>{
  const f=await acceptedProducts(t,{actualProducer:true}),a=await acquire(f);
  const result=await qualify(f,a);assert.equal(result.available,true);
  assert.equal(result.state.selected_commit,f.trusted);
  assert.deepEqual(result.state.certificate,f.products.certificate);
  // Independently check the producer's invariant on this bounded real fixture.
  // Production accepted reuse must not recompute this complete cross product.
  for (const [i,row] of f.products.certificate.entries.entries()) {
    assert.equal(row[1],i+1);
    const effective=nativeLiteral(result.state.additions).filter(p=>p.target_id===row[0]);
    assert(effective.every(p=>p.pixelIndex===row[1] && p.base_geometry_sha256===row[7]));
    assert.equal(row[8],valueSha({base_geometry_sha256:row[7],additions:effective}));
  }

  assert.equal(f.products.facts.validation_stage,'native-passed');
  assert.equal(f.products.facts.continuous_publication,undefined);
  assert.equal(f.products.native.repair_visibility.new_components,0);
  f.api.releaseCheckpoint(result.state);f.transport.releaseAcceptedCheckpoint(a.handle);
});
test('forged and released acceptance handles cannot mint private selected state',async t=>{
  const f=await acceptedProducts(t),a=await acquire(f);
  await assert.rejects(f.api.qualifyAcceptedCheckpoint({reader:a.reader,acceptedHandle:{}}),/private accepted/);
  f.transport.releaseAcceptedCheckpoint(a.handle);
  await assert.rejects(qualify(f,a),/private accepted/);
});
test('accepted native losses or missing native execution cannot mint a successor',async t=>{
  const f=await acceptedProducts(t);
  for(const mutate of [p=>p.native.lost_or_reassigned_cells=1,p=>p.native.intervals.push({bad:true}),
    p=>p.native.method='unknown',p=>p.native.candidate_code_executed=true]){
    await assert.rejects(async()=>{const a=await acquire(f,mutate);try{await qualify(f,a);}finally{f.transport.releaseAcceptedCheckpoint(a.handle);}},/successful.*native result|findings remain unresolved/);
  }
});
test('coherently rehashed omitted routes, stale selectors, old exception drift and unknown schema refuse',async t=>{
  const f=await acceptedProducts(t);
  for(const [mutate,reason] of [
    [p=>p.census.routes.pop(),/route census/],
    ...['ledger_sha256','registry_sha256','patch_sha256','manifest_sha256'].flatMap(key=>[
      [p=>p.facts.candidate_bindings[key]='0'.repeat(64),/complete ledger/],
      [p=>delete p.facts.candidate_bindings[key],/complete ledger/]]),
    [p=>p.facts.executing_policy.body+=' ',/policy identity differs/],
    [p=>p.facts.executing_policy.body=p.facts.executing_policy.body.replace('1','2'),/policy body differs/],
    [p=>p.facts.execution_code=p.facts.execution_code.filter(x=>x.path!=='scripts/selected-checkpoint-native.mjs'),/original native execution/],
    ...[p=>p.certificate.version=3,p=>p.certificate.kind='unknown',
      p=>p.certificate.entry_fields=[],p=>p.certificate.entries=null,
      p=>p.certificate.inputs=null,p=>p.certificate.binding.sources=null]
      .map(mutate=>[mutate,/coordinate product schema/])]) {
    const a=await acquire(f,mutate);
    try {const result=await qualify(f,a);assert.equal(result.available,false);assert.match(result.reason,reason);}
    catch(error){assert.match(error.message,reason);}
    f.transport.releaseAcceptedCheckpoint(a.handle);
  }
  const a=await acquire(f,p=>p.facts.candidate_selection.release_id='geography:stale');
  const result=await qualify(f,a);assert.equal(result.available,false);assert.match(result.reason,/complete selector/);
});
test('accepted admission authenticates committed helper edits without repinning historical science',async t=>{
  const f=await acceptedProducts(t),catalogue=fs.readFileSync(path.join(f.root,CATALOGUE));
  fs.appendFileSync(path.join(f.root,'scripts/evidence-policy.mjs'),'\n// reviewed policy maintenance\n');f.commit();
  const a=await acquire(f),result=await qualify(f,a);
  assert.equal(result.available,true);
  assert.deepEqual(fs.readFileSync(path.join(f.root,CATALOGUE)),catalogue);
  f.transport.releaseAcceptedCheckpoint(a.handle);
});
for(const method of ['scripts/evidence-policy.mjs','scripts/native-patch-store.mjs','scripts/native-word-store.mjs','src/native-grid.js'])
test('actual executing code remains necessary at accepted admission: '+method,async t=>{
  const f=await acceptedProducts(t);
  fs.appendFileSync(path.join(f.root,method),'\n// uncommitted executable drift\n');
  const b=await acquire(f);await assert.rejects(qualify(f,b),/changed executing checkpoint method/);
  f.transport.releaseAcceptedCheckpoint(b.handle);
});
test('census retains complete unchanged/absent routes and rejects public transition wrappers',async t=>{
  const f=await acceptedProducts(t),a=await acquire(f),{state}=await qualify(f,a);
  const transition=(await f.api.qualifyTransition({state,reader:a.reader}));
  assert.throws(()=>f.api.checkpointRouteCensus({transition:{...transition}}),/private qualified selected transition/);
  const census=f.api.checkpointRouteCensus({transition});
  assert(census.routes.some(p=>p.path==='data/native/runs.bin.gz'));assert(census.routes.some(p=>p.path==='data/source.json'));
  assert(Object.isFrozen(census.routes));f.api.releaseCheckpoint(state);
  assert.throws(()=>f.api.checkpointRouteCensus({transition}),/private qualified selected transition/);
});

test('wrapper-only native identities preserve the original native report hash',async t=>{
  const f=await acceptedProducts(t);
  const p=structuredClone(f.products);
  Object.assign(p.native,{runtime:p.facts.runtime[0],caller_runtime:p.facts.runtime[1],
    execution_runtimes:p.facts.runtime,execution_code_inventory:p.facts.execution_code});
  // pack() deliberately hashes the original numerical report, as the real joint
  // producer does before attaching its separately bound wrapper identities.
  f.products=p;const a=await acquire(f);
  assert.equal((await qualify(f,a)).available,true);
  const b=await acquire(f,p=>{p.native.execution_code_inventory=[];});
  await assert.rejects(qualify(f,b),/wrapper execution/);
});

async function installSeed(f,{failedOperating=false,omitRoute=false,omitInherited=false}={}) {
  f={...f,products:structuredClone(f.products)};
  const plain=new Map();
  // The real seed keeps clean004's original provisional schema: no backfilled
  // route-publication field and no claim to be an accepted hosted artifact.
  const copy=structuredClone(f.products);
  const decoded=pack(f);
  const {readReportArchive,geographicReportProducts}=await import('../scripts/geographic-report-artifact.mjs');
  const report=readReportArchive(decoded.zip,sha(decoded.raw),decoded.raw.length);
  for(const [name,bytes] of geographicReportProducts(report).members)plain.set(name,bytes);
  const facts=JSON.parse(plain.get('derived-facts.json'));delete facts.checkpoint_routes;delete facts.executing_policy;
  plain.set('derived-facts.json',valueBytes(facts));
  const publication=JSON.parse(plain.get('derived-publication.json'));delete publication.routes;
  publication.facts={path:'derived-facts.json',bytes:plain.get('derived-facts.json').length,sha256:sha(plain.get('derived-facts.json'))};
  plain.set('derived-publication.json',valueBytes(publication));
  if(omitRoute){const routes=JSON.parse(plain.get('checkpoint-routes.json'));routes.routes.pop();plain.set('checkpoint-routes.json',valueBytes(routes));}
  if(omitInherited){const routes=JSON.parse(plain.get('checkpoint-routes.json'));
    routes.predecessor_paths=routes.predecessor_paths.filter(p=>p!==PROGRAMME);
    routes.routes=routes.routes.filter(p=>p.path!==PROGRAMME);plain.set('checkpoint-routes.json',valueBytes(routes));}
  plain.set('facts.json',valueBytes({archived:true}));plain.set('operands.json.gz',gzipSync(valueBytes({archived:true})));plain.set('publication.json',valueBytes({archived:true}));
  for(const [name,bytes] of plain)f.save('seed/'+name,bytes);
  f.save('seed/joint-result.json',{version:1,kind:'trusted-selected-joint-comparison-v1',mode:'authenticated-checkpoint-append-v1',
    candidate_code_executed:false,native:report.selected_native_report});
  f.save('seed/operating.json',{...structuredClone(REAL004.operating),returncode:failedOperating?1:0});
  f.save('seed/executing-policy.json',f.git('show',f.trusted+':'+PROGRAMME));
  const accepted=f.commit();
  const roleNames={facts:'derived-facts.json',certificate:'derived-certificate.json.gz',publication:'derived-publication.json',
    continuous_facts:'facts.json',operands:'operands.json.gz',continuous_publication:'publication.json',
    joint_result:'joint-result.json',operating:'operating.json',routes:'checkpoint-routes.json',executing_policy:'executing-policy.json'};
  const root={kind:'accepted-derived-selected-checkpoint-v1',id:'fixture-derived-seed',accepted_head:accepted,
    selected_commit:f.trusted,selection_sha256:valueSha(copy.facts.candidate_selection),execution_commit:f.trusted,
    execution_code_sha256:valueSha(copy.facts.execution_code),runtime_sha256:valueSha(copy.facts.runtime)};
  for(const [role,name] of Object.entries(roleNames)) {
    root[role]=f.pin('seed/'+name,accepted);
    if(name.endsWith('.gz')){const body=name.startsWith('derived')?copy.certificate:{archived:true};
      Object.assign(root[role],{decoded_bytes:valueBytes(body).length,decoded_sha256:valueSha(body)});}
  }
  f.save(CATALOGUE,{version:1,kind:'accepted-selected-checkpoints-v1',checkpoints:[f.rootRow,root]});f.commit();
  const reader=new f.native.ImmutableReader(f.root,f.trusted);
  return {reader,checkpointId:root.id};
}
test('one trusted-main derived seed reuses the same admission with truthful distinct lineage',async t=>{
  const f=await acceptedProducts(t),a=await installSeed(f);
  const q=(await f.api.qualifyCheckpoint(a));assert.equal(q.available,true);
  assert.equal(q.state.accepted_execution.kind,'trusted-main-derived-selected-checkpoint-v1');
  assert.equal(q.state.accepted_execution.source,undefined);
  assert.equal(q.state.accepted_execution.checkpoint_id,'fixture-derived-seed');
  f.api.releaseCheckpoint(q.state);
});
// A seed is not a hosted accepted result: even coherently republished owner
// corruption must undergo full coordinate validation on its first admission.
test('trusted-main seed rejects a coherently rehashed wrong owner index',async t=>{
  const f=await acceptedProducts(t);
  f.products.certificate.entries[0][1]=2;
  const a=await installSeed(f);
  await assert.rejects(()=>f.api.qualifyCheckpoint(a),/owner\/index\/parent identity/);
});
test('trusted-main seed still requires original successful terminal custody and complete routes',async t=>{
  const f=await acceptedProducts(t);
  const a=await installSeed(f,{failedOperating:true});await assert.rejects(async()=>(await f.api.qualifyCheckpoint(a)),/terminal custody/);
  const b=await installSeed(f,{omitRoute:true});await assert.rejects(async()=>(await f.api.qualifyCheckpoint(b)),/route census/);
  const c=await installSeed(f,{omitInherited:true});await assert.rejects(async()=>(await f.api.qualifyCheckpoint(c)),/complete inherited route census/);
});


test('accepted embedded policy still detects changed current eligibility without old policy hydration',async t=>{
 const f=await acceptedProducts(t),a=await acquire(f);
 const policy=JSON.parse(fs.readFileSync(path.join(f.root,PROGRAMME)));policy.programs.pop();
 f.save(PROGRAMME,policy);f.commit();
 const result=await qualify(f,a);assert.equal(result.available,false);assert.match(result.reason,/preserves accepted eligibility/);
});

test('accepted complete source routes remain projected from authenticated immutable bodies',async t=>{
  const sourcePaths=[0,1,8,19,28].map(n=>`data/geography/part-${n}.json`);
  const f=await acceptedProducts(t,{sourcePaths}),accepted=await acquire(f);
  const result=await qualify(f,accepted);assert.equal(result.available,true);
  const projection=f.api.projectSourceFeatures({state:result.state,ids:['A','B','C','D','E']});
  assert.deepEqual(projection.inputs.map(p=>p.path),sourcePaths);
  assert.deepEqual(projection.features.map(p=>p.id),['A','B','C','D','E']);
  f.api.releaseCheckpoint(result.state);f.transport.releaseAcceptedCheckpoint(accepted.handle);
  const omitted=await acquire(f,p=>p.certificate.inputs.pop());
  await assert.rejects(qualify(f,omitted),/Incomplete accepted coordinate|source binding inventory/);
});

function successorSelector(f,name='successor/sidecar.json') {
  f.save(name,f.sidecar); const bodyCommit=f.commit(), p=f.pin(name,bodyCommit);
  f.save('data/ownership-selection.json',{...f.selection,
    additive_release:{path:name,bytes:p.bytes,sha256:p.sha256}});
  return f.commit();
}
function currentReader(f,a,version) {
  return new f.native.ImmutableReader(f.root,version,{invocation:a.reader.invocation});
}
function candidateLedger(f,ledger,prefix) {
  const registry=JSON.parse(fs.readFileSync(path.join(f.root,f.sidecar.authority_registry.path)));
  f.save(prefix+'/ledger.json',ledger);const ledgerPin=f.pin(prefix+'/ledger.json',f.commit());
  // Build complete fixture bindings without using the production validator: the
  // adverse candidate must reach its real admission boundary with coherent pins.
  const components=ledger.rows.filter(row=>['assigned','zero-cell'].includes(row.disposition)).map(row=>{
    const entry=registry.entries.find(entry=>entry.authority_sha256===row.authority_sha256);
    return {...row,rule_sha256:entry.rule_sha256,authority_sha256:entry.authority_sha256};
  });
  const effective={...f.envelope.effective_reference,footprints_sha256:valueSha({domain:'worldatlas-effective-native-footprints:v2',
    base_reference:f.envelope.base_reference,authority_registry_sha256:valueSha(registry),ledger_sha256:ledgerPin.sha256,components})};
  f.save(prefix+'/patch.json',{...f.patch,ledger_sha256:ledgerPin.sha256,effective_reference:effective});
  const patchPin=f.pin(prefix+'/patch.json',f.commit());
  const assets={...f.sidecar.logical_asset_map,ledger:ledgerPin,patch:patchPin};
  f.save(prefix+'/envelope.json',{...f.envelope,...assets,effective_reference:effective});
  const envelopePin=f.pin(prefix+'/envelope.json',f.commit());
  f.save(prefix+'/sidecar.json',{...f.sidecar,logical_asset_map:assets,runtime_envelope:envelopePin});
  const sidecarPin=f.pin(prefix+'/sidecar.json',f.commit());
  f.save('data/ownership-selection.json',{...f.selection,additive_release:{path:sidecarPin.path,bytes:sidecarPin.bytes,sha256:sidecarPin.sha256}});
  return f.commit();
}

test('hosted admission omits unused rebind bodies while cold and changed rebinds still require them',async t=>{
  const f=await acceptedProducts(t),a=await acquire(f);
  const certificate=JSON.parse(f.git('show',f.ledger.current_rebind.commit+':'+f.ledger.current_rebind.path));
  const unused=new Set(['result','publication','operating'].map(role=>certificate[role].path));
  const denyUnused=reader=>{
    for(const method of ['read','stream']){const original=reader[method].bind(reader);
      reader[method]=(name,...args)=>{assert(!unused.has(name),'Historical rebind body requested: '+name);return original(name,...args);};}
    return reader;
  };
  denyUnused(a.reader);const admitted=await qualify(f,a);assert.equal(admitted.available,true);
  for(const name of unused)assert(![...a.reader.inventory.values()].some(p=>p.path===name&&p.whole_body_consumed));
  for(const role of ['request','facts'])assert([...a.reader.inventory.values()].some(p=>p.path===certificate[role].path&&p.whole_body_consumed));
  assert.deepEqual(admitted.state.ledger.current_rebind,f.ledger.current_rebind);
  assert.equal(unused.size,3);
  assert.deepEqual(JSON.parse(f.git('show',f.ledger.current_rebind.commit+':'+f.ledger.current_rebind.path)),certificate);
  await assert.rejects(()=>f.api.qualifyCheckpoint({reader:denyUnused(new f.native.ImmutableReader(f.root,f.trusted))}),/Historical rebind body requested/);
  f.save('changed-rebind/certificate.json',certificate);const pin=f.pin('changed-rebind/certificate.json',f.commit());
  const candidate=candidateLedger(f,{...f.ledger,current_rebind:pin},'changed-rebind');
  await assert.rejects(()=>f.api.qualifyTransition({state:admitted.state,reader:denyUnused(currentReader(f,a,candidate))}),/Historical rebind body requested/);
  f.api.releaseCheckpoint(admitted.state);f.transport.releaseAcceptedCheckpoint(a.handle);
});

test('accepted validation inheritance does not admit a malformed or changed candidate component',async t=>{
  const f=await acceptedProducts(t,{actualProducer:true,nativeOnly:true}),a=await acquire(f),admitted=await qualify(f,a);
  assert.equal(admitted.available,true);
  const corrupt=await acquire(f),stream=corrupt.reader.stream.bind(corrupt.reader);
  corrupt.reader.stream=async function*(name,...args){
    if(name!==f.sidecar.logical_asset_map.ledger.path){yield* stream(name,...args);return;}
    const chunks=[];for await(const chunk of stream(name,...args))chunks.push(chunk);
    const original=Buffer.concat(chunks).toString(),changed=original.replace('"native_cells":1','"native_cells":2');
    assert.notEqual(changed,original);yield Buffer.from(changed);
  };
  await assert.rejects(()=>qualify(f,corrupt),/Complete native JSON identity differs/);
  f.transport.releaseAcceptedCheckpoint(corrupt.handle);
  const unchanged=candidateLedger(f,structuredClone(f.ledger),'unchanged-candidate');
  const transition=await f.api.qualifyTransition({state:admitted.state,reader:currentReader(f,a,unchanged)});
  assert.equal(transition.available,true);assert.deepEqual(transition.changedNativeRows,[]);
  const malformed=structuredClone(f.ledger),native=malformed.rows.find(row=>row.representation==='native-cells');
  native.base_geometry.coordinates[0][1][0]+=.01;
  const bad=candidateLedger(f,malformed,'malformed-candidate');
  await assert.rejects(()=>f.api.qualifyTransition({state:admitted.state,reader:currentReader(f,a,bad)}),/current base changed/);
  const changed=structuredClone(f.ledger);changed.rows.find(row=>row.disposition==='rejected').reason='Changed retained exception';
  const drift=candidateLedger(f,changed,'changed-candidate');
  await assert.rejects(()=>f.api.qualifyTransition({state:admitted.state,reader:currentReader(f,a,drift)}),/Old complete ledger primitive/);
  f.api.releaseCheckpoint(admitted.state);f.transport.releaseAcceptedCheckpoint(a.handle);
});

test('older accepted selector advances to actual baseline with zero cold reconstruction',async t=>{
  const f=await acceptedProducts(t),a=await acquire(f),baseline=successorSelector(f);
  a.reader=currentReader(f,a,baseline);
  const read=f.native.ImmutableReader.prototype.read; const sourceReads=[];
  f.native.ImmutableReader.prototype.read=function(name,...args){sourceReads.push(name);return read.call(this,name,...args);};
  try {
    const q=await qualify(f,a);assert.equal(q.available,true);assert.equal(q.state.selected_commit,baseline);
    assert.equal(q.state.accepted_execution.historical_selected_commit,f.trusted);
    assert.equal(sourceReads.includes('data/source.json'),false);
    assert.equal(sourceReads.includes('data/native/runs.bin.gz'),false);
    assert.equal(nativeLiteral(q.state.patch.rows)[0].runs[0][1]-nativeLiteral(q.state.patch.rows)[0].runs[0][0],1);
    const transition=(await f.api.qualifyTransition({state:q.state,reader:a.reader}));
    assert.equal(transition.available,true);assert.equal(transition.baseline.selected_commit,baseline);
    assert.deepEqual(transition.changedNativeRows,[]);
    const census=f.api.checkpointRouteCensus({transition});
    assert(census.routes.some(p=>p.path==='successor/sidecar.json'));
    f.api.releaseCheckpoint(q.state);
  } finally {f.native.ImmutableReader.prototype.read=read;f.transport.releaseAcceptedCheckpoint(a.handle);}
});
test('intermediate newly consumed routes cannot change before the next candidate',async t=>{
  const f=await acceptedProducts(t),a=await acquire(f),baseline=successorSelector(f);
  a.reader=currentReader(f,a,baseline);const q=await qualify(f,a);assert.equal(q.available,true);
  // Keep the candidate selector on a new exact copy; mutate the intermediate
  // ordinary route only. Its old immutable pin alone must not hide this change.
  successorSelector(f,'candidate/sidecar.json');
  f.save('successor/sidecar.json',{changed:true});const candidate=f.commit();
  const result=(await f.api.qualifyTransition({state:q.state,reader:currentReader(f,a,candidate)}));
  assert.equal(result.available,false);assert.match(result.reason,/route changed/);
  f.api.releaseCheckpoint(q.state);f.transport.releaseAcceptedCheckpoint(a.handle);
});
test('older checkpoint cannot skip changed source routing on actual baseline',async t=>{
  const f=await acceptedProducts(t),a=await acquire(f);successorSelector(f);
  f.save('data/source.json',{type:'FeatureCollection',features:[]});const baseline=f.commit();
  a.reader=currentReader(f,a,baseline);const result=await qualify(f,a);
  assert.equal(result.available,false);assert.match(result.reason,/route changed/);
  f.transport.releaseAcceptedCheckpoint(a.handle);
});

test('unavailable accepted historical commit declines reuse without weakening tree validation',async t=>{
  const f=await acceptedProducts(t),a=await acquire(f,undefined,{merged:'d'.repeat(40)});
  const baseline=successorSelector(f);a.reader=currentReader(f,a,baseline);
  const result=await qualify(f,a);assert.equal(result.available,false);
  assert.match(result.reason,/historical checkpoint commit unavailable/);
  f.transport.releaseAcceptedCheckpoint(a.handle);
});

test('historical advancement rejects a local tree inconsistent with accepted provenance',async t=>{
  const f=await acceptedProducts(t),a=await acquire(f,undefined,{tree:'f'.repeat(40)});
  const baseline=successorSelector(f);a.reader=currentReader(f,a,baseline);
  await assert.rejects(qualify(f,a),/historical checkpoint tree differs/);
  f.transport.releaseAcceptedCheckpoint(a.handle);
});


test('actual native-only joint products survive Python retention and fresh accepted archive qualification',async t=>{
 const f=await acceptedProducts(t,{actualProducer:true,nativeOnly:true}),a=await acquire(f);
 // All producer state handles have been released. Admit the independently
 // transported actual products, without adding a new static checkpoint root.
 f.save(CATALOGUE,{version:1,kind:'accepted-selected-checkpoints-v1',checkpoints:[]});f.commit();
 const result=await qualify(f,a);assert.equal(result.available,true);
 assert.equal(result.state.accepted_execution.kind,'accepted-selected-checkpoint-artifact-v1');
 const native=result.state.additions.find(row=>row.representation==='native-cells');
 assert.equal(native.target_id,'B');assert.equal(Object.hasOwn(native,'geometry'),false);
 assert.deepEqual(nativeLiteral(native.native_rows),[{y:2,runs:[[2,3,2]]}]);
 // Independent full normalization of the actual producer's literal input proves
 // that hosted reconstruction retains the same validated native component view.
 const normalized=normaliseRetainedRepairLedger(f.ledger,result.state.registry);
 assert.deepEqual(nativeLiteral(native),nativeLiteral([...normalized.rows.values()].find(row=>row.representation==='native-cells')));
 assert.deepEqual(result.state.certificate,f.products.certificate);
 assert.deepEqual(result.state.certificate.entries.find(row=>row[0]==='B')[9],[[1,0,10,20]]);
 assert.deepEqual(nativeLiteral(result.state.patch.rows),[{y:1,runs:[[2,3,1]]},{y:2,runs:[[2,3,2]]}]);
 const reader=new f.native.ImmutableReader(f.root,f.trusted,{invocation:a.reader.invocation});
 const transition=(await f.api.qualifyTransition({state:result.state,reader}));
 assert.equal(transition.available,true);assert.deepEqual(transition.changedNativeRows,[]);
 f.api.releaseCheckpoint(result.state);f.transport.releaseAcceptedCheckpoint(a.handle);
});

test('accepted derived custody reuses an unchanged physical override after its inert logical file changes',async t=>{
 const f=await acceptedProducts(t,{sourceOverride:true}),a=await acquire(f);
 f.save('data/source.json',{unselected:'changed ordinary logical source'});const candidate=f.commit();
 const reader=new f.native.ImmutableReader(f.root,candidate,{invocation:a.reader.invocation});
 const qualified=await f.api.qualifyAcceptedCheckpoint({reader,acceptedHandle:a.handle});
 assert.equal(qualified.available,true);
 const transition=(await f.api.qualifyTransition({state:qualified.state,reader}));assert.equal(transition.available,true);
 assert.deepEqual(transition.changedNativeRows,[]);
 const census=f.api.checkpointRouteCensus({transition});
 assert.equal(census.routes.find(p=>p.path==='data/source.json').tree,f.git('ls-tree','-z',candidate,'--','data/source.json').toString());
 assert.ok(census.routes.some(p=>p.path==='data/source.json.gz'),'The real physical route remains in the complete census');
 assert.ok(![...reader.inventory.values()].some(p=>p.path==='data/source.json'));
 f.api.releaseCheckpoint(qualified.state);f.transport.releaseAcceptedCheckpoint(a.handle);
});

test('accepted derived custody retains real physical and mixed-use logical source routes',async t=>{
 for(const physicalLogicalSource of [false,true]){
  const f=await acceptedProducts(t,{sourceOverride:true,physicalLogicalSource}),a=await acquire(f);
  if(physicalLogicalSource){
   const inherited=Object.values(f.products.facts.actual_reader_inventories).flat().filter(p=>p.path==='data/source.json');
   assert.ok(inherited.length>0,'The actual derived archive retains inherited physical use');
   assert.ok(inherited.every(p=>p.whole_body_consumed===undefined),'Inherited protection uses actual descriptors, not a fabricated body reread');
  }
  const name=physicalLogicalSource?'data/source.json':'data/source.json.gz';
  f.save(name,Buffer.from('different actual physical input'));const candidate=f.commit();
  const reader=new f.native.ImmutableReader(f.root,candidate,{invocation:a.reader.invocation});
  const qualified=await f.api.qualifyAcceptedCheckpoint({reader,acceptedHandle:a.handle});
  assert.equal(qualified.available,false);assert.match(qualified.reason,/routing alternative changed/);
  f.transport.releaseAcceptedCheckpoint(a.handle);
 }
});


import {referenceCheckpointFixture} from './fixtures/selected-checkpoint.mjs';
// Build immutable accepted history once; every adverse still has a private
// repository, executing module, JSON objects, reader and qualified state.
let referenceSeed;
const referenceSeedCleanup=[];
after(async()=>{for(const cleanup of referenceSeedCleanup.reverse())await cleanup();});
async function referenceRefusalFixture(t){
 const seed=await (referenceSeed??=referenceCheckpointFixture({after:cleanup=>referenceSeedCleanup.push(cleanup)}));
 const repo=fs.mkdtempSync(path.join(path.dirname(seed.repo),'atlas-checkpoint-variant-'));
 t.after(()=>fs.rmSync(repo,{recursive:true,force:true}));
 fs.cpSync(seed.repo,repo,{recursive:true});
 const git=(...args)=>execFileSync('git',['-C',repo,...args],{stdio:['ignore','pipe','pipe']}).toString().trim();
 assert.equal(git('rev-parse','HEAD'),seed.candidate);
 assert.equal(fs.existsSync(path.join(repo,'.git/objects/info/alternates')),false);
 const write=(name,value)=>{const file=path.join(repo,name);fs.mkdirSync(path.dirname(file),{recursive:true});
  fs.writeFileSync(file,Buffer.isBuffer(value)?value:Buffer.from(JSON.stringify(value)));};
 const commit=()=>{git('add','.');git('commit','-m','Isolated checkpoint refusal');return git('rev-parse','HEAD');};
 const pin=(name,version)=>{const raw=execFileSync('git',['-C',repo,'show',version+':'+name]);
  const [mode,,git_blob_oid]=git('ls-tree',version,'--',name).split(/[ \t]/);
  return {commit:version,path:name,mode,git_blob_oid,bytes:raw.length,sha256:sha(raw)};};
 const projection=structuredClone(seed.projection),selection=JSON.parse(git('show',seed.candidate+':data/ownership-selection.json'));
 const project=()=>{write('inputs/projection.json',projection);const raw=fs.readFileSync(path.join(repo,'inputs/projection.json'));
  selection.reference_projection={path:'inputs/projection.json',bytes:raw.length,sha256:sha(raw)};
  write('data/ownership-selection.json',selection);return commit();};
 const api=checkpointTestAPI(t,await import(pathToFileURL(path.join(repo,MODULE)))),native=await import(pathToFileURL(path.join(repo,'scripts/check-effective-geographic-regression.mjs')));
 const reader=new native.ImmutableReader(repo,seed.selected),qualified=(await api.qualifyCheckpoint({reader}));
 assert.equal(qualified.available,true);
 assert.notStrictEqual(reader,seed.reader);assert.notStrictEqual(qualified.state,seed.state);
 t.after(()=>{assert.equal(seed.git('rev-parse','HEAD'),seed.candidate);assert.equal(seed.git('status','--porcelain'),'');});
 return {repo,git,write,commit,pin,projection,selection,project,api,native,reader,state:qualified.state,
  currentFeatures:structuredClone(seed.currentFeatures),features:structuredClone(seed.features)};
}
for (const [name,mutate,reason] of [
 ['forged projection',f=>{f.projection.reference.id='geography:forged';return f.project();},/latest release/],
 ['changed geometry with rebound source pin',f=>{const body=structuredClone(f.currentFeatures);body[0].geometry.coordinates[0][1][0]+=.25;
   f.write('data/geography/fixture.json',{type:'FeatureCollection',features:body});const c=f.commit();
   f.projection.source_updates[0].after=f.pin('data/geography/fixture.json',c);return f.project();},/geometry|pointset|non-metadata/i],
 ['replaced receipt',f=>{f.write('inputs/replacement-receipt.json',{reference_only:true});const c=f.commit();
   f.projection.receipts=[f.pin('inputs/replacement-receipt.json',c)];return f.project();},/receipt|records/i],
 ['changed original source pin',f=>{f.projection.source_updates[0].before=f.projection.source_updates[0].after;return f.project();},/actual selected source/],
 ['current source alias drift',f=>{f.write('data/geography/fixture.json',{type:'FeatureCollection',features:f.features});return f.commit();},/Current complete source differs/],
 ['current hierarchy alias drift',f=>{f.write('data/hierarchy.json',[]);return f.commit();},/Current hierarchy differs/],
 ['wrong complete projection bytes',f=>{f.write('inputs/projection.json',{forged:true});return f.commit();},/projection whole identity|Whole immutable input/],
]) test('checkpoint reference application refuses '+name,async t=>{
 const f=await referenceRefusalFixture(t),candidate=mutate(f);
 const reader=new f.native.ImmutableReader(f.repo,candidate,{invocation:f.reader.invocation});
 await assert.rejects(async()=>(await f.api.qualifyTransition({state:f.state,reader})),reason);
});

test('successor checkpoint binds current metadata routes and keeps unchanged projection reuse local',async t=>{
 const f=await referenceCheckpointFixture(t),reader=new f.native.ImmutableReader(f.repo,f.candidate,{invocation:f.reader.invocation});
 const first=(await f.api.qualifyTransition({state:f.state,reader}));assert.equal(first.available,true);
 const calls=[],nextReader=new f.native.ImmutableReader(f.repo,f.candidate,{invocation:f.reader.invocation});
 const read=nextReader.read.bind(nextReader);nextReader.read=(name,options)=>{calls.push(name);return read(name,options);};
 const next=(await f.api.qualifyTransition({state:first.candidate,reader:nextReader}));assert.equal(next.available,true);
 assert.deepEqual(next.candidate.certificate,first.candidate.certificate);
 assert(!calls.includes('inputs/projection.json'));
 f.write('data/geography/fixture.json',{type:'FeatureCollection',features:f.features});const changed=f.commit();
 const refused=(await f.api.qualifyTransition({state:first.candidate,reader:new f.native.ImmutableReader(f.repo,changed,{invocation:f.reader.invocation})}));
 assert.equal(refused.available,false);assert.match(refused.reason,/route changed/);
});


test('successor checkpoint refuses a changed newly introduced projection route',async t=>{
 const f=await referenceCheckpointFixture(t),reader=new f.native.ImmutableReader(f.repo,f.candidate,{invocation:f.reader.invocation});
 const first=(await f.api.qualifyTransition({state:f.state,reader}));assert.equal(first.available,true);
 f.write('inputs/projection.json',{forged:true});const changed=f.commit();
 const refused=(await f.api.qualifyTransition({state:first.candidate,reader:new f.native.ImmutableReader(f.repo,changed,{invocation:f.reader.invocation})}));
 assert.equal(refused.available,false);assert.match(refused.reason,/route changed/);
});


test('accepted canonical bindings reuse the private admitted ledger and patch digests without replay',async t=>{
 const f=await acceptedProducts(t),a=await acquire(f),records=[],streamed=[];
 const stream=a.reader.stream.bind(a.reader),original=crypto.createHash;
 a.reader.stream=function(name,...args){streamed.push(name);return stream(name,...args);};
 crypto.createHash=function(...args){
  const stack=new Error().stack,hash=Reflect.apply(original,this,args);
  // Observe only direct canonical value hashes at real derived admission, not
  // the store's required parse-time hashing or any nested equality checks.
  if(!/at valueSha[^\n]*\n\s*at admitDerivedCheckpoint/.test(stack))return hash;
  const update=hash.update,digest=hash.digest,record={bytes:0};
  hash.update=function(value,...rest){record.bytes+=typeof value==='string'?Buffer.byteLength(value,rest[0]):value.byteLength;return Reflect.apply(update,this,[value,...rest]);};
  hash.digest=function(...args){const result=Reflect.apply(digest,this,args);record.sha256=typeof result==='string'?result:result.toString('hex');records.push(record);return result;};
  return hash;
 };
 syncBuiltinESMExports();
 let result;
 try{result=await qualify(f,a);}finally{crypto.createHash=original;syncBuiltinESMExports();}
 assert.equal(result.available,true,result.reason);
 const bindings=f.products.facts.candidate_bindings;
 assert(records.some(row=>row.sha256===bindings.registry_sha256),'Instrumentation must observe the real registry comparison');
 assert(records.some(row=>row.sha256===bindings.manifest_sha256),'Instrumentation must observe the real manifest comparison');
 const repeated=records.filter(row=>[bindings.ledger_sha256,bindings.patch_sha256].includes(row.sha256));
 t.diagnostic('Repeated complete ledger/patch canonical hash bytes: '+repeated.reduce((n,row)=>n+row.bytes,0));
 assert.deepEqual(repeated,[],'Already admitted private products must not be traversed again only to recover their canonical digest');
 for(const role of ['ledger','patch'])assert.equal(streamed.filter(name=>name===f.sidecar.logical_asset_map[role].path).length,1);
 assert.equal(valueSha(nativeLiteral(result.state.ledger)),bindings.ledger_sha256);
 assert.equal(valueSha(nativeLiteral(result.state.patch)),bindings.patch_sha256);
 f.api.releaseCheckpoint(result.state);f.transport.releaseAcceptedCheckpoint(a.handle);
});

test('accepted private digests preserve noncanonical wire semantics, immutable views and release refusal',async t=>{
 const f=await acceptedProducts(t,{wireProducts:true}),a=await acquire(f),result=await qualify(f,a);
 assert.equal(result.available,true,result.reason);
 for(const role of ['ledger','patch']){
  const pin=f.sidecar.logical_asset_map[role],raw=f.git('show',pin.commit+':'+pin.path),literal=JSON.parse(raw);
  assert.notEqual(sha(raw),valueSha(literal),'Raw wire identity must remain distinct from the canonical binding');
  assert.equal(f.products.facts.candidate_bindings[role+'_sha256'],valueSha(literal));
  assert.deepEqual(valueBytes(nativeLiteral(result.state[role])),valueBytes(literal));
  assert.throws(()=>{result.state[role].rows=[];},TypeError);
 }
 const ledger=result.state.ledger,patch=result.state.patch;
 f.api.releaseCheckpoint(result.state);
 assert.throws(()=>valueSha(nativeLiteral(ledger)),/closed/);assert.throws(()=>valueSha(nativeLiteral(patch)),/closed/);
 f.transport.releaseAcceptedCheckpoint(a.handle);
});

for(const role of ['ledger','patch'])test('accepted private digest does not cache a changed '+role+' body across admissions',async t=>{
 const f=await acceptedProducts(t),a=await acquire(f),good=await qualify(f,a);
 assert.equal(good.available,true);
 const corrupt=await acquire(f),stream=corrupt.reader.stream.bind(corrupt.reader),directories=[],mkdtemp=fs.mkdtempSync;
 corrupt.reader.stream=async function*(name,...args){
  if(name!==f.sidecar.logical_asset_map[role].path){yield* stream(name,...args);return;}
  const chunks=[];for await(const chunk of stream(name,...args))chunks.push(chunk);
  const raw=Buffer.concat(chunks);assert.equal(raw.at(-1),10);raw[raw.length-1]=32;
  // Same parsed value and length, different complete wire bytes.
  yield raw;
 };
 fs.mkdtempSync=function(prefix,...args){const result=mkdtemp.call(this,prefix,...args);if(String(prefix).endsWith('native-intervals-'))directories.push(result);return result;};
 try{await assert.rejects(()=>qualify(f,corrupt),/Complete native JSON identity differs/);}
 finally{fs.mkdtempSync=mkdtemp;f.transport.releaseAcceptedCheckpoint(corrupt.handle);}
 assert(directories.length>0);for(const directory of directories)assert.equal(fs.existsSync(directory),false,'Failed invocation must release its own stores');
 assert.equal(valueSha(nativeLiteral(good.state[role])),f.products.facts.candidate_bindings[role+'_sha256'],'A failed separate admission must not close the valid snapshot');
 f.api.releaseCheckpoint(good.state);f.transport.releaseAcceptedCheckpoint(a.handle);
});


for(const packed of [false,true])test('accepted checkpoint catch-up acquires only its appended completed-authority operands'+(packed?' (packed objects)':''),async t=>{
  const f=await acceptedProducts(t,{nativeAppend:true,actualProducer:true}),a=await acquire(f);
  const next=await appendNativeAuthority(f,{completedConstructor:true});
  const binding=JSON.parse(f.git('show',next.entry.source_authority.commit+':'+next.entry.source_authority.path));
  const layers=[[next.entry.rule_preimage,next.entry.source_authority],
    [next.entry.completed_constructor,binding.source_evidence,binding.native_patch]];
  const bodies=new Map(layers.flat().map(p=>[p.git_blob_oid,f.git('cat-file','blob',p.git_blob_oid)]));
  omitFixtureObjects(t,f.root,layers.flat().map(p=>p.git_blob_oid),{packed});
  a.reader=currentReader(f,a,next.candidate);
  await assert.rejects(()=>qualify(f,a),/cat-file/,'Library callers remain read-only without acquisition');
  const calls=[];
  const q=await f.api.qualifyAcceptedCheckpoint({reader:a.reader,acceptedHandle:a.handle,
    acquireAuthorityInputs:async (reader,pins)=>{
      if(pins.some(p=>bodies.has(p.git_blob_oid))){
        assert.equal(reader.version,next.candidate);
        assert.deepEqual(pins,layers[calls.length]);calls.push(pins);
        for(const p of pins)assert.equal(execFileSync('git',['-C',f.root,'hash-object','-w','--stdin'],
          {input:bodies.get(p.git_blob_oid),encoding:'utf8'}).trim(),p.git_blob_oid);
      } else for(const p of pins)assert.doesNotThrow(()=>f.git('cat-file','-e',p.git_blob_oid));
      return {available:false,forged:'Callback return is not scientific evidence'};
    }});
  assert.equal(calls.length,2);assert.equal(q.available,true);
  assert.equal(q.state.selected_commit,next.candidate);
  assert.equal(q.state.accepted_execution.historical_selected_commit,f.trusted);
  assert.deepEqual(nativeLiteral(q.state.patch.rows),next.patch.rows);
  assert.deepEqual(nativeLiteral(q.state.ledger.rows),next.ledger.rows);
  f.api.releaseCheckpoint(q.state);f.transport.releaseAcceptedCheckpoint(a.handle);
});


test('accepted aggregate acquires complete inherited read groups without reopening historical science',async t=>{
  const f=await acceptedProducts(t,{nativeOnly:true,actualProducer:true}),a=await acquire(f);
  const read=p=>JSON.parse(f.git('show',p.commit+':'+p.path));
  const registry=read(f.sidecar.authority_registry),certificate=read(f.ledger.current_rebind);
  const bindings=registry.entries.map(entry=>read(entry.source_authority));
  const layers=[[f.sidecar.authority_registry,f.sidecar.runtime_envelope,...Object.values(f.sidecar.logical_asset_map)],
    [f.ledger.current_rebind],[certificate.request,certificate.facts],registry.entries.map(entry=>entry.source_authority)];
  assert.equal(layers.at(-1).length,2,'Both inherited authority bindings are one known group');
  const pins=[...new Map(layers.flat().map(p=>[p.git_blob_oid,p])).values()];
  const bodies=new Map(pins.map(p=>[p.git_blob_oid,f.git('cat-file','blob',p.git_blob_oid)]));
  const unused=[certificate.publication,certificate.operating,certificate.result,...bindings.flatMap(binding=>
    binding.kind==='source-target-native-custody-v1'?[binding.source_evidence,binding.native_patch]:
      [binding.native_proof.publication,...binding.native_proof.assets])];
  const omitted=[...new Map(unused.filter(p=>!bodies.has(p.git_blob_oid)).map(p=>[p.git_blob_oid,p])).values()];
  assert(omitted.length>0);
  omitFixtureObjects(t,f.root,[...pins,...omitted].map(p=>p.git_blob_oid));
  await assert.rejects(()=>qualify(f,a),/Invalid immutable blob size batch/,'No callback keeps the library read-only');
  const calls=[];
  a.reader=currentReader(f,a,f.trusted);
  const q=await f.api.qualifyAcceptedCheckpoint({reader:a.reader,acceptedHandle:a.handle,
    acquireAuthorityInputs:async (reader,group)=>{
      assert.equal(reader.version,f.trusted);
      const ordered=pins=>[...pins].sort((a,b)=>a.path.localeCompare(b.path));
      assert.deepEqual(ordered(group),ordered(layers[calls.length]));calls.push(group);
      for(const p of group)assert.equal(execFileSync('git',['-C',f.root,'hash-object','-w','--stdin'],
        {input:bodies.get(p.git_blob_oid),encoding:'utf8'}).trim(),p.git_blob_oid);
      return {available:true,state:{forged:'The ordinary reader must still authenticate'}};
    }});
  assert.equal(q.available,true,q.reason);assert.equal(calls.length,layers.length);
  assert.deepEqual(nativeLiteral(q.state.ledger.rows),f.ledger.rows);
  assert.deepEqual(nativeLiteral(q.state.patch.rows),f.patch.rows);
  for(const p of omitted)assert.throws(()=>f.git('cat-file','-e',p.git_blob_oid),'Metadata-only reuse must not acquire historical proof products');
  f.api.releaseCheckpoint(q.state);
  const binding=layers.at(-1)[0];omitFixtureObjects(t,f.root,[binding.git_blob_oid]);
  a.reader=currentReader(f,a,f.trusted);
  await assert.rejects(()=>f.api.qualifyAcceptedCheckpoint({reader:a.reader,acceptedHandle:a.handle,
    acquireAuthorityInputs:async()=>({available:true,complete:true})}),/Invalid immutable blob size batch/,'A successful callback return cannot replace missing bytes');
  f.transport.releaseAcceptedCheckpoint(a.handle);
});


test('accepted aggregate reuses only completed native classification under its whole registry binding',async t=>{
  const f=await acceptedProducts(t,{completedNative:true,actualProducer:true}),a=await acquire(f);
  const entries=f.registry.entries,completed=entries.find(entry=>entry.completed_constructor!==undefined);
  const pending=entries.filter(entry=>entry.completed_constructor===undefined);
  assert.equal(entries.length,3);assert.equal(pending.length,2);
  const read=p=>JSON.parse(f.git('show',p.commit+':'+p.path));
  assert.deepEqual(pending.map(entry=>read(entry.source_authority).kind).sort(),
    ['source-target-native-custody-v1',undefined]);
  const legacy=pending.find(entry=>read(entry.source_authority).kind===undefined);
  const {readRetainedRegistryAuthority}=await import(pathToFileURL(path.join(f.root,P+'selected-neighbor-prevention.mjs')));
  assert.throws(()=>readRetainedRegistryAuthority(new f.native.ImmutableReader(f.root,f.trusted),
    {...legacy,completed_constructor:completed.completed_constructor}),/Completed constructor requires a modern source-target authority/,
  'A new completion pin cannot convert legacy custody into native authority');
  // authority_sha256 deliberately excludes completion pins. Only the accepted
  // complete registry binding authorizes reusing the prior classification.
  for(const name of ['added legacy completion','changed native completion']){
    const registry=structuredClone(f.registry),entry=registry.entries.find(row=>row.authority_sha256===
      (name.startsWith('added')?legacy:completed).authority_sha256);
    entry.completed_constructor=name.startsWith('added')?completed.completed_constructor:
      {...completed.completed_constructor,sha256:'f'.repeat(64)};
    assert.deepEqual(registry.entries.map(row=>row.authority_sha256),entries.map(row=>row.authority_sha256));
    const forged=await acquire({...f,produced:undefined},p=>{p.facts.candidate_bindings.registry_sha256=valueSha(registry);});
    await assert.rejects(()=>qualify(f,forged),/Accepted checkpoint changed the complete ledger\/registry\/patch\/manifest/,name);
    f.transport.releaseAcceptedCheckpoint(forged.handle);
  }
  const p=completed.source_authority;omitFixtureObjects(t,f.root,[p.git_blob_oid]);
  const groups=[];
  const q=await f.api.qualifyAcceptedCheckpoint({reader:a.reader,acceptedHandle:a.handle,
    acquireAuthorityInputs:async(_reader,pins)=>{
      groups.push(pins);assert(!pins.some(pin=>pin.git_blob_oid===p.git_blob_oid),'Accepted completed binding must not be requested again');
    }});
  assert.equal(q.available,true,q.reason);
  assert(groups.some(pins=>pins.length===2&&pending.every(entry=>pins.some(pin=>pin.git_blob_oid===entry.source_authority.git_blob_oid))));
  assert(![...a.reader.inventory.values()].some(pin=>pin.git_blob_oid===p.git_blob_oid&&pin.whole_body_consumed));
  assert.deepEqual(nativeLiteral(q.state.ledger),f.ledger);assert.deepEqual(nativeLiteral(q.state.patch),f.patch);
  assert.deepEqual(q.state.registry,f.registry);f.api.releaseCheckpoint(q.state);
  assert.throws(()=>f.git('cat-file','-e',p.git_blob_oid),'The completed original binding remains absent');
  for(const entry of pending){
    const pin=entry.source_authority,body=f.git('cat-file','blob',pin.git_blob_oid);
    omitFixtureObjects(t,f.root,[pin.git_blob_oid]);
    a.reader=currentReader(f,a,f.trusted);
    await assert.rejects(()=>qualify(f,a),/Invalid immutable blob size batch/,'Unclassified accepted bindings still require exact bytes');
    assert.equal(execFileSync('git',['-C',f.root,'hash-object','-w','--stdin'],{input:body,encoding:'utf8'}).trim(),pin.git_blob_oid);
  }
  const coldReader=new f.native.ImmutableReader(f.root,f.acceptedBaseline);
  const cold=await f.api.qualifyCheckpoint({reader:coldReader});assert.equal(cold.available,true,cold.reason);
  await assert.rejects(()=>f.api.qualifyTransition({state:cold.state,reader:new f.native.ImmutableReader(f.root,f.trusted,{invocation:coldReader.invocation})}),
    /cat-file|Invalid immutable blob size batch/,'A fresh append must still read completed authority custody');
  f.api.releaseCheckpoint(cold.state);
  f.transport.releaseAcceptedCheckpoint(a.handle);
});


test('missing-object fixture refuses duplicate or absent targets before changing its store',async t=>{
 const f=await trustedFixture(t),p=f.pin('data/source.json',f.selected);
 const inventory=()=>f.git('cat-file','--batch-all-objects','--batch-check=%(objectname)').toString();
 const before=inventory();
 assert.throws(()=>omitFixtureObjects(t,f.root,[p.git_blob_oid,p.git_blob_oid]),/targets must be unique/);
 assert.equal(inventory(),before);assert.doesNotThrow(()=>f.git('cat-file','-e',p.git_blob_oid));
 assert.throws(()=>omitFixtureObjects(t,f.root,['0'.repeat(40)]),/Every omission target must exist first/);
 assert.equal(inventory(),before);assert.doesNotThrow(()=>f.git('cat-file','-e',p.git_blob_oid));
});

// Actual existing Node/Python producer, actual retained artifact parser and a
// fresh private reader. A live transition alone cannot cover this boundary.
test('final-bank joint output survives retention and fresh accepted checkpoint admission',async t=>{
 const f=await acceptedProducts(t,{actualProducer:true,finalBank:true});
 assert.equal(f.products.facts.version,2);assert.equal(f.products.facts.kind,'derived-selected-final-checkpoint-candidate-v2');
 const a=await acquire(f);t.after(()=>f.transport.releaseAcceptedCheckpoint(a.handle));
 const admitted=await qualify(f,a);assert.equal(admitted.available,true);assert.equal(admitted.state.version,2);
 assert.equal(admitted.state.selection.version,2);
 const next=await f.api.qualifyTransition({state:admitted.state,reader:new f.native.ImmutableReader(f.root,f.trusted,{invocation:a.reader.invocation})});
 assert.equal(next.available,true);assert.deepEqual(next.changedNativeRows,[]);assert.deepEqual(next.changedIds,[]);
});


test('final-bank software cold report reuses comparison without checkpoint issuance',async t=>{
 const f=await acceptedProducts(t,{actualProducer:true,finalBank:true}),a=await acquire(f);
 const acceptedSource=f.transport.readAcceptedCheckpoint(a.handle).source;
 f.transport.releaseAcceptedCheckpoint(a.handle);
 const archivePath='coordination/engineering/final-bank-fixture/geography-artifact.zip';
 f.save(archivePath,a.fixture.archive);f.save('data/selected-checkpoint.json',{...a.fixture.locator,retained_artifact:{path:archivePath}});
 const codePath='scripts/check-effective-geographic-regression.mjs';
 f.save(codePath,Buffer.concat([fs.readFileSync(path.join(f.root,codePath)),Buffer.from('\n// Actual reviewed software fixture.\n')]));
 const candidate=f.commit(),native=await import(pathToFileURL(path.join(f.root,codePath)));
 const keys=['GH_TOKEN','GITHUB_TOKEN','WORLDATLAS_CHECKOUT_TOKEN','GITHUB_REPOSITORY'];
 const previous={fetch:globalThis.fetch,environment:Object.fromEntries(keys.map(key=>[key,process.env[key]]))};
 const requests=[];
 globalThis.fetch=async(input,options)=>{const url=new URL(input);requests.push(url.href);
   assert.equal(options.headers.Authorization,undefined,'Candidate reads carry no credentials');
   assert.equal(options.method,'GET');
   assert.notEqual(url.hostname,'fixtures.blob.core.windows.net','No Actions archive transport in candidate code');
   assert.equal(url.origin,'https://api.github.com');
   assert(!url.pathname.endsWith('/zip'),'No authenticated artifact fallback');
   return new Response(JSON.stringify(await a.fixture.api(url.pathname+url.search)),{headers:{'content-type':'application/json'}});
 };
 for(const key of keys)delete process.env[key];process.env.GITHUB_REPOSITORY='owner/repo';
 try{
   const publicApi=f.transport.acceptedCheckpointAPI(undefined,{publicReadOnly:true,fetchImpl:globalThis.fetch});
   const publicMetadata=await publicApi('/repos/owner/repo/issues','GET');
   assert.deepEqual(publicMetadata,await a.fixture.api('/repos/owner/repo/issues'));
   await assert.rejects(()=>publicApi('/repos/owner/repo/issues','POST',{}),/metadata GET only/);
   await assert.rejects(()=>publicApi.artifactRedirect('/repos/owner/repo/actions/artifacts/56/zip'),/metadata GET only/);
   assert.throws(()=>f.transport.acceptedCheckpointAPI('fixture',{publicReadOnly:true}),/cannot carry credentials/);
   assert.throws(()=>f.transport.acceptedCheckpointAPI(undefined),/token required/,'Ordinary joint issuance retains token-required acquisition');
   const {loadGeographicReport}=await import(pathToFileURL(path.join(f.root,'scripts/geographic-report-artifact.mjs')));
   const retained={api:a.fixture.api,repo:'owner/repo',runId:acceptedSource.run_id,artifactName:acceptedSource.artifact_name,
     expectedHash:acceptedSource.report_sha256,source:acceptedSource};
   await assert.rejects(()=>loadGeographicReport({...retained,retainedArchive:()=>undefined}),/requires its exact retained geographic archive/);
   await assert.rejects(()=>loadGeographicReport({...retained,retainedArchive:()=>Buffer.from('corrupt')}),/differs from accepted artifact digest/);
   const report=await native.inspectSelectedAcquired(f.root,f.trusted,candidate,{fetchImpl:globalThis.fetch});
   assert.equal(report.status,'no-new-native-loss');assert.equal(report.candidate_code_executed,true);
   assert.equal(report.derived_checkpoint,undefined);assert.equal(report.checkpoint,undefined);
   assert(report.execution_code_inventory.some(p=>p.path.endsWith('selected-checkpoint.mjs')));
   assert(report.execution_code_inventory.some(p=>p.path===codePath&&p.sha256===sha(fs.readFileSync(path.join(f.root,codePath)))));
   assert.equal(requests.length,1,'The public-only fixture performs one explicit metadata GET');
   assert.equal(new URL(requests[0]).pathname,'/repos/owner/repo/issues');
   globalThis.fetch=previous.fetch;
   assert.deepEqual(f.git('status','--porcelain').toString().trim(),'','Report-only comparison writes no checkpoint products');
   const raw=path.join(f.root,'fixture-native-report.json');fs.writeFileSync(raw,JSON.stringify(report));
   const driver="import importlib.util,json,pathlib,sys,io,contextlib\nrepo=pathlib.Path(sys.argv[1]);baseline,candidate,raw,out=sys.argv[2:];s=importlib.util.spec_from_file_location('wrapper',repo/'scripts/run-geographic-check.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\noriginal=m.subprocess.check_output\ndef transport(command,*args,**kwargs):\n if '--input-type=module' in command:return pathlib.Path(raw).read_bytes()\n return original(command,*args,**kwargs)\nm.subprocess.check_output=transport\nm.unchanged_selected_inputs=lambda *args,**kwargs:None\nsys.argv=['run-geographic-check.py','--repo',str(repo),'--baseline',baseline,'--candidate',candidate,'--code-commit',candidate,'--out',out]\nwith contextlib.redirect_stdout(io.StringIO()):result=m.main()\nassert result==0\nprint(pathlib.Path(out).read_text())";
   let calls=0;const enclosing=()=>JSON.parse(execFileSync(process.env.PYTHON??'python3',['-I','-B','-c',driver,f.root,f.trusted,candidate,raw,path.join(f.root,'cold-main-'+(++calls)+'.json')],{encoding:'utf8',env:{...process.env,NODE:process.execPath}}));
   const wrapped=enclosing();assert.equal(wrapped.candidate_code_executed,true);assert.equal(wrapped.selected_native_report.candidate_code_executed,true);
   assert.equal(wrapped.checkpoint,undefined);assert.equal(wrapped.source_approval,false);
   fs.writeFileSync(raw,JSON.stringify({...report,candidate_code_executed:false}));
   assert.throws(enclosing,/lacks a completed native result/,'The real wrapper refuses a false candidate-code child claim');
   f.save('data/selected-checkpoint.json',a.fixture.locator);const missingArchive=f.commit();
   await assert.rejects(()=>native.inspectSelectedAcquired(f.root,f.trusted,missingArchive),/requires its authenticated accepted checkpoint/);
 }finally{globalThis.fetch=previous.fetch;for(const [key,value]of Object.entries(previous.environment)){if(value===undefined)delete process.env[key];else process.env[key]=value;}}
});
