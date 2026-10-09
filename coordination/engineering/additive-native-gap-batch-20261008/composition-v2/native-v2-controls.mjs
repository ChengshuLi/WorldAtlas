import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {applyAdditiveNativePatch,footprintValueSha256,additiveReleaseFootprintDigest} from '../../../../src/effective-footprint.js';
const Q='coordination/engineering/additive-native-gap-batch-20261008/composition-v2/';
const ledger=JSON.parse(fs.readFileSync(Q+'composed-original-ledger.json')),registry=JSON.parse(fs.readFileSync(Q+'original-registry.json'));
const original=JSON.parse(fs.readFileSync('coordination/engineering/additive-native-gap-batch-20261008/batch-proposal-v1-run1/ledger-batch.json'));
const selected=ledger.rows.filter(r=>['assigned','zero-cell'].includes(r.disposition)),features=[...new Set(selected.map(r=>r.target_id))].sort().map(id=>{
 const components=selected.filter(r=>r.target_id===id),row=components[0];return {id,pixelIndex:row.pixelIndex,geometry:row.base_geometry,
 additiveFootprint:{version:2,kind:'retained-base-plus-additions',baseline_release_sha256:original.base_reference.footprints_sha256,
 base_geometry_sha256:row.base_geometry_sha256,ledger_sha256:footprintValueSha256(ledger),authority_registry_sha256:footprintValueSha256(registry),components}};});
const mapping=features.map(f=>[f.pixelIndex,f.id]).sort((a,b)=>a[0]-b[0]);
const owner=features[0].pixelIndex,newOwner=features.at(-1).pixelIndex;
const rows=new Uint32Array(262166*2);rows[1]=1;for(let y=1;y<262166;y++)rows[y*2]=1;
const words=(start,end,id)=>[id%8192*524288+start,Math.floor(id/8192)*524288+end-1];
const base={version:2,method:'native-linear-evenodd-first-owner-v1',size:262166,coordinateBits:19,rows,runs:Uint32Array.from(words(0,2,owner)),
 geographic_release:original.base_reference.id,footprints_sha256:original.base_reference.footprints_sha256,hierarchy_sha256:original.base_reference.hierarchy_sha256,
 reference_owner_sha256:createHash('sha256').update(JSON.stringify(mapping)).digest('hex')};
const effective={...original.base_reference,id:'geography:additive:'+footprintValueSha256(ledger),footprints_sha256:additiveReleaseFootprintDigest(original.base_reference,features)};
const patch={version:2,kind:'unassigned-native-cells-v1',base_reference:original.base_reference,effective_reference:effective,
 ledger_sha256:footprintValueSha256(ledger),authority_registry_sha256:footprintValueSha256(registry),rows:[{y:0,runs:[[4,5,newOwner]]}]};
const options={baseReference:original.base_reference,effectiveReference:effective,features};
const result=applyAdditiveNativePatch(base,patch,options);assert.deepEqual([...result.runs],[...base.runs,...words(4,5,newOwner)]);
assert.equal(result.additive_added_cells,1);assert.equal(result.effective_footprint_domain,'worldatlas-effective-native-footprints:v2');
assert.equal(result.additive_authority_registry_sha256,patch.authority_registry_sha256);assert(!Object.hasOwn(result,'additive_rule_sha256'));
assert.equal(applyAdditiveNativePatch(result,patch,options),result);
let negatives=0;const reject=(mutate)=>{const p=structuredClone(patch);mutate(p);assert.throws(()=>applyAdditiveNativePatch(base,p,options));negatives++;};
reject(p=>p.authority_registry_sha256='0'.repeat(64));reject(p=>p.rows[0].runs=[[1,2,newOwner]]);
reject(p=>p.rows[0].runs[0][2]=999);reject(p=>p.rows.push(p.rows[0]));reject(p=>p.rule_sha256='0'.repeat(64));
reject(p=>p.base_reference.footprints_sha256='0'.repeat(64));
const forged={...result};assert.throws(()=>applyAdditiveNativePatch(forged,patch,options));negatives++;
result.runs[0]++;assert.throws(()=>applyAdditiveNativePatch(result,patch,options));negatives++;
fs.writeFileSync(Q+'native-v2-controls.json',JSON.stringify({kind:'actual-native-overlay-v2-fixture-controls',positives:2,negative_controls:negatives,
 limits:['Actual native overlay module with stock-size two-interval fixture and complete original component descriptors; not whole-world/v9 applicability or patch qualification.']},null,2)+'\n');
console.log(JSON.stringify({positives:2,negatives}));
