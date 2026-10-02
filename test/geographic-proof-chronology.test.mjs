import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {identityProofOrder,validateReviewedIdentities} from '../scripts/prepare-geographic-release.mjs';
const pin=s=>createHash('sha256').update(s).digest('hex');
const identity=row=>({...row,kind:row.level??row.kind});
function fixture(t){
 const folder=fs.mkdtempSync(path.join(os.tmpdir(),'atlas-proof-order-'));t.after(()=>fs.rmSync(folder,{recursive:true,force:true}));
 let units=['continent','subcontinent','region','area','province'].map((level,i)=>({id:['c','s','r','a','p'][i],level,name:level+'0',parent_id:[null,'c','s','r','a'][i],metadata:{retained:'Original source bytes',child_count:1}}));
 const before=structuredClone(units),locations=[{id:'l',name:'Original',parent_id:'p',kind:'location'}];
 const original=new Map([...units.map(identity),...locations].map(row=>[row.id,{...row,active:1}]));
 const registry=new Map(original),proofs=[],metadataProofs=[],steps=[];
 function geometry(added=null){
  const index=proofs.length,file=path.join(folder,'hierarchy'+index+'.json');fs.writeFileSync(file,JSON.stringify(units));
  const proof={manifest_sha256:pin('geometry'+index),creationProofs:added?[{}]:[],changed:new Set(),removed:new Set(),added:new Set(added?[added.id]:[]),files:{'after-hierarchy.json':{file}},receipt:{added_features:added?[{properties:added}]:[]}};
  proofs.push(proof);steps.push({type:'geometry',sha256:proof.manifest_sha256});
 }
 function metadata(id,name){
  const before=structuredClone(units),old=units.find(row=>row.id===id),after={...old,name};units=units.map(row=>row.id===id?after:row);
  const proof={sha256:pin('metadata'+metadataProofs.length),receipt:{reference_only:true,historical_claims_transferred:false,summary:{geometry_changes:0},before_units:before,retired_units:[],relationships:[],group_changes:[{id,before:old,after}],changed_location_properties:[],source_evidence:[{url:'https://example.org/synthetic-test-source',source_sha256:pin('source')}]}};
  metadataProofs.push(proof);steps.push({type:'metadata',sha256:proof.sha256});
 }
 geometry();for(let n=1;n<=4;n++)metadata('r','region'+n);
 units=units.map(row=>row.id==='a'?{...row,metadata:{...row.metadata,child_count:2}}:row);
 units.push({id:'p2',level:'province',name:'Separate island province',parent_id:'a',metadata:{child_count:1}});const second={id:'l2',name:'New island',parent_id:'p2',kind:'location'};locations.push(second);geometry(second);
 metadata('a','area1');units=units.map(row=>row.id==='a'?{...row,metadata:{...row.metadata,child_count:3}}:row);units.push({id:'p3',level:'province',name:'Another island province',parent_id:'a',metadata:{child_count:1}});const third={id:'l3',name:'Another island',parent_id:'p3',kind:'location'};locations.push(third);geometry(third);
 const input={original,current:new Map([...units.map(identity),...locations].map(row=>[row.id,row])),migration:{before_units:before,group_changes:[],changes:[]},geometryProof:{proofs},metadataProofs,registry,identitySequence:{version:1,steps}};
 return {input,folder};
}
test('four retained metadata predecessors replay before a late creation and a future second addition',t=>{
 const f=fixture(t),before=JSON.stringify([...f.input.original]);
 const result=validateReviewedIdentities(f.input);assert.equal(result.retired.size,0);assert.equal(result.created.size,0);
 assert.equal(JSON.stringify([...f.input.original]),before);assert.equal(f.input.current.get('r').name,'region4');
});
test('mixed creation and metadata chronology must be explicit',t=>{
 const f=fixture(t);delete f.input.identitySequence;assert.throws(()=>validateReviewedIdentities(f.input),/explicit pinned identity proof sequence/);
});
test('a creation snapshot cannot advance a previous metadata identity or alter its full source record',t=>{
 for(const variant of ['premature','metadata']){
  const f=fixture(t);
  if(variant==='premature'){const s=f.input.identitySequence.steps;[s[4],s[5]]=[s[5],s[4]];}
  else{const file=f.input.geometryProof.proofs[1].files['after-hierarchy.json'].file,units=JSON.parse(fs.readFileSync(file));units[0].metadata.retained='Rewritten source';fs.writeFileSync(file,JSON.stringify(units));}
  assert.throws(()=>validateReviewedIdentities(f.input),/exact chronological predecessor unit|exact retained before records/);
 }
});
test('skipped, duplicate, reordered and mutated sequence pins fail',t=>{
 for(const variant of ['skip','duplicate','metadata-order','geometry-order','mutate','extra-field']){
  const f=fixture(t),steps=f.input.identitySequence.steps;
  if(variant==='skip')steps.pop();
  else if(variant==='duplicate')steps[2]=structuredClone(steps[1]);
  else if(variant==='metadata-order')[steps[1],steps[2]]=[steps[2],steps[1]];
  else if(variant==='geometry-order')[steps[0],steps[5]]=[steps[5],steps[0]];
  else if(variant==='mutate')steps[5].sha256=pin('tampered');
  else steps[0].permit_overwrite=true;
  assert.throws(()=>validateReviewedIdentities(f.input),/Identity proof sequence|identity proof sequence/);
 }
});
test('metadata archive tampering still fails at its chronological predecessor',t=>{
 const f=fixture(t);f.input.metadataProofs[2].receipt.before_units[0].metadata.retained='Tampered retained source';
 assert.throws(()=>validateReviewedIdentities(f.input),/exact retained before records/);
});
test('legacy noncreation order remains stable and an unused new group is rejected',t=>{
 const empty={geometryProofs:[],metadataProofs:[]};assert.equal(identityProofOrder(empty).sha256,null);
 const f=fixture(t),file=f.input.geometryProof.proofs[1].files['after-hierarchy.json'].file,units=JSON.parse(fs.readFileSync(file));units.push({id:'unused',level:'province',name:'Unjustified',parent_id:'a'});units.find(row=>row.id==='a').metadata.child_count=3;fs.writeFileSync(file,JSON.stringify(units));
 assert.throws(()=>validateReviewedIdentities(f.input),/empty active geographic group/);
});

test('derived child counts must equal actual before and after immediate memberships',t=>{
 for(const variant of ['wrong-after','wrong-before']){
  const f=fixture(t);
  if(variant==='wrong-after'){const file=f.input.geometryProof.proofs[1].files['after-hierarchy.json'].file,units=JSON.parse(fs.readFileSync(file));units.find(row=>row.id==='a').metadata.child_count=999;fs.writeFileSync(file,JSON.stringify(units));}
  else f.input.metadataProofs[3].receipt.before_units.find(row=>row.id==='a').metadata.child_count=999;
  assert.throws(()=>validateReviewedIdentities(f.input),/exact chronological predecessor unit|exact retained before records/);
 }
});
