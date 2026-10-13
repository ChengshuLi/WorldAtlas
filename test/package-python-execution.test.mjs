import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {execFileSync,spawnSync} from 'node:child_process';
import {packagePythonArgs,packagePythonProbeArgs} from '../scripts/package-python-execution.mjs';

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
