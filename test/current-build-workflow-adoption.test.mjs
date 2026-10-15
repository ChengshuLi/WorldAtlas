import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync,spawnSync} from 'node:child_process';

const repo=process.cwd(),helper='coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/model-reader-call-boundary-controls.mjs';
const hash=raw=>createHash('sha256').update(raw).digest('hex');
// This is the actual accepted-main caller that first adoption must execute,
// even though the candidate removes that obsolete workflow step permanently.
const command=fs.readFileSync(path.join(repo,'test/fixtures/current-build-inherited-readback.sh'),'utf8');

function fixture(t){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-current-adoption-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const write=(name,value)=>{const file=path.join(root,name);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,typeof value==='string'?value:JSON.stringify(value));};
 fs.cpSync(path.join(repo,'scripts'),path.join(root,'scripts'),{recursive:true});
 write('package.json','{"type":"module"}');fs.mkdirSync(path.dirname(path.join(root,helper)),{recursive:true});fs.copyFileSync(path.join(repo,helper),path.join(root,helper));
 const pin={path:'historical/not-materialized.json',mode:'100644',bytes:1,sha256:'a'.repeat(64)};
 const selection={version:1,method:'native-linear-evenodd-first-owner-v1',manifest_path:'data/base.json',sha256:'b'.repeat(64),release_id:'geography:fixture',artifact_consumption:{certificate:pin,review:pin}};
 write('data/ownership-selection.json',selection);
 const git=(...args)=>execFileSync('git',['-C',root,...args],{encoding:'utf8'}).trim();git('init','-q');git('add','.');git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','Current build adoption fixture');
 const atlas={nativeContextInputStage:{status:'accepted-prepared-assets',native_manifest_sha256:selection.sha256},pixelMap:{canonical_grid_sha256:selection.sha256}};
 write('dist/client/atlas-geography.json',atlas);write('dist/cloudflare/index.js','actual worker');write('dist/cloudflare/wrangler.json','{}');
 const files=['dist/client/atlas-geography.json','dist/cloudflare/index.js','dist/cloudflare/wrangler.json'].map(name=>{const raw=fs.readFileSync(path.join(root,name));return{path:name,bytes:raw.length,sha256:hash(raw)};});
 const definition={version:1,inputs:['.github/package-inputs.json','data/ownership-selection.json'],optional_inputs:[],verification_paths:[],generated_outputs:['dist/']};
 const manifest={version:1,kind:'original-cloudflare-package-output',source:{head:git('rev-parse','HEAD'),tree:git('rev-parse','HEAD^{tree}'),input_definition_sha256:'c'.repeat(64),selection,definition,files:[{path:'data/ownership-selection.json',mode:'100644',oid:git('rev-parse','HEAD:data/ownership-selection.json')}]},runtime:{node:process.version,platform:process.platform,arch:process.arch,dependencies:'d'.repeat(64),installed:{node:{sha256:'e'.repeat(64)},dependencies:{sha256:'f'.repeat(64)}}},configuration:{},output:{files,bytes:files.reduce((sum,row)=>sum+row.bytes,0)}};
 write('.cache/package-output-manifest.json',manifest);
 const run=()=>spawnSync('/bin/bash',['-e','-o','pipefail','-c',command],{cwd:root,encoding:'utf8',env:{...process.env,PATH:path.dirname(process.execPath)+':/usr/bin:/bin',NODE_PATH:'',NODE_OPTIONS:''}});
 return{root,write,atlas,manifest,run};
}

test('actual inherited workflow caller admits current output without any historical inputs or report',t=>{
 const f=fixture(t);assert.equal(fs.existsSync(path.join(f.root,'historical')),false);
 const result=f.run();assert.equal(result.status,0,result.stderr);assert.match(result.stdout,/existing package inventory/);assert.match(result.stdout,/no report is claimed/);
 assert.equal(fs.existsSync(path.join(f.root,'.cache/native-normal-built-output.json')),false);
});

test('inherited caller still rejects stale identity and real output corruption before claiming a report',t=>{
 for(const edit of [
  f=>{f.manifest.source.head='0'.repeat(40);f.write('.cache/package-output-manifest.json',f.manifest);},
  f=>{f.atlas.pixelMap.canonical_grid_sha256='0'.repeat(64);f.write('dist/client/atlas-geography.json',f.atlas);const raw=fs.readFileSync(path.join(f.root,'dist/client/atlas-geography.json'));Object.assign(f.manifest.output.files[0],{bytes:raw.length,sha256:hash(raw)});f.manifest.output.bytes=f.manifest.output.files.reduce((n,p)=>n+p.bytes,0);f.write('.cache/package-output-manifest.json',f.manifest);},
  f=>f.write('dist/cloudflare/index.js','corrupted actual worker')
 ]){const f=fixture(t);edit(f);const result=f.run();assert.notEqual(result.status,0);assert.equal(fs.existsSync(path.join(f.root,'.cache/native-normal-built-output.json')),false);}
});
