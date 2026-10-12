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

test('sixteen accepted producer records and the original471 migration remain unchanged',()=>{
 const c=read();assert.equal(valueSha(c.programs.slice(0,16)),'df048b1a191966ba76a4bea47695f6abb5e3cc6440195664dc012e077a8628e9');
 assert.equal(valueSha(c.current_rebind_migrations[0]),'0d23b26bc7a1730c100921d25524b938498bb37ab231fb3f2a4efe162507845b');
});
test('only finite exact complete migrations succeed and nearby changed vectors refuse',()=>{
 const head=git('rev-parse','HEAD').toString().trim(),reader=new ImmutableReader(root,head,{runtimeBytes:1,metadataBytes:1,executionBytes:1,outputBytes:1});
 const c=read();assert.ok(c.current_rebind_migrations.length>0&&c.current_rebind_migrations.length<=512);
 for(const m of c.current_rebind_migrations){
  assert.deepEqual(compatibleCurrentRebindCode(m.execution_commit,m.current_code,m.historical_code,reader),m.historical_code);
  for(const field of ['current_code','historical_code']){const changed=clone(m);changed[field][0].sha256='e'.repeat(64);
   assert.throws(()=>compatibleCurrentRebindCode(m.execution_commit,changed.current_code,changed.historical_code,reader),/Unknown historical/);}
  assert.throws(()=>compatibleCurrentRebindCode('f'.repeat(40),m.current_code,m.historical_code,reader),/Unknown historical/);
 }
 c.current_rebind_migrations.push(clone(c.current_rebind_migrations[0]));assert.throws(()=>validateSupportedProgrammeCatalogue(c),/Malformed|Ambiguous/);
});

test('current reader adoption preserves all accepted programmes and both earlier migrations',()=>{
 const c=read();
 assert.equal(valueSha(c.programs.slice(0,17)),'f98ce117470918303d67fdcd0392acca35a508908c5ac9db8e15757104003c08');
 assert.equal(valueSha(c.current_rebind_migrations.slice(0,2)),'1b2dc6750f4cd57af263288541b3987b2f5818394c9f1970142c4d1a8b46933e');
});

test('allocator preregistration preserves all nineteen programmes and five earlier migrations',()=>{
 const c=read();
 assert.equal(valueSha(c.programs.slice(0,19)),'436b2e83c9fb4f7bf5b9e408383a5405b36a5b2434bed823e3d952a5921204fb');
 assert.equal(valueSha(c.current_rebind_migrations.slice(0,5)),'8282c68f153fc9459a3d2955ea429e4afa035c21b248f46d3ffe65e59ec06913');
});

test('reviewed allocator admits only the two exact complete retained-consumer vectors',()=>{
 // All three complete vectors were derived from frozen Git bodies at these
 // execution commits and independently reviewed allocator head 7ddc81bc722b4fc16fdeb2674f1cd89d489f595f.
 // Keep literal identities without downloading unrelated history during CI.
 const expected=[
  ['85ca24519d87bb1d62a86d5cb142006e206cb2b8','11487b4d1ad7c12f2d22c6c324d136da555c82cd6c962178767d672cdf0ded1a'],
  ['40d792b2c67b18098c00cd71bce3cfd6a8e63a0b','0e1976f823dcdaf3f843a760ca9f9aa866073d8ae5ecebd67f7588579dcc36d7']
 ];
 const head=git('rev-parse','HEAD').toString().trim();
 const reader=new ImmutableReader(root,head,{runtimeBytes:1,metadataBytes:1,executionBytes:1,outputBytes:1});
 const migrations=read().current_rebind_migrations.slice(5,7);assert.equal(migrations.length,2);
 for(const [index,m]of migrations.entries()){
  assert.equal(m.execution_commit,expected[index][0]);
  assert.equal(valueSha(m.historical_code),expected[index][1]);
  assert.equal(valueSha(m.current_code),'1f616649e45b736ee23c1397f933bcd6c9f73a59b05130a387c48573ed82b2a4');
  assert.equal(m.independent_review_comment,6119154199);
  assert.deepEqual(m.current_code.map(p=>p.path),CURRENT_REBIND_CODE);
  assert.deepEqual(m.historical_code.map(p=>p.path),CURRENT_REBIND_CODE);
  assert.deepEqual(compatibleCurrentRebindCode(m.execution_commit,m.current_code,m.historical_code,reader),m.historical_code);
  assert.throws(()=>compatibleCurrentRebindCode(expected[1-index][0],m.current_code,m.historical_code,reader),/Unknown historical/);
  // Authority comes from the committed trusted catalogue, not a caller's own
  // vector or a candidate-only registration. Missing authority still refuses.
  assert.throws(()=>compatibleCurrentRebindCode(m.execution_commit,m.current_code,m.historical_code),/Unknown historical/);
  for(const field of ['current_code','historical_code']){
   for(const member of ['scripts/local-workspace.mjs','src/native-grid.js']){
    for(const property of ['bytes','sha256']){
     const changed=clone(m),descriptor=changed[field].find(p=>p.path===member);assert.ok(descriptor);
     descriptor[property]=property==='bytes'?descriptor.bytes+1:sha('unreviewed '+member);
     assert.throws(()=>compatibleCurrentRebindCode(m.execution_commit,changed.current_code,changed.historical_code,reader),/Unknown historical/);
    }
   }
   const partial=clone(m);partial[field].splice(26,1);
   assert.throws(()=>compatibleCurrentRebindCode(m.execution_commit,partial.current_code,partial.historical_code,reader),/Incomplete current\/historical/);
   const duplicate=clone(m);duplicate[field][26]=clone(duplicate[field][25]);
   assert.throws(()=>compatibleCurrentRebindCode(m.execution_commit,duplicate.current_code,duplicate.historical_code,reader),/Incomplete current\/historical/);
  }
 }
});
