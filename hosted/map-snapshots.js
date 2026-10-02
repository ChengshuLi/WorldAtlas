import {validYear} from '../src/model.js';
import {RecordError} from './records.js';
import {locationAttributes} from '../src/attributes.js';
export {hydrateMapSnapshotPage} from '../src/map-snapshot-format.js';

const kinds="'location','province','area','region','subcontinent','continent','settlement'";
const query=async statement=>(await statement.all()).results??[];
const revision=async db=>(await db.prepare('SELECT coalesce(max(rowid),0) revision FROM atlas_ingestions').first()).revision;
const clean=row=>Object.fromEntries(Object.entries(row).map(([key,value])=>[key,['value','metadata'].includes(key)&&typeof value==='string'?JSON.parse(value):value]));
// Match src/attributes.js, including explicit unknowns and opt-in examples.
const attributePriority=row=>row.is_example?40+(row.evidence_priority||0):row.method==='direct'?(row.evidence_priority||0):['majority-area','derived'].includes(row.method)?10:row.method==='reference'?20:30;
const namePriority=row=>Number(Boolean(row.is_example))*100+(row.source_status==='reference'?10:0)+(row.language==='en'?0:row.language==='und'?1:2);
const before=(a,b,priority)=>priority(a)<priority(b)||priority(a)===priority(b)&&String(a.id)<String(b.id);
const proofFlags=['estimate','estimated','is_estimate','modeled','modelled','rounded','legacy_snapshot','legacy_attributes'];
const truth=(column,key)=>`CASE json_type(${column},'$.${key}') WHEN 'array' THEN 1 WHEN 'object' THEN 1 WHEN 'text' THEN CASE WHEN json_extract(${column},'$.${key}')!='' THEN 1 ELSE 0 END ELSE CASE WHEN coalesce(json_extract(${column},'$.${key}'),0)!=0 THEN 1 ELSE 0 END END`;
const proofMetadata=column=>`json_object(${proofFlags.map(key=>`'${key}',${truth(column,key)}`).join(',')},'rounding',CASE WHEN json_type(${column},'$.rounding') IS NOT NULL AND json_type(${column},'$.rounding')!='null' THEN 1 ELSE NULL END,'model',CASE WHEN json_type(${column},'$.model') IS NOT NULL AND json_type(${column},'$.model')!='null' THEN 1 ELSE NULL END,'precision',CASE WHEN json_type(${column},'$.precision')='object' THEN '[object Object]' WHEN json_type(${column},'$.precision')='array' THEN json_extract(${column},'$.precision') WHEN lower(coalesce(json_extract(${column},'$.precision'),'')) LIKE '%round%' OR lower(coalesce(json_extract(${column},'$.precision'),'')) LIKE '%model%' OR lower(coalesce(json_extract(${column},'$.precision'),'')) LIKE '%estimate%' OR lower(coalesce(json_extract(${column},'$.precision'),'')) LIKE '%approx%' THEN 'approximate; original precision retained in evidence' ELSE substr(json_extract(${column},'$.precision'),1,256) END)`;
const boundedMetadata=(alias,bytes,proof=false)=>`CASE WHEN length(CAST(${alias}.metadata AS BLOB))<=${bytes} THEN ${alias}.metadata ELSE ${proof?proofMetadata(`${alias}.metadata`):"'{}'"} END metadata,CASE WHEN length(CAST(${alias}.metadata AS BLOB))>${bytes} THEN 1 ELSE 0 END metadata_truncated`;
const attributeColumns=['id','location_id','attribute','value','category_id','valid_from','valid_to','method','status','source_id','is_example'].map(key=>`r.${key}`).join(',');
const nameColumns=['id','entity_id','name','language','role','valid_from','valid_to','source_id','is_example'].map(key=>`n.${key}`).join(',');
const withdrawalColumns=['id','collection','target_id','source_id','reason','replacement_id'].map(key=>`t.${key}`).join(',');
const numericAttributePriority="CASE WHEN r.is_example=1 THEN 40 WHEN r.method='direct' THEN 0 WHEN r.method IN ('majority-area','derived') THEN 10 WHEN r.method='reference' THEN 20 ELSE 30 END";
const numericNamePriority="(n.is_example*100+CASE WHEN s.status='reference' THEN 10 ELSE 0 END+CASE n.language WHEN 'en' THEN 0 WHEN 'und' THEN 1 ELSE 2 END)";
const statementRowsLimit=50000,responseBytesLimit=8*1024*1024;

export const mapSnapshotQueries={
 entities:`SELECT id,kind,active FROM atlas_entities INDEXED BY entities_kind_id WHERE kind IN (${kinds}) AND active=1 AND id>? AND is_example<=? AND (valid_from IS NULL OR valid_from<=?) AND (valid_to IS NULL OR valid_to>?) ORDER BY id LIMIT ?`,
 attributes:`SELECT * FROM (SELECT ${attributeColumns},${boundedMetadata('r',1024,true)},DENSE_RANK() OVER (PARTITION BY r.location_id,r.attribute ORDER BY ${numericAttributePriority}) __priority_rank FROM json_each(?) page CROSS JOIN json_each('${JSON.stringify(locationAttributes)}') attribute CROSS JOIN atlas_attribute_records r INDEXED BY attributes_location_dates ON r.location_id=page.value AND r.attribute=attribute.value JOIN atlas_entities e ON e.id=r.location_id WHERE r.valid_from<=? AND r.valid_to>? AND r.is_example<=? AND e.kind='location' AND e.active=1 AND NOT EXISTS(SELECT 1 FROM atlas_evidence_retirements t WHERE t.collection='records' AND t.target_id=r.id)) WHERE __priority_rank=1 LIMIT ${statementRowsLimit+1}`,
 names:`SELECT * FROM (SELECT ${nameColumns},${boundedMetadata('n',1024)},s.status source_status,DENSE_RANK() OVER (PARTITION BY n.entity_id,n.role ORDER BY ${numericNamePriority}) __priority_rank,ROW_NUMBER() OVER (PARTITION BY n.entity_id,n.role ORDER BY n.id) __alias_order,COUNT(*) OVER (PARTITION BY n.entity_id,n.role) __alias_total FROM json_each(?) page CROSS JOIN atlas_names n INDEXED BY names_entity_dates ON n.entity_id=page.value JOIN atlas_sources s ON s.id=n.source_id WHERE n.valid_from<=? AND n.valid_to>? AND n.is_example<=? AND NOT EXISTS(SELECT 1 FROM atlas_evidence_retirements t WHERE t.collection='names' AND t.target_id=n.id)) WHERE (role='preferred' AND __priority_rank=1) OR (role='alias' AND __alias_order<=?) LIMIT ${statementRowsLimit+1}`,
 retirements:`SELECT ${withdrawalColumns},${boundedMetadata('t',1024)} FROM json_each(?) page CROSS JOIN atlas_attribute_records r INDEXED BY attributes_location_dates ON r.location_id=page.value JOIN atlas_evidence_retirements t ON t.collection='records' AND t.target_id=r.id WHERE r.valid_from<=? AND r.valid_to>? AND r.is_example<=? UNION ALL SELECT ${withdrawalColumns},${boundedMetadata('t',1024)} FROM json_each(?) page CROSS JOIN atlas_names n INDEXED BY names_entity_dates ON n.entity_id=page.value JOIN atlas_evidence_retirements t ON t.collection='names' AND t.target_id=n.id WHERE n.valid_from<=? AND n.valid_to>? AND n.is_example<=? LIMIT ${statementRowsLimit+1}`,
 sources:`SELECT s.id,s.name,s.url,s.license,s.vintage,s.supported_from,s.supported_to,s.status,${boundedMetadata('s',2048)} FROM json_each(?) page CROSS JOIN atlas_sources s ON s.id=page.value LIMIT ${statementRowsLimit+1}`,
};

/** One page contains complete winners/withdrawals for its entity IDs. Prepared
 * caches can therefore merge by claim identity without restoring retired data.
 * Source metadata occurs once per page; evidence remains individually queryable.
 */
export async function mapSnapshotPage(db,year,{examples=false,cursor='',limit=1000,aliasLimit=5}={}){
 if(!validYear(year))throw new RecordError('Invalid selected year');
 if(typeof cursor!=='string'||cursor.length>2000||cursor&&!cursor.trim())throw new RecordError('Invalid map cursor');
 if(!Number.isInteger(limit)||limit<1||limit>1000)throw new RecordError('Map entity page limit must be between 1 and 1000');
 if(!Number.isInteger(aliasLimit)||aliasLimit<0||aliasLimit>5)throw new RecordError('Map alias limit must be between 0 and 5');
 const initial=await revision(db),enabled=Number(Boolean(examples));
 const eligible=await query(db.prepare(mapSnapshotQueries.entities).bind(cursor,enabled,year,year,limit+1));
 const entities=eligible.slice(0,limit),ids=JSON.stringify(entities.map(entity=>entity.id));
 const [attributes,names,retirements]=entities.length?await Promise.all([
  query(db.prepare(mapSnapshotQueries.attributes).bind(ids,year,year,enabled)),
  query(db.prepare(mapSnapshotQueries.names).bind(ids,year,year,enabled,aliasLimit+1)),
  query(db.prepare(mapSnapshotQueries.retirements).bind(ids,year,year,enabled,ids,year,year,enabled)),
 ]):[[],[],[]];
 const tooLarge=()=>{const error=new RecordError('Map snapshot page exceeds its operational limit; retry with fewer entities',413);error.retryable=true;error.suggested_limit=Math.max(1,Math.floor(limit/2));return error;};
 if([attributes,names,retirements].some(rows=>rows.length>statementRowsLimit))throw tooLarge();
 const fields=new Map(),preferred=new Map(),aliases=new Map();
 const claim=(raw,collection)=>{const row=clean(raw);for(const key of ['__priority_rank','__alias_order','__alias_total'])delete row[key];if(row.metadata_truncated)row.evidence_url=`/api/evidence/${collection}/${encodeURIComponent(row.id)}`;else delete row.metadata_truncated;return row;};
 for(const raw of attributes){const row=claim(raw,'records'),key=`${row.location_id}/${row.attribute}`,old=fields.get(key);if(!old||before(row,old,attributePriority))fields.set(key,row);}
 const aliasTotals=new Map();
 for(const raw of names){const row=claim(raw,'names');if(row.role==='alias'){aliasTotals.set(row.entity_id,raw.__alias_total);const rows=aliases.get(row.entity_id)??[];rows.push(row);aliases.set(row.entity_id,rows);}else{const old=preferred.get(row.entity_id);if(!old||before(row,old,namePriority))preferred.set(row.entity_id,row);}}
 const selectedNames=[...preferred.values()],aliasesTruncated=[];
 for(const [id,rows] of aliases){selectedNames.push(...rows.slice(0,aliasLimit));if(aliasTotals.get(id)>aliasLimit)aliasesTruncated.push(id);}
 const records=[...fields.values()],withdrawals=retirements.map(clean);
 const sourceIds=[...new Set([...records,...selectedNames,...withdrawals].map(row=>row.source_id))];
 const sources=sourceIds.length?await query(db.prepare(mapSnapshotQueries.sources).bind(JSON.stringify(sourceIds))):[];
 if(await revision(db)!==initial){const error=new RecordError('Historical content changed while reading; retry the map snapshot',409);error.retryable=true;throw error;}
 const result={year,revision:initial,next_cursor:eligible.length>limit?entities.at(-1).id:null,entities:entities.map(({id,kind})=>({id,kind})),records,names:selectedNames.map(row=>({...row,field:'name',value:row.name,name_role:row.role})),retirements:withdrawals,sources:Object.fromEntries(sources.map(row=>[row.id,clean(row)])),aliases_truncated:aliasesTruncated};
 if(new TextEncoder().encode(JSON.stringify(result)).byteLength>responseBytesLimit)throw tooLarge();
 return result;
}
