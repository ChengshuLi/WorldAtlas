import {locationAttributes,unresolvedAttributeStatuses} from '../src/attributes.js';
import {validYear,ranks} from '../src/model.js';
import {validEnvironmentalClassification} from '../src/environment-classifications.js';
import {referenceMembership} from './geographic-releases.js';

export class RecordError extends Error{constructor(message,status=400){super(message);this.status=status;}}
const fail=(message,status=400)=>{throw new RecordError(message,status);};
const text=(v,name)=>{if(typeof v!=='string'||!v.trim()||v.length>2000)fail(`Invalid ${name}`);return v;};
const object=(v={})=>{if(!v||typeof v!=='object'||Array.isArray(v))fail('Metadata must be an object');if(JSON.stringify(v).length>16384)fail('Metadata exceeds 16 KiB');return v;};
const canonical=v=>Array.isArray(v)?v.map(canonical):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])):v;
const json=v=>JSON.stringify(canonical(v));
const example=v=>{v??=0;if(![0,1].includes(v))fail('is_example must be 0 or 1');return v;};
function dates(from,to,optional=false){if(optional&&from==null&&to==null)return [null,null];if(!validYear(from)||!(validYear(to)||to===2027)||to<=from)fail('Invalid half-open date interval; year zero is excluded');return [from,to];}
const clean=row=>row?Object.fromEntries(Object.entries(row).map(([k,v])=>[k,['metadata','source_metadata','value','counts'].includes(k)&&typeof v==='string'?JSON.parse(v):v])):null;
const all=async statement=>(await statement.all()).results||[];
const first=statement=>statement.first();
async function fingerprint(value){const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(json(value)));return [...new Uint8Array(bytes)].map(v=>v.toString(16).padStart(2,'0')).join('');}
const columns={
 retirements:['id','collection','target_id','source_id','reason','replacement_id','metadata'],
 sources:['id','name','url','license','vintage','supported_from','supported_to','status','metadata'],
 entity_types:['id','name','geographic_level','metadata'],entities:['id','kind','name','parent_id','valid_from','valid_to','source_id','reference_owner','is_example','active','metadata'],
 categories:['id','kind','name','source_id','metadata'],records:['id','location_id','attribute','value','category_id','valid_from','valid_to','method','status','source_id','is_example','metadata'],
 names:['id','entity_id','name','language','role','valid_from','valid_to','source_id','is_example','metadata'],
 relationships:['id','source_entity_id','target_entity_id','relationship_type','valid_from','valid_to','source_id','is_example','metadata'],
 media_links:['id','media_id','entity_id','role','caption','source_id','is_example','valid_from','valid_to','metadata'],
 media:['id','object_key','sha256','bytes','mime','name','license','attribution','source_id','status','metadata'],
};
const tables={retirements:'atlas_evidence_retirements',sources:'atlas_sources',entity_types:'atlas_entity_types',entities:'atlas_entities',categories:'atlas_categories',records:'atlas_attribute_records',names:'atlas_names',relationships:'atlas_relationships',media_links:'atlas_media_links',media:'atlas_media'};
function normalize(kind,r,{retainedEnvironmentalValue=false}={}){
 if(!r||typeof r!=='object'||Array.isArray(r))fail(`Invalid ${kind} row`);
 const base={...r,id:text(r.id,'stable ID'),metadata:json(object(r.metadata??{}))};
 if(kind==='sources'){
  const [supported_from,supported_to]=dates(r.supported_from??r.valid_from,r.supported_to??r.valid_to);let url=r.url??r.source_url??null;
  if(url!=null){text(url,'source URL');try{if(!['https:','http:'].includes(new URL(url).protocol))fail('Source URL must use HTTP(S)');}catch{fail('Invalid source URL');}}
  if(!['historical','reference','estimate','example'].includes(r.status))fail('Invalid source status');
  return {...base,name:text(r.name,'source name'),url,license:text(r.license,'source license'),vintage:text(String(r.vintage??''),'source vintage'),supported_from,supported_to};
 }
 if(kind==='entity_types'){
  const tiers=['location','province','area','region','subcontinent','continent'],expected=tiers.indexOf(r.id);
  if(expected>=0&&r.geographic_level!==expected||expected<0&&r.geographic_level!=null)fail('Geographic type must use its exact fixed tier');
  return {...base,name:text(r.name,'entity type'),geographic_level:expected>=0?expected:null};
 }
 if(kind==='entities'){
  const entityKind=text(r.kind??r.level,'entity kind');let valid_from=r.valid_from??null,valid_to=r.valid_to??null;
  if(valid_from!=null&&!validYear(valid_from)||valid_to!=null&&!(validYear(valid_to)||valid_to===2027)||valid_from!=null&&valid_to!=null&&valid_to<=valid_from)fail('Invalid entity lifetime');
  const source_id=r.source_id??null;if((valid_from!=null||valid_to!=null)&&!source_id)fail('Entity lifetime requires a source');if(source_id!=null)text(source_id,'source ID');
  return {...base,kind:entityKind,name:text(r.name,'reference name'),parent_id:r.parent_id??null,valid_from,valid_to,source_id,reference_owner:r.reference_owner??null,is_example:example(r.is_example),active:example(r.active??1)};
 }
 const source_id=text(r.source_id,'source ID');
 if(kind==='retirements'){if(!['records','names','relationships','media_links'].includes(r.collection))fail('Unsupported retirement collection');const replacement_id=r.replacement_id??null;if(replacement_id!=null){text(replacement_id,'replacement claim ID');if(replacement_id===r.target_id)fail('A claim cannot replace itself');}return {...base,collection:r.collection,target_id:text(r.target_id,'retired claim ID'),source_id,reason:text(r.reason,'retirement reason'),replacement_id};}
 if(kind==='categories'){if(!['owner','culture','religion'].includes(r.kind))fail('Invalid category kind');return {...base,kind:r.kind,name:text(r.name,'category name'),source_id};}
 if(kind==='records'){
  if(!locationAttributes.includes(r.attribute)||!Object.hasOwn(r,'value')||r.value===undefined)fail('Invalid location attribute');
  const value=r.value;
  if(value!=null){if(r.attribute==='population'){if(!Number.isSafeInteger(value)||value<0)fail('Population must be a nonnegative safe integer');}else text(value,'attribute scalar');}
  if(!retainedEnvironmentalValue&&!validEnvironmentalClassification(r.attribute,value))fail(`Invalid ${r.attribute} classification; choose a fixed classification ID or label, or null for unknown.`);
  const categorical=['owner','culture','religion'].includes(r.attribute),category_id=r.category_id??null;
  if(categorical&&value!=null&&!category_id)fail('Stable category_id is required');if(category_id!=null&&(!categorical||value==null))fail('Category ID requires a known categorical value');
  if(r.attribute==='rank'&&value!=null&&!ranks.includes(value))fail('Invalid rank');if(r.attribute==='habitation'&&value!=null&&!['inhabited','uninhabited','unknown'].includes(value))fail('Invalid habitation');
  const [valid_from,valid_to]=dates(r.valid_from,r.valid_to),is_example=example(r.is_example),method=r.method??'direct',status=r.status??(is_example?'example':value==null?'unknown':method==='reference'?'reference':method==='estimate'?'estimate':['derived','majority-area'].includes(method)?'derived':'sourced');
  if(!['direct','majority-area','derived','reference','estimate'].includes(method)||!['sourced','derived','reference','estimate','unknown','disputed','no-majority','example'].includes(status))fail('Invalid evidence method/status');
  if(unresolvedAttributeStatuses.includes(status)&&(value!==null||category_id!==null))fail('Unresolved attribute status requires null value and category_id');
  return {...base,location_id:text(r.location_id,'location ID'),attribute:r.attribute,value:json(value),category_id,valid_from,valid_to,method,status,source_id,is_example};
 }
 if(kind==='names'){
  const [valid_from,valid_to]=dates(r.valid_from,r.valid_to),role=r.role??'preferred';if(!['preferred','alias'].includes(role))fail('Invalid name role');
  return {...base,entity_id:text(r.entity_id,'entity ID'),name:text(r.name,'dated name'),language:text(r.language??'und','language'),role,valid_from,valid_to,source_id,is_example:example(r.is_example)};
 }
 if(kind==='relationships'){
  const [valid_from,valid_to]=dates(r.valid_from,r.valid_to,true);
  return {...base,source_entity_id:text(r.source_entity_id,'source entity ID'),target_entity_id:text(r.target_entity_id,'target entity ID'),relationship_type:text(r.relationship_type,'relationship type'),valid_from,valid_to,source_id,is_example:example(r.is_example)};
 }
 if(kind==='media_links'){
  const [valid_from,valid_to]=dates(r.valid_from,r.valid_to,true);if(r.caption!=null&&typeof r.caption!=='string')fail('Invalid media caption');
  return {...base,media_id:text(r.media_id,'media ID'),entity_id:text(r.entity_id,'entity ID'),role:text(r.role,'media role'),caption:r.caption??null,source_id,is_example:example(r.is_example),valid_from,valid_to};
 }
 if(kind==='media'){
  if(!/^[a-f0-9]{64}$/.test(r.sha256)||r.object_key!==`media/${r.sha256}`)fail('Media object key must match its SHA-256');
  if(!Number.isSafeInteger(r.bytes)||r.bytes<0||typeof r.mime!=='string'||!/^[-\w.+]+\/[-\w.+]+$/.test(r.mime))fail('Invalid media size/type');
  return {...base,object_key:r.object_key,sha256:r.sha256,bytes:r.bytes,mime:r.mime,name:text(r.name,'media name'),license:text(r.license,'media license'),attribution:text(r.attribution,'media attribution'),source_id,status:'ready'};
 }
 fail('Unsupported collection');
}
function insert(db,kind,row){const keys=columns[kind];return db.prepare(`INSERT OR IGNORE INTO ${tables[kind]} (${keys.join(',')}) VALUES (${keys.map(()=>'?').join(',')})`).bind(...keys.map(k=>row[k]??null));}
function expectedGeography(value){
 if(value===undefined)return null;
 if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).sort().join(',')!=='footprints_sha256,hierarchy_sha256,release_id')fail('Invalid expected_geography; provide release_id and both geographic hashes');
 text(value.release_id,'expected geographic release ID');for(const key of ['hierarchy_sha256','footprints_sha256'])if(!/^[a-f0-9]{64}$/.test(value[key]))fail(`Invalid expected geographic ${key}`);
 return {release_id:value.release_id,hierarchy_sha256:value.hierarchy_sha256,footprints_sha256:value.footprints_sha256};
}
const publicCounts=counts=>Object.fromEntries(Object.entries(counts).filter(([key])=>!['_retirement_ids','_expected_geography'].includes(key)));
function geographyGuard(db,geography,id,digest){
 // D1 batch holds the write transaction; PostgreSQL acquires the shared
 // publication/import advisory lock before this statement's fresh snapshot.
 // Invalid JSON deliberately aborts the complete transaction on a mismatch.
 return db.prepare(`SELECT json_extract(CASE WHEN EXISTS(SELECT 1 FROM atlas_ingestions WHERE id=? AND fingerprint=?) OR EXISTS(SELECT 1 FROM atlas_geographic_releases g WHERE g.id=? AND g.hierarchy_sha256=? AND g.footprints_sha256=? AND g.status='published' AND NOT EXISTS(SELECT 1 FROM atlas_geographic_releases newer WHERE newer.status='published' AND newer.version>g.version)) THEN 'true' ELSE 'ATLAS_GEOGRAPHY_CONFLICT' END,'$') AS expected_geography_matches`).bind(id,digest,geography.release_id,geography.hierarchy_sha256,geography.footprints_sha256);
}

/** Internal read-only admission for bootstrap's existing source/entity inputs.
 * Reuse the actual field normalizer without SQL or a public endpoint. Foreign
 * keys and immutable collisions still require the real transactional import.
 */
export function validateGeographicPrerequisiteBatch(payload){
 if(!payload||typeof payload!=='object'||Array.isArray(payload))fail('Import must be an object');
 if(new TextEncoder().encode(JSON.stringify(payload)).length>1024*1024)fail('Import exceeds 1 MiB',413);
 let total=0;const entities=[];
 for(const [key,rows]of Object.entries(payload)){
  if(key==='ingestion_id'){text(rows,'ingestion ID');continue;}
  if(!['sources','entities'].includes(key)||!Array.isArray(rows))fail('Invalid geographic prerequisite collection');
  const normalized=rows.map(row=>normalize(key,row)),ids=normalized.map(row=>row.id);
  if(new Set(ids).size!==ids.length)fail('Duplicate stable IDs within an import collection');
  total+=rows.length;if(key==='entities')entities.push(...normalized);
 }
 if(!total||total>250)fail('Import must contain 1–250 rows');
 const pending=new Map(entities.map(row=>[row.id,row]));
 while(pending.size){const ready=[...pending.values()].filter(row=>!row.parent_id||!pending.has(row.parent_id));if(!ready.length)fail('Entity parent cycle');for(const row of ready)pending.delete(row.id);}
}

export async function importBatch(db,payload){
 if(!payload||typeof payload!=='object'||Array.isArray(payload))fail('Import must be an object');
 if(new TextEncoder().encode(JSON.stringify(payload)).length>1024*1024)fail('Import exceeds 1 MiB',413);
 const geography=expectedGeography(payload.expected_geography);
 const aliases={units:'entities',attribute_entities:'categories',attribute_records:'records'},collections={};
 for(const [key,rows] of Object.entries(payload)){
  if(key==='ingestion_id'||key==='expected_geography')continue;const kind=aliases[key]??key;
  if(!columns[kind]||kind==='media'||!Array.isArray(rows))fail(`Invalid import collection: ${key}`);
  const target=collections[kind]??=[];
  for(const input of rows){
   // Grandfather only a byte-identical existing claim, never a new arbitrary
   // classification. Retrying old immutable evidence must remain idempotent.
   if(kind==='records'&&input&&!validEnvironmentalClassification(input.attribute,input.value)){
    const retained=normalize(kind,input,{retainedEnvironmentalValue:true});
    const previous=await first(db.prepare('SELECT * FROM atlas_attribute_records WHERE id=?').bind(retained.id));
    if(!previous||columns.records.some(key=>(retained[key]??null)!==(previous[key]??null)))fail(`Invalid ${input.attribute} classification; choose a fixed classification ID or label, or null for unknown.`);
    target.push(retained);
   }else target.push(normalize(kind,input));
  }
 }
 const total=Object.values(collections).reduce((n,v)=>n+v.length,0);if(!total||total>250)fail('Import must contain 1–250 rows');
 for(const rows of Object.values(collections))if(new Set(rows.map(r=>r.id)).size!==rows.length)fail('Duplicate stable IDs within an import collection');
 const digest=await fingerprint(geography?{collections,expected_geography:geography}:collections),id=payload.ingestion_id==null?digest:text(payload.ingestion_id,'ingestion ID');
 const prior=await first(db.prepare('SELECT * FROM atlas_ingestions WHERE id=?').bind(id));
 if(prior){if(prior.fingerprint!==digest)fail('Ingestion ID already identifies different evidence or geographic context',409);const retained=JSON.parse(prior.counts);return {ingestion_id:id,duplicate:true,counts:publicCounts(retained),revision:await revision(db),...(retained._expected_geography?{expected_geography:retained._expected_geography}:{})};}
 const sourceById=new Map((collections.sources??[]).map(r=>[r.id,r]));
 const entityById=new Map((collections.entities??[]).map(r=>[r.id,r]));
 for(const category of collections.categories??[]){
  const kind=category.kind==='owner'?'polity':category.kind;
  const existing=entityById.get(category.id)??await first(db.prepare('SELECT * FROM atlas_entities WHERE id=?').bind(category.id));
  if(existing){if(existing.kind!==kind)fail('Category must share a matching graph identity',409);continue;}
  const source=sourceById.get(category.source_id)??await first(db.prepare('SELECT * FROM atlas_sources WHERE id=?').bind(category.source_id));
  const entity=normalize('entities',{id:category.id,kind,name:category.name,source_id:category.source_id,is_example:source?.status==='example'?1:0,metadata:JSON.parse(category.metadata)});
  (collections.entities??=[]).push(entity);entityById.set(entity.id,entity);
 }
 for(const retirement of collections.retirements??[]){if(retirement.replacement_id!=null&&!collections[retirement.collection]?.some(row=>row.id===retirement.replacement_id)&&!await first(db.prepare(`SELECT id FROM ${tables[retirement.collection]} WHERE id=?`).bind(retirement.replacement_id)))fail('Replacement claim must exist or be submitted in the same import',409);}
 if(collections.entities){const pending=new Map(collections.entities.map(r=>[r.id,r])),ordered=[];while(pending.size){const ready=[...pending.values()].filter(r=>!r.parent_id||!pending.has(r.parent_id));if(!ready.length)fail('Entity parent cycle');for(const r of ready){ordered.push(r);pending.delete(r.id);}}collections.entities=ordered;}
 const statements=geography?[geographyGuard(db,geography,id,digest)]:[],counts={};for(const kind of ['sources','entity_types','entities','categories','retirements','records','names','relationships','media_links']){counts[kind]=collections[kind]?.length??0;for(const row of collections[kind]??[])statements.push(insert(db,kind,row));}
 statements.push(db.prepare('INSERT OR IGNORE INTO atlas_ingestions(id,fingerprint,counts,created_at) VALUES (?,?,?,?)').bind(id,digest,json({...counts,...(geography?{_expected_geography:geography}:{}),...(collections.retirements?.length?{_retirement_ids:collections.retirements.map(r=>r.id)}:{})}),Date.now()));
 let result;try{result=await db.batch(statements);}catch(e){
  if(e.commit_status==='unknown'){const error=new RecordError('Import outcome is unknown; retry the identical ingestion to verify its original receipt',503);error.retryable=true;error.commit_status='unknown';throw error;}
  if(geography&&(e.sqlstate==='22P02'||/malformed JSON|ATLAS_GEOGRAPHY_CONFLICT/i.test(e.message))){const error=new RecordError('Published geography changed or does not match the pinned import; no records were committed',409);error.retryable=true;throw error;}
  const error=new RecordError(`Import rejected: ${e.message}`,e.retryable?503:409);if(e.retryable)error.retryable=true;throw error;
 }
 return {ingestion_id:id,duplicate:result.at(-1)?.meta?.changes===0,counts,revision:await revision(db),...(geography?{expected_geography:geography}:{})};
}
async function revision(db){return (await first(db.prepare('SELECT coalesce(max(rowid),0) revision FROM atlas_ingestions'))).revision;}
async function unchangedRevision(db,expected){if(await revision(db)!==expected){const error=new RecordError('Historical content changed while reading; retry the snapshot',409);error.retryable=true;throw error;}return expected;}
export async function attributesAt(db,year,{examples=false,cursor='',limit=250,locationIds}={}){
 if(!validYear(year))fail('Invalid selected year');limit=Math.max(1,Math.min(250,Number.isInteger(limit)?limit:250));if(cursor)text(cursor,'cursor');
 if(locationIds!=null&&(!Array.isArray(locationIds)||locationIds.length>250||locationIds.some(id=>typeof id!=='string'||!id.trim())))fail('Invalid locationIds filter');
 const filter=locationIds==null?'':' AND r.location_id IN (SELECT value FROM json_each(?))',params=[year,year,Number(Boolean(examples)),cursor,Number(Boolean(examples)),year,year,...(locationIds==null?[]:[JSON.stringify(locationIds)]),limit+1];
 const before=await revision(db);
 const rows=await all(db.prepare(`SELECT r.*,s.name source,s.url source_url,s.license source_license,s.vintage source_vintage,s.supported_from source_from,s.supported_to source_to,s.status source_status,s.metadata source_metadata FROM atlas_attribute_records r JOIN atlas_sources s ON s.id=r.source_id JOIN atlas_entities e ON e.id=r.location_id WHERE r.valid_from<=? AND r.valid_to>? AND r.is_example<=? AND r.id>? AND NOT EXISTS(SELECT 1 FROM atlas_evidence_retirements retired WHERE retired.collection='records' AND retired.target_id=r.id) AND e.active=1 AND e.is_example<=? AND (e.valid_from IS NULL OR e.valid_from<=?) AND (e.valid_to IS NULL OR e.valid_to>?)${filter} ORDER BY r.id LIMIT ?`).bind(...params));
 const next_cursor=rows.length>limit?rows[limit-1].id:null;
 return {year,records:rows.slice(0,limit).map(clean),next_cursor,revision:await unchangedRevision(db,before)};
}
// Retirements are permanent claim withdrawals, filtered by the claim's supported
// interval for map snapshots. Returning their IDs prevents prepared fallbacks
// from restoring withdrawn evidence when the live record itself is absent.
export async function retirementsAt(db,year,{examples=false,cursor='',limit=250,mapOnly=false}={}){
 if(!validYear(year))fail('Invalid selected year');limit=Math.max(1,Math.min(250,Number.isInteger(limit)?limit:250));if(cursor)text(cursor,'cursor');
 const before=await revision(db);
 const rows=await all(db.prepare(`SELECT t.* FROM atlas_evidence_retirements t WHERE t.id>? AND (
 (t.collection='records' AND EXISTS(SELECT 1 FROM atlas_attribute_records r JOIN atlas_entities e ON e.id=r.location_id WHERE r.id=t.target_id AND r.valid_from<=? AND r.valid_to>? AND r.is_example<=? AND e.is_example<=?)) OR
 (t.collection='names' AND EXISTS(SELECT 1 FROM atlas_names n JOIN atlas_entities e ON e.id=n.entity_id WHERE n.id=t.target_id AND n.valid_from<=? AND n.valid_to>? AND n.is_example<=? AND e.is_example<=? AND (?=0 OR e.kind IN ('continent','subcontinent','region','area','province','location','settlement'))))) ORDER BY t.id LIMIT ?`).bind(cursor,year,year,Number(Boolean(examples)),Number(Boolean(examples)),year,year,Number(Boolean(examples)),Number(Boolean(examples)),Number(Boolean(mapOnly)),limit+1));
 return {year,records:rows.slice(0,limit).map(clean),next_cursor:rows.length>limit?rows[limit-1].id:null,revision:await unchangedRevision(db,before)};
}
export async function entityProfile(db,id,year=2026,{examples=false,releaseId=null}={}){
 text(id,'entity ID');if(!validYear(year))fail('Invalid selected year');const row=clean(await first(db.prepare('SELECT * FROM atlas_entities WHERE id=?').bind(id)));if(!row||row.is_example&&!examples)return null;
 const names=(await all(db.prepare('SELECT n.*,s.name source,s.url source_url,s.license source_license,s.vintage source_vintage,s.supported_from source_from,s.supported_to source_to,s.status source_status,s.metadata source_metadata FROM atlas_names n JOIN atlas_sources s ON s.id=n.source_id WHERE entity_id=? AND valid_from<=? AND valid_to>? AND is_example<=? AND NOT EXISTS(SELECT 1 FROM atlas_evidence_retirements retired WHERE retired.collection=\'names\' AND retired.target_id=n.id) ORDER BY n.is_example,CASE s.status WHEN \'historical\' THEN 0 WHEN \'reference\' THEN 1 ELSE 2 END,CASE language WHEN \'en\' THEN 0 WHEN \'und\' THEN 1 ELSE 2 END,id LIMIT 250').bind(id,year,year,Number(Boolean(examples))))).map(clean);
 const relationships=(await all(db.prepare('SELECT r.*,s.name source,s.url source_url FROM atlas_relationships r JOIN atlas_sources s ON s.id=r.source_id JOIN atlas_entities outgoing ON outgoing.id=r.source_entity_id JOIN atlas_entities incoming ON incoming.id=r.target_entity_id WHERE (source_entity_id=? OR target_entity_id=?) AND (r.valid_from IS NULL OR (r.valid_from<=? AND r.valid_to>?)) AND r.is_example<=? AND outgoing.is_example<=? AND incoming.is_example<=? AND NOT EXISTS(SELECT 1 FROM atlas_evidence_retirements retired WHERE retired.collection=\'relationships\' AND retired.target_id=r.id) ORDER BY r.id LIMIT 251').bind(id,id,year,year,Number(Boolean(examples)),Number(Boolean(examples)),Number(Boolean(examples))))).map(clean);
 const media=(await all(db.prepare('SELECT l.*,m.object_key,m.sha256,m.bytes,m.mime,m.name,m.license,m.attribution,s.name source,s.url source_url FROM atlas_media_links l JOIN atlas_media m ON m.id=l.media_id JOIN atlas_sources s ON s.id=l.source_id WHERE entity_id=? AND (valid_from IS NULL OR (valid_from<=? AND valid_to>?)) AND l.is_example<=? AND NOT EXISTS(SELECT 1 FROM atlas_evidence_retirements retired WHERE retired.collection=\'media_links\' AND retired.target_id=l.id) AND m.status IN (\'ready\',\'published\') ORDER BY l.id LIMIT 251').bind(id,year,year,Number(Boolean(examples))))).map(clean);
 const exists=(row.valid_from==null||year>=row.valid_from)&&(row.valid_to==null||year<row.valid_to);
 const geographic=['location','province','area','region','subcontinent','continent'].includes(row.kind)?await referenceMembership(db,id,{releaseId}):null;
 const membership=geographic?.membership,referenceName=membership?.resolved_reference_name??row.name;
 const referenceFields=membership?{name:referenceName,parent_id:membership.parent_id,active:membership.active}:{};
 return {...row,...referenceFields,original_registry:{name:row.name,parent_id:row.parent_id,active:row.active,source_id:row.source_id},reference_geography:geographic,year,status:exists?(year===2026?'reference':'unknown'):'not_exists',display_name:exists?(names.find(n=>n.role==='preferred')?.name??(year===2026?referenceName:null)):null,names,relationships:relationships.slice(0,250).map(r=>({...r,date_status:r.valid_from==null?'unknown':'dated'})),relationships_truncated:relationships.length>250,media:media.slice(0,250).map(r=>({...r,date_status:r.valid_from==null?'unknown':'dated'})),media_truncated:media.length>250};
}
export async function namesAt(db,year,{examples=false,cursor='',limit=250,mapOnly=false}={}){
 if(!validYear(year))fail('Invalid selected year');limit=Math.max(1,Math.min(250,Number.isInteger(limit)?limit:250));if(cursor)text(cursor,'cursor');
 const before=await revision(db);
 const rows=await all(db.prepare('SELECT n.*,s.name source,s.url source_url,s.license source_license,s.vintage source_vintage,s.supported_from source_from,s.supported_to source_to,s.status source_status,s.metadata source_metadata FROM atlas_names n JOIN atlas_sources s ON s.id=n.source_id JOIN atlas_entities e ON e.id=n.entity_id WHERE n.valid_from<=? AND n.valid_to>? AND n.is_example<=? AND n.id>? AND NOT EXISTS(SELECT 1 FROM atlas_evidence_retirements retired WHERE retired.collection=\'names\' AND retired.target_id=n.id) AND e.is_example<=? AND (e.valid_from IS NULL OR e.valid_from<=?) AND (e.valid_to IS NULL OR e.valid_to>?) AND (?=0 OR e.kind IN (\'continent\',\'subcontinent\',\'region\',\'area\',\'province\',\'location\',\'settlement\')) ORDER BY n.id LIMIT ?').bind(year,year,Number(Boolean(examples)),cursor,Number(Boolean(examples)),year,year,Number(Boolean(mapOnly)),limit+1));
 return {year,records:rows.slice(0,limit).map(row=>{const r=clean(row);return {...r,field:'name',value:r.name,name_role:r.role};}),next_cursor:rows.length>limit?rows[limit-1].id:null,revision:await unchangedRevision(db,before)};
}
export async function mediaById(db,id){text(id,'media ID');return clean(await first(db.prepare('SELECT * FROM atlas_media WHERE id=?').bind(id)));}
export async function validateMedia(db,input){
 const row=normalize('media',input);if(!await first(db.prepare('SELECT id FROM atlas_sources WHERE id=?').bind(row.source_id)))fail('Unknown media source');
 const prior=await mediaById(db,row.id);
 if(prior){const expected=clean(row);if(columns.media.filter(k=>k!=='status').some(k=>json(prior[k])!==json(expected[k])))fail('Media ID already identifies a different immutable object',409);return {...prior,existing:true};}
 const same=await first(db.prepare('SELECT id FROM atlas_media WHERE object_key=?').bind(row.object_key));if(same)fail('Media digest already has a registered identity',409);
 return {...clean(row),existing:false};
}
export async function registerMedia(db,input){const checked=await validateMedia(db,input);if(checked.existing)return checked;const row=normalize('media',input);await db.batch([insert(db,'media',row)]);return mediaById(db,row.id);}
export async function storageOverview(db){
 const counts={};for(const [name,table] of Object.entries(tables))counts[name]=(await first(db.prepare(`SELECT count(*) n FROM ${table}`))).n;
 const bytes=(await first(db.prepare('SELECT coalesce(sum(bytes),0) bytes FROM atlas_media'))).bytes;
 return {counts,media_bytes:bytes,revision:await revision(db),record_policy:'One sourced scalar per location attribute and date; append-only evidence; unsupported values remain unknown'};
}

export async function evidenceHistory(db,collection,targetId,{examples=false}={}){
 if(!['records','names','relationships','media_links'].includes(collection))fail('Unsupported evidence collection');text(targetId,'claim ID');
 const claim=clean(await first(db.prepare(`SELECT c.*,s.name source,s.url source_url,s.license source_license,s.vintage source_vintage,s.supported_from source_from,s.supported_to source_to,s.status source_status,s.metadata source_metadata FROM ${tables[collection]} c JOIN atlas_sources s ON s.id=c.source_id WHERE c.id=?`).bind(targetId)));
 if(!claim||claim.is_example&&!examples)return null;
 const retirement=clean(await first(db.prepare('SELECT r.*,s.name source,s.url source_url,s.license source_license,s.vintage source_vintage,s.supported_from source_from,s.supported_to source_to,s.status source_status,s.metadata source_metadata FROM atlas_evidence_retirements r JOIN atlas_sources s ON s.id=r.source_id WHERE r.collection=? AND r.target_id=?').bind(collection,targetId)));
 let replacement=null;if(retirement?.replacement_id){replacement=clean(await first(db.prepare(`SELECT c.*,s.name source,s.url source_url FROM ${tables[collection]} c JOIN atlas_sources s ON s.id=c.source_id WHERE c.id=?`).bind(retirement.replacement_id)));if(replacement?.is_example&&!examples)replacement=null;}
 return {collection,claim,status:retirement?(retirement.replacement_id?'superseded':'withdrawn'):'active',retirement,replacement};
}
