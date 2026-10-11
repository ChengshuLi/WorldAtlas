import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {ImmutableReader} from '../scripts/check-effective-geographic-regression.mjs';
import {validateSupportedProgrammeCatalogue,readSupportedProgrammeCatalogue,readSupportedProgrammeAuthority,matchSupportedProgramme,compatibleCurrentRebindCode,CURRENT_REBIND_CODE,valueSha} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const root=fileURLToPath(new URL('../',import.meta.url));
const name='coordination/engineering/selected-geography-effective-prevention-20261009/supported-programs.json';
const helper='coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const read=()=>JSON.parse(fs.readFileSync(path.join(root,name)));
const clone=structuredClone;
const request=p=>({preimageVersion:p.preimage_version,sourceProfile:p.source_profile,sourceCode:p.source_executed_code,nativeCode:p.native_executed_code});
const sha=b=>createHash('sha256').update(b).digest('hex');
const git=(...args)=>execFileSync('git',['-c','core.hooksPath=/dev/null','-C',root,...args],{env:{...process.env,GIT_NO_LAZY_FETCH:'1'}});

test('all twelve literal legacy programme records remain unchanged',()=>{
 // Independent migration review authenticated these exact twelve records
 // against180042b1. Keep their canonical identity without adding a historical
 // Git download to every future test invocation.
 const legacy=read().programs.slice(0,12);assert.equal(legacy.length,12);
 assert.equal(valueSha(legacy),'3bc7b51bf033cffe9ff2c35443fbebbeda2553102c3c00912d62ba5677a90edd');
 for(const p of legacy)assert.deepEqual(matchSupportedProgramme(read(),request(p)),p);
});
test('catalogue-only additions do not change any existing method descriptor',()=>{
 const c=read(),before=clone(c.programs),extra=clone(c.programs.at(-1));
 extra.source_profile='synthetic-other-profile';c.programs.push(extra);
 validateSupportedProgrammeCatalogue(c);assert.deepEqual(c.programs.slice(0,before.length),before);
 for(const p of before)assert.deepEqual(matchSupportedProgramme(c,request(p)),p);
 assert.notEqual(sha(JSON.stringify(c)),sha(JSON.stringify(read())));
});
test('changed caller, helper and other method bytes refuse independently',()=>{
 for(const changedPath of ['scripts/additive-gap-repair.mjs',helper,'package.json']){
  const q=request(clone(read().programs.at(-1))),body=q.nativeCode.find(p=>p.path===changedPath);assert.ok(body);body.sha256='f'.repeat(64);
  assert.throws(()=>matchSupportedProgramme(read(),q),/Unknown\/ambiguous/);
 }
});
test('missing, malformed, duplicate and foreign catalogue records refuse',()=>{
 assert.throws(()=>validateSupportedProgrammeCatalogue(null),/Malformed/);
 for(const mutate of [c=>c.programs.push(clone(c.programs[0])),c=>c.programs[0].source_executed_code.push(clone(c.programs[0].source_executed_code[0])),c=>c.programs[0].accepted_head='latest',c=>c.programs[0].unexpected=true,c=>c.programs[0].native_executed_code[0].bytes=33554433]){
  const c=read();mutate(c);assert.throws(()=>validateSupportedProgrammeCatalogue(c));
 }
 const q=request(clone(read().programs[0]));q.sourceProfile='candidate-only';assert.throws(()=>matchSupportedProgramme(read(),q),/Unknown\/ambiguous/);
});
test('same complete rebind vector retains equality without a generation exception',()=>{
 const code=CURRENT_REBIND_CODE.map(path=>({path,bytes:1,sha256:'a'.repeat(64)}));
 assert.deepEqual(compatibleCurrentRebindCode('f'.repeat(40),code,code),code);
 const changed=clone(code);changed[0].sha256='b'.repeat(64);
 assert.throws(()=>compatibleCurrentRebindCode('f'.repeat(40),changed,code),/Unknown historical/);
});
test('actual trusted-checkout catalogue is inventoried and charged, never selected by reader version',()=>{
 // The candidate version deliberately predates the catalogue. Policy authority
 // still comes from the actual module checkout, whose code/body is committed.
 const reader=new ImmutableReader(root,'180042b1ef55c69a0b2f7b33a9860951d1b5ea82',{runtimeBytes:1,metadataBytes:1,executionBytes:1,outputBytes:1});
 const before=reader.used,policy=readSupportedProgrammeCatalogue(reader),head=git('rev-parse','HEAD').toString().trim();
 assert.equal(policy.pin.commit,head);assert.equal(policy.pin.path,name);assert.equal(policy.pin.sha256,sha(fs.readFileSync(path.join(root,name))));
 assert.equal(policy.pin.whole_body_consumed,true);assert.ok(reader.used>=before+3*policy.pin.bytes);
 assert.ok(reader.inventory.has(head+':'+name));assert.deepEqual(policy.catalogue,read());
});

test('compact programme authority survives a native phase reset with its carry charged',()=>{
 const head=git('rev-parse','HEAD').toString().trim();
 const reader=new ImmutableReader(root,head,{runtimeBytes:1,metadataBytes:17,executionBytes:1,outputBytes:1});
 const proof=readSupportedProgrammeAuthority(reader,request(read().programs[0]));
 assert.deepEqual(Object.keys(proof).sort(),['accepted_head','catalogue','independent_review_comment']);
 assert.equal('programs' in proof,false);assert.equal('source_executed_code' in proof,false);
 const carry=2*(JSON.stringify(proof)+'\n').length;assert.equal(reader.metadataBytes,17+carry);
 reader.phase();assert.equal(reader.used,20+carry);
 assert.equal(reader.inventory.get(head+':'+helper).whole_body_consumed,true);
 assert.match(reader.inventory.get(head+':'+helper).sha256,/^[a-f0-9]{64}$/);
});

test('one exact complete471 migration succeeds and nearby changed vectors refuse',()=>{
 const head=git('rev-parse','HEAD').toString().trim(),reader=new ImmutableReader(root,head,{runtimeBytes:1,metadataBytes:1,executionBytes:1,outputBytes:1});
 const c=read(),m=c.current_rebind_migrations[0];assert.ok(m);assert.equal(c.current_rebind_migrations.length,1);
 assert.deepEqual(compatibleCurrentRebindCode(m.execution_commit,m.current_code,m.historical_code,reader),m.historical_code);
 for(const field of ['current_code','historical_code']){const changed=clone(m);changed[field][0].sha256='e'.repeat(64);
  assert.throws(()=>compatibleCurrentRebindCode(m.execution_commit,changed.current_code,changed.historical_code,reader),/Unknown historical/);}
 assert.throws(()=>compatibleCurrentRebindCode('f'.repeat(40),m.current_code,m.historical_code,reader),/Unknown historical/);
 c.current_rebind_migrations.push(clone(m));assert.throws(()=>validateSupportedProgrammeCatalogue(c),/Malformed/);
});
