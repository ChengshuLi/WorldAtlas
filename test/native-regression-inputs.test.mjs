import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {prepareNativeRegressionInputs,NATIVE_REGRESSION_COMMITS,integrationTestFiles} from '../scripts/run-integration-tests.mjs';
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

const common=[
 'd55795e4c0ad01527029db0bd1d774124a12a61a','548c5f89f00271050823076a84695bb41e1b8454',
 'd70c5d86e345a225b6bc78d67451b3cbbf7a5eed','65cfcef5ffd7d8b98077b9058a374d1e27047430',
 '35d2d3ff48957d34ee8d4329824b268ecadc6d3c'
];
const custody=['8f6dc184d1a41b634cec4759bb57b3cc04dd980a','6ed6406f9fad4c7c468b06a376346b216cb50db7'];
const consumers=[
 ['test/physical-component-custody.test.mjs',custody],
 ['test/physical-component-report-binding.test.mjs',custody]
];
function requiredFor(files,options={}){
 const f=fixture(options),result=prepareNativeRegressionInputs('full',{...f.options,files});
 return {...f,result};
}
test('actual physical consumer files acquire their complete archived source and execution unions',()=>{
 for(const [name,commits] of consumers){
  const f=requiredFor([name]),expected=[...common,...commits];
  assert.deepEqual(f.result,{applicable:true,fetched:expected},name);
  assert.deepEqual(f.calls.filter(c=>c.args[0]==='fetch').map(c=>c.args),
   [['fetch','--no-tags','--depth=1','origin',...expected]],name);
  assert.deepEqual(f.calls.filter(c=>c.args[0]==='cat-file').map(c=>c.args[2]),
   [...expected,...expected].map(commit=>commit+'^{commit}'),name);
 }
});
test('common native inputs remain while unrelated and compact physical controls omit archive acquisition',()=>{
 for(const files of [['test/future-native-consumer.test.mjs'],[
  'test/physical-component-evidence-controls.test.mjs','test/physical-gap-priority-controls.test.mjs',
  'test/physical-gap-priority-evidence-controls.test.mjs','test/context-input-stage.test.mjs']]){
  const f=requiredFor(files);assert.deepEqual(f.result.fetched,common);
 }
 assert.deepEqual(requiredFor(undefined).result.fetched,NATIVE_REGRESSION_COMMITS);
 for(const files of [[],null,'test/physical-component-custody.test.mjs',[null],['../test/physical-component-custody.test.mjs']])
  assert.throws(()=>requiredFor(files),/Actual regression file roster/);
 const f=fixture();
 assert.throws(()=>prepareNativeRegressionInputs('full',{...f.options,files:['test/deleted-consumer.test.mjs'],
  exists:name=>name==='scripts/native-ownership/validate-context-input-stage.mjs'}),/Actual regression file roster/);
 assert.deepEqual(f.calls,[],'A stale roster must fail before any Git read');
});
test('file order, duplicates and shard movement cannot drop or duplicate an archived requirement',()=>{
 const all=consumers.map(([name])=>name);
 for(const files of [all,[...all].reverse(),[...all,all[0]]])
  assert.deepEqual(requiredFor(files).result.fetched,NATIVE_REGRESSION_COMMITS);
 for(const shard of [0,1,2]){
  const files=integrationTestFiles('full',shard),expected=new Set(common);
  for(const [name,commits] of consumers)if(files.includes(name))for(const commit of commits)expected.add(commit);
  assert.deepEqual(new Set(requiredFor(files).result.fetched),expected);
 }
});
test('a missing required archived object still fails after a scoped fetch, and present ones are not fetched again',()=>{
 const files=['test/physical-component-custody.test.mjs'];
 for(const options of [{present:common,fetchFails:true},{present:common,fetchIncomplete:true}])
  assert.throws(()=>requiredFor(files,options),/fetch failed|remain unavailable/);
 const f=requiredFor(files,{present:[...common,custody[0]]});
 assert.deepEqual(f.result.fetched,[custody[1]]);
 assert.deepEqual(prepareNativeRegressionInputs('full',{...f.options,files}),{applicable:true,fetched:[]});
 assert.equal(f.calls.filter(c=>c.args[0]==='fetch').length,1);
});


test('remaining custody pins agree with the actual retained component generations',()=>{
 const read=name=>JSON.parse(fs.readFileSync(name));
 const index=read('coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json');
 assert.deepEqual(new Set(index.generations.map(generation=>generation.executed_code_commit)),new Set(custody));
 const source=fs.readFileSync(new URL('../scripts/run-integration-tests.mjs',import.meta.url),'utf8');
 assert.match(source,/prepareNativeRegressionInputs\(testSelection === 'complete' \? profile : 'evidence',\{files,run:git.run\}\)/);
});
