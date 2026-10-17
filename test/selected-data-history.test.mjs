import test from 'node:test';
import assert from 'node:assert/strict';
import {gzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {createHistoryReader,openSelectedHistory} from './fixtures/selected-data-history.mjs';
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
function specimen() {
  const raw=Buffer.from('{"kind":"contract"}'),sha=createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
  return {version:1,source_commit:'a'.repeat(40),entries:[{path:'data/contract.json',type:'blob',mode:'100644',sha,size:raw.length}],
    bodies:[{sha,base64:raw.toString('base64')}]};
}
const encoded=value=>{const bytes=gzipSync(JSON.stringify(value));return {bytes,pin:{version:1,bytes:bytes.length,sha256:hash(bytes),source_commit:value.source_commit,descriptors:value.entries.length,bodies:value.bodies.length}};};
test('explicit isolated contract reader authenticates bodies and returns owned copies',()=>{
  const value=specimen(),reader=openSelectedHistory(encoded(value));
  assert.deepEqual(reader.entry('data/contract.json'),value.entries[0]);
  assert.equal(reader.readFile('data/contract.json').toString(),'{"kind":"contract"}');
  reader.entry('data/contract.json').sha='f'.repeat(40);reader.readFile('data/contract.json').fill(0);
  assert.equal(reader.readFile('data/contract.json').toString(),'{"kind":"contract"}');
});
test('metadata-only descriptors never imply body availability or fall back to local files',()=>{
  const value=specimen();value.bodies=[];const reader=createHistoryReader(value);
  assert(reader.entry('data/contract.json'));assert.equal(reader.hasBody(value.entries[0].sha),false);
  assert.throws(()=>reader.readFile('data/contract.json'),/Body absent from isolated contract/);
  assert.throws(()=>reader.readFile('package.json'),/Path absent from isolated contract/);
  for(const name of ['../package.json','/etc/passwd','data/../package.json','data//contract.json'])assert.throws(()=>reader.entry(name),/Safe captured path/);
});
test('contract refuses corrupt transport, body identities, descriptor modes, sizes and duplicates',()=>{
  const packet=encoded(specimen()),bad=Buffer.from(packet.bytes);bad[bad.length-1]^=1;
  assert.throws(()=>openSelectedHistory({...packet,bytes:bad}),/fixture hash differs/);
  assert.throws(()=>openSelectedHistory({...packet,bytes:bad.subarray(1)}),/fixture size differs/);
  const omitted=specimen();omitted.bodies=[];const repacked=encoded(omitted);
  assert.throws(()=>openSelectedHistory({...repacked,pin:{...repacked.pin,bodies:packet.pin.bodies}}),/Captured body inventory differs/);
  for(const mutate of [v=>v.entries[0].mode='120000',v=>v.entries[0].size++,v=>v.entries.push(v.entries[0]),
    v=>v.bodies[0].sha='f'.repeat(40),v=>v.bodies[0].base64=Buffer.from('wrong').toString('base64'),v=>v.bodies.push(v.bodies[0])]) {
    const value=specimen();mutate(value);assert.throws(()=>createHistoryReader(value));
  }
});
test('captured real contract bodies are all authenticated before consumers open them',()=>{
  const reader=openSelectedHistory();assert(reader.bodyOids().length>0);
  for(const sha of reader.bodyOids())assert(reader.readBlob(sha).length>0);
});
