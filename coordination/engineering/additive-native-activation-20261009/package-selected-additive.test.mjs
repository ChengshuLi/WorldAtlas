import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {preparePackageSelectedAdditive,publishPackageSelectedAdditive,prepareOrdinaryPublicationDirectory} from './package-selected-additive.mjs';

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
