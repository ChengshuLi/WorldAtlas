/** Offline contract rehearsal only. Publisher preflight/backup/capacity gates
 * must be implemented and reviewed before this contract is used on production. */
import fs from 'node:fs';
import {createHash} from 'node:crypto';

export const compactMembershipDDL=fs.readFileSync(new URL('../postgres/membership-storage-v1.sql',import.meta.url),'utf8');
export const compactMembershipObjects=['worldatlas_membership_release_keys','worldatlas_membership_entity_keys',
 'worldatlas_membership_source_keys','worldatlas_membership_evidence','worldatlas_membership_rows'];
const legacy='worldatlas_memberships_original_v1';
const fields=['release_id','entity_id','parent_id','reference_name','active','source_id','evidence'];
const need=(condition,message)=>{if(!condition)throw Error(message);};
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const rows=async(tx,sql,params=[])=>{const result=await tx.query(sql,params);need(Array.isArray(result.rows),'Invalid rehearsal SQL response');return result.rows;};

export async function compactMembershipParity(tx,original=legacy){
 need([legacy,'atlas_geographic_memberships'].includes(original),'Unreviewed original relation');
 const value=(await rows(tx,`SELECT
 (SELECT count(*)::text FROM public.${original}) original_rows,
 (SELECT count(*)::text FROM public.worldatlas_membership_projection) compact_rows,
 NOT EXISTS((SELECT * FROM public.${original} EXCEPT ALL SELECT * FROM public.worldatlas_membership_projection)
 UNION ALL (SELECT * FROM public.worldatlas_membership_projection EXCEPT ALL SELECT * FROM public.${original})) exact,
 NOT EXISTS(SELECT 1 FROM public.worldatlas_membership_evidence WHERE digest<>pg_catalog.sha256(pg_catalog.convert_to(raw,'UTF8'))) evidence_digest_valid`))[0];
 need(value.exact&&value.evidence_digest_valid&&value.original_rows===value.compact_rows,'Compact membership full-row parity failed');
 return value;
}

/** Owns the complete rehearsal transaction, never accepts a transaction handle.
 * Original rows and primary key remain intact for an owner rollback rehearsal. */
export async function rehearseCompactMembershipStorage(engine,{afterCopy}={}){
 need(typeof engine.transaction==='function','Rehearsal must own its transaction');
 return engine.transaction(async tx=>{
  await tx.query('SELECT pg_advisory_xact_lock(807245315,1)');
  const owner=(await rows(tx,"SELECT current_user role,current_schema() schema,current_setting('server_encoding') encoding"))[0];
  need(owner.schema==='public'&&owner.encoding==='UTF8','Reviewed public UTF8 schema required');
  const relation=(await rows(tx,"SELECT relkind,pg_get_userbyid(relowner) owner FROM pg_class WHERE oid='public.atlas_geographic_memberships'::regclass"))[0];
  need(relation?.relkind==='r'&&relation.owner===owner.role,'Owner of original membership table required');
  const dependencies=await rows(tx,"SELECT 'view' kind FROM pg_depend d JOIN pg_rewrite r ON r.oid=d.objid WHERE d.refobjid='public.atlas_geographic_memberships'::regclass UNION ALL SELECT 'foreign-key' FROM pg_constraint WHERE contype='f' AND confrelid='public.atlas_geographic_memberships'::regclass");
  need(dependencies.length===0,'Unreviewed membership relation dependencies');
  const functionsBefore=await rows(tx,"SELECT proname,pg_get_functiondef(oid) definition FROM pg_proc WHERE oid IN ('public.atlas_immutable_guard()'::regprocedure,'public.atlas_geography_contract()'::regprocedure) ORDER BY proname");
  await tx.exec(compactMembershipDDL);
  let cursorRelease='',cursorEntity='',copied=0;
  for(;;){
   const batch=await rows(tx,`SELECT ${fields.join(',')} FROM public.atlas_geographic_memberships
    WHERE (release_id,entity_id)>($1 COLLATE "C",$2 COLLATE "C") ORDER BY release_id,entity_id LIMIT 200`,[cursorRelease,cursorEntity]);
   if(!batch.length)break;
   for(const row of batch)await tx.query('SELECT public.worldatlas_membership_save($1,$2,$3,$4,$5,$6,$7)',fields.map(k=>row[k]));
   copied+=batch.length;cursorRelease=batch.at(-1).release_id;cursorEntity=batch.at(-1).entity_id;
  }
  if(afterCopy)await afterCopy(tx);
  const parity=await compactMembershipParity(tx,'atlas_geographic_memberships');
  await tx.query(`ALTER TABLE public.atlas_geographic_memberships RENAME TO ${legacy}`);
  // Keep an owner-only projection for independent parity and later recovery.
  await tx.query('CREATE VIEW public.atlas_geographic_memberships AS SELECT * FROM public.worldatlas_membership_projection');
  await tx.query("ALTER VIEW public.atlas_geographic_memberships ALTER COLUMN active SET DEFAULT 1");
  await tx.query("ALTER VIEW public.atlas_geographic_memberships ALTER COLUMN evidence SET DEFAULT '{}'");
  await tx.exec(`CREATE TRIGGER atlas_00_identity INSTEAD OF INSERT ON public.atlas_geographic_memberships FOR EACH ROW EXECUTE FUNCTION public.atlas_immutable_guard();
   CREATE TRIGGER atlas_10_geography INSTEAD OF INSERT ON public.atlas_geographic_memberships FOR EACH ROW EXECUTE FUNCTION public.atlas_geography_contract();
   CREATE TRIGGER atlas_20_compact_insert INSTEAD OF INSERT ON public.atlas_geographic_memberships FOR EACH ROW EXECUTE FUNCTION public.worldatlas_membership_insert();
   CREATE TRIGGER atlas_immutable INSTEAD OF UPDATE OR DELETE ON public.atlas_geographic_memberships FOR EACH ROW EXECUTE FUNCTION public.atlas_immutable_guard();
   REVOKE ALL ON public.atlas_geographic_memberships FROM PUBLIC;`);
  const app=await rows(tx,"SELECT 1 FROM pg_roles WHERE rolname='worldatlas_app'");
  if(app.length){
   for(const name of [...compactMembershipObjects,legacy,'worldatlas_membership_projection'])await tx.query(`REVOKE ALL ON public.${name} FROM worldatlas_app`);
   for(const name of compactMembershipObjects.filter(x=>x!=='worldatlas_membership_rows'))await tx.query(`REVOKE ALL ON SEQUENCE public.${name}_key_seq FROM worldatlas_app,PUBLIC`);
   await tx.query('REVOKE ALL ON FUNCTION public.worldatlas_membership_save(text,text,text,text,integer,text,text),public.worldatlas_membership_insert(),public.worldatlas_membership_append_only() FROM worldatlas_app');
   await tx.query('REVOKE ALL ON public.atlas_geographic_memberships FROM worldatlas_app');
   await tx.query('GRANT SELECT,INSERT ON public.atlas_geographic_memberships TO worldatlas_app');
  }
  const functionsAfter=await rows(tx,"SELECT proname,pg_get_functiondef(oid) definition FROM pg_proc WHERE oid IN ('public.atlas_immutable_guard()'::regprocedure,'public.atlas_geography_contract()'::regprocedure) ORDER BY proname");
  need(JSON.stringify(functionsBefore)===JSON.stringify(functionsAfter),'Original guards changed');
  return {version:1,scope:'isolated-contract-rehearsal',copied,parity,ddl_sha256:hash(compactMembershipDDL),
   original_functions_sha256:hash(JSON.stringify(functionsBefore)),original_physical_rows_retained:true,production_capacity_verified:false};
 });
}

/** Only a no-new-writes rollback: refuse to lose even one newly appended row.
 * Production rollback must also settle maintenance/recovery/provider receipts. */
export async function rehearseCompactMembershipRollback(engine){
 return engine.transaction(async tx=>{
  await tx.query('SELECT pg_advisory_xact_lock(807245315,1)');
  const parity=await compactMembershipParity(tx);
  await tx.query('DROP VIEW public.atlas_geographic_memberships');
  await tx.query(`ALTER TABLE public.${legacy} RENAME TO atlas_geographic_memberships`);
  await tx.query('DROP VIEW public.worldatlas_membership_projection');
  for(const name of [...compactMembershipObjects].reverse())await tx.query(`DROP TABLE public.${name}`);
  await tx.query('DROP FUNCTION public.worldatlas_membership_insert(),public.worldatlas_membership_save(text,text,text,text,integer,text,text),public.worldatlas_membership_append_only()');
  if((await rows(tx,"SELECT 1 FROM pg_roles WHERE rolname='worldatlas_app'")).length)await tx.query('GRANT SELECT,INSERT ON public.atlas_geographic_memberships TO worldatlas_app');
  return {version:1,scope:'isolated-contract-rollback',parity,original_physical_rows_restored:true};
 });
}
