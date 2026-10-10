// Narrow actual-reader ownership test. Whole encoded rowtable custody only;
// no decompression, geography/native operator, selected acquisition or authority.
import fs from 'node:fs';import path from 'node:path';import {fileURLToPath} from 'node:url';import vm from 'node:vm';import assert from 'node:assert/strict';import {createHash} from 'node:crypto';import {execFileSync} from 'node:child_process';
const repo=path.resolve(fileURLToPath(new URL('../../../',import.meta.url))),version=execFileSync('git',['-C',repo,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
const sourcePath=path.join(repo,'coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs');
const sha=b=>createHash('sha256').update(b).digest('hex'),source=fs.readFileSync(sourcePath,'utf8');const expectedSourceSha=sha(source);assert.equal(source,execFileSync('git',['-C',repo,'show',version+':coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs'],{encoding:'utf8',maxBuffer:1024*1024}));
const checker=execFileSync('git',['-C',repo,'show',version+':scripts/check-effective-geographic-regression.mjs'],{maxBuffer:1024*1024,encoding:'utf8'});
const start=checker.indexOf('export class ImmutableReader {'),stop=checker.indexOf('\n}\n',start)+3;assert(start>=0&&stop>start);
const FILE=33554432,PHASE=268435456,OUTPUT=4194304,demand=(v,m)=>{if(!v)throw Error(m);};
const Reader=vm.runInNewContext(checker.slice(start,stop).replace('export class','class')+'\nImmutableReader',{fs,process,execFileSync,FILE,PHASE,OUTPUT,demand,sha,commit:v=>typeof v==='string'&&/^[a-f0-9]{40}$/.test(v),safe:p=>typeof p==='string'&&!p.startsWith('/')&&!p.split('/').some(x=>!x||x==='.'||x==='..')});
const freeze=vm.runInNewContext(source.match(/const freeze=v=>\{[^\n]+/)[0]+'\nfreeze');
const expression=source.match(/input_inventory:([^\n]+?),result,/)[1];
const reader=new Reader(repo,version),name='coordination/engineering/additive-native-gap-batch-20261008/current-v8/rows-0.bin.gz',raw=reader.read(name),wholeSha=sha(raw),record=reader.inventory.get(version+':'+name);
// Reproduce the original bug separately before judging the corrected issuer.
const legacyReader=new Reader(repo,version);legacyReader.read(name,{expected:wholeSha});freeze({input_inventory:[...legacyReader.inventory.values()]});assert.throws(()=>legacyReader.read(name,{expected:wholeSha}),/read only|readonly|Cannot assign/i);
const proof=freeze(vm.runInNewContext('({input_inventory:'+expression+'})',{reader})),proofBytes=JSON.stringify(proof);
assert(Object.isFrozen(proof)&&Object.isFrozen(proof.input_inventory)&&Object.isFrozen(proof.input_inventory[0]));assert(!Object.isFrozen(record));assert.notEqual(proof.input_inventory[0],record);
assert.deepEqual({...proof.input_inventory[0]},{...record});assert.equal(sha(reader.read(name,{expected:wholeSha})),wholeSha);assert.equal(JSON.stringify(proof),proofBytes);
let negative=0;assert.throws(()=>{proof.input_inventory[0].sha256='f'.repeat(64);},TypeError);negative++;
assert.throws(()=>reader.read(name,{expected:'f'.repeat(64)}),/Whole immutable input differs/);negative++;
assert.throws(()=>reader.read('missing-rowtable.bin.gz',{expected:wholeSha}),/Require whole ordinary Git input/);negative++;
const driftReader=new Reader(repo,version);driftReader.read(name,{expected:wholeSha});driftReader.inventory.get(version+':'+name).bytes++;assert.throws(()=>driftReader.read(name,{expected:wholeSha}),/Immutable descriptor drift/);negative++;
const identityReader=new Reader(repo,version);identityReader.read(name,{expected:wholeSha});identityReader.inventory.get(version+':'+name).git_blob_oid='f'.repeat(40);assert.throws(()=>identityReader.read(name,{expected:wholeSha}),/Immutable descriptor drift/);negative++;
record.sha256='e'.repeat(64);assert.equal(sha(reader.read(name,{expected:wholeSha})),wholeSha);assert.equal(record.sha256,wholeSha);assert.equal(JSON.stringify(proof),proofBytes);assert.equal(sha(fs.readFileSync(sourcePath)),expectedSourceSha);
console.log(JSON.stringify({source:{path:sourcePath,bytes:Buffer.byteLength(source),sha256:expectedSourceSha},reader_source:{commit:version,path:'scripts/check-effective-geographic-regression.mjs',sha256:sha(checker)},complete_rowtable:{commit:version,path:name,bytes:raw.length,sha256:wholeSha,mode:record.mode,git_blob_oid:record.git_blob_oid},positive:3,negative,original_live_record_freeze_bug_reproduced:true,returned_copy_value_equal:true,returned_copy_frozen:true,internal_reader_record_mutable:true,genuine_whole_rowtable_reread_passed:true,frozen_proof_unchanged:true,operators_executed:0,limits:'Literal copied-inventory expression/freeze and actual ImmutableReader class; encoded rowtable whole Git reads only. No native/source qualification or selected acquisition.'}));
