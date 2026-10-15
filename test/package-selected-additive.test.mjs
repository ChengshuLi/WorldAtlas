import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {ImmutableReader} from '../scripts/check-effective-geographic-regression.mjs';
import {readBoundPublicationAssets,retainSelectedPackageInputs,publishPackageSelectedAdditive,
  prepareOrdinaryPublicationDirectory,requirePackageAssemblyExecution}
  from '../coordination/engineering/additive-native-activation-20261009/package-selected-additive.mjs';

const sha=raw=>createHash('sha256').update(raw).digest('hex');
function fixture(t){
  const root=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'atlas-additive-publication-')));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  const git=(...args)=>execFileSync('git',['-C',root,...args],{encoding:'utf8'}).trim();
  git('init','-q');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid');
  const bodies=Array.from({length:4},(_,i)=>Buffer.from(JSON.stringify({complete_member:i})));
  for(let i=0;i<bodies.length;i++)fs.writeFileSync(path.join(root,'asset-'+i+'.json'),bodies[i]);
  git('add','.');git('commit','-qm','Immutable original publication bodies');const version=git('rev-parse','HEAD');
  const reader=new ImmutableReader(root,version);
  const roster=bodies.map((body,i)=>{const name='asset-'+i+'.json';reader.read(name,{expected:sha(body)});return {pin:reader.descriptor(name)};});
  for(const {pin}of roster)Object.freeze(pin);
  return {root,reader,roster,bodies};
}

test('publication copying reauthenticates four frozen whole pins and retains actual complete custody',t=>{
  const f=fixture(t),before=structuredClone([...f.reader.inventory.values()]);
  const copied=readBoundPublicationAssets(f.reader,f.roster,()=>true);
  assert.deepEqual(copied.bodies,f.bodies);assert.deepEqual([...f.reader.inventory.values()],before);
  assert.equal(copied.input_inventory.length,8);
  for(const pin of copied.input_inventory){
    assert.equal(pin.whole_body_consumed,true);assert.equal(pin.sha256,sha(f.bodies[Number(pin.path.match(/\d+/)[0])]));
    assert.equal(pin.mode,'100644');assert.equal(pin.commit,f.reader.version);
  }
});

test('publication copying rejects incomplete, duplicate, undeclared and rebound immutable pins',t=>{
  const f=fixture(t);
  assert.throws(()=>readBoundPublicationAssets(f.reader,f.roster.slice(1),()=>true),/Four distinct/);
  assert.throws(()=>readBoundPublicationAssets(f.reader,[f.roster[0],f.roster[0],...f.roster.slice(2)],()=>true),/Four distinct/);
  assert.throws(()=>readBoundPublicationAssets(f.reader,f.roster,()=>false),/Undeclared/);
  for(const edit of [pin=>pin.bytes++,pin=>pin.mode='100755',pin=>pin.git_blob_oid='0'.repeat(40),pin=>pin.sha256='0'.repeat(64)]){
    const roster=structuredClone(f.roster);edit(roster[0].pin);
    assert.throws(()=>readBoundPublicationAssets(f.reader,roster,()=>true),/custody differs|Whole immutable input differs/);
  }
});

test('selected input observation retains only exact actually consumed accepted identities',t=>{
  const f=fixture(t),expected=f.roster.map(({pin})=>({path:pin.path,mode:pin.mode,oid:pin.git_blob_oid,bytes:pin.bytes})),retained=new Map();
  const pins=f.roster.map(({pin})=>({...pin}));
  retainSelectedPackageInputs(expected,pins,retained);assert.equal(retained.size,4);
  assert.notEqual(retained.get(pins[0].path),pins[0]);
  for(const edit of [pin=>pin.bytes++,pin=>pin.mode='100755',pin=>pin.git_blob_oid='0'.repeat(40),pin=>delete pin.whole_body_consumed,pin=>delete pin.sha256]){
    const bad={...pins[0]},result=new Map();edit(bad);retainSelectedPackageInputs(expected,[bad],result);assert.equal(result.size,0);
  }
  retainSelectedPackageInputs(expected,pins,retained);assert.equal(retained.size,4);
});

test('publication requires private capabilities and ordinary output ancestors without changing sentinels',t=>{
  const f=fixture(t);
  assert.throws(()=>publishPackageSelectedAdditive({}, {root:f.root}),/Privately authenticated/);
  assert.throws(()=>requirePackageAssemblyExecution({kind:'current-selected-package-assembly'}),/Private current/);
  assert.equal(fs.existsSync(path.join(f.root,'dist')),false);
  const outside=path.join(f.root,'outside');fs.mkdirSync(outside);fs.writeFileSync(path.join(outside,'sentinel'),'preserve');
  fs.symlinkSync(outside,path.join(f.root,'dist'));
  assert.throws(()=>prepareOrdinaryPublicationDirectory(f.root,'dist/additive-repairs'),/Ordinary publication/);
  assert.equal(fs.readFileSync(path.join(outside,'sentinel'),'utf8'),'preserve');assert.deepEqual(fs.readdirSync(outside),['sentinel']);
  fs.unlinkSync(path.join(f.root,'dist'));
  const destination=prepareOrdinaryPublicationDirectory(f.root,'dist/additive-repairs');
  assert.equal(fs.realpathSync(destination),destination);assert.ok(fs.lstatSync(destination).isDirectory());
});
