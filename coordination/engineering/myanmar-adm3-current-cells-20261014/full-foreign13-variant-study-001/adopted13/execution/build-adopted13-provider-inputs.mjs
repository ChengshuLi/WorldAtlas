import fs from 'node:fs';
import {gunzipSync} from 'node:zlib';
import {valueSha} from '../../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
import {pinReader} from '../../scripts/prepare-delivery-handoff.mjs';
const D='.takeover/full-foreign-variants834/',out=D+'qualification-drafts/',r=pinReader(process.cwd()),load=p=>JSON.parse(fs.readFileSync(p)),need=(x,m)=>{if(!x)throw Error(m);};
const proposal=load(D+'PROPOSED-exact13-full-foreign-source-choice.json'),input=load(D+'physical-input-commit.json'),physical=load(D+'physical-result-commit.json'),stage=load(D+'whole-eight-member-stage-inputs.json');
const prior=r.json(r.pin('6353379186dce92ec76b39561dfb5b32b2aad76b','coordination/engineering/indonesia-provider15-20261016/bukit1/source-evidence.json'));
const mmr=load('.takeover/remaining1295/complete-original-foreign-fine-observation834.json').whole_original_families.find(f=>f.family==='gb:MMR:ADM3'),fullMMR=JSON.parse(Buffer.concat(mmr.parts.map(p=>gunzipSync(r.read(p)))).toString());
const resultPin=physical.results.find(p=>p.path.endsWith('whole-target-support.json'));
const save=(p,x)=>{fs.mkdirSync(out+p.slice(0,p.lastIndexOf('/')),{recursive:true});fs.writeFileSync(out+p,JSON.stringify(x,null,2)+'\n',{flag:'wx'});};
const allKeys=new Set(),groups=[];
for(const code of ['IND','THA']){
 const family=structuredClone(proposal.provider_family_document.families.find(f=>f.source_id===`gb-full:${code}:ADM2:9469f09`));
 const decision='Parent-adopted exact-key display-source choice: use this same-build full foreign member, crosswalked by literal original shapeID to its existing stable target and matching exclusive country reference. Retain original Myanmar fine contact as contextual evidence for only these exact keys, all full-family siblings as potential vetoes and all whole physical issues. No sovereignty, geometry/parent replacement or accepted repair credit. Qualification and actual selected conservation/consumer remain required.';
 for(const b of family.bindings)b.decision=decision;
 const records=proposal.source_records.filter(x=>x.reference_consistent_full_interiors[0].country===code),scope=[],contexts=[],targets=[],tuples=[];
 for(const binding of family.bindings){
  const measured=stage.find(s=>s.target===binding.source_id);need(measured&&measured.selected.id===binding.target_id&&valueSha(measured.selected.geometry)===binding.base_geometry_sha256,'Literal canonical stage target');
  const negatives=[],used=new Map();
  for(const key of binding.scope){
   const rec=records.find(x=>x.y===key.y&&x.x===key.x);need(rec&&rec.proposed_existing_owner===binding.pixelIndex,'Original proposal join');
   const identity=key.y+':'+key.x;need(!allKeys.has(identity),'Duplicate original key');allKeys.add(identity);
   const scopeIndex=scope.length;scope.push({owner:binding.pixelIndex,y:key.y,x:key.x,source_id:binding.source_id,target_id:binding.target_id,original_requested_owner:rec.owner,adopted_decision:decision,original_question_unchanged:rec});tuples.push([key.y,key.x,binding.pixelIndex]);
   need(rec.contrary_original_MMR_fine_interiors.length>0,'Missing retained contrary original');
   for(const hit of rec.contrary_original_MMR_fine_interiors){
    const ordinal=Number(/^\/features\/(\d+)\/geometry$/.exec(hit.pointer)?.[1]),feature=fullMMR.features[ordinal];
    need(feature&&'gb:MMR:ADM3:'+feature.properties.shapeID===hit.source_id&&valueSha(feature.geometry)===hit.geometry_sha256,'Complete original MMR geometry identity');
    let n=used.get(ordinal);if(n===undefined){n=negatives.length;used.set(ordinal,n);negatives.push(feature.geometry);}
    contexts.push({role:'contextual',source_id:binding.source_id,target_id:binding.target_id,pixelIndex:binding.pixelIndex,y:key.y,x:key.x,negative_ordinal:n,geometry_sha256:valueSha(feature.geometry),original_source:{id:'complete-original-MMR-family',pointer:hit.pointer},adoption_scope_index:scopeIndex});
   }
  }
  targets.push({id:binding.source_id,target_id:binding.target_id,pixelIndex:binding.pixelIndex,source_family:family.source_id,base_geometry:measured.selected.geometry,source_receipt_sha256:resultPin.sha256,coverage_classes:['mapped_land_support'],territorial_exclusions:negatives});
 }
 tuples.sort((a,b)=>a[0]-b[0]||a[1]-b[1]);const rows=[];for(const[y,x,owner]of tuples){let row=rows.at(-1);if(!row||row.y!==y){row={y,runs:[]};rows.push(row);}row.runs.push([x,x+1,owner]);}
 const evidence={};for(const k of ['version','kind','catalogue','owner_roster','native_contract','native_latitudes','base_reference'])evidence[k]=prior[k];
 evidence.physical_reproduction=r.pin('168ac2ab36663e31ca16f767340c0ab46bea4185','scripts/qualify-source-cohort.py');
 evidence.source_membership=input.source_membership;evidence.families=[{source_id:family.source_id,parts:[family.product]}];evidence.physical_input=input.stage;evidence.physical_evidence=resultPin;evidence.targets=targets;
 save(code+'/adopted-provider-families.json',{version:1,kind:'adopted-provider-source-families-v1',families:[family]});
 save(code+'/exact-adopted-source-choice.json',{version:1,kind:'parent-adopted-exact-source-choice',proposal_sha256:'415a7f4a543bc97e9a1372324545e5e88d69bc3f4aff5a566d2971c87ac0baff',source_choice_adoption_credit:0,scope,limits:['The sole whole-member contradictory_land_water_support MultiLineString issue belongs to Lawngtlai ID76128533B70210707786180; the original proposal limits sentence misnamed Chandel, while its actual source_records and immutable whole physical report are correct. Preserve all original proposal bytes and all guards.','IND full product has735 actual features versus736 in its upstream metadata; retain the mismatch.']});
 save(code+'/candidate-native-patch.json',{rows});save(code+'/source-evidence.template.json',evidence);save(code+'/territorial-context-records.json',{parts:mmr.parts,records:contexts});
 groups.push({country:code,keys:tuples.length,positive_members:targets.length,contextual_associations:contexts.length,whole_family_features:family.feature_count,decoded_bytes:family.product.decoded_bytes});
}
need(allKeys.size===13,'Exact13 scope');save('inventory.json',{groups,exact_original_keys:13,qualified_credit:0,accepted_credit:0,physical_producers_replayed:false});console.log(JSON.stringify(groups));
