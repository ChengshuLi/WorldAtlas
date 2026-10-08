import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import syncFs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {restoreWholeImage} from './whole-image.mjs';
import {verifyAuthoredValidatorSources} from './chained-context.mjs';
import {materializePackageInputs,runPackageBuild} from '../../../scripts/package-build.mjs';
import {issueCurrentExecution,authenticateCurrentExecution,requireCurrentExecution} from './current-execution.mjs';
async function fixture(t, {program, promoted = false} = {}) {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'atlas-package-boundary-'));
  t.after(() => fs.rm(root, {recursive: true, force: true}));
  const definition = {version: 1, inputs: ['.github/package-inputs.json', 'scripts/build-static-inner.mjs', 'src/'],
    optional_inputs: [], verification_paths: [], generated_outputs: ['dist/']};
  if (promoted) definition.inputs.push('research/paper.json');
  const files = {'.github/package-inputs.json': JSON.stringify(definition), 'src/value.json': '42',
    'scripts/build-static-inner.mjs': program ?? "import fs from 'node:fs'; fs.mkdirSync('dist'); fs.writeFileSync('dist/value.json', fs.readFileSync('src/value.json'));",
    'research/paper.json': '99', 'research/secret.mjs': 'export default 99;'};
  for (const [name, value] of Object.entries(files)) {
    await fs.mkdir(path.dirname(path.join(root, name)), {recursive: true});
    await fs.writeFile(path.join(root, name), value);
  }
  await fs.mkdir(path.join(root, 'node_modules'));
  return {root, definition};
}

async function executionFixture(t){
 const {root}=await fixture(t),ns='coordination/engineering/eastern-two-gap-repair-native-20261007';
 const files={
  'package.json':'{"type":"module"}\n',
  'scripts/native-ownership/validate-build-context-stage.mjs':"import '../evidence-quality.mjs';\nexport const result='current';\n",
  'scripts/evidence-quality.mjs':'export const currentLibrary=1;\n',
  'scripts/package-build.mjs':`import '../${ns}/current-execution.mjs';\n`,
  [ns+'/current-execution.mjs']:await fs.readFile(new URL('./current-execution.mjs',import.meta.url)),
  'data/native-context-migration/manifest.json':JSON.stringify({version:2,kind:'retained-identity-context-continuation-v2',issue:1295,validator_sources:[{path:'scripts/evidence-quality.mjs',bytes:1,sha256:'historical-preserved'}]})
 };
 for(const [name,raw]of Object.entries(files)){await fs.mkdir(path.dirname(path.join(root,name)),{recursive:true});await fs.writeFile(path.join(root,name),raw);}
 const definition=JSON.parse(await fs.readFile(path.join(root,'.github/package-inputs.json')));
 definition.inputs.push('package.json','scripts/native-ownership/validate-build-context-stage.mjs','scripts/evidence-quality.mjs','scripts/package-build.mjs',ns+'/current-execution.mjs','data/native-context-migration/manifest.json');
 await fs.writeFile(path.join(root,'.github/package-inputs.json'),JSON.stringify(definition));
 const git=args=>execFileSync('git',['-C',root,...args],{encoding:'utf8'}).trim();
 git(['init','-q']);git(['config','user.name','package control']);git(['config','user.email','package-control@example.invalid']);
 const commit=()=>{git(['add','--','.']);git(['commit','-qm','actual package fixture']);return git(['rev-parse','HEAD']);};
 commit();return{root,definition,git,commit};
}

async function currentPositive(t){
 const {root,commit}=await executionFixture(t);const historical=await fs.readFile(path.join(root,'data/native-context-migration/manifest.json'));
 const execute=async(entry,{cwd,env})=>{
  const raw=await fs.readFile(path.join(cwd,env.WORLDATLAS_CURRENT_EXECUTION_PATH));
  assert.equal(createHash('sha256').update(raw).digest('hex'),env.WORLDATLAS_CURRENT_EXECUTION_SHA256);
  const record=authenticateCurrentExecution(JSON.parse(raw),{root:cwd,executingRoot:root,sourceRoot:root});requireCurrentExecution(record);
  await fs.mkdir(path.join(cwd,'dist'));await fs.writeFile(path.join(cwd,'dist/value'),'actual current execution');
 };
 const first=await runPackageBuild('static',{root,execute});
 await fs.writeFile(path.join(root,'scripts/evidence-quality.mjs'),'export const currentLibrary=2;\n');const head=commit();
 const second=await runPackageBuild('static',{root,execute});
 assert.notEqual(first.current_context_execution.source_commit,head);assert.equal(second.current_context_execution.source_commit,head);
 assert.notEqual(first.current_context_execution.files.find(p=>p.path==='scripts/evidence-quality.mjs').sha256,second.current_context_execution.files.find(p=>p.path==='scripts/evidence-quality.mjs').sha256);
 assert((await fs.readFile(path.join(root,'data/native-context-migration/manifest.json'))).equals(historical));
 await assert.rejects(runPackageBuild('static',{root,execute:async(entry,{cwd})=>{await fs.appendFile(path.join(cwd,'scripts/evidence-quality.mjs'),'// midrun mutation');}}),/strictly equal|Expected values|SHA|length/i);
}

async function realInnerControls(t){
 const ns='coordination/engineering/eastern-two-gap-repair-native-20261007';
 const cases=[['positive',''],['missing',"delete process.env.WORLDATLAS_CURRENT_EXECUTION_PATH;"],['hash',"process.env.WORLDATLAS_CURRENT_EXECUTION_SHA256='0'.repeat(64);"],['root',"process.env.WORLDATLAS_PACKAGE_SOURCE_ROOT=process.cwd();"],['path',"process.env.WORLDATLAS_CURRENT_EXECUTION_PATH='../foreign.json';"],['stale',"fs.appendFileSync('scripts/evidence-quality.mjs','// stale');"]];
 for(const [name,mutation]of cases){
  const {root,commit}=await executionFixture(t);
  const program=`import fs from 'node:fs';import{readPackageCurrentExecution,requireCurrentExecution}from'../${ns}/current-execution.mjs';${mutation}
const record=readPackageCurrentExecution(process.cwd());requireCurrentExecution(record);fs.mkdirSync('dist');fs.writeFileSync('dist/sentinel','authenticated actual child');
`;
  await fs.writeFile(path.join(root,'scripts/build-static-inner.mjs'),program);commit();
  if(name==='positive'){const result=await runPackageBuild('static',{root});assert(result.current_context_execution);assert.equal(await fs.readFile(path.join(root,'dist/sentinel'),'utf8'),'authenticated actual child');}
  else{await assert.rejects(runPackageBuild('static',{root}),/Package static build failed/);await assert.rejects(fs.stat(path.join(root,'dist/sentinel')),/ENOENT/);}
 }
 return {actual_spawn_without_execute_injection:true,actual_environment_boundary_cases:cases.map(([name])=>name)};
}

async function currentNegative(t){
 const {root,definition}=await executionFixture(t),stage=path.join(root,'test-stage');
 await materializePackageInputs({source:root,destination:stage,definition});
 const record=issueCurrentExecution({source:root,stage});authenticateCurrentExecution(record,{root:stage,executingRoot:root,sourceRoot:root});requireCurrentExecution(record);
 assert.throws(()=>requireCurrentExecution(structuredClone(record)),/authenticated/);
 const badHead={...record,source_commit:'0'.repeat(40)};assert.throws(()=>authenticateCurrentExecution(badHead,{root:stage,executingRoot:root,sourceRoot:root}),/HEAD/);
 assert.throws(()=>authenticateCurrentExecution({...record,source_root:stage},{root:stage,executingRoot:root,sourceRoot:root}));
 const badRuntime=structuredClone(record);badRuntime.runtime.version='foreign';assert.throws(()=>authenticateCurrentExecution(badRuntime,{root:stage,executingRoot:root,sourceRoot:root}));
 const omitted=structuredClone(record);omitted.files.pop();assert.throws(()=>authenticateCurrentExecution(omitted,{root:stage,executingRoot:root,sourceRoot:root}));
 const overbound=structuredClone(record);overbound.files[0].bytes=32*1024*1024+1;assert.throws(()=>authenticateCurrentExecution(overbound,{root:stage,executingRoot:root,sourceRoot:root}));
 const aggregate=structuredClone(record);aggregate.files=Array.from({length:9},()=>({...record.files[0],bytes:32*1024*1024}));let runtimeOpens=0;const originalOpen=syncFs.openSync;syncFs.openSync=function(file,...args){if(String(file)===process.execPath)runtimeOpens++;return originalOpen.call(this,file,...args);};try{assert.throws(()=>authenticateCurrentExecution(aggregate,{root:stage,executingRoot:root,sourceRoot:root}),/aggregate exceeds cap before reads/);assert.equal(runtimeOpens,0,'Overbound combined closure must reject before runtime open');}finally{syncFs.openSync=originalOpen;}
 await fs.chmod(path.join(stage,'scripts/evidence-quality.mjs'),0o755);assert.throws(()=>requireCurrentExecution(record));await fs.chmod(path.join(stage,'scripts/evidence-quality.mjs'),0o644);
 await fs.appendFile(path.join(stage,'scripts/evidence-quality.mjs'),"import './foreign.mjs';\n");assert.throws(()=>requireCurrentExecution(record));
 await fs.writeFile(path.join(stage,'scripts/evidence-quality.mjs'),'export const currentLibrary=1;\n');
 await fs.appendFile(path.join(root,'scripts/evidence-quality.mjs'),'// uncommitted');assert.throws(()=>issueCurrentExecution({source:root,stage}),/immutable actual checkout/);
 record.source_tree='0'.repeat(40);assert.throws(()=>requireCurrentExecution(record),/receipt changed/);
}


async function authoredControls(t){
 const base=path.dirname(fileURLToPath(import.meta.url)),scratch=await fs.mkdtemp(path.join(os.tmpdir(),'atlas-authored-code-'));t.after(()=>fs.rm(scratch,{recursive:true,force:true}));
 const wire=await fs.readFile(base+'/current-consumer-code/index.json');assert.equal(createHash('sha256').update(wire).digest('hex'),'de4a8f7aac3380fc7c5f1cc06ac9bbf0d170c0921d7ef72d5e46187439a80be9');
 const authored=path.join(await fs.realpath(scratch),'image'),codeIndex=restoreWholeImage(base+'/current-consumer-code',authored,{expectedIndexSha:createHash('sha256').update(wire).digest('hex')});
 const stage=JSON.parse(await fs.readFile(base+'/../../../data/native-context-migration/manifest.json'));
 const currentFiles=stage.validator_sources.map(p=>({...p,mode:codeIndex.files.find(f=>f.path===p.path).mode}));
 const args={stage,codeIndex,authored,currentFiles},result=verifyAuthoredValidatorSources(args);assert.equal(result.authored_files,31);
 const omitted=structuredClone(stage);omitted.validator_sources.pop();assert.throws(()=>verifyAuthoredValidatorSources({...args,stage:omitted}));
 for(const name of ['scripts/native-ownership/compile-native-ownership.mjs','scripts/native-ownership/validate-context-migration.mjs','scripts/check-prepared.mjs']){const changed=structuredClone(currentFiles);changed.find(p=>p.path===name).sha256='0'.repeat(64);assert.throws(()=>verifyAuthoredValidatorSources({...args,currentFiles:changed}),/algorithm changed/);}
 const changed=structuredClone(stage);changed.validator_sources[0].sha256='0'.repeat(64);assert.throws(()=>verifyAuthoredValidatorSources({...args,stage:changed}));
 return {...result,all_50_authored_whole_bodies_restored:true,immutable_historical_source_and_numerical_negatives:5};
}
export async function runCurrentExecutionControls(){
 const cleanup=[];const t={after:callback=>cleanup.push(callback)};
 try{await currentPositive(t);await currentNegative(t);const actualInner=await realInnerControls(t);const historical=await authoredControls(t);return {actualInner,historical,status:'PASS',real_plain_node:true,current_commit_drift_positive:true,authored_pins_unchanged:true,adverse_cases:['midrun body','unbranded receipt','wrong HEAD','wrong root','runtime mutation','omitted import','overbound body','aggregate before source reads','mode mutation','new import','uncommitted source','receipt mutation']};}
 finally{for(const callback of cleanup.reverse())await callback();}
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))console.log(JSON.stringify(await runCurrentExecutionControls()));
