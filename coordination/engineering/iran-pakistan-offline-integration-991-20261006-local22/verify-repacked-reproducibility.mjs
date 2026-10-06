import fs from 'node:fs';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {requirePlainExecution,committedPreparationFiles,candidateBudget} from '../../../scripts/native-ownership/native-preparation-guards.mjs';
requirePlainExecution();
const P='coordination/engineering/iran-pakistan-offline-integration-991-20261006-local22';
const output=P+'/repacked-release-reproducibility-v1.json';assert(!fs.existsSync(output));
const head=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
const code=committedPreparationFiles(process.cwd(),head,['package.json','scripts/native-ownership/native-preparation-guards.mjs',P+'/verify-repacked-reproducibility.mjs']);
const budget=candidateBudget(code),sha=b=>createHash('sha256').update(b).digest('hex');
const a=P+'/repacked-release-v2',b=P+'/repacked-release-v3';
const files=fs.readdirSync(a).sort();assert.deepEqual(files,fs.readdirSync(b).sort());
const inventory=[];
for(const name of files){const one=fs.readFileSync(a+'/'+name),two=fs.readFileSync(b+'/'+name);budget.add({bytes:one.length});budget.add({bytes:two.length});assert.deepEqual(one,two,'Independent output differs: '+name);inventory.push({path:name,bytes:one.length,sha256:sha(one)});}
const receipt=JSON.parse(fs.readFileSync(a+'/verification.json'));
for(const pin of receipt.outputs){const actual=inventory.find(p=>p.path===pin.path);assert.deepEqual(actual,pin);}
assert.equal(inventory.length,receipt.outputs.length+1);
const digest=sha(Buffer.from(JSON.stringify(inventory)));
fs.writeFileSync(output,JSON.stringify({method_id:'lossless-release-transport-repack',kind:'reproducibility',outcome:'passed',execution_commit:head,code,run_producer_commit:receipt.execution_commit,run_one_path:a,run_two_path:b,run_one_sha256:digest,run_two_sha256:digest,digest_kind:'complete ordered whole-file output pin inventory, including verification and controls',files:inventory,budget:budget.snapshot()})+'\n',{flag:'wx'});
console.log(JSON.stringify({files:inventory.length,equal:true,digest,budget:budget.snapshot()}));
