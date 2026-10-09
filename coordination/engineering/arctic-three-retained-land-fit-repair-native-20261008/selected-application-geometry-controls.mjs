// Exact production authentication helper; actual qualified application gzip.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
const root=process.cwd(),relative=process.argv[2];
const source=fs.readFileSync(new URL('./install-v9-stage.mjs',import.meta.url),'utf8');
const begin=source.indexOf('function body('),end=source.indexOf('\nfunction write(',begin);
const selectedBegin=source.indexOf('export function authenticateSelectedGeometry('),selectedEnd=source.indexOf('\nexport async function installV9Stage',selectedBegin);
assert(begin>=0&&end>begin&&selectedBegin>=0&&selectedEnd>selectedBegin);
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const authenticate=new Function('assert','fs','path','sha','gunzipSync',source.slice(begin,end)+'\n'+source.slice(selectedBegin,selectedEnd).replace('export function','function')+'\nreturn authenticateSelectedGeometry;')(assert,fs,path,sha,gunzipSync);
const raw=fs.readFileSync(relative),decoded=gunzipSync(raw);
const pin={logical_path:'data/geography/part-29.json',path:relative,mode:'100644',bytes:raw.length,sha256:sha(raw),decoded_bytes:decoded.length,decoded_sha256:sha(decoded)};
assert(authenticate(root,pin).equals(decoded));let rejected=0;
for(const mutate of [p=>p.logical_path='data/geography/part-28.json',p=>delete p.decoded_bytes,p=>p.decoded_bytes++,p=>p.decoded_sha256='0'.repeat(64),p=>p.sha256='0'.repeat(64),p=>p.bytes++,p=>p.path='../foreign.json.gz',p=>p.path='.cache/absent-qualified-body.json.gz']){
 const changed=structuredClone(pin);mutate(changed);assert.throws(()=>authenticate(root,changed));rejected++;
}
console.log(JSON.stringify({positive:1,rejected,production_source_sha256:sha(Buffer.from(source)),actual_pin:pin,limitation:'Exact production read/decode helper; no private consumer identity, installer writes or full normal build exercised.'},null,2));
