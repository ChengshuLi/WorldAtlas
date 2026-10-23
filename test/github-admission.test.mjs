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


function truncatedTrees() {
  const root='1'.repeat(40), shared='2'.repeat(40), nested='3'.repeat(40), blob='4'.repeat(40);
  const route=sha=>'/repos/a/b/git/trees/'+sha;
  const directory=(path,sha)=>({path,sha,type:'tree',mode:'040000'});
  const file=(path,mode='100644')=>({path,sha:blob,type:'blob',mode,size:7});
  const payloads=new Map([
    [route(root)+'?recursive=1',{sha:root,truncated:true,tree:[file('../discarded-partial-row')]}],
    [route(root),{sha:root,truncated:false,tree:[directory('one',shared),directory('two',shared),directory('nested',nested),file('root')]}],
    [route(shared)+'?recursive=1',{sha:shared,truncated:false,tree:[file('ordinary'),file('executable','100755'),file('symlink','120000')]}],
    [route(nested)+'?recursive=1',{sha:nested,truncated:true,tree:[file('discarded')]}],
    [route(nested),{sha:nested,truncated:false,tree:[directory('again',shared),{path:'gitlink',sha:blob,type:'commit',mode:'160000'}]}]
  ]);
  const calls=[];
  const fetchImpl=async(url,init)=>{
    const name=new URL(url).pathname+new URL(url).search;calls.push({name,init});
    assert(payloads.has(name),'Unexpected tree or non-metadata request: '+name);
    return Response.json(payloads.get(name));
  };
  return {root,shared,nested,blob,route,payloads,calls,fetchImpl};
}

test('truncated immutable trees expand complete children, preserve every entry and reuse repeated subtree identities',async()=>{
  const f=truncatedTrees(),accounting=requestAccounting('tree');
  const result=await githubAPI(undefined,{publicReadOnly:true,fetchImpl:f.fetchImpl,onRequest:accounting.observe})(f.route(f.root)+'?recursive=1');
  assert.equal(result.sha,f.root);assert.equal(result.truncated,false);
  assert.deepEqual(result.tree.map(row=>row.path),['nested','nested/again','nested/again/executable','nested/again/ordinary','nested/again/symlink','nested/gitlink',
    'one','one/executable','one/ordinary','one/symlink','root','two','two/executable','two/ordinary','two/symlink']);
  assert.deepEqual(result.tree.find(row=>row.path==='one/executable'),{path:'one/executable',sha:f.blob,type:'blob',mode:'100755',size:7});
  assert.equal(result.tree.find(row=>row.path==='nested/gitlink').mode,'160000');
  assert.equal(f.calls.length,5);assert.equal(accounting.receipt().actual_http_attempts,5);
  assert(f.calls.every(row=>row.init.method==='GET'&&!row.init.headers.Authorization));
  assert(!f.calls.some(row=>row.name.includes('/blobs/')));
});

test('tree decomposition refuses wrong identity, incomplete children, unsafe entries, missing parents and cycles',async()=>{
  const cases=[
    ['root identity',f=>f.payloads.get(f.route(f.root)+'?recursive=1').sha=f.blob],
    ['direct truncation',f=>f.payloads.get(f.route(f.root)).truncated=true],
    ['direct identity',f=>f.payloads.get(f.route(f.root)).sha=f.blob],
    ['direct nested path',f=>f.payloads.get(f.route(f.root)).tree[0].path='a/b'],
    ['direct duplicate',f=>f.payloads.get(f.route(f.root)).tree.push({...f.payloads.get(f.route(f.root)).tree[0]})],
    ['unsafe path',f=>f.payloads.get(f.route(f.shared)+'?recursive=1').tree[0].path='../outside'],
    ['type/mode',f=>f.payloads.get(f.route(f.shared)+'?recursive=1').tree[0].mode='040000'],
    ['size',f=>f.payloads.get(f.route(f.shared)+'?recursive=1').tree[0].size=-1],
    ['missing parent',f=>f.payloads.get(f.route(f.shared)+'?recursive=1').tree[0].path='absent/leaf'],
    ['child identity',f=>f.payloads.get(f.route(f.shared)+'?recursive=1').sha=f.blob],
    ['cycle',f=>f.payloads.get(f.route(f.root)).tree[0].sha=f.root],
    ['recursive ancestor cycle',f=>f.payloads.get(f.route(f.shared)+'?recursive=1').tree.push({path:'cycle',sha:f.root,type:'tree',mode:'040000'})]
  ];
  for(const [label,mutate]of cases){
    const f=truncatedTrees();mutate(f);
    await assert.rejects(githubAPI('fixture',{fetchImpl:f.fetchImpl})(f.route(f.root)+'?recursive=1'),/immutable tree/i,label);
  }
});

test('truncated-tree completion does not retry the root when a child refuses or exhausts its bounded retries',async()=>{
  for(const status of [403,404,503]){
    const f=truncatedTrees();let child=0;
    const api=githubAPI('fixture',{readWaitMs:60000,now:()=>0,sleep:async()=>{},fetchImpl:async(url,init)=>{
      if(url.endsWith(f.route(f.shared)+'?recursive=1')){child++;return Response.json({message:'Unavailable'},{status});}
      return f.fetchImpl(url,init);
    }});
    await assert.rejects(api(f.route(f.root)+'?recursive=1'),error=>error.github?.http_status===status);
    assert.equal(child,status===503?3:1);assert.deepEqual(f.calls.map(row=>row.name),[f.route(f.root)+'?recursive=1',f.route(f.root)]);
  }
  const f=truncatedTrees();
  // Finish the second request within its deadline, then refuse the child before fetch.
  let checks=0;const bounded=githubAPI('fixture',{deadlineRemaining:()=>++checks>4?0:60000,fetchImpl:f.fetchImpl});
  await assert.rejects(bounded(f.route(f.root)+'?recursive=1'),/deadline/);
  assert.equal(f.calls.length,2);
});

test('raw partial ETag snapshots never become synthetic complete provider responses',async()=>{
  const f=truncatedTrees(),seen=new Map();
  const api=githubAPI('fixture',{fetchImpl:async(url,init)=>{
    const name=new URL(url).pathname+new URL(url).search,etag='"'+name+'"';
    if(seen.has(name)){assert.equal(init.headers['If-None-Match'],etag);seen.set(name,seen.get(name)+1);return new Response(null,{status:304,headers:{etag}});}
    seen.set(name,1);assert(f.payloads.has(name));return Response.json(f.payloads.get(name),{headers:{etag}});
  }});
  const first=await api(f.route(f.root)+'?recursive=1');
  assert.deepEqual(await api(f.route(f.root)+'?recursive=1'),first);
  assert.equal(seen.size,5);assert([...seen.values()].every(count=>count===2));
});

test('tree completion cannot broaden bounded reads, malformed responses, mutable refs or mutation routes',async()=>{
  const f=truncatedTrees();
  const api=githubAPI('fixture',{fetchImpl:f.fetchImpl});
  const raw=await api(f.route(f.root)+'?recursive=1','GET',undefined,{maxResponseBytes:4096});
  assert.equal(raw.truncated,true);assert.equal(f.calls.length,1);
  for(const [route,method,body,payload]of [
    [f.route(f.root)+'?recursive=1','GET',undefined,{truncated:'true',tree:[]}],
    [f.route(f.root)+'?recursive=1','GET',undefined,{truncated:true}],
    ['/repos/a/b/git/trees/main?recursive=1','GET',undefined,{truncated:true,tree:[]}],
    [f.route(f.root)+'?recursive=true','GET',undefined,{truncated:true,tree:[]}],
    [f.route(f.root)+'?recursive=1','POST',{}, {truncated:true,tree:[]}]
  ]){
    let calls=0;const client=githubAPI('fixture',{fetchImpl:async()=>{calls++;return Response.json(payload);}});
    if(payload.truncated===true&&route===f.route(f.root)+'?recursive=1'&&method==='GET')
      await assert.rejects(client(route,method,body),/tree response identity/);
    else assert.deepEqual(await client(route,method,body),payload);
    assert.equal(calls,1);
  }
});
