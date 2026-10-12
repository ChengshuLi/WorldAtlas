import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {processingAllowance,ImmutableReader} from '../scripts/check-effective-geographic-regression.mjs';
import {currentRebindReadbackLimits,admitCurrentRebindOutputFrame} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const MiB=1024**2,GiB=1024**3,root=path.resolve(import.meta.dirname,'..');
const grant=()=>processingAllowance({availableBytes:8*GiB,concurrentReservedBytes:GiB,phaseBytes:512*MiB,rssBytes:GiB});
const reader=allowance=>new ImmutableReader(root,'a'.repeat(40),{runtimeBytes:1,executionBytes:1,metadataBytes:300*MiB,outputBytes:1,allowance});
test('normal allowance scales with current capacity instead of the former 256 MiB ceiling',()=>{
 const small=processingAllowance({availableBytes:6*GiB,concurrentReservedBytes:GiB});
 const large=processingAllowance({availableBytes:10*GiB,concurrentReservedBytes:GiB});
 assert(small.phaseBytes>256*MiB);assert(large.phaseBytes>small.phaseBytes);
 assert(large.rssBytes<10*GiB-GiB-2*GiB-768*MiB);
 for(const availableBytes of [0,NaN,Infinity,-1,Number.MAX_SAFE_INTEGER+1])assert.throws(()=>processingAllowance({availableBytes}),/observations|memory/);
 for(const concurrentReservedBytes of [-1,NaN,8*GiB])assert.throws(()=>processingAllowance({availableBytes:8*GiB,concurrentReservedBytes}),/observations|memory/);
 assert.throws(()=>processingAllowance({availableBytes:8*GiB,rssBytes:7*GiB}),/admission/);
});
test('the actual reader admits the demonstrated >256 MiB logical frame with a finite current allowance',()=>{
 const allowance=grant(),r=reader(allowance);assert.equal(r.used,300*MiB+3);
 const nested=new ImmutableReader(root,'b'.repeat(40),{runtimeBytes:1,metadataBytes:1,outputBytes:1,budget:r.budget});
 assert.equal(nested.allowance,allowance);assert.equal(nested.budget,r.budget);
 r.admit({commit:'a'.repeat(40),path:'one.json',bytes:20*MiB});assert.equal(nested.used,r.used);
 assert.throws(()=>reader({...allowance,phaseBytes:256*MiB}),/complete phase/);
 assert.throws(()=>r.admit({commit:'a'.repeat(40),path:'oversized.json',bytes:1},32*MiB+1),/decoded member/);
 assert.throws(()=>reader({...allowance,rssBytes:1}),/RSS/);
});
test('historical output grant cannot authorize or constrain current readback allocation',()=>{
 const roster=['request','facts','result','publication'].map(name=>({name,p:{bytes:MiB}}));
 const r=reader(grant()),limits=currentRebindReadbackLimits(r,roster);
 assert.deepEqual(limits,{output_bytes:4*MiB,complete_phase_bytes:512*MiB});
 assert.equal(admitCurrentRebindOutputFrame(r,limits),328*MiB+2);
 assert.throws(()=>admitCurrentRebindOutputFrame(r,{...limits,complete_phase_bytes:245679353}),/before products/);
 const small=new ImmutableReader(root,'a'.repeat(40),{runtimeBytes:1,metadataBytes:200*MiB,allowance:{phaseBytes:256*MiB,rssBytes:GiB}});
 const large=roster.map(row=>({...row,p:{bytes:4*MiB}}));
 assert.throws(()=>admitCurrentRebindOutputFrame(small,currentRebindReadbackLimits(small,large)),/complete phase/);
 assert.throws(()=>currentRebindReadbackLimits(r,roster.slice(1)),/Incomplete/);
});
