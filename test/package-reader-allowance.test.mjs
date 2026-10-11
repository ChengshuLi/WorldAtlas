import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {ImmutableReader} from '../scripts/check-effective-geographic-regression.mjs';
import {readBoundPublicationAssets} from '../coordination/engineering/additive-native-activation-20261009/package-selected-additive.mjs';
const MiB=1024**2;
test('package publication copy inherits the admitted current allowance',t=>{
 const repo=fs.mkdtempSync(path.join(os.tmpdir(),'package-current-allowance-'));t.after(()=>fs.rmSync(repo,{recursive:true}));
 const git=(...args)=>execFileSync('git',['-C',repo,...args],{encoding:'utf8',stdio:['ignore','pipe','pipe']}).trim();
 git('init');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid');
 for(let i=0;i<4;i++)fs.writeFileSync(path.join(repo,`${i}.json`),Buffer.alloc(2*MiB,48+i),{flag:'wx'});
 git('add','.');git('commit','-m','Immutable publication fixture');const head=git('rev-parse','HEAD');
 const make=phaseBytes=>new ImmutableReader(repo,head,{runtimeBytes:1,executionBytes:1,metadataBytes:200*MiB,outputBytes:8*MiB,allowance:{phaseBytes,rssBytes:1024*MiB}});
 const r=make(256*MiB),roster=Array.from({length:4},(_,i)=>{const name=`${i}.json`,pin=r.descriptor(name);return {pin:{...pin,sha256:createHash('sha256').update(fs.readFileSync(path.join(repo,name))).digest('hex')}};});
 const copied=readBoundPublicationAssets(r,roster,()=>true);assert.equal(copied.bodies.length,4);assert.equal(copied.bodies.reduce((n,b)=>n+b.length,0),8*MiB);assert(copied.complete_phase_bytes<256*MiB);
 assert.throws(()=>readBoundPublicationAssets(make(210*MiB),roster,()=>true),/prospective cap/);
});

test('package outer entry derives its output reserve from the authenticated roster',()=>{
 const body=fs.readFileSync(new URL('../coordination/engineering/additive-native-activation-20261009/package-selected-additive.mjs',import.meta.url),'utf8');
 assert(!body.includes('4194304'));assert.match(body,/reader.outputBytes=outputBytes/);assert.match(body,/outputBytes<=reader.phaseLimit/);
});
