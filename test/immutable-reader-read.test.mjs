import test from 'node:test';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {syncBuiltinESMExports} from 'node:module';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const {ImmutableReader} = await import(process.env.IMMUTABLE_READER_TEST_MODULE
  ? pathToFileURL(path.resolve(process.env.IMMUTABLE_READER_TEST_MODULE)).href
  : new URL('../scripts/check-effective-geographic-regression.mjs',import.meta.url).href);
const originalCreateHash=crypto.createHash;
const hash=body=>originalCreateHash('sha256').update(body).digest('hex');
const version='1'.repeat(40),name='tiny/body.json';

// Exercise the exported reader's real descriptor and complete read methods.
// Only Git's bounded metadata/body responses are synthetic; no Git history,
// production instrumentation or duplicated reader implementation is required.
function fixture() {
  class ControlledReader extends ImmutableReader {
    git(...args) {
      this.calls.push(args);
      if(args[0]==='ls-tree')return Buffer.from(`100644 blob ${this.blob}\t${name}\0`);
      if(args[0]==='cat-file'&&args[1]==='-s')return Buffer.from(String(this.declaredBytes));
      if(args[0]==='cat-file'&&args[1]==='blob')return this.body;
      throw Error('Unexpected fixture Git call: '+args.join(' '));
    }
  }
  const reader=new ControlledReader('.',version);
  reader.calls=[];reader.body=Buffer.from('{"tiny":"body"}\n');
  reader.blob='a'.repeat(40);reader.declaredBytes=reader.body.length;
  return reader;
}
function observeHashes(t) {
  const algorithms=[];
  t.mock.method(crypto,'createHash',function(algorithm,...args){
    algorithms.push(algorithm);return originalCreateHash.call(this,algorithm,...args);
  });
  syncBuiltinESMExports();
  t.after(()=>{t.mock.restoreAll();syncBuiltinESMExports();});
  return algorithms;
}
const wholeReads=reader=>reader.calls.filter(args=>args[0]==='cat-file'&&args[1]==='blob').length;
const pin=reader=>reader.inventory.get(version+':'+name);

test('matching expected hash authenticates one whole read and records one computed digest',t=>{
  const reader=fixture(),expected=hash(reader.body);
  const algorithms=observeHashes(t),actual=reader.read(name,{expected});
  assert.equal(actual,reader.body);assert.deepEqual(algorithms,['sha256']);
  assert.equal(wholeReads(reader),1);
  assert.equal(pin(reader).sha256,expected);assert.equal(pin(reader).whole_body_consumed,true);
  assert.equal(pin(reader).git_blob_oid,reader.blob);
});

test('absent expected hash still computes and records the actual whole-body digest once',t=>{
  const reader=fixture(),expected=hash(reader.body),algorithms=observeHashes(t);
  assert.equal(reader.read(name),reader.body);
  assert.deepEqual(algorithms,['sha256']);assert.equal(wholeReads(reader),1);
  assert.equal(pin(reader).sha256,expected);assert.equal(pin(reader).whole_body_consumed,true);
});

test('wrong expected hash refuses before marking the initially unconsumed inventory',t=>{
  const reader=fixture(),algorithms=observeHashes(t);
  assert.throws(()=>reader.read(name,{expected:'0'.repeat(64)}),/Whole immutable input differs: tiny\/body.json/);
  assert.deepEqual(algorithms,['sha256']);assert.equal(wholeReads(reader),1);
  assert.equal(Object.hasOwn(pin(reader),'sha256'),false);
  assert.equal(Object.hasOwn(pin(reader),'whole_body_consumed'),false);
});

for(const delta of [-1,1])test('body length '+(delta<0?'shortfall':'excess')+' refuses before hashing or inventory consumption',t=>{
  const reader=fixture(),algorithms=observeHashes(t);
  reader.body=Buffer.alloc(reader.declaredBytes+delta,120);
  assert.throws(()=>reader.read(name,{expected:'0'.repeat(64)}),/Whole immutable input differs/);
  assert.deepEqual(algorithms,[]);assert.equal(wholeReads(reader),1);
  assert.equal(Object.hasOwn(pin(reader),'sha256'),false);
  assert.equal(Object.hasOwn(pin(reader),'whole_body_consumed'),false);
});

test('each call rereads and reauthenticates; a later same-size body drift preserves prior inventory state',t=>{
  const reader=fixture(),expected=hash(reader.body),algorithms=observeHashes(t);
  reader.read(name,{expected});const before={...pin(reader)};
  reader.body=Buffer.alloc(reader.declaredBytes,120);
  assert.throws(()=>reader.read(name,{expected}),/Whole immutable input differs/);
  assert.deepEqual(algorithms,['sha256','sha256']);assert.equal(wholeReads(reader),2);
  assert.deepEqual(pin(reader),before);
});

test('descriptor drift is rejected before a second body read and leaves the original inventory intact',t=>{
  const reader=fixture(),expected=hash(reader.body),algorithms=observeHashes(t);
  reader.read(name,{expected});const before={...pin(reader)};
  reader.blob='b'.repeat(40);
  assert.throws(()=>reader.read(name,{expected}),/Immutable descriptor drift/);
  assert.deepEqual(algorithms,['sha256']);assert.equal(wholeReads(reader),1);
  assert.deepEqual(pin(reader),before);
});
