import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {openLeaseCheckpoint} from '../scripts/issue-lease-checkpoint.mjs';
const fixture=run=>{const dir=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-lease-writer-'));try{return run(path.join(dir,'receipt.json'));}finally{fs.rmSync(dir,{recursive:true,force:true});}};
test('durable writer publishes complete checkpoints and serializes only its owned receipt',()=>fixture(file=>{
 const writer=openLeaseCheckpoint(file);try{writer.write({status:'pending',request_id:'unique'});assert.deepEqual(JSON.parse(fs.readFileSync(file)),{status:'pending',request_id:'unique'});assert.throws(()=>openLeaseCheckpoint(file),/owns/);writer.write({accepted:true});}finally{writer.close();}
 assert.equal(JSON.parse(fs.readFileSync(file)).accepted,true);assert.throws(()=>openLeaseCheckpoint(file),/preserved/);assert(!fs.existsSync(file+'.lock'));
}));
test('external replacement cannot be silently overwritten by checkpoint publication',()=>fixture(file=>{
 const writer=openLeaseCheckpoint(file);try{writer.write({status:'pending'});fs.writeFileSync(file,'sentinel');assert.throws(()=>writer.write({status:'pending'}),/outside/);assert.equal(fs.readFileSync(file,'utf8'),'sentinel');}finally{writer.close();}
}));
test('dead owner lock permits resume while retaining original pending identity',()=>fixture(file=>{
 const module=new URL('../scripts/issue-lease-checkpoint.mjs',import.meta.url).href;
 const child=spawnSync(process.execPath,['--input-type=module','-e',`import {openLeaseCheckpoint} from ${JSON.stringify(module)}; const w=openLeaseCheckpoint(${JSON.stringify(file)});w.write({status:'pending',request_id:'original'});process.exit(0);`],{encoding:'utf8'});
 assert.equal(child.status,0,child.stderr);const resumed=openLeaseCheckpoint(file);try{assert.equal(resumed.stored.request_id,'original');}finally{resumed.close();}
}));
test('symlink output and invalid collisions preserve existing bytes without leaking lock',()=>fixture(file=>{
 const sentinel=file+'.source';fs.writeFileSync(sentinel,'retained');fs.symlinkSync(sentinel,file);assert.throws(()=>openLeaseCheckpoint(file),/ordinary/);assert.equal(fs.readFileSync(sentinel,'utf8'),'retained');assert(!fs.existsSync(file+'.lock'));
}));

for(const value of [null,false,0,'',[],{}])test(`nonpending JSON ${JSON.stringify(value)} is preserved`,()=>fixture(file=>{
 const raw=JSON.stringify(value);fs.writeFileSync(file,raw);assert.throws(()=>openLeaseCheckpoint(file),/preserved/);assert.equal(fs.readFileSync(file,'utf8'),raw);assert(!fs.existsSync(file+'.lock'));
}));
