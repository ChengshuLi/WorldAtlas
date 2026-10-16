import test from 'node:test';
import assert from 'node:assert/strict';
import {githubAPI} from '../scripts/issue-claim-contract.mjs';
import {requestAccounting} from '../scripts/github-quota.mjs';

// Exercise the production Actions-token default, without a test-only floor override.
function actionsAPI(options) {
  const names=['GITHUB_ACTIONS','GH_TOKEN','GITHUB_TOKEN'];
  const previous=names.map(name=>process.env[name]);
  try {
    process.env.GITHUB_ACTIONS='true';process.env.GH_TOKEN='private';delete process.env.GITHUB_TOKEN;
    return githubAPI('private',options);
  } finally {
    names.forEach((name,index)=>previous[index]===undefined?delete process.env[name]:process.env[name]=previous[index]);
  }
}

const headers=remaining=>({'x-ratelimit-limit':'1000','x-ratelimit-remaining':String(remaining),
  'x-ratelimit-reset':'3600','x-ratelimit-resource':'core'});

test('successful reads and writes need no quota headers or preliminary capacity requests', async () => {
  const calls=[],accounting=requestAccounting('actual-success');
  const api=actionsAPI({onRequest:accounting.observe,fetchImpl:async(url,options)=>{
    calls.push({url,method:options.method});
    return options.method==='DELETE'?new Response(null,{status:204}):Response.json({ok:true});
  }});
  for(const method of ['GET','POST','PATCH','DELETE'])
    assert.deepEqual(await api('/repos/a/b/issues/1',method),method==='DELETE'?null:{ok:true});
  assert.deepEqual(calls.map(row=>row.method),['GET','POST','PATCH','DELETE']);
  assert(calls.every(row=>row.url==='https://api.github.com/repos/a/b/issues/1'));
  assert.equal(accounting.receipt().actual_http_attempts,4);
  assert.equal(accounting.receipt().observed_repository_core,undefined);
});

test('observed low or stale counters cannot reject a successful operation', async () => {
  const seen=[];let calls=0;
  const api=actionsAPI({onRequest:row=>seen.push(row),fetchImpl:async()=>
    Response.json({ok:true},{headers:headers([0,16,999,1][calls++])})});
  for(let i=0;i<4;i++)assert.deepEqual(await api('/repos/a/b/issues/1'),{ok:true});
  assert.equal(calls,4);assert.deepEqual(seen.map(row=>row.capacity.remaining),[0,16,999,1]);
});

test('independent requests start without waiting for the first response', async () => {
  let release,calls=0;const held=new Promise(resolve=>{release=resolve;});
  const api=actionsAPI({fetchImpl:async()=>{
    const number=++calls;if(number===1)await held;return Response.json({number});
  }});
  const first=api('/repos/a/b/issues/1'),second=api('/repos/a/b/issues/2');
  try {assert.equal(calls,2);assert.deepEqual(await second,{number:2});}
  finally {release();await Promise.allSettled([first,second]);}
  assert.deepEqual(await first,{number:1});
});

test('a first ambiguous mutation is attempted once without a speculative read', async () => {
  const methods=[];
  const api=actionsAPI({readWaitMs:60000,sleep:async()=>assert.fail('uncertain write must not retry'),
    fetchImpl:async(url,options)=>{methods.push(options.method);throw Error('lost response');}});
  await assert.rejects(api('/repos/a/b/issues/1/comments','POST',{body:'progress'}),/lost response/);
  assert.deepEqual(methods,['POST']);
});

test('artifact and original-package log redirects keep fixed-host credentials and secret-free accounting without quota headers', async () => {
  const accounting=requestAccounting('artifact'),calls=[];
  const api=actionsAPI({onRequest:accounting.observe,fetchImpl:async(url,options)=>{
    calls.push({url,options});
    return new Response(null,{status:302,headers:{location:'https://results.blob.core.windows.net/a?signature=private-secret'}});
  }});
  for(const [method,route,invalid] of [
    ['artifactRedirect','/repos/a/b/actions/artifacts/12/zip',['/repos/a/b/actions/artifacts/0/zip','/repos/a/b/actions/artifacts/12/zip?redirect=1']],
    ['jobLogRedirect','/repos/a/b/actions/jobs/12/logs',['/repos/a/b/actions/jobs/0/logs','/repos/a/b/actions/jobs/12/logs?redirect=1']]
  ]) {
    assert.equal((await api[method](route)).status,302);
    assert.equal(calls.at(-1).url,'https://api.github.com'+route);
    assert.equal(calls.at(-1).options.redirect,'manual');
    assert.equal(calls.at(-1).options.headers.Authorization,'Bearer private');
    for(const bad of ['https://attacker.example/a',...invalid])
      assert.throws(()=>api[method](bad),/Invalid .* redirect route/);
  }
  assert.equal(calls.length,2);assert.equal(accounting.receipt().actual_http_attempts,2);
  assert(!JSON.stringify(accounting.receipt()).includes('private-secret'));
});

test('redirect and recovery dispatch preserve real provider refusals without automatic retry', async () => {
  for(const status of [403,429,503]) {
    const calls=[];const api=actionsAPI({readWaitMs:60000,sleep:async()=>assert.fail('must not wait'),
      fetchImpl:async(url,options)=>{calls.push(options.method);return Response.json({message:'Unavailable'},
        {status,headers:{...headers(0),'retry-after':'1'}});}});
    await assert.rejects(api.artifactRedirect('/repos/a/b/actions/artifacts/12/zip'),e=>e.github?.http_status===status);
    await assert.rejects(api.jobLogRedirect('/repos/a/b/actions/jobs/12/logs'),e=>e.github?.http_status===status);
    await assert.rejects(api.recovery('/repos/a/b/git/ref/heads/worldatlas-integration/pr-1-synthetic-unique-request'),
      e=>e.github?.http_status===status);
    assert.deepEqual(calls,['GET','GET','GET']);
  }
});

test('owned cleanup and durable notification remain restricted to their actual routes and SHA', async () => {
  const calls=[],ref='worldatlas-integration/pr-1-synthetic-unique-request';
  const api=actionsAPI({fetchImpl:async(url,options)=>{
    calls.push({url,method:options.method});
    return options.method==='DELETE'?new Response(null,{status:204}):Response.json({object:{sha:'a'.repeat(40)}});
  }});
  const {cleanupCandidate}=await import('../scripts/merge-integration.mjs');
  const options={api,repo:'a/b',number:1,integrationRequestId:'synthetic-unique-request'};
  assert.equal((await cleanupCandidate(options,ref,'a'.repeat(40))).status,'deleted');
  await api.recovery('/repos/a/b/issues/1/comments','POST',{body:'**Merge result:** not accepted\n<!-- worldatlas-merge-result:v1\n{}\n-->'});
  assert.deepEqual(calls.map(row=>row.method),['GET','DELETE','POST']);
  for(const [route,method,body] of [
    ['/repos/a/b/issues/1','GET'],['/repos/a/b/git/refs/heads/main','DELETE'],
    ['/repos/a/b/issues/1/comments','POST',{body:'arbitrary new work'}]
  ])assert.throws(()=>api.recovery(route,method,body),/outside bounded merge recovery/);
  assert.equal(calls.length,3);
});

test('recovery keeps ref ownership checks and never repeats an ambiguous delete', async () => {
  const methods=[];
  const api=actionsAPI({fetchImpl:async(url,options)=>{
    methods.push(options.method);if(options.method==='DELETE')throw Error('lost deletion response');
    return Response.json({object:{sha:'b'.repeat(40)}});
  }});
  const {cleanupCandidate}=await import('../scripts/merge-integration.mjs');
  const options={api,repo:'a/b',number:1,integrationRequestId:'synthetic-unique-request'};
  await assert.rejects(cleanupCandidate(options,'main','a'.repeat(40)),/unowned/);
  await assert.rejects(cleanupCandidate(options,'worldatlas-integration/pr-1-synthetic-unique-request','a'.repeat(40)),/reference changed/);
  assert(!methods.includes('DELETE'));
  await assert.rejects(api.recovery('/repos/a/b/git/refs/heads/worldatlas-integration/pr-1-synthetic-unique-request','DELETE'),/lost deletion response/);
  assert.deepEqual(methods,['GET','DELETE']);
});
