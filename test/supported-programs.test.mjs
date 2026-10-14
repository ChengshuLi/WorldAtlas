import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {ImmutableReader} from '../scripts/check-effective-geographic-regression.mjs';
import {validateSupportedProgrammeCatalogue,readSupportedProgrammeCatalogue,readSupportedProgrammeAuthority,matchSupportedProgramme,valueSha} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const root=fileURLToPath(new URL('../',import.meta.url));
const name='coordination/engineering/selected-geography-effective-prevention-20261009/supported-programs.json';
const helper='coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const read=()=>JSON.parse(fs.readFileSync(path.join(root,name)));
const clone=structuredClone;
const request=p=>({preimageVersion:p.preimage_version,sourceProfile:p.source_profile,sourceCode:p.source_executed_code,nativeCode:p.native_executed_code});
const requestFromMatch=({source,native})=>({...request(source),nativeCode:native.native_executed_code});
const sha=b=>createHash('sha256').update(b).digest('hex');
const git=(...args)=>execFileSync('git',['-c','core.hooksPath=/dev/null','-C',root,...args],{env:{...process.env,GIT_NO_LAZY_FETCH:'1'}});

test('all twelve literal legacy programme records remain unchanged',()=>{
 // Independent migration review authenticated these exact twelve records
 // against180042b1. Keep their canonical identity without adding a historical
 // Git download to every future test invocation.
 const legacy=read().programs.slice(0,12);assert.equal(legacy.length,12);
 assert.equal(valueSha(legacy),'3bc7b51bf033cffe9ff2c35443fbebbeda2553102c3c00912d62ba5677a90edd');
 for(const p of legacy)assert.deepEqual(request(p),requestFromMatch(matchSupportedProgramme(read(),request(p))));
});
test('catalogue-only additions do not change any existing method descriptor',()=>{
 const c=read(),before=clone(c.programs),extra=clone(c.programs.at(-1));
 extra.source_profile='synthetic-other-profile';c.programs.push(extra);
 validateSupportedProgrammeCatalogue(c);assert.deepEqual(c.programs.slice(0,before.length),before);
 for(const p of before)assert.deepEqual(request(p),requestFromMatch(matchSupportedProgramme(c,request(p))));
 assert.notEqual(sha(JSON.stringify(c)),sha(JSON.stringify(read())));
});
test('changed caller, helper and other method bytes refuse independently',()=>{
 for(const changedPath of ['scripts/additive-gap-repair.mjs',helper,'package.json']){
  const q=request(clone(read().programs.at(-1))),body=q.nativeCode.find(p=>p.path===changedPath);assert.ok(body);body.sha256='f'.repeat(64);
  assert.throws(()=>matchSupportedProgramme(read(),q),/Unknown\/ambiguous original/);
 }
});
test('missing, malformed, duplicate and foreign catalogue records refuse',()=>{
 assert.throws(()=>validateSupportedProgrammeCatalogue(null),/Malformed/);
 for(const mutate of [c=>c.programs.push(clone(c.programs[0])),c=>c.programs[0].source_executed_code.push(clone(c.programs[0].source_executed_code[0])),c=>c.programs[0].accepted_head='latest',c=>c.programs[0].unexpected=true,c=>c.programs[0].native_executed_code[0].bytes=33554433]){
  const c=read();mutate(c);assert.throws(()=>validateSupportedProgrammeCatalogue(c));
 }
 const q=request(clone(read().programs[0]));q.sourceProfile='candidate-only';assert.throws(()=>matchSupportedProgramme(read(),q),/Unknown\/ambiguous original/);
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
 assert.deepEqual(Object.keys(proof).sort(),['catalogue','native','source']);
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


test('native checkpoint preregistration preserves every prior programme and migration',()=>{
 const c=read();
 assert.equal(valueSha(c.programs.slice(0,19)),'436b2e83c9fb4f7bf5b9e408383a5405b36a5b2434bed823e3d952a5921204fb');
 assert.equal(valueSha(c.current_rebind_migrations.slice(0,7)),'0d8b3270702433ee1158add45771b2e95466519c64ea65a91a88ea80e59be9b2');
 const p=c.programs[19];assert.ok(p);
 assert.equal(p.accepted_head,'392b1cda6d529f13f8e9d5fc86efe8dc436386a3');assert.equal(p.independent_review_comment,6120928599);
 assert.equal(valueSha(p.source_executed_code),'997be89cc71a802b318b427b925da37cfd4126d15b2f23d1937f3eaf79a7c6f7');
 assert.deepEqual(p.native_executed_code,p.source_executed_code);
 assert.deepEqual(request(p),requestFromMatch(matchSupportedProgramme(c,request(p))));
 for(const changedPath of ['scripts/check-effective-geographic-regression.mjs','src/native-grid.js']){
  const q=request(clone(p)),body=q.nativeCode.find(row=>row.path===changedPath);assert.ok(body);body.bytes++;
  assert.throws(()=>matchSupportedProgramme(c,q),/Unknown\/ambiguous original/);
 }
});


test('approved SOURCE000 and fresh accepted NATIVE compose without a registered pair',()=>{
 const c=read(),source=c.programs.find(p=>p.accepted_head.startsWith('f8c37b5'));
 const native=c.programs.find(p=>p.accepted_head==='37811b29f5227b2a54ae64e0e9e4be06f3e8499c');
 assert.ok(source);assert.ok(native);
 const q={...request(source),nativeCode:native.native_executed_code};
 assert.equal(c.programs.some(p=>valueSha(request(p))===valueSha(q)),false);
 const matched=matchSupportedProgramme(c,q);
 assert.deepEqual(requestFromMatch(matched),q);
 assert.ok(c.programs.includes(matched.source));assert.ok(c.programs.includes(matched.native));
 // Multiple accepted records for the identical SOURCE are evidence of the same
 // method, not ambiguity that demands another pair registration.
 assert.ok(c.programs.filter(p=>valueSha(p.source_executed_code)===valueSha(q.sourceCode)).length>1);
 for(const field of ['sourceCode','nativeCode'])for(const mutate of [
  rows=>rows[0].sha256='e'.repeat(64),rows=>rows[0].bytes++,rows=>rows.pop(),rows=>rows.push(clone(rows[0]))]){
  const unknown=clone(q);mutate(unknown[field]);
  assert.throws(()=>matchSupportedProgramme(c,unknown),/Unknown\/ambiguous original/);
 }
});

test('independent admission cannot borrow a closure from another profile or preimage version',()=>{
 const c=read(),original=c.programs[0],q=request(original);
 for(const key of ['source_profile','preimage_version']){
  const isolated=clone(c);isolated.programs=[clone(original),clone(original)];
  isolated.programs[0].source_executed_code[0].sha256='d'.repeat(64);
  isolated.programs[1][key]=key==='source_profile'?'foreign-profile':original.preimage_version===2?3:2;
  assert.throws(()=>matchSupportedProgramme(isolated,q),/Unknown\/ambiguous original/);
 }
});
