// Correct only the documented object-key-order false refusal. No operator rerun.
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import {createHash} from 'node:crypto';
import {assemblyProducts} from '../supervise-selected-assembly-linux.mjs';
const base='coordination/engineering/melanesia363-additive-delivery-20261010/ukraine-original-batch-20261010/';
const op=base+'selected-assembly-001/',out=base+'selected-release-001/';
const raw=n=>fs.readFileSync(n),sha=b=>createHash('sha256').update(b).digest('hex'),r=JSON.parse(raw(op+'receipt.json'));
assert.equal(r.qualified,false);assert.equal(r.refusal,'Assembly qualification summary differs');assert.deepEqual(r.exit,{code:0,signal:null});assert.deepEqual(r.owned_processes_remaining,[]);assert.deepEqual(r.termination_events,[]);assert.deepEqual(r.pre_use,r.post_use);
assert(r.elapsed_seconds<=1200&&r.rss_cap_bytes===1073741824&&r.wall_deadline_seconds===1200);
assert(r.peak_sampled_group_rss_bytes+r.peak_supervisor_rss_bytes<=r.rss_cap_bytes&&r.conservative_lifetime_and_supervisor_bound_bytes<=r.rss_cap_bytes);
assert.equal(sha(raw(op+'issued-parameters.json')),r.parameters_sha256);
assert(raw(op+'stderr.txt').length<=40960);
const product=assemblyProducts(out,raw(op+'stdout.txt'),r.execution_commit);
const names=[...['receipt.json','samples.json','stdout.txt','stderr.txt','issued-parameters.json'].map(n=>op+n),...['ledger','patch','envelope','qualification'].map(n=>out+n+'.json')];
const pins=names.map(p=>{const b=raw(p);return {path:p,bytes:b.length,sha256:sha(b)}});assert(pins.reduce((n,p)=>n+p.bytes,0)<=12*1048576);
const report={version:1,kind:'assembly-object-order-correction-readback-v1',operator_rerun:false,original_wrapper_qualified:false,original_refusal:r.refusal,output_validation:'passed',execution_commit:r.execution_commit,corrected_checker:{path:'coordination/engineering/melanesia363-additive-delivery-20261010/supervise-selected-assembly-linux.mjs',sha256:sha(raw('coordination/engineering/melanesia363-additive-delivery-20261010/supervise-selected-assembly-linux.mjs'))},inputs:pins,complete_reader_phase_bytes:product.complete_reader_phase_bytes,assigned_cells:product.qualification.assigned_cells,components:product.qualification.components,elapsed_seconds:r.elapsed_seconds,lifetime_plus_supervisor_bytes:r.conservative_lifetime_and_supervisor_bound_bytes,limits:['Original false refusal and measurements remain unchanged. This is corrected parsed-value output validation, not a newly executed operating receipt.','Current-rebind certificate and normal independent selected native/continuous gates remain authoritative.']};
fs.writeFileSync(op+'output-order-readback.json',JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({output_validation:report.output_validation,operator_rerun:false,complete_reader_phase_bytes:report.complete_reader_phase_bytes,assigned_cells:report.assigned_cells,components:report.components}));
