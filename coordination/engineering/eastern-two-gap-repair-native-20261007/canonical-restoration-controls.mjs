// Exercise the actual custody functions with tiny complete ordinary bodies.
import fs from 'node:fs';import os from 'node:os';import path from 'node:path';
import vm from 'node:vm';import assert from 'node:assert/strict';import {createHash} from 'node:crypto';
import {restoreCanonicalProducts} from './restore-canonical-products.mjs';
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const source=new URL('./restore-canonical-products.mjs',import.meta.url);
const raw=fs.readFileSync(source),text=raw.toString('utf8');
// Only expose the literal private functions; keep their real filesystem/hash operators.
const local=text.replace(/^import .*;$/gm,'').replace(/^export /gm,'');
const context=vm.createContext({fs,path,assert,createHash,Buffer,process,Map,Set});
vm.runInContext(local+'\nglobalThis.actual={ordinary,read,copy};',context,{filename:source.pathname});
const fixture=fs.mkdtempSync(path.join(process.cwd(),'.cache/1295-restoration-controls-'));
const sourceRoot=path.join(fixture,'source'),targetRoot=path.join(fixture,'target');
fs.mkdirSync(sourceRoot);fs.mkdirSync(targetRoot);
const newBody=Buffer.from('new'),oldBody=Buffer.from('old');
fs.writeFileSync(path.join(sourceRoot,'body'),newBody);
const pin={path:'body',bytes:3,sha256:sha(newBody),mode:'100644'};
const original={path:'value',bytes:3,sha256:sha(oldBody),mode:'100644'};
const results=[];function rejected(name,fn){assert.throws(fn);results.push(name);}
try{
 assert(context.actual.read(sourceRoot,pin).equals(newBody));results.push('complete-body-positive');
 fs.writeFileSync(path.join(targetRoot,'value'),oldBody);context.actual.copy(targetRoot,'value',sourceRoot,pin,original);
 assert(fs.readFileSync(path.join(targetRoot,'value')).equals(newBody));results.push('exact-original-to-successor-positive');
 fs.writeFileSync(path.join(targetRoot,'value'),'bad');
 rejected('foreign-existing-before-write',()=>context.actual.copy(targetRoot,'value',sourceRoot,pin,original));
 assert.equal(fs.readFileSync(path.join(targetRoot,'value'),'utf8'),'bad');
 rejected('wrong-whole-sha',()=>context.actual.read(sourceRoot,{...pin,sha256:'0'.repeat(64)}));
 rejected('overbound-declaration-before-read',()=>context.actual.read(sourceRoot,{...pin,bytes:32*1024*1024+1}));
 rejected('wrong-eof-length',()=>context.actual.read(sourceRoot,{...pin,bytes:2}));
 rejected('absolute-path',()=>context.actual.ordinary(targetRoot,'/outside'));
 rejected('parent-traversal',()=>context.actual.ordinary(targetRoot,'../outside'));
 const linked=path.join(fixture,'linked');fs.symlinkSync(targetRoot,linked);
 rejected('supplied-symlink-root',()=>context.actual.ordinary(linked,'value'));
 fs.symlinkSync(sourceRoot,path.join(targetRoot,'ancestor'));
 rejected('symlink-ancestor',()=>context.actual.ordinary(targetRoot,'ancestor/body'));
 const priorStage=process.env.WORLDATLAS_PACKAGE_STAGE;
 delete process.env.WORLDATLAS_PACKAGE_STAGE;
 rejected('missing-normal-package-boundary-before-write',()=>restoreCanonicalProducts({root:targetRoot,temporaryRoot:fixture}));
 if(priorStage===undefined)delete process.env.WORLDATLAS_PACKAGE_STAGE;else process.env.WORLDATLAS_PACKAGE_STAGE=priorStage;
 console.log(JSON.stringify({status:'PASS',controls:results,actual_source_sha256:sha(raw),
  driver:'literal private-function exposure only; real ordinary filesystem/hash/read/copy operators',scientific_producers_invoked:false}));
}finally{fs.rmSync(fixture,{recursive:true});}
