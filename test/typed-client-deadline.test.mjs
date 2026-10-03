import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {loadHostedTypedEvidence,loadPreparedTypedEvidence} from '../src/typed-client.js';
const bytes=fs.readFileSync(new URL('../data/typed-prepared-v1.json',import.meta.url)),sha256=createHash('sha256').update(bytes).digest('hex');
const prepared={url:'https://example.org/typed-evidence.json',sha256,year:2026};

test('prepared and hosted typed loads terminate stalled fetches and cancel stalled bodies without accepting partial evidence',async()=>{
 for(const load of [options=>loadPreparedTypedEvidence({...prepared,...options}),options=>loadHostedTypedEvidence({origin:'https://example.org',year:2026,...options})]){
  let forwarded;
  await assert.rejects(load({timeoutMs:30,fetcher:async(url,options)=>{forwarded=options.signal;return new Promise(()=>{});}}),error=>error.name==='TimeoutError');assert.equal(forwarded.aborted,true);
  let cancelled=false;
  await assert.rejects(load({timeoutMs:30,fetcher:async()=>new Response(new ReadableStream({start(){},cancel(){cancelled=true;}}))}),error=>error.name==='TimeoutError');assert.equal(cancelled,true);
 }
});

test('external cancellation reaches typed transport/read cleanup and completed exact-byte loads clear their deadline',async()=>{
 const controller=new AbortController();let forwarded,cancelled=false;
 const loading=loadPreparedTypedEvidence({...prepared,timeoutMs:1000,signal:controller.signal,fetcher:async(url,options)=>{forwarded=options.signal;return new Response(new ReadableStream({start(){},cancel(){cancelled=true;}}));}});
 await new Promise(resolve=>setTimeout(resolve,10));controller.abort();await assert.rejects(loading,error=>error.name==='AbortError');assert.equal(forwarded.aborted,true);assert.equal(cancelled,true);
 const preaborted=new AbortController();preaborted.abort();await assert.rejects(loadHostedTypedEvidence({origin:'https://example.org',year:2026,signal:preaborted.signal,fetcher:async()=>new Promise(()=>{})}),error=>error.name==='AbortError');
 const completed=await loadPreparedTypedEvidence({...prepared,timeoutMs:1000,fetcher:async()=>new Response(bytes)});assert.equal(completed.observations.length,0);
 for(const timeoutMs of [0,-1,Infinity,120001])await assert.rejects(loadPreparedTypedEvidence({...prepared,timeoutMs,fetcher:async()=>new Response(bytes)}),/Invalid typed load deadline/);
});
