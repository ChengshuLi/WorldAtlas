import test from 'node:test';
import assert from 'node:assert/strict';
import {githubAPI} from '../scripts/issue-claim-contract.mjs';
import {requestAccounting} from '../scripts/github-quota.mjs';

async function mocked(fetchImpl, run) {
  const original=globalThis.fetch; globalThis.fetch=fetchImpl;
  try { await run(); } finally { globalThis.fetch=original; }
}
const fresh=(value,etag='"one"',extra={})=>new Response(JSON.stringify(value),{headers:{etag,...extra}});
const unchanged=etag=>new Response(null,{status:304,headers:etag?{etag}:{}});

test('every unchanged authority reuse makes an authenticated network recheck and returns independent data',async()=>{
  let calls=0;const accounting=requestAccounting('snapshots');
  await mocked(async(url,options)=>{
    calls++;assert.equal(options.headers.Authorization,'Bearer private');
    if(calls===1){assert.equal(options.headers['If-None-Match'],undefined);return fresh({body:'contract',labels:['ready']});}
    assert.equal(options.headers['If-None-Match'],'"one"');return unchanged('"one"');
  },async()=>{
    const api=githubAPI('private',{onRequest:accounting.observe});
    const first=await api('/repos/a/b/issues/1');first.body='poison';first.labels.push('closed');
    const second=await api('/repos/a/b/issues/1');assert.deepEqual(second,{body:'contract',labels:['ready']});
    second.labels.pop();assert.deepEqual(await api('/repos/a/b/issues/1'),{body:'contract',labels:['ready']});
  });
  assert.equal(calls,3);assert.equal(accounting.receipt().counts['GET:issues:304'],2);
});
test('changed head, contract and revocation are consumed rather than hidden by the snapshot',async()=>{
  const rows=[fresh({head:'old',claimed:true}),fresh({head:'new',claimed:false},'"two"'),unchanged('"two"')];
  await mocked(async()=>rows.shift(),async()=>{
    const api=githubAPI('private');assert.equal((await api('/repos/a/b/pulls/1')).head,'old');
    assert.deepEqual(await api('/repos/a/b/pulls/1'),{head:'new',claimed:false});
    assert.deepEqual(await api('/repos/a/b/pulls/1'),{head:'new',claimed:false});
  });
});
test('authorization loss and an ambiguous write do not reuse a successful read or retry mutation',async()=>{
  let calls=0;
  await mocked(async(url,options)=>{
    calls++;if(calls===1)return fresh({approved:true});
    if(options.method==='PUT')throw Error('lost write response');
    return new Response('{}',{status:403});
  },async()=>{
    const api=githubAPI('private');await api('/repos/a/b/pulls/1');
    await assert.rejects(api('/repos/a/b/pulls/1'),/HTTP 403/);
    await assert.rejects(api('/repos/a/b/pulls/1','PUT',{state:'closed'}),/lost write/);
    assert.equal(calls,3);
  });
});
test('route, page, client and credential boundaries never borrow another response',async()=>{
  await mocked(async(url,options)=>{
    assert.equal(options.headers['If-None-Match'],undefined);return fresh({route:url});
  },async()=>{
    const api=githubAPI('one');await api('/repos/a/b/issues/1');await api('/repos/a/b/issues/2');
    await api('/repos/a/b/issues/1/comments?page=1');await api('/repos/a/b/issues/1/comments?page=2');
    await githubAPI('two')('/repos/a/b/issues/1');await githubAPI('one')('/repos/a/b/issues/1');
  });
});
test('missing or mismatched conditional responses cannot produce authority',async()=>{
  for(const badTag of [null,'"different"'])await mocked(async(url,options)=>options.headers['If-None-Match']?unchanged(badTag):fresh({ok:true}),async()=>{
    const api=githubAPI('private');
    await api('/repos/a/b/issues/1');
    if(badTag!==null)await assert.rejects(api('/repos/a/b/issues/1'),/Unbound/);
    else assert.deepEqual(await api('/repos/a/b/issues/1'),{ok:true}); // ETag on 304 is optional.
  });
  await mocked(async()=>unchanged('"one"'),async()=>{
    await assert.rejects(githubAPI('private')('/repos/a/b/issues/1'),/Unrequested/);
  });
});
test('entry and byte bounds retain no oversized snapshot and overflow remains freshly read',async()=>{
  for(const settings of [{snapshotBytes:1},{snapshotEntries:0}])await mocked(async(url,options)=>{
    assert.equal(options.headers['If-None-Match'],undefined);return fresh({large:'abcdef'});
  },async()=>{
    const api=githubAPI('private',settings);await api('/repos/a/b/issues/1');await api('/repos/a/b/issues/1');
  });
});
test('capacity probes, generic quota, blobs and writes never use conditional authority',async()=>{
  await mocked(async(url,options)=>{
    assert.equal(options.headers['If-None-Match'],undefined);
    return fresh({ok:true},'"one"',{'x-ratelimit-limit':'1000','x-ratelimit-remaining':'42','x-ratelimit-reset':'100','x-ratelimit-resource':'core'});
  },async()=>{
    const api=githubAPI('private');
    await api.readRepositoryCapacity('a/b');await api.readRepositoryCapacity('a/b');
    for(const route of ['/rate_limit','/repos/a/b/git/blobs/'+'a'.repeat(40)]){await api(route);await api(route);}
    await api('/repos/a/b/issues/1');await api('/repos/a/b/issues/1','PATCH',{body:'changed'});
  });
});
test('missing and malformed ETags erase the old binding',async()=>{
  for(const tag of [null,'unquoted','"'+ 'a'.repeat(300)+'"']){
    let calls=0;
    await mocked(async(url,options)=>{
      calls++;
      if(calls===1)return fresh({n:1});
      if(calls===2){assert.equal(options.headers['If-None-Match'],'"one"');return new Response('{"n":2}',{headers:tag?{etag:tag}:{}});}
      assert.equal(options.headers['If-None-Match'],undefined);return fresh({n:3});
    },async()=>{
      const api=githubAPI('private');await api('/repos/a/b/issues/1');assert.equal((await api('/repos/a/b/issues/1')).n,2);
      assert.equal((await api('/repos/a/b/issues/1')).n,3);
    });
  }
});

// Native Node fetch negotiates encoded content: GitHub can return W/ on 200
// and the same opaque tag without W/ on 304. Exercise the shared API boundary.
test('conditional GET accepts weak-equivalent validators in both directions without extra requests', async () => {
  for (const [initial, returned] of [['W/"same"', '"same"'], ['"same"', 'W/"same"']]) {
    let calls = 0;
    await mocked(async (url, options) => {
      calls++;
      assert.equal(options.headers.Authorization, 'Bearer private');
      if (calls === 1) return fresh({head: 'exact', labels: ['ready']}, initial);
      assert.equal(options.headers['If-None-Match'], initial);
      return unchanged(returned);
    }, async () => {
      const api = githubAPI('private');
      const first = await api('/repos/a/b/git/commits/' + 'a'.repeat(40));
      first.labels.push('poison');
      const second = await api('/repos/a/b/git/commits/' + 'a'.repeat(40));
      assert.deepEqual(second, {head: 'exact', labels: ['ready']});
      second.head = 'poison';
      assert.deepEqual(await api('/repos/a/b/git/commits/' + 'a'.repeat(40)), {head: 'exact', labels: ['ready']});
    });
    assert.equal(calls, 3);
  }
});

test('weak comparison still rejects different or malformed conditional validators', async () => {
  for (const returned of ['W/"different"', '"different"', 'same', 'w/"same"', '"same", "different"']) {
    let calls = 0;
    await mocked(async (url, options) => {
      calls++;
      if (calls === 1) return fresh({approved: true}, 'W/"same"');
      assert.equal(options.headers['If-None-Match'], 'W/"same"');
      return unchanged(returned);
    }, async () => {
      const api = githubAPI('private');
      await api('/repos/a/b/issues/1');
      await assert.rejects(api('/repos/a/b/issues/1'), /Unbound/);
    });
    assert.equal(calls, 2);
  }
});
