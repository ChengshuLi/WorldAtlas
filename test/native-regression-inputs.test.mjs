import test from 'node:test';
import assert from 'node:assert/strict';
import {prepareNativeRegressionInputs,NATIVE_REGRESSION_COMMITS} from '../scripts/run-integration-tests.mjs';
function fixture({present=[],fetchFails=false,fetchIncomplete=false}={}){
 const available=new Set(present),calls=[];
 const run=(command,args)=>{
  calls.push({command,args});assert.equal(command,'git');
  if(args[0]==='cat-file')return {status:available.has(args[2].slice(0,-9))?0:1};
  assert.deepEqual(args.slice(0,5),['fetch','--no-tags','--depth=1','origin',args[4]]);
  if(!fetchFails&&!fetchIncomplete)for(const commit of args.slice(4))available.add(commit);
  return {status:fetchFails?1:0,stderr:fetchFails?'synthetic unavailable remote':''};
 };
 return {calls,options:{exists:()=>true,run}};
}
test('shallow PR and queue regressions obtain only missing immutable vintages and verify availability',()=>{
 const f=fixture({present:[NATIVE_REGRESSION_COMMITS[0]]});
 assert.deepEqual(prepareNativeRegressionInputs('full',f.options),{applicable:true,fetched:NATIVE_REGRESSION_COMMITS.slice(1)});
 assert.deepEqual(f.calls.find(c=>c.args[0]==='fetch').args,['fetch','--no-tags','--depth=1','origin',...NATIVE_REGRESSION_COMMITS.slice(1)]);
 const count=f.calls.filter(c=>c.args[0]==='fetch').length;
 assert.deepEqual(prepareNativeRegressionInputs('full',f.options),{applicable:true,fetched:[]});
 assert.equal(f.calls.filter(c=>c.args[0]==='fetch').length,count);
});
test('unpublished evidence and absent native implementation do not fetch or inspect Git',()=>{
 for(const [profile,exists] of [['evidence',()=>true],['full',()=>false]])
  assert.deepEqual(prepareNativeRegressionInputs(profile,{exists,run:()=>assert.fail('unexpected Git read')}),{applicable:false,fetched:[]});
});
test('failed or incomplete frozen input fetch cannot establish regression coverage',()=>{
 for(const options of [{fetchFails:true},{fetchIncomplete:true}]){
  const f=fixture(options);assert.throws(()=>prepareNativeRegressionInputs('full',f.options),/fetch failed|remain unavailable/);
 }
});
