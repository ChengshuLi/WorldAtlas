// Normal package data installation after the explicit live-validation or
// independently qualified immutable-artifact consumption authority.
// No producer, geometry kernel, or stock ownership codec is replaced here.
import assert from 'node:assert/strict';
import fs from 'node:fs';import path from 'node:path';import {createHash} from 'node:crypto';import {gunzipSync} from 'node:zlib';
import {restoreWholeImage} from '../eastern-two-gap-repair-native-20261007/whole-image.mjs';
import {continueTemporalBucket} from './temporal-runtime-binding.mjs';
import {continueRetainedProductIndex} from './retained-product-binding.mjs';
import {readPreparedEvidenceBundle} from '../../../scripts/read-prepared-evidence-bundle.mjs';
import {requireArcticContinuation} from './arctic-context.mjs';
import {requireConsumedArcticArtifacts} from './qualified-artifact-consumer.mjs';
const N='coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008';
const sha=b=>createHash('sha256').update(b).digest('hex');
function body(root,pin){
 assert(!path.isAbsolute(pin.path)&&pin.path.split('/').every(s=>s&&s!=='.'&&s!=='..'));
 assert(Number.isSafeInteger(pin.bytes)&&pin.bytes<=32*1024*1024);
 const file=path.join(root,pin.path);for(let p=file;;p=path.dirname(p)){assert(!fs.lstatSync(p).isSymbolicLink());if(p===path.dirname(p))break}
 const before=fs.lstatSync(file);assert(before.isFile()&&(before.mode&511)===420&&before.size===pin.bytes);
 const fd=fs.openSync(file,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW);let raw;
 try{for(const k of ['dev','ino','size','mode','mtimeMs','ctimeMs'])assert.equal(before[k],fs.fstatSync(fd)[k]);raw=fs.readFileSync(fd);for(const k of ['dev','ino','size','mode','mtimeMs','ctimeMs'])assert.equal(before[k],fs.fstatSync(fd)[k]);}finally{fs.closeSync(fd)}
 const after=fs.lstatSync(file);for(const k of ['dev','ino','size','mode','mtimeMs','ctimeMs'])assert.equal(before[k],after[k]);assert.equal(sha(raw),pin.sha256);return raw;
}
function write(root,relative,raw){
 assert(!path.isAbsolute(relative)&&relative.split('/').every(s=>s&&s!=='.'&&s!=='..'));assert(raw.length<=32*1024*1024);const file=path.join(root,relative);
 for(let p=path.dirname(file);;p=path.dirname(p)){try{const stat=fs.lstatSync(p);assert(stat.isDirectory()&&!stat.isSymbolicLink());}catch(error){if(error.code!=='ENOENT')throw error;}if(p===path.dirname(p))break}
 fs.mkdirSync(path.dirname(file),{recursive:true});const temporary=file+'.n2-install';for(const target of [temporary,file]){let existing;try{existing=fs.lstatSync(target)}catch(error){if(error.code!=='ENOENT')throw error;}if(target===temporary)assert(!existing,'Fresh installer temporary entry required');else if(existing)assert(existing.isFile()&&!existing.isSymbolicLink()&&(existing.mode&511)===420);} fs.writeFileSync(temporary,raw,{flag:'wx',mode:0o644});fs.renameSync(temporary,file);assert.equal(sha(fs.readFileSync(file)),sha(raw));
}
export async function installV9Stage({root,stage,context}){
 assert.equal(process.env.WORLDATLAS_PACKAGE_STAGE,root);assert.equal(fs.realpathSync(root),root);assert.notEqual(root,fs.realpathSync(process.env.WORLDATLAS_PACKAGE_SOURCE_ROOT));
 const artifact=context.kind==='authenticated-qualified-artifact-consumption-v1';
 const success=artifact?requireConsumedArcticArtifacts(context):requireArcticContinuation(context);assert.equal(success.manifest_sha256,stage.nativeManifest.sha256);assert.equal(success.release_id,stage.release_id);
 const manifestRaw=body(root,stage.nativeManifest),manifest=JSON.parse(manifestRaw),indexPin=manifest.native_asset_transport.index;
 const indexRaw=body(root,indexPin),index=JSON.parse(indexRaw);assert.equal(index.files.length,56);assert.equal(index.whole_bytes,47604645);
 const pixelPin={path:N+'/pixel-audit-v9.json',bytes:14325660,sha256:'fb87c4b48428579bb039337c3bd70180844ad6c5d0f14e03d57048215e99deda'};
 const proposed={path:'coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/selected-geography/part-29.json.gz',bytes:3399520,sha256:'5f76a01a2c43eeccb3a202507faf593f56157fe38bd89f541be3b64145bdb1a8'};
 const oldPins=[{path:'data/pixel-audit.json',bytes:14323438,sha256:'a49773818f963c15c27b52a0cad7be6dabcb6dddf9523bdbc253118e177c9cd8'},{path:'data/geography/part-29.json',bytes:12932407,sha256:'c34114912dc620dce0821e251877470b5a83385ab3bf1284408f077b78bbdec8'},{path:'data/granularity-audit.json',bytes:10365238,sha256:'dec8c12a40a8f6d59ba5924cf52262c6831151f741f73863d3118bf5f9ff19c5'}];
 // Actual normal-package union: no invented scientific aggregate limit. All
 // ordinary members retain32MiB cap; input/decode/output costs are reported.
 const retainedPins=[{path:'data/prepared-evidence/index.json',bytes:14987,sha256:'b233282e4ea3f3e51658f6f1a272e995ddf93823c9f74759e1a353261c3baa5e'},{path:'data/reference-attributes/index.json',bytes:36740,sha256:'e21a5361d7ab74f8c9a909b681c6eda0d0c6c1e1becf36154bcf5b4b2215c356'}];
 const retainedIndices=retainedPins.map(p=>JSON.parse(body(root,p)));
 // The unchanged stock reader verifies all prepared payload/import bodies before
 // binding their retained same-ID records to the new physical reference.
 assert.deepEqual(await readPreparedEvidenceBundle(path.join(root,'data/prepared-evidence')),retainedIndices[0]);
 const continuedIndices=retainedIndices.map((index,i)=>continueRetainedProductIndex(index,{context,kind:i===0?'prepared-evidence':'reference-attributes'}));
 const ownerPin={path:'data/ownership-history/index.json',bytes:587478,sha256:'5ebc361385644f3a3069daafa2202403a47ec574bb723f82b68fa229a4c875fc'};
 const runtimePin={path:'data/ownership-runtime/index.json',bytes:789596,sha256:'6b900c855bb221fd1070b106d53432b362b0ef1128c92f765c4c29c9077541d8'};
 const ownerRaw=body(root,ownerPin),runtimeRaw=body(root,runtimePin),runtime=JSON.parse(runtimeRaw);
 assert.equal(runtime.source_index_sha256,ownerPin.sha256);assert.equal(runtime.shared.footprints_sha256,'b9a3c8bf375217dba3a50d1a022ec7e4ac6c6f1cdedff22845da953c805b7433');
 const nextOwner=Buffer.from(JSON.stringify(continueRetainedProductIndex(JSON.parse(ownerRaw),{context,kind:'ownership-history'}))+'\n'),nextOwnerSha=sha(nextOwner);
 const nextRuntime=structuredClone(runtime),temporalProofs=[];nextRuntime.source_index_sha256=nextOwnerSha;nextRuntime.footprints_sha256=manifest.footprints_sha256;nextRuntime.shared.footprints_sha256=manifest.footprints_sha256;
 // All original temporal gzip bodies are authenticated before any replacement.
 for(const bucket of runtime.buckets)body(root,{path:'data/ownership-runtime/'+bucket.path,bytes:bucket.compressed_bytes,sha256:bucket.sha256});
 const old=oldPins.map(p=>body(root,p));const audit=JSON.parse(old[2]);assert.equal(audit.input_sha256['geography/part-29.json'],oldPins[1].sha256);assert.equal(audit.issues.length,0);
 const pixel=body(root,pixelPin),compressed=body(root,proposed);const geometry=gunzipSync(compressed,{maxOutputLength:12932723});assert.equal(geometry.length,12932723);assert.equal(sha(geometry),'4eca02f85d5e3a0974a96a38d59e46b0b71b41d2513dcf20ab27eb17fd5a0b4c');
 const registry=JSON.parse(gunzipSync(body(root,stage.registry),{maxOutputLength:stage.registry.decoded_bytes}));
 const releases=registry.batches.slice(-343);assert.equal(releases.length,343);
 for(const p of releases)body(root,{path:N+'/release-v9/'+p.path,bytes:p.bytes,sha256:p.sha256});
 // Every original gzip stays immutable; restore authentic full compressed
 // native assets into a FRESH temporary tree then install the56 exact files.
 let image;
 if(artifact)image=success.nativeImage;
 else{const temporary=fs.mkdtempSync(path.join(root,'.cache/native-v9-install-'));image=path.join(temporary,'image');restoreWholeImage(path.dirname(path.join(root,indexPin.path)),image,{expectedIndexSha:indexPin.sha256});}
 assert.deepEqual(index.files.map(p=>p.path).sort(),manifest.parts.map(p=>p.path).sort());
 for(const pin of index.files){const part=manifest.parts.find(p=>p.path===pin.path);assert.equal(pin.bytes,part.bytes);assert.equal(pin.sha256,part.sha256);assert.equal(pin.mode,'100644');}
 for(const pin of index.files){const raw=body(image,pin);write(root,N+'/native-v9/'+pin.path,raw);}
 // All old302 getters have finished. Preserve old installed bodies separately
 // before changing normal global data paths in this ephemeral stage.
 for(let i=0;i<oldPins.length;i++)write(root,'.cache/n2-preserved-v8/'+oldPins[i].path,old[i]);
 audit.input_sha256['geography/part-29.json']=sha(geometry);audit.reference_correction={...audit.reference_correction,successor:{issue:1520,changed_ids:context.receipt.migration.changed_ids,geometry_receipt_sha256:stage.migrationReceipt.sha256,complete_constructed_source_proof:true,global_audit_reexecuted:false}};
 write(root,'.cache/n2-preserved-v8/'+ownerPin.path,ownerRaw);write(root,'.cache/n2-preserved-v8/'+runtimePin.path,runtimeRaw);
 for(let i=0;i<runtime.buckets.length;i++){const bucket=runtime.buckets[i];const rebound=continueTemporalBucket(body(root,{path:'data/ownership-runtime/'+bucket.path,bytes:bucket.compressed_bytes,sha256:bucket.sha256}),bucket,{originalSourceSha:ownerPin.sha256,currentSourceSha:nextOwnerSha});
  const name='v9-'+nextOwnerSha+'/'+bucket.path;nextRuntime.buckets[i]={...rebound.pin,path:name};write(root,'data/ownership-runtime/'+name,rebound.bytes);temporalProofs.push({...rebound.proof,original_path:bucket.path,successor_path:name});}
 write(root,ownerPin.path,nextOwner);write(root,runtimePin.path,Buffer.from(JSON.stringify(nextRuntime)+'\n'));
 write(root,'.cache/n2-temporal-header-continuation.json',Buffer.from(JSON.stringify({version:1,issue:1520,old_source_index_sha256:ownerPin.sha256,new_source_index_sha256:nextOwnerSha,all_original_paths_retained:true,proofs:temporalProofs})+'\n'));
 for(let i=0;i<retainedPins.length;i++){write(root,'.cache/n2-preserved-v8/'+retainedPins[i].path,body(root,retainedPins[i]));write(root,retainedPins[i].path,Buffer.from(JSON.stringify(continuedIndices[i])+'\n'));}
 write(root,'data/geography/part-29.json',geometry);write(root,'data/pixel-audit.json',pixel);write(root,'data/granularity-audit.json',Buffer.from(JSON.stringify(audit)+'\n'));
 for(const p of releases)write(root,'data/geographic-releases/'+p.path,body(root,{path:N+'/release-v9/'+p.path,bytes:p.bytes,sha256:p.sha256}));
 return {kind:artifact?'ephemeral-after-qualified-artifact-consumption':'ephemeral-after-three-live-validations',native_parts:56,old_native_urls_preserved:true,release_products:343,old_global_bodies_preserved:oldPins.map(p=>({...p,path:'.cache/n2-preserved-v8/'+p.path})),scientific_producers_invoked:false,normal_package_aggregate_cap_invented:false};
}
