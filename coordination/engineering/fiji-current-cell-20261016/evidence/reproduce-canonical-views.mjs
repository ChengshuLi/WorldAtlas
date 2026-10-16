// Run with the already authenticated GIS Python from physical-001's receipt.
// Emits the complete explicit view table and whole-native comparison, never
// rewrites original sources or measured physical evidence.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {publish,pinReader} from '../../../../scripts/prepare-delivery-handoff.mjs';
import {verifyNativeSeamView} from '../../../../src/native-grid.js';
import {valueSha} from '../../selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const here=path.dirname(fileURLToPath(import.meta.url)),root=path.resolve(here,'../../../..');
export function authenticateLocalPinnedInput(reader,root,pin){
 const expected=reader.read(pin),name=path.join(root,pin.path);
 if(!fs.lstatSync(name).isFile()||fs.realpathSync(name)!==name)throw Error('Original local input must be an ordinary file');
 const actual=fs.readFileSync(name);
 if(!actual.equals(expected))throw Error('Original local input differs: '+pin.path);
 return actual;
}
export function captureCanonicalInputs(reader,root,evidence){
 const inputs={};
 for(const role of ['physical_input','physical_evidence']){
  const body=authenticateLocalPinnedInput(reader,root,evidence[role]);
  inputs[role]={bytes:body.length,sha256:createHash('sha256').update(body).digest('hex'),body_base64:body.toString('base64')};
 }
 return Buffer.from(JSON.stringify({version:1,inputs})+'\n');
}
export function reproduceCanonicalViews(python,destination){
 const reader=pinReader(root);
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const git=(...args)=>execFileSync('git',args,{cwd:root,maxBuffer:32*1024**2});
const commit='ab0d2088bc66e0d9847b273eb8519a92c0f109b1';
const pin=name=>{const raw=git('show',commit+':'+name),entry=git('ls-tree',commit,'--',name).toString().split(/\s+/);
 return {commit,path:name,mode:entry[0],git_blob_oid:entry[2],bytes:raw.length,sha256:sha(raw)};};
const sourcePin=reader.pin('f0f7c3082ade4b1dfa302b9b5099f0ea04b89766',
 'coordination/engineering/fiji-current-cell-20261016/source-001/source-evidence.json');
const evidence=JSON.parse(authenticateLocalPinnedInput(reader,root,sourcePin));
const capturedInputs=captureCanonicalInputs(reader,root,evidence);
const lp=evidence.native_latitudes;
const encoded=reader.read(lp);
if(encoded.length!==lp.bytes||sha(encoded)!==lp.sha256)throw Error('Original encoded latitudes differ');
const raw=gunzipSync(encoded,{maxOutputLength:lp.decoded_bytes});
if(raw.length!==lp.decoded_bytes||sha(raw)!==lp.decoded_sha256)throw Error('Original normative latitudes differ');
const latitudes=Float64Array.from({length:raw.length/8},(_,i)=>raw.readDoubleLE(i*8));
if(!python||!destination)throw Error('Use PYTHON DESTINATION');
const method=pin('scripts/majority.py');
if(sha(fs.readFileSync(path.join(root,method.path)))!==method.sha256)throw Error('Executing canonical method differs');
const receiptPin=reader.pin(evidence.physical_evidence.commit,
 'coordination/engineering/fiji-current-cell-20261016/physical-001/execution-receipt.json');
const receiptRaw=authenticateLocalPinnedInput(reader,root,receiptPin),receipt=JSON.parse(receiptRaw);
for(const file of receipt.fresh_admission.runtime_files){
 const body=fs.readFileSync(file.path);
 if(body.length!==file.bytes||sha(body)!==file.sha256)throw Error('Admitted GIS runtime changed: '+file.path);
}
const resolved=fs.realpathSync(python);
if(!receipt.fresh_admission.runtime_files.some(file=>fs.realpathSync(file.path)===resolved))
 throw Error('Python is outside the authenticated physical runtime');
const original=JSON.parse(execFileSync(python,[path.join(here,'reproduce-canonical-views.py')],{cwd:root,input:capturedInputs,maxBuffer:32*1024**2}));
const records=[],proofs=[];
for(const {original_geometry,...record} of original){
 records.push({...record,original_geometry_sha256:valueSha(original_geometry)});
 proofs.push({role:record.role,source_id:record.source_id,pointer:record.pointer,
  ...verifyNativeSeamView(original_geometry,record.geometry,{size:latitudes.length,latitudes})});
}
const result={version:1,kind:'retained-periodic-native-views-v1',method:{pin:method,export:'canonical'},records};
publish(root,destination,{
 'canonical-seam-views.json':Buffer.from(JSON.stringify(result)+'\n'),
 'canonical-native-equivalence.json':Buffer.from(JSON.stringify({version:1,method:'complete-native-span-and-boundary-tie-equality',proofs},null,2)+'\n')
},{phase:'fiji-canonical-seam-view-reproduction',method_sha256:method.sha256,
 program_sha256:sha(fs.readFileSync(fileURLToPath(import.meta.url))),
 python_program_sha256:sha(fs.readFileSync(path.join(here,'reproduce-canonical-views.py'))),
 physical_execution_receipt_sha256:sha(receiptRaw),source_evidence:sourcePin});
console.log(JSON.stringify(proofs));
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))
 reproduceCanonicalViews(process.argv[2],process.argv[3]);
