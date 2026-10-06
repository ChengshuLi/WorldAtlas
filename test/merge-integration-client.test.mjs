import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
function run(scenario) {
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'worldatlas-queue-client-'));
 const file=path.join(directory,'state.json');fs.writeFileSync(file,JSON.stringify({scenario,routes:[],polls:0}));
 const clock=path.join(directory,'clock.mjs');
 fs.writeFileSync(clock,`const native=Date.now;let now=0;Date.now=()=>native()+now;globalThis.setTimeout=(f)=>{now+=${scenario==='timeout'?3900001:1};f();};`);
 const mock=`#!${process.execPath}\n`+String.raw`
import fs from 'node:fs';
const file=process.env.WORLDATLAS_FAKE_GH_STATE,s=JSON.parse(fs.readFileSync(file)),args=process.argv.slice(2),route=args[1]??'';
s.routes.push(args);let result={};
if(args[0]==='workflow') s.request=args.find(x=>x.startsWith('request_id=')).split('=')[1];
else if(route.includes('/pulls/2')) result={state:'open',head:{sha:'a'.repeat(40)},merged:!!s.finished,merge_commit_sha:s.finished?'f'.repeat(40):null};
else if(route.includes('/issues/2/comments')) {
 s.polls++;
 if(s.polls===1||s.scenario==='timeout') result=[];
 else {const failed=s.scenario==='failed';s.finished=!failed;const value={request_id:s.request,pr_number:2,accepted:!failed,status:failed?'not-merged':'merged',retryable:false,merge_commit:failed?undefined:'f'.repeat(40)};
 result=[{id:1,user:{login:'github-actions[bot]'},body:'**Merge result:** accepted\n\n<!-- worldatlas-merge-result:v1\n'+JSON.stringify(value)+'\n-->'}];}
} else if(route.includes('/actions/workflows/')) {
 if(s.scenario==='slide'&&!route.includes('page=2'))result={workflow_runs:Array.from({length:100},()=>({display_title:'other'}))};
 else result={workflow_runs:[{id:101,display_title:'queue #2 '+s.request,status:'completed',conclusion:s.scenario==='cancel'?'cancelled':'success',html_url:'https://example.test/run'}]};
} else if(route.includes('/actions/runs/')) result={id:101,status:'completed',conclusion:'success'};
else throw Error('Unexpected route '+route);
fs.writeFileSync(file,JSON.stringify(s));console.log(JSON.stringify(result));
`;
 fs.writeFileSync(path.join(directory,'gh'),mock,{mode:0o700});
 try {
  const result=spawnSync(process.execPath,['--import',clock,'scripts/queue-pr-merge.mjs','--pr','2','--head','a'.repeat(40),'--request-id','stable-client-request'],{cwd:path.resolve(import.meta.dirname,'..'),encoding:'utf8',timeout:30000,env:{PATH:directory+path.delimiter+process.env.PATH,WORLDATLAS_FAKE_GH_STATE:file}});
  return {result,state:JSON.parse(fs.readFileSync(file))};
 } finally {fs.rmSync(directory,{recursive:true,force:true});}
}
test('client discovers registration later pages and confirms actual merge against durable result',()=>{
 const {result,state}=run('slide');assert.equal(result.status,0,result.stderr);
 assert.ok(state.routes.some(a=>a[1]?.includes('page=2')));assert.equal(state.finished,true);
 assert.equal(state.routes.filter(a=>a[0]==='workflow').length,1);
});
test('registration cancellation retains stable identity for safe explicit resume',()=>{
 const {result,state}=run('cancel');assert.notEqual(result.status,0);assert.match(result.stderr,/resume the same request stable-client-request/);
 assert.equal(state.routes.filter(a=>a[0]==='workflow').length,1);
});
test('failed tests remain visible and never trigger another submission',()=>{
 const {result,state}=run('failed');assert.equal(result.status,2,result.stderr);assert.equal(state.finished,false);
 assert.equal(state.routes.filter(a=>a[0]==='workflow').length,1);
});
test('observation timeout leaves durable/live execution untouched',()=>{
 const {result,state}=run('timeout');assert.notEqual(result.status,0);assert.match(result.stderr,/durable request stable-client-request remains queued\/live/);
 assert.equal(state.routes.filter(a=>a[0]==='workflow').length,1);
 assert.ok(!state.routes.some(a=>a.includes('cancel')));
});
