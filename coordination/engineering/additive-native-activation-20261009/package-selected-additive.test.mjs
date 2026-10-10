import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {preparePackageSelectedAdditive,publishPackageSelectedAdditive,prepareOrdinaryPublicationDirectory,readBoundPublicationAssets} from './package-selected-additive.mjs';

test('ordinary nonadditive selection preserves the default route without execution or payload reads',async()=>{
  const root=fs.mkdtempSync(path.join(fs.realpathSync(os.tmpdir()),'additive-package-default-'));
  try{
    assert.equal(await preparePackageSelectedAdditive({root}),null);
    fs.mkdirSync(path.join(root,'data'));fs.writeFileSync(path.join(root,'data/ownership-selection.json'),JSON.stringify({version:1,manifest_path:'original',sha256:'original'}));
    assert.equal(await preparePackageSelectedAdditive({root}),null);
    assert.equal(publishPackageSelectedAdditive(null,{root}),null);
    assert.equal(fs.existsSync(path.join(root,'dist')),false);
  }finally{fs.rmSync(root,{recursive:true,force:true});}
});
test('the actual writer directory boundary refuses a symlink before any foreign directory creation',()=>{
  const root=fs.mkdtempSync(path.join(fs.realpathSync(os.tmpdir()),'additive-package-writer-'));
  const foreign=fs.mkdtempSync(path.join(fs.realpathSync(os.tmpdir()),'additive-package-foreign-'));
  try{
    fs.symlinkSync(foreign,path.join(root,'dist'));
    assert.throws(()=>prepareOrdinaryPublicationDirectory(root,'dist/additive-repairs'),/Ordinary publication/);
    assert.deepEqual(fs.readdirSync(foreign),[]);
    fs.unlinkSync(path.join(root,'dist'));fs.mkdirSync(path.join(root,'dist'));
    fs.symlinkSync(foreign,path.join(root,'dist/additive-repairs'));
    assert.throws(()=>prepareOrdinaryPublicationDirectory(root,'dist/additive-repairs'),/Ordinary publication/);
    assert.deepEqual(fs.readdirSync(foreign),[]);
  }finally{fs.rmSync(root,{recursive:true,force:true});fs.rmSync(foreign,{recursive:true,force:true});}
});
test('the real publication entry rejects copied and invented authority before creating output',()=>{
  const root=fs.mkdtempSync(path.join(fs.realpathSync(os.tmpdir()),'additive-package-forged-'));
  try{
    for(const token of [{},{additiveRelease:{}},{reference_release:{},additiveRelease:{version:2}}])
      assert.throws(()=>publishPackageSelectedAdditive(token,{root}),/Privately authenticated/);
    assert.equal(fs.existsSync(path.join(root,'dist')),false);
  }finally{fs.rmSync(root,{recursive:true,force:true});}
});
test('whole selection metadata rejects oversize and symlink boundaries',async()=>{
  const root=fs.mkdtempSync(path.join(fs.realpathSync(os.tmpdir()),'additive-package-selection-'));
  try{
    fs.mkdirSync(path.join(root,'data'));const name=path.join(root,'data/ownership-selection.json');
    fs.writeFileSync(name,' '.repeat(131073));await assert.rejects(preparePackageSelectedAdditive({root}),/Bounded selection/);
    fs.unlinkSync(name);fs.writeFileSync(path.join(root,'source.json'),'{}');fs.symlinkSync(path.join(root,'source.json'),name);
    await assert.rejects(preparePackageSelectedAdditive({root}),/Ordinary ancestors/);
  }finally{fs.rmSync(root,{recursive:true,force:true});}
});

// Tiny actual Git copy-frame control; it does not create publication authority.
test('fresh publication frame authenticates frozen accepted descriptors and refuses whole-pin drift',async()=>{
  const {execFileSync}=await import('node:child_process');
  const {ImmutableReader}=await import('../../../scripts/check-effective-geographic-regression.mjs');
  const root=fs.mkdtempSync(path.join(fs.realpathSync(os.tmpdir()),'additive-frozen-copy-'));
  const git=process.platform==='darwin'?'/Library/Developer/CommandLineTools/usr/bin/git':'/usr/bin/git';
  const run=args=>execFileSync(git,['-C',root,...args],{stdio:'pipe'});
  try{
    run(['init']);for(let i=0;i<4;i++)fs.writeFileSync(path.join(root,`asset-${i}.json`),JSON.stringify({i})+'\n');
    run(['add','.']);run(['-c','user.name=fixture','-c','user.email=fixture@example.invalid','commit','-m','bounded fixture']);
    const head=run(['rev-parse','HEAD']).toString().trim(),reader=new ImmutableReader(root,head,{gitExecutable:git}),roster=[];
    for(let i=0;i<4;i++){const name=`asset-${i}.json`;reader.read(name);const pin=reader.descriptor(name);Object.freeze(pin);roster.push({pin});}
    const saved=JSON.stringify([...reader.inventory.values()]),copy=readBoundPublicationAssets(reader,roster,()=>true);
    assert.equal(copy.bodies.length,4);copy.bodies.forEach((b,i)=>assert.equal(b.toString(),JSON.stringify({i})+'\n'));
    assert.equal(JSON.stringify([...reader.inventory.values()]),saved);
    assert(copy.complete_phase_bytes>=reader.metadataBytes+2*Buffer.byteLength(saved));
    assert.throws(()=>readBoundPublicationAssets(reader,roster.slice(0,3),()=>true),/Four distinct/);
    assert.throws(()=>readBoundPublicationAssets(reader,roster,()=>false),/Undeclared/);
    const changed=structuredClone(roster);changed[0].pin.sha256='0'.repeat(64);
    assert.throws(()=>readBoundPublicationAssets(reader,changed,()=>true),/Whole immutable input differs/);
  }finally{fs.rmSync(root,{recursive:true,force:true});}
});
