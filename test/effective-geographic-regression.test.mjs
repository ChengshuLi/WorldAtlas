import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync,spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gzipSync,gunzipSync} from 'node:zlib';
import {ImmutableReader,NativeAssetImage,loadSelection,inspectSelected,compareIntervals,compareRepairLedgers,readArtifactConsumption,validateReleaseCatalogue} from '../scripts/check-effective-geographic-regression.mjs';
import {shuffleOwnershipBytes} from '../src/ownership-codec.js';
import {valueBytes,valueSha,readOriginalRuleAuthority,selectedCoordinateShard,joinSelectedCoordinateCertificate,acceptColdCoordinateCertificate,selectedAffectedPlan,possibleNeighbors,compareVersionedRepairLedgers} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';

const sha=b=>createHash('sha256').update(b).digest('hex'),root=process.cwd();
const retained=process.env.WORLDATLAS_PREVENTION_CONTROLS;
if(retained){assert.equal(fs.realpathSync(path.dirname(retained)),path.dirname(retained));assert.equal(fs.existsSync(retained),false);assert.throws(()=>fs.lstatSync(retained),{code:'ENOENT'});fs.mkdirSync(retained);}
let fixtureOrdinal=0;
function fixture(){
 const repo=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'selected-geography-fixture-')));
 const git=(...args)=>execFileSync('git',['-C',repo,...args],{stdio:['ignore','pipe','pipe']}).toString().trim();
 git('init');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid');
 const write=(name,value)=>{const raw=Buffer.isBuffer(value)?value:Buffer.from(JSON.stringify(value));fs.mkdirSync(path.dirname(path.join(repo,name)),{recursive:true});fs.writeFileSync(path.join(repo,name),raw);return raw;};
 const issued=[];
 const commit=()=>{git('add','.');git('commit','-m','Whole immutable synthetic fixture');const head=git('rev-parse','HEAD');issued.push(head);return head;};
 // Copy only real executing namespaces; no dependencies, datasets or checkout.
 for(const name of ['scripts/run-geographic-check.py','scripts/check-effective-geographic-regression.mjs','scripts/check-geographic-regression.py','scripts/evidence/immutable.py','scripts/evidence/geometry.py','scripts/ellipsoidal_area.py','src/ownership-codec.js','coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs','coordination/engineering/selected-geography-effective-prevention-20261009/selected-continuous-entry.mjs'])write(name,fs.readFileSync(name));
 for(const name of ['package.json','requirements.txt','.github/evidence-policy.json'])write(name,fs.readFileSync(name));
 write('data/world-index.json',{parts:['geography/fixture.json']});write('data/geography/fixture.json',{type:'FeatureCollection',features:[]});
 write('data/hierarchy.json',[]);write('data/canonical-grid/manifest.json',{version:1});write('data/geographic-releases/index.json',{});
 const release=write('data/geographic-releases/release.json',{id:'geography:review:fixture'});
 write('data/geographic-releases/current-manifest.json',{path:'release.json',sha256:sha(release)});
 const owners=[{index:1,id:'old-owner',province_id:'parent',province_index:1},{index:2,id:'other-owner',province_id:'parent',province_index:1}];
 const bounds=write('data/canonical-grid/bounds.json.gz',gzipSync(Buffer.from(JSON.stringify(owners))));
 const origin=commit();
 const part=(kind,words)=>{const raw=Buffer.from(words.buffer),encoded=gzipSync(shuffleOwnershipBytes(words)),name=`native-v1/ownership/${kind}-0.bin.gz`;write('data/canonical-grid/fixture/'+name,encoded);return {kind,offset:0,words:words.length,path:name,bytes:encoded.length,sha256:sha(encoded),decoded_bytes:raw.length,decoded_sha256:sha(raw),encoding:'byte-shuffle'};};
 const select=(intervals,{extraSelection={},indices=false,badRows=false,transport=false,releaseId='geography:review:fixture'}={})=>{
  const rows=new Uint32Array(8),words=[];let cursor=0;
  for(let y=0;y<4;y++){rows[y*2]=cursor;rows[y*2+1]=(intervals[y]??[]).length;for(const [start,end,owner]of intervals[y]??[]){words.push(owner*4+start,end-1);cursor++;}}
  if(badRows)rows[2]++;
  const manifest={version:2,method:'native-linear-evenodd-first-owner-v1',size:4,coordinateBits:2,runWords:words.length,parts:[part('rows',rows),part('runs',Uint32Array.from(words))],geographic_release:releaseId,bounds:{sha256:sha(bounds),decoded_bytes:Buffer.byteLength(JSON.stringify(owners))},original_assets:{bounds:{role:'original-identity-parent-camera-context',commit:origin,path:'data/canonical-grid/bounds.json.gz',sha256:sha(bounds)}},native_latitudes:{sha256:'1'.repeat(64)}};
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
  if(retained){const objects=[...new Set(git('rev-list','--objects',...issued).split('\n').map(row=>row.split(' ')[0]))].map(oid=>{const type=git('cat-file','-t',oid),body=execFileSync('git',['-C',repo,'cat-file',type,oid]);assert.equal(createHash('sha1').update(Buffer.from(type+' '+body.length+'\0')).update(body).digest('hex'),oid);return {oid,type,bytes:body.length,sha256:sha(body),base64:body.toString('base64')};});const result={kind:'complete-synthetic-immutable-entry-fixture',commits:issued,objects,source_approval:false};fs.writeFileSync(path.join(retained,`fixture-${fixtureOrdinal++}.json.gz`),gzipSync(Buffer.from(JSON.stringify(result))),{flag:'wx'});}
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
 assert.throws(()=>compareRepairLedgers(ledger,{...ledger,scope_ids:[],rows:[]}),/lost\/rebound/);
 const changed=structuredClone(ledger);changed.rows[0].source_receipt_sha256='5'.repeat(64);assert.throws(()=>compareRepairLedgers(ledger,changed),/lost\/rebound/);
 assert.throws(()=>compareRepairLedgers(ledger,{...ledger,scope_ids:['x','x'],rows:[row,row]}),/duplicate/);
});

test('aggregate admission rejects before any actual body read',()=>{
 const reader=new ImmutableReader('.', '1'.repeat(40),{runtimeBytes:256*1024*1024-100,metadataBytes:0,outputBytes:0});let bodies=0;
 reader.descriptor=()=>({commit:'1'.repeat(40),path:'input',bytes:101});reader.git=()=>{bodies++;return Buffer.alloc(101);};
 assert.throws(()=>reader.read('input'),/prospective cap/);assert.equal(bodies,0);
 assert.throws(()=>reader.admit({commit:'1'.repeat(40),path:'input',bytes:1},32*1024*1024+1),/decoded member/);assert.equal(bodies,0);
});


test('complete bootstrap admission precedes runtime opens and trusted code reads',()=>{
 const stat=fs.statSync,open=fs.openSync,read=fs.readFileSync;let opens=0,reads=0;const node=fs.realpathSync(process.execPath);
 try{fs.statSync=(name,...args)=>{const value=stat(name,...args);return name===node?new Proxy(value,{get:(target,key)=>key==='size'?256*1024*1024-100:typeof target[key]==='function'?target[key].bind(target):target[key]}):value;};fs.openSync=(...args)=>{opens++;return open(...args);};fs.readFileSync=(...args)=>{reads++;return read(...args);};
  assert.throws(()=>inspectSelected('.', '1'.repeat(40),'1'.repeat(40)),/bootstrap exceeds prospective phase/);assert.equal(opens,0);assert.equal(reads,0);
 }finally{fs.statSync=stat;fs.openSync=open;fs.readFileSync=read;}
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
  reader.phase();assert.deepEqual(image.logical('native/'+members[1].path,members[1]),bodies[1]);
  assert.throws(()=>new NativeAssetImage(new ImmutableReader(f.repo,version),{...manifest,native_asset_transport:{...manifest.native_asset_transport,logical_assets:1}},'native/manifest.json'),/roster/);
  const changed={...index,files:[{...members[0],sha256:'0'.repeat(64)},members[1]]};const raw=f.write('bank/index.json',changed),coherent=f.commit();
  assert.throws(()=>new NativeAssetImage(new ImmutableReader(f.repo,coherent),{...manifest,native_asset_transport:{...manifest.native_asset_transport,index:{path:'bank/index.json',bytes:raw.length,sha256:sha(raw)}}},'native/manifest.json'),/Foreign\/rebound/);
  reader.phase();reader.used=256*1024*1024;let reads=0;const git=reader.git.bind(reader);reader.git=(...args)=>{if(args[0]==='cat-file'&&args[1]==='blob')reads++;return git(...args);};
  assert.throws(()=>image.logical('native/'+members[0].path,members[0]),/prospective cap/);assert.equal(reads,0,'whole containing fragments must be admitted before any body read');
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


test('selected continuous source consumes exact encoded override and rejects incomplete or stale maps',()=>{
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
  assert.throws(()=>possibleNeighbors(certificate,geometry,{excludeIds:['old-owner','other-owner']}),/SELF target/);
  assert.notDeepEqual(actual.body,execFileSync('git',['-C',f.repo,'show',current+':data/geography/fixture.json']),'historical ordinary path must never replace selected body');
  const cold=path.join(f.repo,'cold-coordinate-control'),entry=path.join(f.repo,'coordination/engineering/selected-geography-effective-prevention-20261009/selected-continuous-entry.mjs');
  const env={...process.env};delete env.NODE_OPTIONS;delete env.NODE_PATH;
  const invoke=dest=>spawnSync(process.execPath,['--expose-gc',entry,'coordinate',f.repo,current,current,dest],{env,encoding:'utf8'});
  const noGc=spawnSync(process.execPath,[entry,'coordinate',f.repo,current,current,cold+'-missing-gc'],{env,encoding:'utf8'});assert.notEqual(noGc.status,0);assert.match(noGc.stderr,/authenticated native GC/);assert.equal(fs.existsSync(cold+'-missing-gc'),false);
  const gcScript=path.join(f.repo,'gc-identity-drift-control.mjs');fs.writeFileSync(gcScript,`const m=await import(${JSON.stringify('file://'+entry)});globalThis.gc=()=>{};m.checkColdReclaimer();`);
  const gcDrift=spawnSync(process.execPath,['--expose-gc',gcScript],{env,encoding:'utf8'});assert.notEqual(gcDrift.status,0);assert.match(gcDrift.stderr,/authenticated native GC/);fs.unlinkSync(gcScript);
  const extraFlag=spawnSync(process.execPath,['--expose-gc','--require=node:fs',entry,'coordinate',f.repo,current,current,cold+'-extra-flag'],{env,encoding:'utf8'});assert.notEqual(extraFlag.status,0);assert.match(extraFlag.stderr,/authenticated native GC/);assert.equal(fs.existsSync(cold+'-extra-flag'),false);

  const emitted=invoke(cold);assert.equal(emitted.status,0,emitted.stderr);assert.equal(JSON.parse(emitted.stdout).complete_owners,2);
  const publication=JSON.parse(fs.readFileSync(path.join(cold,'publication.json'))),facts=fs.readFileSync(path.join(cold,'facts.json'));
  assert.equal(sha(facts),publication.facts.sha256);assert.equal(JSON.parse(facts).candidate_code_executed,false);
  const fullFacts=JSON.parse(facts),completeCertificate=JSON.parse(gunzipSync(fs.readFileSync(path.join(cold,'certificate.json.gz'))));
  assert.equal(fullFacts.source_certificate_domain,'complete-selected-source-pointsets:v1');assert.equal(fullFacts.historical_footprint_authority.recomputed,false);assert.equal(fullFacts.historical_footprint_authority.value,footprint);
  const accept=value=>acceptColdCoordinateCertificate(snapshot.geometrySources,value,{facts:fullFacts,expectedPublication:publication,publication,encoded_sha256:publication.certificate.sha256,decoded_sha256:publication.certificate.decoded_sha256});
  assert.equal(accept(structuredClone(completeCertificate)).entries.length,2);
  const altered=structuredClone(completeCertificate);altered.inputs[0].whole_body_sha256='0'.repeat(64);assert.throws(()=>accept(altered),/source body differs/);
  const omitted=structuredClone(completeCertificate);omitted.inputs=[];assert.throws(()=>accept(omitted),/Incomplete cold/);
  const reordered=structuredClone(completeCertificate);reordered.entries.reverse();assert.throws(()=>accept(reordered),/cold owner record/);
  const rebound=structuredClone(completeCertificate);rebound.inputs[0].source.sha256='0'.repeat(64);assert.throws(()=>accept(rebound),/drifted complete cold source/);
  const wrongEffective=structuredClone(completeCertificate);wrongEffective.entries[0][8]='0'.repeat(64);assert.throws(()=>accept(wrongEffective),/effective primitive set/);

  const collision=invoke(cold);assert.notEqual(collision.status,0);assert.match(collision.stderr,/already exists/);assert.equal(sha(fs.readFileSync(path.join(cold,'facts.json'))),publication.facts.sha256);
  const dangling=path.join(f.repo,'dangling-coordinate-control');fs.symlinkSync('/nonexistent-coordinate-fixture',dangling);const link=invoke(dangling);assert.notEqual(link.status,0);assert.match(link.stderr,/already exists/);assert.equal(fs.readlinkSync(dangling),'/nonexistent-coordinate-fixture');fs.unlinkSync(dangling);
  fs.rmSync(cold,{recursive:true});

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
  const limited=new ImmutableReader(f.repo,head,{runtimeBytes:268435455,metadataBytes:0,outputBytes:0});let opens=0;const git=limited.git.bind(limited);limited.git=(...args)=>{if(args[0]==='cat-file'&&args[1]==='blob')opens++;return git(...args);};assert.throws(()=>readOriginalRuleAuthority(limited,pins),/complete phase/i);assert.equal(opens,0);
  const missing={...pins};delete missing.source_request;assert.throws(()=>readOriginalRuleAuthority(open(),missing),/exact original rule body roster/);
 }finally{f.cleanup();}
});


test('cold selected continuous operands preserve complete neighbors and original loss/overlap comparisons',()=>{
 const f=fixture(),coldRoot=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'selected-continuous-output-fixture-')));try{
  const rect=(a,b)=>({type:'Polygon',coordinates:[[[a,0],[b,0],[b,1],[a,1],[a,0]]]});
  const features=geometry=>['old-owner','other-owner'].map((id,i)=>({type:'Feature',id,properties:{id,parent_id:'parent'},geometry:i?rect(2,3):geometry}));
  const hashFeatures=rows=>sha(Buffer.from(JSON.stringify(rows.map(r=>[r.id,r.geometry]).sort((a,b)=>a[0].localeCompare(b[0])))));
  const pin=(name,commit)=>{const raw=execFileSync('git',['-C',f.repo,'show',commit+':'+name]),[mode,,git_blob_oid]=f.git('ls-tree',commit,'--',name).split(/[ \t]/);return {commit,path:name,mode,git_blob_oid,bytes:raw.length,sha256:sha(raw)};};
  const install=(rows,releaseId)=>{
   const selected=f.select([[[0,1,1]],[[2,3,2]],[],[]],{transport:true,releaseId}),selection=JSON.parse(fs.readFileSync(path.join(f.repo,'data/ownership-selection.json'))),body=Buffer.from(JSON.stringify({type:'FeatureCollection',features:rows})),encoded=f.write('source/current.json.gz',gzipSync(body));
   const releases=f.write('data/geographic-releases/selected.json.gz',gzipSync(Buffer.from(JSON.stringify({releases:[{id:releaseId,footprints_sha256:hashFeatures(rows)}]}))));f.write('data/geographic-releases/current-manifest.json',{path:'selected.json.gz',sha256:sha(releases)});const origin=f.commit();
   const override={...pin('source/current.json.gz',origin),logical_path:'data/geography/fixture.json',encoding:'gzip',decoded_bytes:body.length,decoded_sha256:sha(body)},bank={version:1,kind:'complete-world-index-with-exact-encoded-overrides',release_id:releaseId,native_manifest_sha256:selection.sha256,footprints_sha256:hashFeatures(rows),locations:2,world_index:pin('data/world-index.json',selected),unchanged_files:[],overrides:[override]},raw=f.write('source/selected-bank.json',bank);
   f.write('data/ownership-selection.json',{...selection,selected_geography:{version:1,kind:bank.kind,path:'source/selected-bank.json',bytes:raw.length,sha256:sha(raw)}});return f.commit();
  };
  const baseline=install(features(rect(0,1)),'geography:review:before');
  const run=(candidate,name)=>{f.git('checkout',baseline);const entry=path.join(f.repo,'coordination/engineering/selected-geography-effective-prevention-20261009/selected-continuous-entry.mjs'),destination=path.join(coldRoot,'continuous-'+name),env={...process.env};delete env.NODE_OPTIONS;delete env.NODE_PATH;
   const result=spawnSync(process.execPath,[entry,'continuous',f.repo,baseline,baseline,candidate,destination],{env,encoding:'utf8'});assert.equal(result.status,0,result.stderr);const ack=JSON.parse(result.stdout),pub=JSON.parse(fs.readFileSync(path.join(destination,'publication.json')));assert.deepEqual(pub,ack.publication);
   const encoded=fs.readFileSync(path.join(destination,pub.operands.path));assert.equal(sha(encoded),pub.operands.sha256);return {ack,operands:JSON.parse(gunzipSync(encoded)),destination};};
  const gain=install(features(rect(0,1.5)),'geography:review:gain'),positive=run(gain,'gain');assert.deepEqual(positive.ack.changed_ids,['old-owner']);assert.deepEqual(Object.keys(positive.operands.baseline),['old-owner']);assert.equal(positive.operands.plan.source_bindings.baseline.sources.length,1);
  const lost=install(features(rect(0,.5)),'geography:review:loss'),negative=run(lost,'loss');assert.deepEqual(negative.ack.changed_ids,['old-owner']);
  const overlap=install(features(rect(0,2.5)),'geography:review:overlap'),conflict=run(overlap,'overlap');assert.deepEqual(conflict.ack.affected_ids,['old-owner','other-owner']);assert.deepEqual(conflict.operands.plan.pairs,[['old-owner','other-owner']]);
  // Invoke the actual trusted Python caller, not a duplicated polygon algorithm.
  const python=process.env.WORLDATLAS_TEST_PYTHON??process.env.PYTHON??(process.platform==='darwin'?'/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12':'python3');
  if(path.isAbsolute(python))assert.ok(fs.existsSync(python),'Actual original Python operator runtime is required for this control');
  {
   const driver="import importlib.util,json,pathlib,sys\nsys.path[:0]=json.loads(sys.argv[3])\nsys.path.insert(0,str(pathlib.Path(sys.argv[1])/'scripts'))\ns=importlib.util.spec_from_file_location('original',str(pathlib.Path(sys.argv[1])/'scripts/check-geographic-regression.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\nv=json.load(open(sys.argv[2]));print(json.dumps(m.compare(v['baseline'],v['candidate'])))";
   for(const [stage,expected]of [[positive,'no-new-regression'],[negative,'regressions-found'],[conflict,'regressions-found']]){const source=path.join(stage.destination,'plain-control.json');fs.writeFileSync(source,JSON.stringify(stage.operands));const result=spawnSync(python,['-I','-B','-c',driver,f.repo,source,JSON.stringify((process.env.WORLDATLAS_TEST_PYTHON_SITE_PATHS??(process.platform==='darwin'?'/Users/chengshuli/.local/lib/python3.12/site-packages:/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/lib/python3.12/site-packages':'')).split(path.delimiter).filter(Boolean))],{encoding:'utf8'});assert.equal(result.status,0,result.stderr);assert.equal(JSON.parse(result.stdout).status,expected);}
   const wrapper="import importlib.util,json,pathlib,sys\nsys.path[:0]=json.loads(sys.argv[4]);sys.path.insert(0,str(pathlib.Path(sys.argv[1])/'scripts'))\ndef load(n,p):\n s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m\nd=load('original',str(pathlib.Path(sys.argv[1])/'scripts/check-geographic-regression.py'));w=load('wrapper',str(pathlib.Path(sys.argv[1])/'scripts/run-geographic-check.py'));print(json.dumps(w.selected_continuous(pathlib.Path(sys.argv[1]),sys.argv[2],sys.argv[3],d)))";
   const sites=(process.env.WORLDATLAS_TEST_PYTHON_SITE_PATHS??(process.platform==='darwin'?'/Users/chengshuli/.local/lib/python3.12/site-packages:/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/lib/python3.12/site-packages':'')).split(path.delimiter).filter(Boolean);
   const result=spawnSync(python,['-I','-B','-c',wrapper,f.repo,baseline,overlap,JSON.stringify(sites)],{encoding:'utf8',env:{...process.env,NODE:process.execPath}});assert.equal(result.status,0,result.stderr);const enforced=JSON.parse(result.stdout);assert.equal(enforced.status,'regressions-found');assert.deepEqual(enforced.required_ids,['old-owner','other-owner']);assert.equal(enforced.candidate_code_executed,false);

  }
 }finally{fs.rmSync(coldRoot,{recursive:true,force:true});f.cleanup();}
});


test('renewed immutable artifact entry binds complete catalogue and independent authority',()=>{
 const directory=path.join(root,'coordination/engineering/selected-geography-effective-prevention-20261009/artifact-interface-controls/latest-999db');
 const rows=JSON.parse(fs.readFileSync(path.join(directory,'original-inputs.json'))).pins;
 const read=name=>fs.readFileSync(path.join(directory,name));
 for(const p of rows)assert.equal(sha(read(p.copy)),p.sha256);
 const certificate=JSON.parse(read('certificate.json')),catalogue=JSON.parse(gunzipSync(read('catalogue.json.gz'))),registry=JSON.parse(gunzipSync(read('registry.json.gz')));
 assert.deepEqual(validateReleaseCatalogue(certificate,catalogue,registry),{inline_roles:137,release_products:343,complete_roles:480});
 for(const [change,pattern]of [
  [(c,p)=>p.products.pop(),/Incomplete qualified/],
  [(c,p)=>p.products[1]=structuredClone(p.products[0]),/Duplicate/],
  [(c,p)=>p.products[0].path='foreign/product.gz',/ordered path/],
  [(c,p)=>[p.products[0],p.products[1]]=[p.products[1],p.products[0]],/ordered path/],
  [(c,p)=>p.products[0].sha256='0'.repeat(64),/encoded\/payload/],
  [(c,p)=>p.products[0].decoded_sha256='0'.repeat(64),/encoded\/payload/],
  [(c,p)=>delete p.products[0].decoded_bytes,/Incomplete whole/],
  [(c,p)=>p.products[0].decoded_bytes=33554433,/decoded role/],
  [(c)=>c.application_inputs.pop(),/exact inline/],
  [(c)=>c.application_inputs[1]=structuredClone(c.application_inputs[0]),/Duplicate/]
 ]) {const c=structuredClone(certificate),p=structuredClone(catalogue);change(c,p);assert.throws(()=>validateReleaseCatalogue(c,p,registry),pattern);}
 const f=fixture();try{
  for(const p of rows)f.write(p.path,read(p.copy));const head=f.commit();
  const selection=JSON.parse(read('selection.json')),manifest=JSON.parse(read('manifest.json'));
  const open=()=>new ImmutableReader(f.repo,head);
  const positive=readArtifactConsumption(open(),selection,manifest);assert.equal(positive.review_id,6079096820);assert.equal(positive.releaseCatalogue.complete_roles,480);
  for(const [change,pattern]of [
   [s=>s.artifact_consumption.certificate.sha256='0'.repeat(64),/differs/],
   [s=>s.artifact_consumption.review.sha256='0'.repeat(64),/independently registered/],
   [s=>s.artifact_consumption.review.sha256='79024f6fd9335b0ad9da0ed936f5eabc600188f6176d9f953ceb006946626dbd',/Historical artifact authority/],
   [s=>s.artifact_consumption.certificate.mode='100755',/whole artifact authority pin/],
   [s=>s.artifact_consumption.certificate.bytes--,/whole mode\/size differs/],
   [s=>s.sha256='0'.repeat(64),/Typed independent/],
   [s=>s.selected_geography.sha256='0'.repeat(64),/Selected source\/policy/],
   [s=>s.release_id='geography:foreign',/native\/release/],
   [s=>s.artifact_consumption.approved=true,/Unsupported artifact-consumption/]
  ]){const s=structuredClone(selection);change(s);assert.throws(()=>readArtifactConsumption(open(),s,manifest),pattern);}
 }finally{f.cleanup();}
});
