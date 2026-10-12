import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {checkpointTransportInput, JOINT_CODE} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-joint-entry.mjs';
import {ACCEPTED_CHECKPOINT_CODE} from '../scripts/accepted-selected-checkpoint.mjs';

function fixture(t) {
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'checkpoint-transport-input-'));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  const git=(...args)=>execFileSync('git',['-c','core.hooksPath=/dev/null','-C',root,...args],{stdio:['ignore','pipe','pipe']});
  git('init','-q');fs.mkdirSync(path.join(root,'data'));fs.writeFileSync(path.join(root,'data/selected-checkpoint.json'),'{"hint":true}\n');
  fs.writeFileSync(path.join(root,'archive.zip'),'whole archive sentinel');fs.symlinkSync('missing',path.join(root,'link'));
  git('add','.');git('-c','user.name=Fixture','-c','user.email=fixture@example.test','commit','-qm','fixture');
  const calls=[],reader={version:git('rev-parse','HEAD').toString().trim(),inventory:new Map(),checkMemory(){},git(...args){calls.push(args);return git(...args);}};
  return {root,reader,calls};
}
test('joint transport closure includes every authenticated acquisition import and Python retention role',()=>{
  assert.equal(new Set(JOINT_CODE).size,JOINT_CODE.length);
  for(const name of [...ACCEPTED_CHECKPOINT_CODE,'scripts/geographic_checkpoint_products.py']) assert(JOINT_CODE.includes(name),name);
});
test('immutable locator and retained archive metadata stay outside the scientific inventory',t=>{
  const {reader}=fixture(t),admitted=[];
  const input=checkpointTransportInput(reader,'data/selected-checkpoint.json',4096,n=>admitted.push(n));
  assert.equal(input.pin.commit,reader.version);assert.equal(input.pin.whole_body_consumed,true);
  assert.equal(input.pin.sha256,createHash('sha256').update(input.body).digest('hex'));assert.equal(admitted[0],input.body.length);
  const held=checkpointTransportInput(reader,'archive.zip',1024,()=>assert.fail('unconsumed archive cannot allocate'),{consume:false});
  assert.equal(held.body,null);assert.equal(held.pin.present,true);assert.equal(held.pin.whole_body_consumed,false);assert.equal(held.pin.sha256,undefined);
  assert.equal(reader.inventory.size,0);
  const absent=checkpointTransportInput(reader,'absent.zip',1024,()=>assert.fail('absent input cannot allocate'));
  assert.equal(absent.body,null);assert.equal(absent.pin.present,false);assert.equal(reader.inventory.size,0);
});
test('transport admission rejects unsafe types and size before body reads, and denied allocation remains closed',t=>{
  for(const [name,maximum,pattern] of [['link',1024,/ordinary Git file/],['archive.zip',1,/ordinary cap/],['../outside',4096,/Unsafe/]]) {
    const {reader,calls}=fixture(t);assert.throws(()=>checkpointTransportInput(reader,name,maximum,()=>{}),pattern);
    assert(!calls.some(args=>args[0]==='cat-file'&&args[1]==='blob'));
  }
  const {reader,calls}=fixture(t);
  assert.throws(()=>checkpointTransportInput(reader,'archive.zip',1024,()=>{throw Error('current carried budget');}),/current carried budget/);
  assert(!calls.some(args=>args[0]==='cat-file'&&args[1]==='blob'));assert.equal(reader.inventory.size,0);
});
