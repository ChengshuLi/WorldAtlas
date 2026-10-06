// Lossless offline transport repack. Source files and release definitions stay intact.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gzipSync,gunzipSync} from 'node:zlib';
import {readGeographicReleaseManifest,decodeGeographicReleaseBatch} from '../../../scripts/read-geographic-release-manifest.mjs';
import {geographicMembershipHash} from '../../../hosted/geographic-releases.js';
import {requirePlainExecution,committedPreparationFiles,candidateBudget} from '../../../scripts/native-ownership/native-preparation-guards.mjs';

requirePlainExecution();
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
const prefix='coordination/engineering/iran-pakistan-offline-integration-991-20261006-local22';
const options={};
for(let i=2;i<process.argv.length;i+=2){assert.ok(['--out'].includes(process.argv[i])&&process.argv[i+1]&&!options[process.argv[i]],'Use optional --out fresh/owned/output');options[process.argv[i]]=process.argv[i+1];}
const out=path.resolve(root,options['--out']??prefix+'/repacked-release-v1');
assert.ok(out.startsWith(path.join(root,prefix)+path.sep)&&!fs.existsSync(out),'Fresh owned output required');
for(let parent=path.dirname(out);parent!==root;parent=path.dirname(parent)){assert.ok(parent.startsWith(root+path.sep));const stat=fs.lstatSync(parent);assert.ok(stat.isDirectory()&&!stat.isSymbolicLink());}
const head=execFileSync('git',['-C',root,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
const producer=committedPreparationFiles(root,head,[prefix+'/repack-successor-batches.mjs','scripts/read-geographic-release-manifest.mjs','scripts/native-ownership/native-preparation-guards.mjs','hosted/geographic-releases.js','package.json','package-lock.json']);
const ledger=candidateBudget([]),inputs=new Map(),outputs=[];
const MAX=32*1024*1024,PAYLOAD_LIMIT=900000,sha=raw=>createHash('sha256').update(raw).digest('hex');
const originalCommit='d0cc67eac85038159f88a673acbc39b77ab7461d';
const directory='data/geographic-releases';
function safe(name){assert.ok(typeof name==='string'&&!path.posix.isAbsolute(name)&&name.split('/').every(p=>/^[a-zA-Z0-9._-]+$/.test(p)&&p!=='.'&&p!=='..'),'Safe ordinary path required');}
function read(name,commit=head,{local=false}={}){
  safe(name);assert.match(commit,/^[a-f0-9]{40}$/);const key=commit+':'+name;
  const tree=execFileSync('git',['-C',root,'ls-tree','-z',commit,'--',name],{encoding:'utf8'});
  assert.ok(/^100644 blob /.test(tree)&&tree.slice(tree.indexOf('\t')+1)===name+'\0','Committed ordinary input required');
  const bytes=Number(execFileSync('git',['-C',root,'cat-file','-s',key],{encoding:'utf8'}));assert.ok(bytes<=MAX);
  const raw=execFileSync('git',['-C',root,'show',key],{maxBuffer:MAX});assert.equal(raw.length,bytes);
  const pin={commit,path:name,bytes,sha256:sha(raw)};
  if(inputs.has(key))assert.deepEqual(inputs.get(key),pin);else{ledger.add(pin);inputs.set(key,pin);}
  if(local){const filename=path.join(root,name),stat=fs.lstatSync(filename);assert.ok(stat.isFile()&&fs.realpathSync(filename)===filename);assert.ok(fs.readFileSync(filename).equals(raw),'Actual resolver input differs from immutable commit: '+name);}
  return raw;
}
for(const pin of producer)read(pin.path,head,{local:true});
const indexRaw=read(directory+'/index.json',head,{local:true});
const pointerRaw=read(directory+'/current-manifest.json',head,{local:true}),pointer=JSON.parse(pointerRaw);safe(pointer.path);
const registryRaw=read(directory+'/'+pointer.path,head,{local:true});assert.equal(sha(registryRaw),pointer.sha256);assert.equal(sha(indexRaw),pointer.predecessor_index_sha256);
const registry=readGeographicReleaseManifest(path.join(root,directory));
const originalIndex=read(directory+'/index.json',originalCommit);
const originalPointer=JSON.parse(read(directory+'/current-manifest.json',originalCommit));safe(originalPointer.path);
const originalRegistryRaw=read(directory+'/'+originalPointer.path,originalCommit);
assert.equal(sha(originalIndex),originalPointer.predecessor_index_sha256);assert.equal(sha(originalRegistryRaw),originalPointer.sha256);
const prior=JSON.parse(gunzipSync(originalRegistryRaw,{maxOutputLength:MAX}));
const release=registry.releases.at(-1);assert.equal(release.version,7);assert.equal(prior.releases.at(-1).version,6);
assert.equal(release.id,'geography:review:2632d51da0efa5574c74638afe441c4efd5f29e93804c507a24cc6dbb56c0199');
assert.deepEqual(registry.releases.slice(0,-1),prior.releases,'All predecessor release definitions must remain intact');
assert.deepEqual(registry.batches.slice(0,prior.batches.length),prior.batches,'Complete predecessor batch array must remain intact');
assert.deepEqual(registry.sources_batches.slice(0,prior.sources_batches.length),prior.sources_batches);
const successor=registry.batches.slice(prior.batches.length);
const memberships=successor.filter(p=>/^7-memberships-\d+\.json\.gz$/.test(p.path));
assert.equal(memberships.length,340,'Only the original fragmented release-7 transport is supported');
assert.ok(registry.batches.filter(p=>p.path.startsWith('7-memberships-')).length===memberships.length);
const removedNames=new Set(memberships.map(p=>p.path));
const retained=registry.batches.filter(p=>!removedNames.has(p.path));
const unchangedPayloadNames=new Set([...registry.sources_batches,...successor.filter(p=>!removedNames.has(p.path)).map(p=>p.path)]);
for(const name of unchangedPayloadNames){
  const descriptor=registry.batches.find(p=>p.path===name);assert.ok(descriptor);
  const raw=read(directory+'/'+name,head,{local:true});decodeGeographicReleaseBatch(raw,descriptor);
}
const rows=[],originalBatches=[];
for(const descriptor of memberships){
  assert.equal(descriptor.route,'/api/geography/stage');
  const raw=read(directory+'/'+descriptor.path,head,{local:true});const decoded=decodeGeographicReleaseBatch(raw,descriptor);assert.ok(decoded.length<=1024*1024);
  const payload=JSON.parse(decoded);assert.deepEqual(Object.keys(payload).sort(),['ingestion_id','memberships','release_id']);assert.equal(payload.release_id,release.id);
  assert.equal(payload.ingestion_id,release.id+':memberships:'+rows.length);assert.equal(descriptor.path,'7-memberships-'+rows.length+'.json.gz');
  assert.ok(Array.isArray(payload.memberships)&&payload.memberships.length);
  originalBatches.push({...descriptor,bytes:raw.length,payload_bytes:decoded.length,rows:payload.memberships.length,ingestion_id:payload.ingestion_id});rows.push(...payload.memberships);
}
assert.equal(rows.length,84833,'Complete ordered successor membership inventory required');
assert.equal(await geographicMembershipHash(rows),release.membership_sha256,'Actual independent release membership contract must match');
const rowJSON=rows.map(row=>JSON.stringify(row));
function orderedHash(items){const hash=createHash('sha256').update('[');items.forEach((item,i)=>{if(i)hash.update(',');hash.update(item);});return hash.update(']').digest('hex');}
const orderedRowsHash=orderedHash(rowJSON),releaseJSON=JSON.stringify(release);
const names=new Set(registry.batches.map(p=>p.path)),oldIngestionIDs=new Set(originalBatches.map(p=>p.ingestion_id));
const newDescriptors=[],newProducts=[];
function write(name,raw){safe(name);assert.ok(!name.includes('/')&&raw.length<=MAX);ledger.add({bytes:raw.length});fs.writeFileSync(path.join(out,name),raw,{flag:'wx'});const pin={path:name,bytes:raw.length,sha256:sha(raw)};assert.ok(fs.readFileSync(path.join(out,name)).equals(raw),'Exact output byte readback required');outputs.push(pin);return pin;}
fs.mkdirSync(out);
const ingestion=(start,digest)=>release.id+':memberships:repacked:'+start+':'+digest;
let start=0,group=[],groupBytes=0;
function overhead(at){return Buffer.byteLength(JSON.stringify({release_id:release.id,memberships:[],ingestion_id:ingestion(at,'0'.repeat(64))}));}
function flush(){
  if(!group.length)return;
  const digest=orderedHash(group.map(row=>JSON.stringify(row))),ingestionID=ingestion(start,digest),name='7-memberships-repacked-'+start+'.json.gz';
  assert.ok(!names.has(name)&&!oldIngestionIDs.has(ingestionID));names.add(name);oldIngestionIDs.add(ingestionID);
  const payload=Buffer.from(JSON.stringify({release_id:release.id,memberships:group,ingestion_id:ingestionID}));assert.ok(payload.length<=PAYLOAD_LIMIT);
  const encoded=gzipSync(payload,{level:9}),pin=write(name,encoded);
  const descriptor={path:name,route:'/api/geography/stage',encoding:'gzip',sha256:pin.sha256,payload_sha256:sha(payload)};
  const actual=JSON.parse(decodeGeographicReleaseBatch(fs.readFileSync(path.join(out,name)),descriptor));assert.equal(actual.release_id,release.id);assert.equal(actual.ingestion_id,ingestionID);
  assert.equal(actual.memberships.length,group.length);for(let i=0;i<group.length;i++)assert.equal(JSON.stringify(actual.memberships[i]),rowJSON[start+i],'Exact original row value, key order and sequence required');
  newDescriptors.push(descriptor);newProducts.push({...pin,payload_bytes:payload.length,payload_sha256:sha(payload),first_row:start,rows:group.length,ingestion_id:ingestionID});
  start+=group.length;group=[];groupBytes=0;
}
for(let i=0;i<rows.length;i++){
  const bytes=Buffer.byteLength(rowJSON[i]);
  if(group.length&&overhead(start)+groupBytes+bytes+group.length>PAYLOAD_LIMIT)flush();
  assert.ok(overhead(start)+bytes<=PAYLOAD_LIMIT,'Single membership cannot exceed bounded payload');
  group.push(rows[i]);groupBytes+=bytes;
}
flush();assert.equal(start,rows.length);assert.ok(newDescriptors.length<memberships.length);
// Keep the source/release/membership/changes import ordering, replacing only
// the old membership span with its complete new span.
let inserted=false;
const next={...registry,batches:registry.batches.flatMap(part=>{
  if(!removedNames.has(part.path))return [part];
  if(inserted)return [];
  inserted=true;return newDescriptors;
})};
for(const key of Object.keys(registry).filter(k=>k!=='batches'))assert.equal(JSON.stringify(next[key]),JSON.stringify(registry[key]),'Registry field JSON bytes changed: '+key);
assert.equal(JSON.stringify(next.releases.at(-1)),releaseJSON);assert.deepEqual(next.batches.slice(0,prior.batches.length),prior.batches);
assert.deepEqual(next.batches.filter(p=>!newDescriptors.some(n=>n.path===p.path)),retained);
const registryName='releases-v7-repacked-gzip.json.gz',nextDecoded=Buffer.from(JSON.stringify(next));assert.ok(nextDecoded.length<=MAX);
const registryProduct=write(registryName,gzipSync(nextDecoded,{level:9}));
const nextPointer={...pointer,path:registryName,sha256:registryProduct.sha256};
write('index.json',indexRaw);const pointerProduct=write('current-manifest.json',Buffer.from(JSON.stringify(nextPointer)+'\n'));
assert.deepEqual(readGeographicReleaseManifest(out),next,'Actual pointer/registry resolver must read the exact repacked registry');
const readback=[];
for(const descriptor of newDescriptors){const payload=JSON.parse(decodeGeographicReleaseBatch(fs.readFileSync(path.join(out,descriptor.path)),descriptor));for(const row of payload.memberships)readback.push(JSON.stringify(row));}
assert.equal(readback.length,rows.length);assert.equal(orderedHash(readback),orderedRowsHash);for(let i=0;i<rows.length;i++)assert.equal(readback[i],rowJSON[i]);
assert.equal(await geographicMembershipHash(readback.map(row=>JSON.parse(row))),release.membership_sha256);
const controls=[];
const corrupt=Buffer.from(fs.readFileSync(path.join(out,newDescriptors[0].path)));corrupt[corrupt.length-1]^=1;
assert.throws(()=>decodeGeographicReleaseBatch(corrupt,newDescriptors[0]),/hash mismatch/);
controls.push('Altered compressed bytes rejected by the existing release decoder');
const altered=readback.map(row=>JSON.parse(row));altered[0]={...altered[0],parent_id:'deliberately-wrong-parent-control'};
assert.notEqual(await geographicMembershipHash(altered),release.membership_sha256);
controls.push('Changed parent in otherwise well-formed rows rejected by the independent release membership hash');
assert.notEqual(orderedHash(readback.slice(1)),orderedRowsHash);
assert.notEqual(orderedHash([readback[1],readback[0],...readback.slice(2)]),orderedRowsHash);
controls.push('Omitted or reordered rows rejected by complete ordered-row comparison');
write('positive-control.json',Buffer.from(JSON.stringify({method_id:'lossless-release-transport-repack',kind:'positive',outcome:'passed',memberships:rows.length,ordered_membership_rows_sha256:orderedRowsHash,release_membership_sha256:release.membership_sha256})+'\n'));
write('negative-control.json',Buffer.from(JSON.stringify({method_id:'lossless-release-transport-repack',kind:'negative',outcome:'passed',controls})+'\n'));
// Recheck every unchanged actual source input after generation. No source data,
// original batch, source definition or predecessor manifest is overwritten.
for(const pin of inputs.values())if(pin.commit===head&&!producer.some(p=>p.path===pin.path))assert.equal(sha(fs.readFileSync(path.join(root,pin.path))),pin.sha256,'An actual source changed during repack');
const receipt={version:1,execution_commit:head,producer,inputs:[...inputs.values()],outputs,
  source_pointer:{path:directory+'/current-manifest.json',sha256:sha(pointerRaw)},source_registry:{path:directory+'/'+pointer.path,sha256:sha(registryRaw)},
  predecessor_commit:originalCommit,release_id:release.id,release_version:7,release_json_sha256:sha(releaseJSON),
  memberships:rows.length,ordered_membership_rows_sha256:orderedRowsHash,original_membership_batches:originalBatches,
  new_membership_batches:newProducts,unchanged_batch_descriptors:retained.length,original_membership_files_preserved:true,
  predecessor_release_objects_preserved:true,source_batches_and_metadata_preserved:true,nonmembership_payload_bytes_preserved:true,
  maximum_payload_bytes:PAYLOAD_LIMIT,payload_size_only_partitioning:true,row_count_cap:null,
  registry:registryProduct,pointer:pointerProduct,budget:ledger.snapshot(),runtime:{node:process.version,zlib:process.versions.zlib},
  installed:false,published:false,
  limits:['Offline transport repack preserves exact ordered membership row objects and release definitions; it grants no geographic/historical/publication approval.',
    'Original compressed batches and pointer/registry bytes remain in the committed source; staging, archival and any removal are separate root actions.',
    'All predecessor batch descriptors remain exact. Their unchanged payloads are referenced rather than reread en masse; source batches and successor nonmembership payloads are byte-checked.']};
let receiptRaw=Buffer.from(JSON.stringify(receipt)+'\n');
for(let pass=0;pass<4;pass++){const snapshot=ledger.snapshot();receipt.budget={...snapshot,accounted_bytes:snapshot.accounted_bytes+receiptRaw.length,accounted_descriptors:snapshot.accounted_descriptors+1};const nextRaw=Buffer.from(JSON.stringify(receipt)+'\n');if(nextRaw.length===receiptRaw.length){receiptRaw=nextRaw;break;}receiptRaw=nextRaw;}
assert.equal(receipt.budget.accounted_bytes,ledger.snapshot().accounted_bytes+receiptRaw.length);write('verification.json',receiptRaw);
console.log(JSON.stringify({release:release.id,memberships:rows.length,original_batches:memberships.length,repacked_batches:newDescriptors.length,ordered_rows_sha256:orderedRowsHash,budget:ledger.snapshot(),out}));
