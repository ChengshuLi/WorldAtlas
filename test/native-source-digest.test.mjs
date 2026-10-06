import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {nativeSourceDigest} from '../src/native-source-digest.js';
const expected = features => createHash('sha256').update(JSON.stringify(features.map(f => [f.id, f.geometry])
  .sort((a,b) => a[0].localeCompare(b[0])))).digest('hex');

test('streamed source digest equals original whole JSON bytes including Unicode, ordering and numeric edge cases',async()=>{
  const fixtures=[[],[{id:'Ω 🗺️\ud800',geometry:null},{id:'a',geometry:undefined}],
    [{id:'z',geometry:{type:'Polygon',coordinates:[[[-0,1e-15],[180,-90],[1.2345678901234567,90],[-0,1e-15]]]}},
    {id:'ä',geometry:{coordinates:[],type:'MultiPolygon'}}],
    Array.from({length:520},(_,i)=>({id:'id:'+i,geometry:{type:'Polygon',coordinates:[[[i/100,0],[1,1],[0,1],[i/100,0]]]}}))];
  for(const features of fixtures){
    const before=JSON.stringify(features),progress=[];
    const actual=await nativeSourceDigest(features,{onProgress:p=>progress.push(p)});
    assert.equal(actual.sha256,expected(features));
    assert.equal(actual.bytes,Buffer.byteLength(JSON.stringify(features.map(f=>[f.id,f.geometry]).sort((a,b)=>a[0].localeCompare(b[0])))));
    assert.equal(JSON.stringify(features),before);
    if(features.length>256)assert.ok(progress.length>=2);
  }
});

test('source changes alter digest and cancellation/callback errors never return a partial digest',async()=>{
  const features=Array.from({length:520},(_,i)=>({id:'id:'+i,geometry:{type:'Polygon',coordinates:[]}}));
  const baseline=await nativeSourceDigest(features);
  const changed=structuredClone(features);changed[500].geometry.coordinates=[[[-1,0],[0,1],[1,0],[-1,0]]];
  assert.notEqual((await nativeSourceDigest(changed)).sha256,baseline.sha256);
  const controller=new AbortController();
  await assert.rejects(nativeSourceDigest(features,{signal:controller.signal,onProgress:()=>controller.abort()}),{name:'AbortError'});
  await assert.rejects(nativeSourceDigest(features,{onProgress:()=>{throw Error('Progress callback failed');}}),/callback failed/);
});
