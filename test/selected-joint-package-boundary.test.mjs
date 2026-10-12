import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {inspectPackageExecutionInputs, validatePackageExecutionRoles} from '../scripts/package-build.mjs';
import {loadPackageInputs} from '../scripts/package-inputs.mjs';
import {ACCEPTED_CHECKPOINT_CODE} from '../scripts/accepted-selected-checkpoint.mjs';
import * as cold from '../scripts/check-effective-geographic-regression.mjs';
import {compareSelectedCheckpointNative} from '../scripts/selected-checkpoint-native.mjs';

const ROOT=process.cwd();
const COLD='scripts/check-effective-geographic-regression.mjs';
const NATIVE='scripts/selected-checkpoint-native.mjs';
const SHARED='coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint.mjs';
const PREFIX='coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/';
const ROLES=PREFIX+'qualified-artifacts/application-consumer-code.json';
const sha=body=>createHash('sha256').update(body).digest('hex');

test('joint native extraction preserves the exact cold checker and every moved numerical body',()=>{
 assert.equal(sha(fs.readFileSync(COLD)),'5aa156ef010e0bfb14b88286a1c82231f6e4a7749c8063142082feb84e721cda');
 const source=fs.readFileSync(NATIVE,'utf8'), start=source.indexOf('// Numerical consumers of complete row projections.');
 assert(start>0);
 assert.equal(sha(source.slice(start)),'226438eae159af1aca0848431d1a509485bad2bf2798dfa05ecc1b18af88060e');
 assert.equal(cold.compareSelectedCheckpointNative,undefined);
 assert.equal(typeof compareSelectedCheckpointNative,'function');
});

test('all actual package entries retain their original complete role roster',()=>{
 const definition=loadPackageInputs(ROOT), roles=JSON.parse(fs.readFileSync(ROLES));
 assert.equal(sha(fs.readFileSync(ROLES)),'f62d4053a3f81a498fa8b5ac66723683ce064867f35aab6d5eb8cd4b6948c624');
 for(const kind of ['static','hosted','cloudflare']){
  const actual=inspectPackageExecutionInputs(ROOT,definition,kind);
  assert.deepEqual(actual.errors,[]);
  assert(actual.files.includes(COLD));
  assert(!actual.files.includes(NATIVE));assert(!actual.files.includes(SHARED));
  assert.equal(validatePackageExecutionRoles(actual.files,roles,`scripts/build-${kind}-inner.mjs`),true);
 }
});

test('a literal joint import in the cold checker still fails actual declaration and exact-role preflight',t=>{
 const definition=loadPackageInputs(ROOT), actual=inspectPackageExecutionInputs(ROOT,definition,'static');
 assert.deepEqual(actual.errors,[]);
 const root=fs.mkdtempSync(path.join(ROOT,'.joint-package-boundary-'));
 t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const inputs=new Set([...actual.files,NATIVE,SHARED,...ACCEPTED_CHECKPOINT_CODE,'data/native-context-migration/manifest.json',
  PREFIX+'context-stage-v9.json',PREFIX+'qualified-artifacts/consumption-certificate.json',ROLES]);
 for(const name of inputs){const target=path.join(root,name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.copyFileSync(path.join(ROOT,name),target,fs.constants.COPYFILE_EXCL);}
 fs.appendFileSync(path.join(root,COLD),"\nawait import('./selected-checkpoint-native.mjs');\n");
 const rejected=inspectPackageExecutionInputs(root,definition,'static');
 assert(rejected.files.includes(NATIVE)&&rejected.files.includes(SHARED));
 for(const name of [NATIVE,SHARED])assert(rejected.errors.some(e=>e.kind==='execution-declaration'&&e.path===name));
 assert(rejected.errors.some(e=>e.kind==='execution-inputs'&&e.detail==='Complete actual execution role closure required'));
});
