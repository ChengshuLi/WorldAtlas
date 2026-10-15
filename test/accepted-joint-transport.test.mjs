import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {checkpointTransportInput, JOINT_CODE} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-joint-entry.mjs';
import {ImmutableReader} from '../scripts/check-effective-geographic-regression.mjs';
import {ACCEPTED_CHECKPOINT_CODE} from '../scripts/accepted-selected-checkpoint.mjs';

function fixture(t) {
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'checkpoint-transport-input-'));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  const git=(...args)=>execFileSync('git',['-c','core.hooksPath=/dev/null','-C',root,...args],{stdio:['ignore','pipe','pipe']});
  git('init','-q');fs.mkdirSync(path.join(root,'data'));fs.writeFileSync(path.join(root,'data/selected-checkpoint.json'),'{"hint":true}\n');
  fs.writeFileSync(path.join(root,'archive.zip'),'whole archive sentinel');fs.symlinkSync('missing',path.join(root,'link'));
  git('add','.');git('-c','user.name=Fixture','-c','user.email=fixture@example.test','commit','-qm','fixture');
  const calls=[],reader=new ImmutableReader(root,git('rev-parse','HEAD').toString().trim()),readGit=reader.git.bind(reader);
  reader.git=(...args)=>{calls.push(args);return readGit(...args);};
  return {root,reader,calls};
}
test('joint transport closure includes every authenticated acquisition import and Python retention role',()=>{
  assert.equal(new Set(JOINT_CODE).size,JOINT_CODE.length);
  for(const name of [...ACCEPTED_CHECKPOINT_CODE,'scripts/geographic_checkpoint_products.py']) assert(JOINT_CODE.includes(name),name);
});
test('immutable locator and retained archive metadata stay outside the scientific inventory',t=>{
  const {reader}=fixture(t);
  const input=checkpointTransportInput(reader,'data/selected-checkpoint.json');
  assert.equal(input.pin.commit,reader.version);assert.equal(input.pin.whole_body_consumed,true);
  assert.equal(input.pin.sha256,createHash('sha256').update(input.body).digest('hex'));
  const held=checkpointTransportInput(reader,'archive.zip',{consume:false});
  assert.equal(held.body,null);assert.equal(held.pin.present,true);assert.equal(held.pin.whole_body_consumed,false);assert.equal(held.pin.sha256,undefined);
  assert.equal(reader.inventory.size,0);
  const absent=checkpointTransportInput(reader,'absent.zip');
  assert.equal(absent.body,null);assert.equal(absent.pin.present,false);assert.equal(reader.inventory.size,0);
});
test('transport rejects unsafe paths and nonordinary inputs before body reads',t=>{
  for(const [name,pattern] of [['link',/ordinary Git file/],['../outside',/Unsafe/]]) {
    const {reader,calls}=fixture(t);assert.throws(()=>checkpointTransportInput(reader,name),pattern);
    assert(!calls.some(args=>args[0]==='cat-file'&&args[1]==='blob'));
  }
});
