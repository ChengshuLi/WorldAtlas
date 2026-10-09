// Real CLI/Git execution fixture; not a full selected-product checkout.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {authenticateInstalledCheckoutExecutable,checkoutExecutionClosure} from './artifact-checkout-execution.mjs';
const destination=path.resolve(process.argv[2]);
assert(destination.includes('/.cache/'));assert(!fs.existsSync(destination));
fs.mkdirSync(path.join(destination,'scripts'),{recursive:true});
const source=fs.readFileSync(new URL('./artifact-checkout-execution.mjs',import.meta.url));
fs.writeFileSync(path.join(destination,'scripts/artifact-checkout-execution.mjs'),source);
fs.writeFileSync(path.join(destination,'package.json'),'{"type":"module"}\n');
const entry=[
  "import assert from 'node:assert/strict';import fs from 'node:fs';",
  "import {issueCheckoutExecution,requireCheckoutExecution} from './artifact-checkout-execution.mjs';",
  "const admission={kind:'qualified-artifact-normal-package-stat-admission',numerical_aggregate_cap_applied:false};",
  "if(process.env.CONTROL_REFUSAL){let opens=0;const original=fs.openSync;fs.openSync=(...args)=>{opens++;return original(...args)};",
  "try{assert.throws(()=>issueCheckoutExecution({root:process.cwd(),admission}));assert.equal(opens,0);console.log(JSON.stringify({refused:true,opens}));}finally{fs.openSync=original;}}",
  "else{const record=issueCheckoutExecution({root:process.cwd(),admission});assert.equal(requireCheckoutExecution(record),record);",
  "let rejected=0;for(const foreign of [{},structuredClone(record)]){assert.throws(()=>requireCheckoutExecution(foreign));rejected++;}",
  "const originalShard=process.env.INTEGRATION_SHARD;process.env.INTEGRATION_SHARD=originalShard==='2'?'1':'2';assert.throws(()=>requireCheckoutExecution(record));rejected++;process.env.INTEGRATION_SHARD=originalShard;",
  "const hash=record.runtime.sha256;record.runtime.sha256='0'.repeat(64);assert.throws(()=>requireCheckoutExecution(record));rejected++;record.runtime.sha256=hash;",
  "const name='scripts/artifact-checkout-execution.mjs',raw=fs.readFileSync(name);fs.appendFileSync(name,'\\n// body drift\\n');",
  "try{assert.throws(()=>requireCheckoutExecution(record));rejected++;}finally{fs.writeFileSync(name,raw);}",
  "assert.equal(requireCheckoutExecution(record),record);",
  "console.log(JSON.stringify({positive:2,rejected,files:record.files,source_commit:record.source_commit,runtime:record.runtime,tool:record.tool}));}"
].join('\n')+'\n';
fs.writeFileSync(path.join(destination,'scripts/run-integration-tests.mjs'),entry);
fs.writeFileSync(path.join(destination,'scripts/wrong-entry.mjs'),entry);
const git=process.platform==='darwin'?'/Library/Developer/CommandLineTools/usr/bin/git':'/usr/bin/git';
function run(command,args,env={}){const result=spawnSync(command,args,{cwd:destination,encoding:'utf8',env:{...process.env,NODE_OPTIONS:'',NODE_PATH:'',...env},maxBuffer:4*1024*1024});assert.equal(result.status,0,result.stderr);return result.stdout;}
run(git,['init','--quiet']);run(git,['add','.']);run(git,['-c','user.name=Boundary fixture','-c','user.email=fixture@example.invalid','commit','--quiet','-m','Complete tiny execution fixture']);
const installedFixture=path.join(destination,'installed-executable');fs.writeFileSync(installedFixture,'#!/bin/sh\nexit 0\n');fs.chmodSync(installedFixture,0o777);
const installed777=authenticateInstalledCheckoutExecutable(installedFixture);assert.equal(installed777.mode,0o777);
fs.chmodSync(installedFixture,0o644);assert.throws(()=>authenticateInstalledCheckoutExecutable(installedFixture));
fs.chmodSync(path.join(destination,'scripts/artifact-checkout-execution.mjs'),0o777);assert.throws(()=>checkoutExecutionClosure(destination));
fs.chmodSync(path.join(destination,'scripts/artifact-checkout-execution.mjs'),0o644);
const positive=JSON.parse(run(process.execPath,['scripts/run-integration-tests.mjs'],{INTEGRATION_PROFILE:'full',INTEGRATION_SHARD:'2'}));
const preparedPositive=JSON.parse(run(process.execPath,['scripts/run-integration-tests.mjs'],{INTEGRATION_PROFILE:'full',INTEGRATION_SHARD:'1'}));
assert.equal(preparedPositive.positive,2);
const packagedPositive=JSON.parse(run(process.execPath,['scripts/run-integration-tests.mjs'],{INTEGRATION_PROFILE:'full',INTEGRATION_SHARD:'0'}));
assert.equal(packagedPositive.positive,2);
const refusals=[];
for(const [script,profile,shard] of [['scripts/wrong-entry.mjs','full','2'],['scripts/run-integration-tests.mjs','evidence','2'],['scripts/run-integration-tests.mjs','full','3']])
  refusals.push(JSON.parse(run(process.execPath,[script],{INTEGRATION_PROFILE:profile,INTEGRATION_SHARD:shard,CONTROL_REFUSAL:'1'})));
console.log(JSON.stringify({kind:'actual-checkout-execution-boundary-controls',production_module_sha256:createHash('sha256').update(source).digest('hex'),fixture:destination,installed_executable_0777:installed777,non_executable_and_source_0777_refusals:2,positive,prepared_shard_positive:preparedPositive,packaged_shard_positive:packagedPositive,zero_open_entry_refusals:refusals,
  limitation:'Fixture runner differs from the production runner; final production closure and actual selected-product checkout remain required.'},null,2));
