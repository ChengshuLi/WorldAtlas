import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import os from 'node:os';import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {pinReader} from '../scripts/prepare-delivery-handoff.mjs';
import {authenticateLocalPinnedInput,captureCanonicalInputs} from '../coordination/engineering/fiji-current-cell-20261016/evidence/reproduce-canonical-views.mjs';
test('Fiji reproduction authenticates complete local inputs against original immutable pins',t=>{
 const root=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'fiji-original-custody-')));
 t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const git=(...args)=>execFileSync('git',args,{cwd:root,encoding:'utf8'}).trim();
 git('init','-q');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid');
 const names=['original-stage-inputs.json','whole-target-support.json','execution-receipt.json','source-evidence.json'];
 for(const name of names)fs.writeFileSync(path.join(root,name),JSON.stringify({original:name,geometry:{type:'Polygon',coordinates:[]}})+'\n');
 git('add','.');git('commit','-qm','Original complete bodies');
 const commit=git('rev-parse','HEAD'),reader=pinReader(root);
 for(const name of names){
  const pin=reader.pin(commit,name),original=fs.readFileSync(path.join(root,name));
  assert.deepEqual(authenticateLocalPinnedInput(reader,root,pin),original);
  const changed=JSON.parse(original);changed.geometry.coordinates=[[[0,0],[1,0],[0,1],[0,0]]];
  fs.writeFileSync(path.join(root,name),JSON.stringify(changed)+'\n');
  assert.throws(()=>authenticateLocalPinnedInput(reader,root,pin),/Original local input differs/);
  fs.writeFileSync(path.join(root,name),original);
  assert.deepEqual(authenticateLocalPinnedInput(reader,root,pin),original);
 }
 const evidence={physical_input:reader.pin(commit,names[0]),physical_evidence:reader.pin(commit,names[1])};
 const captured=captureCanonicalInputs(reader,root,evidence);
 // Mutate the two isolated local fixtures after authentication/capture. The
 // actual Python envelope reader must consume the captured original bodies.
 for(const role of Object.keys(evidence))fs.writeFileSync(path.join(root,evidence[role].path),'{}\n');
 const program=path.resolve('coordination/engineering/fiji-current-cell-20261016/evidence/reproduce-canonical-views.py');
 const readCaptured=`import importlib.util,json,sys\nspec=importlib.util.spec_from_file_location('fiji',sys.argv[1])\nm=importlib.util.module_from_spec(spec)\nspec.loader.exec_module(m)\nprint(json.dumps(m.read_captured_inputs(sys.stdin)))`;
 const consume=input=>execFileSync('python3',['-c',readCaptured,program],{input,encoding:'utf8',stdio:['pipe','pipe','pipe']});
 const actualCaptured=JSON.parse(consume(captured));
 for(const role of Object.keys(evidence))assert.deepEqual(actualCaptured[role],JSON.parse(reader.read(evidence[role])));
 assert.throws(()=>captureCanonicalInputs(reader,root,evidence),/Original local input differs/);
 for(const field of ['bytes','sha256','body_base64']){
  const changed=JSON.parse(captured);
  changed.inputs.physical_input[field]=field==='bytes'?0:field==='sha256'?'0'.repeat(64):Buffer.from('{}').toString('base64');
  assert.throws(()=>consume(JSON.stringify(changed)),/Captured input differs/);
 }
 for(const role of Object.keys(evidence))fs.writeFileSync(path.join(root,evidence[role].path),reader.read(evidence[role]));
 const pin=reader.pin(commit,names[0]),actual=path.join(root,names[0]);
 fs.renameSync(actual,path.join(root,'original-copy.json'));fs.symlinkSync('original-copy.json',actual);
 assert.throws(()=>authenticateLocalPinnedInput(reader,root,pin),/ordinary file/);
});
