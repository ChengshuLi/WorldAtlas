import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {PassThrough} from 'node:stream';
import {streamTestProcess} from '../scripts/run-integration-tests.mjs';

function sinks() {
  const stdout=new PassThrough(),stderr=new PassThrough(); let out='',err='';
  stdout.on('data',b=>out+=b);stderr.on('data',b=>err+=b);
  return {stdout,stderr,get out(){return out;},get err(){return err;}};
}
const code = source => ['--input-type=module','--eval',source];
test('stdout and stderr arrive while the child is still waiting, with chunked zero-skips summary',async t=>{
  const root=fs.mkdtempSync(path.join(process.cwd(),'.cache/integration-stream-'));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  const release=path.join(root,'release'),s=sinks();let observed=false;
  s.stdout.once('data',()=>{
    observed=true;assert.ok(!s.out.includes('# skipped 0'));
    fs.writeFileSync(release,'continue',{flag:'wx'});
  });
  const pending=streamTestProcess(code(`
    import fs from 'node:fs';
    console.log('first-test-completed');console.error('active-next-phase');
    const timer=setInterval(()=>{if(fs.existsSync(${JSON.stringify(release)})){
      clearInterval(timer);process.stdout.write('# skip');
      setTimeout(()=>{console.log('ped 0');process.exit(0);},20);
    }},20);
    setTimeout(()=>process.exit(9),5000).unref();
  `),s);
  assert.equal(await pending,0);assert.ok(observed);assert.match(s.err,/active-next-phase/);
});
test('the real Node TAP runner reports a finished test while the next test is still active',async t=>{
  const root=fs.mkdtempSync(path.join(process.cwd(),'.cache/integration-progress-'));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  const done=path.join(root,'second.done'),file=path.join(root,'progress.test.mjs');
  fs.writeFileSync(file,`import test from 'node:test';import fs from 'node:fs';
    test('first actual test',()=>{});
    test('second actual test',async()=>{await new Promise(r=>setTimeout(r,500));fs.writeFileSync(${JSON.stringify(done)},'done');});`,{flag:'wx'});
  const s=sinks();let live=false;
  s.stdout.on('data',()=>{if(s.out.includes('ok 1 - first actual test')&&!fs.existsSync(done))live=true;});
  const env={...process.env};delete env.NODE_TEST_CONTEXT;
  assert.equal(await streamTestProcess(['--test','--test-reporter=tap',file],{...s,env}),0);
  assert.ok(live,'first TAP result must arrive before the real second test finishes');
});
test('failed children retain their status and diagnostics; successful missing or skipped summaries reject',async()=>{
  const s=sinks();assert.equal(await streamTestProcess(code("console.error('specific failure');process.exit(7)"),s),7);
  assert.match(s.err,/specific failure/);
  for(const source of ["console.log('no footer')","console.log('# skipped 2')"])
    await assert.rejects(streamTestProcess(code(source),sinks()),/zero skipped/);
});
test('large prior output cannot bury the final summary or require retention of the full transcript',async()=>{
  assert.equal(await streamTestProcess(code("process.stdout.write('x'.repeat(100000)+'\\n# skipped 0\\n')"),sinks()),0);
});
test('output overflow terminates the actual child and refuses its apparent success',async()=>{
  await assert.rejects(streamTestProcess(code("console.log('x'.repeat(10000));setInterval(()=>{},1000)"),
    {...sinks(),maxBytes:1000}),/output exceeds/);
});
test('cancellation terminates the actual test process group, including a descendant', {skip:process.platform==='win32'}, async t=>{
  const root=fs.mkdtempSync(path.join(process.cwd(),'.cache/integration-cancel-'));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  const pidFile=path.join(root,'descendant.pid');
  const runner=new URL('../scripts/run-integration-tests.mjs',import.meta.url).href;
  const childSource=`import {spawn} from 'node:child_process';import fs from 'node:fs';
    const c=spawn(process.execPath,['-e','setInterval(()=>{},1000)'],{stdio:'ignore'});
    fs.writeFileSync(${JSON.stringify(pidFile)},String(c.pid),{flag:'wx'});
    console.log('ready');setInterval(()=>{},1000);`;
  const parent=spawn(process.execPath,code(`import {streamTestProcess} from ${JSON.stringify(runner)};
    process.exitCode=await streamTestProcess(${JSON.stringify(code(childSource))});`),{stdio:['ignore','pipe','pipe']});
  let error='';parent.stderr.on('data',b=>error+=b);
  const done=new Promise(resolve=>parent.once('close',(status,signal)=>resolve({status,signal})));
  t.after(()=>{try{parent.kill('SIGKILL');}catch{}});
  await new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>reject(Error('actual child never started: '+error)),5000);
    parent.stdout.once('data',()=>{clearTimeout(timer);resolve();});
  });
  const descendant=Number(fs.readFileSync(pidFile,'utf8'));
  parent.kill('SIGTERM');assert.equal((await done).status,143,error);
  let absent=false;
  for(let i=0;i<40;i++){
    try{process.kill(descendant,0);}catch(e){if(e.code==='ESRCH'){absent=true;break;}throw e;}
    await new Promise(r=>setTimeout(r,50));
  }
  assert.ok(absent,'cancelled descendant must be reaped');
});

test('exited failures clean detached-stdio descendants and successful orphans reject', {skip:process.platform==='win32'}, async t=>{
  const root=fs.mkdtempSync(path.join(process.cwd(),'.cache/integration-orphan-'));
  t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
  for (const status of [7,0]) {
    const pidFile=path.join(root,`${status}.pid`);
    const source=`import {spawn} from 'node:child_process';import fs from 'node:fs';
      const c=spawn(process.execPath,['-e',"process.on('SIGTERM',()=>{});setInterval(()=>{},1000)"],{stdio:'ignore'});
      c.unref();fs.writeFileSync(${JSON.stringify(pidFile)},String(c.pid),{flag:'wx'});
      setTimeout(()=>{console.log('# skipped 0');process.exit(${status});},150);`;
    const pending=streamTestProcess(code(source),sinks());
    if(status===0) await assert.rejects(pending,/unfinished descendants/);
    else assert.equal(await pending,7);
    const descendant=Number(fs.readFileSync(pidFile,'utf8'));
    t.after(()=>{try{process.kill(descendant,'SIGKILL');}catch{}});
    let absent=false;
    for(let i=0;i<40;i++){
      try{process.kill(descendant,0);}catch(e){if(e.code==='ESRCH'){absent=true;break;}throw e;}
      await new Promise(r=>setTimeout(r,50));
    }
    assert.ok(absent,'terminal child must leave no running descendant');
  }
});
