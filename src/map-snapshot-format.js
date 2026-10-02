import {validYear} from './model.js';
import {locationAttributes} from './attributes.js';

const geographicKinds=new Set(['location','province','area','region','subcontinent','continent','settlement']);
const object=value=>value!==null&&typeof value==='object'&&!Array.isArray(value);
const text=value=>typeof value==='string'&&Boolean(value.trim());
const interval=row=>validYear(row.valid_from)&&(validYear(row.valid_to)||row.valid_to===2027)&&row.valid_to>row.valid_from;
const invalid=detail=>{throw new Error(`Invalid map snapshot: ${detail}`);};
const flag=value=>value===undefined||[0,1,false,true].includes(value);

/** Validate compact network pages, then restore the existing resolver's claim
 * shape. The browser imports only this shared format module, never D1 services.
 */
export function hydrateMapSnapshotPage(page){
 if(!object(page)||!validYear(page.year)||!Number.isSafeInteger(page.revision)||page.revision<0)invalid('year or revision');
 if(page.next_cursor!==null&&!text(page.next_cursor))invalid('next cursor');
 for(const key of ['entities','records','names','retirements','aliases_truncated'])if(!Array.isArray(page[key]))invalid(`${key} must be an array`);
 if(!object(page.sources))invalid('source dictionary');
 const entities=new Map();
 for(const row of page.entities){if(!object(row)||!text(row.id)||!geographicKinds.has(row.kind)||entities.has(row.id))invalid('entity identity or kind');entities.set(row.id,row.kind);}
 if(page.aliases_truncated.some(id=>!text(id)||!entities.has(id))||new Set(page.aliases_truncated).size!==page.aliases_truncated.length)invalid('alias truncation identities');
 for(const [id,source] of Object.entries(page.sources)){
  if(!object(source)||source.id!==id||!text(source.name)||!text(source.license)||!text(source.vintage)||!['historical','reference','estimate','example'].includes(source.status)||!object(source.metadata)||!flag(source.metadata_truncated))invalid(`source ${id}`);
  if(!validYear(source.supported_from)||!(validYear(source.supported_to)||source.supported_to===2027)||source.supported_to<=source.supported_from||source.url!==null&&typeof source.url!=='string')invalid(`source interval or URL ${id}`);
 }
 const hydrate=row=>{
  if(!object(row)||!text(row.id)||!text(row.source_id)||!object(row.metadata)||!flag(row.metadata_truncated)||!Object.hasOwn(page.sources,row.source_id))invalid('claim or source identity');
  const source=page.sources[row.source_id];
  if(row.valid_from!==undefined&&(!interval(row)||row.valid_from>page.year||row.valid_to<=page.year||row.valid_from<source.supported_from||row.valid_to>source.supported_to))invalid('claim outside selected year or source support');
  const collection=row.attribute?'records':row.entity_id&&row.role?'names':row.collection,target=row.collection?row.target_id:row.id;
  return {...row,source:source.name,source_url:source.url,source_license:source.license,source_vintage:source.vintage,source_from:source.supported_from,source_to:source.supported_to,source_status:source.status,source_metadata:source.metadata,...(source.metadata_truncated?{source_metadata_truncated:true,...(!row.evidence_url&&collection?{evidence_url:`/api/evidence/${collection}/${encodeURIComponent(target)}`}:{})}:{})};
 };
 const fields=new Set(),claims=new Set();
 const records=page.records.map(row=>{
  const result=hydrate(row),key=`${result.location_id}/${result.attribute}`;
  if(entities.get(result.location_id)!=='location'||!locationAttributes.includes(result.attribute)||!interval(result)||!Object.hasOwn(result,'value')||result.value!==null&&(result.attribute==='population'?!Number.isSafeInteger(result.value)||result.value<0:!text(result.value))||fields.has(key)||claims.has(result.id))invalid('attribute identity, interval or scalar');
  fields.add(key);claims.add(result.id);return result;
 });
 const preferred=new Set(),nameClaims=new Set();
 const names=page.names.map(row=>{
  const result=hydrate(row);
  if(!entities.has(result.entity_id)||!text(result.name)||!text(result.language)||!['preferred','alias'].includes(result.role)||!interval(result)||result.field!=='name'||result.value!==result.name||result.name_role!==result.role||nameClaims.has(result.id)||result.role==='preferred'&&preferred.has(result.entity_id))invalid('dated name');
  nameClaims.add(result.id);if(result.role==='preferred')preferred.add(result.entity_id);return result;
 });
 const withdrawals=new Set();
 const retirements=page.retirements.map(row=>{
  const result=hydrate(row);
  if(!['records','names'].includes(result.collection)||!text(result.target_id)||!text(result.reason)||withdrawals.has(result.id))invalid('withdrawal');
  withdrawals.add(result.id);return result;
 });
 return {...page,records,names,retirements};
}
