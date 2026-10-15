import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync,spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gzipSync,gunzipSync} from 'node:zlib';
import {ImmutableReader,NativeAssetImage,SelectedGeometrySources,loadBaseSelection,loadSelection,inspectSelected,compareIntervals,compareRepairLedgers,readArtifactConsumption,validateReleaseCatalogue,validateArtifactSourceMetadata,loadNativeRowTable,acquireNativeRows,validateNativeRowCarry} from '../scripts/check-effective-geographic-regression.mjs';
import {shuffleOwnershipBytes} from '../src/ownership-codec.js';
import {nativeRowLatitudes} from '../src/native-grid.js';
import {JOINT_CODE} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-joint-entry.mjs';
import {valueBytes,valueSha,readOriginalRuleAuthority,selectedCoordinateShard,joinSelectedCoordinateCertificate,acceptColdCoordinateCertificate,selectedAffectedPlan,possibleNeighbors,compareVersionedRepairLedgers,readRetainedRegistryAuthority} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';

const sha=b=>createHash('sha256').update(b).digest('hex'),root=process.cwd();
const retained=process.env.WORLDATLAS_PREVENTION_CONTROLS;
if(retained){assert.equal(fs.realpathSync(path.dirname(retained)),path.dirname(retained));assert.equal(fs.existsSync(retained),false);assert.throws(()=>fs.lstatSync(retained),{code:'ENOENT'});fs.mkdirSync(retained);}
let fixtureOrdinal=0;
function fixture({size=4}={}){
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
 const owners=[{index:1,id:'old-owner',province_id:'parent',province_index:1},{index:2,id:'other-owner',province_id:'parent',province_index:1}];
 const bounds=write('data/canonical-grid/bounds.json.gz',gzipSync(Buffer.from(JSON.stringify(owners))));
 const latitudeBytes=size===4?null:Buffer.alloc(size*8);
 if(latitudeBytes){const latitudes=nativeRowLatitudes(size);latitudes.forEach((latitude,y)=>latitudeBytes.writeDoubleLE(latitude,y*8));write('original/latitudes.f64le',latitudeBytes);}
 const origin=commit(),bits=Math.ceil(Math.log2(size));
 const part=(kind,words)=>{const raw=Buffer.from(words.buffer),encoded=gzipSync(shuffleOwnershipBytes(words)),name=`native-v1/ownership/${kind}-0.bin.gz`;write('data/canonical-grid/fixture/'+name,encoded);return {kind,offset:0,words:words.length,path:name,bytes:encoded.length,sha256:sha(encoded),decoded_bytes:raw.length,decoded_sha256:sha(raw),encoding:'byte-shuffle'};};
 const select=(intervals,{extraSelection={},indices=false,badRows=false,transport=false,releaseId='geography:review:fixture'}={})=>{
  const rows=new Uint32Array(size*2),words=[];let cursor=0;
  for(let y=0;y<size;y++){rows[y*2]=cursor;rows[y*2+1]=(intervals[y]??[]).length;for(const [start,end,owner]of intervals[y]??[]){words.push(owner*2**bits+start,end-1);cursor++;}}
  if(badRows)rows[2]++;
  const manifest={version:2,method:'native-linear-evenodd-first-owner-v1',size,coordinateBits:bits,runWords:words.length,parts:[part('rows',rows),part('runs',Uint32Array.from(words))],geographic_release:releaseId,bounds:{sha256:sha(bounds),decoded_bytes:Buffer.byteLength(JSON.stringify(owners))},original_assets:{bounds:{role:'original-identity-parent-camera-context',commit:origin,path:'data/canonical-grid/bounds.json.gz',sha256:sha(bounds)}},native_latitudes:latitudeBytes?{commit:origin,path:'original/latitudes.f64le',mode:'100644',git_blob_oid:createHash('sha1').update(Buffer.from('blob '+latitudeBytes.length+'\0')).update(latitudeBytes).digest('hex'),bytes:latitudeBytes.length,sha256:sha(latitudeBytes)}:{sha256:'1'.repeat(64)},...(latitudeBytes?{hierarchy_sha256:'a'.repeat(64)}:{})};
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
  const receipt={method:manifest.method,checked_rows:size,checked_cells:size**2,unchecked_cells:0,checked_runs:words.length/2,installation_ready:false,products,two_run_products:products.length,run_one_sha256:sha(Buffer.from(JSON.stringify(products))),run_two_sha256:sha(Buffer.from(JSON.stringify(products)))};
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
  const lost=f.select([[[0,1,1]],[[1,3,2]],[],[]]);
  const report=inspectSelected(f.repo,base,lost);assert.equal(report.lost_or_reassigned_cells,1);assert.deepEqual(report.intervals,[{row:0,start:1,end:2,previous_owner:'old-owner',candidate_owner:null}]);
  const transferred=f.select([[[0,2,2]],[[1,3,2]],[],[]]);assert.equal(inspectSelected(f.repo,base,transferred).lost_or_reassigned_cells,2);
  f.git('checkout',base,'--','scripts/native-ownership/verified-candidates.json');f.git('reset','--hard',base);
  const command=[path.join(f.repo,'scripts/run-geographic-check.py'),'-I'];
  const preload=path.join(f.repo,'untrusted-preload.cjs'),preloadSentinel=path.join(f.repo,'preload-executed');fs.writeFileSync(preload,`require('node:fs').writeFileSync(${JSON.stringify(preloadSentinel)},'executed');`);
  const result=spawnSync(process.env.WORLDATLAS_TEST_PYTHON??'python3',['-I','-B',command[0],'--repo',f.repo,'--baseline',base,'--candidate',lost,'--out',path.join(f.repo,'blocked.json')],{encoding:'utf8',env:{...process.env,NODE:process.execPath,NODE_OPTIONS:'--require='+preload,NODE_PATH:f.repo}});
  assert.equal(fs.existsSync(preloadSentinel),false,'actual trusted child must not execute an inherited preload');
  assert.equal(result.status,1,result.stderr);assert.ok(fs.existsSync(path.join(f.repo,'blocked.json')),result.stderr);const actual=JSON.parse(fs.readFileSync(path.join(f.repo,'blocked.json')));assert.equal(actual.status,'native-regressions-found');assert.equal(actual.candidate_code_executed,false);assert.equal(actual.selected_native_report.lost_or_reassigned_cells,1);
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


test('whole original rule custody derives actual issued preimage and refuses rebinding before selection',()=>{
 const f=fixture();try{
  const pin=(name,commit)=>{const raw=execFileSync('git',['-C',f.repo,'show',commit+':'+name]),[mode,,blob]=f.git('ls-tree',commit,'--',name).split(/[ \t]/);return {commit,path:name,mode,blob,bytes:raw.length,sha256:sha(raw)};};
  const id='component:a',geometry={type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,0]]]},executed_code=[{path:'model.js',bytes:1,sha256:'1'.repeat(64)}];
  const baseline={pins:[]},parent={kind:'model-full-parent'},source_rule={profile:'model-retained-source',expected_ids:[id]};
  f.write('source/request.json',{version:1,operation:'retained-land-source-premises-v1',executed_code,baseline,parent,source_rule});
  const sr=pin('source/request.json',f.commit());
  f.write('source/facts.json',{operation:'retained-land-source-premises-v1',request:sr,executed_code,baseline,parent,source_rule,components:1});
  const sf=pin('source/facts.json',f.commit());
  f.write('native/manifest.json',{method:'model-native-method'});const mp=pin('native/manifest.json',f.commit());baseline.pins=[mp];
  // Source baseline belongs to its original issued vintage, which must also be
  // present unchanged in its facts. The proposal has its independently bound
  // native baseline; these are not asserted to be one source authority.
  const additive={scope_ids:[id],inputs:[sr,sf],source_request_path:sr.path,facts_path:sf.path,manifest_path:mp.path};
  const request={version:1,operation:'unactivated-additive-native-batch-v1',executed_code,baseline,parent,additive};
  f.write('native/request.json',request);const nr=pin('native/request.json',f.commit());
  const preimage={version:3,source_profile:source_rule.profile,source_rule,representation:'literal-base-or-complete-additions',native_method:'model-native-method',executed_code};
  const row={component_id:id,disposition:'zero-cell',target_id:'owner:a',pixelIndex:1,geometry,geometry_sha256:valueSha(geometry),base_geometry_sha256:'2'.repeat(64),native_cells:0,source_receipt_sha256:sf.sha256};
  const ledger={version:1,kind:'native-additive-repair-ledger-v1',scope_ids:[id],rows:[row],rule_sha256:valueSha(preimage)};
  const native={operation:request.operation,executed_code,baseline,parent,request:nr,source_predecessor:additive};
  f.write('native/facts.json',native);f.write('native/ledger.json',ledger);const head=f.commit();
  const pins={ledger:pin('native/ledger.json',head),native_facts:pin('native/facts.json',head),native_manifest:mp,native_request:nr,source_facts:sf,source_request:sr};
  const open=()=>new ImmutableReader(f.repo,head);
  const result=readOriginalRuleAuthority(open(),pins);assert.equal(result.rule_sha256,valueSha(preimage));assert.equal(result.ledger.rows[0].native_cells,0);
  const wrong=structuredClone(pins);wrong.source_request.sha256='0'.repeat(64);assert.throws(()=>readOriginalRuleAuthority(open(),wrong),/Whole immutable input differs/);
  f.write('native/facts.json',{...native,executed_code:[]});const rebound=f.commit();assert.throws(()=>readOriginalRuleAuthority(new ImmutableReader(f.repo,rebound),{...pins,native_facts:pin('native/facts.json',rebound)}),/executed code differs/);
  const missing={...pins};delete missing.source_request;assert.throws(()=>readOriginalRuleAuthority(open(),missing),/exact original rule body roster/);
 }finally{f.cleanup();}
});


test('renewed immutable artifact entry binds complete catalogue and independent authority',()=>{
 const directory=path.join(root,'coordination/engineering/selected-geography-effective-prevention-20261009/artifact-interface-controls/latest-999db');
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
  const original=path.join(root,'coordination/engineering/qualified-artifact-authority-admission-20261009/fixtures/original-999');
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
 const directory=path.join(root,'coordination/engineering/qualified-artifact-authority-admission-20261009/fixtures/latest-e177');
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
 const directory=path.join(root,'coordination/engineering/qualified-artifact-authority-admission-20261009/fixtures/latest-e177');
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


for(const [title,relative]of [['genuine Cloudflare authority retains complete 533 roles and four explicit entry profiles','coordination/engineering/qualified-artifact-authority-admission-20261009/fixtures/latest-8832354'],['renewed installer authority retains genuine complete 533-role custody','coordination/engineering/selected-native-side-acquisition-20261009/authority-121149']])test(title,()=>{
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


// Extend the existing immutable bank fixture with the genuine modern source
// constructor and explicit ordinary selected-source/delta metadata. The complete
// normative lattice is two MiB; only one source-supported cell is proposed.
function additiveComparisonFixture({overlap=false,transport=false,empty=false,invalidOwner=false}={}){
 const size=262166,f=fixture({size}),y=size/2,x=size/2;
 // Issued JSON uses the accepted canonical bytes. Whole-body pins below still
 // come from actual committed blobs, so semantic and encoded hashes agree only
 // where the producer deliberately issues canonical JSON.
 const write=(name,value)=>f.write(name,Buffer.isBuffer(value)?value:valueBytes(value));
 const pin=(name,commit)=>{const raw=execFileSync('git',['-C',f.repo,'show',commit+':'+name]),[mode,,git_blob_oid]=f.git('ls-tree',commit,'--',name).split(/[ \t]/);return {commit,path:name,mode,git_blob_oid,bytes:raw.length,sha256:sha(raw)};};
 const rectangle=(left,right)=>({type:'Polygon',coordinates:[[[left,-.02],[right,-.02],[right,.02],[left,.02],[left,-.02]]]});
 const features=[{type:'Feature',id:'old-owner',properties:{parent_id:'parent',metadata:{source_member_ids:['gb:TST:ADM2:A']}},geometry:rectangle(-.02,.02)},
  {type:'Feature',id:'other-owner',properties:{parent_id:'parent',metadata:{source_member_ids:['gb:TST:ADM2:B']}},geometry:rectangle(1,1.02)}];
 const reference={id:'geography:review:fixture',hierarchy_sha256:'a'.repeat(64),footprints_sha256:'b'.repeat(64)};
 write('data/geography/fixture.json',{type:'FeatureCollection',features});
 const release=write('data/geographic-releases/release.json.gz',gzipSync(valueBytes({releases:[reference]})));
 write('data/geographic-releases/current-manifest.json',{path:'release.json.gz',sha256:sha(release)});const sources=f.commit();
 const intervals=[];intervals[y-2]=[[0,1,2]];if(!empty)intervals[y]=overlap?[[x,x+1,1]]:[[x-3,x-2,invalidOwner?3:1]];
 const bank=f.select(intervals,{transport}),selection=JSON.parse(fs.readFileSync(path.join(f.repo,'data/ownership-selection.json'))),manifest=JSON.parse(fs.readFileSync(path.join(f.repo,selection.manifest_path)));
 const boundsPin=pin('data/canonical-grid/bounds.json.gz',manifest.original_assets.bounds.commit);
 const decoded=gunzipSync(fs.readFileSync(path.join(f.repo,boundsPin.path)));
 const ownersPin={...boundsPin,decoded_bytes:decoded.length,decoded_sha256:sha(decoded)};
 const family='gb:TST:ADM2',raw={type:'FeatureCollection',features:features.map((feature,i)=>({type:'Feature',properties:{shapeID:i?'B':'A'},geometry:feature.geometry}))};
 write('original/source.json',raw);
 write('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json',{products:[{key:family,parts:[{path:'original/source.json',bytes:valueBytes(raw).length,sha256:valueSha(raw)}],feature_count:2,original_bytes:valueBytes(raw).length,original_sha256:valueSha(raw)}]});
 write('original/physical.json',{results:[{target:family+':A',issues:[],support:{mapped_land_support:features[0].geometry}}]});
 write('original/measured.json',[{target:family+':A',consumed:{geometry:features[0].geometry},selected:{id:'old-owner',geometry:features[0].geometry}}]);
 write('original/physical.py',Buffer.from('# retained tiny constructor fixture\n'));
 write('data/semantic-report.json',{changes:[{id:'old-owner',replaces:[family+':A']},{id:'other-owner',replaces:[family+':B']}]});
 write('original/native-patch.json',{rows:[{y,runs:[[x,x+1,1]]}]});const originals=f.commit();
 write('data/selected-source-bank.json',{version:1,kind:'complete-world-index-with-exact-encoded-overrides',release_id:reference.id,native_manifest_sha256:selection.sha256,footprints_sha256:reference.footprints_sha256,locations:2,world_index:pin('data/world-index.json',sources),unchanged_files:[pin('data/geography/fixture.json',sources)],overrides:[]});
 const bankRaw=fs.readFileSync(path.join(f.repo,'data/selected-source-bank.json'));
 selection.selected_geography={version:1,kind:'complete-world-index-with-exact-encoded-overrides',path:'data/selected-source-bank.json',bytes:bankRaw.length,sha256:sha(bankRaw)};
 const evidence={version:1,kind:'source-target-native-evidence-v1',catalogue:pin('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json',originals),
  owner_roster:ownersPin,physical_evidence:pin('original/physical.json',originals),physical_input:pin('original/measured.json',originals),physical_reproduction:pin('original/physical.py',originals),native_latitudes:manifest.native_latitudes,
  native_contract:Object.fromEntries(['size','coordinateBits','method','native_latitudes','hierarchy_sha256','original_assets'].map(k=>[k,manifest[k]])),base_reference:reference,
  families:[{source_id:family,parts:[pin('original/source.json',originals)]}],targets:[{id:family+':A',target_id:'old-owner',pixelIndex:1,source_family:family,base_geometry:features[0].geometry,source_receipt_sha256:pin('original/physical.json',originals).sha256,coverage_classes:['mapped_land_support']}],
  source_membership:{index:pin('data/world-index.json',originals),lineage:pin('data/semantic-report.json',originals),parts:[pin('data/geography/fixture.json',originals)]}};
 write('original/evidence.json',evidence);const ev=f.commit(),operands={source_evidence:pin('original/evidence.json',ev),native_patch:pin('original/native-patch.json',originals)};
 write('original/rule.json',{version:1,kind:'source-target-native-rule-v1',...operands});write('original/binding.json',{version:1,kind:'source-target-native-custody-v1',...operands});const authority=f.commit();
 const entry={policy_id:'retained-source-literal-additions',policy_version:1,rule_preimage:pin('original/rule.json',authority),rule_sha256:pin('original/rule.json',authority).sha256,source_authority:pin('original/binding.json',authority)};entry.authority_sha256=valueSha(entry);
 const proof=readRetainedRegistryAuthority(new ImmutableReader(f.repo,authority),entry),registry={version:1,kind:'retained-rule-authority-registry-v1',entries:[entry]};
 const ledger={...proof.original_ledger,version:2,kind:'native-additive-repair-ledger-v2',authority_registry_sha256:valueSha(registry),rows:proof.original_ledger.rows.map(row=>({...row,authority_sha256:entry.authority_sha256}))};delete ledger.rule_sha256;
 write('selected/registry.json',registry);write('selected/ledger.json',ledger);const l=f.commit();
 const components=ledger.rows.filter(row=>['assigned','zero-cell'].includes(row.disposition)).map(row=>({...row,rule_sha256:entry.rule_sha256}));
 const effective={...reference,footprints_sha256:valueSha({domain:'worldatlas-effective-native-footprints:v2',base_reference:reference,authority_registry_sha256:valueSha(registry),ledger_sha256:pin('selected/ledger.json',l).sha256,components})};
 const patch={version:2,kind:'unassigned-native-cells-v1',authority_registry_sha256:valueSha(registry),ledger_sha256:pin('selected/ledger.json',l).sha256,base_reference:reference,effective_reference:effective,rows:proof.native_proof.native_patches.flatMap(patch=>patch.rows)};
 write('selected/patch.json',patch);const p=f.commit(),assets={base_manifest:pin(selection.manifest_path,bank),owner_roster:ownersPin,ledger:pin('selected/ledger.json',l),patch:pin('selected/patch.json',p)};
 write('selected/envelope.json',{version:2,kind:'retained-native-base-plus-delta-v2',base_reference:reference,effective_reference:effective,...assets});const e=f.commit();
 write('selected/sidecar.json',{version:2,kind:'retained-native-additive-selection-v2',base_selection:selection,authority_registry:pin('selected/registry.json',l),logical_asset_map:assets,runtime_envelope:pin('selected/envelope.json',e)});const sc=f.commit(),side=pin('selected/sidecar.json',sc);
 write('data/ownership-selection.json',{...selection,additive_release:{path:side.path,bytes:side.bytes,sha256:side.sha256}});const selected=f.commit();
 return {...f,selected,y,x};
}

test('identical cold additive selections use one whole native acquisition and retain actual custody',()=>{
 for(const options of [{transport:false},{transport:true},{empty:true}]){
  const f=additiveComparisonFixture(options);try{
   f.write('unrelated.json',{nongeographic:true});const candidate=f.commit();
   const opens=[],read=ImmutableReader.prototype.read;
   ImmutableReader.prototype.read=function(name,options){if(name.includes('/ownership/runs-')||name.includes('/bank/group/'))opens.push([this.version,name]);return read.call(this,name,options);};
   let result;try{result=inspectSelected(f.repo,f.selected,candidate);}finally{ImmutableReader.prototype.read=read;}
   assert.equal(result.affected_rows,1);assert.equal(result.phases.length,1);assert.equal(result.lost_or_reassigned_cells,0);
   const phase=result.phases[0];assert.equal(phase.candidate.reused_baseline_acquisition,true);assert.equal(Object.hasOwn(phase,'baseline_carried_bytes'),false);
   assert.deepEqual(phase.candidate.rows,[f.y]);assert.equal(phase.baseline.whole_inputs.length===0,!!options.empty);
   if(!options.transport&&!options.empty)assert.equal(opens.filter(([,name])=>name.includes('/ownership/runs-')).length,1,'one complete ordinary run member, rather than baseline plus candidate');
   if(options.transport)assert.equal(opens.filter(([commit])=>commit===f.selected).length-opens.filter(([commit])=>commit===candidate).length,phase.baseline.whole_inputs.length,'only baseline acquires the complete run-containing fragments after both row tables');
   assert.ok(phase.baseline.whole_inputs.every(pin=>pin.commit===f.selected),'retain actual baseline snapshot custody');
   assert.equal(opens.filter(([commit,name])=>commit===candidate&&name.includes('/ownership/runs-')).length,0);
   assert.equal(result.additive_conservation.appended_authorities,0);
  }finally{f.cleanup();}
 }
});

test('new ordinary shadow of identical transport member retains separate actual acquisition',()=>{
 const f=additiveComparisonFixture({transport:true});try{
  const name='native-v1/ownership/runs-0.bin.gz';
  f.write('data/canonical-grid/transport/'+name,fs.readFileSync(path.join(f.repo,'data/canonical-grid/fixture',name)));const candidate=f.commit();
  const result=inspectSelected(f.repo,f.selected,candidate),phase=result.phases[0];
  assert.equal(result.lost_or_reassigned_cells,0);assert.equal(phase.candidate.reused_baseline_acquisition,undefined);
  assert.equal(phase.candidate.whole_inputs.length,1);assert.equal(phase.candidate.whole_inputs[0].path,'data/canonical-grid/transport/'+name);
  assert.equal(phase.candidate.whole_inputs[0].commit,candidate);assert.equal(Object.hasOwn(phase,'baseline_carried_bytes'),false);
 }finally{f.cleanup();}
});

test('identical cold additive selection still rejects same-owner native overlap',()=>{
 const f=additiveComparisonFixture({overlap:true});try{
  f.write('unrelated.json',{nongeographic:true});const candidate=f.commit();
  assert.throws(()=>inspectSelected(f.repo,f.selected,candidate),/Selected additive delta overlaps preexisting assigned native cells/);
 }finally{f.cleanup();}
});

test('identical cold additive selection still rejects an unregistered native owner',()=>{
 const f=additiveComparisonFixture({invalidOwner:true});try{
  f.write('unrelated.json',{nongeographic:true});const candidate=f.commit();
  assert.throws(()=>inspectSelected(f.repo,f.selected,candidate),/Invalid complete owner interval/);
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
