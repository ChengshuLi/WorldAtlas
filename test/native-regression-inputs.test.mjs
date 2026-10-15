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

test('complete archived priority artifacts register their immutable input and execution vintages',()=>{
 const report=JSON.parse(fs.readFileSync('coordination/engineering/physical-gap-priorities-1005-20261006-local20/priorities-v2/report.json'));
 for(const commit of [report.input_commit,report.executed_code_commit,report.original_native_commit]){
  assert.ok(NATIVE_REGRESSION_COMMITS.includes(commit),`Shallow CI must restore ${commit}`);
 }
});


const common=[
 'd55795e4c0ad01527029db0bd1d774124a12a61a','548c5f89f00271050823076a84695bb41e1b8454',
 'd70c5d86e345a225b6bc78d67451b3cbbf7a5eed','65cfcef5ffd7d8b98077b9058a374d1e27047430',
 '35d2d3ff48957d34ee8d4329824b268ecadc6d3c'
];
const audit=[
 'ff566eab31ef072084c548f67dee8ee727ab3d47','e67eeafc1aa130aa5c1a6d1222d39116625fd003',
 '8b61b9303553f2068f18ad5a000d4cba14059547','b6e0d0d21cfd6dde68c3c292c9513d3a24896a11',
 '85571b6ef23f5565f08693a542fa7dad20c651b8'
];
const componentInput='c603befd3aaf4da90d59b12378e1e0739331efba';
const custody=['8f6dc184d1a41b634cec4759bb57b3cc04dd980a','6ed6406f9fad4c7c468b06a376346b216cb50db7'];
const priority='bf9e8a6580e997d82d0414235e3a0d2a81e1e24a';
const consumers=[
 ['test/physical-audit-evidence.test.mjs',audit],
 ['test/physical-component-evidence.test.mjs',[componentInput,...custody]],
 ['test/physical-component-custody.test.mjs',custody],
 ['test/physical-component-fixture.test.mjs',custody],
 ['test/physical-component-report-binding.test.mjs',custody],
 ['test/physical-gap-priority-evidence.test.mjs',[priority]]
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
 for(const files of [[],null,'test/physical-audit-evidence.test.mjs',[null],['../test/physical-audit-evidence.test.mjs']])
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


test('scoped physical pins agree with the actual retained audit envelope, reports and component generations',()=>{
 const read=name=>JSON.parse(fs.readFileSync(name));
 const root=read('coordination/engineering/physical-gap-audit-1005-20261005-local18/evidence-quality.json');
 const envelope=read(root.mandatory_input_stage.envelope_manifest);
 const reports=root.audit_reports.map(pin=>read(pin.path));
 const actualAudit=new Set([envelope.executed_code_commit,
  ...reports.flatMap(report=>[report.baseline_commit,report.water_commit,report.executed_code_commit])]);
 assert.deepEqual(actualAudit,new Set([common[1],...audit]));
 const index=read('coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json');
 assert.deepEqual(new Set(index.generations.map(generation=>generation.executed_code_commit)),new Set(custody));
 assert.deepEqual(new Set(index.generations.map(generation=>generation.input_commit)),new Set([componentInput]));
 const source=fs.readFileSync(new URL('../scripts/run-integration-tests.mjs',import.meta.url),'utf8');
 assert.match(source,/prepareNativeRegressionInputs\(testSelection === 'complete' \? profile : 'evidence',\{files,run:git.run\}\)/);
});
