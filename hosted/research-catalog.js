import {RecordError} from './records.js';
import {validYear} from '../src/model.js';

const fail=message=>{throw new RecordError(message,400);};
const text=(value,label,max=2000)=>{if(typeof value!=='string'||!value.trim()||value.length>max)fail(`Invalid ${label}`);return value;};
const clean=row=>Object.fromEntries(Object.entries(row).map(([key,value])=>[key,['metadata','source_metadata'].includes(key)&&typeof value==='string'?JSON.parse(value):value]));
const all=async statement=>(await statement.all()).results||[];
async function revision(db){return (await db.prepare('SELECT coalesce(max(rowid),0) revision FROM atlas_ingestions').first()).revision;}
async function sameRevision(db,before){if(await revision(db)!==before){const error=new RecordError('Historical content changed while reading; retry the page',409);error.retryable=true;throw error;}return before;}
function paging({cursor='',limit=250}={}){
 if(cursor)text(cursor,'cursor');
 if(!Number.isSafeInteger(limit)||limit<1)fail('Page limit must be a positive integer');
 return {cursor,limit:Math.min(limit,250)};
}
function page(rows,limit){return {records:rows.slice(0,limit).map(clean),next_cursor:rows.length>limit?rows[limit-1].id:null};}

/** Search immutable identities before creating a source, category or entity.
 * These undated labels aid matching; they do not establish ancient names or state.
 */
export async function catalogPage(db,collection,{q='',kind=null,cursor='',limit=250,examples=false,active=null}={}){
 const policies={sources:{table:'atlas_sources',kind:'status',example:"c.status!='example'"},categories:{table:'atlas_categories',kind:'kind',example:"s.status!='example' AND coalesce(e.is_example,0)=0"},entities:{table:'atlas_entities',kind:'kind',example:'c.is_example=0'}};
 if(!Object.hasOwn(policies,collection))fail('Catalog collection must be sources, categories or entities');
 const policy=policies[collection];
 ({cursor,limit}=paging({cursor,limit}));
 if(typeof q!=='string'||q.length>256)fail('Search text must contain at most 256 characters');
 q=q.trim();if(kind!=null)text(kind,'catalog kind',100);
 if(active!=null&&(![true,false,0,1].includes(active)||collection!=='entities'))fail('Active filter applies only to entities and must be boolean');
 const before=await revision(db),params=[cursor],where=['c.id>?'];
 if(q){where.push('(instr(lower(c.name),lower(?))>0 OR instr(lower(c.id),lower(?))>0)');params.push(q,q);}
 if(kind!=null){where.push(`c.${policy.kind}=?`);params.push(kind);}
 if(!examples)where.push(policy.example);
 if(active!=null){where.push('c.active=?');params.push(Number(Boolean(active)));}
 const joins=collection==='categories'?' JOIN atlas_sources s ON s.id=c.source_id LEFT JOIN atlas_entities e ON e.id=c.id':'';
 const rows=await all(db.prepare(`SELECT c.* FROM ${policy.table} c${joins} WHERE ${where.join(' AND ')} ORDER BY c.id LIMIT ?`).bind(...params,limit+1));
 return {collection,...page(rows,limit),revision:await sameRevision(db,before),identity_context:'Undated identity registry; names and attributes require their own supported evidence intervals.'};
}

async function entityForPage(db,id,year,examples){
 text(id,'entity ID');if(!validYear(year))fail('Invalid selected year');
 const entity=await db.prepare('SELECT id,is_example FROM atlas_entities WHERE id=?').bind(id).first();
 return entity&&(!entity.is_example||examples)?entity:null;
}
const sourceColumns='s.name source,s.url source_url,s.license source_license,s.vintage source_vintage,s.supported_from source_from,s.supported_to source_to,s.status source_status,s.metadata source_metadata';

/** Page all incoming/outgoing links; preserve the profile's date/example policy. */
export async function entityRelationshipsPage(db,id,year=2026,{examples=false,cursor='',limit=250}={}){
 ({cursor,limit}=paging({cursor,limit}));const before=await revision(db);
 if(!await entityForPage(db,id,year,examples)){await sameRevision(db,before);return null;}
 const rows=await all(db.prepare(`SELECT r.*,${sourceColumns} FROM atlas_relationships r
 JOIN atlas_sources s ON s.id=r.source_id
 JOIN atlas_entities outgoing ON outgoing.id=r.source_entity_id JOIN atlas_entities incoming ON incoming.id=r.target_entity_id
 WHERE (r.source_entity_id=? OR r.target_entity_id=?) AND r.id>?
 AND (r.valid_from IS NULL OR (r.valid_from<=? AND r.valid_to>?))
 AND r.is_example<=? AND outgoing.is_example<=? AND incoming.is_example<=?
 AND NOT EXISTS(SELECT 1 FROM atlas_evidence_retirements retired WHERE retired.collection='relationships' AND retired.target_id=r.id)
 ORDER BY r.id LIMIT ?`).bind(id,id,cursor,year,year,Number(Boolean(examples)),Number(Boolean(examples)),Number(Boolean(examples)),limit+1));
 const result=page(rows,limit);result.records=result.records.map(row=>({...row,date_status:row.valid_from==null?'unknown':'dated'}));
 return {entity_id:id,year,...result,revision:await sameRevision(db,before)};
}

/** Page links rather than blobs; object bytes retain the existing media endpoint. */
export async function entityMediaPage(db,id,year=2026,{examples=false,cursor='',limit=250}={}){
 ({cursor,limit}=paging({cursor,limit}));const before=await revision(db);
 if(!await entityForPage(db,id,year,examples)){await sameRevision(db,before);return null;}
 const rows=await all(db.prepare(`SELECT l.*,m.object_key,m.sha256,m.bytes,m.mime,m.name,m.license,m.attribution,${sourceColumns}
 FROM atlas_media_links l JOIN atlas_media m ON m.id=l.media_id JOIN atlas_sources s ON s.id=l.source_id
 WHERE l.entity_id=? AND l.id>? AND (l.valid_from IS NULL OR (l.valid_from<=? AND l.valid_to>?)) AND l.is_example<=?
 AND NOT EXISTS(SELECT 1 FROM atlas_evidence_retirements retired WHERE retired.collection='media_links' AND retired.target_id=l.id)
 AND m.status IN ('ready','published') ORDER BY l.id LIMIT ?`).bind(id,cursor,year,year,Number(Boolean(examples)),limit+1));
 const result=page(rows,limit);result.records=result.records.map(row=>({...row,date_status:row.valid_from==null?'unknown':'dated'}));
 return {entity_id:id,year,...result,revision:await sameRevision(db,before)};
}

const countedTables={sources:'atlas_sources',entity_types:'atlas_entity_types',entities:'atlas_entities',categories:'atlas_categories',records:'atlas_attribute_records',names:'atlas_names',relationships:'atlas_relationships',media_links:'atlas_media_links',media:'atlas_media',retirements:'atlas_evidence_retirements',ingestions:'atlas_ingestions',geographic_releases:'atlas_geographic_releases',geographic_memberships:'atlas_geographic_memberships',geographic_changes:'atlas_geographic_changes'};

/** Diagnostic measurements, never a claim that the managed Site has a known quota. */
export async function capacityReport(db,{databaseBudgetBytes=null,warningFraction=0.8}={}){
 if(databaseBudgetBytes!=null&&(!Number.isSafeInteger(databaseBudgetBytes)||databaseBudgetBytes<=0))fail('Database budget must be a positive safe integer in bytes');
 if(typeof warningFraction!=='number'||!Number.isFinite(warningFraction)||warningFraction<=0||warningFraction>=1)fail('Warning fraction must be between zero and one');
 const before=await revision(db),counts={};let databaseBytes=null,measurement='unavailable';
 // An explicit administrative diagnostic, not a per-navigation count scan.
 for(const [key,table] of Object.entries(countedTables)){
  const result=await db.prepare(`SELECT count(*) n FROM ${table}`).all();counts[key]=result.results[0].n;
  if(Number.isSafeInteger(result.meta?.size_after)&&result.meta.size_after>=0){databaseBytes=result.meta.size_after;measurement='d1-query-size-after';}
 }
 const mediaBytes=(await db.prepare('SELECT coalesce(sum(bytes),0) bytes FROM atlas_media').first()).bytes;
 if(databaseBytes==null)try{
  const size=await db.prepare('PRAGMA page_size').first(),pages=await db.prepare('PRAGMA page_count').first();
  if(Number.isSafeInteger(size?.page_size)&&size.page_size>0&&Number.isSafeInteger(pages?.page_count)&&pages.page_count>=0&&Number.isSafeInteger(size.page_size*pages.page_count)){
   databaseBytes=size.page_size*pages.page_count;measurement='sqlite-page-count-times-page-size';
  }
 }catch{/* The managed D1 API may not permit these PRAGMAs. Counts remain useful. */}
 const ratio=databaseBytes!=null&&databaseBudgetBytes!=null?databaseBytes/databaseBudgetBytes:null;
 return {measured_at:new Date().toISOString(),revision:await sameRevision(db,before),counts,
  database:{bytes:databaseBytes,measurement,configured_budget_bytes:databaseBudgetBytes,budget_is_provider_quota:false,quota_verified:false,warning_fraction:warningFraction,budget_fraction:ratio,budget_status:ratio==null?'unknown':ratio>=1?'at-or-above-budget':ratio>=warningFraction?'approaching-budget':'below-budget'},
  media:{registered_objects:counts.media,registered_bytes:mediaBytes,measurement:'database metadata; object existence and checksums require separate read-back',upload_limit_bytes:20*1024*1024},
  storage_scope:'Hosted database and registered object metadata only; prepared ownership, environment and grid assets are separate.',
  backend:{kind:'single-d1-plus-r2',partitioning_deployed:false,managed_plan:'unverified',growth_policy:'Use sparse supported intervals. Measure database/index bytes and query latency. Technical maintainers own storage partitioning and map-read changes behind stable IDs/API; research contributors only submit supported evidence.'}};
}
