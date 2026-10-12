import fs from 'node:fs';import path from 'node:path';import {fileURLToPath} from 'node:url';import {createHash} from 'node:crypto';import test from 'node:test';import assert from 'node:assert/strict';
import {candidateBudget,preparationAllowance,preparationRequestAllowance} from '../scripts/native-ownership/native-preparation-guards.mjs';
import {verifyPreparationBudgetCode} from '../scripts/native-ownership/chained-build-context.mjs';
import {inventoryResourceAdmission} from '../scripts/additive-gap-repair.mjs';
const MiB=1024**2,GiB=1024**3,sha=b=>createHash('sha256').update(b).digest('hex');
const root=fileURLToPath(new URL('../',import.meta.url));
test('native preparation admits requested current aggregate above historical256MiB without relaxing members/descriptors',()=>{
 const inputs=Array.from({length:9},()=>({bytes:32*MiB})),small=preparationAllowance({phaseBytes:256*MiB,rssBytes:512*MiB}),large=preparationAllowance({phaseBytes:512*MiB,rssBytes:768*MiB});
 assert.throws(()=>candidateBudget(inputs,{allowance:small}),/Aggregate/);const budget=candidateBudget(inputs,{allowance:large});assert.equal(budget.snapshot().limit_bytes,512*MiB);assert.equal(budget.snapshot().rss_limit_bytes,768*MiB);
 assert.throws(()=>budget.add({bytes:32*MiB+1}),/whole-file/);assert.throws(()=>candidateBudget(Array.from({length:497},()=>({bytes:1})),{allowance:large}),/Aggregate/);
 assert.throws(()=>candidateBudget([],{allowance:{phaseBytes:Number.MAX_SAFE_INTEGER,rssBytes:Number.MAX_SAFE_INTEGER}}),/admission/);
});
test('native preparation refuses unadmitted, malformed and RSS-exhausted configurations',()=>{
 for(const options of [{availableBytes:2*GiB},{availableBytes:4*GiB,concurrentReservedBytes:2*GiB},{phaseBytes:NaN},{rssBytes:Infinity},{phaseBytes:0},{phaseBytes:Number.MAX_SAFE_INTEGER}])assert.throws(()=>preparationAllowance(options),/admission|Insufficient/);
 for(const bad of [null,{}, {phaseBytes:null,rssBytes:null},{phaseBytes:undefined,rssBytes:768*MiB},{phaseBytes:512*MiB,rssBytes:undefined}, {phaseBytes:512*MiB,rssBytes:768*MiB,availableBytes:2**40}])assert.throws(()=>preparationRequestAllowance(bad),/request allowance/);
 assert.throws(()=>candidateBudget([],{allowance:{phaseBytes:MiB,rssBytes:1}}),/RSS/);
});
test('source/native output reserve grows by issued parameters while historical v1 retains its literal96MiB',()=>{
 const requested={processing_allowance:{phaseBytes:512*MiB,rssBytes:768*MiB},output_reserve:128*MiB,operating_profile:'source-native-v2',operating_runtime:{version:1}};
 assert.equal(inventoryResourceAdmission(requested).outputReserve,128*MiB);
 const legacy={output_reserve:128*MiB,operating_runtime:{version:1}};assert.throws(()=>inventoryResourceAdmission(legacy),/historical output/);
 assert.equal(inventoryResourceAdmission({...legacy,output_reserve:MiB}).allowance.phaseBytes,256*MiB);
 assert.throws(()=>inventoryResourceAdmission({...requested,output_reserve:513*MiB}),/admitted output/);
});

const originalPrefix="import fs from 'node:fs';\nimport path from 'node:path';\nimport {execFileSync} from 'node:child_process';\nimport {createHash} from 'node:crypto';\n\nconst digest = raw => createHash('sha256').update(raw).digest('hex');\nconst safe = name => typeof name === 'string' && /^[a-zA-Z0-9_./-]+$/.test(name) &&\n  name.split('/').every(part => part && part !== '.' && part !== '..');\n\nexport function requirePlainExecution() {\n  if (process.execArgv.length || process.env.NODE_OPTIONS?.trim() || process.env.NODE_PATH?.trim())\n    throw Error('Native preparation requires the reviewed plain Node launch without loaders/preloads');\n}\n\n";
const originalBudget="export function candidateBudget(inputs, {reserveBytes = 131072, reserveDescriptors = 16} = {}) {\n  const limitBytes = 256 * 1024 * 1024, limitDescriptors = 512;\n  if (!Number.isSafeInteger(reserveBytes) || reserveBytes < 0 || !Number.isInteger(reserveDescriptors) || reserveDescriptors < 0)\n    throw Error('Invalid preparation budget reservation');\n  let bytes = 0, descriptors = 0;\n  function add(item) {\n    if (!Number.isSafeInteger(item?.bytes) || item.bytes < 0 || item.bytes > 32 * 1024 * 1024)\n      throw Error('Invalid whole-file admission');\n    if (bytes + item.bytes + reserveBytes > limitBytes || descriptors + 1 + reserveDescriptors > limitDescriptors)\n      throw Error('Aggregate evidence preparation budget exceeded');\n    bytes += item.bytes; descriptors++;\n  }\n  for (const input of inputs) add(input);\n  return {add, snapshot: () => ({accounted_bytes: bytes, accounted_descriptors: descriptors,\n    reserved_review_bytes: reserveBytes, reserved_review_descriptors: reserveDescriptors, limit_bytes: limitBytes,\n    limit_descriptors: limitDescriptors, limits_include_reserve: true})};\n}\n\n";
test('exact guard compatibility preserves non-budget helpers and refuses foreign operational or numerical bodies',()=>{
 const current=fs.readFileSync(path.join(root,'scripts/native-ownership/native-preparation-guards.mjs'));const text=current.toString(),start=text.indexOf('// Current operational admission'),end=text.indexOf('export function originalCandidateAssets(');
 assert(start>0&&end>start);const original=Buffer.from(originalPrefix+originalBudget+text.slice(end));const oldPin={bytes:original.length,sha256:sha(original)},newPin={bytes:current.length,sha256:sha(current)};
 assert.equal(verifyPreparationBudgetCode(original,current,oldPin,newPin),current.length-original.length);
 for(const name of ['requirePlainExecution','originalCandidateAssets','committedPreparationFiles','createNativeCandidateOutput','candidateBudget']){const changed=Buffer.from(text.replace('function '+name+'(', 'function '+name+'Changed('));assert.throws(()=>verifyPreparationBudgetCode(original,changed,oldPin,{bytes:changed.length,sha256:sha(changed)}),/preparation guard/);}
 const changedOld=Buffer.from(original.toString().replace('256 * 1024 * 1024','255 * 1024 * 1024'));assert.throws(()=>verifyPreparationBudgetCode(changedOld,current,{bytes:changedOld.length,sha256:sha(changedOld)},newPin),/historical/);
});
