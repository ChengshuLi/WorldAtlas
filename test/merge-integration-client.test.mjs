import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

function run(scenario) {
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'worldatlas-queue-client-'));
  const stateFile=path.join(directory,'state.json');
  fs.writeFileSync(stateFile,JSON.stringify({scenario,attempt:0,routes:[],delays:[]}));
  // Preload only this spawned test CLI; keep production polling/backoff unchanged.
  const clock=path.join(directory,'clock.mjs');
  fs.writeFileSync(clock,String.raw`
import fs from 'node:fs';
const realSetTimeout=globalThis.setTimeout;
globalThis.setTimeout=(callback,delay,...args)=>{
 const file=process.env.WORLDATLAS_FAKE_GH_STATE;
 const state=JSON.parse(fs.readFileSync(file));
 state.delays.push(delay);fs.writeFileSync(file,JSON.stringify(state));
 return realSetTimeout(callback,0,...args);
};
`);
  const mock=`#!${process.execPath}\n`+String.raw`
import fs from 'node:fs';
const file=process.env.WORLDATLAS_FAKE_GH_STATE, s=JSON.parse(fs.readFileSync(file));
const args=process.argv.slice(2), route=args[1]??'';
s.routes.push(args);let result={};
if(args[0]==='workflow') {
 s.attempt++;s.request=args.find(x=>x.startsWith('request_id=')).split('=')[1];
} else if(route.includes('/pulls/2')) {
 result={head:{sha:'a'.repeat(40)},merged:!!s.finished,merge_commit_sha:s.finished?'f'.repeat(40):null};
} else if(route.includes('/actions/workflows/')) {
 const title='merge #2 '+s.request;
 if(s.scenario==='slide'&&!route.includes('page=2'))result={workflow_runs:Array.from({length:100},(_,i)=>({id:i,display_title:'unrelated'}))};
 else result={workflow_runs:[{id:100+s.attempt,display_title:title,status:s.scenario==='slide'?'in_progress':'completed',
 conclusion:s.scenario==='cancel'&&s.attempt===1?'cancelled':'success',html_url:'https://example.test/run'}]};
} else if(route.includes('/actions/runs/')) {
 result={id:100+s.attempt,status:'completed',conclusion:'success',html_url:'https://example.test/run'};
} else if(route.includes('/issues/2/comments')) {
 const denied=(s.scenario==='advance'&&s.attempt===1)||s.scenario==='failed';
 const value={request_id:s.request,pr_number:2,accepted:!denied,status:denied?'not-merged':'merged',
 retryable:s.scenario==='advance'&&s.attempt===1,reason:denied?'integration stopped':undefined,merge_commit:denied?undefined:'f'.repeat(40)};
 if(!denied)s.finished=true;
 result=[{id:s.attempt,user:{login:'github-actions[bot]'},body:'**Merge result:** accepted\n\n<!-- worldatlas-merge-result:v1\n'+JSON.stringify(value)+'\n-->'}];
} else throw Error('Unexpected gh request '+JSON.stringify(args));
fs.writeFileSync(file,JSON.stringify(s));console.log(JSON.stringify(result));
`;
  const executable=path.join(directory,'gh');fs.writeFileSync(executable,mock,{mode:0o700});
  try {
    const result=spawnSync(process.execPath,['--import',clock,'scripts/queue-pr-merge.mjs','--pr','2','--head','a'.repeat(40)],
      {cwd:path.resolve(import.meta.dirname,'..'),encoding:'utf8',timeout:30000,
       env:{PATH:directory+path.delimiter+process.env.PATH,WORLDATLAS_FAKE_GH_STATE:stateFile}});
    return {result,state:JSON.parse(fs.readFileSync(stateFile))};
  } finally {fs.rmSync(directory,{recursive:true,force:true});}
}

test('client discovers later pages and polls latched ID when the run leaves recent results',()=>{
 const {result,state}=run('slide');assert.equal(result.status,0,result.stderr);
 assert.ok(state.routes.some(args=>args[1]?.includes('page=2')));
 assert.ok(state.routes.some(args=>args[1]?.includes('/actions/runs/101')));
 assert.equal(state.attempt,1);assert.equal(state.finished,true);
 assert.deepEqual(state.delays,[5000]);
});
test('cancelled pending request is retried without changing authored head',()=>{
 const {result,state}=run('cancel');assert.equal(result.status,0,result.stderr);assert.equal(state.attempt,2);
 const requests=state.routes.filter(args=>args[0]==='workflow');assert.equal(requests.length,2);
 assert.ok(requests.every(args=>args.includes('expected_head='+'a'.repeat(40))));
 assert.equal(state.delays.length,1);
 assert.ok(state.delays[0]>=2000&&state.delays[0]<5000);
});
test('main advance retries unchanged head but failed integration ends without retry',()=>{
 const advanced=run('advance');assert.equal(advanced.result.status,0,advanced.result.stderr);assert.equal(advanced.state.attempt,2);
 assert.equal(advanced.state.delays.length,1);
 assert.ok(advanced.state.delays[0]>=2000&&advanced.state.delays[0]<5000);
 const failed=run('failed');assert.equal(failed.result.status,2);assert.equal(failed.state.attempt,1);assert.equal(failed.state.finished,undefined);
 assert.deepEqual(failed.state.delays,[]);
});
