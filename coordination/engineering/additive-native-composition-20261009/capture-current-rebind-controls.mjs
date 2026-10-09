// Actual exported producer boundary controls. No cold source/native acquisition.
import assert from 'node:assert/strict';import fs from 'node:fs';import os from 'node:os';import path from 'node:path';
import {ImmutableReader} from '../../../scripts/check-effective-geographic-regression.mjs';
import {all} from '../additive-native-gap-batch-20261008/composition-v2/current-rebind-controls.mjs';
import {fixtureIssuedPlan} from '../additive-native-gap-batch-20261008/composition-v2/execution-custody-fixture.mjs';
import {valueBytes} from '../selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
import {prepareCurrentRebindDestination,validateCurrentRebindPlan,captureCurrentRebindProducts} from './capture-current-rebind.mjs';
const root=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'rebind-producer-boundary-')));fs.mkdirSync(path.join(root,'.cache'));
const originalLedger=JSON.parse(fs.readFileSync('coordination/engineering/additive-native-gap-batch-20261008/composition-v2/composed-original-ledger.json'));
const plan=fixtureIssuedPlan(all.request);plan.limits.output_bytes=4194304;
const context={executionCommit:all.request.execution_commit,baseSelection:all.baseSelection,registry:all.registry,originalRows:all.originalRows,executedCode:all.expectedCode};
assert.equal(validateCurrentRebindPlan(plan,context),plan);
const prepared=prepareCurrentRebindDestination(root,path.join(root,'.cache','fresh'));
let bodyOpens=0,negatives=0;const open=fs.openSync;fs.openSync=(...args)=>{bodyOpens++;return open(...args);};
const reject=(fn,re)=>{const start=bodyOpens;assert.throws(fn,re);assert.equal(bodyOpens,start);negatives++;};
try{
 reject(()=>prepareCurrentRebindDestination(root,path.join(root,'.cache')),/fresh owned/);
 reject(()=>prepareCurrentRebindDestination(root,path.join(root,'outside')),/fresh owned/);
 for(const mutate of [p=>p.limits.complete_phase_bytes++,p=>p.limits.rss_bytes++,p=>p.original_rows_sha256='f'.repeat(64),p=>p.executed_code.pop()]){const p=structuredClone(plan);mutate(p);reject(()=>validateCurrentRebindPlan(p,context),/differs|bounds/);}
 const reader=Object.create(ImmutableReader.prototype),snapshot={reader,selection:all.baseSelection};
 const input={destination:prepared,snapshot,plan,registry:all.registry,originalLedger,executionCommit:all.request.execution_commit,executedCode:all.expectedCode,executionPreUse:all.request.execution};
 reject(()=>captureCurrentRebindProducts({...input,destination:{...prepared}}),/prepared owned/);
 reject(()=>captureCurrentRebindProducts(input),/authenticated selected snapshot/);
 const wrong=structuredClone(plan);wrong.original_rows_sha256='f'.repeat(64);
 reject(()=>captureCurrentRebindProducts({...input,plan:wrong}),/planned source\/method/);
}finally{fs.openSync=open;fs.rmSync(root,{recursive:true,force:true});}
fs.writeFileSync('coordination/engineering/additive-native-composition-20261009/capture-current-rebind-controls.json',valueBytes({version:1,positives:2,negatives,source_body_opens:bodyOpens,limits:['Actual exported plan/destination/producer entry, tiny ordinary destination and explicit forged snapshot. No positive cold producer/source/native acquisition, runtime or operating qualification.']}));
console.log(JSON.stringify({positives:2,negatives,source_body_opens:bodyOpens}));
