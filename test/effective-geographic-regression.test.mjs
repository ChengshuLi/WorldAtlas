import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync,spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gzipSync,gunzipSync} from 'node:zlib';
import {ImmutableReader,NativeAssetImage,SelectedGeometrySources,loadBaseSelection,loadSelection,inspectSelectedAcquired,selectedReferenceOwners,selectedGeometrySourceAlias,selectedNativeSourceMembership,inspectSelected,compareIntervals,compareRepairLedgers,readArtifactConsumption,validateReleaseCatalogue,validateArtifactSourceMetadata,loadNativeRowTable,acquireNativeRows,validateNativeRowCarry} from '../scripts/check-effective-geographic-regression.mjs';
import {shuffleOwnershipBytes} from '../src/ownership-codec.js';
import {prepareReferenceMetadataProjection} from '../scripts/selected-reference-metadata.mjs';
import {projectReferenceFeatures} from '../src/reference-metadata.js';
import {JOINT_CODE} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-joint-entry.mjs';
import {valueBytes,valueSha,readOriginalRuleAuthority,readCurrentRebindCustody,LEGACY_CURRENT_REBIND_CODE,selectedCoordinateShard,joinSelectedCoordinateCertificate,acceptColdCoordinateCertificate,selectedAffectedPlan,possibleNeighbors,compareVersionedRepairLedgers,selectedCertificateAffectedPlan,acquireCurrentRebindOperands,sealColdCoordinateCertificate,reopenColdCoordinateCertificate} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';

const sha=b=>createHash('sha256').update(b).digest('hex'),root=process.cwd();
const retained=process.env.WORLDATLAS_PREVENTION_CONTROLS;
if(retained){assert.equal(fs.realpathSync(path.dirname(retained)),path.dirname(retained));assert.equal(fs.existsSync(retained),false);assert.throws(()=>fs.lstatSync(retained),{code:'ENOENT'});fs.mkdirSync(retained);}
let fixtureOrdinal=0;
function fixture({ownerRows}={}){
 const repo=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'selected-geography-fixture-')));
 const git=(...args)=>execFileSync('git',['-C',repo,...args],{stdio:['ignore','pipe','pipe']}).toString().trim();
 git('init');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid');
 const write=(name,value)=>{const raw=Buffer.isBuffer(value)?value:Buffer.from(JSON.stringify(value));fs.mkdirSync(path.dirname(path.join(repo,name)),{recursive:true});fs.writeFileSync(path.join(repo,name),raw);return raw;};
 const issued=[];
 const commit=()=>{git('add','.');git('commit','-m','Whole immutable synthetic fixture');const head=git('rev-parse','HEAD');issued.push(head);return head;};
 // Copy only real executing namespaces; no dependencies, datasets or checkout.
 for(const name of [...JOINT_CODE,'coordination/engineering/selected-checkpoint-reuse-20261012/accepted-checkpoints.json'])write(name,fs.readFileSync(name));
 for(const name of ['package.json','requirements.txt','.github/evidence-policy.json'])write(name,fs.readFileSync(name));
 write('data/world-index.json',{parts:['geography/fixture.json']});write('data/geography/fixture.json',{type:'FeatureCollection',features:[]});
 write('data/hierarchy.json',[]);write('data/canonical-grid/manifest.json',{version:1});write('data/geographic-releases/index.json',{});
 const release=write('data/geographic-releases/release.json',{id:'geography:review:fixture'});
 write('data/geographic-releases/current-manifest.json',{path:'release.json',sha256:sha(release)});
 const owners=ownerRows??[{index:1,id:'old-owner',province_id:'parent',province_index:1},{index:2,id:'other-owner',province_id:'parent',province_index:1}];
 const bounds=write('data/canonical-grid/bounds.json.gz',gzipSync(Buffer.from(JSON.stringify(owners))));
 const origin=commit();
 const part=(kind,words)=>{const raw=Buffer.from(words.buffer),encoded=gzipSync(shuffleOwnershipBytes(words)),name=`native-v1/ownership/${kind}-0.bin.gz`;write('data/canonical-grid/fixture/'+name,encoded);return {kind,offset:0,words:words.length,path:name,bytes:encoded.length,sha256:sha(encoded),decoded_bytes:raw.length,decoded_sha256:sha(raw),encoding:'byte-shuffle'};};
 const select=(intervals,{extraSelection={},indices=false,badRows=false,transport=false,releaseId='geography:review:fixture',reference=null}={})=>{
  const rows=new Uint32Array(8),words=[];let cursor=0;
  for(let y=0;y<4;y++){rows[y*2]=cursor;rows[y*2+1]=(intervals[y]??[]).length;for(const [start,end,owner]of intervals[y]??[]){words.push(owner*4+start,end-1);cursor++;}}
  if(badRows)rows[2]++;
  const manifest={version:2,method:'native-linear-evenodd-first-owner-v1',size:4,coordinateBits:2,runWords:words.length,parts:[part('rows',rows),part('runs',Uint32Array.from(words))],geographic_release:releaseId,bounds:{sha256:sha(bounds),decoded_bytes:Buffer.byteLength(JSON.stringify(owners))},original_assets:{bounds:{role:'original-identity-parent-camera-context',commit:origin,path:'data/canonical-grid/bounds.json.gz',sha256:sha(bounds)}},native_latitudes:{sha256:'1'.repeat(64)},...(reference?{footprints_sha256:reference.footprints_sha256,hierarchy_sha256:reference.hierarchy_sha256}:{})};
  const manifestPath=transport?'data/canonical-grid/transport/manifest.json':'data/canonical-grid/fixture/manifest.json';
  if(transport){
   let offset=0;const bodies=manifest.parts.map(p=>fs.readFileSync(path.join(repo,'data/canonical-grid/fixture',p.path)));
   const files=manifest.parts.map((p,i)=>{const item={path:p.path,offset,bytes:bodies[i].length,sha256:sha(bodies[i]),mode:'100644'};offset+=item.bytes;return item;});
   const whole=Buffer.concat(bodies),cut=Math.max(1,Math.floor(whole.length/2));let at=0;
   const parts=[whole.subarray(0,cut),whole.subarray(cut)].map((body,i)=>{const raw=gzipSync(body),item={path:'group/part-'+i+'.bin.gz',offset:at,bytes:raw.length,sha256:sha(raw),decoded_bytes:body.length,decoded_sha256:sha(body)};at+=body.length;write('data/canonical-grid/transport/bank/'+item.path,raw);return item;});
   const index={version:1,issue:1295,kind:'ordered-exact-original-byte-fragments',files,parts,whole_bytes:whole.length,whole_sha256:sha(whole)},encoded=write('data/canonical-grid/transport/bank/index.json',index);
   manifest.native_asset_transport={version:1,kind:index.kind,index:{path:'data/canonical-grid/transport/bank/index.json',bytes:encoded.length,sha256:sha(encoded)},logical_assets:files.length,original_compressed_bytes:whole.length};
  }
  const raw=write(manifestPath,manifest),digest=sha(raw);
  const products=[{path:'manifest.json',bytes:raw.length,sha256:digest},...manifest.parts];
  const receipt={method:manifest.method,checked_rows:4,checked_cells:16,unchecked_cells:0,checked_runs:words.length/2,installation_ready:false,products,two_run_products:products.length,run_one_sha256:sha(Buffer.from(JSON.stringify(products))),run_two_sha256:sha(Buffer.from(JSON.stringify(products)))};
  const receiptRaw=write('coordination/engineering/fixture/receipt.json',receipt),proofCommit=commit();
  write('scripts/native-ownership/verified-candidates.json',{version:1,candidates:{[digest]:{commit:proofCommit,path:'coordination/engineering/fixture/receipt.json',sha256:sha(receiptRaw),role:'reviewed-exhaustive-native-rule-comparison',installation_approval:false}}});
  write('data/ownership-selection.json',{version:1,method:manifest.method,manifest_path:manifestPath,sha256:digest,release_id:manifest.geographic_release,...extraSelection});
  return commit();
 };
 return {repo,git,write,commit,select,cleanup:()=>{
  if(retained){const objects=[...new Set(git('rev-list','--objects',...issued).split('\n').map(row=>row.split(' ')[0]))].map(oid=>{const type=git('cat-file','-t',oid),body=execFileSync('git',['-C',repo,'cat-file',type,oid],{maxBuffer:Number(git('cat-file','-s',oid))});assert.equal(createHash('sha1').update(Buffer.from(type+' '+body.length+'\0')).update(body).digest('hex'),oid);return {oid,type,bytes:body.length,sha256:sha(body),base64:body.toString('base64')};});const result={kind:'complete-synthetic-immutable-entry-fixture',commits:issued,objects,source_approval:false};fs.writeFileSync(path.join(retained,`fixture-${fixtureOrdinal++}.json.gz`),gzipSync(Buffer.from(JSON.stringify(result))),{flag:'wx'});}
  fs.rmSync(repo,{recursive:true,force:true});
 }};
}

test('actual immutable entry rejects owner loss/reassignment with rawworld geometry unchanged',()=>{
 const f=fixture();try{
  const base=f.select([[[0,2,1]],[[1,3,2]],[],[]]);
  const gain=f.select([[[0,3,1]],[[1,3,2]],[],[]]);
  assert.equal(inspectSelected(f.repo,base,gain).status,'no-new-native-loss');
  const retired=spawnSync(process.execPath,[path.join(f.repo,'scripts/check-effective-geographic-regression.mjs'),f.repo,base,gain],{encoding:'utf8'});
  assert.equal(retired.status,1);assert.equal(retired.stdout,'');
  assert.match(retired.stderr,/Use python -I -B scripts\/run-geographic-check\.py/);
  const lost=f.select([[[0,1,1]],[[1,3,2]],[],[]]);
  const report=inspectSelected(f.repo,base,lost);assert.equal(report.lost_or_reassigned_cells,1);assert.deepEqual(report.intervals,[{row:0,start:1,end:2,previous_owner:'old-owner',candidate_owner:null}]);
  const transferred=f.select([[[0,2,2]],[[1,3,2]],[],[]]);assert.equal(inspectSelected(f.repo,base,transferred).lost_or_reassigned_cells,2);
  f.git('checkout',base,'--','scripts/native-ownership/verified-candidates.json');f.git('reset','--hard',base);
  const command=[path.join(f.repo,'scripts/run-geographic-check.py'),'-I'];
  const preload=path.join(f.repo,'untrusted-preload.cjs'),preloadSentinel=path.join(f.repo,'preload-executed');fs.writeFileSync(preload,`require('node:fs').writeFileSync(${JSON.stringify(preloadSentinel)},'executed');`);
  const result=spawnSync(process.env.WORLDATLAS_TEST_PYTHON??'python3',['-I','-B',command[0],'--repo',f.repo,'--baseline',base,'--candidate',lost,'--out',path.join(f.repo,'blocked.json')],{encoding:'utf8',env:{...process.env,NODE:process.execPath,NODE_OPTIONS:'--require='+preload,NODE_PATH:f.repo}});
  assert.equal(fs.existsSync(preloadSentinel),false,'actual trusted child must not execute an inherited preload');
  assert.equal(result.status,1,result.stderr);assert.ok(fs.existsSync(path.join(f.repo,'blocked.json')),result.stderr);const actual=JSON.parse(fs.readFileSync(path.join(f.repo,'blocked.json')));assert.equal(actual.status,'native-regressions-found');assert.equal(actual.candidate_code_executed,false);assert.equal(actual.selected_native_report.lost_or_reassigned_cells,1);
  const native=actual.selected_native_report;
  assert.equal(native.runtime.path,fs.realpathSync(process.execPath));
  assert(native.execution_code_inventory.some(p=>p.path==='scripts/geography-prefetch.mjs'&&p.sha256===sha(fs.readFileSync(path.join(f.repo,p.path)))));
  assert(native.caller_runtime&&native.execution_runtimes.some(p=>p.path===native.caller_runtime.path&&p.sha256===native.caller_runtime.sha256));
  assert(native.execution_runtimes.some(p=>p.path===native.runtime.path&&p.sha256===native.runtime.sha256));
  const sentinel=fs.readFileSync(path.join(f.repo,'blocked.json'));
  fs.appendFileSync(path.join(f.repo,'scripts/check-effective-geographic-regression.mjs'),'\n// Deliberate current checkout drift');
  const collision=spawnSync(process.env.WORLDATLAS_TEST_PYTHON??'python3',['-I','-B',command[0],'--repo',f.repo,'--baseline',base,'--candidate',lost,'--out',path.join(f.repo,'blocked.json')],{encoding:'utf8',env:{...process.env,NODE:process.execPath}});
  assert.match(collision.stderr,/Report destination already exists/);assert.deepEqual(fs.readFileSync(path.join(f.repo,'blocked.json')),sentinel);
  const dangling=path.join(f.repo,'dangling.json');fs.symlinkSync('missing.json',dangling);
  const link=spawnSync(process.env.WORLDATLAS_TEST_PYTHON??'python3',['-I','-B',command[0],'--repo',f.repo,'--baseline',base,'--candidate',lost,'--out',dangling],{encoding:'utf8',env:{...process.env,NODE:process.execPath}});
  assert.match(link.stderr,/Symlink report path forbidden/);assert.equal(fs.readlinkSync(dangling),'missing.json');
 }finally{f.cleanup();}
});

test('software checker executes candidate native code against distinct data and detects real owner loss', () => {
 const f = fixture();
 try {
  const base = f.select([[[0, 2, 1]], [], [], []]);
  f.select([[[0, 1, 1]], [], [], []]);
  const nativePath = 'scripts/check-effective-geographic-regression.mjs';
  fs.appendFileSync(path.join(f.repo, nativePath), '\n// Reviewed candidate-code identity control.\n');
  const candidate = f.commit();
  const output = path.join(f.repo, 'software-native-loss.json');
  const env = {...process.env, NODE: process.execPath};
  for (const name of ['GH_TOKEN', 'GITHUB_TOKEN', 'WORLDATLAS_CHECKOUT_TOKEN', 'GIT_CONFIG_COUNT', 'GIT_ASKPASS', 'SSH_ASKPASS', 'GIT_SSH_COMMAND']) delete env[name];
  const result = spawnSync(process.env.WORLDATLAS_TEST_PYTHON ?? 'python3', ['-I', '-B',
   path.join(f.repo, 'scripts/run-geographic-check.py'), '--repo', f.repo,
   '--baseline', base, '--candidate', candidate, '--code-commit', candidate, '--out', output], {encoding: 'utf8', env});
  assert.equal(result.status, 1, result.stderr);
  assert.ok(fs.existsSync(output), result.stderr);
  const report = JSON.parse(fs.readFileSync(output));
  assert.equal(report.status, 'native-regressions-found');
  assert.equal(report.baseline_commit, base);
  assert.equal(report.candidate_commit, candidate);
  assert.notEqual(base, candidate);
  assert.equal(report.trusted_code_commit, candidate);
  assert.equal(report.candidate_code_executed, true);
  assert.equal(report.selected_native_report.lost_or_reassigned_cells, 1);
  assert.equal(report.selected_native_report.candidate_code_executed, false, 'retain legacy child bytes honestly');
  assert.match(report.execution_limits.join(' '), /marker is not evidence/);
  const code = report.selected_native_report.execution_code_inventory.find(row => row.path === nativePath);
  assert.equal(code.sha256, sha(fs.readFileSync(path.join(f.repo, nativePath))));
  assert.notEqual(code.sha256, sha(execFileSync('git', ['-C', f.repo, 'show', base + ':' + nativePath])));
  assert.equal(report.checkpoint, undefined);
  assert.equal(report.unchanged_selected_inputs, undefined);
 } finally { f.cleanup(); }
});

test('missing native selection, dishonest row partition and unsupported additive hook fail closed',()=>{
 const f=fixture();try{const base=f.select([[[0,2,1]],[],[],[]]);
  fs.unlinkSync(path.join(f.repo,'data/ownership-selection.json'));const removed=f.commit();assert.throws(()=>inspectSelected(f.repo,base,removed),/removed or introduced/);
  const bad=f.select([[[0,2,1]],[],[],[]],{badRows:true});assert.throws(()=>inspectSelected(f.repo,base,bad),/partition incomplete/);
  const unsupported=f.select([[[0,2,1]],[],[],[]],{extraSelection:{additive_release:{path:'proposal.json'}}});assert.throws(()=>inspectSelected(f.repo,base,unsupported),/Unsupported committed additive/);
 }finally{f.cleanup();}
});

test('changed actual asset body cannot hide behind an unchanged manifest descriptor',()=>{
 const f=fixture();try{const base=f.select([[[0,2,1]],[],[],[]]);
  f.write('data/canonical-grid/fixture/native-v1/ownership/runs-0.bin.gz',Buffer.from('coherently unchanged manifest, corrupt actual native words'));
  const corrupt=f.commit();assert.throws(()=>inspectSelected(f.repo,base,corrupt),/Whole immutable input differs/);
 }finally{f.cleanup();}
});

test('full stable owner identity detects coherent index relabel and boundary-sized gaps',()=>{
 const owners=[{id:'a'},{id:'b'}];assert.deepEqual(compareIntervals([[0,4,1]],[[0,4,1]],{row:2,ownersBefore:owners,ownersAfter:[{id:'b'},{id:'a'}]}),[{row:2,start:0,end:4,previous_owner:'a',candidate_owner:'b'}]);
 assert.equal(compareIntervals([[0,1,1],[3,4,2]],[[0,1,1],[1,3,2],[3,4,2]],{row:0,ownersBefore:owners,ownersAfter:owners}).length,0);
 assert.throws(()=>compareIntervals([[0,2,1]],[[0,3,1],[2,4,2]],{row:0,ownersBefore:owners,ownersAfter:owners}),/Invalid complete owner interval/);
});

test('full ledger comparison retains zero-cell primitives and rejects coherent omission/source drift',()=>{
 const row={component_id:'x',disposition:'zero-cell',target_id:'a',pixelIndex:1,base_geometry_sha256:'1'.repeat(64),geometry_sha256:'2'.repeat(64),geometry:{type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,0]]]},source_receipt_sha256:'3'.repeat(64)};
 const ledger={version:1,kind:'native-additive-repair-ledger-v1',rule_sha256:'4'.repeat(64),scope_ids:['x'],rows:[row]};
 assert.equal(compareRepairLedgers(ledger,structuredClone(ledger)),1);
 const reordered=structuredClone(ledger);reordered.rows[0].geometry={coordinates:row.geometry.coordinates,type:row.geometry.type};
 assert.notEqual(JSON.stringify(reordered.rows[0].geometry),JSON.stringify(row.geometry));
 assert.equal(compareRepairLedgers(ledger,reordered),1);
 for(const change of [
  r=>r.pixelIndex=String(r.pixelIndex),
  r=>[r.geometry.coordinates[0][1],r.geometry.coordinates[0][2]]=[r.geometry.coordinates[0][2],r.geometry.coordinates[0][1]],
  r=>r.geometry.coordinates[0].pop(),
  r=>r.geometry.coordinates[0][1][0]='1',
  r=>r.geometry.coordinates[0][1]={0:1,1:0},
  r=>delete r.geometry.type,
  r=>r.geometry.foreign=null
 ]){const changed=structuredClone(ledger);change(changed.rows[0]);assert.throws(()=>compareRepairLedgers(ledger,changed),/lost\/rebound/);}
 assert.throws(()=>compareRepairLedgers(ledger,{...ledger,scope_ids:[],rows:[]}),/lost\/rebound/);
 const changed=structuredClone(ledger);changed.rows[0].source_receipt_sha256='5'.repeat(64);assert.throws(()=>compareRepairLedgers(ledger,changed),/lost\/rebound/);
 assert.throws(()=>compareRepairLedgers(ledger,{...ledger,scope_ids:['x','x'],rows:[row,row]}),/duplicate/);
});


test('missing original proof object uses only the exact whole same-path retained receipt',()=>{
 const f=fixture();try{const base=f.select([[[0,2,1]],[],[],[]]);
  const file='scripts/native-ownership/verified-candidates.json',registry=JSON.parse(fs.readFileSync(path.join(f.repo,file))),proof=Object.values(registry.candidates)[0];proof.commit='f'.repeat(40);f.write(file,registry);const retained=f.commit();
  const report=inspectSelected(f.repo,retained,retained);assert.equal(report.status,'no-new-native-loss');assert.equal(report.baseline_receipt_provenance.registered_origin.commit,'f'.repeat(40));assert.equal(report.baseline_receipt_provenance.consumed.commit,retained);assert.equal(report.baseline_receipt_provenance.whole_body_alias,true);
  f.write(proof.path,{coherent:'foreign receipt body'});const wrong=f.commit();assert.throws(()=>inspectSelected(f.repo,retained,wrong),/Whole immutable input differs/);
 }finally{f.cleanup();}
});


test('manifest-bound immutable native transport restores full cross-fragment original members',()=>{
 const f=fixture();try{
  const bodies=[Buffer.from('whole-rows-original'),Buffer.from('whole-runs-original')];let offset=0;
  const members=bodies.map((b,i)=>{const p={path:'native-v1/ownership/'+(i?'runs':'rows')+'-0.bin.gz',offset,bytes:b.length,sha256:sha(b),mode:'100644'};offset+=b.length;return p;});
  const whole=Buffer.concat(bodies),cut=bodies[0].length-3;let at=0;
  const parts=[whole.subarray(0,cut),whole.subarray(cut)].map((body,i)=>{const encoded=gzipSync(body),p={path:'group/part-'+i+'.bin.gz',offset:at,bytes:encoded.length,sha256:sha(encoded),decoded_bytes:body.length,decoded_sha256:sha(body)};at+=body.length;f.write('bank/'+p.path,encoded);return p;});
  const index={version:1,issue:1295,kind:'ordered-exact-original-byte-fragments',files:members,parts,whole_bytes:whole.length,whole_sha256:sha(whole)};
  const encoded=f.write('bank/index.json',index),version=f.commit();
  const manifest={parts:members,native_asset_transport:{version:1,kind:index.kind,index:{path:'bank/index.json',bytes:encoded.length,sha256:sha(encoded)},logical_assets:members.length,original_compressed_bytes:whole.length}};
  const reader=new ImmutableReader(f.repo,version),image=new NativeAssetImage(reader,manifest,'native/manifest.json');
  assert.deepEqual(image.logical('native/'+members[0].path,members[0]),bodies[0]);
  assert.throws(()=>image.logical('foreign/'+members[0].path,members[0]),/Foreign selected native logical path/);
  assert.deepEqual(image.logical('native/'+members[1].path,members[1]),bodies[1]);
  assert.throws(()=>new NativeAssetImage(new ImmutableReader(f.repo,version),{...manifest,native_asset_transport:{...manifest.native_asset_transport,logical_assets:1}},'native/manifest.json'),/roster/);
  const changed={...index,files:[{...members[0],sha256:'0'.repeat(64)},members[1]]};const raw=f.write('bank/index.json',changed),coherent=f.commit();
  assert.throws(()=>new NativeAssetImage(new ImmutableReader(f.repo,coherent),{...manifest,native_asset_transport:{...manifest.native_asset_transport,index:{path:'bank/index.json',bytes:raw.length,sha256:sha(raw)}}},'native/manifest.json'),/Foreign\/rebound/);
  // Coherently rebind adjacent offsets while preserving every original member.
  // Actual complete gzip lengths must still match the declared decoded pins.
  const rebound=structuredClone(index);rebound.parts[0].decoded_bytes--;rebound.parts[1].offset--;rebound.parts[1].decoded_bytes++;
  const reboundRaw=f.write('bank/index.json',rebound),reboundVersion=f.commit();
  const reboundImage=new NativeAssetImage(new ImmutableReader(f.repo,reboundVersion),{...manifest,native_asset_transport:{...manifest.native_asset_transport,index:{path:'bank/index.json',bytes:reboundRaw.length,sha256:sha(reboundRaw)}}},'native/manifest.json');
  assert.throws(()=>reboundImage.logical('native/'+members[0].path,members[0]),/declared decoded size differs/);

 }finally{f.cleanup();}
});


test('actual selected entry compares typed whole native bank against ordinary predecessor',()=>{
 const f=fixture();try{
  const base=f.select([[[0,2,1]],[[1,3,2]],[],[]]);
  const identical=f.select([[[0,2,1]],[[1,3,2]],[],[]],{transport:true});
  assert.equal(inspectSelected(f.repo,base,identical).lost_or_reassigned_cells,0);
  const lost=f.select([[[0,1,1]],[[1,3,2]],[],[]],{transport:true});
  const report=inspectSelected(f.repo,base,lost);assert.equal(report.lost_or_reassigned_cells,1);
  f.write('data/canonical-grid/transport/bank/group/part-0.bin.gz',Buffer.from('drifted actual whole transport'));
  const drift=f.commit();assert.throws(()=>inspectSelected(f.repo,base,drift),/Whole native fragment size differs|Whole immutable input differs/);
 }finally{f.cleanup();}
});


test('selected source identity consumes exact encoded override and rejects incomplete or stale maps',()=>{
 const f=fixture();try{
  const base=f.select([[[0,2,1]],[[1,3,2]],[],[]],{transport:true});
  const selection=JSON.parse(fs.readFileSync(path.join(f.repo,'data/ownership-selection.json')));
  const geometry={type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,0]]]};
  const collection={type:'FeatureCollection',features:['old-owner','other-owner'].map(id=>({type:'Feature',id,properties:{id,parent_id:'parent'},geometry}))};
  const whole=Buffer.from(JSON.stringify(collection)),encoded=f.write('source/complete.json.gz',gzipSync(whole));
  const footprint=sha(Buffer.from(JSON.stringify(collection.features.map(f=>[f.id,f.geometry]).sort((a,b)=>a[0].localeCompare(b[0]))))),release=f.write('data/geographic-releases/selected.json.gz',gzipSync(Buffer.from(JSON.stringify({releases:[{id:selection.release_id,footprints_sha256:footprint}]}))));
  f.write('data/geographic-releases/current-manifest.json',{path:'selected.json.gz',sha256:sha(release)});const origin=f.commit();
  const pin=(name,version)=>{const body=execFileSync('git',['-C',f.repo,'show',version+':'+name]),[mode,,oid]=f.git('ls-tree',version,'--',name).split(/[ \t]/);return {commit:version,path:name,mode,git_blob_oid:oid,bytes:body.length,sha256:sha(body)};};
  const override={...pin('source/complete.json.gz',origin),logical_path:'data/geography/fixture.json',encoding:'gzip',decoded_bytes:whole.length,decoded_sha256:sha(whole)};
  const bank={version:1,kind:'complete-world-index-with-exact-encoded-overrides',release_id:selection.release_id,native_manifest_sha256:selection.sha256,footprints_sha256:footprint,locations:2,world_index:pin('data/world-index.json',base),unchanged_files:[],overrides:[override]};
  const select=bank=>{const raw=f.write('source/selected-bank.json',bank);f.write('data/ownership-selection.json',{...selection,selected_geography:{version:1,kind:bank.kind,path:'source/selected-bank.json',bytes:raw.length,sha256:sha(raw)}});return f.commit();};
  const current=select(bank),snapshot=loadSelection(new ImmutableReader(f.repo,current));
  const actual=snapshot.geometrySources.read('data/geography/fixture.json');assert.deepEqual(actual.body,whole);assert.equal(actual.source.kind,'selected-exact-encoded-override');
  const shard=selectedCoordinateShard(snapshot.geometrySources,['data/geography/fixture.json']);
  const certificate=joinSelectedCoordinateCertificate(snapshot.geometrySources,[shard]);
  assert.equal(certificate.entries.length,2);assert.throws(()=>joinSelectedCoordinateCertificate(snapshot.geometrySources,[]),/Missing actual/);assert.throws(()=>joinSelectedCoordinateCertificate(snapshot.geometrySources,[shard,shard]),/duplicate source/);
  const plan=selectedAffectedPlan(certificate,['old-owner','other-owner'].map(id=>({id,primitives:[geometry]})));assert.deepEqual(plan.pairs,[['old-owner','other-owner']]);assert.deepEqual(plan.required_ids,['old-owner','other-owner']);
  const nativeOnly={representation:'native-cells',component_id:'source-target:old-owner',target_id:'old-owner',pixelIndex:1,
   disposition:'assigned',base_geometry:geometry,base_geometry_sha256:valueSha(geometry),native_cells:1,
   native_rows:[{y:2,runs:[[3,4,1]]}],native_bounds:[10,20,10,20],
   source_receipt_sha256:'a'.repeat(64),authority_sha256:'b'.repeat(64),rule_sha256:'c'.repeat(64)};
  const nativeSnapshot=loadBaseSelection(new ImmutableReader(f.repo,current));
  nativeSnapshot.additive={normalized_rows:[nativeOnly]};
  const nativeSources=new SelectedGeometrySources(nativeSnapshot);
  const nativeShard=selectedCoordinateShard(nativeSources,['data/geography/fixture.json']);
  assert.deepEqual(nativeShard.entries.find(row=>row.id==='old-owner').boxes,[[0,0,10,20]]);
  assert.equal(nativeShard.entries.find(row=>row.id==='old-owner').effective_geometry_sha256,
   valueSha({base_geometry_sha256:valueSha(geometry),additions:[nativeOnly]}));
  nativeSnapshot.additive={normalized_rows:[{...nativeOnly,native_rows:[{y:2,runs:[[3,4,2]]}]}]};
  assert.throws(()=>selectedCoordinateShard(nativeSources,['data/geography/fixture.json']),/native component interval/i);
  assert.throws(()=>possibleNeighbors(certificate,geometry,{excludeIds:['old-owner','other-owner']}),/SELF target/);
  assert.notDeepEqual(actual.body,execFileSync('git',['-C',f.repo,'show',current+':data/geography/fixture.json']),'historical ordinary path must never replace selected body');
  assert.throws(()=>snapshot.geometrySources.read('data/geography/foreign.json'),/Foreign source/);
  const incomplete=select({...bank,overrides:[]});assert.throws(()=>loadSelection(new ImmutableReader(f.repo,incomplete)),/Incomplete selected source containing/);
  const stale=select({...bank,native_manifest_sha256:'0'.repeat(64)});assert.throws(()=>loadSelection(new ImmutableReader(f.repo,stale)),/source\/native\/release binding/);
  const wrong=select({...bank,overrides:[{...override,decoded_sha256:'0'.repeat(64)}]});
  const bound=loadSelection(new ImmutableReader(f.repo,wrong));assert.throws(()=>bound.geometrySources.read('data/geography/fixture.json'),/Whole selected source override differs/);
 }finally{f.cleanup();}
});


test('explicit v2 authority conservation permits append but preserves every original zero-cell primitive',()=>{
 const geometry={type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,0]]]};
 const pin=(name,value)=>{const bytes=valueBytes(value);return {commit:'1'.repeat(40),path:name,mode:'100644',git_blob_oid:createHash('sha1').update(Buffer.from('blob '+bytes.length+'\0')).update(bytes).digest('hex'),bytes:bytes.length,sha256:sha(bytes)};};
 const entry=profile=>{const preimage={version:3,source_profile:profile,representation:'literal-base-or-complete-additions'},rule_preimage=pin(profile+'/rule.json',preimage),source_authority=pin(profile+'/source.json',{kind:'model-control-only',profile});const e={policy_id:'retained-source-addition',policy_version:3,rule_sha256:rule_preimage.sha256,rule_preimage,source_authority};return {...e,authority_sha256:valueSha(e)};};
 const first=entry('A'),second=entry('B'),registry=entries=>({version:1,kind:'retained-rule-authority-registry-v1',entries:entries.sort((a,b)=>a.authority_sha256.localeCompare(b.authority_sha256))});
 const oldRegistry=registry([first]),newRegistry=registry([first,second]);
 const row={component_id:'component:a',disposition:'zero-cell',target_id:'owner:a',pixelIndex:1,base_geometry_sha256:'2'.repeat(64),geometry,geometry_sha256:valueSha(geometry),source_receipt_sha256:'3'.repeat(64),native_cells:0};
 const before={version:1,kind:'native-additive-repair-ledger-v1',rule_sha256:first.rule_sha256,scope_ids:[row.component_id],rows:[row]};
 const oldRow={...row,rule_sha256:first.rule_sha256,authority_sha256:first.authority_sha256},nextRow={...row,component_id:'component:b',target_id:'owner:b',rule_sha256:second.rule_sha256,authority_sha256:second.authority_sha256};
 const after={version:2,kind:'native-additive-repair-ledger-v2',authority_registry_sha256:valueSha(newRegistry),scope_ids:[row.component_id,nextRow.component_id],rows:[oldRow,nextRow]};
 assert.equal(compareVersionedRepairLedgers(before,after,{beforeRegistry:oldRegistry,afterRegistry:newRegistry}).appended_authorities,1);
 const omitted={...after,scope_ids:[nextRow.component_id],rows:[nextRow]};assert.throws(()=>compareVersionedRepairLedgers(before,omitted,{beforeRegistry:oldRegistry,afterRegistry:newRegistry}),/primitive\/authority lost/);
 const rebound={...after,rows:[{...oldRow,rule_sha256:second.rule_sha256,authority_sha256:second.authority_sha256},nextRow]};assert.throws(()=>compareVersionedRepairLedgers(before,rebound,{beforeRegistry:oldRegistry,afterRegistry:newRegistry}),/primitive\/authority lost/);
 const altered=structuredClone(after);altered.rows[0].geometry.coordinates[0][1][0]=2;assert.throws(()=>compareVersionedRepairLedgers(before,altered,{beforeRegistry:oldRegistry,afterRegistry:newRegistry}),/original primitive identity/);
 const changedRegistry=registry([second]),missing={...after,authority_registry_sha256:valueSha(changedRegistry)};assert.throws(()=>compareVersionedRepairLedgers(before,missing,{beforeRegistry:oldRegistry,afterRegistry:changedRegistry}),/authority rebound|authority removed/);
 assert.throws(()=>compareVersionedRepairLedgers(before,{...after,authority_registry_sha256:'0'.repeat(64)},{beforeRegistry:oldRegistry,afterRegistry:newRegistry}),/unbound versioned/);
 assert.throws(()=>compareRepairLedgers(before,after),/Incomplete selected repair ledger/,'legacy v1 dispatch must never silently interpret v2');
});


for(const completedAliases of [false,true])test('whole original rule custody derives actual issued preimage and refuses rebinding before selection, aliases='+completedAliases,()=>{
 const f=fixture();try{
  const pin=(name,commit)=>{const raw=execFileSync('git',['-C',f.repo,'show',commit+':'+name]),[mode,,blob]=f.git('ls-tree',commit,'--',name).split(/[ \t]/);return {commit,path:name,mode,blob,bytes:raw.length,sha256:sha(raw)};};
  const id='component:a',geometry={type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,0]]]},executed_code=[{path:'model.js',bytes:1,sha256:'1'.repeat(64)}];
  const baseline={pins:[]},parent={kind:'model-full-parent'},source_rule={profile:'model-retained-source',expected_ids:[id]};
  f.write('source/request.json',{version:1,operation:'retained-land-source-premises-v1',executed_code,baseline,parent,source_rule});
  const sr=pin('source/request.json',f.commit());
  f.write('source/facts.json',{operation:'retained-land-source-premises-v1',request:sr,executed_code,baseline,parent,source_rule,components:1});
  let sf=pin('source/facts.json',f.commit());
  const aliases=[],absent='f'.repeat(40),beforePublication=sf.commit;let stalePublication,published;
  if(completedAliases){
   f.write('source/publication.json',{stale:true});stalePublication=f.commit();
   f.write('source/publication.json',{complete:true});const decoded=Buffer.from('whole synthetic inventory\n');
   f.write('source/inventory.jsonl.gz',gzipSync(decoded));published=f.commit();sf={...sf,commit:absent};
   for(const item of [sf,pin('source/publication.json',published),{...pin('source/inventory.jsonl.gz',published),uncompressed_bytes:decoded.length,uncompressed_sha256:sha(decoded)}]){
    const q={...item,commit:absent},original={kind:'completed-inventory-body',mode:q.mode,path:'.cache/native-grid-candidates/completed-source/'+path.basename(q.path),bytes:q.bytes,sha256:q.sha256};
    if(q.uncompressed_bytes!==undefined)Object.assign(original,{uncompressed_bytes:q.uncompressed_bytes,uncompressed_sha256:q.uncompressed_sha256});
    aliases.push({original,published:q});
   }
  }
  f.write('native/manifest.json',{method:'model-native-method'});const mp=pin('native/manifest.json',f.commit());baseline.pins=[mp];
  // Source baseline belongs to its original issued vintage, which must also be
  // present unchanged in its facts. The proposal has its independently bound
  // native baseline; these are not asserted to be one source authority.
  const additive={scope_ids:[id],inputs:[sr,...(completedAliases?aliases.map(a=>a.original):[sf])],source_request_path:sr.path,facts_path:aliases[0]?.original.path??sf.path,manifest_path:mp.path,...(completedAliases?{publication_path:aliases[1].original.path,inventory_path:aliases[2].original.path}:{})};
  const request={version:1,operation:'unactivated-additive-native-batch-v1',executed_code,baseline,parent,additive};
  f.write('native/request.json',request);const nr=pin('native/request.json',f.commit());
  const preimage={version:3,source_profile:source_rule.profile,source_rule,representation:'literal-base-or-complete-additions',native_method:'model-native-method',executed_code};
  const row={component_id:id,disposition:'zero-cell',target_id:'owner:a',pixelIndex:1,geometry,geometry_sha256:valueSha(geometry),base_geometry_sha256:'2'.repeat(64),native_cells:0,source_receipt_sha256:sf.sha256};
  const ledger={version:1,kind:'native-additive-repair-ledger-v1',scope_ids:[id],rows:[row],rule_sha256:valueSha(preimage)};
  const native={operation:request.operation,executed_code,baseline,parent,request:nr,source_predecessor:additive};
  f.write('native/facts.json',native);f.write('native/ledger.json',ledger);const head=f.commit();
  const pins={ledger:pin('native/ledger.json',head),native_facts:pin('native/facts.json',head),native_manifest:mp,native_request:nr,source_facts:sf,source_request:sr};
  const open=()=>new ImmutableReader(f.repo,head);
  const reader=open(),calls=[],git=reader.git.bind(reader);reader.git=(...args)=>{calls.push(args);return git(...args);};
  const result=readOriginalRuleAuthority(reader,pins,aliases);assert.equal(result.rule_sha256,valueSha(preimage));assert.equal(result.ledger.rows[0].native_cells,0);
  if(completedAliases){
   assert.deepEqual(result.source_output_aliases,aliases,'Issued published tuples stay unchanged');
   assert.ok(!calls.some(args=>args.includes('fetch')||args.includes('ls-tree')&&args.includes(absent)),'Exact current aliases need no origin metadata transport');
   for(const commit of [beforePublication,stalePublication]){
    const wrong=structuredClone(aliases);wrong[1].published.commit=commit;
    assert.throws(()=>readOriginalRuleAuthority(open(),pins,wrong),/whole ordinary Git input|actual Git identity differs/,'A known missing/mismatched origin never falls back to current');
   }
   for(const [key,value]of [['mode','100755'],['blob','0'.repeat(40)],['bytes',0],['sha256','0'.repeat(64)]]){
    const wrong=structuredClone(aliases);wrong[1].published[key]=value;
    assert.throws(()=>readOriginalRuleAuthority(open(),pins,wrong),/whole encoded\/decoded pins differ|actual Git identity differs/);
   }
   f.write('source/publication.json',{changed:true});const changed=f.commit();
   assert.throws(()=>readOriginalRuleAuthority(new ImmutableReader(f.repo,changed),pins,aliases),/actual Git identity differs/);
   const known=structuredClone(aliases);known[1].published.commit=published;
   assert.equal(readOriginalRuleAuthority(new ImmutableReader(f.repo,changed),pins,known).rule_sha256,valueSha(preimage),'Known exact original wins over a changed current path');
   fs.unlinkSync(path.join(f.repo,'source/publication.json'));const missingCurrent=f.commit();
   assert.throws(()=>readOriginalRuleAuthority(new ImmutableReader(f.repo,missingCurrent),pins,aliases),/whole ordinary Git input/);
  }
  const wrong=structuredClone(pins);wrong.source_request.sha256='0'.repeat(64);assert.throws(()=>readOriginalRuleAuthority(open(),wrong),/Whole immutable input differs/);
  f.write('native/facts.json',{...native,executed_code:[]});const rebound=f.commit();assert.throws(()=>readOriginalRuleAuthority(new ImmutableReader(f.repo,rebound),{...pins,native_facts:pin('native/facts.json',rebound)}),/executed code differs/);
  const missing={...pins};delete missing.source_request;assert.throws(()=>readOriginalRuleAuthority(open(),missing),/exact original rule body roster/);
 }finally{f.cleanup();}
});


test('renewed immutable artifact entry binds complete catalogue and independent authority',()=>{
 const directory=path.join(root,'test/fixtures/artifact-authority/latest-999db');
 const rows=JSON.parse(fs.readFileSync(path.join(directory,'original-inputs.json'))).pins;
 const read=name=>fs.readFileSync(path.join(directory,name));
 for(const p of rows)assert.equal(sha(read(p.copy)),p.sha256);
 const certificate=JSON.parse(read('certificate.json')),catalogue=JSON.parse(gunzipSync(read('catalogue.json.gz'))),registry=JSON.parse(gunzipSync(read('registry.json.gz')));
 assert.deepEqual(validateReleaseCatalogue(certificate,catalogue,registry),{inline_roles:137,release_products:343,complete_roles:480});
 const reorderedCatalogue=structuredClone(certificate),catalogueInput=reorderedCatalogue.application_inputs.find(p=>p.path===certificate.release_product_catalogue.path);
 const catalogueIndex=reorderedCatalogue.application_inputs.indexOf(catalogueInput);
 reorderedCatalogue.application_inputs[catalogueIndex]=Object.fromEntries(Object.entries(catalogueInput).reverse());
 assert.notEqual(JSON.stringify(reorderedCatalogue.application_inputs[catalogueIndex]),JSON.stringify(catalogueInput));
 assert.deepEqual(validateReleaseCatalogue(reorderedCatalogue,catalogue,registry),{inline_roles:137,release_products:343,complete_roles:480});
 for(const [change,pattern]of [
  [(c,p)=>p.products.pop(),/Incomplete qualified/],
  [(c,p)=>p.products[1]=structuredClone(p.products[0]),/Duplicate/],
  [(c,p)=>p.products[0].path='foreign/product.gz',/ordered path/],
  [(c,p)=>[p.products[0],p.products[1]]=[p.products[1],p.products[0]],/ordered path/],
  [(c,p)=>p.products[0].sha256='0'.repeat(64),/encoded\/payload/],
  [(c,p)=>p.products[0].decoded_sha256='0'.repeat(64),/encoded\/payload/],
  [(c,p)=>delete p.products[0].decoded_bytes,/Incomplete whole/],
  [(c,p)=>p.products[0].decoded_bytes=1.5,/decoded role/],
  [(c)=>c.application_inputs=c.application_inputs.filter(p=>p.path!==c.release_product_catalogue.path),/exact inline/],
  [(c)=>c.application_inputs[1]=structuredClone(c.application_inputs[0]),/Duplicate/]
 ]) {const c=structuredClone(certificate),p=structuredClone(catalogue);change(c,p);assert.throws(()=>validateReleaseCatalogue(c,p,registry),pattern);}
 const f=fixture();try{
  for(const p of rows)f.write(p.path,read(p.copy));
  const original=path.join(root,'test/fixtures/artifact-authority/original-999');
  for(const p of JSON.parse(fs.readFileSync(path.join(original,'original-inputs.json'))).pins)f.write(p.path,fs.readFileSync(path.join(original,p.copy)));const head=f.commit();
  const selection=JSON.parse(read('selection.json')),manifest=JSON.parse(read('manifest.json'));
  const open=()=>new ImmutableReader(f.repo,head);
  const positive=readArtifactConsumption(open(),selection,manifest);assert.equal(positive.review_id,6079096820);assert.equal(positive.releaseCatalogue.complete_roles,480);
  const reordered=structuredClone(selection);reordered.selected_geography=Object.fromEntries(Object.entries(reordered.selected_geography).reverse());
  assert.notEqual(JSON.stringify(reordered.selected_geography),JSON.stringify(selection.selected_geography));
  assert.deepEqual(reordered.selected_geography,selection.selected_geography);
  assert.equal(readArtifactConsumption(open(),reordered,manifest).review_id,positive.review_id);
  for(const [change,pattern]of [
   [s=>s.artifact_consumption.certificate.sha256='0'.repeat(64),/differs/],
   [s=>s.artifact_consumption.review.sha256='0'.repeat(64),/independently registered/],
   [s=>s.artifact_consumption.review.sha256='79024f6fd9335b0ad9da0ed936f5eabc600188f6176d9f953ceb006946626dbd',/Historical artifact authority/],
   [s=>s.artifact_consumption.certificate.mode='100755',/whole artifact authority pin/],
   [s=>s.artifact_consumption.certificate.bytes--,/whole mode\/size differs/],
   [s=>s.sha256='0'.repeat(64),/Typed independent/],
   [s=>s.selected_geography.sha256='0'.repeat(64),/Selected source\/policy/],
   [s=>s.selected_geography.bytes=String(s.selected_geography.bytes),/Selected source\/policy/],
   [s=>delete s.selected_geography.kind,/Selected source\/policy/],
   [s=>s.selected_geography.foreign=null,/Selected source\/policy/],
   [s=>s.release_id='geography:foreign',/native\/release/],
   [s=>s.artifact_consumption.approved=true,/Unsupported artifact-consumption/]
  ]){const s=structuredClone(selection);change(s);assert.throws(()=>readArtifactConsumption(open(),s,manifest),pattern);}
  // Equal parsed values cannot authenticate differently serialized external bytes.
  const originalBytes=read('certificate.json'),reorderedBytes=Buffer.from(JSON.stringify(Object.fromEntries(Object.entries(certificate).reverse()),null,2)+'\n');
  assert.equal(reorderedBytes.length,originalBytes.length);assert.notEqual(sha(reorderedBytes),sha(originalBytes));
  assert.deepEqual(JSON.parse(reorderedBytes),certificate);
  f.write(selection.artifact_consumption.certificate.path,reorderedBytes);const changedBytes=f.commit();
  assert.throws(()=>readArtifactConsumption(new ImmutableReader(f.repo,changedBytes),selection,manifest),/Whole immutable input differs/);
 }finally{f.cleanup();}
});

test('registered 533-role authority derives complete whole-input custody',()=>{
 const directory=path.join(root,'test/fixtures/artifact-authority/latest-e177');
 const read=name=>fs.readFileSync(path.join(directory,name));
 const rows=JSON.parse(read('original-inputs.json')).pins;
 for(const p of rows)assert.equal(sha(read(p.copy)),p.sha256);
 const certificate=JSON.parse(read('certificate.json')),code=JSON.parse(read('code.json')),qualification=JSON.parse(gunzipSync(read('qualification.json.gz'))),catalogue=JSON.parse(gunzipSync(read('catalogue.json.gz'))),registry=JSON.parse(gunzipSync(read('registry.json.gz')));
 assert.deepEqual(validateReleaseCatalogue(certificate,catalogue,registry),{inline_roles:190,release_products:343,complete_roles:533});
 const custody=validateArtifactSourceMetadata(certificate,code,qualification,{entryProfiles:true});
 assert.equal(custody.source_critical_roles,33);assert.equal(custody.candidate_code_executed,false);
 assert.equal(custody.entry_profiles['scripts/run-integration-tests.mjs'].entry_critical_roles,1);
 for(const [change,pattern]of [
  [(c,a)=>a.critical_files[1]=structuredClone(a.critical_files[0]),/duplicate critical/],
  [(c,a)=>a.critical_files[0].sha256='0'.repeat(64),/omitted\/rebound/],
  [(c,a)=>delete a.entry_roles['scripts/run-integration-tests.mjs'],/actual entry profile/],
  [(c,a)=>delete a.entry_critical_files['scripts/build-static-inner.mjs'],/entry-specific source/],
  [(c,a)=>a.entry_critical_files['scripts/build-hosted-inner.mjs'][0].bytes++,/omitted\/rebound/],
  [(c,a)=>a.entry_roles['scripts/run-integration-tests.mjs'].actual_current_execution_wrappers.push('../foreign'),/wrapper profile/],
  [(c,a,q)=>q.source_policy.water_status='approved',/source policy/],
  [(c,a,q)=>q.complete_phase_inventory[0].runs.pop(),/qualification runs/],
  [(c,a,q)=>q.complete_phase_inventory[0].runs[0].actual_terminal.qualified=false,/Unqualified/],
  [(c)=>c.application_inputs=c.application_inputs.filter(p=>p.path!==code.critical_files[0].path),/omitted\/rebound/]
 ]){const c=structuredClone(certificate),a=structuredClone(code),q=structuredClone(qualification);change(c,a,q);assert.throws(()=>validateArtifactSourceMetadata(c,a,q,{entryProfiles:true}),pattern);}
 const f=fixture();try{
  for(const p of rows)f.write(p.path,read(p.copy));let head=f.commit();
  const selection=JSON.parse(read('selection.json')),manifest=JSON.parse(read('manifest.json'));
  const reader=new ImmutableReader(f.repo,head),result=readArtifactConsumption(reader,selection,manifest);
  assert.equal(result.review_id,6080211722);assert.equal(result.releaseCatalogue.complete_roles,533);assert.equal(result.sourceCustody.source_critical_roles,33);
  assert.equal([...reader.inventory.values()].filter(p=>p.whole_body_consumed===true).length,6);
  // The original whole certificate/GET binds all inline metadata. Coherently
  // editing a metadata body cannot mint a new accepted certificate authority.
  for(const [copy,change]of [
   ['certificate.json',c=>c.application_inputs.pop()],
   ['certificate.json',c=>c.application_inputs[1]=structuredClone(c.application_inputs[0])],
   ['certificate.json',c=>c.application_inputs[1].sha256='0'.repeat(64)],
   ['code.json',c=>c.critical_files.pop()],
   ['code.json',c=>delete c.entry_critical_files['scripts/run-integration-tests.mjs']],
   ['review.json',c=>c.user.id++],
  ]){const pin=rows.find(p=>p.copy===copy),value=JSON.parse(read(copy));change(value);f.write(pin.path,value);head=f.commit();assert.throws(()=>readArtifactConsumption(new ImmutableReader(f.repo,head),selection,manifest),/differs/);f.write(pin.path,read(copy));head=f.commit();}
  const codePin=rows.find(p=>p.copy==='code.json');fs.unlinkSync(path.join(f.repo,codePin.path));head=f.commit();assert.throws(()=>readArtifactConsumption(new ImmutableReader(f.repo,head),selection,manifest),/whole ordinary Git input/);f.write(codePin.path,read('code.json'));head=f.commit();
 }finally{f.cleanup();}
});


test('Cloudflare fourth entry is explicit and cannot reinterpret historical profile shapes',()=>{
 const directory=path.join(root,'test/fixtures/artifact-authority/latest-e177');
 const read=name=>fs.readFileSync(path.join(directory,name));
 const certificate=JSON.parse(read('certificate.json')),code=JSON.parse(read('code.json')),qualification=JSON.parse(gunzipSync(read('qualification.json.gz')));
 const cloudflare='scripts/build-cloudflare-inner.mjs';
 // Model schema control only: the final registered authority must supply its
 // actual complete Cloudflare closure; this does not mint a review or source.
 code.entry_roles[cloudflare]=structuredClone(code.entry_roles['scripts/build-static-inner.mjs']);
 code.entry_critical_files[cloudflare]=structuredClone(code.entry_critical_files['scripts/build-static-inner.mjs']);
 assert.throws(()=>validateArtifactSourceMetadata(certificate,code,qualification,{entryProfiles:true}),/actual entry profile/);
 assert.throws(()=>validateArtifactSourceMetadata(certificate,code,qualification,{cloudflareProfile:true}),/explicit entry-specific/);
 const result=validateArtifactSourceMetadata(certificate,code,qualification,{entryProfiles:true,cloudflareProfile:true});
 assert.equal(result.candidate_code_executed,false);assert.ok(result.entry_profiles[cloudflare]);
 delete code.entry_critical_files[cloudflare];
 assert.throws(()=>validateArtifactSourceMetadata(certificate,code,qualification,{entryProfiles:true,cloudflareProfile:true}),/entry-specific source/);
});


for(const [title,relative]of [['genuine Cloudflare authority retains complete 533 roles and four explicit entry profiles','test/fixtures/artifact-authority/latest-8832354'],['renewed installer authority retains genuine complete 533-role custody','test/fixtures/artifact-authority/authority-121149']])test(title,()=>{
 const directory=path.join(root,relative);
 const read=name=>fs.readFileSync(path.join(directory,name));
 const rows=JSON.parse(read('original-inputs.json')).pins;
 for(const p of rows)assert.equal(sha(read(p.copy)),p.sha256);
 const certificate=JSON.parse(read('certificate.json')),code=JSON.parse(read('code.json')),qualification=JSON.parse(gunzipSync(read('qualification.json.gz'))),catalogue=JSON.parse(gunzipSync(read('catalogue.json.gz'))),registry=JSON.parse(gunzipSync(read('registry.json.gz')));
 assert.deepEqual(validateReleaseCatalogue(certificate,catalogue,registry),{inline_roles:190,release_products:343,complete_roles:533});
 const custody=validateArtifactSourceMetadata(certificate,code,qualification,{entryProfiles:true,cloudflareProfile:true});
 assert.equal(custody.entry_profiles['scripts/build-cloudflare-inner.mjs'].entry_critical_roles,3);
 assert.equal(custody.entry_profiles['scripts/build-cloudflare-inner.mjs'].declared_current_role_groups.actual_current_execution_wrappers.length,58);
 assert.throws(()=>validateArtifactSourceMetadata(certificate,code,qualification,{entryProfiles:true}),/actual entry profile/);
 assert.equal(custody.source_critical_roles,33);assert.equal(custody.candidate_code_executed,false);
 assert.equal(custody.entry_profiles['scripts/run-integration-tests.mjs'].entry_critical_roles,1);
 for(const [change,pattern]of [
  [(c,a)=>a.critical_files[1]=structuredClone(a.critical_files[0]),/duplicate critical/],
  [(c,a)=>a.critical_files[0].sha256='0'.repeat(64),/omitted\/rebound/],
  [(c,a)=>delete a.entry_roles['scripts/run-integration-tests.mjs'],/actual entry profile/],
  [(c,a)=>delete a.entry_roles['scripts/build-cloudflare-inner.mjs'],/actual entry profile/],
  [(c,a)=>delete a.entry_critical_files['scripts/build-cloudflare-inner.mjs'],/entry-specific source/],
  [(c,a)=>a.entry_roles['scripts/build-cloudflare-inner.mjs'].actual_current_execution_wrappers.push('../foreign'),/wrapper profile/],
  [(c,a)=>delete a.entry_critical_files['scripts/build-static-inner.mjs'],/entry-specific source/],
  [(c,a)=>a.entry_critical_files['scripts/build-hosted-inner.mjs'][0].bytes++,/omitted\/rebound/],
  [(c,a)=>a.entry_roles['scripts/run-integration-tests.mjs'].actual_current_execution_wrappers.push('../foreign'),/wrapper profile/],
  [(c,a,q)=>q.source_policy.water_status='approved',/source policy/],
  [(c,a,q)=>q.complete_phase_inventory[0].runs.pop(),/qualification runs/],
  [(c,a,q)=>q.complete_phase_inventory[0].runs[0].actual_terminal.qualified=false,/Unqualified/],
  [(c)=>c.application_inputs=c.application_inputs.filter(p=>p.path!==code.critical_files[0].path),/omitted\/rebound/]
 ]){const c=structuredClone(certificate),a=structuredClone(code),q=structuredClone(qualification);change(c,a,q);assert.throws(()=>validateArtifactSourceMetadata(c,a,q,{entryProfiles:true,cloudflareProfile:true}),pattern);}
 const f=fixture();try{
  for(const p of rows)f.write(p.path,read(p.copy));let head=f.commit();
  const selection=JSON.parse(read('selection.json')),manifest=JSON.parse(read('manifest.json'));
  const reader=new ImmutableReader(f.repo,head),result=readArtifactConsumption(reader,selection,manifest);
  assert.equal(result.review_id,JSON.parse(read('review.json')).id);assert.equal(result.releaseCatalogue.complete_roles,533);assert.equal(result.sourceCustody.source_critical_roles,33);
  assert.equal([...reader.inventory.values()].filter(p=>p.whole_body_consumed===true).length,6);
  // The original whole certificate/GET binds all inline metadata. Coherently
  // editing a metadata body cannot mint a new accepted certificate authority.
  for(const [copy,change]of [
   ['certificate.json',c=>c.application_inputs.pop()],
   ['certificate.json',c=>c.application_inputs[1]=structuredClone(c.application_inputs[0])],
   ['certificate.json',c=>c.application_inputs[1].sha256='0'.repeat(64)],
   ['code.json',c=>c.critical_files.pop()],
   ['code.json',c=>delete c.entry_critical_files['scripts/run-integration-tests.mjs']],
   ['review.json',c=>c.user.id++],
  ]){const pin=rows.find(p=>p.copy===copy),value=JSON.parse(read(copy));change(value);f.write(pin.path,value);head=f.commit();assert.throws(()=>readArtifactConsumption(new ImmutableReader(f.repo,head),selection,manifest),/differs/);f.write(pin.path,read(copy));head=f.commit();}
  const codePin=rows.find(p=>p.copy==='code.json');fs.unlinkSync(path.join(f.repo,codePin.path));head=f.commit();assert.throws(()=>readArtifactConsumption(new ImmutableReader(f.repo,head),selection,manifest),/whole ordinary Git input/);f.write(codePin.path,read('code.json'));head=f.commit();
 }finally{f.cleanup();}
});


test('separate authenticated native stages preserve all rows and relinquish containing buffers',()=>{
 const f=fixture();try{
  const before=f.select([[[0,2,1]],[[1,3,2]],[],[]]);
  const after=f.select([[[0,3,1]],[[1,4,2]],[],[]],{transport:true});
  const result=inspectSelected(f.repo,before,after);
  assert.equal(result.status,'no-new-native-loss');assert.equal(result.lost_or_reassigned_cells,0);
  assert.equal(result.affected_rows,2);assert.equal(result.phases.length,1);
  const phase=result.phases[0];assert.deepEqual(phase.baseline.rows,[0,1]);assert.deepEqual(phase.candidate.rows,[0,1]);
  assert.equal(phase.baseline.whole_parts.length,1);assert.equal(phase.candidate.whole_parts.length,1);
  for(const side of [phase.baseline,phase.candidate])assert.ok(side.whole_inputs.every(p=>p.whole_body_consumed===true&&sha(execFileSync('git',['-C',f.repo,'cat-file','blob',p.git_blob_oid]))===p.sha256));
  const lost=f.select([[[0,1,1]],[[1,4,2]],[],[]],{transport:true});
  assert.equal(inspectSelected(f.repo,before,lost).lost_or_reassigned_cells,1);
 }finally{f.cleanup();}
});

test('actual whole-part acquisition reads once for several rows and rejects incomplete or forged carry',()=>{
 const f=fixture();try{
  const version=f.select([[[0,2,1]],[[1,3,2]],[[0,1,1]],[]],{transport:true});
  const reader=new ImmutableReader(f.repo,version),snapshot=loadSelection(reader);
  assert.ok(snapshot.acquisitionPhases.every(phase=>phase.inputs.every(pin=>pin.whole_body_consumed===true&&typeof pin.sha256==='string')));
  const declared=[...reader.inventory.values()].filter(pin=>pin.whole_body_consumed!==true);
  assert.ok(declared.length>0,'whole native descriptors have not yet been consumed');
  assert.ok(declared.every(pin=>!snapshot.acquisitionPhases.some(phase=>phase.inputs.some(input=>input.commit===pin.commit&&input.path===pin.path))));
  const table=loadNativeRowTable(snapshot);let bodies=0;const actual=reader.read.bind(reader);
  reader.read=(name,options)=>{if(name.includes('/bank/group/'))bodies++;return actual(name,options);};
  const product=acquireNativeRows(snapshot,table,[0,1,2]);
  assert.equal(bodies,product.custody.whole_inputs.length); // One containing roster, not three row decodes.
  assert.equal(product.custody.whole_parts.length,1);assert.equal(product.words.length,9);
  assert.deepEqual([...product.words],[0,2,1,1,3,2,0,1,1]);validateNativeRowCarry(product,snapshot,[0,1,2]);
  assert.throws(()=>validateNativeRowCarry({...product},snapshot,[0,1,2]),/carry/);
  assert.throws(()=>validateNativeRowCarry(product,snapshot,[0,2]),/carry/);
  product.words[2]=2;assert.throws(()=>validateNativeRowCarry(product,snapshot,[0,1,2]),/carry/);product.words[2]=1;
  product.custody.whole_inputs=[];assert.throws(()=>validateNativeRowCarry(product,snapshot,[0,1,2]),/carry/);
  assert.throws(()=>acquireNativeRows(snapshot,table,[0,0]),/duplicate/);
  assert.throws(()=>acquireNativeRows(snapshot,table,[4]),/foreign/);
  assert.throws(()=>acquireNativeRows({...snapshot},table,[0]),/authenticated/);
  const altered=table.slice();assert.throws(()=>acquireNativeRows(snapshot,altered,[0]),/authenticated/);
  table[0]++;assert.throws(()=>acquireNativeRows(snapshot,table,[0]),/unchanged/);
 }finally{f.cleanup();}
});

test('forged native carried projection refuses before any whole body opens',()=>{
 const f=fixture();try{
  const version=f.select([[[0,2,1]],[[1,3,2]],[],[]],{transport:true});
  const reader=new ImmutableReader(f.repo,version),snapshot=loadSelection(reader);const table=loadNativeRowTable(snapshot);
  let opens=0;const actual=reader.git.bind(reader);reader.git=(...args)=>{if(args[0]==='cat-file'&&args[1]==='blob')opens++;return actual(...args);};
  assert.throws(()=>acquireNativeRows(snapshot,table,[0,1],{carry:{rows:new Uint32Array([0,1])}}),/authenticated native carry/);assert.equal(opens,0);
 }finally{f.cleanup();}
});


test('one complete row spanning two whole native members retains all intervals and custody',()=>{
 const f=fixture();try{
  f.select([[[0,1,1],[1,2,2]],[],[],[]]);
  const manifestPath='data/canonical-grid/fixture/manifest.json',manifest=JSON.parse(fs.readFileSync(path.join(f.repo,manifestPath)));
  const halves=[Uint32Array.from([4,0]),Uint32Array.from([9,1])];
  manifest.parts=[manifest.parts.find(p=>p.kind==='rows'),...halves.map((words,i)=>{
   const encoded=gzipSync(shuffleOwnershipBytes(words)),name=`native-v1/ownership/runs-${i*2}.bin.gz`;f.write('data/canonical-grid/fixture/'+name,encoded);
   return {kind:'runs',offset:i*2,words:2,path:name,bytes:encoded.length,sha256:sha(encoded),decoded_bytes:8,decoded_sha256:sha(Buffer.from(words.buffer)),encoding:'byte-shuffle'};
  })];
  const raw=f.write(manifestPath,manifest),selection=JSON.parse(fs.readFileSync(path.join(f.repo,'data/ownership-selection.json')));selection.sha256=sha(raw);
  const products=[{path:'manifest.json',bytes:raw.length,sha256:sha(raw)},...manifest.parts];
  const receipt={method:manifest.method,checked_rows:4,checked_cells:16,unchecked_cells:0,checked_runs:manifest.runWords/2,installation_ready:false,products,two_run_products:products.length,run_one_sha256:sha(Buffer.from(JSON.stringify(products))),run_two_sha256:sha(Buffer.from(JSON.stringify(products)))};
  const receiptRaw=f.write('coordination/engineering/fixture/receipt.json',receipt),proofCommit=f.commit();
  f.write('scripts/native-ownership/verified-candidates.json',{version:1,candidates:{[sha(raw)]:{commit:proofCommit,path:'coordination/engineering/fixture/receipt.json',sha256:sha(receiptRaw),role:'reviewed-exhaustive-native-rule-comparison',installation_approval:false}}});
  f.write('data/ownership-selection.json',selection);const version=f.commit();
  const reader=new ImmutableReader(f.repo,version),snapshot=loadSelection(reader);const table=loadNativeRowTable(snapshot);
  const initial=acquireNativeRows(snapshot,table,[0]);assert.equal(initial.custody.member_phases.length,2);assert.deepEqual([...initial.words],[0,1,1,1,2,2]);
  let memberReads=0;const actual=reader.read.bind(reader);reader.read=(name,options)=>{if(name.includes('/runs-'))memberReads++;return actual(name,options);};
  const complete=acquireNativeRows(snapshot,table,[0]);assert.equal(memberReads,2);assert.equal(complete.custody.member_phases.length,2);validateNativeRowCarry(complete,snapshot,[0]);assert.deepEqual([...complete.words],[0,1,1,1,2,2]);
  assert.equal(complete.custody.whole_inputs.length,2);assert.ok(complete.custody.whole_inputs.every(p=>p.whole_body_consumed===true));
 }finally{f.cleanup();}
});


test('actual whole encoded interval outside the original native grid refuses during projection',()=>{
 const f=fixture();try{
  f.select([[[0,1,1]],[],[],[]]);
  const manifestPath='data/canonical-grid/fixture/manifest.json',manifest=JSON.parse(fs.readFileSync(path.join(f.repo,manifestPath)));
  manifest.size=3;
  const rowWords=Uint32Array.from([0,1,1,0,1,0]),rowEncoded=gzipSync(shuffleOwnershipBytes(rowWords)),rowPin=manifest.parts.find(p=>p.kind==='rows');
  Object.assign(rowPin,{words:6,bytes:rowEncoded.length,sha256:sha(rowEncoded),decoded_bytes:24,decoded_sha256:sha(Buffer.from(rowWords.buffer))});f.write('data/canonical-grid/fixture/'+rowPin.path,rowEncoded);
  const words=Uint32Array.from([6,3]),encoded=gzipSync(shuffleOwnershipBytes(words)),pin=manifest.parts.find(p=>p.kind==='runs');
  Object.assign(pin,{bytes:encoded.length,sha256:sha(encoded),decoded_bytes:8,decoded_sha256:sha(Buffer.from(words.buffer))});
  f.write('data/canonical-grid/fixture/'+pin.path,encoded);
  const raw=f.write(manifestPath,manifest),selection=JSON.parse(fs.readFileSync(path.join(f.repo,'data/ownership-selection.json')));selection.sha256=sha(raw);
  const products=[{path:'manifest.json',bytes:raw.length,sha256:sha(raw)},...manifest.parts];
  const receipt={method:manifest.method,checked_rows:3,checked_cells:9,unchecked_cells:0,checked_runs:1,installation_ready:false,products,two_run_products:products.length,run_one_sha256:sha(Buffer.from(JSON.stringify(products))),run_two_sha256:sha(Buffer.from(JSON.stringify(products)))};
  const receiptRaw=f.write('coordination/engineering/fixture/receipt.json',receipt),proofCommit=f.commit();
  f.write('scripts/native-ownership/verified-candidates.json',{version:1,candidates:{[sha(raw)]:{commit:proofCommit,path:'coordination/engineering/fixture/receipt.json',sha256:sha(receiptRaw),role:'reviewed-exhaustive-native-rule-comparison',installation_approval:false}}});
  f.write('data/ownership-selection.json',selection);const version=f.commit();
  const reader=new ImmutableReader(f.repo,version),snapshot=loadSelection(reader);const table=loadNativeRowTable(snapshot);
  assert.throws(()=>acquireNativeRows(snapshot,table,[0]),/original grid domain/);
 }finally{f.cleanup();}
});


test('complete zero-interval row retains authenticated empty projection and carry',()=>{
 const f=fixture();try{
  const version=f.select([[],[[0,1,1]],[],[]]);
  const reader=new ImmutableReader(f.repo,version),snapshot=loadSelection(reader);const table=loadNativeRowTable(snapshot);
  let opens=0;const actual=reader.git.bind(reader);reader.git=(...args)=>{if(args[0]==='cat-file'&&args[1]==='blob')opens++;return actual(...args);};
  const empty=acquireNativeRows(snapshot,table,[0]);
  assert.equal(opens,0);assert.equal(empty.words.length,0);assert.equal(empty.custody.member_phases.length,0);assert.deepEqual(empty.custody.whole_inputs,[]);assert.deepEqual([...empty.offsets],[0,0]);
  validateNativeRowCarry(empty,snapshot,[0]);
  const next=acquireNativeRows(snapshot,table,[0],{carry:empty});validateNativeRowCarry(next,snapshot,[0]);
  assert.equal(opens,0);assert.deepEqual([...next.words],[]);assert.deepEqual(next.custody.whole_inputs,[]);
 }finally{f.cleanup();}
});


test('immutable reader distinguishes actual whole consumption from descriptors and preserves invocation identity',()=>{
 const f=fixture();try{
  const body=f.write('reader/complete.json',{whole:'actual committed body'}),version=f.commit();
  const reader=new ImmutableReader(f.repo,version),other=new ImmutableReader(f.repo,version);
  assert.ok(Object.isFrozen(reader.invocation));assert.notEqual(reader.invocation,other.invocation);
  const shared=new ImmutableReader(f.repo,version,{invocation:reader.invocation});assert.equal(shared.invocation,reader.invocation);
  const pin=reader.descriptor('reader/complete.json');assert.equal(pin.whole_body_consumed,undefined);assert.equal(pin.sha256,undefined);
  assert.throws(()=>reader.read('reader/complete.json',{expected:'0'.repeat(64)}),/Whole immutable input differs/);
  assert.equal(pin.whole_body_consumed,undefined,'a rejected body must not establish consumed custody');
  assert.deepEqual(reader.read('reader/complete.json',{expected:sha(body)}),body);
  assert.equal(pin.whole_body_consumed,true);assert.equal(pin.sha256,sha(body));assert.equal(pin.bytes,body.length);
  assert.equal(pin.git_blob_oid,f.git('rev-parse',version+':reader/complete.json'));assert.equal(pin.mode,'100644');
  assert.throws(()=>reader.read('../reader/complete.json'),/Unsafe immutable path/);
  const actual=other.git.bind(other);other.git=(...args)=>args[0]==='cat-file'&&args[1]==='blob'?body.subarray(1):actual(...args);
  assert.throws(()=>other.read('reader/complete.json'),/Whole immutable input differs/);
  assert.equal(other.inventory.get(version+':reader/complete.json').whole_body_consumed,undefined);

 }finally{f.cleanup();}
});


function selectedMetadataFixture(){
 const owners=[{index:1,id:'member',province_id:'old',province_index:2},{index:2,id:'retained',province_id:'old',province_index:2},{index:3,id:'existing',province_id:'new',province_index:1}];
 const f=fixture({ownerRows:owners});
 const pin=(name,version)=>{const raw=execFileSync('git',['-C',f.repo,'show',version+':'+name]);const [mode,,oid]=f.git('ls-tree',version,'--',name).split(/[ \t]/);return {commit:version,path:name,mode,git_blob_oid:oid,bytes:raw.length,sha256:sha(raw)};};
 const read=p=>execFileSync('git',['-C',f.repo,'show',p.commit+':'+p.path]);
 const geometry={type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,0]]]};
 const features=owners.map(owner=>({type:'Feature',id:owner.id,properties:{id:owner.id,name:owner.id,parent_id:owner.province_id,metadata:{source_id:'literal original',framework_match:{id:'fallback',overlap:.8}}},geometry}));
 for(const feature of features){feature.properties.reference_owner='Recorded winner';Object.assign(feature.properties.metadata,{reference_polity:'Stale alias',reference_owner_id:'owner:Q1',reference_owner_evidence:{winner:{owner_id:'owner:Q1',name:'Recorded winner',share:.75}},semantic_review:{status:'open'}});}
 const units=[{id:'c',name:'C',level:'continent',parent_id:null},{id:'s',name:'S',level:'subcontinent',parent_id:'c'},
  {id:'r',name:'R',level:'region',parent_id:'s'},{id:'a',name:'A',level:'area',parent_id:'r'},
  {id:'old',name:'Old',level:'province',parent_id:'a',metadata:{child_count:2}},{id:'new',name:'New',level:'province',parent_id:'a',metadata:{child_count:1}}];
 const afterUnits=structuredClone(units);afterUnits[4].metadata.child_count=1;afterUnits[5].metadata.child_count=2;
 f.write('data/geography/fixture.json',{type:'FeatureCollection',features});const hierarchyBefore=f.write('data/hierarchy.json',units),before=f.commit();
 const native={id:'geography:review:fixture',footprints_sha256:'b'.repeat(64),hierarchy_sha256:sha(hierarchyBefore)};
 const nativeHead=f.select([[[0,1,1]],[[2,3,2]],[],[]],{reference:native});
 const selection=JSON.parse(fs.readFileSync(path.join(f.repo,'data/ownership-selection.json'))),manifest=JSON.parse(fs.readFileSync(path.join(f.repo,selection.manifest_path)));
 const bank={version:1,kind:'complete-world-index-with-exact-encoded-overrides',release_id:native.id,native_manifest_sha256:selection.sha256,footprints_sha256:native.footprints_sha256,locations:owners.length,world_index:pin('data/world-index.json',before),unchanged_files:[pin('data/geography/fixture.json',before)],overrides:[]};
 const bankRaw=f.write('source/bank.json',bank),selected={...selection,selected_geography:{version:1,kind:bank.kind,path:'source/bank.json',bytes:bankRaw.length,sha256:sha(bankRaw)}};
 const setRelease=releases=>{const raw=f.write('data/geographic-releases/selected.json.gz',gzipSync(Buffer.from(JSON.stringify({releases}))));f.write('data/geographic-releases/current-manifest.json',{path:'selected.json.gz',sha256:sha(raw)});};
 setRelease([native]);f.write('data/ownership-selection.json',selected);const base=f.commit();
 const afterProperties=structuredClone(features[0].properties);afterProperties.parent_id='new';afterProperties.metadata.reference_corrections=[{id:'member',action:'reparent',current_name:'member',current_parent_id:'old',new_parent_id:'new',rationale:'Exact inspected source parent.',evidence:[{url:'https://example.org/source',title:'Inspected source',inspected_fact:'The original member has this parent.'}]}];
 const changes=[{location_id:'member',before_properties:features[0].properties,after_properties:afterProperties}];
 const currentFeatures=projectReferenceFeatures(features,changes),hierarchyAfter=f.write('data/hierarchy.json',afterUnits);
 f.write('data/geography/fixture.json',{type:'FeatureCollection',features:currentFeatures});
 const reference={...native,id:'geography:current-metadata',hierarchy_sha256:sha(hierarchyAfter)};
 const receipt={before_sha256:native.hierarchy_sha256,after_sha256:reference.hierarchy_sha256,footprints_sha256_before:native.footprints_sha256,footprints_sha256_after:native.footprints_sha256,reference_only:true,historical_claims_transferred:false,summary:{geometry_changes:0},relationships:[],before_units:units,retired_units:[],group_changes:[4,5].map(index=>({id:units[index].id,before:units[index],after:afterUnits[index]})),changed_location_properties:changes,source_evidence:[{url:'https://example.org/source',source_sha256:'c'.repeat(64)}]};
 const receiptRaw=f.write('data/reference-correction.json',receipt);setRelease([native,{...reference,metadata:{metadata_migration_sha256:{correction:sha(receiptRaw)}}}]);const inputs=f.commit();
 const projection=prepareReferenceMetadataProjection({selection:selected,manifest,owners,reference,hierarchy:{before:pin('data/hierarchy.json',before),after:pin('data/hierarchy.json',inputs)},receipts:[pin('data/reference-correction.json',inputs)],source_updates:[{logical_path:'data/geography/fixture.json',before:pin('data/geography/fixture.json',before),after:pin('data/geography/fixture.json',inputs)}],read});
 const project=()=>{const raw=f.write('data/reference-projection.json',projection);f.write('data/ownership-selection.json',{...selected,reference_projection:{path:'data/reference-projection.json',bytes:raw.length,sha256:sha(raw)}});return f.commit();};
 const current=project();return {...f,pin,read,owners,features,currentFeatures,native,reference,projection,selected,base,current,project,manifest,setRelease};
}

test('selected metadata application exposes truthful current parents and literal native scientific inputs',()=>{
 const f=selectedMetadataFixture();try{
  const before=loadSelection(new ImmutableReader(f.repo,f.base)),after=loadSelection(new ImmutableReader(f.repo,f.current));
  const resolver=selectedGeometrySourceAlias(after),old=before.geometrySources.read('data/geography/fixture.json');
  assert.equal(after.manifest.hierarchy_sha256,f.native.hierarchy_sha256);assert.deepEqual(after.owners,f.owners);
  assert.equal(selectedReferenceOwners(after)[0].province_id,'new');assert.equal(after.owners[0].province_id,'old');
  const current=resolver.read('data/geography/fixture.json'),scientific=resolver.readNativeReferenceSource('data/geography/fixture.json');
  assert.deepEqual(current.collection.features,f.currentFeatures);assert.equal(current.source.kind,'metadata-projected-selected-source');
  assert.deepEqual(scientific,old,'Original scientific byte/source custody remains exact');
  const originalPin=f.projection.source_updates[0].before;
  assert.deepEqual(selectedNativeSourceMembership(after,originalPin),scientific);
  assert.throws(()=>selectedNativeSourceMembership(after,f.projection.source_updates[0].after),/original scientific membership/);
  assert.throws(()=>selectedNativeSourceMembership({...after},originalPin),/privately/);
  assert.equal(current.collection.features[0].properties.metadata.framework_match.id,'fallback');
  assert.throws(()=>selectedReferenceOwners({...after}),/authenticated/);
  const certificate=snapshot=>joinSelectedCoordinateCertificate(snapshot.geometrySources,[selectedCoordinateShard(snapshot.geometrySources,snapshot.geometrySources.paths)]);
  const a=certificate(before),b=certificate(after),plan=selectedCertificateAffectedPlan(a,b);
  assert.equal(a.entries[0].parent_id,'old');assert.equal(b.entries[0].parent_id,'new');
  assert.deepEqual(plan.changed_ids,[],'A parent correction does not fabricate changed physical geometry');
  const persist=(snapshot,certificate)=>{
   const facts={kind:'trusted-selected-coordinate-stage-v1',selected_commit:snapshot.reader.version,candidate_code_executed:false,binding:certificate.binding,complete_owners:certificate.entries.length,complete_sources:certificate.inputs.length};
   const encoded=gzipSync(valueBytes(certificate)),encoded_sha256=sha(encoded),decoded_sha256=valueSha(certificate);
   const publication={kind:facts.kind,complete:true,facts:{sha256:valueSha(facts)},certificate:{path:'certificate.json.gz',bytes:encoded.length,sha256:encoded_sha256,decoded_bytes:valueBytes(certificate).length,decoded_sha256}};
   const product={certificate,facts,publication,encoded_sha256,decoded_sha256};
   acceptColdCoordinateCertificate(snapshot.geometrySources,certificate,{...product,expectedPublication:publication});
   const receipt=sealColdCoordinateCertificate(certificate,product);
   assert.throws(()=>reopenColdCoordinateCertificate({...receipt},product),/private persisted custody/);
   return reopenColdCoordinateCertificate(receipt,{...product,certificate:JSON.parse(JSON.stringify(certificate))});
  };
  const persistedPlan=selectedCertificateAffectedPlan(persist(before,a),persist(after,b));
  assert.deepEqual(persistedPlan.changed_ids,[],'Detached cold metadata applicability survives exact private custody');

  const request={version:1,kind:'retained-rule-authority-registry-v1',entries:[]};
  const addition={type:'Polygon',coordinates:[[[2,0],[3,0],[3,1],[2,0]]]};
  const originalRows=[{component_id:'original',target_id:'member',pixelIndex:1,disposition:'zero-cell',geometry:addition,geometry_sha256:valueSha(addition),base_geometry:f.features[0].geometry,base_geometry_sha256:valueSha(f.features[0].geometry)}];
  const options={targetSources:[{target_id:'member',path:'data/geography/fixture.json'}]},patches=[{version:1,kind:'unassigned-native-cells-v1',rows:[{y:2,runs:[[2,3,1]]}]}];
  const oldOperands=acquireCurrentRebindOperands(before,request,originalRows,patches,options),newOperands=acquireCurrentRebindOperands(after,request,originalRows,patches,options);
  assert.deepEqual(newOperands.acquisition,oldOperands.acquisition,'No repinning or forged native execution after metadata-only change');
  assert.deepEqual(newOperands.current_targets,oldOperands.current_targets);assert.deepEqual(newOperands.base_selection,oldOperands.base_selection);
 }finally{f.cleanup();}
});

test('selected metadata application rejects absent selector, wrong actual current sources and coherent geometry drift',()=>{
 for(const mutate of [
  f=>f.write('data/ownership-selection.json',f.selected),
  f=>{const value=structuredClone(f.currentFeatures);value[0].geometry.coordinates[0][1][0]=.9;f.write('data/geography/fixture.json',{type:'FeatureCollection',features:value});},
  f=>f.write('data/hierarchy.json',[]),
  f=>{f.projection.source_updates=[];f.project();},
  f=>{f.projection.native_selection.sha256='0'.repeat(64);f.project();},
 ]){
  const f=selectedMetadataFixture();try{mutate(f);const bad=f.git('status','--porcelain')?f.commit():f.git('rev-parse','HEAD');assert.throws(()=>loadSelection(new ImmutableReader(f.repo,bad)),/Native source|source|hierarchy|original native selection|metadata/i);}finally{f.cleanup();}
 }
});

function appendAliasProjection(f){
 const features=structuredClone(f.currentFeatures),before=structuredClone(features[0].properties);features[0].properties.metadata.reference_polity='Recorded winner';
 const receipt={before_sha256:f.reference.hierarchy_sha256,after_sha256:f.reference.hierarchy_sha256,footprints_sha256_before:f.reference.footprints_sha256,footprints_sha256_after:f.reference.footprints_sha256,
  reference_only:true,historical_claims_transferred:false,summary:{geometry_changes:0},relationships:[],retired_units:[],group_changes:[],before_units:JSON.parse(f.read(f.projection.hierarchy.after)),
  changed_location_properties:[{location_id:before.id,before_properties:before,after_properties:features[0].properties}],source_evidence:[{url:'https://example.invalid/winner',source_sha256:f.projection.source_updates[0].after.sha256}]};
 f.write('data/geography/fixture.json',{type:'FeatureCollection',features});f.write('inputs/alias-receipt.json',receipt);const inputs=f.commit();
 Object.assign(f.projection,prepareReferenceMetadataProjection({selection:f.selected,manifest:f.manifest,owners:f.owners,reference:f.reference,hierarchy:f.projection.hierarchy,
  receipts:[...f.projection.receipts,f.pin('inputs/alias-receipt.json',inputs)],source_updates:[{...f.projection.source_updates[0],after:f.pin('data/geography/fixture.json',inputs)}],read:f.read}));
 return {version:f.project(),features};
}

test('real selected reader admits same-M alias correction while preserving scientific N and every owner',()=>{
 const f=selectedMetadataFixture();try{
  const prior=loadSelection(new ImmutableReader(f.repo,f.current)),release=fs.readFileSync(path.join(f.repo,'data/geographic-releases/selected.json.gz'));
  const next=appendAliasProjection(f),after=loadSelection(new ImmutableReader(f.repo,next.version));
  assert.deepEqual(selectedReferenceOwners(after),selectedReferenceOwners(prior));assert.deepEqual(after.manifest,prior.manifest);
  assert.deepEqual(selectedGeometrySourceAlias(after).read('data/geography/fixture.json').collection.features,next.features);
  assert.deepEqual(after.geometrySources.readNativeReferenceSource('data/geography/fixture.json'),prior.geometrySources.readNativeReferenceSource('data/geography/fixture.json'));
  assert.deepEqual(fs.readFileSync(path.join(f.repo,'data/geographic-releases/selected.json.gz')),release);
  f.setRelease([f.native,{...f.reference,metadata:{metadata_migration_sha256:{}}}]);const invalid=f.commit();
  assert.throws(()=>loadSelection(new ImmutableReader(f.repo,invalid)),/does not bind every applied metadata receipt/);
 }finally{f.cleanup();}
});


test('actual cold entry acquires a detached physical-program origin before preserving the next scientific refusal',async t=>{
 const lazy=process.env.GIT_NO_LAZY_FETCH;process.env.GIT_NO_LAZY_FETCH='0';
 const f=fixture();try{
  const base=f.select([[[0,2,1]],[[1,3,2]],[],[]],{transport:true});
  const selection=JSON.parse(fs.readFileSync(path.join(f.repo,'data/ownership-selection.json')));
  const pin=(name,version=f.git('rev-parse','HEAD'))=>{const raw=execFileSync('git',['-C',f.repo,'show',version+':'+name]);
   const [mode,,oid]=f.git('ls-tree',version,'--',name).split(/[ \t]/);return {commit:version,path:name,mode,git_blob_oid:oid,bytes:raw.length,sha256:sha(raw)};};
  const footprint='a'.repeat(64),reference={id:selection.release_id,footprints_sha256:footprint,hierarchy_sha256:'b'.repeat(64)};
  const release=f.write('data/geographic-releases/selected.json.gz',gzipSync(valueBytes({releases:[reference]})));
  f.write('data/geographic-releases/current-manifest.json',{path:'selected.json.gz',sha256:sha(release)});
  const catalogue='coordination/engineering/original-geography-source-corpus-20261006/catalogue.json';
  f.write(catalogue,{products:[]});f.write('physical.py',Buffer.from('# original retained programme\n'));
  f.write('physical-input.json',[]);f.write('physical-evidence.json',{});f.write('latitudes.bin',Buffer.alloc(0));
  const original=f.commit(),program=pin('physical.py',original);
  const bank={version:1,kind:'complete-world-index-with-exact-encoded-overrides',release_id:selection.release_id,
   native_manifest_sha256:selection.sha256,footprints_sha256:footprint,locations:2,world_index:pin('data/world-index.json',base),
   unchanged_files:[pin('data/geography/fixture.json',base)],overrides:[]};
  const bankRaw=f.write('source/selected-bank.json',bank),baseSelection={...selection,selected_geography:{version:1,kind:bank.kind,path:'source/selected-bank.json',bytes:bankRaw.length,sha256:sha(bankRaw)}};
  const latitude=pin('latitudes.bin',original),evidence={version:1,kind:'source-target-native-evidence-v1',targets:[{}],
   catalogue:pin(catalogue,original),physical_input:pin('physical-input.json',original),physical_evidence:pin('physical-evidence.json',original),
   physical_reproduction:program,native_latitudes:latitude,native_contract:{size:4,native_latitudes:latitude}};
  f.write('evidence.json',evidence);f.write('proposed.json',{rows:[]});const evidenceCommit=f.commit();
  const binding={version:1,kind:'source-target-native-custody-v1',source_evidence:pin('evidence.json',evidenceCommit),native_patch:pin('proposed.json',evidenceCommit)};
  const preimage={...binding,kind:'source-target-native-rule-v1'};f.write('binding.json',binding);f.write('rule.json',valueBytes(preimage));const rules=f.commit();
  const e={policy_id:'retained-source-literal-additions',policy_version:1,rule_sha256:valueSha(preimage),rule_preimage:pin('rule.json',rules),source_authority:pin('binding.json',rules)};
  const registry={version:1,kind:'retained-rule-authority-registry-v1',entries:[{...e,authority_sha256:valueSha(e)}]};
  f.write('registry.json',registry);f.write('ledger.json',{version:2,kind:'native-additive-repair-ledger-v2',authority_registry_sha256:valueSha(registry),scope_ids:[],rows:[]});f.write('patch.json',{rows:[]});const products=f.commit();
  const manifest=JSON.parse(fs.readFileSync(path.join(f.repo,selection.manifest_path)));
  const assets={base_manifest:pin(selection.manifest_path,base),owner_roster:pin(manifest.original_assets.bounds.path,base),ledger:pin('ledger.json',products),patch:pin('patch.json',products)};
  const ownerBody=gunzipSync(fs.readFileSync(path.join(f.repo,assets.owner_roster.path)));Object.assign(assets.owner_roster,{decoded_bytes:ownerBody.length,decoded_sha256:sha(ownerBody)});
  f.write('envelope.json',{version:2,kind:'retained-native-base-plus-delta-v2',base_reference:reference,effective_reference:reference,...assets});const envelope=f.commit();
  const sidecar=f.write('sidecar.json',{version:2,kind:'retained-native-additive-selection-v2',base_selection:baseSelection,authority_registry:pin('registry.json',products),runtime_envelope:pin('envelope.json',envelope),logical_asset_map:assets});
  f.write('data/ownership-selection.json',{...baseSelection,additive_release:{path:'sidecar.json',bytes:sidecar.length,sha256:sha(sidecar)}});
  f.write('physical.py',Buffer.from('# newer incompatible programme\n'));const current=f.commit();
  const remote=path.join(f.repo,'remote.git');execFileSync('git',['clone','--bare','--no-hardlinks',f.repo,remote],{stdio:'pipe'});
  execFileSync('git',['-C',remote,'config','uploadpack.allowFilter','true']);execFileSync('git',['-C',remote,'config','uploadpack.allowAnySHA1InWant','true']);
  for(const oid of [original,program.git_blob_oid])fs.unlinkSync(path.join(f.repo,'.git/objects',oid.slice(0,2),oid.slice(2)));
  assert.throws(()=>loadSelection(new ImmutableReader(f.repo,current)),/Source-target whole identity differs/);
  const actual=ImmutableReader.prototype.acquirePinned,calls=[];
  t.mock.method(ImmutableReader.prototype,'acquirePinned',async function(p){calls.push({reader:this,pin:p});return actual.call(this,p,{
   loadCommit:async id=>({sha:id,tree:{sha:execFileSync('git',['-C',remote,'rev-parse',id+'^{tree}']).toString().trim()}}),
   loadTree:async id=>({sha:id,truncated:false,tree:execFileSync('git',['-C',remote,'ls-tree','-z',id]).toString().split('\0').filter(Boolean).map(line=>{const [,mode,type,sha,name]=line.match(/^(\d+) (\w+) ([a-f0-9]+)\t(.+)$/s);return {mode,type,sha,path:name};})}),
   execute:(command,args,options)=>execFileSync(command,args.map(arg=>arg==='https://github.com/ChengshuLi/WorldAtlas.git'?'file://'+remote:arg),options)
  });});
  await assert.rejects(inspectSelectedAcquired(f.repo,current,current),/Unsupported source-target native lattice/);
  const consumed=calls.find(row=>row.pin.path==='physical.py');assert(consumed,'Actual evaluator must yield the physical program');
  assert.equal(consumed.reader.inventory.get(original+':physical.py').sha256,program.sha256);
  assert.equal(consumed.reader.inventory.get(original+':physical.py').whole_body_consumed,true);
  assert.deepEqual(calls.slice(0,5).map(row=>row.pin.path),['evidence.json','proposed.json',catalogue,'physical-input.json','physical.py']);
  assert.throws(()=>f.git('--no-lazy-fetch','cat-file','-e',original+'^{commit}'),'Private origin metadata never becomes a partial local producer');
  assert(!fs.existsSync(path.join(f.repo,'.git/shallow')));
  t.mock.restoreAll();
 }finally{f.cleanup();if(lazy===undefined)delete process.env.GIT_NO_LAZY_FETCH;else process.env.GIT_NO_LAZY_FETCH=lazy;}
});

// This is a small real-Git custody fixture, not a source/native producer run.
// It must get through the complete administrative source proof and then refuse
// the deliberately absent native proof, with no successful geography receipt.
for(const variant of ['exact','duplicate-map','missing-map','map-path','map-hash','map-bytes','map-oid','map-mode','wrong-map-origin','known-selector-missing-tree','metadata-unavailable'])
test('actual cold administrative read preserves issued selector and consumed-map custody: '+variant,async t=>{
 const f=fixture();try{
  const base=f.select([[[0,2,1]],[[1,3,2]],[],[]],{transport:true});
  const selection=JSON.parse(fs.readFileSync(path.join(f.repo,'data/ownership-selection.json')));
  const pin=(name,version=f.git('rev-parse','HEAD'))=>{const raw=execFileSync('git',['-C',f.repo,'show',version+':'+name]);const [mode,,oid]=f.git('ls-tree',version,'--',name).split(/[ \t]/);return {commit:version,path:name,mode,git_blob_oid:oid,bytes:raw.length,sha256:sha(raw)};};
  const cataloguePath='coordination/engineering/selected-geography-effective-prevention-20261009/supported-programs.json';f.write(cataloguePath,fs.readFileSync(cataloguePath));
  const programme=JSON.parse(fs.readFileSync(path.join(f.repo,cataloguePath))).programs.find(p=>p.source_profile==='retained-consumed-administrative-source');
  const reference={id:selection.release_id,footprints_sha256:'a'.repeat(64),hierarchy_sha256:'b'.repeat(64)};
  const release=f.write('data/geographic-releases/selected.json.gz',gzipSync(valueBytes({releases:[reference]})));
  f.write('data/geographic-releases/current-manifest.json',{path:'selected.json.gz',sha256:sha(release)});
  const target=pin('data/geography/fixture.json',base),targetInput={...target,blob:target.git_blob_oid};delete targetInput.git_blob_oid;
  const bank={version:1,kind:'complete-world-index-with-exact-encoded-overrides',release_id:selection.release_id,native_manifest_sha256:selection.sha256,footprints_sha256:reference.footprints_sha256,locations:2,world_index:pin('data/world-index.json',base),unchanged_files:[target],overrides:[]};
  const bankRaw=f.write('source/selected-bank.json',bank),baseSelection={...selection,selected_geography:{version:1,kind:bank.kind,path:'source/selected-bank.json',bytes:bankRaw.length,sha256:sha(bankRaw)}};
  const mapOrigin=f.commit(),mapPin=pin('source/selected-bank.json',mapOrigin);
  f.write('source/selected-bank.json',{different:true});const wrongMapOrigin=f.commit();f.write('source/selected-bank.json',bankRaw);
  f.write('data/ownership-selection.json',baseSelection);const old=f.commit(),oldPin=pin('data/ownership-selection.json',old);
  const selected={...baseSelection,additive_release:{path:'prior-sidecar.json',bytes:1,sha256:'c'.repeat(64)}};
  f.write('data/ownership-selection.json',selected);const newer=f.commit(),newPin=pin('data/ownership-selection.json',newer);
  const baseline=p=>({version:2,kind:'current-selected-native-baseline-v1',pins:[p]});
  const id='component:held',parent={},runtime={},installed_modules=[],report={whole:'fixture-report'};
  const source_rule={profile:programme.source_profile,expected_ids:[id],inputs:[targetInput],target_banks:[target.path]};
  const issued={version:1,operation:'retained-land-source-premises-v1',executed_code:programme.source_executed_code,baseline:baseline(oldPin),parent,source_rule,installed_modules,report,destination:'source-output'};
  f.write('source/request.json',issued);const sr=pin('source/request.json',f.commit());
  const source={operation:issued.operation,request:sr,executed_code:issued.executed_code,baseline:issued.baseline,parent,source_rule,components:1,execution_commit:base,runtime,installed_modules,input_descriptors:[report,targetInput,oldPin]};
  f.write('source/facts.json',source);const sf=pin('source/facts.json',f.commit());
  f.write('source/inventory.jsonl',Buffer.from(JSON.stringify({component_id:id})+'\n'));const si=pin('source/inventory.jsonl',f.commit());
  f.write('source/publication.json',{complete:true,facts:{bytes:sf.bytes,sha256:sf.sha256},inventory:{bytes:si.bytes,sha256:si.sha256}});
  f.write('source/operating.json',{qualified:true,execution_commit:base,exit:{code:0,signal:null},owned_processes_remaining:[],refusal:null,request_sha256:sr.sha256,destination:issued.destination});const proofs=f.commit(),sp=pin('source/publication.json',proofs),so=pin('source/operating.json',proofs);
  const mp=pin(selection.manifest_path,base),additive={scope_ids:[id],source_profile:source_rule.profile,source_execution_commit:base,source_runtime:runtime,inputs:[sr,sf,sp,si,so,mp],source_request_path:sr.path,facts_path:sf.path,publication_path:sp.path,inventory_path:si.path,operating_path:so.path,manifest_path:mp.path};
  const request={version:1,operation:'unactivated-additive-native-batch-v1',executed_code:programme.native_executed_code,baseline:baseline(newPin),parent,additive};
  f.write('native/request.json',request);const nr=pin('native/request.json',f.commit());
  const consumed={...mapPin,whole_body_consumed:true};if(variant==='map-path')consumed.path='source/absent-bank.json';if(variant==='map-hash')consumed.sha256='f'.repeat(64);if(variant==='map-bytes')consumed.bytes++;if(variant==='map-oid')consumed.git_blob_oid='f'.repeat(40);if(variant==='map-mode')consumed.mode='100755';if(variant==='wrong-map-origin')consumed.commit=wrongMapOrigin;
  const acquisition={kind:'current-selected-native-baseline-custody-v1',baseline_pin:newPin,selection:selected,manifest_sha256:mp.sha256,source_map_sha256:baseSelection.selected_geography.sha256,input_inventory:[{...mp,whole_body_consumed:true},...(variant==='missing-map'?[]:variant==='duplicate-map'?[consumed,consumed]:[consumed])],source_bindings:[{...target,kind:'ordinary-immutable-git-source'}]};
  const preimage={version:3,source_profile:source_rule.profile,source_rule,representation:'literal-base-or-complete-additions',native_method:selection.method,executed_code:request.executed_code};
  f.write('native/facts.json',{operation:request.operation,executed_code:request.executed_code,baseline:request.baseline,parent,request:nr,source_predecessor:additive,baseline_acquisition:acquisition});
  f.write('native/ledger.json',{version:1,kind:'native-additive-repair-ledger-v1',scope_ids:[id],rows:[{component_id:id,disposition:'held'}],rule_sha256:valueSha(preimage)});const native=f.commit();
  f.write('binding.json',{version:1,kind:'original-issued-rule-source-custody-v1',original_pins:{ledger:pin('native/ledger.json',native),native_facts:pin('native/facts.json',native),native_manifest:mp,native_request:nr,source_facts:sf,source_request:sr},native_proof:{}});
  f.write('rule.json',valueBytes(preimage));const rules=f.commit(),e={policy_id:'retained-source-literal-additions',policy_version:1,rule_sha256:valueSha(preimage),rule_preimage:pin('rule.json',rules),source_authority:pin('binding.json',rules)};
  const registry={version:1,kind:'retained-rule-authority-registry-v1',entries:[{...e,authority_sha256:valueSha(e)}]};
  f.write('registry.json',registry);f.write('ledger.json',{version:2,kind:'native-additive-repair-ledger-v2',authority_registry_sha256:valueSha(registry),scope_ids:[],rows:[]});f.write('patch.json',{rows:[]});const products=f.commit();
  const manifest=JSON.parse(fs.readFileSync(path.join(f.repo,selection.manifest_path))),assets={base_manifest:mp,owner_roster:pin(manifest.original_assets.bounds.path,base),ledger:pin('ledger.json',products),patch:pin('patch.json',products)};
  const owners=gunzipSync(fs.readFileSync(path.join(f.repo,assets.owner_roster.path)));Object.assign(assets.owner_roster,{decoded_bytes:owners.length,decoded_sha256:sha(owners)});
  f.write('envelope.json',{version:2,kind:'retained-native-base-plus-delta-v2',base_reference:reference,effective_reference:reference,...assets});const envelope=f.commit();
  const sidecar=f.write('sidecar.json',{version:2,kind:'retained-native-additive-selection-v2',base_selection:baseSelection,authority_registry:pin('registry.json',products),runtime_envelope:pin('envelope.json',envelope),logical_asset_map:assets});
  f.write('data/ownership-selection.json',{...baseSelection,additive_release:{path:'sidecar.json',bytes:sidecar.length,sha256:sha(sidecar)}});const current=f.commit();
  const remote=path.join(f.repo,'remote.git');execFileSync('git',['clone','--bare','--no-hardlinks',f.repo,remote],{stdio:'pipe'});for(const key of ['uploadpack.allowFilter','uploadpack.allowAnySHA1InWant'])execFileSync('git',['-C',remote,'config',key,'true']);
  const removed=[...(variant==='known-selector-missing-tree'?[f.git('rev-parse',old+'^{tree}')]:[old]),newer,mapOrigin,oldPin.git_blob_oid,newPin.git_blob_oid];
  for(const oid of removed)fs.unlinkSync(path.join(f.repo,'.git/objects',oid.slice(0,2),oid.slice(2)));
  // Use the fixture's actual executing module, whose committed policy catalogue
  // is authenticated by the same real module-body binding as production.
  const mod=await import('file://'+path.join(f.repo,'scripts/check-effective-geographic-regression.mjs'));
  const original=mod.ImmutableReader.prototype.acquirePinned,calls=[];
  t.mock.method(mod.ImmutableReader.prototype,'acquirePinned',async function(p){calls.push({reader:this,pin:p});return original.call(this,p,{
   loadCommit:async id=>{if(variant==='metadata-unavailable')throw Error('fixture original metadata unavailable');return {sha:id,tree:{sha:execFileSync('git',['-C',remote,'rev-parse',id+'^{tree}']).toString().trim()}};},
   loadTree:async id=>({sha:id,truncated:false,tree:execFileSync('git',['-C',remote,'ls-tree','-z',id]).toString().split('\0').filter(Boolean).map(line=>{const [,mode,type,sha,name]=line.match(/^(\d+) (\w+) ([a-f0-9]+)\t(.+)$/s);return {mode,type,sha,path:name};})}),
   execute:(command,args,options)=>execFileSync(command,args.map(arg=>arg==='https://github.com/ChengshuLi/WorldAtlas.git'?'file://'+remote:arg),options)
  });});
  const expected=variant==='exact'?/Require complete native proof roster/:['duplicate-map','missing-map','map-path'].includes(variant)?/Missing\/duplicate administrative consumed source map/:['map-hash','map-bytes'].includes(variant)?/Administrative consumed source map identity differs/:variant==='metadata-unavailable'?/fixture original metadata unavailable/:variant==='known-selector-missing-tree'?/not a tree object|unable to read tree|bad tree object/:['map-oid','map-mode'].includes(variant)?/differs from original path|differs from tree|descriptor differs|blob identity differs/:/Source-target whole identity differs/;
  await assert.rejects(mod.inspectSelectedAcquired(f.repo,current,current),expected);
  assert.deepEqual(calls.slice(0,2).map(r=>r.pin),['metadata-unavailable','known-selector-missing-tree'].includes(variant)?[oldPin]:[oldPin,newPin]);
  if(variant==='exact'){
   assert.equal(calls[2].pin.commit,mapOrigin,'The map retains its genuine native origin, not a selector origin');
   assert.equal(calls[2].reader.inventory.get(current+':'+mapPin.path).whole_body_consumed,true,'An exact current map remains the cheap whole-body route');
   for(const oid of [old,newer,mapOrigin])assert.throws(()=>f.git('--no-lazy-fetch','cat-file','-e',oid+'^{commit}'));
   assert(!fs.existsSync(path.join(f.repo,'.git','shallow')));
  }
 }finally{f.cleanup();}
});

test('real current-rebind custody consumes privately authenticated historical code and retains its execution refusal',async()=>{
 const f=fixture();try{
  const baseline=f.select([[[0,2,1]],[[1,3,2]],[],[]]);
  const pin=(name,version)=>{const raw=execFileSync('git',['-C',f.repo,'show',version+':'+name]);const [mode,,git_blob_oid]=f.git('ls-tree',version,'--',name).split(/[ \t]/);return {commit:version,path:name,mode,git_blob_oid,bytes:raw.length,sha256:sha(raw)};};
  const code=LEGACY_CURRENT_REBIND_CODE.map(name=>{const raw=f.write(name,Buffer.from('retained original code: '+name+'\n'));return {path:name,bytes:raw.length,sha256:sha(raw)};});
  const execution=f.commit(),externalNames=['code_source','terminal','stderr','stdout','issued_plan'];
  for(const name of externalNames)f.write('rebind/'+name+'.json',{});const external=f.commit();
  const externalPins=Object.fromEntries(externalNames.map(name=>[name,pin('rebind/'+name+'.json',external)]));
  f.write('rebind/request.json',{executed_code:code});f.write('rebind/operating.json',{execution_custody:externalPins});
  for(const name of ['facts','publication','result'])f.write('rebind/'+name+'.json',{});const products=f.commit();
  const names=['request','facts','publication','operating','result'],productPins=Object.fromEntries(names.map(name=>[name,pin('rebind/'+name+'.json',products)]));
  f.write('rebind/certificate.json',{version:1,kind:'qualified-native-additive-current-bank-rebind-v1',execution_commit:execution,base_selection:{},authority_registry_sha256:'a'.repeat(64),...productPins});const issued=f.commit(),certificate=pin('rebind/certificate.json',issued);
  for(const p of code)f.write(p.path,Buffer.from('different current code\n'));
  f.write('rebind/request.json',{unrelated:true});const current=f.commit();
  const remote=path.join(f.repo,'remote.git');execFileSync('git',['clone','--bare','--no-hardlinks',f.repo,remote],{stdio:'pipe'});for(const key of ['uploadpack.allowFilter','uploadpack.allowAnySHA1InWant'])execFileSync('git',['-C',remote,'config',key,'true']);
  for(const oid of [execution,products,issued])fs.unlinkSync(path.join(f.repo,'.git/objects',oid.slice(0,2),oid.slice(2)));
  const options={loadCommit:async id=>({sha:id,tree:{sha:execFileSync('git',['-C',remote,'rev-parse',id+'^{tree}']).toString().trim()}}),
   loadTree:async id=>({sha:id,truncated:false,tree:execFileSync('git',['-C',remote,'ls-tree','-z',id]).toString().split('\0').filter(Boolean).map(line=>{const [,mode,type,sha,name]=line.match(/^(\d+) (\w+) ([a-f0-9]+)\t(.+)$/s);return {mode,type,sha,path:name};})}),
   execute:(command,args,options)=>execFileSync(command,args.map(arg=>arg==='https://github.com/ChengshuLi/WorldAtlas.git'?'file://'+remote:arg),options)};
  const reader=new ImmutableReader(f.repo,current),snapshot=loadSelection(reader);
  const consume=()=>readCurrentRebindCustody(reader,certificate,{snapshot});
  assert.throws(consume,/Whole rebind product mode\/OID\/length differs/,'The sync wrapper does not acquire missing-origin proof');
  for(const p of [certificate,...Object.values(productPins),...Object.values(externalPins)])await reader.acquirePinned(p,options);
  await reader.acquireOriginalPaths(code.map(p=>({...p,commit:execution})),options);
  assert.throws(consume,/Missing issued actual execution contract/,'Authenticating historical code never fabricates successful operating custody');
  for(const p of code){const row=reader.inventory.get(execution+':'+p.path);assert.equal(row.whole_body_consumed,true);assert.equal(row.sha256,p.sha256);assert.equal(row.bytes,p.bytes);}
  assert.equal(reader.inventory.get(products+':rebind/request.json').whole_body_consumed,true);
  for(const oid of [execution,products,issued])assert.throws(()=>f.git('--no-lazy-fetch','cat-file','-e',oid+'^{commit}'));
  assert(!fs.existsSync(path.join(f.repo,'.git','shallow')));assert.equal(baseline.length,40);
 }finally{f.cleanup();}
});
