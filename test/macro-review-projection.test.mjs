import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';import path from 'node:path';import os from 'node:os';import {createHash} from 'node:crypto';import {gzipSync,gunzipSync} from 'node:zlib';
import {stageLandCreations} from '../scripts/stage-land-creations.mjs';import {footprintHash} from '../scripts/check-prepared.mjs';
import {validateMacroReviewProjection,resolveProjectionGeometry,retainProjectionInputs} from '../scripts/prepare-macro-review-projection.mjs';
const units=[{id:'c',name:'C',level:'continent',parent_id:null},{id:'s',name:'S',level:'subcontinent',parent_id:'c'},{id:'r',name:'R',level:'region',parent_id:'s'},{id:'a',name:'A',level:'area',parent_id:'r'},{id:'p',name:'P',level:'province',parent_id:'a'}];
const pins={hierarchy_sha256:'a'.repeat(64),location_index_sha256:'b'.repeat(64),footprints_sha256:'c'.repeat(64)};
function fixture(){
 const hierarchy=units.map(row=>row.id==='r'?{...row,id:'new:r',name:'New R'}:row.id==='a'?{...row,parent_id:'new:r'}:{...row}),locations=[{id:'l',name:'L',parent_id:'p',owner:'Owner'}];
 const projection={version:1,kind:'current-membership-projection',semantic_complete:false,regional_interiors_approved:false,historical_claims_transferred:false,geometry_changes:0,current_pins:{...pins},counts:{locations:1,groups:5,continent:1,subcontinent:1,region:1,area:1,province:1},locations:[{...locations[0],parent_chain:['p','a','new:r','s','c'],status:'open',semantic_status:'open'}],groups:hierarchy.map(row=>({...row,member_location_ids:['l'],branch_semantic_status:'open'})),archived_predecessors:[{...units[2]}],crosswalks:[{retired_units:[{...units[2]}],group_changes:[{id:'r',before:{...units[2]},after:null},{id:'new:r',before:null,after:{...hierarchy[2]}}]}]};
 return {projection,hierarchy,locations,currentPins:{...pins},baselineHierarchy:units,baselineLocations:locations.map(row=>({...row}))};
}
test('current projection preserves identities and keeps source inspection separate from semantic approval',()=>{
 const result=validateMacroReviewProjection(fixture());assert.equal(result.validated,true);assert.equal(result.semantic_complete,false);assert.equal(result.projection_only,true);assert.equal(result.baseline_inspections_preserved,true);
});
test('source-backed projection cannot change timeline facts or invent geographic review completion',()=>{
 for(const change of [{semantic_complete:true},{historical_claims_transferred:true},{regional_interiors_approved:true},{geometry_changes:1}]){const input=fixture();Object.assign(input.projection,change);assert.throws(()=>validateMacroReviewProjection(input),/contract/);}
});
test('current pins and exact counts must describe the actual geography',()=>{
 let input=fixture();input.currentPins.hierarchy_sha256='d'.repeat(64);assert.throws(()=>validateMacroReviewProjection(input),/stale geographic pins/);
 input=fixture();input.projection.counts.region=81;assert.throws(()=>validateMacroReviewProjection(input),/counts differ/);
});
test('complete current chains cannot be reordered or silently assigned different parents',()=>{
 for(const change of [row=>row.parent_chain.reverse(),row=>row.parent_id='new:r',row=>row.name='Invented',row=>row.owner='Changed',row=>row.status='approved']){const input=fixture();change(input.projection.locations[0]);assert.throws(()=>validateMacroReviewProjection(input),/stale or unapproved/);}
});
test('every retired or created parent has exact original archive and explicit crosswalk',()=>{
 for(const change of [input=>input.projection.archived_predecessors[0].name='Rewritten original',input=>input.projection.archived_predecessors=[],input=>input.projection.crosswalks[0].retired_units=[],input=>input.projection.crosswalks[0].group_changes=[]]){const input=fixture();change(input);assert.throws(()=>validateMacroReviewProjection(input));}
});
test('location conservation and exact parent descendant membership remain exhaustive',()=>{
 let input=fixture();input.baselineLocations.push({id:'lost'});assert.throws(()=>validateMacroReviewProjection(input),/loses original/);
 input=fixture();input.projection.groups[0].member_location_ids=[];assert.throws(()=>validateMacroReviewProjection(input),/stale group membership/);
 input=fixture();input.projection.groups[0].branch_semantic_status='approved';assert.throws(()=>validateMacroReviewProjection(input),/semantic approval/);
});

const sha=b=>createHash('sha256').update(b).digest('hex'),put=(file,value)=>{fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,JSON.stringify(value));return sha(fs.readFileSync(file));};
function geometryFixture(t){
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-projection-geometry-'));t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));
 const polygon=x=>({type:'Polygon',coordinates:[[[x,0],[x+1,0],[x+1,1],[x,1],[x,0]]]}),feature=(id,x,parent='p')=>({type:'Feature',id,properties:{id,name:id,parent_id:parent,reference_owner:id==='new'?null:'Owner'},geometry:polygon(x)});
 const original=[feature('l',0)],replaced=[feature('l',.1)],created=feature('new',20,'new:p'),newUnits=units.concat([{id:'new:a',name:'Isolated area',level:'area',parent_id:'r',metadata:{source_url:'https://example.org/synthetic-island',basis:'Synthetic isolated geographic area'}},{id:'new:p',name:'Isolated province',level:'province',parent_id:'new:a',metadata:{source_url:'https://example.org/synthetic-island',basis:'Synthetic local island territory'}}]),afterFeatures=[...replaced,created];
 for(const [name,features,groups] of [['replacement',replaced,units],['after',afterFeatures,newUnits]]){put(dir+'/'+name+'/world-index.json',{parts:['geography/part.json']});put(dir+'/'+name+'/geography/part.json',{features});put(dir+'/'+name+'/hierarchy.json',groups);}
 const replacement={geometry_stage_validated:true,historical_claims_transferred:false,before_footprints_sha256:footprintHash(original),after_footprints_sha256:footprintHash(replaced),changed_ids:['l'],removed_ids:[],added_ids:[],reused_ids:[],archives:[{id:'l',feature:original[0]}],relationships:[{before_ids:['l'],after_ids:['l'],history_transfer:false}],source_evidence:[{url:'https://example.org/synthetic-original',source_sha256:'d'.repeat(64)}]};
 const receiptPin=put(dir+'/replacement-migration/migration-receipt.json',replacement);put(dir+'/replacement-migration/index.json',{history_transfer:false,before_footprints_sha256:replacement.before_footprints_sha256,after_footprints_sha256:replacement.after_footprints_sha256,files:{'migration-receipt.json':{sha256:receiptPin}}});
 const source={...created,id:'source-new'};put(dir+'/source.json',source);put(dir+'/proofs.json',[{location_id:'new',parent_chain:['new:p','new:a','r','s','c'],source:{path:'source.json',sha256:sha(fs.readFileSync(dir+'/source.json')),identity:source.id,url:'https://example.org/synthetic-island',license:'Synthetic test',attribution:'Synthetic test-only',supported_from:2026,supported_to:2027},identity_review:{status:'distinct-new-territory',evidence_url:'https://example.org/synthetic-name',rationale:'Synthetic absent land'}}]);stageLandCreations({before:dir+'/replacement',after:dir+'/after',proofs:dir+'/proofs.json',output:dir+'/creation-migration'});
 const creation=JSON.parse(fs.readFileSync(dir+'/creation-migration/migration-receipt.json')),aggregate={...replacement,after_footprints_sha256:footprintHash(afterFeatures),added_ids:['new'],creation_proofs:creation.creation_proofs.map(row=>({...row,source:{...row.source,path:'creation-migration/'+row.source.path}}))};put(dir+'/aggregate.json',aggregate);
 const descriptor={version:1,before_footprints_sha256:footprintHash(original),after_footprints_sha256:footprintHash(afterFeatures),manifests:['replacement-migration/index.json','creation-migration/index.json'].map(path=>({path,sha256:sha(fs.readFileSync(dir+'/'+path))})),metadata_receipts:[]};put(dir+'/geometry-proofs.json',descriptor);
 const before={features:original,units,proof:{...pins,footprints_sha256:footprintHash(original)}},after={features:afterFeatures,units:newUnits,proof:{...pins,footprints_sha256:footprintHash(afterFeatures)}};
 return {dir,before,after,descriptor,geometryProofs:dir+'/geometry-proofs.json',sourceReceipt:dir+'/aggregate.json'};
}
function geometryProjection(f,proof){
 const groups=new Map(f.after.units.map(row=>[row.id,row])),rows=f.after.features.map(feature=>{let parent=feature.properties.parent_id,parent_chain=[];while(parent){const g=groups.get(parent);parent_chain.push(parent);parent=g.parent_id;}return {id:feature.id,name:feature.properties.name,parent_id:feature.properties.parent_id,owner:feature.properties.reference_owner,parent_chain,status:'open',semantic_status:'open'};}),locations=rows.map(({parent_chain,status,semantic_status,...row})=>row);
 const hierarchy=f.after.units,projection={version:1,kind:'current-membership-projection',semantic_complete:false,regional_interiors_approved:false,historical_claims_transferred:false,geometry_changes:2,geometry_proof:proof,before_pins:f.before.proof,current_pins:f.after.proof,counts:{locations:2,groups:7,continent:1,subcontinent:1,region:1,area:2,province:2},locations:rows,groups:hierarchy.map(row=>({...row,member_location_ids:rows.filter(loc=>loc.parent_chain.includes(row.id)).map(loc=>loc.id),branch_semantic_status:'open'})),archived_predecessors:[],created_groups:hierarchy.filter(row=>row.id.startsWith('new:')),crosswalks:[]};
 return {projection,hierarchy,locations,currentPins:f.after.proof,baselineHierarchy:units,baselineLocations:[{id:'l',name:'l',parent_id:'p',owner:'Owner'}]};
}
test('source-backed projection resolves exact replacements and creations while all semantic branches remain open',async t=>{
 const f=geometryFixture(t),proof=await resolveProjectionGeometry(f);assert.deepEqual(proof.changed_ids,['l']);assert.deepEqual(proof.added_ids,['new']);assert.deepEqual(proof.created_group_ids,['new:a','new:p']);assert.equal(proof.archived_location_references[0].reference.name,'l');assert.equal(proof.source_assessments.locations.length,2);assert.equal(proof.source_assessments.groups.length,2);assert.ok(proof.source_assessments.locations.every(row=>!row.historical_attributes_assessed&&!row.regional_interior_approved));assert.equal(validateMacroReviewProjection(geometryProjection(f,proof)).validated,true);
});
test('projection preparation rejects altered source pins, wrong order and invented historical transfers',async t=>{
 const f=geometryFixture(t);
 for(const kind of ['pin','order','transfer','footprint']){const descriptor=structuredClone(f.descriptor),aggregate=JSON.parse(fs.readFileSync(f.sourceReceipt)),input={...f};if(kind==='pin')descriptor.manifests[1].sha256='0'.repeat(64);if(kind==='order')descriptor.manifests.reverse();if(kind==='transfer')aggregate.historical_claims_transferred=true;if(kind==='footprint')input.after={...f.after,proof:{...f.after.proof,footprints_sha256:'0'.repeat(64)}};put(f.geometryProofs,descriptor);put(f.sourceReceipt,aggregate);await assert.rejects(()=>resolveProjectionGeometry(input));}
});
test('projection validator exhausts added identities, retained archives and new source-assessed groups',async t=>{
 const f=geometryFixture(t),proof=await resolveProjectionGeometry(f);
 for(const kind of ['addition','order','archive','assessment','new-group','approved','source','count']){const input=geometryProjection(f,structuredClone(proof)),g=input.projection.geometry_proof;if(kind==='addition')g.added_ids=[];if(kind==='order')g.manifests.reverse();if(kind==='archive')g.archived_location_references[0].reference.name='Rewritten original';if(kind==='assessment')g.source_assessments.locations=[];if(kind==='new-group')g.created_group_ids.pop();if(kind==='approved')g.source_assessments.groups[0].semantic_status='approved';if(kind==='source')delete g.source_assessments.groups[0].source_url;if(kind==='count')input.projection.geometry_changes=1;assert.throws(()=>validateMacroReviewProjection(input),undefined,kind);}
});

test('later geometry projection preserves original inspection bytes and namespaces current predecessor snapshots',t=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-retained-projection-'));t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));
 const original=Buffer.from('{"source_inspection":true,"number":1.0}'),current=Buffer.from('{"current_projection":true,"number":2.0}'),archive='macro-foundation/retained-inspections/world-review.json.gz',compressed=gzipSync(original);
 fs.mkdirSync(path.dirname(dir+'/'+archive),{recursive:true});fs.writeFileSync(dir+'/'+archive,compressed);fs.writeFileSync(dir+'/world-review.json',current);
 const entry={archive_path:'data/'+archive,archive_sha256:sha(compressed),original_sha256:sha(original),compression:'gzip'},previous={baseline_files:{'data/world-review.json':entry}},files=new Map(),result=retainProjectionInputs({data:dir,sourcePaths:['world-review.json'],files,previousProjection:previous,predecessorKey:'a'.repeat(64)});
 assert.deepEqual(result.baselineFiles,previous.baseline_files);assert.equal(files.get(archive).equals(compressed),true);assert.equal(result.predecessorFiles['data/world-review.json'].original_sha256,sha(current));assert.equal(gunzipSync(files.get(result.predecessorFiles['data/world-review.json'].archive_path.replace(/^data\//,''))).equals(current),true);
 fs.appendFileSync(dir+'/'+archive,'changed');assert.throws(()=>retainProjectionInputs({data:dir,sourcePaths:[],files:new Map(),previousProjection:previous}),/Prior source inspection bytes changed/);
});
