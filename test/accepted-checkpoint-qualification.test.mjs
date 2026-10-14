import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';
import {gzipSync,crc32,deflateRawSync} from 'node:zlib';
import {ACCEPTED_CHECKPOINT_CODE} from '../scripts/accepted-selected-checkpoint.mjs';
import {renderWorkerResult} from '../scripts/worker-result.mjs';
import {createHash} from 'node:crypto';
import {shuffleOwnershipBytes} from '../src/ownership-codec.js';
import {valueBytes,valueSha,coordinateBounds,validateCurrentRebindLimits} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
import {deriveCoordinateDelta,projectSourceFeatures,projectNativeRows,qualifyTransition} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint.mjs';
const MODULE='coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint.mjs';
const PROGRAMME='coordination/engineering/selected-geography-effective-prevention-20261009/supported-programs.json';
const CATALOGUE='coordination/engineering/selected-checkpoint-reuse-20261012/accepted-checkpoints.json';
const CODE=[MODULE,'coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs','scripts/check-effective-geographic-regression.mjs','src/native-grid.js','src/ownership-codec.js'];
const sha=b=>createHash('sha256').update(b).digest('hex');
const polygon=(x,y=0)=>({type:'Polygon',coordinates:[[[x,y],[x+.2,y],[x+.2,y+.2],[x,y+.2],[x,y]]]});
const feature=(id,x)=>({type:'Feature',id,properties:{id,parent_id:'parent'},geometry:polygon(x)});
function fixtures(sourcePaths){
 const features=sourcePaths?sourcePaths.map((_,i)=>feature(String.fromCharCode(65+i),i*2)):[feature('A',0),feature('B',1),feature('C',5)];
 const rows=features.map((f,i)=>[f.id,i+1,'parent',1,sourcePaths?.[i]??'data/source.json',sourcePaths?0:i,valueSha(f),valueSha(f.geometry),valueSha({base_geometry_sha256:valueSha(f.geometry),additions:[]}),coordinateBounds(f.geometry)]);
 return {features,certificate:{version:2,kind:'selected-coordinate-neighbor-certificate-v2',entry_fields:['id','index','parent_id','parent_index','source','ordinal','whole_feature_sha256','geometry_sha256','effective_geometry_sha256','boxes'],binding:{selection:{old:true},sources:[],owners_sha256:valueSha(rows.map(r=>r.slice(0,4)))},entries:rows,inputs:[]}};
}
function addition(id,target,index,base,x){const geometry=polygon(x);return {component_id:id,target_id:target,pixelIndex:index,base_geometry_sha256:base,geometry,geometry_sha256:valueSha(geometry)};}

// This is a fresh miniature trusted repository, not a test-only authority hook.
// The real entry reads its ordinary committed catalogue and products exactly as
// production does. Candidate edits never control that executing catalogue.
async function trustedFixture(t,{incompleteNative=false,sourcePaths}={}){
 const root=fs.mkdtempSync(path.join(process.cwd(),'.checkpoint-test-'));
 t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const git=(...a)=>execFileSync('git',['-c','core.hooksPath=/dev/null','-c','user.name=Checkpoint fixture','-c','user.email=checkpoint@example.invalid','-C',root,...a],{env:{...process.env,GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:'/dev/null',GIT_NO_LAZY_FETCH:'1'},stdio:['ignore','pipe','pipe']});
 const save=(name,value)=>{const f=path.join(root,name);fs.mkdirSync(path.dirname(f),{recursive:true});fs.writeFileSync(f,Buffer.isBuffer(value)?value:valueBytes(value));};
 const commit=()=>{git('add','.');git('commit','-qm','Checkpoint fixture');return git('rev-parse','HEAD').toString().trim();};
 git('init','-q');save(PROGRAMME,fs.readFileSync(PROGRAMME));for(const name of CODE)save(name,fs.readFileSync(name));save('package.json',{type:'module'});
 const {features,certificate}=fixtures(sourcePaths), paths=sourcePaths??['data/source.json'];
 for(const name of paths)save(name,{type:'FeatureCollection',features:features.filter((_,i)=>certificate.entries[i][4]===name)});
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
 const pin=(name,at=git('rev-parse','HEAD').toString().trim())=>{const body=git('show',at+':'+name),tree=git('ls-tree',at,'--',name).toString().split(/\s+/);return {commit:at,path:name,mode:tree[0],git_blob_oid:tree[2],bytes:body.length,sha256:sha(body)};};
 save('original/publication.json',{assets:[{path:'patch-one.json',bytes:pin('original/patch-one.json').bytes,sha256:pin('original/patch-one.json').sha256}]});
 const two=commit();save('original/binding.json',{native_proof:{publication:pin('original/publication.json'),assets:[pin('original/patch-one.json',one)]}});const three=commit();
 const entry={policy_id:'retained-source-literal-additions',policy_version:1,rule_preimage:pin('original/rule.json',one),rule_sha256:pin('original/rule.json',one).sha256,source_authority:pin('original/binding.json',three)};entry.authority_sha256=valueSha(entry);
 const registry={version:1,kind:'retained-rule-authority-registry-v1',entries:[entry]};save('data/registry.json',registry);
 const baseSelection={version:1,method:manifest.method,manifest_path:'data/manifest.json',sha256:pin('data/manifest.json',one).sha256,release_id:reference.id,selected_geography:{version:1,kind:'complete-world-index-with-exact-encoded-overrides',path:'data/bank.json',bytes:1,sha256:'d'.repeat(64)}};
 const target={target_id:'A',pixelIndex:1,geometry:features[0].geometry,geometry_sha256:valueSha(features[0].geometry)};
 const currentRows=[{y:1,runs:[[0,1,2]]}];
 const request={base_selection:baseSelection,authority_registry_sha256:valueSha(registry),current_targets:[target],current_rows:currentRows,original_patch_sha256s:[valueSha(originalPatch)],acquisition:{predecessor_rows:[],predecessor_proof:null,native_inputs:[]}};
 const rebind={request,result:{native:{rows:originalPatch.rows}},facts:{acquisition_phases:[]},publication:{},operating:{}};
 for(const [name,body]of Object.entries(rebind))save('accepted-rebind/'+name+'.json',body);const four=commit();
 const rc={version:1,kind:'qualified-native-additive-current-bank-rebind-v1',execution_commit:one,base_selection:baseSelection,authority_registry_sha256:valueSha(registry),...Object.fromEntries(Object.keys(rebind).map(name=>[name,pin('accepted-rebind/'+name+'.json',four)]))};save('accepted-rebind/certificate.json',rc);const five=commit();
 const ledger={version:2,kind:'native-additive-repair-ledger-v2',authority_registry_sha256:valueSha(registry),scope_ids:['old','rejected'],rows:[{...literal,authority_sha256:entry.authority_sha256},{component_id:'rejected',disposition:'rejected',reason:'complete original exception',authority_sha256:entry.authority_sha256}],parent_inventory:{components:2,roster_sha256:'e'.repeat(64)},current_rebind:pin('accepted-rebind/certificate.json',five),current_targets:[target]};save('data/ledger.json',ledger);const six=commit();
 const normalized=[{...literal,authority_sha256:entry.authority_sha256,rule_sha256:entry.rule_sha256}];
 const effective={...reference,footprints_sha256:valueSha({domain:'worldatlas-effective-native-footprints:v2',base_reference:reference,authority_registry_sha256:valueSha(registry),ledger_sha256:pin('data/ledger.json',six).sha256,components:normalized})};
 const patch={version:2,kind:'unassigned-native-cells-v1',authority_registry_sha256:valueSha(registry),ledger_sha256:pin('data/ledger.json',six).sha256,base_reference:reference,effective_reference:effective,rows:originalPatch.rows};save('data/patch.json',patch);const seven=commit();
 const assets={base_manifest:pin('data/manifest.json',one),owner_roster:pin('data/owners.json',one),ledger:pin('data/ledger.json',six),patch:pin('data/patch.json',seven)};
 const envelope={version:2,kind:'retained-native-base-plus-delta-v2',base_reference:reference,effective_reference:effective,...assets};save('data/envelope.json',envelope);const eight=commit();
 const sidecar={version:2,kind:'retained-native-additive-selection-v2',base_selection:baseSelection,authority_registry:pin('data/registry.json',four),logical_asset_map:assets,runtime_envelope:pin('data/envelope.json',eight)};save('data/sidecar.json',sidecar);const nine=commit();
 const selection={...baseSelection,additive_release:{path:'data/sidecar.json',bytes:pin('data/sidecar.json',nine).bytes,sha256:pin('data/sidecar.json',nine).sha256}};save('data/ownership-selection.json',selection);const selected=commit();
 const sourcePins=paths.map(name=>({...pin(name,one),kind:'ordinary-immutable-git-source'}));
 const additions=normalized.map(row=>({...row,base_geometry:target.geometry,base_geometry_sha256:target.geometry_sha256}));
 const derived=deriveCoordinateDelta({certificate,oldAdditions:[],additions,selection}).certificate;
 const full={...derived,binding:{...derived.binding,release:reference,sources:sourcePins},inputs:sourcePins.map(source=>({path:source.path,source,whole_body_sha256:source.sha256,bytes:source.bytes}))};
 const execution_code=CODE.map(name=>pin(name,one)),runtime=[{path:process.execPath,bytes:fs.statSync(process.execPath).size,sha256:'f'.repeat(64)}];
 const facts={version:1,kind:'trusted-selected-coordinate-stage-v1',candidate_code_executed:false,selected_commit:selected,executing_commit:one,execution_code,runtime,binding:full.binding,complete_owners:features.length,complete_sources:paths.length};
 const compressed=gzipSync(valueBytes(full));save('accepted/certificate.json.gz',compressed);save('accepted/facts.json',facts);
 const publication={version:1,kind:facts.kind,complete:true,facts:{path:'facts.json',bytes:valueBytes(facts).length,sha256:valueSha(facts)},certificate:{path:'certificate.json.gz',bytes:compressed.length,sha256:sha(compressed),decoded_bytes:valueBytes(full).length,decoded_sha256:valueSha(full)}};save('accepted/publication.json',publication);
 const inventory=[PROGRAMME,...paths,'data/manifest.json','data/owners.json','data/registry.json','data/ledger.json','data/patch.json','data/sidecar.json','data/envelope.json','data/native/rows.bin.gz','data/native/runs.bin.gz'].map(name=>pin(name,selected));
 save('accepted/custody.json',{complete_cold_custody:[{facts,publication,effective_additions:additions,inventory}]});
 save('accepted/routes.json',inventory.map(p=>p.path).sort().map(name=>({path:name,tree:git('ls-tree','-z',selected,'--',name).toString()})));const accepted=commit();
 const rootRow={id:'fixture',accepted_head:accepted,selected_commit:selected,selection_sha256:valueSha(selection),execution_commit:one,execution_code_sha256:valueSha(execution_code),runtime_sha256:valueSha(runtime),facts:pin('accepted/facts.json'),certificate:{...pin('accepted/certificate.json.gz'),decoded_bytes:valueBytes(full).length,decoded_sha256:valueSha(full)},publication:pin('accepted/publication.json'),custody:pin('accepted/custody.json'),routes:pin('accepted/routes.json')};
 save(CATALOGUE,{version:1,kind:'accepted-selected-checkpoints-v1',checkpoints:[rootRow]});commit();
 const api=await import(pathToFileURL(path.join(root,MODULE))),native=await import(pathToFileURL(path.join(root,'scripts/check-effective-geographic-regression.mjs')));
 const reader=new native.ImmutableReader(root,selected,{allowance:{phaseBytes:512*1024**2,rssBytes:512*1024**2}}),budget={shared:reader.budget,carriedBytes:1024};
 return {api,native,reader,budget,selected,root,git,save,commit,pin,ledger,patch,sidecar,envelope,selection,rootRow};
}

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
const JOINT=['scripts/run-geographic-check.py','scripts/check-geographic-regression.py',
  'scripts/check-effective-geographic-regression.mjs','scripts/selected-checkpoint-native.mjs','src/native-grid.js','src/ownership-codec.js','scripts/evidence/immutable.py',
  'scripts/evidence/geometry.py','scripts/ellipsoidal_area.py','requirements.txt',P+'selected-neighbor-prevention.mjs',
  P+'selected-continuous-entry.mjs',MODULE,P+'selected-checkpoint-continuous.mjs',P+'selected-joint-entry.mjs',
  ...ACCEPTED_CHECKPOINT_CODE,'scripts/geographic_checkpoint_products.py'];
const MEMBERS=['derived-certificate.json.gz','derived-facts.json','derived-publication.json','facts.json',
  'operands.json.gz','publication.json','checkpoint-routes.json'];
async function acceptedProducts(t,{sourcePaths}={}) {
  const f=await trustedFixture(t,{sourcePaths});
  for(const name of JOINT)f.save(name,fs.readFileSync(name));
  f.save(CATALOGUE,{version:1,kind:'accepted-selected-checkpoints-v1',checkpoints:[f.rootRow]});
  const trusted=f.commit();
  const reader=new f.native.ImmutableReader(f.root,trusted,{allowance:f.reader.allowance});
  const budget={shared:reader.budget,carriedBytes:1024};
  const {state}=f.api.qualifyCheckpoint({reader,budget});
  const afterReader=new f.native.ImmutableReader(f.root,trusted,{allowance:reader.allowance,budget:reader.budget});
  const transition=f.api.qualifyTransition({state,reader:afterReader,budget});
  const census=f.api.checkpointRouteCensus({transition,budget});
  const certificate=transition.candidate.certificate;
  // A conservative complete superset exercises real nonempty source projection
  // and inverse custody without inventing a producer repair in this small repo.
  const plan=sourcePaths?{...transition.plan,required_ids:certificate.entries.map(r=>r[0]).sort(),
    source_paths:{baseline:[...sourcePaths].sort(),candidate:[...sourcePaths].sort()}}:transition.plan;
  const before=f.api.projectSourceFeatures({state,ids:plan.required_ids,budget});
  const after=f.api.projectSourceFeatures({state:transition.candidate,ids:plan.required_ids,budget,reuse:before});
  const sourceCustody=p=>({state_binding:p.state_binding,inputs:p.inputs,...p.custody});
  const inventory=r=>[...r.inventory.values()].sort((a,b)=>(a.commit+':'+a.path).localeCompare(b.commit+':'+b.path));
  const runtime=[0,1,2].map(i=>({path:'/fixture/runtime-'+i,mode:493,bytes:100+i,sha256:String(i+1).repeat(64),version:null}));
  const native={...structuredClone(REAL004.native),baseline_selection:state.selection,candidate_selection:state.selection,
    affected_rows:0,native_row_scope:{...REAL004.native.native_row_scope,changed_rows:[],shared_base_acquired_rows:[],shared_base_reused_rows:[]}};
  const continuousFacts={version:1,kind:'trusted-selected-continuous-comparison-v1',baseline_commit:trusted,
    candidate_commit:trusted,executing_commit:trusted,execution_code:JOINT.map(name=>f.pin(name,trusted)),runtime,
    plan,inverse:[...before.inverse.map(r=>({vintage:'baseline',...r})),...after.inverse.map(r=>({vintage:'candidate',...r}))],checkpoint_custody:{baseline:state.accepted_execution,candidate:state.accepted_execution},
    source_custody:{baseline:sourceCustody(before),candidate:sourceCustody(after),source_features_reused:true},
    candidate_code_executed:false,validation_route:'authenticated-checkpoint-append-v1'};
  const facts={version:1,kind:'derived-selected-checkpoint-candidate-v1',validation_stage:'native-passed-continuous-pending',
    accepted_checkpoint:false,executing_commit:trusted,execution_code:continuousFacts.execution_code,runtime,
    baseline_accepted_execution:state.accepted_execution,executing_authority_pins:[PROGRAMME,CATALOGUE]
      .map(name=>({...f.pin(name,trusted),whole_body_consumed:true})),
    actual_reader_inventories:{baseline:inventory(reader),candidate:inventory(afterReader)},
    baseline_commit:trusted,candidate_commit:trusted,baseline_selection:state.selection,candidate_selection:state.selection,
    candidate_bindings:{ledger_sha256:valueSha(state.ledger),registry_sha256:valueSha(state.registry),
      patch_sha256:valueSha(state.patch),manifest_sha256:valueSha(state.manifest)},
    transition_plan:plan,native_result_sha256:valueSha(native),candidate_code_executed:false,executing_policy:f.api.checkpointExecutingPolicy({transition,budget})};
  const operands={version:1,kind:'complete-selected-continuous-operands-v1',plan,
    effective_additions:{baseline:state.additions,candidate:state.additions},
    baseline:Object.fromEntries(before.features.map(f=>[f.id,f])),candidate:Object.fromEntries(after.features.map(f=>[f.id,f]))};
  const continuous={version:1,kind:continuousFacts.kind,candidate_code_executed:false,complete_owners:certificate.entries.length,
    source_binding:plan.source_bindings,required_ids:plan.required_ids,status:'no-footprint-change',regressions:0,
    original_strict_polygon_result:{...structuredClone(REAL004.strict),status:'no-footprint-change',changed_location_ids:[],changed_primitive_ids:[]}};
  const products=structuredClone({facts,certificate,census,continuousFacts,operands,native,continuous});
  f.api.releaseCheckpoint(state);
  const transport=await import(pathToFileURL(path.join(f.root,'scripts/accepted-selected-checkpoint.mjs')));
  return {...f,trusted,transport,products};
}
function pack(f,mutate=()=>{}) {
  const p=structuredClone(f.products);mutate(p);
  const bodies=new Map();
  const put=(name,value)=>{const decoded=valueBytes(value),encoded=name.endsWith('.gz')?gzipSync(decoded):decoded;
    bodies.set(name,encoded);return {path:name,bytes:encoded.length,sha256:sha(encoded),
      ...(name.endsWith('.gz')?{decoded_bytes:decoded.length,decoded_sha256:sha(decoded)}:{})};};
  const certificate=put('derived-certificate.json.gz',p.certificate),routes=put('checkpoint-routes.json',p.census);
  const cf=put('facts.json',p.continuousFacts),op=put('operands.json.gz',p.operands);
  const cp={version:1,kind:'trusted-selected-continuous-comparison-v1',complete:true,facts:cf,operands:op};put('publication.json',cp);
  const {runtime,caller_runtime,execution_runtimes,execution_code_inventory,...nativeInverse}=p.native;
  Object.assign(p.facts,{certificate,checkpoint_routes:routes,continuous_publication:cp,native_result_sha256:valueSha(nativeInverse)});
  const df=put('derived-facts.json',p.facts);
  put('derived-publication.json',{version:1,kind:p.facts.kind,complete:true,accepted_checkpoint:false,
    validation_stage:p.facts.validation_stage,certificate,facts:df,routes});
  p.continuous.issued_publication=cp;
  const report={version:1,method_id:'worldatlas-trusted-geography-check-v1',baseline_commit:f.trusted,
    candidate_commit:f.trusted,trusted_code_commit:f.trusted,candidate_code_executed:false,published:false,
    source_approval:false,gate_status:'passed',status:'no-new-regression',selected_native_report:p.native,
    selected_continuous_report:p.continuous,checkpoint:{version:1,kind:'selected-checkpoint-products-v1',members:MEMBERS.map(name=>{
      const raw=bodies.get(name),decoded=name.endsWith('.gz')?name.startsWith('derived')?valueBytes(p.certificate):valueBytes(p.operands):null;
      return {name,bytes:raw.length,sha256:sha(raw),...(decoded?{decoded_bytes:decoded.length,decoded_sha256:sha(decoded)}:{})};})}};
  const raw=valueBytes(report);return {report,raw,zip:zipMembers([['geography-check.json',raw],...MEMBERS.map(name=>[name,bodies.get(name)])])};
}
async function acquire(f,mutate) {
  const p=pack(f,mutate), request='01234567-abcd-4321-aaaa-123456789012',head=f.trusted,baseline=f.trusted,
    candidate=f.trusted,merged=f.trusted,tree=f.git('rev-parse',f.trusted+'^{tree}').toString().trim(),workflowHead=f.trusted;
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
  let carry=0;
  const result=await f.transport.acquireAcceptedCheckpoint({api,repo:'owner/repo',locator:{pr_number:7,request_id:request,head},
    token:'fixture',admit:bytes=>{carry=Math.max(carry,bytes);},fetchImpl:async()=>new Response(p.zip)});
  assert.equal(result.available,true);
  const reader=new f.native.ImmutableReader(f.root,f.trusted,{allowance:f.reader.allowance});
  return {handle:result.handle,reader,budget:{shared:reader.budget,carriedBytes:carry}};
}
async function qualify(f,a) {return f.api.qualifyAcceptedCheckpoint({reader:a.reader,acceptedHandle:a.handle,budget:a.budget});}

test('accepted original archive admits a private successor without a catalogue row for that selector',async t=>{
  const f=await acceptedProducts(t),a=await acquire(f);
  // Remove all static roots. Only current method authentication remains.
  f.save(CATALOGUE,{version:1,kind:'accepted-selected-checkpoints-v1',checkpoints:[]});f.commit();
  const result=await qualify(f,a);assert.equal(result.available,true);
  assert.equal(result.state.accepted_execution.kind,'accepted-selected-checkpoint-artifact-v1');
  assert.equal(result.state.ledger.rows.length,2);assert.equal(result.state.ledger.rows[1].disposition,'rejected');
  assert.deepEqual(f.api.projectNativeRows({state:result.state,rows:[1],budget:a.budget}).rows,[{y:1,runs:[[0,1,2]]}]);
  assert.equal(f.api.projectSourceFeatures({state:result.state,ids:['A'],budget:a.budget}).features[0].id,'A');
  const candidateReader=new f.native.ImmutableReader(f.root,f.trusted,{allowance:a.reader.allowance,budget:a.reader.budget});
  const transition=f.api.qualifyTransition({state:result.state,reader:candidateReader,budget:a.budget});assert.equal(transition.available,true);
  assert.deepEqual(f.api.checkpointRouteCensus({transition,budget:a.budget}).routes,f.products.census.routes);
  f.api.releaseCheckpoint(result.state);f.transport.releaseAcceptedCheckpoint(a.handle);
});
test('forged and released acceptance handles cannot mint private selected state',async t=>{
  const f=await acceptedProducts(t),a=await acquire(f);
  await assert.rejects(f.api.qualifyAcceptedCheckpoint({reader:a.reader,acceptedHandle:{},budget:a.budget}),/private accepted/);
  f.transport.releaseAcceptedCheckpoint(a.handle);
  await assert.rejects(qualify(f,a),/private accepted/);
});
test('accepted native success does not replace a missing or failed strict result',async t=>{
  const f=await acceptedProducts(t);
  for(const mutate of [p=>delete p.continuous.original_strict_polygon_result,p=>p.continuous.original_strict_polygon_result.regressions=1,
    p=>p.continuous.original_strict_polygon_result.geometry_errors.push({bad:true}),
    p=>p.continuous.original_strict_polygon_result.findings=[],p=>p.native.lost_or_reassigned_cells=1]){
    const a=await acquire(f,mutate);await assert.rejects(qualify(f,a),/successful.*result/);f.transport.releaseAcceptedCheckpoint(a.handle);
  }
});
test('coherently rehashed omitted routes, stale selectors, old exception drift and unknown schema refuse',async t=>{
  const f=await acceptedProducts(t);
  for(const [mutate,reason] of [
    [p=>p.census.routes.pop(),/route census/],
    [p=>p.facts.candidate_bindings.ledger_sha256='0'.repeat(64),/complete ledger/],
    [p=>p.facts.foreign_schema=true,/Unknown accepted derived/],
    [p=>delete p.continuousFacts.checkpoint_custody,/Unknown complete accepted continuous/],
    [p=>p.facts.executing_policy.body+=' ',/policy identity differs/],
    [p=>p.facts.executing_policy.body=p.facts.executing_policy.body.replace('1','2'),/policy body differs/],
    [p=>p.facts.execution_code.pop(),/Unsupported accepted joint/],
    [p=>p.certificate.entries.pop(),/Incomplete accepted coordinate/]]) {
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
test('archive carry and actual executing code remain necessary at accepted admission',async t=>{
  const f=await acceptedProducts(t),a=await acquire(f);a.budget.carriedBytes=0;
  await assert.rejects(qualify(f,a),/carry is undercharged/);
  fs.appendFileSync(path.join(f.root,'scripts/evidence-policy.mjs'),'\n// uncommitted executable drift\n');
  const b=await acquire(f);await assert.rejects(qualify(f,b),/changed executing checkpoint method/);
});
test('census retains complete unchanged/absent routes and rejects public transition wrappers',async t=>{
  const f=await acceptedProducts(t),a=await acquire(f),{state}=await qualify(f,a);
  const transition=f.api.qualifyTransition({state,reader:a.reader,budget:a.budget});
  assert.throws(()=>f.api.checkpointRouteCensus({transition:{...transition},budget:a.budget}),/private qualified selected transition/);
  const census=f.api.checkpointRouteCensus({transition,budget:a.budget});
  assert(census.routes.some(p=>p.path==='data/native/runs.bin.gz'));assert(census.routes.some(p=>p.path==='data/source.json'));
  assert(Object.isFrozen(census.routes));f.api.releaseCheckpoint(state);
  assert.throws(()=>f.api.checkpointRouteCensus({transition,budget:a.budget}),/private qualified selected transition/);
});

test('wrapper-only native identities have an exact inverse and empty strict scopes preserve null regressions',async t=>{
  const f=await acceptedProducts(t);
  const p=structuredClone(f.products);
  Object.assign(p.native,{runtime:p.facts.runtime[0],caller_runtime:p.facts.runtime[1],
    execution_runtimes:p.facts.runtime,execution_code_inventory:p.facts.execution_code});
  // pack() deliberately hashes the original numerical report, as the real joint
  // producer does before attaching its separately bound wrapper identities.
  f.products=p;const a=await acquire(f,p=>{
    p.continuous.regressions=null;p.continuous.original_strict_polygon_result.regressions=null;
  });
  assert.equal((await qualify(f,a)).available,true);
  const b=await acquire(f,p=>{p.native.execution_code_inventory=[];});
  await assert.rejects(qualify(f,b),/wrapper execution/);
});

async function installSeed(f,{failedOperating=false,omitRoute=false,omitInherited=false}={}) {
  f={...f,products:structuredClone(f.products)};
  f.products.facts.execution_code=f.products.facts.execution_code.slice(0,15);
  f.products.continuousFacts.execution_code=f.products.facts.execution_code;
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
  for(const [name,bytes] of plain)f.save('seed/'+name,bytes);
  f.save('seed/joint-result.json',{version:1,kind:'trusted-selected-joint-comparison-v1',mode:'authenticated-checkpoint-append-v1',
    candidate_code_executed:false,native:report.selected_native_report,continuous_result:report.selected_continuous_report});
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
    if(name.endsWith('.gz')){const body=name.startsWith('derived')?copy.certificate:copy.operands;
      Object.assign(root[role],{decoded_bytes:valueBytes(body).length,decoded_sha256:valueSha(body)});}
  }
  f.save(CATALOGUE,{version:1,kind:'accepted-selected-checkpoints-v1',checkpoints:[f.rootRow,root]});f.commit();
  const reader=new f.native.ImmutableReader(f.root,f.trusted,{allowance:f.reader.allowance});
  return {reader,checkpointId:root.id,budget:{shared:reader.budget,carriedBytes:0}};
}
test('one trusted-main derived seed reuses the same admission with truthful distinct lineage',async t=>{
  const f=await acceptedProducts(t),a=await installSeed(f);
  const q=f.api.qualifyCheckpoint(a);assert.equal(q.available,true);
  assert.equal(q.state.accepted_execution.kind,'trusted-main-derived-selected-checkpoint-v1');
  assert.equal(q.state.accepted_execution.source,undefined);
  assert.equal(q.state.accepted_execution.checkpoint_id,'fixture-derived-seed');
  f.api.releaseCheckpoint(q.state);
});
test('trusted-main seed still requires original successful terminal custody and complete routes',async t=>{
  const f=await acceptedProducts(t);
  const a=await installSeed(f,{failedOperating:true});assert.throws(()=>f.api.qualifyCheckpoint(a),/terminal custody/);
  const b=await installSeed(f,{omitRoute:true});assert.throws(()=>f.api.qualifyCheckpoint(b),/route census/);
  const c=await installSeed(f,{omitInherited:true});assert.throws(()=>f.api.qualifyCheckpoint(c),/complete inherited route census/);
});


test('accepted embedded policy still detects changed current eligibility without old policy hydration',async t=>{
 const f=await acceptedProducts(t),a=await acquire(f);
 const policy=JSON.parse(fs.readFileSync(path.join(f.root,PROGRAMME)));policy.programs.pop();
 f.save(PROGRAMME,policy);f.commit();
 const result=await qualify(f,a);assert.equal(result.available,false);assert.match(result.reason,/preserves accepted eligibility/);
});

// Exact clean004 logical path roster/order, from facts.json SHA256
// 3c024899d7be3e8726179eb22609ebc07854cb35c86b84baa02943d9020bb2a9.
// Body identities below come from the miniature repository's actual reads.
test('accepted five-source custody joins complete real-order projections to lexical plan paths',async t=>{
  const sourcePaths=[0,1,8,19,28].map(n=>`data/geography/part-${n}.json`);
  const f=await acceptedProducts(t,{sourcePaths});
  assert.deepEqual(f.products.continuousFacts.source_custody.baseline.inputs.map(p=>p.path),sourcePaths);
  assert.deepEqual(f.products.facts.transition_plan.source_paths.baseline,[...sourcePaths].sort());
  const accepted=await acquire(f);const result=await qualify(f,accepted);assert.equal(result.available,true);
  f.api.releaseCheckpoint(result.state);f.transport.releaseAcceptedCheckpoint(accepted.handle);
  for(const mutate of [
    p=>p.continuousFacts.source_custody.baseline.inputs.pop(),
    p=>{const side=p.continuousFacts.source_custody.baseline;side.inputs[4]=side.inputs[0];},
    p=>{const side=p.continuousFacts.source_custody.baseline;side.actual_inputs[4]=side.actual_inputs[0];},
    p=>p.continuousFacts.source_custody.candidate.actual_inputs[0].sha256='0'.repeat(64),
    p=>p.continuousFacts.source_custody.baseline.actual_inputs[0].whole_body_consumed=false,
  ]){const a=await acquire(f,mutate);await assert.rejects(qualify(f,a),/source (input custody|body mode\/OID\/hash)/);
    f.transport.releaseAcceptedCheckpoint(a.handle);}
});

function successorSelector(f,name='successor/sidecar.json') {
  f.save(name,f.sidecar); const bodyCommit=f.commit(), p=f.pin(name,bodyCommit);
  f.save('data/ownership-selection.json',{...f.selection,
    additive_release:{path:name,bytes:p.bytes,sha256:p.sha256}});
  return f.commit();
}
function currentReader(f,a,version) {
  return new f.native.ImmutableReader(f.root,version,{allowance:a.reader.allowance,
    budget:a.reader.budget});
}
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
    assert.equal(q.state.patch.rows[0].runs[0][1]-q.state.patch.rows[0].runs[0][0],1);
    const transition=f.api.qualifyTransition({state:q.state,reader:a.reader,budget:a.budget});
    assert.equal(transition.available,true);assert.equal(transition.baseline.selected_commit,baseline);
    assert.deepEqual(transition.changedNativeRows,[]);
    const census=f.api.checkpointRouteCensus({transition,budget:a.budget});
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
  const result=f.api.qualifyTransition({state:q.state,reader:currentReader(f,a,candidate),budget:a.budget});
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
