import {attributes,validYear,explicitPopulationZero} from './model.js';
export const locationAttributes=[...attributes,'habitation'];
export const unresolvedAttributeStatuses=['unknown','disputed','no-majority'];
export function categoryId(kind,name){return name==null?null:`${kind}:${encodeURIComponent(name.normalize('NFC').trim().toLocaleLowerCase('en'))}`;}
const priority=r=>r.is_example?40+(r.evidence_priority||0):r.method==='direct'?(r.evidence_priority||0):r.method==='majority-area'||r.method==='derived'?10:r.method==='reference'?20:30;
export function resolveAttributes(features,year,{states=[],records=[],temporal,examples=false,evidenceAvailable=true}={}){
 if(!validYear(year))throw Error('Year must be between 3000 BC and 2026 AD, excluding zero');
 if(!evidenceAvailable){states=[];records=[];temporal=undefined;}
 const candidates=new Map();
 const add=(id,attribute,value,r)=>{
  if(r.valid_from>year||r.valid_to<=year||r.is_example&&!examples)return;
  const key=`${id}/${attribute}`,previous=candidates.get(key),rank=priority(r);
  if(!previous||rank<previous.rank||rank===previous.rank&&String(r.id)<String(previous.evidence.id))candidates.set(key,{value,rank,evidence:r});
 };
 for(const r of states)for(const attribute of locationAttributes)if(attribute in r)add(r.location_id,attribute,r[attribute],{...r,metadata:{...(r.metadata||{}),legacy_snapshot:true},method:'direct',evidence_priority:2,status:r.is_example?'example':'sourced',id:`state:${r.id??r.location_id}`});
 for(const e of temporal?.entities.values()||[])if(e.kind==='location'&&e.attributes?.source){const a=e.attributes,r={...a,metadata:{legacy_attributes:true},method:'direct',status:a.is_example?'example':'sourced',valid_from:e.attribute_record?.valid_from??year,valid_to:e.attribute_record?.valid_to??(year===-1?1:year+1),evidence_priority:1,id:`temporal:${e.id}`};for(const attribute of locationAttributes)add(e.id,attribute,a[attribute]??null,r);}
 for(const r of records)add(r.location_id,r.attribute,r.value,r);
 const output=new Map();
 for(const f of features){const value={location_id:f.id,provenance:{},category_ids:{}};
  for(const attribute of locationAttributes){let c=candidates.get(`${f.id}/${attribute}`);
   if(evidenceAvailable&&(!c||c.rank>20)&&year===2026&&attribute==='owner'&&f.properties.reference_owner){const m=f.properties.metadata||{},name='reference_polity' in m?m.reference_polity:f.properties.reference_owner;c={value:name,evidence:{category_id:m.reference_owner_id??categoryId('owner',name),method:'reference',status:m.reference_polity_status||'reference',valid_from:2026,valid_to:2027,source:m.reference_polity_evidence?.source||`${m.source_name||'Geographic'} ownership reference; source dates vary`,metadata:m.reference_polity_evidence||{}}};}
   const unresolved=unresolvedAttributeStatuses.includes(c?.evidence.status);
   value[attribute]=unresolved?null:c?.value??null;
   value.provenance[attribute]=c?{...c.evidence,value:undefined,location_id:undefined,attribute:undefined}:{status:'unknown',method:null,source:null};
   if(['owner','culture','religion'].includes(attribute)){value.category_ids[attribute]=value[attribute]==null?null:c?.evidence.category_id??categoryId(attribute,value[attribute]);if(value[attribute]==null)value.provenance[attribute].category_id=null;}
  }
  resolveSettlementEvidence(value,candidates);
  const evidence=value.provenance.owner;value.source=evidence.source;value.reference=evidence.method==='reference';value.is_example=Object.values(value.provenance).some(p=>p.is_example)?1:0;output.set(f.id,value);
 }
 return output;
}
function resolveSettlementEvidence(value,candidates){
 const known=p=>p&&(p.source||p.source_id)&&!unresolvedAttributeStatuses.includes(p.status);
 const proof=attribute=>{const c=candidates.get(`${value.location_id}/${attribute}`);return c&&known(c.evidence)?{attribute,...c}:null;};
 const habitation=proof('habitation'),rank=proof('rank'),population=proof('population');
 if(value.rank==='unsettled'&&!rank){value.rank=null;value.provenance.rank={...value.provenance.rank,status:'unknown',metadata:{...(value.provenance.rank.metadata||{}),reason:'Unsettled requires explicit sourced evidence of no inhabitants'}};}
 const negative=[habitation?.value==='uninhabited'?habitation:null,rank?.value==='unsettled'?rank:null,population&&explicitPopulationZero(population.value,population.evidence)?population:null].filter(Boolean).sort((a,b)=>a.rank-b.rank||String(a.evidence.id).localeCompare(String(b.evidence.id),'en'));
 const positive=[habitation?.value==='inhabited'?habitation:null,rank?.value!=null&&rank?.value!=='unsettled'?rank:null,population?.value>0?population:null].filter(Boolean).sort((a,b)=>a.rank-b.rank||String(a.evidence.id).localeCompare(String(b.evidence.id),'en'));
 if(!negative.length)return;
 const noInhabitants=negative[0],inhabited=positive[0],conflict=inhabited&&inhabited.rank===noInhabitants.rank;
 const invalidate=(p,reason)=>{value[p.attribute]=null;value.provenance[p.attribute]={...value.provenance[p.attribute],status:'disputed',metadata:{...(p.evidence.metadata||{}),reason,conflicting_evidence:[noInhabitants.evidence.id,inhabited?.evidence.id].filter(Boolean)}};};
 if(conflict){for(const p of [...negative,...positive])invalidate(p,'Equally preferred settlement evidence contradicts habitation; no settlement rank inferred');value.rank=null;value.provenance.rank={...value.provenance.rank,status:'disputed',metadata:{...(value.provenance.rank.metadata||{}),reason:'Conflicting evidence of inhabitants and no inhabitants'}};return;}
 if(inhabited&&inhabited.rank<noInhabitants.rank){for(const p of negative)invalidate(p,'Stronger evidence of inhabitants contradicts this no-inhabitants assignment');return;}
 for(const p of positive)invalidate(p,'Stronger explicit no-inhabitants evidence contradicts this settlement assignment');
 const rankCandidate=candidates.get(`${value.location_id}/rank`);
 if(rankCandidate&&unresolvedAttributeStatuses.includes(rankCandidate.evidence.status)&&rankCandidate.rank<=noInhabitants.rank)return;
 if(value.rank!=='unsettled'){
  value.rank='unsettled';value.provenance.rank={...noInhabitants.evidence,id:`derived:unsettled:${noInhabitants.evidence.id}`,value:undefined,location_id:undefined,attribute:undefined,method:'derived',status:noInhabitants.evidence.is_example?'example':'derived',metadata:{...(noInhabitants.evidence.metadata||{}),assignment_method:'explicit-no-inhabitants',supporting_attribute:noInhabitants.attribute,supporting_record_id:noInhabitants.evidence.id,reason:noInhabitants.attribute==='population'?'Direct sourced literal zero inhabitants; not an estimated or rounded zero':'Explicit sourced evidence of no inhabitants'}};
 }
}
export function selectAttributeRecords(records,year,examples=false){if(!validYear(year))throw Error('Invalid selected year');return records.filter(r=>r.valid_from<=year&&r.valid_to>year&&(!r.is_example||examples));}
