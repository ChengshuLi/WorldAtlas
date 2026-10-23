#!/usr/bin/env node
// Re-run the retained, one-row native contact queries from immutable Git inputs.
// This is a numerical recheck only: it does not decide source applicability,
// territorial status, qualification, acceptance, owner, or repair credit.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';

const here=path.dirname(fileURLToPath(import.meta.url));
const repo=path.resolve(process.argv[2]||'');
if (!process.argv[2] || !fs.existsSync(path.join(repo,'.git')))
  throw Error('Usage: node reproduce-native-centres.mjs /path/to/WorldAtlas-checkout [OUTPUT.json]');
const pins=JSON.parse(fs.readFileSync(path.join(here,'input-pins.json'),'utf8'));
const observations=JSON.parse(fs.readFileSync(path.join(here,'native-center-observations.json'),'utf8'));
const lbrResult=JSON.parse(fs.readFileSync(path.join(here,'liberia-causal-result.json'),'utf8'));
const sha256=b=>createHash('sha256').update(b).digest('hex');
const localFallbackInputs=[];
const gitBlobOid=b=>createHash('sha1').update(`blob ${b.length}\0`).update(b).digest('hex');
const gitShow=pin=>{
  const spec=`${pin.commit}:${pin.path}`;
  let bytes;
  try {
    bytes=execFileSync('git',['show',spec],{cwd:repo,encoding:'buffer',maxBuffer:64*1024*1024,
      env:{...process.env,GIT_NO_LAZY_FETCH:'1',GIT_TERMINAL_PROMPT:'0'}});
  } catch (error) {
    // Some partial worktrees have exact pinned bodies in the checkout but not
    // the corresponding tree object. Permit that body only after all hashes
    // below verify; never fetch or accept an unpinned local edit.
    const local=path.join(repo,pin.path);
    if (!fs.existsSync(local)) throw error;
    bytes=fs.readFileSync(local);
    localFallbackInputs.push(spec);
  }
  if (pin.bytes!==undefined && bytes.length!==pin.bytes) throw Error(`${spec}: byte-size mismatch ${bytes.length} != ${pin.bytes}`);
  if (pin.git_blob_oid && gitBlobOid(bytes)!==pin.git_blob_oid) throw Error(`${spec}: Git blob OID mismatch`);
  if (pin.sha256 && sha256(bytes)!==pin.sha256) throw Error(`${spec}: SHA-256 mismatch`);
  return bytes;
};
const scannerPin=pins.exact_scanner;
const scannerBytes=fs.readFileSync(path.join(here,'native-grid-pinned.mjs'));
if (scannerBytes.length!==scannerPin.bytes || sha256(scannerBytes)!==scannerPin.sha256 || gitBlobOid(scannerBytes)!==scannerPin.git_blob_oid)
  throw Error('Bundled scanner copy differs from its immutable repository pin');
const {witnessCellEffects,nativePolygonIntervals}=await import(pathToFileURL(path.join(here,'native-grid-pinned.mjs')));
const latPin=pins.liberia.native_latitudes;
const latEncoded=gitShow(latPin), latRaw=gunzipSync(latEncoded);
if ((latPin.decoded_bytes!==undefined && latRaw.length!==latPin.decoded_bytes) || sha256(latRaw)!==latPin.decoded_sha256) throw Error('Decoded native latitude table mismatch');
if (latRaw.length!==pins.egypt.native_latitudes.decoded_bytes || sha256(latRaw)!==pins.egypt.native_latitudes.decoded_sha256) throw Error('Egypt latitude pin differs');
const size=latRaw.length/8;
if (!Number.isInteger(size) || size!==latPin.grid_size) throw Error('Native latitude-table length mismatch');
const dv=new DataView(latRaw.buffer,latRaw.byteOffset,latRaw.byteLength), latitudes=new Float64Array(size);
for(let i=0;i<size;i++) latitudes[i]=dv.getFloat64(i*8,true);

const lbrSource=JSON.parse(gitShow(pins.liberia.source_evidence));
const egySource=JSON.parse(gitShow(pins.egypt.source_evidence));
const physical=JSON.parse(gitShow(pins.liberia.physical_whole_target_support));
const familyBodies=new Map();
for(const [family,descriptor] of Object.entries(pins.liberia.original_negative_families.reduce((a,x)=>(a[x.source_id]=x.part,a),{}))) {
  const buf=gunzipSync(gitShow(descriptor));
  if(buf.length!==descriptor.decoded_bytes || sha256(buf)!==descriptor.decoded_sha256) throw Error(`${family}: decoded payload mismatch`);
  familyBodies.set(family,JSON.parse(buf.toString('utf8')));
}
for(const [family,descriptor] of Object.entries(pins.egypt.whole_original_family_payloads)) {
  if(familyBodies.has(family)) continue;
  const part=descriptor.parts[0], buf=gunzipSync(gitShow(part));
  if(buf.length!==part.decoded_bytes || sha256(buf)!==part.decoded_sha256) throw Error(`${family}: decoded payload mismatch`);
  familyBodies.set(family,JSON.parse(buf.toString('utf8')));
}
const familyFor=id=>{
  let m=id.match(/^gb:([A-Z]{3}):ADM([1-4]):(.+)$/);
  if(m) return `gb:${m[1]}:ADM${m[2]}`;
  m=id.match(/^gb:([A-Z]{3}):([1-4]):(.+)$/);
  if(m) return `gb:${m[1]}:ADM${m[2]}`;
  throw Error(`Cannot map source ID to pinned source family: ${id}`);
};
const suffixFor=id=>id.slice(id.lastIndexOf(':')+1);
function featureGeometry(sourceId,ordinal) {
  const body=familyBodies.get(familyFor(sourceId));
  const f=body?.features?.[ordinal];
  if(!f?.geometry) throw Error(`Missing pinned feature ${sourceId} ordinal ${ordinal}`);
  const shape=f.properties?.shapeID;
  if(shape && shape!==suffixFor(sourceId)) throw Error(`Feature identity mismatch ${sourceId} ordinal ${ordinal}: ${shape}`);
  return f.geometry;
}
function targetGeometry(evidence,sourceId) {
  const t=evidence.targets.find(x=>x.id===sourceId || x.target_id===sourceId);
  if(!t?.base_geometry) throw Error(`Missing exact target geometry ${sourceId}`);
  return t.base_geometry;
}
function physicalSupport(sourceId) {
  const r=physical.results.find(x=>x.target===sourceId);
  if(!r?.support?.mapped_land_support) throw Error(`Missing physical mapped-land support ${sourceId}`);
  return r.support.mapped_land_support;
}
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const reports=[];
function run(label,geometry,cell,expected,authority) {
  const end=cell.end??cell.x+1;
  const actual=witnessCellEffects(geometry,{size,latitudes,requestedRows:[{y:cell.y,runs:[[cell.x,end,cell.owner]]}],nativePolygonIntervals});
  if(!same(actual.hits,expected.hits)) throw Error(`${label}: recheck differs from retained expected hits: ${JSON.stringify({actual:actual.hits,expected:expected.hits})}`);
  reports.push({label,authority,query:{y:cell.y,x_start:cell.x,x_end_exclusive:end,owner:cell.owner},hits:actual.hits,counts:actual.counts,work:actual.work,exact_hit_list_matches_retained:true});
}
const lbrCell=lbrResult.key;
run('LBR selected Buu-Yao base footprint (target.base_geometry)',targetGeometry(lbrSource,lbrResult.positive_target.source_id),lbrCell,lbrResult.positive_target.effects,
  `source-evidence ${pins.liberia.source_evidence.commit}:${pins.liberia.source_evidence.path}`);
const lbrObs=observations.liberia;
run('LBR original physical mapped-land support',physicalSupport(lbrResult.positive_target.source_id),{...lbrCell,end:lbrCell.x+2},lbrObs.physical_report_mapped_land_support.effect,
  `whole-target-support ${pins.liberia.physical_whole_target_support.commit}:${pins.liberia.physical_whole_target_support.path}`);
for(let i=0;i<lbrResult.negative_results.length;i++) {
  const n=lbrResult.negative_results[i], geometry=featureGeometry(n.source_id,n.feature_ordinal);
  run(`LBR retained CIV negative ${i+1}`,geometry,lbrCell,n.effects,
    `source payload ordinal ${n.feature_ordinal}; ${familyFor(n.source_id)}`);
}
for(let i=0;i<observations.egypt.length;i++) {
  const q=observations.egypt[i], sourceId=q.feature.source_id_canonical||q.feature.source_id;
  const geometry=featureGeometry(sourceId,q.feature.ordinal_zero_based);
  run(`EGY ${q.cell.label}: ${q.operand}`,geometry,q.cell,q.effect,
    `whole-family feature ${sourceId}, ordinal ${q.feature.ordinal_zero_based}`);
}
const result={
  kind:'reproduced-held-cell-native-center-queries',
  status:'all_retained_hit_lists_reproduced; observations_only',
  scanner:{commit:scannerPin.commit,path:scannerPin.path,git_blob_oid:scannerPin.git_blob_oid,bytes:scannerPin.bytes,sha256:scannerPin.sha256},
  historical_liberia_result_scanner_sha256:lbrResult.native_rule.scanner_module_sha256,
  historical_hash_matches_recheck_scanner:lbrResult.native_rule.scanner_module_sha256===scannerPin.sha256,
  latitude_table:{commit:latPin.commit,path:latPin.path,encoded_sha256:latPin.encoded_sha256,decoded_sha256:latPin.decoded_sha256,grid_size:size},
  input_resolution:{git_show_with_verified_worktree_fallbacks:localFallbackInputs},
  query_count:reports.length,
  matching_queries:reports.length,
  queries:reports,
  limits:['This rerun validates only exact numeric cell contacts against the pinned geometries.','It does not resolve original source applicability, sovereignty, land truth, qualification, acceptance, selected state, or repair credit.','The historical Liberia causal result uses a different scanner module SHA than this later repository-pinned recheck; neither is rewritten or called byte-equivalent.']
};
const output=JSON.stringify(result,null,2)+'\n';
if(process.argv[3]) fs.writeFileSync(path.resolve(process.argv[3]),output,{flag:'wx'}); else process.stdout.write(output);
