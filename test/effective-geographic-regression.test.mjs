import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync,spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {ImmutableReader,inspectSelected,compareIntervals,compareRepairLedgers} from '../scripts/check-effective-geographic-regression.mjs';
import {shuffleOwnershipBytes} from '../src/ownership-codec.js';

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
 for(const name of ['scripts/run-geographic-check.py','scripts/check-effective-geographic-regression.mjs','scripts/check-geographic-regression.py','scripts/evidence/immutable.py','scripts/evidence/geometry.py','scripts/ellipsoidal_area.py','src/ownership-codec.js'])write(name,fs.readFileSync(name));
 for(const name of ['package.json','requirements.txt','.github/evidence-policy.json'])write(name,fs.readFileSync(name));
 write('data/world-index.json',{parts:['geography/fixture.json']});write('data/geography/fixture.json',{type:'FeatureCollection',features:[]});
 write('data/hierarchy.json',[]);write('data/canonical-grid/manifest.json',{version:1});write('data/geographic-releases/index.json',{});
 const release=write('data/geographic-releases/release.json',{id:'geography:review:fixture'});
 write('data/geographic-releases/current-manifest.json',{path:'release.json',sha256:sha(release)});
 const owners=[{index:1,id:'old-owner',province_id:'parent',province_index:1},{index:2,id:'other-owner',province_id:'parent',province_index:1}];
 const bounds=write('data/canonical-grid/bounds.json.gz',gzipSync(Buffer.from(JSON.stringify(owners))));
 const origin=commit();
 const part=(kind,words)=>{const raw=Buffer.from(words.buffer),encoded=gzipSync(shuffleOwnershipBytes(words)),name=`native-v1/ownership/${kind}-0.bin.gz`;write('data/canonical-grid/fixture/'+name,encoded);return {kind,offset:0,words:words.length,path:name,bytes:encoded.length,sha256:sha(encoded),decoded_bytes:raw.length,decoded_sha256:sha(raw),encoding:'byte-shuffle'};};
 const select=(intervals,{extraSelection={},indices=false,badRows=false}={})=>{
  const rows=new Uint32Array(8),words=[];let cursor=0;
  for(let y=0;y<4;y++){rows[y*2]=cursor;rows[y*2+1]=(intervals[y]??[]).length;for(const [start,end,owner]of intervals[y]??[]){words.push(owner*4+start,end-1);cursor++;}}
  if(badRows)rows[2]++;
  const manifest={version:2,method:'native-linear-evenodd-first-owner-v1',size:4,coordinateBits:2,runWords:words.length,parts:[part('rows',rows),part('runs',Uint32Array.from(words))],geographic_release:'geography:review:fixture',bounds:{sha256:sha(bounds),decoded_bytes:Buffer.byteLength(JSON.stringify(owners))},original_assets:{bounds:{role:'original-identity-parent-camera-context',commit:origin,path:'data/canonical-grid/bounds.json.gz',sha256:sha(bounds)}},native_latitudes:{sha256:'1'.repeat(64)}};
  const raw=write('data/canonical-grid/fixture/manifest.json',manifest),digest=sha(raw);
  const products=[{path:'manifest.json',bytes:raw.length,sha256:digest},...manifest.parts];
  const receipt={method:manifest.method,checked_rows:4,checked_cells:16,unchecked_cells:0,checked_runs:words.length/2,installation_ready:false,products,two_run_products:products.length,run_one_sha256:sha(Buffer.from(JSON.stringify(products))),run_two_sha256:sha(Buffer.from(JSON.stringify(products)))};
  const receiptRaw=write('coordination/engineering/fixture/receipt.json',receipt),proofCommit=commit();
  write('scripts/native-ownership/verified-candidates.json',{version:1,candidates:{[digest]:{commit:proofCommit,path:'coordination/engineering/fixture/receipt.json',sha256:sha(receiptRaw),role:'reviewed-exhaustive-native-rule-comparison',installation_approval:false}}});
  write('data/ownership-selection.json',{version:1,method:manifest.method,manifest_path:'data/canonical-grid/fixture/manifest.json',sha256:digest,release_id:manifest.geographic_release,...extraSelection});
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
