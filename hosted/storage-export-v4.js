import {RecordError} from './records.js';

import {storageExportV2Contract} from './storage-export-v2-contract.js';
import {storageExportV3Contract} from './storage-export-v3-contract.js';
import {compactMembershipCatalog} from './membership-storage-profile.js';
const logicalContract=base=>base===3?storageExportV3Contract:storageExportV2Contract;
export const storageCatalogV4=db=>compactMembershipCatalog(db);
import {v4MarkerIdentity} from './storage-export-v4-contract.js';
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
export async function exportStorageMarkerV4(db){return markerForCatalog(db,await storageCatalogV4(db));}
async function markerForCatalog(db,catalog){
 const base=logicalContract(catalog.base_version),definitions=base.definitions,storageExportCollections=Object.keys(definitions);
 const contract={version:4,base_contract:base,membership_storage:'compact-membership-v1',profile:catalog.profile,public_sha256:catalog.public_sha256,private_sha256:catalog.private_sha256};
 const before=await revision(db),counts=Object.fromEntries(storageExportCollections.map(key=>[key,0]));
 // Managed D1 limits compound SELECT terms below the local SQLite default.
 // Scalar counts keep the complete marker in one read without a UNION chain.
 const countSql='SELECT '+storageExportCollections.map(key=>`(SELECT count(*) FROM ${definitions[key].table}) AS ${key}`).join(',');
 const counters=await db.prepare(countSql).first();
 for(const key of storageExportCollections){const n=counters?.[key];if(!Number.isSafeInteger(n)||n<0)throw new RecordError('Invalid storage counter',503);counts[key]=n;}
 const releases=await rows(db.prepare(`SELECT ${identifiers(definitions.geographic_releases.columns)} FROM atlas_geographic_releases ORDER BY id`));
 if(await revision(db)!==before||releases.length!==counts.geographic_releases)changed();
 const versions=await rows(db.prepare(`SELECT ${identifiers(definitions.footprint_versions.columns)} FROM atlas_footprint_versions ORDER BY id`));
 if(await revision(db)!==before||versions.length!==counts.footprint_versions)changed();
 const snapshot={version:4,revision:before,counts,geographic_releases_sha256:await digest(releases),footprint_versions_sha256:await digest(versions),catalog_sha256:await digest(catalog),contract};
 return {...snapshot,fingerprint:await digest(v4MarkerIdentity(snapshot)),backend:db.dialect==='postgres'?'postgres':'d1'};
}

function encodeCursor(collection,key){
 const bytes=new TextEncoder().encode(JSON.stringify({version:4,collection,key}));let raw='';for(const byte of bytes)raw+=String.fromCharCode(byte);
 return btoa(raw).replaceAll('+','-').replaceAll('/','_').replace(/=+$/,'');
}
function decodeCursor(cursor,collection,keys){
 if(typeof cursor!=='string'||cursor.length>20000||!/^[A-Za-z0-9_-]+$/.test(cursor))fail('Invalid storage export cursor');
 let value;try{const raw=atob(cursor.replaceAll('-','+').replaceAll('_','/'));value=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(Uint8Array.from(raw,c=>c.charCodeAt(0))));}catch{fail('Invalid storage export cursor');}
 if(!value||Array.isArray(value)||Object.keys(value).sort().join(',')!=='collection,key,version'||value.version!==4||value.collection!==collection||!Array.isArray(value.key)||value.key.length!==keys.length)fail('Invalid storage export cursor');
 for(let i=0;i<keys.length;i++)if(keys[i]==='rowid'? !Number.isSafeInteger(value.key[i])||value.key[i]<1:typeof value.key[i]!=='string'||!value.key[i].trim()||value.key[i].length>2000)fail('Invalid storage export cursor');
 if(encodeCursor(collection,value.key)!==cursor)fail('Noncanonical storage export cursor');return value.key;
}

/** All rows, including examples, archives and withdrawals. JSON TEXT columns
 * stay verbatim: this endpoint deliberately does not use profile normalizers.
 */
export async function exportStoragePageV4(db,collection,{cursor='',limit=200}={}){
 const catalog=await storageCatalogV4(db),definitions=logicalContract(catalog.base_version).definitions;
 if(!Object.hasOwn(definitions,collection))fail('Unknown storage export collection');
 if(!Number.isSafeInteger(limit)||limit<1)fail('Storage export limit must be a positive integer');limit=Math.min(limit,200);
 const definition=definitions[collection],key=cursor?decodeCursor(cursor,collection,definition.keys):null;
 if(!cursor&&typeof cursor!=='string')fail('Invalid storage export cursor');
 const before=await markerForCatalog(db,catalog);let where='',parameters=[];
 if(key){if(key.length===1){where=` WHERE ${definition.keys[0]}>?`;parameters=key;}else {where=` WHERE (${definition.keys[0]}>? OR (${definition.keys[0]}=? AND ${definition.keys[1]}>?))`;parameters=[key[0],key[0],key[1]];}}
 // Calculate encoded scalar lengths in the database before materializing a
 // large retained page. The extra key-only row establishes has-more without
 // downloading its evidence. PostgreSQL uses an explicit byte-length variant.
 const scalarBytes=column=>db.dialect==='postgres'?`coalesce(octet_length(CAST(to_json(${column}) AS TEXT)),4)`:`length(CAST(json_quote(${column}) AS BLOB))`;
 const keys=await rows(db.prepare(`SELECT ${definition.keys.join(',')},(${definition.columns.map(column=>scalarBytes('"'+column+'"')).join('+')}+${definition.columns.reduce((sum,key)=>sum+key.length+4,1)}) __row_bytes FROM ${definition.table}${where} ORDER BY ${definition.keys.join(',')} LIMIT ?`).bind(...parameters,limit+1));
 const envelope={collection,columns:[...definition.columns],records:[],next_cursor:keys.length>limit?encodeCursor(collection,definition.keys.map(key=>keys[limit-1][key])):null,revision:before.revision,snapshot_marker:before};
 if(keys.slice(0,limit).reduce((sum,row)=>sum+row.__row_bytes,0)+new TextEncoder().encode(JSON.stringify(envelope)).byteLength>maxBytes)oversized(limit);
 const selected=await rows(db.prepare(`SELECT ${identifiers(definition.columns)} FROM ${definition.table}${where} ORDER BY ${definition.keys.join(',')} LIMIT ?`).bind(...parameters,limit));
 const after=await exportStorageMarkerV4(db);if(after.fingerprint!==before.fingerprint)changed();
 const records=selected,next=keys.length>limit?encodeCursor(collection,definition.keys.map(key=>records.at(-1)[key])):null;
 const result={collection,columns:[...definition.columns],records,next_cursor:next,revision:before.revision,snapshot_marker:before};
 if(new TextEncoder().encode(JSON.stringify(result)).byteLength>maxBytes)oversized(limit);
 return result;
}

