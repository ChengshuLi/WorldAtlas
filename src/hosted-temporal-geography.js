import {levels,validYear} from './model.js';

const object=value=>value!==null&&typeof value==='object'&&!Array.isArray(value);
const text=value=>typeof value==='string'&&Boolean(value.trim());
const invalid=detail=>{throw Error(`Invalid hosted dated geography: ${detail}`);};
const metadata=(value={})=>{let parsed=value;if(typeof value==='string'){try{parsed=JSON.parse(value);}catch{invalid('metadata JSON');}}if(!object(parsed))invalid('metadata object');return parsed;};
const interval=row=>validYear(row.valid_from)&&(validYear(row.valid_to)||row.valid_to===2027)&&row.valid_from<row.valid_to;
const methods=['direct','derived','reference'],statuses=['sourced','derived','reference','unknown','disputed','example'];
const nextYear=year=>year===-1?1:year+1;

/** Pure browser-side validation/hydration. Reference release publication is
 * context, never an assertion that its administrative membership is ancient.
 * Footprint selection is deliberately unsupported in this capability version.
 */
function hydrateResolvedTemporalGeography(page,{year=page?.year,expectedGeography,examples=false}={}){
 if(!object(page)||!validYear(year)||page.year!==year||!Number.isSafeInteger(page.revision)||page.revision<0)invalid('year/revision');
 const release=page.release;
 if(!object(release)||!text(release.id)||release.status!=='published'||!['hierarchy_sha256','footprints_sha256'].every(key=>/^[a-f0-9]{64}$/.test(release[key]??'')))invalid('published release');
 if(expectedGeography&&((expectedGeography.release_id??expectedGeography.id)!==release.id||['hierarchy_sha256','footprints_sha256'].some(key=>expectedGeography[key]!==release[key])))invalid('pinned release mismatch');
 if(!object(page.footprints)||page.footprints.status!=='reference'||page.footprints.historical!==false||page.footprints.footprints_sha256!==release.footprints_sha256)invalid('unvetted historical footprint');
 if(!object(page.capability)||page.capability.datedMembership!==1||page.capability.datedExistence!==1||page.capability.datedFootprints!==0)invalid('unsupported capability');
 if(page.next_cursor!==undefined&&page.next_cursor!==null&&!text(page.next_cursor))invalid('cursor');
 for(const key of ['entities','claims','withdrawals','excluded_entity_ids'])if(!Array.isArray(page[key]))invalid(`${key} array`);
 if(page.sources!==undefined&&!object(page.sources))invalid('source dictionary');
 const sources=page.sources??{},identities=new Map(),claimsById=new Map(),withdrawn=new Set();
 function sourced(row){
  const source=Object.hasOwn(sources,row.source_id)?sources[row.source_id]:null;if(source&&source.id!==row.source_id)invalid('source identity');const joined=source?{source:source.name,source_url:source.url,source_license:source.license,source_vintage:source.vintage,source_status:source.status,source_from:source.supported_from,source_to:source.supported_to,source_metadata:source.metadata}:row;
  if(!text(joined.source)||!text(joined.source_license)||!text(String(joined.source_vintage??''))||!['historical','reference','estimate','example'].includes(joined.source_status))invalid('claim source');
  if(!validYear(joined.source_from)||!(validYear(joined.source_to)||joined.source_to===2027)||joined.source_from>=joined.source_to)invalid('source interval');
  if(joined.source_url!=null){try{if(!['https:','http:'].includes(new URL(joined.source_url).protocol))invalid('source URL');}catch{invalid('source URL');}}
  return {...row,...(source?joined:{}),metadata:metadata(row.metadata),source_metadata:metadata(joined.source_metadata)};
 }
 const claims=page.claims.map(raw=>{
  if(!object(raw)||!['memberships','existence'].includes(raw.collection)||!text(raw.id)||!text(raw.entity_id)||!text(raw.source_id)||!text(raw.validation_id)||raw.release_id!==release.id||!interval(raw)||raw.valid_from>year||raw.valid_to<=year||!methods.includes(raw.method)||!statuses.includes(raw.status)||![0,1].includes(raw.is_example)||raw.is_example&&!examples)invalid('dated claim');
  const row=sourced(raw);
  if(row.valid_from<row.source_from||row.valid_to>row.source_to||row.source_status==='example'&&!row.is_example||row.source_status==='reference'&&row.method!=='reference')invalid('source support/class');
  if(row.collection==='memberships'&&row.parent_id!==null&&!text(row.parent_id)||row.collection==='existence'&&!['exists','not_exists','unknown'].includes(row.value)||['unknown','disputed'].includes(row.status)&&(row.collection==='memberships'?row.parent_id!==null:row.value!=='unknown'))invalid('claim scalar');
  const key=`${row.collection}/${row.id}`;if(claimsById.has(key))invalid('duplicate claim');claimsById.set(key,row);return row;
 });
 const withdrawals=page.withdrawals.map(row=>{
  if(!object(row)||!text(row.id)||!['memberships','existence'].includes(row.collection)||!text(row.target_id)||!text(row.source_id)||!text(row.reason)||row.release_id!==release.id||!text(row.validation_id)||row.replacement_id!=null&&(!text(row.replacement_id)||row.replacement_id===row.target_id))invalid('withdrawal');
  const key=`${row.collection}/${row.target_id}`;if(withdrawn.has(key)||claimsById.has(key))invalid('withdrawn active claim');withdrawn.add(key);return {...row,metadata:metadata(row.metadata)};
 });
 const entities=page.entities.map(row=>{
  if(!object(row)||!text(row.id)||row.entity_id!==row.id||!levels.includes(row.kind)||typeof row.present!=='boolean'||row.parent_id!==null&&!text(row.parent_id)||row.reference_parent_id!==null&&!text(row.reference_parent_id)||row.historical_parent_id!==null&&!text(row.historical_parent_id)||!['dated','unknown','reference'].includes(row.membership_status)||!['historical','reference'].includes(row.parent_context)||!['exists','not_exists','unknown'].includes(row.existence_status)||identities.has(row.id))invalid('resolved entity');
  const claim=(record,collection)=>{if(record==null)return null;const known=claimsById.get(`${collection}/${record.id}`);if(!known||known.entity_id!==row.id)invalid('resolved record identity');return known;};
  const membership_record=claim(row.membership_record,'memberships'),existence_record=claim(row.existence_record,'existence');
  if(membership_record){if(row.historical_parent_id!==membership_record.parent_id||row.parent_id!==(membership_record.parent_id??row.reference_parent_id)||row.membership_status!==(membership_record.parent_id==null?'unknown':'dated')||row.parent_context!==(membership_record.parent_id==null?'reference':'historical'))invalid('resolved parent disagrees with evidence');}
  else if(row.parent_id!==row.reference_parent_id||row.historical_parent_id!==null||row.membership_status!=='reference'||row.parent_context!=='reference')invalid('unsupported historical parent');
  if(existence_record?.value==='not_exists'&&row.present||row.existence_status==='not_exists'&&row.present)invalid('absent entity present');
  if(row.kind==='continent'&&row.parent_id!==null||row.present&&row.kind!=='continent'&&row.parent_id===null)invalid('adjacent parent');
  const resolved={...row,membership_record,existence_record};identities.set(row.id,resolved);return resolved;
 });
 const excluded=new Set();for(const id of page.excluded_entity_ids){if(!text(id)||excluded.has(id)||!identities.has(id)||identities.get(id).present)invalid('exclusion identity');excluded.add(id);}
 for(const row of entities){if(!row.present&&!excluded.has(row.id))invalid('missing exclusion');const parent=identities.get(row.parent_id);if(row.present&&parent&&(!parent.present||levels.indexOf(parent.kind)!==levels.indexOf(row.kind)+1))invalid('incomplete adjacent chain');}
 return {...page,entities,claims,withdrawals};
}

export function hydrateHostedTemporalGeographyPage(page,options={}){
 if(!object(page)||page.stream===undefined)return hydrateResolvedTemporalGeography(page,options);
 if(!['records','withdrawals'].includes(page.stream)||!Array.isArray(page.records)||!Array.isArray(page.withdrawals)||!Array.isArray(page.sources))invalid('bounded stream');
 if(!options.complete&&(page.records.length>400||page.withdrawals.length>200))invalid('page limit');
 if(page.stream==='withdrawals'&&page.records.length)invalid('withdrawal stream contains claims');
 const release={id:page.release_id,status:'published',hierarchy_sha256:page.hierarchy_sha256,footprints_sha256:page.footprints_sha256},sources=Object.create(null),identities=new Map(),winners=new Set();
 for(const source of page.sources){if(!object(source)||!text(source.id)||Object.hasOwn(sources,source.id))invalid('source dictionary identity');sources[source.id]=source;}
 for(const row of page.records){
  if(!object(row)||!text(row.entity_id)||!levels.includes(row.entity_kind)||![0,1].includes(row.reference_active)||row.reference_parent_id!==null&&!text(row.reference_parent_id)||row.entity_valid_from!=null&&!validYear(row.entity_valid_from)||row.entity_valid_to!=null&&!(validYear(row.entity_valid_to)||row.entity_valid_to===2027)||row.entity_valid_from!=null&&row.entity_valid_to!=null&&row.entity_valid_from>=row.entity_valid_to)invalid('bounded reference identity');
  const key=`${row.collection}/${row.entity_id}`;if(winners.has(key))invalid('duplicate winning field');winners.add(key);
  const fields={id:row.entity_id,entity_id:row.entity_id,kind:row.entity_kind,active:row.reference_active,valid_from:row.entity_valid_from,valid_to:row.entity_valid_to,reference_parent_id:row.reference_parent_id},old=identities.get(row.entity_id);
  if(old&&['kind','active','valid_from','valid_to','reference_parent_id'].some(field=>old[field]!==fields[field]))invalid('inconsistent reference identity');
  const entity=old??{...fields,parent_id:row.reference_parent_id,historical_parent_id:null,membership_status:'reference',parent_context:'reference',existence_status:'unknown',membership_record:null,existence_record:null};
  if(row.collection==='memberships'){
   if(row.effective_parent_id!==(row.parent_id??row.reference_parent_id)||row.parent_context!==(row.parent_id==null?'reference':'historical')||row.membership_status!==(row.parent_id==null?'unknown':'dated'))invalid('bounded effective parent');
   entity.membership_record=row;entity.parent_id=row.effective_parent_id;entity.historical_parent_id=row.parent_id;entity.membership_status=row.membership_status;entity.parent_context=row.parent_context;
  }else if(row.collection==='existence'){entity.existence_record=row;entity.existence_status=row.value;}else invalid('bounded claim collection');
  identities.set(row.entity_id,entity);
 }
 for(const entity of identities.values()){const within=(entity.valid_from==null||entity.valid_from<=page.year)&&(entity.valid_to==null||entity.valid_to>page.year);entity.present=Boolean(entity.active)&&within&&entity.existence_status!=='not_exists';if(!within)entity.existence_status='not_exists';}
 const snapshot={...page,release,sources,entities:[...identities.values()],claims:page.records,excluded_entity_ids:[...identities.values()].filter(entity=>!entity.present).map(entity=>entity.id),footprints:{status:'reference',historical:false,footprints_sha256:release.footprints_sha256}};
 const hydrated=hydrateResolvedTemporalGeography(snapshot,options);
 return {...hydrated,records:hydrated.claims,sources:page.sources,source_dictionary:hydrated.sources};
}

/** Emit only already-resolved winning claims for the existing temporal
 * resolver. Explicit unknown parent evidence retains its source while using
 * the complete, visibly reference effective chain, never a fabricated parent.
 */
export function hostedTemporalHistory(snapshot,options={}){
 const page=hydrateHostedTemporalGeographyPage(snapshot,options),history=[];
 for(const entity of page.entities){
  const membership=entity.membership_record,existence=entity.existence_record;
  if(membership)history.push({...membership,field:'parent',value:entity.parent_id,language:'und',metadata:{...membership.metadata,reference_parent_id:entity.reference_parent_id,historical_parent_id:entity.historical_parent_id,parent_context:entity.parent_context,historical_membership_status:entity.membership_status},evidence_url:`/api/geography/temporal/evidence/memberships/${encodeURIComponent(membership.id)}`});
  if(existence)history.push({...existence,field:'existence',language:'und',evidence_url:`/api/geography/temporal/evidence/existence/${encodeURIComponent(existence.id)}`});
  if(!entity.present&&existence?.value!=='not_exists')history.push({id:`hosted-reference-exclusion:${page.release.id}:${entity.id}`,entity_id:entity.id,field:'existence',value:'not_exists',valid_from:page.year,valid_to:nextYear(page.year),source:'Published identity lifetime or inactive reference identity',method:'reference',status:'reference',language:'und',is_example:0,metadata:{resolution_only:true,reference_context:true,release_id:page.release.id,reason:'Exclusion from the resolved selected-year geographic identity set; not an assertion about habitation'}});
 }
 return history;
}

/** Call only after exhausting compatible pages from one complete revision, or
 * with a retained complete same-year cache. Never grant authority to a failed
 * read or an incomplete page. Withdrawals remove matching legacy claim IDs;
 * live winners/exclusions override fallback fields without deleting archives.
 */
export function mergeHostedTemporalHistory(referenceHistory,snapshot,{complete=false,...options}={}){
 if(complete!==true||!Array.isArray(referenceHistory)||snapshot?.next_cursor!=null)invalid('complete snapshot authority required');
 const page=hydrateHostedTemporalGeographyPage(snapshot,{...options,complete:true}),withdrawn=new Set(page.withdrawals.map(row=>`${row.collection}/${row.target_id}`)),authoritative=new Set();
 for(const row of page.entities){if(row.membership_record||!row.present)authoritative.add(`${row.id}/parent`);if(row.existence_record||!row.present)authoritative.add(`${row.id}/existence`);}
 const retained=referenceHistory.filter(row=>{
  const collection=row.field==='parent'?'memberships':row.field==='existence'?'existence':null;
  if(!collection)return true;
  if(withdrawn.has(`${collection}/${row.id}`))return false;
  return !(row.valid_from<=page.year&&row.valid_to>page.year&&authoritative.has(`${row.entity_id}/${row.field}`));
 });
 return [...retained,...hostedTemporalHistory({...page,stream:undefined,sources:page.source_dictionary??page.sources},options)];
}
