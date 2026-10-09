// Explicit read-only reproduction. No credentials or response bodies are printed.
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {githubAPI} from '../../../scripts/issue-claim-contract.mjs';
const observations=[];
const token=execFileSync('gh',['auth','token'],{encoding:'utf8',timeout:20000,maxBuffer:16384}).trim();
const deadline=Date.now()+60000;
const api=githubAPI(token,{deadlineRemaining:()=>deadline-Date.now(),fetchImpl:async(url,options)=>{
 const result=await fetch(url,options);
 observations.push({status:result.status,sent_etag:options.headers['If-None-Match']??null,response_etag:result.headers.get('etag')});
 return result;
}});
const route='/repos/ChengshuLi/WorldAtlas/git/commits/9ccb16dcb3ebe89e9f38df01dc75934cd6d11c9b';
const first=await api(route),second=await api(route);
assert.deepEqual(second,first);
assert.equal(first.sha,'9ccb16dcb3ebe89e9f38df01dc75934cd6d11c9b');
console.log(JSON.stringify({route,observations,same_authenticated_value:true,value_sha256:createHash('sha256').update(JSON.stringify(first)).digest('hex')}));
