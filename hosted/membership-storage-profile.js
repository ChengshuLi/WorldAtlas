/** Exact known compact contracts. Frozen V2/V3 contracts remain strict; compact
 * storage uses a separately versioned logical export and native owner backup. */
import {RecordError} from './records.js';
import {storageCatalogV2} from './storage-export-v2.js';
import {storageCatalogV3} from './storage-export-v3.js';
import {membershipStoragePins} from './membership-storage-pins.js';
const rows=async(db,sql)=>(await db.prepare(sql).all()).results||[];
const hash=async value=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(value))))].map(x=>x.toString(16).padStart(2,'0')).join('');
const fail=message=>{throw new RecordError(message,503);};
export const compactMembershipNames=Object.freeze(['worldatlas_membership_release_keys','worldatlas_membership_entity_keys','worldatlas_membership_source_keys','worldatlas_membership_evidence','worldatlas_membership_rows','worldatlas_membership_projection']);
const original='worldatlas_memberships_original_v1';
const names=[...compactMembershipNames,original].map(x=>"'"+x+"'").join(',');
export async function membershipStorageKind(db){
 if(db.dialect!=='postgres')return 'original';
 const relation=(await rows(db,"SELECT relkind FROM pg_class WHERE oid=to_regclass('public.atlas_geographic_memberships')"))[0];
 if(relation?.relkind==='r')return 'original';if(relation?.relkind==='v')return 'compact';return 'unknown';
}
async function metadataRows(db,queries,batchMetadata){
 if(batchMetadata&&typeof db.batch==='function'){
  const results=await db.batch(queries.map(sql=>db.prepare(sql)));
  return results.map(result=>result.results||[]);
 }
 const results=[];for(const sql of queries)results.push(await rows(db,sql));return results;
}
export async function readCompactMembershipPrivateCatalog(db,{batchMetadata=false}={}){
 if(db.dialect!=='postgres')fail('Compact storage requires PostgreSQL');
 const [columns,constraints,triggers,constraintTriggers,indexes,functions,sequences,relations]=await metadataRows(db,[
  `SELECT c.relname table_name,a.attname column_name,format_type(a.atttypid,a.atttypmod) data_type,
 CASE WHEN a.attnotnull THEN 'NO' ELSE 'YES' END is_nullable,pg_get_expr(d.adbin,d.adrelid) column_default,
 co.collname collation_name,CASE WHEN a.attidentity<>'' THEN 'YES' ELSE 'NO' END is_identity,
 CASE a.attidentity WHEN 'a' THEN 'ALWAYS' WHEN 'd' THEN 'BY DEFAULT' ELSE NULL END identity_generation
 FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace
 LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum LEFT JOIN pg_collation co ON co.oid=a.attcollation
 WHERE n.nspname='public' AND c.relname IN (${names}) AND a.attnum>0 AND NOT a.attisdropped ORDER BY c.relname,a.attnum`,
  `SELECT c.relname relation,k.conname,k.contype,k.convalidated,k.condeferrable,k.condeferred,pg_get_constraintdef(k.oid) definition FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname IN (${names}) ORDER BY c.relname,k.conname`,
  `SELECT c.relname relation,t.tgname,t.tgenabled,pg_get_triggerdef(t.oid) definition FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname IN (${names}) AND NOT t.tgisinternal ORDER BY c.relname,t.tgname`,
  `SELECT c.relname relation,k.conname,t.tgtype,t.tgenabled FROM pg_trigger t JOIN pg_constraint k ON k.oid=t.tgconstraint JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname IN (${names}) AND t.tgisinternal ORDER BY c.relname,k.conname,t.tgtype`,
  `SELECT c.relname relation,i.relname name,x.indisvalid,x.indisready,pg_get_indexdef(i.oid) definition FROM pg_index x JOIN pg_class c ON c.oid=x.indrelid JOIN pg_class i ON i.oid=x.indexrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname IN (${names}) AND c.relname<>'${original}' ORDER BY c.relname,i.relname`,
  "SELECT proname,pg_get_functiondef(p.oid) definition,prosecdef,p.proowner=(SELECT relowner FROM pg_class WHERE oid='public.atlas_geographic_memberships'::regclass) same_owner FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname LIKE 'worldatlas_membership_%' ORDER BY proname",
  "SELECT c.relname name,c.relowner=(SELECT relowner FROM pg_class WHERE oid='public.atlas_geographic_memberships'::regclass) same_owner,format_type(s.seqtypid,NULL) data_type,s.seqstart::text start,s.seqincrement::text increment,s.seqmin::text minimum,s.seqmax::text maximum,s.seqcache::text cache,s.seqcycle cycle FROM pg_sequence s JOIN pg_class c ON c.oid=s.seqrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname LIKE 'worldatlas_membership_%' ORDER BY c.relname",
  `SELECT c.relname name,c.relkind,c.relrowsecurity,c.relforcerowsecurity,c.reloptions,
 CASE WHEN c.relkind='v' THEN pg_get_viewdef(c.oid,true) ELSE NULL END view_definition,
 c.relowner=(SELECT relowner FROM pg_class WHERE oid='public.atlas_geographic_memberships'::regclass) same_owner
 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND (c.relname='atlas_geographic_memberships' OR c.relname IN (${names}) OR c.relname LIKE 'worldatlas_membership_%') AND c.relkind IN ('r','v','m','p','f') ORDER BY c.relname`
 ],batchMetadata);
 if(functions.some(x=>!x.same_owner)||sequences.some(x=>!x.same_owner)||constraintTriggers.some(x=>x.tgenabled!=='O')||triggers.some(x=>x.tgenabled!=='O')||indexes.some(x=>!x.indisvalid||!x.indisready)||relations.some(x=>!x.same_owner||x.relrowsecurity||x.relforcerowsecurity))fail('Unverified compact owner or guards');
 // No secret data or sequence state is exposed. Effective role/column grants
 // and extra PUBLIC/other-role ACLs are checked through PostgreSQL catalogs.
 const [exposed,columnExposure,functionExposure]=await metadataRows(db,[
  `SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND
 (c.relname IN (${names}) OR c.relname LIKE 'worldatlas_membership_%') AND
 ((c.relkind IN ('r','v') AND (has_table_privilege('worldatlas_app',c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') OR has_any_column_privilege('worldatlas_app',c.oid,'SELECT,INSERT,UPDATE,REFERENCES')))
 OR (c.relkind='S' AND has_sequence_privilege('worldatlas_app',c.oid,'USAGE,SELECT,UPDATE'))
 OR EXISTS(SELECT 1 FROM aclexplode(coalesce(c.relacl,acldefault(CASE WHEN c.relkind='S' THEN 'S'::"char" ELSE 'r'::"char" END,c.relowner))) a WHERE a.grantee<>c.relowner))`,
  `SELECT c.relname,a.attname FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND (c.relname IN (${names}) OR c.relname LIKE 'worldatlas_membership_%') AND a.attacl IS NOT NULL AND EXISTS(SELECT 1 FROM aclexplode(a.attacl) acl WHERE acl.grantee<>c.relowner)`,
  "SELECT proname FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname LIKE 'worldatlas_membership_%' AND (has_function_privilege('worldatlas_app',p.oid,'EXECUTE') OR EXISTS(SELECT 1 FROM aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a WHERE a.grantee<>p.proowner))"
 ],batchMetadata);
 if(exposed.length||columnExposure.length||functionExposure.length)fail('Compact private storage privileges are exposed');
 return {columns,constraints,triggers,constraint_triggers:constraintTriggers,indexes,functions,sequences,relations};
}
export async function compactMembershipCatalog(db,{verifyPins=true,batchMetadata=false}={}){
 if(await membershipStorageKind(db)!=='compact')fail('Verified compact membership view required');
 const inventory=await rows(db,"SELECT table_name FROM information_schema.columns WHERE table_schema='public' AND left(table_name,6)='atlas_' GROUP BY table_name ORDER BY table_name");
 const baseVersion=inventory.some(x=>x.table_name==='atlas_typed_observations')?3:2;
 const catalog=await (baseVersion===3?storageCatalogV3(db,{verifyPins:false}):storageCatalogV2(db,{verifyPins:false}));
 const privateCatalog=await readCompactMembershipPrivateCatalog(db,{batchMetadata});
 const retained=privateCatalog.relations.some(x=>x.name===original),profile=retained?'retained-original':'compact-only';
 const publicHash=await hash(catalog),privateHash=await hash(privateCatalog),pins=membershipStoragePins[baseVersion]?.[profile];
 if(verifyPins&&(!pins||publicHash!==pins.public_sha256||privateHash!==pins.private_sha256))fail('Compact schema differs from exact reviewed storage pins');
 return {version:4,base_version:baseVersion,profile,public_catalog:catalog,private_catalog:privateCatalog,public_sha256:publicHash,private_sha256:privateHash};
}
