import assert from 'node:assert/strict';
import fs from 'node:fs';
import {effectivePrimitiveGeometries,effectiveFootprintValue,footprintValueSha256,additiveReleaseFootprintDigest,loadedBaseFootprintSha256,verifyAdditiveLedgerSelection} from '../../../../src/effective-footprint.js';
import {conserveCurrentNativeRows} from './compose-retained.mjs';
import {nativeSourceDigest} from '../../../../src/native-source-digest.js';
const P='coordination/engineering/additive-native-gap-batch-20261008/',Q=P+'composition-v2/';
const ledger=JSON.parse(fs.readFileSync(Q+'composed-original-ledger.json')),registry=JSON.parse(fs.readFileSync(Q+'original-registry.json'));
const original=JSON.parse(fs.readFileSync(P+'batch-proposal-v1-run1/ledger-batch.json'));
const baseReference=original.base_reference,selected=ledger.rows.filter(r=>['assigned','zero-cell'].includes(r.disposition));
const features=[...new Set(selected.map(r=>r.target_id))].sort().map(id=>{
 const components=selected.filter(r=>r.target_id===id),row=components[0];
 return {id,pixelIndex:row.pixelIndex,geometry:row.base_geometry,additiveFootprint:{version:2,kind:'retained-base-plus-additions',
 baseline_release_sha256:baseReference.footprints_sha256,base_geometry_sha256:row.base_geometry_sha256,
 ledger_sha256:footprintValueSha256(ledger),authority_registry_sha256:footprintValueSha256(registry),components}};});
for(const f of features){assert.equal(effectivePrimitiveGeometries(f).length,f.additiveFootprint.components.length+1);assert.equal(effectiveFootprintValue(f).version,2);}
const expected=footprintValueSha256({domain:'worldatlas-effective-native-footprints:v2',base_reference:baseReference,
 authority_registry_sha256:footprintValueSha256(registry),ledger_sha256:footprintValueSha256(ledger),components:selected});
assert.equal(additiveReleaseFootprintDigest(baseReference,features),expected);
const pilotRoot='coordination/engineering/additive-native-gap-repair-20261008/add031-release-proposal-v3-run1/';
const patches=[JSON.parse(fs.readFileSync(pilotRoot+'patch-add031.json')),JSON.parse(fs.readFileSync(P+'batch-proposal-v1-run1/patch-batch.json'))];
const wanted=new Set(patches.flatMap(p=>p.rows.map(r=>r.y))),windows=new Map();
for(const path of [pilotRoot+'owner-window.json',P+'batch-proposal-v1-run1/owner-window.json'])for(const row of JSON.parse(fs.readFileSync(path)))if(wanted.has(row.y))windows.set(row.y,row.complete_owner_intervals);
const combined=conserveCurrentNativeRows({originalPatches:patches,currentRows:[...wanted].sort((a,b)=>a-b).map(y=>({y,runs:windows.get(y)})),size:262166});
const selectedLedger={...ledger,base_reference:baseReference,assigned_cells:combined.assigned_cells};
const selectedFeatures=structuredClone(features);for(const f of selectedFeatures)f.additiveFootprint.ledger_sha256=footprintValueSha256(selectedLedger);
const selectedPatch={version:2,kind:'unassigned-native-cells-v1',base_reference:baseReference,
 effective_reference:{...baseReference,id:'geography:additive:'+footprintValueSha256(selectedLedger),footprints_sha256:additiveReleaseFootprintDigest(baseReference,selectedFeatures)},
 authority_registry_sha256:footprintValueSha256(registry),ledger_sha256:footprintValueSha256(selectedLedger),rows:combined.rows};
assert.deepEqual(verifyAdditiveLedgerSelection(selectedLedger,selectedFeatures,selectedPatch),{selected_components:12,assigned_cells:141});
const missing=structuredClone(selectedFeatures);missing[0].additiveFootprint.components.pop();assert.throws(()=>verifyAdditiveLedgerSelection(selectedLedger,missing,selectedPatch));
const incompleteCurrent={...selectedLedger,current_targets:[]};assert.throws(()=>verifyAdditiveLedgerSelection(incompleteCurrent,selectedFeatures,selectedPatch));
const fixtureFeatures=structuredClone(features),fixtureBase={...baseReference,footprints_sha256:loadedBaseFootprintSha256(fixtureFeatures)};
for(const f of fixtureFeatures)f.additiveFootprint.baseline_release_sha256=fixtureBase.footprints_sha256;
const fixtureDigest=await nativeSourceDigest(fixtureFeatures,{additiveBaseReference:fixtureBase});
assert.equal(fixtureDigest.domain,'worldatlas-effective-native-footprints:v2');
assert.equal(fixtureDigest.sha256,additiveReleaseFootprintDigest(fixtureBase,fixtureFeatures));
await assert.rejects(()=>nativeSourceDigest(fixtureFeatures.slice(1),{additiveBaseReference:fixtureBase}));
// Consumer structure allows a separately bound current base without changing
// any complete original source row. This square is a fixture, not a v9 proof.
const current=structuredClone(features),changed=current.find(f=>f.pixelIndex===6757);
changed.geometry={type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,0]]]};changed.additiveFootprint.base_geometry_sha256=footprintValueSha256(changed.geometry);
assert.deepEqual(changed.additiveFootprint.components,features.find(f=>f.pixelIndex===6757).additiveFootprint.components);
assert.equal(effectivePrimitiveGeometries(changed)[0],changed.geometry);
const v1=JSON.parse(fs.readFileSync(P+'batch-proposal-v1-run1/features.json'));
const envelope=JSON.parse(fs.readFileSync(P+'batch-proposal-v1-run1/release-envelope.json'));
assert.equal(additiveReleaseFootprintDigest(baseReference,v1),envelope.additiveRelease.effective_reference.footprints_sha256);
let negatives=3;const rejects=mutate=>{const copy=structuredClone(features);mutate(copy);assert.throws(()=>additiveReleaseFootprintDigest(baseReference,copy));negatives++;};
rejects(a=>a[0].additiveFootprint.components[0].geometry.coordinates[0][0][0]+=1);
rejects(a=>a[0].additiveFootprint.components[0].target_id='foreign');
rejects(a=>a[0].additiveFootprint.components[0].pixelIndex++);
rejects(a=>a[0].additiveFootprint.components[0].authority_sha256='foreign');
rejects(a=>a[0].additiveFootprint.components[0].native_cells=false);
rejects(a=>a[0].additiveFootprint.components[0].base_geometry_sha256='0'.repeat(64));
rejects(a=>a[0].additiveFootprint.components.push(a[0].additiveFootprint.components[0]));
rejects(a=>a[0].additiveFootprint.baseline_release_sha256='0'.repeat(64));
rejects(a=>a[0].additiveFootprint.ledger_sha256='0'.repeat(64));
assert.throws(()=>additiveReleaseFootprintDigest(baseReference,[...features,v1[0]]));negatives++;
fs.writeFileSync(Q+'browser-v2-controls.json',JSON.stringify({kind:'complete-original-component-browser-v2-controls',
 original_components:selected.length,original_target_owners:features.length,negative_controls:negatives,legacy_digest_exact:true,
 effective_domain_sha256:expected,limits:['Whole original component representation and explicit digest controls; fixture current base is not an authenticated v9 rebind. No renderer/picker/native-patch V2 qualification or activation.']},null,2)+'\n');
console.log(JSON.stringify({components:selected.length,owners:features.length,negatives,legacy_digest_exact:true}));
