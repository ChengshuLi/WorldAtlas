import test from 'node:test';
import assert from 'node:assert/strict';
import zlib, {gzipSync} from 'node:zlib';
import {syncBuiltinESMExports} from 'node:module';
import {validateEvidence, sha256, subjectsHash} from '../scripts/evidence-quality.mjs';
const commit='a'.repeat(40), ids=['gap-source-batch:'+'a'.repeat(24),'gap-source-batch:'+'b'.repeat(24)];
function fixture(lines=ids.map(id=>JSON.stringify({id,unresolved:['physical-class']})+'\n')) {
  const prefix='original split edge\n',body=Buffer.from(prefix+lines.join('')+'unterminated original edge');
  const raw=gzipSync(body),file={path:'original-part.bin.gz',commit,bytes:raw.length,sha256:sha256(raw),hash_kind:'file-bytes',uncompressed_bytes:body.length,uncompressed_sha256:sha256(body)};
  let offset=Buffer.byteLength(prefix);
  const bindings=Object.fromEntries(ids.map((id,n)=>{const row=Buffer.from(lines[n]??'');const value={version:2,kind:'gzip-jsonl-record',path:file.path,commit,record_offset:offset,record_bytes:row.length,record_sha256:sha256(row)};offset+=row.length;return [id,value]}));
  const manifest={version:1,issue:1475,lane:'geography',worker_id:'synthetic-control',subject_ids:ids,subject_ids_sha256:subjectsHash(ids),baseline:{version:2,commit,files:[file],pins:{},subject_files:bindings},sources:[],outputs:[],methods:[{id:'family-source-custody',kind:'source',description:'Original family identity only',software:'Node24',units:'bytes/native IDs'}],metrics:[],summaries:[],conclusions:[],stages:{research:'partial',implementation:'not-proposed',geographic_approval:'unapproved'},commands:['node --test test/evidence-family-record-binding.test.mjs']};
  const readFile=Object.assign(()=>raw,{assertAncestor:c=>assert.equal(c,commit)});
  return {manifest,readFile,raw,file};
}
const run=f=>validateEvidence(f.manifest,{readFile:f.readFile});
test('whole original family records retain scope and explicit identity-only limits',()=>{
  const f=fixture(),result=run(f);assert.equal(result.status,'limited');assert.equal(result.checked.length,1);assert.equal(result.limits.length,2);assert.match(result.limits[0],/identity only/);
});
test('missing, partial, foreign and drifted records cannot become original subjects',()=>{
  const changes=[m=>delete m.baseline.subject_files[ids[0]],m=>m.baseline.subject_files[ids[0]].record_offset++,m=>m.baseline.subject_files[ids[0]].record_bytes--,m=>m.baseline.subject_files[ids[0]].record_sha256='0'.repeat(64),m=>m.baseline.subject_files[ids[1]]={...m.baseline.subject_files[ids[0]]},m=>m.baseline.subject_files[ids[0]].record_offset=999999,m=>m.baseline.subject_files[ids[0]].record_bytes=33554433,m=>m.baseline.subject_files[ids[0]].extra='not allowed',m=>m.baseline.subject_files[ids[0]].commit='b'.repeat(40)];
  for(const change of changes){const f=fixture();change(f.manifest);assert.throws(()=>run(f));}
  const f=fixture();f.raw[15]^=1;assert.throws(()=>run(f),/bytes mismatch/);
});
test('duplicate original native IDs, foreign record types and missing final newlines reject',()=>{
  let f=fixture([JSON.stringify({id:ids[0]})+'\n',JSON.stringify({id:ids[0]})+'\n']);assert.throws(()=>run(f),/Duplicate original/);
  f=fixture([JSON.stringify({id:'physical-component:'+'c'.repeat(64)})+'\n',JSON.stringify({id:ids[1]})+'\n']);assert.throws(()=>run(f),/Foreign\/non-family/);
  f=fixture([JSON.stringify({id:ids[0]}),JSON.stringify({id:ids[1]})+'\n']);assert.throws(()=>run(f),/Malformed complete/);
});
test('encoded, decoded, combined and future output admission reject before any body read or gunzip',()=>{
  for(const scenario of ['combined','decoded','future-output','future-source']){
    const f=fixture();let reads=0,gunzips=0;const orig=zlib.gunzipSync;
    f.readFile=Object.assign(()=>{reads++;return f.raw},{assertAncestor:()=>{}});
    zlib.gunzipSync=(...args)=>{gunzips++;return orig(...args)};syncBuiltinESMExports();
    const options={readFile:f.readFile,maxTotalBytes:f.file.bytes+f.file.uncompressed_bytes-1};
    if(scenario==='decoded'){f.file.uncompressed_bytes=33554433;options.maxTotalBytes=268435456;}
    if(scenario==='future-output')f.manifest.outputs=[{path:'future.txt',bytes:200,sha256:'0'.repeat(64),hash_kind:'file-bytes'}];
    if(scenario==='future-source')f.manifest.sources=[{id:'future',retention:'retained',files:[{path:'future-source.txt',bytes:200,sha256:'0'.repeat(64),hash_kind:'file-bytes'}]}];
    try{assert.throws(()=>validateEvidence(f.manifest,options),/budget|phase/);assert.equal(reads,0);assert.equal(gunzips,0);}
    finally{zlib.gunzipSync=orig;syncBuiltinESMExports();}
  }
});
test('record sources retain ancestry and declared whole decoded pins',()=>{
  let f=fixture();f.readFile.assertAncestor=()=>{throw Error('Not a base ancestor')};assert.throws(()=>run(f),/base ancestor/);
  f=fixture();delete f.file.uncompressed_sha256;delete f.file.uncompressed_bytes;assert.throws(()=>run(f),/whole decoded/);
  f=fixture();f.file.uncompressed_sha256='0'.repeat(64);assert.throws(()=>run(f),/Uncompressed bytes mismatch/);
});
