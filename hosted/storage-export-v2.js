import {RecordError} from './records.js';

import {storageExportV2Definitions as definitions,storageExportV2Collections as storageExportCollections,storageExportV2Columns as storageExportColumns,storageExportV2Contract,v2MarkerIdentity} from './storage-export-v2-contract.js';
export {storageExportV2Collections,storageExportV2Columns} from './storage-export-v2-contract.js';
const identifiers=columns=>columns.map(column=>'"'+column+'"').join(',');
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
export async function exportStorageMarkerV2(db){
 const before=await revision(db),counts=Object.fromEntries(storageExportCollections.map(key=>[key,0]));
 // Managed D1 limits compound SELECT terms below the local SQLite default.
 // Scalar counts keep the complete marker in one read without a UNION chain.
 const countSql='SELECT '+storageExportCollections.map(key=>`(SELECT count(*) FROM ${definitions[key].table}) AS ${key}`).join(',');
 const counters=await db.prepare(countSql).first();
 for(const key of storageExportCollections){const n=counters?.[key];if(!Number.isSafeInteger(n)||n<0)throw new RecordError('Invalid storage counter',503);counts[key]=n;}
 const releases=await rows(db.prepare(`SELECT ${identifiers(definitions.geographic_releases.columns)} FROM atlas_geographic_releases ORDER BY id`));
 if(await revision(db)!==before||releases.length!==counts.geographic_releases)changed();
 const versions=await rows(db.prepare(`SELECT ${identifiers(definitions.footprint_versions.columns)} FROM atlas_footprint_versions ORDER BY id`));
 const catalog=await storageCatalogV2(db);
 if(await revision(db)!==before||versions.length!==counts.footprint_versions)changed();
 const snapshot={version:2,revision:before,counts,geographic_releases_sha256:await digest(releases),footprint_versions_sha256:await digest(versions),catalog_sha256:await digest(catalog),contract:storageExportV2Contract};
 return {...snapshot,fingerprint:await digest(v2MarkerIdentity(snapshot)),backend:db.dialect==='postgres'?'postgres':'d1'};
}

function encodeCursor(collection,key){
 const bytes=new TextEncoder().encode(JSON.stringify({version:2,collection,key}));let raw='';for(const byte of bytes)raw+=String.fromCharCode(byte);
 return btoa(raw).replaceAll('+','-').replaceAll('/','_').replace(/=+$/,'');
}
function decodeCursor(cursor,collection,keys){
 if(typeof cursor!=='string'||cursor.length>20000||!/^[A-Za-z0-9_-]+$/.test(cursor))fail('Invalid storage export cursor');
 let value;try{const raw=atob(cursor.replaceAll('-','+').replaceAll('_','/'));value=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(Uint8Array.from(raw,c=>c.charCodeAt(0))));}catch{fail('Invalid storage export cursor');}
 if(!value||Array.isArray(value)||Object.keys(value).sort().join(',')!=='collection,key,version'||value.version!==2||value.collection!==collection||!Array.isArray(value.key)||value.key.length!==keys.length)fail('Invalid storage export cursor');
 for(let i=0;i<keys.length;i++)if(keys[i]==='rowid'? !Number.isSafeInteger(value.key[i])||value.key[i]<1:typeof value.key[i]!=='string'||!value.key[i].trim()||value.key[i].length>2000)fail('Invalid storage export cursor');
 if(encodeCursor(collection,value.key)!==cursor)fail('Noncanonical storage export cursor');return value.key;
}

/** All rows, including examples, archives and withdrawals. JSON TEXT columns
 * stay verbatim: this endpoint deliberately does not use profile normalizers.
 */
export async function exportStoragePageV2(db,collection,{cursor='',limit=200}={}){
 if(!Object.hasOwn(definitions,collection))fail('Unknown storage export collection');
 if(!Number.isSafeInteger(limit)||limit<1)fail('Storage export limit must be a positive integer');limit=Math.min(limit,200);
 const definition=definitions[collection],key=cursor?decodeCursor(cursor,collection,definition.keys):null;
 if(!cursor&&typeof cursor!=='string')fail('Invalid storage export cursor');
 const before=await exportStorageMarkerV2(db);let where='',parameters=[];
 if(key){if(key.length===1){where=` WHERE ${definition.keys[0]}>?`;parameters=key;}else {where=` WHERE (${definition.keys[0]}>? OR (${definition.keys[0]}=? AND ${definition.keys[1]}>?))`;parameters=[key[0],key[0],key[1]];}}
 // Calculate encoded scalar lengths in the database before materializing a
 // large retained page. The extra key-only row establishes has-more without
 // downloading its evidence. PostgreSQL uses an explicit byte-length variant.
 const scalarBytes=column=>db.dialect==='postgres'?`coalesce(octet_length(CAST(to_json(${column}) AS TEXT)),4)`:`length(CAST(json_quote(${column}) AS BLOB))`;
 const keys=await rows(db.prepare(`SELECT ${definition.keys.join(',')},(${definition.columns.map(column=>scalarBytes('"'+column+'"')).join('+')}+${definition.columns.reduce((sum,key)=>sum+key.length+4,1)}) __row_bytes FROM ${definition.table}${where} ORDER BY ${definition.keys.join(',')} LIMIT ?`).bind(...parameters,limit+1));
 const envelope={collection,columns:[...definition.columns],records:[],next_cursor:keys.length>limit?encodeCursor(collection,definition.keys.map(key=>keys[limit-1][key])):null,revision:before.revision,snapshot_marker:before};
 if(keys.slice(0,limit).reduce((sum,row)=>sum+row.__row_bytes,0)+new TextEncoder().encode(JSON.stringify(envelope)).byteLength>maxBytes)oversized(limit);
 const selected=await rows(db.prepare(`SELECT ${identifiers(definition.columns)} FROM ${definition.table}${where} ORDER BY ${definition.keys.join(',')} LIMIT ?`).bind(...parameters,limit));
 const after=await exportStorageMarkerV2(db);if(after.fingerprint!==before.fingerprint)changed();
 const records=selected,next=keys.length>limit?encodeCursor(collection,definition.keys.map(key=>records.at(-1)[key])):null;
 const result={collection,columns:[...definition.columns],records,next_cursor:next,revision:before.revision,snapshot_marker:before};
 if(new TextEncoder().encode(JSON.stringify(result)).byteLength>maxBytes)oversized(limit);
 return result;
}

/** Catalog coverage is explicit: a future factual table cannot disappear from a
 * supposedly complete v2 backup. Owner deployment metadata is outside atlas_*.
 */
export async function storageCatalogV2(db,{verifyPins=true}={}){
 const tables=storageExportCollections.map(key=>definitions[key].table);
 if(db.dialect!=='postgres'){
  const inventory=await rows(db.prepare("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE (name GLOB 'atlas_*' OR tbl_name GLOB 'atlas_*') AND type IN ('table','index','trigger') ORDER BY type,name"));
  if(JSON.stringify(inventory.filter(row=>row.type==='table').map(row=>row.name).sort())!==JSON.stringify([...tables].sort()))throw new RecordError('Forward raw-storage table inventory is incomplete or has changed',503);
  if(verifyPins&&await digest(inventory)!==storageExportV2Contract.d1_catalog_sha256)throw new RecordError('Forward D1 schema or immutable guards do not match reviewed migration pins',503);
  return inventory;
 }
 const columns=await rows(db.prepare("SELECT table_name,column_name,data_type,domain_name,is_nullable,column_default,collation_name FROM information_schema.columns WHERE table_schema=current_schema() AND left(table_name,6)='atlas_' ORDER BY table_name,ordinal_position"));
 const names=[...new Set(columns.map(row=>row.table_name))].sort();
 if(JSON.stringify(names)!==JSON.stringify([...tables].sort()))throw new RecordError('Forward raw-storage table inventory is incomplete or has changed',503);
 for(const key of storageExportCollections)if(JSON.stringify(columns.filter(row=>row.table_name===definitions[key].table).map(row=>row.column_name))!==JSON.stringify(definitions[key].columns))throw new RecordError('Forward raw-storage columns have changed',503);
 const triggers=await rows(db.prepare("SELECT c.relname AS table_name,t.tgname AS trigger_name,t.tgenabled AS enabled,pg_get_triggerdef(t.oid) AS definition FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=current_schema() AND left(c.relname,6)='atlas_' AND NOT t.tgisinternal ORDER BY c.relname,t.tgname"));
 if(triggers.some(row=>row.enabled!=='O'))throw new RecordError('Forward raw-storage guards are disabled',503);
 const constraints=await rows(db.prepare("SELECT c.relname AS table_name,x.conname AS name,x.contype AS type,x.condeferrable AS deferrable,x.condeferred AS deferred,x.convalidated AS validated,pg_get_constraintdef(x.oid) AS definition FROM pg_constraint x JOIN pg_class c ON c.oid=x.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=current_schema() AND left(c.relname,6)='atlas_' ORDER BY c.relname,x.conname"));
 const functions=await rows(db.prepare("SELECT p.proname AS name,pg_get_functiondef(p.oid) AS definition FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname=current_schema() AND (left(p.proname,6)='atlas_' OR p.proname IN ('json_valid','json_type','json_extract','json_each','instr')) ORDER BY p.proname,pg_get_function_identity_arguments(p.oid)"));
 const constraint_triggers=await rows(db.prepare("SELECT c.relname AS table_name,x.conname AS constraint_name,t.tgtype AS type,t.tgenabled AS enabled FROM pg_trigger t JOIN pg_constraint x ON x.oid=t.tgconstraint JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=current_schema() AND left(c.relname,6)='atlas_' AND t.tgisinternal ORDER BY c.relname,x.conname,t.tgtype"));
 if(constraint_triggers.some(row=>row.enabled!=='O'))throw new RecordError('Forward raw-storage foreign-key guards are disabled',503);
 const domains=await rows(db.prepare("SELECT t.typname AS name,format_type(t.typbasetype,t.typtypmod) AS base_type,t.typnotnull AS not_null,t.typdefault AS default_value,c.conname AS constraint_name,pg_get_constraintdef(c.oid) AS definition FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace LEFT JOIN pg_constraint c ON c.contypid=t.oid WHERE n.nspname=current_schema() AND t.typtype='d' AND left(t.typname,6)='atlas_' ORDER BY t.typname,c.conname"));
 const catalog={columns,triggers,constraints,constraint_triggers,domains,functions};
 if(verifyPins&&await digest(catalog)!==storageExportV2Contract.postgres_catalog_sha256)throw new RecordError('Forward PostgreSQL schema or immutable guards do not match reviewed migration pins',503);
 return catalog;
}
