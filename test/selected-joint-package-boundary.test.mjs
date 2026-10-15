import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {inspectPackageExecutionInputs} from '../scripts/package-build.mjs';
import {loadPackageInputs, containsPackagePath} from '../scripts/package-inputs.mjs';
import * as cold from '../scripts/check-effective-geographic-regression.mjs';
import {compareSelectedCheckpointNative,compareEffectiveNativeRows} from '../scripts/selected-checkpoint-native.mjs';

const ROOT=process.cwd();
const COLD='scripts/check-effective-geographic-regression.mjs';
const NATIVE='scripts/selected-checkpoint-native.mjs';
const SHARED='coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint.mjs';
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

test('all ordinary package entries declare their complete current consumer closure',()=>{
 const definition=loadPackageInputs(ROOT);
 for(const kind of ['static','hosted','cloudflare']){
  const actual=inspectPackageExecutionInputs(ROOT,definition,kind);
  assert.deepEqual(actual.errors,[]);
  assert(actual.files.includes('scripts/package-current-additive.mjs'));
  assert(actual.files.includes('src/native-grid.js'));
  for(const name of [COLD,NATIVE,SHARED,'scripts/visible-gap-eligibility.mjs','scripts/native-ownership/validate-build-context-stage.mjs'])assert(!actual.files.includes(name),name);
  assert(actual.files.includes(`scripts/build-${kind}-inner.mjs`));
  assert.deepEqual(actual.files,[...new Set(actual.files)].sort());
  for(const name of actual.files)assert(containsPackagePath(definition.inputs,name),name);
 }
});

test('an undeclared import in the actual current consumer fails current-input preflight',t=>{
 const definition=loadPackageInputs(ROOT), actual=inspectPackageExecutionInputs(ROOT,definition,'static');
 assert.deepEqual(actual.errors,[]);
 const root=fs.mkdtempSync(path.join(ROOT,'.joint-package-boundary-'));
 t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 for(const name of actual.files){const target=path.join(root,name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.copyFileSync(path.join(ROOT,name),target,fs.constants.COPYFILE_EXCL);}
 const undeclared='coordination/undeclared-acceptance-probe.mjs';
 fs.mkdirSync(path.dirname(path.join(root,undeclared)),{recursive:true});
 fs.writeFileSync(path.join(root,undeclared),'export const current = true;\n',{flag:'wx'});
 fs.appendFileSync(path.join(root,'scripts/package-current-additive.mjs'),"\nawait import('../"+undeclared+"');\n");
 const rejected=inspectPackageExecutionInputs(root,definition,'static');
 assert(rejected.files.includes(undeclared));
 assert(rejected.errors.some(e=>e.kind==='execution-declaration'&&e.path===undeclared));
});
