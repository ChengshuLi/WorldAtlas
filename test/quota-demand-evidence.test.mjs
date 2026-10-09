import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import os from 'node:os';import path from 'node:path';import {spawnSync} from 'node:child_process';
const original=path.resolve(import.meta.dirname,'../coordination/engineering/global-quota-1543-20261009');
const fixture=run=>{const dir=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-demand-'));try{for(const name of ['aggregate-demand.mjs','day-inventory.json','day-demand.json','day-evidence-demand.json','day-claims.json'])fs.copyFileSync(path.join(original,name),path.join(dir,name));return run(dir);}finally{fs.rmSync(dir,{recursive:true,force:true});}};
const cli=(dir,out)=>spawnSync(process.execPath,[path.join(dir,'aggregate-demand.mjs'),'--out',out],{encoding:'utf8'});
test('real aggregate entrypoint requires fresh output and preserves ordinary/symlink sentinels',()=>fixture(dir=>{
 const target=path.join(dir,'retained');fs.mkdirSync(target);fs.writeFileSync(path.join(target,'demand-summary.json'),'sentinel');assert.notEqual(cli(dir,target).status,0);assert.equal(fs.readFileSync(path.join(target,'demand-summary.json'),'utf8'),'sentinel');assert.equal(fs.readdirSync(target).length,1);
 const link=path.join(dir,'link');fs.symlinkSync(target,link);assert.notEqual(cli(dir,link).status,0);assert.equal(fs.readFileSync(path.join(target,'demand-summary.json'),'utf8'),'sentinel');
 const fresh=path.join(dir,'fresh');const good=cli(dir,fresh);assert.equal(good.status,0,good.stderr);assert.equal(JSON.parse(fs.readFileSync(path.join(fresh,'run-receipt.json'))).status,'complete');assert.equal(JSON.parse(fs.readFileSync(path.join(fresh,'demand-summary.json'))).workflow_runs,1243);assert.notEqual(cli(dir,fresh).status,0);
}));
test('aggregate import is pure and invalid inputs create no outputs',()=>fixture(dir=>{
 const pure=spawnSync(process.execPath,['--input-type=module','-e',`await import(${JSON.stringify('file://'+path.join(dir,'aggregate-demand.mjs'))})`],{encoding:'utf8'});assert.equal(pure.status,0,pure.stderr);assert.equal(fs.readdirSync(dir).length,5);
 fs.writeFileSync(path.join(dir,'day-inventory.json'),JSON.stringify({runs:[{id:1},{id:1}]}));const out=path.join(dir,'failed');assert.notEqual(cli(dir,out).status,0);assert(!fs.existsSync(out));
}));

test('independent consumer join and missing-roster mutations reject before publishing',()=>fixture(dir=>{
 const file=path.join(dir,'day-demand.json'), original=JSON.parse(fs.readFileSync(file));
 const wrong=structuredClone(original);wrong.runs.find(r=>r.path==='.github/workflows/worker-merge.yml').path='.github/workflows/merge-scheduler.yml';fs.writeFileSync(file,JSON.stringify(wrong));const first=path.join(dir,'wrong');assert.notEqual(cli(dir,first).status,0);assert(!fs.existsSync(first));
 original.runs.pop();fs.writeFileSync(file,JSON.stringify(original));const second=path.join(dir,'missing');assert.notEqual(cli(dir,second).status,0);assert(!fs.existsSync(second));
}));
