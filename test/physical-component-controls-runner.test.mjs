import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawn,spawnSync} from 'node:child_process';

function fixture(t,body) {
  const root=fs.mkdtempSync(path.join(process.cwd(),'.cache/component-runner-'));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  const python=path.join(root,'python'),done=path.join(root,'done');
  fs.writeFileSync(python,`#!${process.execPath}\n${body.replaceAll('DONE_PATH',JSON.stringify(done))}`,{flag:'wx',mode:0o700});
  const env={...process.env,PYTHON:python};delete env.NODE_TEST_CONTEXT;
  const args=['--test','--test-reporter=tap','test/physical-component-evidence-controls.test.mjs'];
  return {env,args,done};
}
test('actual control wrapper rejects failure even when a producer prints the expected test count',t=>{
  const f=fixture(t,"console.error('Ran 7 tests');console.error('semantic failure');process.exit(3);");
  const r=spawnSync(process.execPath,f.args,{env:f.env,encoding:'utf8',timeout:5000});
  assert.notEqual(r.status,0);assert.match(r.stdout+r.stderr,/semantic failure/);
});
test('actual control wrapper rejects a zero exit without all seven controls',t=>{
  const f=fixture(t,"console.error('Ran 6 tests');");
  const r=spawnSync(process.execPath,f.args,{env:f.env,encoding:'utf8',timeout:5000});
  assert.notEqual(r.status,0);assert.match(r.stdout+r.stderr,/Ran 6 tests/);
});
test('actual control wrapper streams the active Python phase before producer completion',async t=>{
  const f=fixture(t,"import fs from 'node:fs';console.error('ACTIVE_CONTROL_PHASE');setTimeout(()=>{fs.writeFileSync(DONE_PATH,'done');console.error('Ran 7 tests');},500);");
  const child=spawn(process.execPath,f.args,{env:f.env,stdio:['ignore','pipe','pipe']});
  t.after(()=>child.kill('SIGKILL'));
  let text='',live=false;
  for(const stream of [child.stdout,child.stderr])stream.on('data',b=>{
    text+=b;if(text.includes('ACTIVE_CONTROL_PHASE')&&!fs.existsSync(f.done))live=true;
  });
  const status=await new Promise(resolve=>child.once('close',resolve));
  assert.equal(status,0,text);assert.ok(live,'active control must be visible before completion');
});
