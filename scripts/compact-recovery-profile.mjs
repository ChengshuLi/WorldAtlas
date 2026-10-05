import {createHash} from 'node:crypto';
import {storageExportV2Contract,storageExportV2Collections,v2MarkerIdentity} from '../hosted/storage-export-v2-contract.js';
import {checkedStorageV4Contract,v4MarkerIdentity} from '../hosted/storage-export-v4-contract.js';
import {compactMembershipCatalog} from '../hosted/membership-storage-profile.js';

const sha=value=>createHash('sha256').update(value).digest('hex');
const need=(condition,code)=>{if(!condition)throw Error(code);};
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const hash=value=>/^[a-f0-9]{64}$/.test(value??'');
export const originalRecoveryProfile='original-v2';
export const compactRecoveryProfile='compact-only-v4-base2';
export const compactRecoveryTables=Object.freeze({
 worldatlas_membership_release_keys:{columns:['key','id'],keys:['key']},
 worldatlas_membership_entity_keys:{columns:['key','id'],keys:['key']},
 worldatlas_membership_source_keys:{columns:['key','id'],keys:['key']},
 worldatlas_membership_evidence:{columns:['key','digest','raw'],keys:['key']},
 worldatlas_membership_rows:{columns:['release_key','entity_key','parent_key','reference_name','active','source_key','evidence_key'],keys:['release_key','entity_key']},
});
const forwardProfiles=[
 {id:'0001_temporal_geography',prefix:'atlas_temporal_',tables:['atlas_temporal_geography_validations','atlas_geographic_membership_records','atlas_geographic_existence_records','atlas_temporal_geography_retirements']},
 {id:'0002_footprint_versions',prefix:'atlas_footprint_',tables:['atlas_footprint_versions','atlas_footprint_version_objects','atlas_footprint_selection_validations','atlas_geographic_footprint_records','atlas_footprint_retirements']},
];

/** Matches the original forward installer's native catalog hash, with fixed
 * identifiers only. It does not treat a copied registry hash as DDL proof. */
export async function recoveryForwardContract(query,id){
 const definition=forwardProfiles.find(item=>item.id===id);need(definition,'unsupported-forward-recovery-migration');
 const names=definition.tables.map(name=>"'"+name+"'").join(',');
 const columns=await query(`SELECT table_name,column_name,data_type,domain_name,is_nullable,column_default,collation_name FROM information_schema.columns WHERE table_schema='public' AND table_name IN (${names}) ORDER BY table_name,ordinal_position`);
 need(new Set(columns.map(row=>row.table_name)).size===definition.tables.length,'forward-table-inventory-incomplete');
 const constraints=await query(`SELECT c.relname table_name,k.conname,pg_get_constraintdef(k.oid) definition,k.condeferrable,k.condeferred FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname IN (${names}) ORDER BY c.relname,k.conname`);
 const triggers=await query(`SELECT c.relname table_name,t.tgname,t.tgenabled,pg_get_triggerdef(t.oid) definition FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND NOT t.tgisinternal AND (c.relname IN (${names}) OR t.tgname LIKE '${definition.prefix}%') ORDER BY c.relname,t.tgname`);
 need(triggers.every(row=>row.tgenabled==='O')&&definition.tables.every(table=>triggers.some(row=>row.table_name===table&&row.tgname==='atlas_no_truncate')),'forward-retention-guard-missing');
 const functions=await query(`SELECT p.proname,pg_get_function_identity_arguments(p.oid) arguments,pg_get_functiondef(p.oid) definition FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.prokind IN ('f','p') AND (p.proname LIKE '${definition.prefix}%' OR EXISTS(SELECT 1 FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid WHERE t.tgfoid=p.oid AND c.relname IN (${names}))) ORDER BY p.proname,arguments`);
 need(functions.length>0,'forward-functions-missing');
 return sha(JSON.stringify({columns,constraints,triggers,functions}));
}
export async function verifyCompactRecoveryRegistry(query,registry){
 need(same(registry.map(row=>row.migration_id),forwardProfiles.map(item=>item.id)),'unsupported-compact-migration-registry');
 for(const row of registry){
  const pin=storageExportV2Contract.postgres_migrations.find(item=>item.path==='postgres/migrations/'+row.migration_id+'.sql');
  need(row.file_sha256===pin.sha256&&row.core_schema_sha256===storageExportV2Contract.postgres_migrations[0].sha256&&hash(row.source_snapshot_fingerprint)&&hash(row.base_guards_sha256)&&Number.isSafeInteger(row.applied_at)&&row.applied_at>0,'changed-compact-migration-registry');
  need(row.installed_contract_sha256===await recoveryForwardContract(query,row.migration_id),'registered-forward-contract-mismatch');
 }
}

/** Only the installed original profile or the reviewed current compact-only
 * base2 profile is supported. Retained-original/base3 need their own review. */
export function recoveryProfileForMarker(marker){
 need(marker?.backend==='postgres'&&marker.read_only===true&&!marker.legacy_projection&&Number.isSafeInteger(marker.revision)&&marker.revision>=0,'unsupported-source-contract');
 let profile,identity;
 if(marker.version===2){
  need(same(marker.contract,storageExportV2Contract)&&marker.catalog_sha256===storageExportV2Contract.postgres_catalog_sha256,'unsupported-source-contract');
  profile=originalRecoveryProfile;identity=v2MarkerIdentity;
 }else{
  need(marker.version===4,'unsupported-source-contract');
  checkedStorageV4Contract(marker.contract);
  need(marker.contract.profile==='compact-only'&&marker.contract.base_contract.version===2,'unsupported-recovery-profile');
  profile=compactRecoveryProfile;identity=v4MarkerIdentity;
 }
 need(['fingerprint','catalog_sha256','geographic_releases_sha256','footprint_versions_sha256'].every(k=>hash(marker[k])),'incomplete-source-hashes');
 need(same(Object.keys(marker.counts??{}).sort(),[...storageExportV2Collections].sort())&&storageExportV2Collections.every(k=>Number.isSafeInteger(marker.counts[k])&&marker.counts[k]>=0),'incomplete-source-counts');
 need(sha(JSON.stringify(identity(marker)))===marker.fingerprint,'invalid-source-marker');
 return profile;
}

export function compactPhysicalReadSQL(table){
 const definition=compactRecoveryTables[table];need(definition,'unsupported-compact-physical-table');
 const ident=value=>'"'+value+'"';
 return `SELECT ${definition.columns.map(ident).join(',')} FROM public.${ident(table)} ORDER BY ${definition.keys.map(ident).join(',')}`;
}
export function compactPhysicalDigestSQL(table){
 const definition=compactRecoveryTables[table];need(definition,'unsupported-compact-physical-table');
 const order=definition.keys.map(key=>'"'+key+'"').join(',');
 return `SELECT count(*)::bigint rows,encode(sha256(convert_to(coalesce(string_agg(encode(sha256(convert_to(row_to_json(q)::text,'UTF8')),'hex'),'' ORDER BY ${order}),''),'UTF8')),'hex') ordered_rows_sha256 FROM (${compactPhysicalReadSQL(table)}) q`;
}

/** Exact logical and private DDL/ACL pins precede any physical row scan. Native
 * ordered digests preserve raw JSON TEXT spelling, BYTEA and dictionary keys. */
export async function readCompactRecoveryStorage(query){
 const db={dialect:'postgres',prepare:sql=>({all:async()=>({results:await query(sql)})})};
 const catalog=await compactMembershipCatalog(db);
 need(catalog.base_version===2&&catalog.profile==='compact-only','unsupported-recovery-profile');
 const physical={};
 for(const table of Object.keys(compactRecoveryTables)){
  const metrics=(await query(`SELECT count(*) rows,coalesce(max(octet_length(row_to_json(q)::text)),0) largest FROM (${compactPhysicalReadSQL(table)}) q`))[0];
  need(metrics&&Number.isSafeInteger(metrics.rows)&&metrics.rows>=0&&metrics.rows<=2000000&&Number.isSafeInteger(metrics.largest)&&metrics.largest>=0&&metrics.largest<=8*1024*1024,'compact-physical-digest-bound');
  const proof=(await query(compactPhysicalDigestSQL(table)))[0];
  need(proof?.rows===metrics.rows&&hash(proof.ordered_rows_sha256),'compact-physical-digest-invalid');
  physical[table]={count:proof.rows,ordered_rows_sha256:proof.ordered_rows_sha256,hash_kind:'sha256-pg-json-text-row-digests-numeric-key-order-v1'};
 }
 const sequences={};
 for(const table of Object.keys(compactRecoveryTables).filter(table=>table!=='worldatlas_membership_rows')){
  const name=table+'_key_seq',state=await query(`SELECT last_value,is_called FROM public."${name}"`);
  need(state.length===1&&Number.isSafeInteger(state[0].last_value)&&state[0].last_value>=1&&typeof state[0].is_called==='boolean','invalid-compact-sequence');
  const maximum=(await query(`SELECT coalesce(max(key),0) maximum FROM public."${table}"`))[0];
  need(Number.isSafeInteger(maximum?.maximum)&&maximum.maximum>=0&&state[0].last_value>=maximum.maximum,'compact-sequence-behind-dictionary');
  sequences[name]=state[0];
 }
 return {catalog,physical,sequences};
}
