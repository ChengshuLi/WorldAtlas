import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync,spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {staticModuleClosure} from './helpers/static-module-closure.mjs';
import {inspectPreviewPackage,preparePreviewPackage,startPreview} from '../server.mjs';
import {observationContract} from '../src/observation-modules.js';
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const git=(root,...args)=>execFileSync('git',['--no-replace-objects','-C',root,...args],{encoding:'utf8',env:{...process.env,GIT_NO_LAZY_FETCH:'1',GIT_NO_REPLACE_OBJECTS:'1'}}).trim();
async function fixture(t,{cloudflare=false}={}){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-preview-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const put=(name,raw)=>{fs.mkdirSync(path.dirname(path.join(root,name)),{recursive:true});fs.writeFileSync(path.join(root,name),raw);};
 const source=fileURLToPath(new URL('../',import.meta.url));
 for(const name of staticModuleClosure(source,['server.mjs']))put(name,fs.readFileSync(path.join(source,name)));
 const reference={id:'geography:preview',footprints_sha256:'b'.repeat(64),hierarchy_sha256:'c'.repeat(64)};
 const output=cloudflare?'dist/client':'dist',word=Buffer.from('exact fixture words'),pin={path:'native-v1/ownership/rows-0.bin.gz',bytes:word.length,sha256:sha(word)};
 const proof={version:3,native_manifest_sha256:'a'.repeat(64),effective_reference:reference,base_reference:reference};
 const pixelMap={version:2,method:'native-linear-evenodd-first-owner-v1',parts:[pin]};
 const indexRaw=Buffer.from(JSON.stringify({version:3,native_manifest_sha256:'a'.repeat(64),preparedOwnership:proof,pixelMap,files:[pin]}));
 const selection={version:2,kind:'selected-final-native-bank-v2',native_selection:{version:1,method:pixelMap.method,manifest_path:'data/native/manifest.json',sha256:'a'.repeat(64),release_id:'geography:native',selected_geography:{kind:'complete-world-index-with-exact-encoded-overrides'}},prepared_bank:{path:'data/canonical-grid/current-startup/index.json',bytes:indexRaw.length,sha256:sha(indexRaw)},reference};
 put(selection.prepared_bank.path,indexRaw);put('data/ownership-selection.json',JSON.stringify(selection));
 put('src/probe.js',"export const staticAtlas=import.meta.env.VITE_STATIC_ATLAS; export const hosted=import.meta.env.VITE_HOSTED_DATABASE;\n");
 put('index.html','<script type="module" src="/src/probe.js"></script>');put('package.json','{"type":"module"}');
 put('.gitignore','dist/\n.cache/\nnode_modules/\n');
 const definition=JSON.stringify({version:1,inputs:['.github/package-inputs.json','data/','src/','scripts/','server.mjs','index.html','package.json'],optional_inputs:[],verification_paths:[],generated_outputs:['dist/']});
 put('.github/package-inputs.json',definition);
 git(root,'init','-q');git(root,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','add','.');git(root,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','Preview input fixture');
 const head=git(root,'rev-parse','HEAD');
 const typed=JSON.stringify({version:1,registry_sha256:(await observationContract()).registry_sha256,sources:[],entities:[],observations:[],feature_links:[],retirements:[]});
 const atlas=JSON.stringify({reference_release:reference,preparedOwnership:proof,pixelMap:{...pixelMap,reference_owner_sha256:'d'.repeat(64)}});
 function publish(){
  put(output+'/atlas-geography.json',atlas);put(output+'/'+pin.path,word);
  put(output+'/index.html','<!doctype html><title>Exact compiled preview</title>');put(output+'/atlas-history.json.gz','fixture-history');
  put(output+'/typed-evidence.json',typed);put(output+'/typed-evidence-manifest.json',JSON.stringify({version:1,path:'typed-evidence.json',bytes:Buffer.byteLength(typed),sha256:sha(typed)}));
  put(output+'/environment-classifications.json','{"version":1,"unknown":null,"attributes":{"fixture":true}}');
  put('.cache/package-input-build.json',JSON.stringify({kind:cloudflare?'cloudflare':'static',input_definition_sha256:sha(definition),preflight:{passed:true,inputs:{head}}}));
 }
 publish();fs.symlinkSync(fs.realpathSync(new URL('../node_modules',import.meta.url)),path.join(root,'node_modules'),'dir');
 return {root,output,put,publish,pin,selection,atlas};
}

test('preview reuses canonical output without build; missing/stale/damaged output uses only the normal builder',async t=>{
 const f=await fixture(t);let calls=0;
 const build=async(kind,{root})=>{calls++;assert.equal(kind,'static');assert.equal(root,f.root);f.publish();};
 assert.equal((await preparePreviewPackage(f.root,{build})).output,'dist');assert.equal(calls,0);
 f.put('research-note.txt','Unrelated evidence does not require a package rebuild');git(f.root,'add','research-note.txt');git(f.root,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','Unrelated evidence');
 await preparePreviewPackage(f.root,{build});assert.equal(calls,0);
 fs.unlinkSync(path.join(f.root,'dist/atlas-geography.json'));await preparePreviewPackage(f.root,{build});assert.equal(calls,1);
 f.put('src/probe.js','// real source edit, not erased by preview\n');await preparePreviewPackage(f.root,{build});assert.equal(calls,2);
 assert.match(fs.readFileSync(path.join(f.root,'src/probe.js'),'utf8'),/real source edit/);
 f.put('dist/'+f.pin.path,'damaged');assert.throws(()=>inspectPreviewPackage(f.root),/member differs/);
 await assert.rejects(preparePreviewPackage(f.root,{build:async()=>{throw Error('required canonical input unavailable');}}),/required canonical input unavailable/);
 assert.equal(fs.readFileSync(path.join(f.root,'dist/'+f.pin.path),'utf8'),'damaged','failed preparation does not silently rewrite prior output');
 f.publish();const atlas=JSON.parse(f.atlas);atlas.reference_release={...atlas.reference_release,id:'geography:stale'};f.put('dist/atlas-geography.json',JSON.stringify(atlas));
 assert.throws(()=>inspectPreviewPackage(f.root),/final release differs/);
});

for(const production of [false,true])for(const cloudflare of [false,true])test(`actual ${production?'start':'dev'} HTTP route serves ${cloudflare?'Cloudflare':'standalone'} package, preserves GETs and never creates a DB`,async t=>{
 const f=await fixture(t,{cloudflare});
 const child=spawn(process.execPath,['server.mjs',...(production?['--production']:[])],{cwd:f.root,env:{...process.env,PORT:'0',ATLAS_TEST_MODE:'1'},stdio:['ignore','pipe','pipe']});
 let stdout='',stderr='';child.stdout.on('data',chunk=>stdout+=chunk);child.stderr.on('data',chunk=>stderr+=chunk);
 t.after(async()=>{if(child.exitCode===null){const exit=new Promise(resolve=>child.once('exit',resolve));child.kill('SIGTERM');await exit;}});
 const base=await new Promise((resolve,reject)=>{
   child.stdout.on('data',()=>{const match=/WorldAtlas listening on (http:\/\/localhost:\d+)/.exec(stdout);if(match)resolve(match[1].replace('localhost','127.0.0.1'));});
   child.once('error',reject);child.once('exit',code=>reject(Error('Preview exited '+code+': '+stderr)));
 });
 assert.equal(await(await fetch(base+'/atlas-geography.json')).text(),f.atlas);
 assert.equal(await(await fetch(base+'/'+f.pin.path)).text(),'exact fixture words');
 assert.deepEqual(await(await fetch(base+'/api/classifications')).json(),{version:1,unknown:null,attributes:{fixture:true}});
 const typed=await fetch(base+'/api/typed/v1/prepared-snapshot?year=2026');assert.equal(typed.status,200);assert.equal((await typed.json()).year,2026);
 assert.equal((await fetch(base+'/api/typed/v1/prepared-snapshot?year=0')).status,400);
 for(const route of ['/api/geography','/api/snapshot?year=2026'])assert.equal((await fetch(base+route)).status,404);
 assert.equal((await fetch(base+'/api/classifications',{method:'POST'})).status,405);
 assert.equal((await fetch(base+'/atlas-geography.json',{method:'POST'})).status,405);
 if(production)assert.match(await(await fetch(base+'/')).text(),/Exact compiled preview/);
 else{const source=await(await fetch(base+'/src/probe.js')).text();const module=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));assert.equal(module.staticAtlas,'true');assert.equal(module.hosted,'false');}
 assert.doesNotMatch(stdout,/Preparing canonical/);assert.equal(fs.existsSync(path.join(f.root,'data/atlas.sqlite')),false);
 assert.equal(fs.existsSync(path.join(f.root,'.cache/package-atlas.sqlite')),false);
});


test('preview refuses mismatched current headers, members, staged inputs and hidden worktree edits',async t=>{
 const f=await fixture(t);
 for(const mutate of [atlas=>atlas.preparedOwnership.native_manifest_sha256='f'.repeat(64),atlas=>atlas.pixelMap.parts=[],atlas=>atlas.referenceMetadata={version:1}]){
  const atlas=JSON.parse(f.atlas);mutate(atlas);f.put('dist/atlas-geography.json',JSON.stringify(atlas));assert.throws(()=>inspectPreviewPackage(f.root),/differs/);f.publish();
 }
 const failBuild=async()=>{throw Error('normal constructor selected');};
 f.put('src/probe.js','// staged change');git(f.root,'add','src/probe.js');
 await assert.rejects(preparePreviewPackage(f.root,{build:failBuild}),/normal constructor selected/);
 git(f.root,'restore','--staged','--worktree','src/probe.js');git(f.root,'update-index','--assume-unchanged','src/probe.js');
 f.put('src/probe.js','// hidden dirty change');await assert.rejects(preparePreviewPackage(f.root,{build:failBuild}),/normal constructor selected/);
 assert.equal(fs.readFileSync(path.join(f.root,'src/probe.js'),'utf8'),'// hidden dirty change');
});
