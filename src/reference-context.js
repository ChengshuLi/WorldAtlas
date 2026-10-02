import {environmentalAttributes,environmentalClassification} from './environment-classifications.js';

// Presentation context never becomes evidence for the selected historical year.
export function referenceContextByLocation(records=[]){
 const output=new Map();
 for(const row of records){
  if(!environmentalAttributes.includes(row.attribute)||row.method!=='reference'||row.is_example||row.value==null||['unknown','disputed','no-majority'].includes(row.status)||row.metadata?.invalidated_footprint)continue;
  const classification=environmentalClassification(row.attribute,row.value);if(!classification)continue;
  if(!output.has(row.location_id))output.set(row.location_id,{});
  const values=output.get(row.location_id),old=values[row.attribute];
  if(!old||row.valid_from>old.provenance.valid_from||row.valid_from===old.provenance.valid_from&&String(row.id)<String(old.provenance.id)){
   values[row.attribute]={value:classification.label,category_id:classification.id,reference_context:true,provenance:{...row,classification_id:classification.id,source_value:row.value,context_only:true}};
  }
 }
 return output;
}

export function presentedAttribute(record={},attribute){
 const provenance=record.provenance?.[attribute]??{status:'unknown'};
 if(record[attribute]!=null)return {value:record[attribute],category_id:record.category_ids?.[attribute]??null,provenance,reference_context:provenance.method==='reference'};
 // Explicit dated uncertainty, rejected classifications or invalidated footprints
 // remain authoritative. A modern baseline cannot silently override that evidence.
 if(provenance.id||provenance.source||provenance.source_id||provenance.metadata?.invalidated_footprint)return {value:null,category_id:null,provenance,reference_context:false};
 return record.reference_baselines?.[attribute]??{value:null,category_id:null,provenance,reference_context:false};
}
