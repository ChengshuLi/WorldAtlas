// Run with the already authenticated GIS Python from physical-001's receipt.
// Emits the complete explicit view table and whole-native comparison, never
// rewrites original sources or measured physical evidence.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {verifyNativeSeamView} from '../../../../src/native-grid.js';
import {valueSha} from '../../selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const here=path.dirname(fileURLToPath(import.meta.url)),root=path.resolve(here,'../../../..');
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const git=(...args)=>execFileSync('git',args,{cwd:root,maxBuffer:32*1024**2});
const commit='ab0d2088bc66e0d9847b273eb8519a92c0f109b1';
const pin=name=>{const raw=git('show',commit+':'+name),entry=git('ls-tree',commit,'--',name).toString().split(/\s+/);
 return {commit,path:name,mode:entry[0],git_blob_oid:entry[2],bytes:raw.length,sha256:sha(raw)};};
const evidence=JSON.parse(fs.readFileSync(path.join(here,'../source-001/source-evidence.json')));
const lp=evidence.native_latitudes;
const raw=gunzipSync(git('show',lp.commit+':'+lp.path));
if(raw.length!==lp.decoded_bytes||sha(raw)!==lp.decoded_sha256)throw Error('Original normative latitudes differ');
const latitudes=Float64Array.from({length:raw.length/8},(_,i)=>raw.readDoubleLE(i*8));
const python=process.argv[2],destination=process.argv[3];
if(!python||!destination)throw Error('Use PYTHON DESTINATION');
const original=JSON.parse(execFileSync(python,[path.join(here,'reproduce-canonical-views.py')],{cwd:root,maxBuffer:32*1024**2}));
const records=[],proofs=[];
for(const {original_geometry,...record} of original){
 records.push({...record,original_geometry_sha256:valueSha(original_geometry)});
 proofs.push({role:record.role,source_id:record.source_id,pointer:record.pointer,
  ...verifyNativeSeamView(original_geometry,record.geometry,{size:latitudes.length,latitudes})});
}
const result={version:1,kind:'retained-periodic-native-views-v1',method:{pin:pin('scripts/majority.py'),export:'canonical'},records};
fs.mkdirSync(destination,{recursive:true});
fs.writeFileSync(path.join(destination,'canonical-seam-views.json'),JSON.stringify(result)+'\n');
fs.writeFileSync(path.join(destination,'canonical-native-equivalence.json'),JSON.stringify({version:1,method:'complete-native-span-and-boundary-tie-equality',proofs},null,2)+'\n');
console.log(JSON.stringify(proofs));
