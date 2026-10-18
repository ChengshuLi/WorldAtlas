// Execute only exact frozen admission fragments and unchanged outcome branching on synthetic fixtures.
// Does not import/invoke the caller or coordinateBounds, read target stages, access Git, or scan source records.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
const root=path.dirname(fileURLToPath(import.meta.url)),proposal=path.dirname(root);
const caller=fs.readFileSync(path.join(proposal,'derive-declared-scope-applicability.proposed.mjs'),'utf8');
const reference=fs.readFileSync(path.join(proposal,'reference-four-scope-caller.mjs'),'utf8');
const contract=JSON.parse(fs.readFileSync(path.join(proposal,'scope-contract.proposed.json'),'utf8'));
const freeze=JSON.parse(fs.readFileSync(path.join(proposal,'FREEZE.json'),'utf8'));
const sha=b=>createHash('sha256').update(b).digest('hex');
for(const name of ['derive-declared-scope-applicability.proposed.mjs','adapter-config.proposed.json','scope-contract.proposed.json']){
  assert.equal(sha(fs.readFileSync(path.join(proposal,name))),freeze.files.find(x=>x.path===name).sha256);
}
function slice(text,start,end){const a=text.indexOf(start),b=text.indexOf(end,a);assert(a>=0&&b>a,`Exact fragment markers required: ${start}`);return text.slice(a,b);}
const needLine=caller.split('\n').find(x=>x.startsWith('const need = '));
const sameLine=caller.split('\n').find(x=>x.startsWith('const same = '));
const unique=slice(caller,'function unique(rows,key,label) {','// The frozen scope contract');
const helpers=needLine+'\n'+sameLine+'\n'+unique;
const initial=slice(caller,"need(config.version === 2",'const env = ');
const scope=slice(caller,'const scopeContract=json(config.inputs.scope_contract)','const closure=');
const own=slice(caller,'  const declared=declaredScopes.get(c.iso);','  const stages=');
const count=slice(caller,'  read(c.original_membership);','  const owners=new Set()');
const join=slice(caller,"    need(id.startsWith(c.positive_family+':')",'    const t=');
const admit=new Function('config','fixtureContract',helpers+`
function json(pin){assertScopePin(pin);return fixtureContract;}
function assertScopePin(pin){need(pin===config.inputs.scope_contract,'Fixture scope binding differs');}
`+initial+scope+'\nreturn {declaredScopes,scopeContract};');
const roles=new Function('c','declaredScopes','products',helpers+own+'\nreturn ownFamilies;');
const stageCount=new Function('c','stages','members','pkg','declared',helpers+'\nfunction read(){}\n'+count+'\nreturn true;');
const targetJoin=new Function('c','id','m','s','original',helpers+join+'\nreturn true;');
const clone=x=>structuredClone(x),results=[];
function fixture(){
  const config={version:2,kind:'parameterized-scope-retained-bounds-adapter-v2',countries:clone(contract.countries),target_frames:clone(contract.target_frames),expected:clone(contract.expected),inputs:{scope_contract:{fixture:true}}};
  const products=new Map();
  for(const c of contract.countries)for(const family of [c.positive_family,...c.parent_context_families])products.set(family,{feature_count:1});
  // Family names only: 361 synthetic foreign catalogue entries, no source geometries or records.
  for(let i=products.size;i<368;i++)products.set('fixture:foreign:'+i,{feature_count:1});
  const data=new Map(config.countries.map(c=>{
    c.target_ids=Array.from({length:c.target_count},(_,i)=>c.positive_family+':fixture-'+i);
    return [c.iso,{stages:new Map(c.target_ids.map(id=>[id,{}])),members:new Map(c.target_ids.map(id=>[id,{}])),pkg:{package_id:c.package_id,location_count:c.target_count,native_cells:c.native_cells}}];
  }));
  return {config,contract:clone(contract),products,data};
}
function run(f){
  const {declaredScopes}=admit(f.config,f.contract),observed=[];
  for(const c of f.config.countries){
    const ownFamilies=roles(c,declaredScopes,f.products),d=f.data.get(c.iso);stageCount(c,d.stages,d.members,d.pkg,declaredScopes.get(c.iso));
    const id=c.target_ids[0],m={source_id:id,target_id:id,pixelIndex:9,source_index:10,source_ordinal:0};
    targetJoin(c,id,m,{selected:{id},consumed:{properties:{shapeID:id.slice(c.positive_family.length+1)}}},{owners:[9],source_index:10,ordinal:0});
    observed.push({iso:c.iso,positive_family:c.positive_family,parent_context_families:c.parent_context_families,own_families:ownFamilies,complete_foreign_families:f.products.size-ownFamilies.length});
  }
  return observed;
}
function pass(name,mutate,check){const f=fixture();mutate?.(f);const observed=run(f);check?.(observed);results.push({name,expected:'admit',actual:'admitted',observed});}
function refuse(name,mutate,message){const f=fixture();mutate(f);let error;try{run(f);}catch(e){error=e;}assert(error,`${name}: expected refusal`);assert(error.message.includes(message),`${name}: unexpected refusal ${error.message}`);results.push({name,expected:'refuse',actual:'refused',guard_error:error.message});}
pass('exact-four-scope-admission',null,r=>assert.deepEqual(r.map(x=>[x.iso,x.own_families.length,x.complete_foreign_families]),[['GTM',2,366],['BLZ',1,367],['DOM',2,366],['SLV',2,366]]));
refuse('wrong-scope-country-order',f=>f.config.countries.reverse(),'Exact frozen scope contract required');
refuse('wrong-aggregate-target-count',f=>f.config.expected.targets=145,'Exact frozen scope contract required');
refuse('wrong-aggregate-key-count',f=>f.config.expected.native_cells=7554,'Exact frozen scope contract required');
refuse('contract-target-total-inconsistent',f=>f.contract.countries[1].target_count=5,'Declared aggregate scope differs');
refuse('missing-blz-parent-declaration',f=>delete f.contract.countries[1].parent_context_families,'Explicit bounded scope declaration required');
refuse('invented-blz-adm0-parent',f=>f.contract.countries[1].parent_context_families=['gb:BLZ:ADM0'],'Supported positive-level and exact parent roles required');
refuse('blz-positive-repeated-as-parent',f=>f.contract.countries[1].parent_context_families=['gb:BLZ:ADM1'],'Supported positive-level and exact parent roles required');
refuse('unknown-positive-source-level',f=>f.contract.countries[1].positive_family='gb:BLZ:ADM3','Supported positive-level and exact parent roles required');
refuse('wrong-positive-family-in-country',f=>f.config.countries[1].positive_family='gb:BLZ:ADM2','Country roles differ from frozen declaration');
refuse('unknown-parent-role-in-country',f=>f.config.countries[1].parent_context_families=['territorial-exclusion'],'Country roles differ from frozen declaration');
refuse('wrong-country-parent-in-adm2-contract',f=>f.contract.countries[2].parent_context_families=['gb:GTM:ADM1'],'Supported positive-level and exact parent roles required');
refuse('unclassified-extra-own-catalogue-family',f=>f.products.set('gb:BLZ:ADM2',{feature_count:1}),'Every retained own family must have exactly one declared role');
refuse('missing-declared-parent-catalogue-family',f=>f.products.delete('gb:SLV:ADM1'),'Every retained own family must have exactly one declared role');
refuse('wrong-blz-stage-member-count',f=>f.data.get('BLZ').stages.delete(f.config.countries[1].target_ids[0]),'Complete declared original stage scope required');
refuse('wrong-blz-membership-count',f=>f.data.get('BLZ').members.delete(f.config.countries[1].target_ids[0]),'Complete declared original stage scope required');
refuse('wrong-blz-package-key-count',f=>f.data.get('BLZ').pkg.native_cells=916,'Complete declared original stage scope required');
refuse('wrong-blz-package-source-level',f=>f.data.get('BLZ').pkg.package_id='gb-BLZ-ADM2--repair-evaluation','Complete declared original stage scope required');
refuse('wrong-target-positive-prefix',f=>f.config.countries[1].target_ids[0]='gb:BLZ:ADM2:fixture-0','Original target association differs');
refuse('reduced-global-source-declaration',f=>{f.contract.expected.source_features=73566;f.config.expected.source_features=73566;},'Exact frozen scope contract required');
refuse('duplicate-country-declaration',f=>f.contract.countries.push(clone(f.contract.countries[1])),'Duplicate declared evaluation scopes');

// Reuse the unchanged inclusive/outcome controls with entirely synthetic bounds.
const relation=caller.split('\n').find(x=>x.startsWith('const intersection = '));
assert.equal(relation,reference.split('\n').find(x=>x.startsWith('const intersection = ')));
const intersection=new Function(relation+'\nreturn intersection;')();
const outcomeStart='const outcomes=countries.map(c=>{',outcomeEnd='\n    emit({...r,new_country_outcomes:outcomes});';
const callbackText=slice(caller,outcomeStart,outcomeEnd);assert.equal(callbackText,slice(reference,outcomeStart,outcomeEnd));
const callback=new Function('countries','r','usable','isPeriodic','config','periodic','intersection','proof',callbackText+'\nreturn outcomes;');
function kernel(name,bounds,usable,isPeriodic,enclosure,expected){
  const c={iso:'BLZ',positive_family:'gb:BLZ:ADM1',parent_context_families:[],targets:[{id:'synthetic-target',frames:{consumed:[[0,0,1,1]],selected:[[3,0,4,1]]}}],enclosure,feature_counts:{positive:0,parent_context:0,foreign:0,foreign_candidates:0,foreign_disjoint:0,foreign_unresolved:0},candidates:new Set(),unresolved:new Set()};
  const r={source_family:'gb:FJI:ADM1',source_id:'synthetic-foreign-source',owners:[],complete_part_bounds:bounds,original_geometry_sha256:'synthetic',retained_canonical_geometry_sha256:'synthetic'};
  const periodic=[],outcome=callback([c],r,usable,isPeriodic,{target_frames:['consumed','selected']},periodic,intersection,{exact_output_match:true})[0];assert.equal(outcome.status,expected);
  if(expected.startsWith('unresolved')){assert.deepEqual([...c.unresolved],['gb:FJI:ADM1']);assert.deepEqual([...c.candidates],['gb:FJI:ADM1']);}
  return {name,outcome,candidate_families:[...c.candidates],unresolved_families:[...c.unresolved],periodic};
}
const kernels=[
  kernel('ownerless-selected-only-contact',[[3,0,3.5,1]],true,false,[-75,-71],'whole-bounds-candidate'),
  kernel('inclusive-edge-contact',[[1,0,2,1]],true,false,[-75,-71],'whole-bounds-candidate'),
  kernel('inclusive-corner-contact',[[1,1,2,2]],true,false,[-75,-71],'whole-bounds-candidate'),
  kernel('unknown-retained-outcome',null,false,false,[-75,-71],'unresolved-retained-coordinate-outcome'),
  kernel('periodic-selected-frame-contact',[[3,0,3.5,1]],true,true,[-75,-71],'unresolved-retained-periodic-contact'),
  kernel('periodic-native-enclosure-endpoint-contact',[[8,0,9,1]],true,true,[9,10],'unresolved-retained-periodic-contact'),
  kernel('periodic-both-disjoint-synthetic-control',[[8,0,9,1]],true,true,[-75,-71],'retained-periodic-bounds-and-native-key-enclosure-disjoint')
];
assert.deepEqual(kernels[0].outcome.frame_target_ids,{consumed:[],selected:['synthetic-target']});
const report={observed_at_utc:new Date().toISOString(),node:process.version,caller_sha256:sha(caller),scope_contract_sha256:sha(fs.readFileSync(path.join(proposal,'scope-contract.proposed.json'))),admission_controls:results,kernel_controls:kernels,unchanged_callback_and_inclusive_relation:true,full_caller_invocations:0,real_target_geometry_reads:0,world_source_records_scanned:0,source_geometry_transports_decoded:0,qualified_cells:0,accepted_credit:0,limits:['Exact changed admission fragments run with synthetic scope/family/count/identity fixtures; immutable Git/byte input admission and actual stage contents are not rerun.','Unchanged outcome callback uses synthetic bounds and an already-admitted synthetic periodic proof; actual Fiji identity/native-equality proof guards are not replayed.','No coordinateBounds import, real target-frame derivation, full catalogue record traversal, applicability producer, physical/source/native producer or scientific result.']};
fs.writeFileSync(path.join(root,'results.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({node:process.version,admission_controls:results.length,admitted:results.filter(x=>x.actual==='admitted').length,expected_refusals:results.filter(x=>x.actual==='refused').length,synthetic_unchanged_kernel_controls:kernels.length,full_caller_invocations:0,world_records_scanned:0}));
