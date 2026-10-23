import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {gzipSync} from 'node:zlib';
import {prepareReferenceMetadataProjection} from '../scripts/selected-reference-metadata.mjs';
import {footprintHash} from '../scripts/check-prepared.mjs';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {selectedNativeReference,composeEvidence,applyInstall,retainHistoricalMacroReview,validateMetadataStages} from '../scripts/install-macro-reference.mjs';
import {preparedEvidenceJSON} from '../src/prepared-evidence.js';
import {staticModuleClosure} from './helpers/static-module-closure.mjs';

const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const fixtureDirectory=fileURLToPath(new URL('./fixtures/selected-native-reference/',import.meta.url));
// Only eager module imports are discovered. Synthetic registrations and
// all non-module scientific/data operands below remain explicit fixture roles.
const installerSources=staticModuleClosure(fileURLToPath(new URL('../',import.meta.url)),['scripts/install-macro-reference.mjs']);
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

function secondInstallTarget({data,stage,prepared}){
 const name='later.json',target=path.join(data,name),raw='original later metadata\n',next='reviewed later metadata\n';
 fs.writeFileSync(target,raw);fs.writeFileSync(path.join(stage,'after',name),next);prepared.report.originals[name]=sha(raw);prepared.report.writes[name]=sha(next);prepared.validation_sha256=sha(JSON.stringify(prepared.report));
 return target;
}

test('all temporary destinations reject existing files and live or dangling symlinks before any replacement',()=>{
 for(const kind of ['file','live-symlink','dangling-symlink'])nativeInstallFixture(fixture=>{
  const {base,data,stage,target,prepared}=fixture,later=secondInstallTarget(fixture),temporary=later+'.macro-tmp',sentinel=path.join(base,'unrelated-sentinel'),prior=fs.readFileSync(target),laterPrior=fs.readFileSync(later);
  fs.writeFileSync(sentinel,'unrelated original bytes\n');const sentinelPrior=fs.readFileSync(sentinel);
  if(kind==='file')fs.writeFileSync(temporary,'existing temporary bytes\n');else fs.symlinkSync(kind==='live-symlink'?sentinel:path.join(base,'missing-sentinel'),temporary);
  const temporaryPrior=kind==='file'?fs.readFileSync(temporary):fs.readlinkSync(temporary),stagePrior=fs.readdirSync(stage);
  assert.throws(()=>applyInstall(prepared,{expectedValidation:prepared.validation_sha256}),/temporary destination already exists/);
  assert.deepEqual(fs.readFileSync(target),prior);assert.deepEqual(fs.readFileSync(later),laterPrior);assert.deepEqual(fs.readFileSync(sentinel),sentinelPrior);
  assert.deepEqual(kind==='file'?fs.readFileSync(temporary):fs.readlinkSync(temporary),temporaryPrior);
  assert.deepEqual(fs.readdirSync(stage),stagePrior);assert.equal(fs.existsSync(path.join(data,'.macro-reference-install.lock')),false);assert.equal(fs.existsSync(target+'.macro-tmp'),false);
 });
});

test('a temporary collision after admission preserves the unowned file and rolls back prior replacements',()=>nativeInstallFixture(fixture=>{
 const {target,prepared,data}=fixture,later=secondInstallTarget(fixture),temporary=later+'.macro-tmp',prior=fs.readFileSync(target),laterPrior=fs.readFileSync(later),open=fs.openSync;
 try{fs.openSync=function(file,flags,...args){if(file===temporary&&flags==='wx')fs.writeFileSync(temporary,'concurrent unowned bytes\n');return open.call(this,file,flags,...args);};
  assert.throws(()=>applyInstall(prepared,{expectedValidation:prepared.validation_sha256}),/EEXIST/);
 }finally{fs.openSync=open;}
 assert.equal(fs.readFileSync(temporary,'utf8'),'concurrent unowned bytes\n');assert.deepEqual(fs.readFileSync(target),prior);assert.deepEqual(fs.readFileSync(later),laterPrior);
 assert.equal(fs.existsSync(target+'.macro-tmp'),false);assert.equal(fs.existsSync(path.join(data,'.macro-reference-install.lock')),false);
}));

test('a failed write cleans only its exclusively created temporary and restores originals',()=>nativeInstallFixture(({target,prepared,data})=>{
 const prior=fs.readFileSync(target),open=fs.openSync,write=fs.writeFileSync;let temporaryFD;
 try{fs.openSync=function(file,flags,...args){const fd=open.call(this,file,flags,...args);if(file===target+'.macro-tmp')temporaryFD=fd;return fd;};
  fs.writeFileSync=function(file,...args){if(file===temporaryFD)throw Error('Injected temporary write failure');return write.call(this,file,...args);};
  assert.throws(()=>applyInstall(prepared,{expectedValidation:prepared.validation_sha256}),/Injected temporary write failure/);
 }finally{fs.openSync=open;fs.writeFileSync=write;}
 assert.deepEqual(fs.readFileSync(target),prior);assert.equal(fs.existsSync(target+'.macro-tmp'),false);assert.equal(fs.existsSync(path.join(data,'.macro-reference-install.lock')),false);
}));

test('installation refuses symlinked targets and parent directories without changing outside files',()=>{
 for(const kind of ['target','parent'])nativeInstallFixture(({base,data,stage,target,prepared})=>{
  const outside=path.join(base,'outside');fs.mkdirSync(outside);const sentinel=path.join(outside,'parent.json');fs.writeFileSync(sentinel,'outside original bytes\n');const prior=fs.readFileSync(sentinel);
  if(kind==='target'){fs.unlinkSync(target);fs.symlinkSync(sentinel,target);}else{
   fs.mkdirSync(path.join(stage,'after','nested'));fs.writeFileSync(path.join(stage,'after','nested/parent.json'),'replacement');fs.symlinkSync(outside,path.join(data,'nested'));
   prepared.report.originals['nested/parent.json']=sha(prior);prepared.report.writes['nested/parent.json']=sha('replacement');prepared.validation_sha256=sha(JSON.stringify(prepared.report));
  }
  assert.throws(()=>applyInstall(prepared,{expectedValidation:prepared.validation_sha256}),/ordinary files and directories/);
  assert.deepEqual(fs.readFileSync(sentinel),prior);assert.equal(fs.existsSync(path.join(data,'.macro-reference-install.lock')),false);
 });
});

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

// Private synthetic registration exercises the real installer, not geographic
// qualification. All executable bodies are copied unchanged from this candidate.
async function aliasInstallerFixture(t,{referenceVersion=3}={}){
 const repo=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'atlas-alias-install-')));t.after(()=>fs.rmSync(repo,{recursive:true,force:true}));
 const git=(...args)=>execFileSync('git',['-C',repo,...args],{stdio:['ignore','pipe','pipe']}).toString().trim();git('init');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid');
 const write=(name,value)=>{const raw=Buffer.isBuffer(value)?value:Buffer.from(JSON.stringify(value));fs.mkdirSync(path.dirname(path.join(repo,name)),{recursive:true});fs.writeFileSync(path.join(repo,name),raw);return raw;};
 const commit=()=>{git('add','.');git('commit','-m','Synthetic reference alias fixture');return git('rev-parse','HEAD');};
 const read=p=>execFileSync('git',['-C',repo,'show',p.commit+':'+p.path],{maxBuffer:32*1024*1024});
 const pin=(name,version)=>{const raw=read({path:name,commit:version}),[mode,,oid]=git('ls-tree',version,'--',name).split(/[ \t]/);return {commit:version,path:name,mode,git_blob_oid:oid,bytes:raw.length,sha256:sha(raw)};};
 for(const name of installerSources)write(name,fs.readFileSync(new URL('../'+name,import.meta.url)));
 write('package.json',{type:'module'});
 const units=[],features=[],owners=[];
 for(let i=0;i<6;i++){
  for(const [j,level]of ['continent','subcontinent','region','area','province'].entries())units.push({id:level+i,name:level+i,level,parent_id:j?['continent','subcontinent','region','area'][j-1]+i:null});
  features.push({type:'Feature',id:'L'+i,properties:{id:'L'+i,name:'Location '+i,parent_id:'province'+i,reference_owner:'Recorded winner',metadata:{reference_version:i===0?referenceVersion:i===5?4:3,reference_polity:'Stale alias',reference_owner_id:'owner:Q1',reference_owner_evidence:{winner:{owner_id:'owner:Q1',name:'Recorded winner',share:.75}},semantic_review:{status:'open'}}},geometry:{type:'Polygon',coordinates:[[[i,0],[i+1,0],[i+1,1],[i,0]]]}});
  owners.push({id:'L'+i,index:i+1,province_id:'province'+i,province_index:i+1});
 }
 const source='geography/fixture.json',index={parts:[source]},originalHierarchy=write('data/hierarchy.json',units);write('data/world-index.json',index);write('data/'+source,{type:'FeatureCollection',features});
 const ownerRaw=write('inputs/owners.json.gz',gzipSync(Buffer.from(JSON.stringify(owners)))),origin=commit();
 const native={id:'geography:fixture-native',hierarchy_sha256:sha(originalHierarchy),footprints_sha256:footprintHash(features)};
 const manifest=JSON.parse(fs.readFileSync(path.join(fixtureDirectory,'native-manifest.json')));Object.assign(manifest,{geographic_release:native.id,hierarchy_sha256:native.hierarchy_sha256,footprints_sha256:native.footprints_sha256});manifest.original_assets.bounds={...pin('inputs/owners.json.gz',origin),sha256:sha(ownerRaw)};
 const manifestRaw=write('data/native-fixture.json',manifest),manifestSha=sha(manifestRaw),products=[{path:'manifest.json',bytes:manifestRaw.length,sha256:manifestSha},...manifest.parts.map(p=>({path:p.path,bytes:p.bytes,sha256:p.sha256}))];
 const receiptPath='coordination/engineering/alias-fixture/native-receipt.json';write(receiptPath,{method:manifest.method,baseline_commit:manifest.provenance?.baseline_commit,preparation_commit:manifest.provenance?.evaluation_commit,checked_rows:manifest.size,checked_cells:manifest.size**2,unchecked_cells:0,checked_runs:manifest.runWords/2,owned_cells:manifest.accounting?.owned_cells,owners:manifest.accounting?.owners,installation_ready:false,products,two_run_products:products.length,run_one_sha256:sha(Buffer.from(JSON.stringify(products))),run_two_sha256:sha(Buffer.from(JSON.stringify(products)))});const proof=commit();
 write('scripts/native-ownership/verified-candidates.json',{version:1,candidates:{[manifestSha]:{...pin(receiptPath,proof),role:'reviewed-exhaustive-native-rule-comparison',installation_approval:false}}});
 const bank={version:1,kind:'complete-world-index-with-exact-encoded-overrides',release_id:native.id,native_manifest_sha256:manifestSha,world_index:pin('data/world-index.json',origin),unchanged_files:[pin('data/'+source,origin)],overrides:[]},bankRaw=write('inputs/bank.json',bank);
 const selection={version:1,method:manifest.method,manifest_path:'data/native-fixture.json',release_id:native.id,sha256:manifestSha,selected_geography:{path:'inputs/bank.json',bytes:bankRaw.length,sha256:sha(bankRaw)}};
 const currentUnits=structuredClone(units);currentUnits[4].name='Current province';const currentHierarchy=write('data/hierarchy.json',currentUnits),reference={...native,id:'geography:fixture-current',hierarchy_sha256:sha(currentHierarchy)};
 const common={footprints_sha256_before:native.footprints_sha256,footprints_sha256_after:native.footprints_sha256,reference_only:true,historical_claims_transferred:false,summary:{geometry_changes:0},relationships:[],retired_units:[],source_evidence:[{url:'https://example.invalid/retained',source_sha256:pin('data/'+source,origin).sha256}]};
 const oldReceipt={...common,before_sha256:native.hierarchy_sha256,after_sha256:reference.hierarchy_sha256,before_units:units,group_changes:[{id:units[4].id,before:units[4],after:currentUnits[4]}],changed_location_properties:[]};write('inputs/prior-receipt.json',oldReceipt);const prior=commit();
 const projection=prepareReferenceMetadataProjection({selection,manifest,owners,reference,hierarchy:{before:pin('data/hierarchy.json',origin),after:pin('data/hierarchy.json',prior)},receipts:[pin('inputs/prior-receipt.json',prior)],source_updates:[],read});
 const projectionRaw=write('inputs/projection.json',projection);selection.reference_projection={path:'inputs/projection.json',bytes:projectionRaw.length,sha256:sha(projectionRaw)};write('data/ownership-selection.json',selection);
 const release={version:1,releases:[{...native,version:1},{...reference,version:2,expected_counts:{location:6},metadata:{metadata_migration_sha256:{prior:pin('inputs/prior-receipt.json',prior).sha256}}}],batches:[]};write('data/geographic-releases/index.json',release);
 for(const name of ['world-review.json','global-semantic-closure.json.gz','macro-foundation/current-membership-inventory.json.gz','prepared-evidence/imports/index.json','demographic-evidence/revalidation.json','dated-reference-names/revalidation.json','ownership-history/original.json'])write('data/'+name,{retained:name});
 const pixel={footprints_sha256:reference.footprints_sha256,hierarchy_sha256:reference.hierarchy_sha256,method:manifest.method,native_manifest:{sha256:manifestSha}};write('data/pixel-audit.json',pixel);
 const evidence={footprints_sha256:reference.footprints_sha256,hierarchy_sha256:reference.hierarchy_sha256,location_index_sha256:sha(Buffer.from(JSON.stringify(index))),products:[]};write('data/prepared-evidence/index.json',evidence);
 const audit={input_sha256:Object.fromEntries(['hierarchy.json','world-index.json',source].map(p=>[p,sha(fs.readFileSync(path.join(repo,'data',p)))])),counts:{location:6},locations_audited:[{id:'L0',result:'retained'}],coarse_units:[],small_units:[]};write('data/granularity-audit.json',audit);
 for(const p of ['hierarchy.json','world-index.json'])write('after/'+p,fs.readFileSync(path.join(repo,'data',p)));
 const next=structuredClone(features);next[0].properties.metadata.reference_polity='Recorded winner';write('after/'+source,{type:'FeatureCollection',features:next});
 const alias={...common,before_sha256:reference.hierarchy_sha256,after_sha256:reference.hierarchy_sha256,before_units:currentUnits,group_changes:[],changed_location_properties:[{location_id:'L0',before_properties:features[0].properties,after_properties:next[0].properties}]};write('alias-receipt.json',alias);commit();
 const api=await import(pathToFileURL(path.join(repo,'scripts/install-macro-reference.mjs')));
 return {repo,write,api,source,audit,pixel,evidence,release,alias,features,next,options:{data:path.join(repo,'data'),geographyData:path.join(repo,'after'),releaseData:path.join(repo,'data/geographic-releases'),stage:path.join(repo,'stage'),receipts:[path.join(repo,'alias-receipt.json')],metadataMode:'reference-correction',repository:repo}};
}

test('actual alias installer changes only source and audit pins, preserving M, N and historical evidence',async t=>{
 const f=await aliasInstallerFixture(t),baseline=fs.readFileSync(path.join(f.repo,'data/geographic-releases/index.json'));
 const prepared=await f.api.prepareInstall(f.options);
 assert.deepEqual(Object.keys(prepared.report.writes).sort(),[f.source,'granularity-audit.json']);assert.deepEqual(prepared.report.archives,[]);
 for(const p of ['pixel-audit.json','prepared-evidence/index.json','prepared-evidence/imports/index.json','demographic-evidence/revalidation.json','dated-reference-names/revalidation.json'])assert.equal(prepared.report.preserved[p],sha(fs.readFileSync(path.join(f.repo,'data',p))));
 const audit=JSON.parse(fs.readFileSync(path.join(prepared.stage,'after/granularity-audit.json'))),expected=structuredClone(f.audit);expected.input_sha256[f.source]=sha(fs.readFileSync(path.join(f.repo,'after',f.source)));assert.deepEqual(audit,expected);
 assert.equal(prepared.report.release_id,f.release.releases.at(-1).id);assert.equal(prepared.report.ownership_recompiled,false);
 assert.throws(()=>f.api.applyInstall(prepared,{expectedValidation:prepared.validation_sha256,failAfter:1}),/Injected metadata install failure/);
 assert.deepEqual(JSON.parse(fs.readFileSync(path.join(f.repo,'data',f.source))).features,f.features);
 assert.equal(f.api.applyInstall(prepared,{expectedValidation:prepared.validation_sha256}).applied,true);
 assert.deepEqual(JSON.parse(fs.readFileSync(path.join(f.repo,'data',f.source))).features,f.next);
 assert.deepEqual(fs.readFileSync(path.join(f.repo,'data/geographic-releases/index.json')),baseline);
 assert.deepEqual(JSON.parse(fs.readFileSync(path.join(f.repo,'data/ownership-history/original.json'))),{retained:'ownership-history/original.json'});
});

test('actual alias installer refuses stale audit, changed source inventory and hidden fields before staging',async t=>{
 for(const mutate of [
  f=>{f.audit.input_sha256[f.source]='0'.repeat(64);f.write('data/granularity-audit.json',f.audit);},
  f=>{f.pixel.hierarchy_sha256='0'.repeat(64);f.write('data/pixel-audit.json',f.pixel);},
  f=>{f.evidence.location_index_sha256='0'.repeat(64);f.write('data/prepared-evidence/index.json',f.evidence);},
  f=>f.write('after/'+f.source,{type:'FeatureCollection',extra:'hidden',features:f.next}),
  f=>f.write('after/'+f.source,{type:'FeatureCollection',features:[...f.next].reverse()}),
  f=>{f.next[0].properties.metadata.semantic_review.status='approved';f.alias.changed_location_properties[0].after_properties=f.next[0].properties;f.write('alias-receipt.json',f.alias);f.write('after/'+f.source,{type:'FeatureCollection',features:f.next});},
  f=>{f.release.releases.at(-1).metadata.metadata_migration_sha256={};f.write('data/geographic-releases/index.json',f.release);},
 ]){const f=await aliasInstallerFixture(t);mutate(f);await assert.rejects(()=>f.api.prepareInstall(f.options));assert.equal(fs.existsSync(f.options.stage),false);}
});

test('alias audit reuse refuses changed created features without rejecting unchanged created features',async t=>{
 const f=await aliasInstallerFixture(t,{referenceVersion:4});
 await assert.rejects(()=>f.api.prepareInstall(f.options),/Alias audit reuse requires an original reference-version-3 feature/);
 assert.equal(fs.existsSync(f.options.stage),false);
});
