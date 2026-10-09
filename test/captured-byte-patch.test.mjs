import test from 'node:test';
import assert from 'node:assert/strict';
import {gzipSync} from 'node:zlib';
import {byteSha,applyBytePatch} from '../coordination/engineering/eastern-two-gap-repair-native-20261007/byte-patch.mjs';
import {applyEncodedBytePatch} from '../scripts/evidence/captured-byte-patch.mjs';
function fixture() {
 const body=Buffer.from('the original complete source');let encoded=gzipSync(body),reads=0,lookups=0;
 const declaration={path:'original/source.gz',object:'source',mode:'100644',encoded_bytes:encoded.length,encoded_sha256:byteSha(encoded),decoded_bytes:body.length,decoded_sha256:byteSha(body)};
 const commands=[{copy:['source',0,4]},{copy:['source',4,body.length-4]}];
 const target={path:'original/output',bytes:body.length,sha256:byteSha(body),mode:'100644'};
 return {body,declaration,commands,target,get reads(){return reads;},get lookups(){return lookups;},replace(b){encoded=gzipSync(b);},
  resolve(name){assert.equal(name,'source');lookups++;return {declaration,read(){reads++;return encoded;}};}};
}
test('one patch authenticates one captured source and every output byte',()=>{
 const f=fixture();assert.deepEqual(applyEncodedBytePatch(f.commands,f.target,f.resolve),f.body);assert.equal(f.reads,1);assert.equal(f.lookups,2);
});
test('captured decoding does not observe a later external encoded-body replacement',()=>{
 const f=fixture();let n=0;
 const resolve=name=>{if(++n===2)f.replace(Buffer.from('a changed complete source!'));return f.resolve(name);};
 assert.deepEqual(applyEncodedBytePatch(f.commands,f.target,resolve),f.body);assert.equal(f.reads,1);
 assert.throws(()=>applyEncodedBytePatch(f.commands,f.target,f.resolve));
});
test('a changed declaration during reuse is rejected',()=>{
 const f=fixture();let n=0;const resolve=name=>{if(++n===2)f.declaration.decoded_sha256='0'.repeat(64);return f.resolve(name);};
 assert.throws(()=>applyEncodedBytePatch(f.commands,f.target,resolve),/Captured source declaration changed/);
});
test('a changed identity during reuse is rejected',()=>{
 const f=fixture();let n=0;const resolve=name=>{if(++n===2)f.declaration.path='different/source.gz';return f.resolve(name);};
 assert.throws(()=>applyEncodedBytePatch(f.commands,f.target,resolve),/Captured source declaration changed/);
});
test('wrong encoded bytes fail before producing an output',()=>{
 const f=fixture();f.replace(Buffer.from('wrong original source'));
 assert.throws(()=>applyEncodedBytePatch(f.commands,f.target,f.resolve));assert.equal(f.reads,1);
});
test('a correct encoded pin cannot hide incorrect decoded custody',()=>{
 const f=fixture();f.declaration.decoded_sha256='0'.repeat(64);
 assert.throws(()=>applyEncodedBytePatch(f.commands,f.target,f.resolve),/Consumed decoded source differs/);
});
test('an oversized declaration fails before the loader opens a source',()=>{
 const f=fixture();f.declaration.decoded_bytes=32*1024*1024+1;
 assert.throws(()=>applyEncodedBytePatch(f.commands,f.target,f.resolve));assert.equal(f.reads,0);
});
test('copy-range and complete-target checks remain active',()=>{
 const f=fixture();assert.throws(()=>applyEncodedBytePatch([{copy:['source',f.body.length,1]}],{...f.target,bytes:1},f.resolve),/Escaped source copy range/);
 assert.throws(()=>applyEncodedBytePatch(f.commands,{...f.target,sha256:'0'.repeat(64)},f.resolve));
});
test('fresh invocations do not reuse old source buffers or successful verdicts',()=>{
 const f=fixture();const output=applyEncodedBytePatch(f.commands,f.target,f.resolve);output.fill(0);
 assert.deepEqual(applyEncodedBytePatch(f.commands,f.target,f.resolve),f.body);assert.equal(f.reads,2);
 f.replace(Buffer.from('new external source'));
 assert.throws(()=>applyEncodedBytePatch(f.commands,f.target,f.resolve));assert.equal(f.reads,3);
});

test('complete unique input budget rejects before any source opens',()=>{
 let opens=0;
 const commands=['a','b','c','d'].map(name=>({copy:[name,0,1]}));
 const resolve=name=>({declaration:{path:name+'.gz',object:name,mode:'100644',encoded_bytes:32*1024*1024,decoded_bytes:32*1024*1024,encoded_sha256:'0'.repeat(64),decoded_sha256:'0'.repeat(64)},read(){opens++;assert.fail('source must not open');}});
 assert.throws(()=>applyEncodedBytePatch(commands,{bytes:4,sha256:'0'.repeat(64),mode:'100644'},resolve),/Complete captured input\/output phase exceeds cap/);
 assert.equal(opens,0);
});
test('a malformed late command rejects before opening an earlier valid source',()=>{
 const f=fixture();assert.throws(()=>applyEncodedBytePatch([{copy:['source',0,4]},{literal:'!!!='}],f.target,f.resolve));assert.equal(f.reads,0);
});
test('command mutation by the source loader is rejected before output publication',()=>{
 const f=fixture();const resolve=name=>{const resolved=f.resolve(name);return {...resolved,read(){f.target.sha256='0'.repeat(64);f.commands[1].copy[1]=0;return resolved.read();}};};
 assert.throws(()=>applyEncodedBytePatch(f.commands,f.target,resolve),/Validated command layout changed/);
});
test('mixed copy/literal reconstruction agrees with the immutable original helper',()=>{
 const f=fixture(),literal=Buffer.from(' plus a literal'),commands=[{copy:['source',3,7]},{literal:literal.toString('base64')},{copy:['source',1,3]}];
 const expected=Buffer.concat([f.body.subarray(3,10),literal,f.body.subarray(1,4)]),target={bytes:expected.length,sha256:byteSha(expected),mode:'100644'};
 assert.deepEqual(applyEncodedBytePatch(commands,target,f.resolve),applyBytePatch(commands,target,()=>f.body));
 assert.throws(()=>applyEncodedBytePatch([{literal:'AB=='}],{bytes:1,sha256:byteSha(Buffer.from([0])),mode:'100644'},()=>assert.fail('no source lookup')),/Noncanonical literal/);
});

test('command accessors and custom serialization fail without executing user code',()=>{
 let invoked=0;
 const getter={get literal(){invoked++;return 'YQ==';}};
 const serialized={literal:'YQ=='};Object.defineProperty(serialized,'toJSON',{value(){invoked++;return {literal:'YQ=='};}});
 const target={bytes:1,sha256:byteSha(Buffer.from('a')),mode:'100644'};
 for(const command of [getter,serialized])assert.throws(()=>applyEncodedBytePatch([command],target,()=>{throw new Error('No source expected');}));
 assert.equal(invoked,0);
});

test('loader-installed accessors and command-array getters cannot execute during reconstruction',()=>{
 const f=fixture();let invoked=0;
 const resolve=name=>{const r=f.resolve(name);return {...r,read(){const wire=r.read();Object.defineProperty(f.commands[0],'copy',{get(){invoked++;return ['source',0,4];},enumerable:true});return wire;}};};
 assert.throws(()=>applyEncodedBytePatch(f.commands,f.target,resolve));assert.equal(invoked,0);
 const commands=[];Object.defineProperty(commands,'0',{get(){invoked++;return {literal:'YQ=='};},enumerable:true});
 assert.throws(()=>applyEncodedBytePatch(commands,{bytes:1,sha256:byteSha(Buffer.from('a')),mode:'100644'},()=>{}));assert.equal(invoked,0);
});
