import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {inspectPackageExecutionInputs} from '../scripts/package-build.mjs';
import {loadPackageInputs, containsPackagePath} from '../scripts/package-inputs.mjs';
import {ACCEPTED_CHECKPOINT_CODE} from '../scripts/accepted-selected-checkpoint.mjs';
import * as cold from '../scripts/check-effective-geographic-regression.mjs';
import {compareSelectedCheckpointNative,compareEffectiveNativeRows} from '../scripts/selected-checkpoint-native.mjs';

const ROOT=process.cwd();
const COLD='scripts/check-effective-geographic-regression.mjs';
const NATIVE='scripts/selected-checkpoint-native.mjs';
const SHARED='coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint.mjs';
const PREFIX='coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/';
const sha=body=>createHash('sha256').update(body).digest('hex');

test('native row derivation stays unchanged while interval conservation remains in the joint consumer',()=>{
 const source=fs.readFileSync(NATIVE,'utf8'), start=source.indexOf('// Numerical consumers of complete row projections.');
 assert(start>0);
 // Pin the original unchanged row/owner/delta primitives. The following
 // interval comparator lost only obsolete receipt-size limits.
 assert.equal(sha(source.slice(start,source.indexOf('export function compareEffectiveNativeRows'))),'46573049a336d665a80a1e4478c32a498c7ea1cb46f263a8b82467f035c43cc1');
 const owners=[{id:'original-owner'},{id:'other-owner'}];
 assert.deepEqual(compareEffectiveNativeRows([{y:1,runs:[[0,4,1]]}],[{y:1,runs:[[0,2,1],[2,3,2]]}],{size:8,ownersBefore:owners,ownersAfter:owners,rows:[1]}),{checked_rows:1,lost_or_reassigned_cells:2,intervals:[{row:1,start:2,end:3,previous_owner:'original-owner',candidate_owner:'other-owner'},{row:1,start:3,end:4,previous_owner:'original-owner',candidate_owner:null}]});
 assert.equal(typeof cold.screenNativeGapCandidates,'function');
 assert.equal(typeof cold.repairVisibilityWitnesses,'function');
 assert.equal(cold.compareSelectedCheckpointNative,undefined);
 assert.equal(typeof compareSelectedCheckpointNative,'function');
});

test('all actual package entries discover complete declared current closures without joint-only modules',()=>{
 const definition=loadPackageInputs(ROOT);
 for(const kind of ['static','hosted','cloudflare']){
  const actual=inspectPackageExecutionInputs(ROOT,definition,kind);
  assert.deepEqual(actual.errors,[]);
  assert(actual.files.includes(COLD));
  assert(actual.files.includes('src/native-grid.js'));
  assert(!actual.files.includes('scripts/visible-gap-eligibility.mjs'));
  assert(!actual.files.includes(NATIVE));assert(!actual.files.includes(SHARED));
  assert(actual.files.includes(`scripts/build-${kind}-inner.mjs`));
  assert.deepEqual(actual.files,[...new Set(actual.files)].sort());
  for(const name of actual.files)assert(containsPackagePath(definition.inputs,name),name);
 }
});

test('a literal joint import in the cold checker still fails actual current-input declaration preflight',t=>{
 const definition=loadPackageInputs(ROOT), actual=inspectPackageExecutionInputs(ROOT,definition,'static');
 assert.deepEqual(actual.errors,[]);
 const root=fs.mkdtempSync(path.join(ROOT,'.joint-package-boundary-'));
 t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const inputs=new Set([...actual.files,NATIVE,SHARED,...ACCEPTED_CHECKPOINT_CODE,'data/native-context-migration/manifest.json',
  PREFIX+'context-stage-v9.json',PREFIX+'qualified-artifacts/consumption-certificate.json']);
 for(const name of inputs){const target=path.join(root,name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.copyFileSync(path.join(ROOT,name),target,fs.constants.COPYFILE_EXCL);}
 fs.appendFileSync(path.join(root,COLD),"\nawait import('./selected-checkpoint-native.mjs');\n");
 const rejected=inspectPackageExecutionInputs(root,definition,'static');
 assert(rejected.files.includes(NATIVE)&&rejected.files.includes(SHARED));
 for(const name of [NATIVE,SHARED])assert(rejected.errors.some(e=>e.kind==='execution-declaration'&&e.path===name));
});
