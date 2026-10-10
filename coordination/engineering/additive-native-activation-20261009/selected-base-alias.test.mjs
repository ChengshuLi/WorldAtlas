import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync,spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gzipSync,gunzipSync} from 'node:zlib';
import {ImmutableReader,NativeAssetImage,loadSelection,inspectSelected,compareIntervals,compareRepairLedgers,readArtifactConsumption,validateReleaseCatalogue,validateArtifactSourceMetadata,loadNativeRowTable,acquireNativeRows,validateNativeRowCarry} from '../../../scripts/check-effective-geographic-regression.mjs';
import {shuffleOwnershipBytes} from '../../../src/ownership-codec.js';
import {valueBytes,valueSha,readOriginalRuleAuthority,selectedCoordinateShard,joinSelectedCoordinateCertificate,acceptColdCoordinateCertificate,selectedAffectedPlan,possibleNeighbors,compareVersionedRepairLedgers} from '../../../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';

const sha=b=>createHash('sha256').update(b).digest('hex'),root=process.cwd();
const retained=undefined;
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
  if(retained){const objects=[...new Set(git('rev-list','--objects',...issued).split('\n').map(row=>row.split(' ')[0]))].map(oid=>{const type=git('cat-file','-t',oid),body=execFileSync('git',['-C',repo,'cat-file',type,oid],{maxBuffer:32*1024*1024});assert.equal(createHash('sha1').update(Buffer.from(type+' '+body.length+'\0')).update(body).digest('hex'),oid);return {oid,type,bytes:body.length,sha256:sha(body),base64:body.toString('base64')};});const result={kind:'complete-synthetic-immutable-entry-fixture',commits:issued,objects,source_approval:false};fs.writeFileSync(path.join(retained,`fixture-${fixtureOrdinal++}.json.gz`),gzipSync(Buffer.from(JSON.stringify(result))),{flag:'wx'});}
  fs.rmSync(repo,{recursive:true,force:true});
 }};
}

import {selectedBaseAssetAlias} from '../../../scripts/check-effective-geographic-regression.mjs';
test('private selected base alias preserves actual complete graph and rejects foreign identities',()=>{
 const f=fixture();try{
 const head=f.select([[[0,1,1]],[[2,3,2]],[],[]]);
 const snapshot=loadSelection(new ImmutableReader(f.repo,head));
 const manifest=snapshot.manifest,encoded=execFileSync('git',['-C',f.repo,'show',manifest.original_assets.bounds.commit+':'+manifest.original_assets.bounds.path]),decoded=gunzipSync(encoded);
 const owners={mode:'100644',bytes:encoded.length,sha256:sha(encoded),decoded_bytes:decoded.length,decoded_sha256:sha(decoded)};
 const base={mode:'100644',bytes:execFileSync('git',['-C',f.repo,'show',head+':'+snapshot.selection.manifest_path]).length,sha256:snapshot.selection.sha256};
 assert.equal(selectedBaseAssetAlias(snapshot,'owner_roster',owners),snapshot.owners);
 assert.equal(selectedBaseAssetAlias(snapshot,'base_manifest',base),snapshot.manifest);
 assert.equal(Object.isFrozen(snapshot.owners[0]),true);
 assert.throws(()=>{snapshot.owners[0].id='foreign';},TypeError);
 assert.throws(()=>selectedBaseAssetAlias({...snapshot},'owner_roster',owners),/privately/);
 assert.throws(()=>selectedBaseAssetAlias(snapshot,'patch',owners),/Foreign/);
 assert.throws(()=>selectedBaseAssetAlias(snapshot,'owner_roster',{...owners,mode:'100755'}),/identity/);
 for(const field of ['bytes','sha256','decoded_bytes','decoded_sha256'])assert.throws(()=>selectedBaseAssetAlias(snapshot,'owner_roster',{...owners,[field]:typeof owners[field]==='number'?owners[field]+1:'0'.repeat(64)}),/identity/);
 assert.throws(()=>selectedBaseAssetAlias(snapshot,'base_manifest',{...base,decoded_bytes:base.bytes,decoded_sha256:base.sha256}),/identity/);
 assert.equal(snapshot.owners.length,2);assert.equal(snapshot.owners[0].id,'old-owner');
 }finally{f.cleanup();}
});

test('literal six-asset acquisition authenticates encoded aliases without duplicate decoding',()=>{
 const f=fixture();try{
 const head=f.select([[[0,1,1]],[[2,3,2]],[],[]]),selection=JSON.parse(fs.readFileSync(path.join(f.repo,'data/ownership-selection.json'))),manifest=JSON.parse(fs.readFileSync(path.join(f.repo,selection.manifest_path)));
 const prefix='coordination/engineering/alias-fixture/';
 const pin=(name,raw,decoded)=>{const full=prefix+name;f.write(full,raw);return {path:full,mode:'100644',bytes:raw.length,sha256:sha(raw),...(decoded?{decoded_bytes:decoded.length,decoded_sha256:sha(decoded)}:{})};};
 const bound=execFileSync('git',['-C',f.repo,'show',manifest.original_assets.bounds.commit+':'+manifest.original_assets.bounds.path]);
 const assets={base_manifest:pin('manifest.json',fs.readFileSync(path.join(f.repo,selection.manifest_path))),ledger:pin('ledger.json',Buffer.from('{}')),owner_roster:pin('owners.gz',bound,gunzipSync(bound)),patch:pin('patch.json',Buffer.from('{}'))};
 const envelope={version:2,kind:'retained-native-base-plus-delta-v2',base_reference:{},effective_reference:{},...assets};
 const runtime=pin('envelope.json',Buffer.from(JSON.stringify(envelope))),registry=pin('registry.json',Buffer.from('{}'));const commit=f.commit();
 for(const p of [runtime,registry,...Object.values(assets)])Object.assign(p,{commit,git_blob_oid:f.git('ls-tree',commit,'--',p.path).split(/[ \t]/)[2]});
 const sidecar={version:2,kind:'retained-native-additive-selection-v2',base_selection:selection,runtime_envelope:runtime,authority_registry:registry,logical_asset_map:assets};
 const raw=f.write(prefix+'sidecar.json',sidecar),final=f.commit(),snapshot=loadSelection(new ImmutableReader(f.repo,final)),hook={path:prefix+'sidecar.json',bytes:raw.length,sha256:sha(raw)};
 const source=fs.readFileSync('coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs','utf8');
 let body=source.slice(source.indexOf('export function readSelectedAdditive(snapshot) {')+'export function readSelectedAdditive(snapshot) {'.length,source.indexOf(' const {registry,envelope,named}=assetFrame();'));
 body=body.replace('hook=selection.additive_release','hook=providedHook');
 // Only the input hook is passed explicitly to this extracted asset boundary;
 // private snapshot authentication and all six production reads remain literal.
 const invoke=new Function('snapshot','providedHook','demand','hash','pinCheck','same','nativeBaseSelection','selectedBaseAssetAlias','gunzipSync','sha','FILE','PHASE','valueBytes',body+'return {...assetFrame(),canonical_inventory:valueBytes(admitted)};');
 const demand=(v,m)=>{if(!v)throw Error(m);},hash=v=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v),check=p=>{assert.equal(p.mode,'100644');assert.equal(p.bytes>0,true);};
 let reads=0;const original=snapshot.reader.read.bind(snapshot.reader);snapshot.reader.read=(...args)=>{reads++;return original(...args);};
 const result=invoke(snapshot,hook,demand,hash,check,(a,b)=>JSON.stringify(a)===JSON.stringify(b),s=>s,selectedBaseAssetAlias,gunzipSync,sha,33554432,268435456,valueBytes);
 assert.deepEqual(result.named,{ledger:{},patch:{}});assert.equal(reads,7);
 assert.equal(snapshot.reader.charged.get(commit+':'+assets.owner_roster.path),bound.length,'Alias still charges complete encoded body');
 assert.equal(snapshot.owners.length,2);
 assert.throws(()=>invoke({...snapshot},hook,demand,hash,check,(a,b)=>JSON.stringify(a)===JSON.stringify(b),s=>s,selectedBaseAssetAlias,gunzipSync,sha,33554432,268435456,valueBytes),/privately/);
 snapshot.reader.read=(name,options)=>{if(name===assets.owner_roster.path)return original(name,{...options,expected:'0'.repeat(64)});return original(name,options);};
 assert.throws(()=>invoke(snapshot,hook,demand,hash,check,(a,b)=>JSON.stringify(a)===JSON.stringify(b),s=>s,selectedBaseAssetAlias,gunzipSync,sha,33554432,268435456,valueBytes),/hash|SHA|differs/i);
 }finally{f.cleanup();}
});
