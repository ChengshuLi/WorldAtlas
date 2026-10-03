/** Labelled legacy projection only after full known V3 verification. The strict
 * V2 contract/modules/restorers remain unchanged; unknown schemas never filter. */
import {RecordError} from './records.js';
import {storageCatalogV3,exportStorageMarkerV3} from './storage-export-v3.js';
import {storageCatalogV2,exportStorageMarkerV2,exportStoragePageV2} from './storage-export-v2.js';
const typedTables=new Set(['atlas_typed_observations','atlas_typed_feature_links','atlas_typed_retirements']);
function projectedDatabase(db){
 const typed=value=>typeof value==='string'&&value.startsWith('atlas_typed_');
 const omit=row=>typedTables.has(row.table_name)||typedTables.has(row.tbl_name)||typed(row.name)||typed(row.trigger_name)||typed(row.constraint_name);
 return {dialect:db.dialect,prepare(sql){let original=db.prepare(sql);const catalog=/sqlite_master|information_schema\.columns|FROM pg_trigger|FROM pg_constraint|FROM pg_proc|FROM pg_type/.test(sql);
  return {bind(...values){original=original.bind(...values);return this;},async all(){const result=await original.all();return catalog?{...result,results:result.results.filter(row=>!omit(row))}:result;},first:()=>original.first()};
 }};
}
async function compatible(db,operation){
 try{return await operation(db,null);}catch(error){if(error.status!==503)throw error;}
 // A failed strict V2 inventory may be the exact reviewed V3 extension, or an
 // unknown/altered schema. Only the complete latter contract can authorize it.
 await storageCatalogV3(db);const before=await exportStorageMarkerV3(db);
 const label={complete:false,scope:'legacy23-table projection',required_complete_export_version:3,full_snapshot_fingerprint:before.fingerprint};
 const result=await operation(projectedDatabase(db),label),after=await exportStorageMarkerV3(db);
 if(before.fingerprint!==after.fingerprint)throw new RecordError('Storage changed during legacy projection; retry',409);
 return result;
}
export const legacyStorageMarker=db=>compatible(db,async(backend,label)=>{const marker=await exportStorageMarkerV2(backend);return label?{...marker,legacy_projection:label}:marker;});
export const legacyStoragePage=(db,collection,options)=>compatible(db,async(backend,label)=>{const page=await exportStoragePageV2(backend,collection,options);return label?{...page,snapshot_marker:{...page.snapshot_marker,legacy_projection:label},legacy_projection:label}:page;});
export const legacyStorageCatalog=db=>compatible(db,async(backend,label)=>{const catalog=await storageCatalogV2(backend);return label?{version:2,legacy_projection:label,catalog}:catalog;});
