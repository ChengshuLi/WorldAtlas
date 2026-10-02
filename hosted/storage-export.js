import {RecordError} from './records.js';

const definitions={
 sources:{table:'atlas_sources',columns:['id','name','url','license','vintage','supported_from','supported_to','status','metadata'],keys:['id']},
 entity_types:{table:'atlas_entity_types',columns:['id','name','geographic_level','metadata'],keys:['id']},
 entities:{table:'atlas_entities',columns:['id','kind','name','parent_id','valid_from','valid_to','source_id','reference_owner','is_example','active','metadata'],keys:['id']},
 categories:{table:'atlas_categories',columns:['id','kind','name','source_id','metadata'],keys:['id']},
 records:{table:'atlas_attribute_records',columns:['id','location_id','attribute','value','category_id','valid_from','valid_to','method','status','source_id','is_example','metadata'],keys:['id']},
 names:{table:'atlas_names',columns:['id','entity_id','name','language','role','valid_from','valid_to','source_id','is_example','metadata'],keys:['id']},
 relationships:{table:'atlas_relationships',columns:['id','source_entity_id','target_entity_id','relationship_type','valid_from','valid_to','source_id','is_example','metadata'],keys:['id']},
 media:{table:'atlas_media',columns:['id','object_key','sha256','bytes','mime','name','license','attribution','source_id','status','metadata'],keys:['id']},
 media_links:{table:'atlas_media_links',columns:['id','media_id','entity_id','role','caption','source_id','is_example','valid_from','valid_to','metadata'],keys:['id']},
 retirements:{table:'atlas_evidence_retirements',columns:['id','collection','target_id','source_id','reason','replacement_id','metadata'],keys:['id']},
 ingestions:{table:'atlas_ingestions',columns:['rowid','id','fingerprint','counts','created_at'],keys:['rowid']},
 geographic_releases:{table:'atlas_geographic_releases',columns:['id','source_id','version','reference_date','status','hierarchy_sha256','footprints_sha256','membership_sha256','location_ids_sha256','changes_sha256','expected_counts','metadata','published_at'],keys:['id']},
 geographic_memberships:{table:'atlas_geographic_memberships',columns:['release_id','entity_id','parent_id','reference_name','active','source_id','evidence'],keys:['release_id','entity_id']},
 geographic_changes:{table:'atlas_geographic_changes',columns:['id','release_id','old_entity_id','new_entity_id','change_type','source_id','evidence'],keys:['release_id','id']},
};
export const storageExportCollections=Object.freeze(Object.keys(definitions));
export const storageExportColumns=Object.freeze(Object.fromEntries(Object.entries(definitions).map(([key,value])=>[key,Object.freeze([...value.columns])])));
const maxBytes=8*1024*1024;
const fail=message=>{throw new RecordError(message,400);};
const rows=async statement=>(await statement.all()).results||[];
const revision=async db=>(await db.prepare('SELECT coalesce(max(rowid),0) revision FROM atlas_ingestions').first()).revision;
const digest=async value=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(value))))].map(v=>v.toString(16).padStart(2,'0')).join('');
function changed(){const error=new RecordError('Storage changed during read-only export; restart from a stable maintenance snapshot',409);error.retryable=true;throw error;}
function oversized(limit){const error=new RecordError('Storage export page exceeds 8 MiB; retry with fewer rows',413);error.retryable=true;error.suggested_limit=Math.max(1,Math.floor(limit/2));throw error;}

/** Counts cover append-only changes outside ingestion journals; release hashes
 * also detect the permitted staged-to-published transition. Maintenance mode
 * remains required across the complete transfer, not merely this one page.
 */
export async function exportStorageMarker(db){
 const before=await revision(db),counts=Object.fromEntries(storageExportCollections.map(key=>[key,0]));
 const countSql=storageExportCollections.map(key=>`SELECT '${key}' collection,count(*) n FROM ${definitions[key].table}`).join(' UNION ALL ');
 for(const row of await rows(db.prepare(countSql))){if(!Number.isSafeInteger(row.n)||row.n<0)throw new RecordError('Invalid storage counter',503);counts[row.collection]=row.n;}
 const releases=await rows(db.prepare(`SELECT ${definitions.geographic_releases.columns.join(',')} FROM atlas_geographic_releases ORDER BY id`));
 if(await revision(db)!==before||releases.length!==counts.geographic_releases)changed();
 const snapshot={version:1,revision:before,counts,geographic_releases_sha256:await digest(releases)};
 return {...snapshot,fingerprint:await digest(snapshot),backend:db.dialect==='postgres'?'postgres':'d1'};
}

function encodeCursor(collection,key){
 const bytes=new TextEncoder().encode(JSON.stringify({version:1,collection,key}));let raw='';for(const byte of bytes)raw+=String.fromCharCode(byte);
 return btoa(raw).replaceAll('+','-').replaceAll('/','_').replace(/=+$/,'');
}
function decodeCursor(cursor,collection,keys){
 if(typeof cursor!=='string'||cursor.length>20000||!/^[A-Za-z0-9_-]+$/.test(cursor))fail('Invalid storage export cursor');
 let value;try{const raw=atob(cursor.replaceAll('-','+').replaceAll('_','/'));value=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(Uint8Array.from(raw,c=>c.charCodeAt(0))));}catch{fail('Invalid storage export cursor');}
 if(!value||Array.isArray(value)||Object.keys(value).sort().join(',')!=='collection,key,version'||value.version!==1||value.collection!==collection||!Array.isArray(value.key)||value.key.length!==keys.length)fail('Invalid storage export cursor');
 for(let i=0;i<keys.length;i++)if(keys[i]==='rowid'? !Number.isSafeInteger(value.key[i])||value.key[i]<1:typeof value.key[i]!=='string'||!value.key[i].trim()||value.key[i].length>2000)fail('Invalid storage export cursor');
 if(encodeCursor(collection,value.key)!==cursor)fail('Noncanonical storage export cursor');return value.key;
}

/** All rows, including examples, archives and withdrawals. JSON TEXT columns
 * stay verbatim: this endpoint deliberately does not use profile normalizers.
 */
export async function exportStoragePage(db,collection,{cursor='',limit=200}={}){
 if(!Object.hasOwn(definitions,collection))fail('Unknown storage export collection');
 if(!Number.isSafeInteger(limit)||limit<1)fail('Storage export limit must be a positive integer');limit=Math.min(limit,200);
 const definition=definitions[collection],key=cursor?decodeCursor(cursor,collection,definition.keys):null;
 if(!cursor&&typeof cursor!=='string')fail('Invalid storage export cursor');
 const before=await exportStorageMarker(db);let where='',parameters=[];
 if(key){if(key.length===1){where=` WHERE ${definition.keys[0]}>?`;parameters=key;}else {where=` WHERE (${definition.keys[0]}>? OR (${definition.keys[0]}=? AND ${definition.keys[1]}>?))`;parameters=[key[0],key[0],key[1]];}}
 // Calculate encoded scalar lengths in the database before materializing a
 // large retained page. The extra key-only row establishes has-more without
 // downloading its evidence. PostgreSQL uses an explicit byte-length variant.
 const scalarBytes=column=>db.dialect==='postgres'?`coalesce(octet_length(CAST(to_json(${column}) AS TEXT)),4)`:`length(CAST(json_quote(${column}) AS BLOB))`;
 const keys=await rows(db.prepare(`SELECT ${definition.keys.join(',')},(${definition.columns.map(scalarBytes).join('+')}+${definition.columns.reduce((sum,key)=>sum+key.length+4,1)}) __row_bytes FROM ${definition.table}${where} ORDER BY ${definition.keys.join(',')} LIMIT ?`).bind(...parameters,limit+1));
 const envelope={collection,columns:[...definition.columns],records:[],next_cursor:keys.length>limit?encodeCursor(collection,definition.keys.map(key=>keys[limit-1][key])):null,revision:before.revision,snapshot_marker:before};
 if(keys.slice(0,limit).reduce((sum,row)=>sum+row.__row_bytes,0)+new TextEncoder().encode(JSON.stringify(envelope)).byteLength>maxBytes)oversized(limit);
 const selected=await rows(db.prepare(`SELECT ${definition.columns.join(',')} FROM ${definition.table}${where} ORDER BY ${definition.keys.join(',')} LIMIT ?`).bind(...parameters,limit));
 const after=await exportStorageMarker(db);if(after.fingerprint!==before.fingerprint)changed();
 const records=selected,next=keys.length>limit?encodeCursor(collection,definition.keys.map(key=>records.at(-1)[key])):null;
 const result={collection,columns:[...definition.columns],records,next_cursor:next,revision:before.revision,snapshot_marker:before};
 if(new TextEncoder().encode(JSON.stringify(result)).byteLength>maxBytes)oversized(limit);
 return result;
}
