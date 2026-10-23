import fs from 'node:fs';
import path from 'node:path';
import {gzipSync,gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {valueSha,valueBytes,coordinateBounds} from '../../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
import {nativeLiteral} from '../helpers/native-literal.mjs';
import {unshuffleOwnershipBytes} from '../../src/ownership-codec.js';
import {finalBankReference} from '../../src/reference-metadata.js';
import {ownershipMetadata} from '../../src/ownership-method.js';
import {finishEffectiveFootprint,extendFinishedNativeFootprint,mergeUnassignedNativeIntervals,finishedReleaseFootprintDigest} from '../../src/native-grid.js';
import {packageFinalStartupOwnership} from '../../scripts/package-startup-ownership.mjs';
import {prepareFinalBankStartupOwnership} from '../../scripts/prepare-startup-ownership.mjs';
const root='data/canonical-grid/current-startup',hash=b=>createHash('sha256').update(b).digest('hex');
function inventory(directory){return fs.readdirSync(directory,{recursive:true}).filter(n=>fs.statSync(path.join(directory,n)).isFile()&&n!=='index.json')
 .sort().map(name=>{const raw=fs.readFileSync(path.join(directory,name));return {path:name,bytes:raw.length,sha256:hash(raw)};});}
function copyCompatibility(f,prior,destination){for(const pin of prior.compatibility_files){const raw=f.git('show',f.bankCommit+':'+root+'/'+pin.path);
 const target=path.join(destination,pin.path);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,raw);}}
export async function oldBank(f,state){
 const destination=path.join(f.root,root);fs.mkdirSync(destination,{recursive:true});
 const native={...ownershipMetadata(f.manifest),native_latitudes:{...f.manifest.native_latitudes,transport_path:'native-v1/native-row-latitudes.f64le.gz'},
  canonical_grid_sha256:f.selection.sha256,parts:f.manifest.parts.map(p=>({...p,path:p.kind==='rows'?p.path:'ownership-vintages/'+f.selection.sha256+'/native-v1/ownership/startup-runs-0.bin.gz'}))};
 for(let i=0;i<native.parts.length;i++){const p=native.parts[i],raw=f.git('show',f.sidecar.logical_asset_map.base_manifest.commit+':'+path.posix.join(path.posix.dirname(f.selection.manifest_path),f.manifest.parts[i].path));
  const target=path.join(destination,p.path);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,raw);}
 const latitude=f.manifest.native_latitudes;const target=path.join(destination,native.native_latitudes.transport_path);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,f.git('show',latitude.commit+':'+latitude.path));
 const retired=path.join(destination,'native-v1/ownership/startup-runs-999.bin.gz');fs.writeFileSync(retired,Buffer.from('existing compatibility URL'));
 const compatibility=inventory(destination);
 const decode=p=>{const bytes=unshuffleOwnershipBytes(gunzipSync(f.git('show',f.sidecar.logical_asset_map.base_manifest.commit+':'+path.posix.join(path.posix.dirname(f.selection.manifest_path),p.path))),p.words);return new Uint32Array(bytes.buffer,bytes.byteOffset,bytes.byteLength/4);};
 const base={...native,rows:decode(f.manifest.parts[0]),runs:decode(f.manifest.parts[1])};
 const merged=mergeUnassignedNativeIntervals(base,nativeLiteral(state.patch.rows),{owners:new Set([1,2,3]),allowed:new Set([1,2,3])});
 const reference=f.envelope.effective_reference,ownerSha=hash(Buffer.from(JSON.stringify(f.features.map((p,i)=>[i+1,p.id]))));
 const ownership={...native,...merged,runWords:merged.runs.length,geographic_release:reference.id,footprints_sha256:reference.footprints_sha256,
  reference_owner_sha256:ownerSha};delete ownership.canonical_grid_sha256;
 const packaged=await packageFinalStartupOwnership({ownership,destination,expectedReference:reference});
 const components=nativeLiteral(state.additions);
 const features=f.features.map((feature,i)=>({id:feature.id,pixelIndex:i+1,gridBounds:coordinateBounds(feature.geometry)[0],properties:{...feature.properties},geometry:i===0?feature.geometry:null,
  ...(i===0&&components.length?{additiveFootprint:{version:2,kind:'retained-base-plus-additions',baseline_release_sha256:f.envelope.base_reference.footprints_sha256,
   base_geometry_sha256:valueSha(feature.geometry),ledger_sha256:f.sidecar.logical_asset_map.ledger.sha256,
   authority_registry_sha256:valueSha(f.registry),components}}:{})}));
 const decoded=Buffer.from(JSON.stringify(features)),raw=gzipSync(decoded),context={path:'geography/effective-context-'+hash(raw)+'.json.gz',bytes:raw.length,sha256:hash(raw),encoding:'gzip',decoded_bytes:decoded.length,decoded_sha256:hash(decoded),offset:0,features:features.length};
 fs.mkdirSync(path.join(destination,'geography'));fs.writeFileSync(path.join(destination,context.path),raw);
 const preparedOwnership={version:2,selection_sha256:hash(fs.readFileSync(path.join(f.root,'data/ownership-selection.json'))),native_manifest_sha256:f.selection.sha256,native_pixel_map:native,
  base_reference:f.envelope.base_reference,effective_reference:reference,context_parts:[context],owners:3,reference_owner_sha256:ownerSha,
  rows_sha256:packaged.rows_sha256,runs_word_stream_sha256:packaged.runs_word_stream_sha256,
  effective_footprint_domain:'worldatlas-effective-native-footprints:v2',additive_patch_sha256:valueSha(f.patch),
  additive_ledger_sha256:f.sidecar.logical_asset_map.ledger.sha256,additive_added_cells:merged.addedCells,additive_authority_registry_sha256:valueSha(f.registry)};
 const index={version:2,compatibility_files:compatibility,native_manifest_sha256:f.selection.sha256,release_id:reference.id,footprints_sha256:reference.footprints_sha256,
  hierarchy_sha256:reference.hierarchy_sha256,pixelMap:packaged.pixelMap,preparedOwnership,additiveRelease:f.envelope,files:inventory(destination)};
 f.save(root+'/index.json',index);f.bankCommit=f.commit();return {index,features,ownership};
}
export async function writeFinal(f,prior,features,ownership,changeEvidence){
 const temporary=path.join(f.root,'bank-output');fs.mkdirSync(temporary);copyCompatibility(f,prior,temporary);
 const index=await prepareFinalBankStartupOwnership({manifest:f.manifest,manifestSha:f.selection.sha256,previous:prior,features,ownership,
  baseReference:f.envelope.base_reference,destination:temporary});index.files=inventory(temporary);
 fs.writeFileSync(path.join(temporary,'index.json'),valueBytes(index));fs.rmSync(path.join(f.root,root),{recursive:true});fs.renameSync(temporary,path.join(f.root,root));
 const raw=valueBytes(index),selection={version:2,kind:'selected-final-native-bank-v2',native_selection:f.sidecar.base_selection,
  prepared_bank:{path:root+'/index.json',bytes:raw.length,sha256:hash(raw)},reference:index.preparedOwnership.effective_reference,
  ...(changeEvidence?{change_evidence:changeEvidence}:{})};f.save('data/ownership-selection.json',selection);const commit=f.commit();
 return {index,selection,commit};
}

