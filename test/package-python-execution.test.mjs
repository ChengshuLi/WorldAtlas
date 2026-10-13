import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {execFileSync,spawnSync} from 'node:child_process';
import {packagePythonArgs,packagePythonProbeArgs} from '../scripts/package-build.mjs';

async function fixture(t){
 const root=await fs.mkdtemp(path.join(os.tmpdir(),'package-python-execution-'));
 t.after(()=>fs.rm(root,{recursive:true,force:true}));
 const venv=path.join(root,'venv');execFileSync('python3',['-I','-S','-B','-m','venv','--without-pip',venv]);
 const python=path.join(venv,'bin/python3');
 const version=execFileSync(python,['-I','-S','-B','-c','import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")'],{encoding:'utf8'}).trim();
 const site=path.join(venv,'lib','python'+version,'site-packages'),scripts=path.join(root,'scripts'),marker=path.join(root,'hooks');
 await fs.mkdir(site,{recursive:true});await fs.mkdir(scripts);
 const hook='import pathlib;pathlib.Path('+JSON.stringify(marker)+').write_text("executed")\n';
 await fs.writeFile(path.join(site,'sitecustomize.py'),hook);await fs.writeFile(path.join(site,'active.pth'),hook);
 await fs.writeFile(path.join(site,'science.py'),'__version__="1.0"\nvalue="installed"\n');
 const run=args=>execFileSync(python,args,{encoding:'utf8',input:'payload',env:{...process.env,PYTHONPATH:scripts}});
 return {root,python,site,scripts,marker,run};
}

test('real script, inline code and import probe share isolated startup and installed precedence',async t=>{
 const f=await fixture(t),script=path.join(f.scripts,'operation.py');
 await fs.writeFile(path.join(f.scripts,'sibling.py'),'value="authored"\n');
 await fs.writeFile(path.join(f.scripts,'science.py'),'raise RuntimeError("local science must not shadow installed runtime")\n');
 await fs.writeFile(script,'import science,sibling,sys,json\nprint(json.dumps([science.value,sibling.value,sys.argv[1:],sys.stdin.read(),__file__]))\n');
 assert.deepEqual(JSON.parse(f.run(packagePythonArgs([script,'arg']))),['installed','authored',['arg'],'payload',script]);
 assert.deepEqual(JSON.parse(f.run(packagePythonArgs(['-c','import science,sys,json;print(json.dumps([science.value,sys.argv[1:],sys.stdin.read()]))','arg']))),['installed',['arg'],'payload']);
 assert.equal(JSON.parse(f.run(packagePythonProbeArgs([{name:'science',version:'1.0'}]))).imports[0].actual,'1.0');
 await assert.rejects(fs.stat(f.marker),{code:'ENOENT'});
 f.run(['-c','pass']);assert.equal(await fs.readFile(f.marker,'utf8'),'executed');
});

test('script-parent namespace portions cannot expand or replace installed import roots',async t=>{
 const f=await fixture(t),script=path.join(f.scripts,'operation.py');
 await fs.mkdir(path.join(f.site,'sharedns'));await fs.writeFile(path.join(f.site,'sharedns','installed.py'),'value=1\n');
 await fs.mkdir(path.join(f.scripts,'sharedns'));await fs.writeFile(path.join(f.scripts,'sharedns','injected.py'),'value=2\n');
 await fs.writeFile(script,'raise RuntimeError("must fail before script executes")\n');
 for(const regular of [false,true]){
  if(regular)await fs.writeFile(path.join(f.scripts,'sharedns','__init__.py'),'value=3\n');
  const result=spawnSync(f.python,packagePythonArgs([script]),{encoding:'utf8'});
  assert.notEqual(result.status,0);assert.match(result.stderr,/changes admitted import resolution: sharedns/);
  assert.doesNotMatch(result.stderr,/RuntimeError: must fail/);
 }
});

test('real execution retains explicit failures and rejects unsupported invocation forms',async t=>{
 const f=await fixture(t);
 const result=spawnSync(f.python,packagePythonArgs(['-c','raise ValueError("genuine operation failure")']),{encoding:'utf8'});
 assert.notEqual(result.status,0);assert.match(result.stderr,/ValueError: genuine operation failure/);
 assert.throws(()=>packagePythonArgs(['-m','arbitrary']),/explicit source/);
 assert.throws(()=>packagePythonArgs(['-c']),/Explicit Python source/);
});

test('current wrapper drives unchanged critical checkPrepared through real isolated Python',async t=>{
 const f=await fixture(t),{createPackagePythonExecution}=await import('../scripts/package-build.mjs');
 const {createHash}=await import('node:crypto'),hash=raw=>createHash('sha256').update(raw).digest('hex');
 await fs.writeFile(path.join(f.root,'package.json'),'{"type":"module"}');
 for(const name of ['package-python-runtime.py','boundary-version-hash.py','check-prepared.mjs'])await fs.copyFile(new URL('../scripts/'+name,import.meta.url),path.join(f.scripts,name));
 await fs.mkdir(path.join(f.site,'shapely'));await fs.writeFile(path.join(f.site,'shapely','__init__.py'),'');await fs.writeFile(path.join(f.site,'shapely','geometry.py'),'def shape(value): return value\n');
 const majority='def canonical(value): return value\n',algorithm={path:'majority.py',sha256:hash(majority)},footprint=hash('[]');
 const owner={footprints_sha256:footprint,locations:0,execution_algorithms:[algorithm],initial_execution:{algorithms:[algorithm],inputs:{algorithm_sha256:algorithm.sha256}},inputs:{algorithm_sha256:algorithm.sha256,boundary_versions:footprint},parts:[]};
 const ownerRaw=JSON.stringify(owner),files={
  'data/ownership-history/index.json':ownerRaw,'data/ownership-history/majority.py':majority,
  'data/reference-attributes/index.json':JSON.stringify({footprints_sha256:footprint,locations:0,parts_sha256:{}}),
  'data/pixel-audit.json':JSON.stringify({footprints_sha256:footprint,locations:0}),
  'data/ownership-runtime/index.json':JSON.stringify({source_index_sha256:hash(ownerRaw),shared:{footprints_sha256:footprint},buckets:[]})};
 for(const[name,body]of Object.entries(files)){await fs.mkdir(path.dirname(path.join(f.root,name)),{recursive:true});await fs.writeFile(path.join(f.root,name),body);}
 execFileSync(f.python,['-I','-S','-B','-c','import sqlite3,sys;c=sqlite3.connect(sys.argv[1]);c.execute("CREATE TABLE boundaries(location_id,valid_from,valid_to,geometry,is_example)");c.close()',path.join(f.root,'data/atlas.sqlite')]);
 const actual=await fs.readFile(path.join(f.scripts,'check-prepared.mjs'));
 assert.equal(hash(actual),'66926416887b1e3a69962837a9e10ff322dc061f6f1a70be4624edb3583c5242');
 const helperRaw=await fs.readFile(new URL('../scripts/package-python-runtime.py',import.meta.url));
 const sourceHelper={path:'scripts/package-python-runtime.py',bytes:helperRaw.length,sha256:hash(helperRaw),mode:'100644'};
 await fs.appendFile(path.join(f.scripts,'package-python-runtime.py'),'# staged substitution\n');
 assert.throws(()=>createPackagePythonExecution(f.root,{python:f.python,sourceHelper}),/independently authenticated source/);
 await fs.writeFile(path.join(f.scripts,'package-python-runtime.py'),helperRaw);
 const launch=createPackagePythonExecution(f.root,{python:f.python,sourceHelper,env:{...process.env,NODE_OPTIONS:'',NODE_PATH:''}});
 const result=execFileSync(process.execPath,['--input-type=module','-e','import{checkPrepared}from"./scripts/check-prepared.mjs";console.log(checkPrepared([]));'],{cwd:f.root,env:launch.env,encoding:'utf8'}).trim();
 assert.equal(result,footprint);launch.verify();await assert.rejects(fs.stat(f.marker),{code:'ENOENT'});
 const child=spawnSync('python3',['-c','import sys,json;print(json.dumps([sys.argv[1:],sys.stdin.read()]));raise SystemExit(17)','arg'],{env:launch.env,input:'payload',encoding:'utf8'});
 assert.equal(child.status,17);assert.deepEqual(JSON.parse(child.stdout),[['arg'],'payload']);launch.verify();
 const signalled=spawnSync('python3',['-c','import os,signal;os.kill(os.getpid(),signal.SIGTERM)'],{env:launch.env,encoding:'utf8'});assert.equal(signalled.signal,'SIGTERM');launch.verify();
 await fs.appendFile(launch.record.launcher.path,'// mutation\n');assert.throws(()=>launch.verify(),/execution tool changed/);
});

test('package wrapper records real child custody and cleans its stage on success and failure',async t=>{
 const f=await fixture(t),{runPackageBuild}=await import('../scripts/package-build.mjs');
 await fs.copyFile(new URL('../scripts/package-python-runtime.py',import.meta.url),path.join(f.scripts,'package-python-runtime.py'));
 const definition={version:1,inputs:['.github/package-inputs.json','package.json','scripts/build-static-inner.mjs','scripts/package-python-runtime.py'],optional_inputs:[],verification_paths:[],generated_outputs:['dist/']};
 await fs.mkdir(path.join(f.root,'.github'));await fs.mkdir(path.join(f.root,'node_modules'));
 await fs.writeFile(path.join(f.root,'.github/package-inputs.json'),JSON.stringify(definition));await fs.writeFile(path.join(f.root,'package.json'),'{"type":"module"}');
 const program="import fs from 'node:fs';import{execFileSync}from'node:child_process';const value=execFileSync('python3',['-c','import science;print(science.value)'],{encoding:'utf8'});fs.mkdirSync('dist');fs.writeFileSync('dist/value',value);";
 const entry=path.join(f.scripts,'build-static-inner.mjs');await fs.writeFile(entry,program);
 const git=args=>execFileSync('git',['-C',f.root,...args],{encoding:'utf8',env:{...process.env,GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:'/dev/null'}});
 git(['init','-q']);git(['add','.github/package-inputs.json','package.json','scripts/']);git(['-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false','commit','-qm','Package source fixture']);
 const preflight=async()=>({passed:true,inputs:{head:git(['rev-parse','HEAD']).trim()},runtime:{python:{executable:f.python}}});
 const prior=process.env.NODE_OPTIONS;delete process.env.NODE_OPTIONS;t.after(()=>prior===undefined?delete process.env.NODE_OPTIONS:process.env.NODE_OPTIONS=prior);
 const receipt=await runPackageBuild('static',{root:f.root,preflight});
 assert.equal(receipt.current_python_execution.kind,'current-package-isolated-python-execution-v1');
 assert.equal(await fs.readFile(path.join(f.root,'dist/value'),'utf8'),'installed\n');
 await assert.rejects(fs.stat(receipt.current_python_execution.launcher.path),{code:'ENOENT'});
 definition.inputs=['.github/package-inputs.json','package.json','scripts/'];await fs.writeFile(path.join(f.root,'.github/package-inputs.json'),JSON.stringify(definition));
 const directoryCovered=await runPackageBuild('static',{root:f.root,preflight});assert.equal(directoryCovered.current_python_execution.kind,'current-package-isolated-python-execution-v1');
 await assert.rejects(fs.stat(directoryCovered.current_python_execution.launcher.path),{code:'ENOENT'});
 await fs.writeFile(entry,program+'throw Error("actual child failure");');
 await assert.rejects(runPackageBuild('static',{root:f.root,preflight}),/build failed/);
 assert.equal(await fs.readFile(path.join(f.root,'dist/value'),'utf8'),'installed\n');
 assert.equal((await fs.readdir(path.join(f.root,'.cache'))).filter(name=>name.startsWith('package-input-image-')).length,0);
 await assert.rejects(fs.stat(f.marker),{code:'ENOENT'});
});
