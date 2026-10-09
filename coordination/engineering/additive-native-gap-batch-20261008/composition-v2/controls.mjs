import assert from 'node:assert/strict';
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {composeRetainedLedgers,conserveCurrentNativeRows} from './compose-retained.mjs';
import {valueSha,valueBytes,normaliseRetainedRepairLedger} from '../../selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const git='/Library/Developer/CommandLineTools/usr/bin/git';
const executionHead=execFileSync(git,['rev-parse','HEAD'],{encoding:'utf8'}).trim();
const head='381d8733e2f105ac16e764c20bb800c40cafea3a';
const sha=b=>createHash('sha256').update(b).digest('hex');
const P='coordination/engineering/',out=P+'additive-native-gap-batch-20261008/composition-v2/';
const specs=[{name:'pilot-add031',root:P+'additive-native-gap-repair-20261008/add031-release-proposal-v3-run1/',ledger:'ledger-add031.json',patch:'patch-add031.json'},
 {name:'alaska-thirteen',root:P+'additive-native-gap-batch-20261008/batch-proposal-v1-run1/',ledger:'ledger-batch.json',patch:'patch-batch.json'}];
const paths=specs.flatMap(s=>[s.root+s.ledger,s.root+s.patch,s.root+'owner-window.json',...['preimage','source-custody'].map(k=>P+'selected-geography-effective-prevention-20261009/policy-provenance/'+s.name+'-'+k+'.json')]);
const descriptors=new Map(paths.map(path=>{const row=execFileSync(git,['ls-tree','-l',head,'--',path],{encoding:'utf8'}).trim().split(/\s+/);assert.equal(row[0],'100644');const bytes=Number(row[3]);assert(bytes>0&&bytes<=33554432);return [path,{commit:head,path,mode:row[0],git_blob_oid:row[2],bytes}];}));
// Bounded metadata controls: complete union admitted before any Git blob opens.
const phase=fs.statSync(process.execPath).size+fs.statSync(git).size+1048576+[...descriptors.values()].reduce((n,p)=>n+2*p.bytes,0);
assert(phase<268435456&&descriptors.size<=512);
const read=path=>{const p=descriptors.get(path),body=execFileSync(git,['show',head+':'+path],{maxBuffer:33554432});assert.equal(body.length,p.bytes);p.sha256=sha(body);return JSON.parse(body);};
const members=specs.map(s=>({ledger:read(s.root+s.ledger),patch:read(s.root+s.patch),window:read(s.root+'owner-window.json'),
 preimage:read(P+'selected-geography-effective-prevention-20261009/policy-provenance/'+s.name+'-preimage.json'),
 custody:read(P+'selected-geography-effective-prevention-20261009/policy-provenance/'+s.name+'-source-custody.json'),spec:s}));
const entries=members.map(m=>{assert.equal(valueSha(m.preimage),m.ledger.rule_sha256);
 const entry={policy_id:'retained-source-literal-additions',policy_version:1,rule_sha256:m.ledger.rule_sha256,
 rule_preimage:descriptors.get(P+'selected-geography-effective-prevention-20261009/policy-provenance/'+m.spec.name+'-preimage.json'),
 source_authority:descriptors.get(P+'selected-geography-effective-prevention-20261009/policy-provenance/'+m.spec.name+'-source-custody.json')};return {...entry,authority_sha256:valueSha(entry)};}).sort((a,b)=>a.authority_sha256.localeCompare(b.authority_sha256));
const registry={version:1,kind:'retained-rule-authority-registry-v1',entries};
const composed=composeRetainedLedgers(members.map(m=>m.ledger),registry),normalized=normaliseRetainedRepairLedger(composed,registry);
assert.equal(composed.rows.length,20);assert.equal(normalized.rows.size,12);
for(const member of members)for(const old of member.ledger.rows){const row=composed.rows.find(r=>r.component_id===old.component_id);const {authority_sha256,rule_sha256,...literal}=row;assert.deepEqual(literal,old);assert.equal(rule_sha256,member.ledger.rule_sha256);}
let negative=0;const refuses=fn=>{assert.throws(fn);negative++;};
refuses(()=>composeRetainedLedgers([members[0].ledger,members[0].ledger],registry));
const badParent=structuredClone(members[1].ledger);badParent.parent_inventory.sha256='0'.repeat(64);refuses(()=>composeRetainedLedgers([members[0].ledger,badParent],registry));
const badRule=structuredClone(registry);badRule.entries[0].rule_sha256='0'.repeat(64);refuses(()=>composeRetainedLedgers(members.map(m=>m.ledger),badRule));
const badGeometry=structuredClone(members[0].ledger);badGeometry.rows.find(r=>r.disposition==='assigned').geometry.coordinates[0][0][0]+=1;refuses(()=>composeRetainedLedgers([badGeometry,members[1].ledger],registry));
const patches=members.map(m=>m.patch),wanted=new Set(patches.flatMap(p=>p.rows.map(r=>r.y))),map=new Map();
for(const m of members)for(const row of m.window)if(wanted.has(row.y)){if(map.has(row.y))assert.deepEqual(map.get(row.y),row.complete_owner_intervals);map.set(row.y,row.complete_owner_intervals);}
const currentRows=[...wanted].sort((a,b)=>a-b).map(y=>{assert(map.has(y),'Original whole owner window omitted requested row');return {y,runs:map.get(y)};});
const conserved=conserveCurrentNativeRows({originalPatches:patches,currentRows,size:262166});assert.equal(conserved.assigned_cells,141);
refuses(()=>conserveCurrentNativeRows({originalPatches:patches,currentRows:currentRows.slice(1),size:262166}));
const occupied=structuredClone(currentRows),first=conserved.rows.find(r=>r.runs.length);occupied.find(r=>r.y===first.y).runs.push([...first.runs[0]]);occupied.find(r=>r.y===first.y).runs.sort((a,b)=>a[0]-b[0]);refuses(()=>conserveCurrentNativeRows({originalPatches:patches,currentRows:occupied,size:262166}));
const conflict=structuredClone(patches);const row=conflict[0].rows.find(r=>r.runs.length);row.runs[0][2]+=1;conflict.push(patches[0]);refuses(()=>conserveCurrentNativeRows({originalPatches:conflict,currentRows,size:262166}));
refuses(()=>conserveCurrentNativeRows({originalPatches:patches,currentRows:[...currentRows,currentRows[0]],size:262166}));
const result={version:1,kind:'complete-original-additive-composition-controls',head,execution_head:executionHead,complete_phase_bytes:phase,input_pins:[...descriptors.values()],
 complete_scope:20,supported_primitives:12,original_cells:141,negative_controls:negative,
 limits:['Metadata composition and original-v8 row conservation only. No current-v9 rebind, source requalification, activation, or whole-world computation.']};
fs.writeFileSync(out+'original-registry.json',valueBytes(registry));fs.writeFileSync(out+'composed-original-ledger.json',valueBytes(composed));fs.writeFileSync(out+'controls.json',valueBytes(result));
console.log(JSON.stringify({scope:20,primitives:12,cells:141,negatives:negative,complete_phase_bytes:phase}));
