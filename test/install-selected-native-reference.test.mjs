import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {selectedNativeReference,composeEvidence,applyInstall,retainHistoricalMacroReview,validateMetadataStages} from '../scripts/install-macro-reference.mjs';
import {preparedEvidenceJSON} from '../src/prepared-evidence.js';

const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const fixtureDirectory=fileURLToPath(new URL('../coordination/engineering/vietnam-selected-native-reference-install-20261016/test-fixtures/',import.meta.url));
function nativeFixture(run){
 const base=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'atlas-selected-reference-')));
 try{
  execFileSync('git',['init','-q',base]);
  execFileSync('git',['-C',base,'index-pack','--stdin'],{input:fs.readFileSync(path.join(fixtureDirectory,'registered-proof-objects.pack'))});
  const selectionRaw=fs.readFileSync(path.join(fixtureDirectory,'selection.json')),selection=JSON.parse(selectionRaw),manifestRaw=fs.readFileSync(path.join(fixtureDirectory,'native-manifest.json')),manifest=JSON.parse(manifestRaw);
  const data=path.join(base,'data'),manifestFile=path.join(base,selection.manifest_path);fs.mkdirSync(data);fs.mkdirSync(path.dirname(manifestFile),{recursive:true});fs.writeFileSync(path.join(data,'ownership-selection.json'),selectionRaw);fs.writeFileSync(manifestFile,manifestRaw);
  const release={id:manifest.geographic_release,footprints_sha256:manifest.footprints_sha256,hierarchy_sha256:manifest.hierarchy_sha256},before={proof:{footprints_sha256:manifest.footprints_sha256,hierarchy_sha256:manifest.hierarchy_sha256}};
  return run({base,data,selection,selectionRaw,manifest,manifestRaw,manifestFile,release,before});
 }finally{fs.rmSync(base,{recursive:true,force:true});}
}

test('registered selected native reference authenticates without a legacy grid or rewriting scientific inputs',()=>nativeFixture(({base,data,selectionRaw,manifestRaw,manifestFile,release,before})=>{
 const result=selectedNativeReference(data,before,release,base);
 assert.equal(result.verification.role,'reviewed-exhaustive-native-rule-comparison');
 assert.equal(result.new_native_or_publication_approval,false);
 assert.equal(result.original_native_bytes_unchanged,true);
 assert.equal(result.canonical_metadata_commit_required,true);
 assert.equal(fs.existsSync(path.join(data,'canonical-grid')),false);
 assert.deepEqual(fs.readFileSync(path.join(data,'ownership-selection.json')),selectionRaw);
 assert.deepEqual(fs.readFileSync(manifestFile),manifestRaw);
}));

test('a forged checksum or coherently repinned unregistered native manifest cannot select the historical-independent route',()=>nativeFixture(({base,data,selection,manifest,manifestFile,release,before})=>{
 const selector=path.join(data,'ownership-selection.json');
 fs.writeFileSync(selector,JSON.stringify({...selection,sha256:'f'.repeat(64)}));
 assert.throws(()=>selectedNativeReference(data,before,release,base),/manifest checksum/);
 const modified=Buffer.from(JSON.stringify({...manifest,scientific_approval:true}));fs.writeFileSync(manifestFile,modified);fs.writeFileSync(selector,JSON.stringify({...selection,sha256:sha(modified)}));
 assert.throws(()=>selectedNativeReference(data,before,release,base),/reviewed exhaustive comparison registration/);
}));

test('selected native metadata still requires the actual complete baseline reference and safe paths',()=>nativeFixture(({base,data,selection,release,before})=>{
 assert.throws(()=>selectedNativeReference(data,{proof:{...before.proof,hierarchy_sha256:'f'.repeat(64)}},release,base),/complete installer baseline/);
 assert.throws(()=>selectedNativeReference(data,before,{...release,id:'geography:wrong'},base),/complete installer baseline/);
 fs.writeFileSync(path.join(data,'ownership-selection.json'),JSON.stringify({...selection,manifest_path:'data/../manifest.json'}));
 assert.throws(()=>selectedNativeReference(data,before,release,base),/Unsafe current native reference path/);
}));

test('absence of a selection retains the original strict legacy installation path',()=>{
 const data=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-no-selected-reference-'));
 try{assert.equal(selectedNativeReference(data,{proof:{}},{},data),null);}finally{fs.rmSync(data,{recursive:true,force:true});}
});

function evidenceFixture(run){
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-native-evidence-'));
 try{
  fs.writeFileSync(path.join(directory,'source.json'),'original historical payload');
  const geometry={type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,0]]]},feature={id:'retained',geometry},footprint=sha(preparedEvidenceJSON([['retained',geometry]]));
  const prior={footprints_sha256:'a'.repeat(64),hierarchy_sha256:'b'.repeat(64),location_index_sha256:'c'.repeat(64)},before={proof:{...prior,footprints_sha256:'d'.repeat(64)},locations:new Map([['retained',feature]]),members:new Map(),groups:new Map()},after={...before,proof:{...before.proof,hierarchy_sha256:'e'.repeat(64)}};
  const receipt={version:1,original_geography:{original:'retained'},revalidated_geography:prior,historical_membership_assigned:false,source_product_files:[{path:'source.json',sha256:sha('original historical payload')}],entities:[{entity_id:'retained',kind:'location',original_footprint_sha256:footprint,revalidated_footprint_sha256:footprint,result:'identical-footprint'}],records:4,prior_revalidation:{archive_path:'data/retained-historical-archive-not-materialized.gz',sha256:'f'.repeat(64)}};
  const continuation={version:1,issue:1520,kind:'prepared-evidence',receipt_sha256:'1'.repeat(64),predecessor_footprints_sha256:prior.footprints_sha256,successor_footprints_sha256:before.proof.footprints_sha256,history_transfer:'none',payloads_and_original_inputs_unchanged:true,new_factual_import:false};
  return run({directory,receipt,before,after,continuation});
 }finally{fs.rmSync(directory,{recursive:true,force:true});}
}

test('an existing physical association continuation composes actual subject equality without relabeling the old receipt',()=>evidenceFixture(({directory,receipt,before,after,continuation})=>{
 const original=structuredClone(receipt),result=composeEvidence(receipt,before,after,directory,{associationContinuation:continuation});
 assert.deepEqual(receipt,original);
 assert.deepEqual(result.revalidated_geography,after.proof);
 assert.deepEqual(result.entities,receipt.entities);
 assert.deepEqual(result.original_geography,receipt.original_geography);
 assert.deepEqual(result.source_product_files,receipt.source_product_files);
 assert.deepEqual(result.projection.physical_association_continuation,continuation);
 assert.deepEqual(result.projection.current_before_geography,before.proof);
 assert.equal(result.historical_membership_assigned,false);
 assert.throws(()=>composeEvidence(receipt,before,after,directory),/Previous evidence projection is stale/);
}));

test('continuation metadata cannot authorize changed subject territory, changed payloads or a false chronology',()=>evidenceFixture(({directory,receipt,before,after,continuation})=>{
 for(const change of [{history_transfer:'copied'},{predecessor_footprints_sha256:'2'.repeat(64)},{payloads_and_original_inputs_unchanged:false}])
  assert.throws(()=>composeEvidence(receipt,before,after,directory,{associationContinuation:{...continuation,...change}}),/Previous evidence projection is stale/);
 const original=before.locations.get('retained');after={...after,locations:new Map([['retained',{...original,geometry:{type:'Polygon',coordinates:[]}}]])};
 assert.throws(()=>composeEvidence(receipt,before,after,directory,{associationContinuation:continuation}),/Historical evidence territory changed/);
 fs.writeFileSync(path.join(directory,'source.json'),'changed historical payload');
 assert.throws(()=>composeEvidence(receipt,before,before,directory,{associationContinuation:continuation}),/Original evidence source bytes changed/);
}));

function nativeInstallFixture(run){return nativeFixture(({base,data,release,before,...rest})=>{
 const target=path.join(data,'parent.json'),certificate=path.join(data,'macro-certificate.json'),stage=path.join(base,'stage');fs.mkdirSync(path.join(stage,'after'),{recursive:true});
 fs.writeFileSync(path.join(data,'world-index.json'),'unchanged index bytes\n');fs.writeFileSync(target,'original parent metadata\n');fs.writeFileSync(certificate,'historical pending certificate\n');fs.writeFileSync(path.join(stage,'after','parent.json'),'reviewed parent metadata\n');
 const native=selectedNativeReference(data,before,release,base),report={native_reference:native,before_geography:before.proof,immutable_grid_parts:[],preserved:{'world-index.json':sha(fs.readFileSync(path.join(data,'world-index.json'))),'ownership-selection.json':sha(fs.readFileSync(path.join(data,'ownership-selection.json'))),'macro-certificate.json':sha(fs.readFileSync(certificate))},originals:{'parent.json':sha(fs.readFileSync(target))},writes:{'parent.json':sha(fs.readFileSync(path.join(stage,'after','parent.json')))}};
 const prepared={data,stage,repository:base,report,validation_sha256:sha(JSON.stringify(report))};return run({base,data,target,certificate,stage,prepared,...rest});
});}

test('selected-native install rolls back an actual failed write and retains historical certificate bytes',()=>nativeInstallFixture(({data,target,certificate,prepared})=>{
 const prior=fs.readFileSync(target),historical=fs.readFileSync(certificate);
 assert.throws(()=>applyInstall(prepared,{expectedValidation:prepared.validation_sha256,failAfter:1}),/Injected metadata install failure/);
 assert.deepEqual(fs.readFileSync(target),prior);assert.deepEqual(fs.readFileSync(certificate),historical);assert.equal(fs.existsSync(path.join(data,'.macro-reference-install.lock')),false);
 const result=applyInstall(prepared,{expectedValidation:prepared.validation_sha256});assert.equal(result.applied,true);assert.equal(fs.readFileSync(target,'utf8'),'reviewed parent metadata\n');assert.deepEqual(fs.readFileSync(certificate),historical);
}));

test('selected-native apply rejects changed selector, historical certificate and staged metadata before writing',()=>nativeInstallFixture(({data,target,certificate,stage,prepared})=>{
 const prior=fs.readFileSync(target),selector=path.join(data,'ownership-selection.json'),selectionRaw=fs.readFileSync(selector),historical=fs.readFileSync(certificate);
 assert.throws(()=>applyInstall(prepared,{expectedValidation:'f'.repeat(64)}),/exact reviewed validation hash/);
 fs.writeFileSync(selector,JSON.stringify({...JSON.parse(selectionRaw),sha256:'f'.repeat(64)}));assert.throws(()=>applyInstall(prepared,{expectedValidation:prepared.validation_sha256}),/manifest checksum/);fs.writeFileSync(selector,selectionRaw);
 fs.writeFileSync(certificate,'forged current approval');assert.throws(()=>applyInstall(prepared,{expectedValidation:prepared.validation_sha256}),/Historical bytes changed/);fs.writeFileSync(certificate,historical);
 const index=path.join(data,'world-index.json'),indexRaw=fs.readFileSync(index);fs.writeFileSync(index,'changed unchanged-index input');assert.throws(()=>applyInstall(prepared,{expectedValidation:prepared.validation_sha256}),/Historical bytes changed/);fs.writeFileSync(index,indexRaw);
 fs.writeFileSync(path.join(stage,'after','parent.json'),'unreviewed metadata');assert.throws(()=>applyInstall(prepared,{expectedValidation:prepared.validation_sha256}),/Staged install bytes changed/);
 assert.deepEqual(fs.readFileSync(target),prior);assert.equal(fs.existsSync(path.join(data,'.macro-reference-install.lock')),false);
}));

test('retaining historical macro review preserves pending status and exact files without old inspection bodies',()=>{
 const data=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'atlas-historical-macro-')));
 try{const files={'macro-foundation/macro-certificate.json':'{"status":"reference-compatible-pending-publication","reference_compatibility_verified":false}\n','macro-foundation/current-membership-projection.json.gz':'literal old projection bytes','macro-foundation/world-review-projection.json':'{"current_pins":{"footprints_sha256":"old"},"semantic_complete":false}\n','macro-foundation/current-membership-inventory.json.gz':'current inventory','research-geography-gate.json':'{"ready_for_location_attributes":false}\n'};
 for(const [name,raw]of Object.entries(files)){fs.mkdirSync(path.dirname(path.join(data,name)),{recursive:true});fs.writeFileSync(path.join(data,name),raw);}
 const retained=retainHistoricalMacroReview(data);assert.equal(retained.status.current_macro_compatibility_asserted,false);assert.equal(retained.status.membership_review_projection_updated,false);assert.equal(retained.status.new_approval_created,false);assert.equal(retained.status.published,false);
 assert.equal(Object.hasOwn(retained.files,'macro-foundation/current-membership-inventory.json.gz'),false);assert.equal(Object.keys(retained.files).length,4);
 for(const [name,raw]of Object.entries(files)){assert.equal(fs.readFileSync(path.join(data,name),'utf8'),raw);if(name!=='macro-foundation/current-membership-inventory.json.gz')assert.equal(retained.files[name],sha(raw));}
 assert.equal(fs.existsSync(path.join(data,'macro-foundation/retained-inspections')),false);
 }finally{fs.rmSync(data,{recursive:true,force:true});}
});

function receiptedParentFixture(run){
 const directory=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-receipted-parent-'));
 try{const units=[{id:'c',name:'C',level:'continent',parent_id:null},{id:'s',name:'S',level:'subcontinent',parent_id:'c'},{id:'r',name:'R',level:'region',parent_id:'s'},{id:'a',name:'A',level:'area',parent_id:'r'},{id:'old',name:'Old',level:'province',parent_id:'a',metadata:{child_count:2}},{id:'new',name:'New',level:'province',parent_id:'a',metadata:{child_count:1}}];
 const correction=(id,from,to)=>({id,action:'reparent',current_name:id,current_parent_id:from,new_parent_id:to,rationale:'Literal inspected source correspondence',evidence:[{url:'https://example.org/literal-source',title:'Literal source',inspected_fact:'This exact member belongs to this parent.'}]});
 const features=['member','retained','other'].map((id,i)=>({type:'Feature',id,properties:{id,name:id,parent_id:i===2?'new':'old',metadata:{source_id:'retained:'+id,framework_match:{id:'original fallback'},reference_corrections:[]}},geometry:{type:'Polygon',coordinates:[[[0,0],[1,0],[1,1],[0,0]]]}}));
 const afterFeatures=structuredClone(features);afterFeatures[0].properties.parent_id='new';afterFeatures[0].properties.metadata.reference_corrections.push(correction('member','old','new'));
 const afterUnits=structuredClone(units);afterUnits[4].metadata.child_count=1;afterUnits[5].metadata.child_count=2;
 const geo=(rows,unitRows,hierarchy)=>({units:unitRows,groups:new Map(unitRows.map(row=>[row.id,row])),features:rows,locations:new Map(rows.map(row=>[row.id,row])),proof:{hierarchy_sha256:hierarchy,footprints_sha256:'unchanged footprints'}});
 const before=geo(features,units,'before'),after=geo(afterFeatures,afterUnits,'after');
 const receipt={before_sha256:'before',after_sha256:'after',footprints_sha256_before:'unchanged footprints',footprints_sha256_after:'unchanged footprints',reference_only:true,historical_claims_transferred:false,summary:{geometry_changes:0},relationships:[],before_units:units,retired_units:[],group_changes:[4,5].map(index=>({id:units[index].id,before:units[index],after:afterUnits[index]})),changed_location_properties:[{location_id:'member',before_properties:features[0].properties,after_properties:structuredClone(afterFeatures[0].properties)}],source_evidence:[{url:'https://example.org/literal-source',source_sha256:'a'.repeat(64)}]};
 const file=path.join(directory,'receipt.json');fs.writeFileSync(file,JSON.stringify(receipt));return run({before,after,file,correction});
 }finally{fs.rmSync(directory,{recursive:true,force:true});}
}

test('complete candidate properties must equal the authenticated receipt, including literal correction history and source',()=>{
 receiptedParentFixture(({before,after,file})=>validateMetadataStages(before,after,[file],{mode:'reference-correction'}));
 for(const mutate of [
  row=>row.metadata.reference_corrections[0].rationale='Substituted rationale for the same parent',
  row=>row.metadata.reference_corrections[0].evidence[0].url='https://example.org/substituted-source',
  row=>row.metadata.reference_corrections.pop(),
 ])receiptedParentFixture(({before,after,file})=>{mutate(after.features[0].properties);assert.equal(after.features[0].properties.parent_id,'new');assert.throws(()=>validateMetadataStages(before,after,[file],{mode:'reference-correction'}),/Unreceipted location properties/);});
});

test('an unchanged member cannot acquire unreceipted history while retaining its parent',()=>receiptedParentFixture(({before,after,file,correction})=>{
 const row=after.features[1].properties;row.metadata.reference_corrections.push(correction('retained','old','new'),correction('retained','new','old'));assert.equal(row.parent_id,'old');
 assert.throws(()=>validateMetadataStages(before,after,[file],{mode:'reference-correction'}),/Unreceipted location properties/);
}));
