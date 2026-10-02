import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {postgresTables} from './verify-postgres-schema.mjs';

export const runtimeRole='worldatlas_app';
const schemaSHA='1a43333772e6059d4fa97ce60baad7a27239616693c86708d08eadbc73b97618';
const roleSQL=fs.readFileSync(new URL('../postgres/runtime-role.sql',import.meta.url),'utf8');
const sha=text=>createHash('sha256').update(text).digest('hex');
async function rows(driver,sql,params=[]){const result=await driver.query(sql,params);if(!Array.isArray(result?.rows))throw Error('Invalid private PostgreSQL administration result');return result.rows;}
/** Read-only effective-permission check. Does not inspect or return passwords. */
export async function verifyPostgresRuntimeRole(driver){
 const role=(await rows(driver,'SELECT oid,rolname,rolcanlogin,rolsuper,rolinherit,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls,rolconfig FROM pg_roles WHERE rolname=$1',[runtimeRole]))[0];
 if(!role||!role.rolcanlogin||['rolsuper','rolinherit','rolcreatedb','rolcreaterole','rolreplication','rolbypassrls'].some(key=>role[key])||role.rolconfig?.length)throw Error('Application LOGIN attributes are not restricted');
 const owners=await rows(driver,"SELECT DISTINCT c.relowner AS owner_oid FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname=ANY($1::text[]) AND c.relkind='r'",[postgresTables]);if(owners.length!==1)throw Error('Reviewed tables do not share one maintenance owner');
 const ownerOID=owners[0].owner_oid;
 const memberships=(await rows(driver,'SELECT count(*)::int AS n FROM pg_auth_members WHERE member=$1::oid OR (roleid=$1::oid AND NOT(member=$2::oid AND admin_option AND NOT inherit_option AND NOT set_option))',[role.oid,ownerOID]))[0].n;
 const ownerAdministration=(await rows(driver,'SELECT count(*)::int AS n FROM pg_auth_members WHERE roleid=$1::oid AND member=$2::oid AND admin_option AND NOT inherit_option AND NOT set_option',[role.oid,ownerOID]))[0].n;
 const ownership=(await rows(driver,"SELECT count(*)::int AS n FROM pg_shdepend WHERE refclassid='pg_authid'::regclass AND refobjid=$1::oid AND deptype='o'",[role.oid]))[0].n;
 if(memberships||ownership)throw Error('Application role has membership or ownership');
 if((await rows(driver,"SELECT count(*)::int AS n FROM pg_db_role_setting WHERE setrole=$1::oid AND coalesce(array_length(setconfig,1),0)>0",[role.oid]))[0].n||(await rows(driver,"SELECT has_parameter_privilege($1,'session_replication_role','SET') AS allowed",[runtimeRole]))[0].allowed)throw Error('Application role has unreviewed settings or trigger-bypass privilege');
 const schema=(await rows(driver,"SELECT has_schema_privilege($1,'public','USAGE') AS usage,has_schema_privilege($1,'public','CREATE') AS create",[runtimeRole]))[0];if(!schema.usage||schema.create)throw Error('Application schema privileges are not restricted');
 if((await rows(driver,"SELECT count(*)::int AS n FROM pg_namespace WHERE nspname !~ '^pg_' AND nspname<>'information_schema' AND has_schema_privilege($1,oid,'CREATE')",[runtimeRole]))[0].n)throw Error('Application role can create persistent schema objects');
 const permissions=[];
 for(const table of postgresTables){
  const item=(await rows(driver,"SELECT has_table_privilege($1,$2,'SELECT') AS select,has_table_privilege($1,$2,'INSERT') AS insert,has_table_privilege($1,$2,'UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') AS excessive",[runtimeRole,`public.${table}`]))[0];
  if(!item.select||item.excessive||item.insert!==(table!=='atlas_ingestions'))throw Error('Application table privileges are not restricted');
  const columns=await rows(driver,"SELECT column_name,has_column_privilege($1,format('public.%I',table_name),column_name,'INSERT') AS insert,has_column_privilege($1,format('public.%I',table_name),column_name,'UPDATE') AS update,has_column_privilege($1,format('public.%I',table_name),column_name,'REFERENCES') AS references FROM information_schema.columns WHERE table_schema='public' AND table_name=$2 ORDER BY ordinal_position",[runtimeRole,table]);
  for(const column of columns)if(column.references||column.insert!==(table!=='atlas_ingestions'||column.column_name!=='rowid')||column.update!==(table==='atlas_geographic_releases'&&['status','published_at'].includes(column.column_name)))throw Error('Application column privileges are not restricted');
  permissions.push({table,select:true,insert:table==='atlas_ingestions'?'id,fingerprint,counts,created_at':'all columns',update:table==='atlas_geographic_releases'?'status,published_at':'none'});
 }
 const unrelated=await rows(driver,"SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname !~ '^pg_' AND n.nspname<>'information_schema' AND c.relkind IN ('r','p','v','m','f') AND NOT(n.nspname='public' AND c.relname=ANY($2::text[])) AND (has_table_privilege($1,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') OR has_any_column_privilege($1,c.oid,'SELECT,INSERT,UPDATE,REFERENCES'))",[runtimeRole,postgresTables]);if(unrelated.length)throw Error('Application role has unrelated table permissions');
 const sequence=(await rows(driver,"SELECT has_sequence_privilege($1,'public.atlas_ingestions_rowid_seq','USAGE') AS usage,has_sequence_privilege($1,'public.atlas_ingestions_rowid_seq','SELECT,UPDATE') AS excessive",[runtimeRole]))[0];if(!sequence.usage||sequence.excessive)throw Error('Application sequence privileges are not restricted');
 if((await rows(driver,"SELECT count(*)::int AS n FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname !~ '^pg_' AND n.nspname<>'information_schema' AND NOT(n.nspname='public' AND c.relname='atlas_ingestions_rowid_seq') AND CASE WHEN c.relkind='S' THEN has_sequence_privilege($1,c.oid,'USAGE,SELECT,UPDATE') ELSE false END",[runtimeRole]))[0].n)throw Error('Application role has unrelated sequence privileges');
 const disabled=(await rows(driver,"SELECT count(*)::int AS n FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname=ANY($1::text[]) AND NOT t.tgisinternal AND t.tgenabled<>'O'",[postgresTables]))[0].n;if(disabled)throw Error('Application database has disabled guards');
 const required=(await rows(driver,"SELECT count(*)::int AS n FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname=ANY($1::text[]) AND NOT t.tgisinternal AND t.tgname IN ('atlas_00_identity','atlas_no_truncate')",[postgresTables]))[0].n;if(required!==28)throw Error('Application database is missing immutable guards');
 return {version:1,role:runtimeRole,status:'verified',read_only:true,login:true,inheritance:false,memberships:0,owner_administration_membership:ownerAdministration,owner_administration_policy:'Only table owner ADMIN OPTION into app; INHERIT=false, SET=false. App belongs to no roles.',ownership:0,public_schema_create:false,permissions,sequence:'USAGE only; no SELECT, UPDATE, explicit rowid or restart',guards_enabled:true,runtime_role_sql_sha256:sha(roleSQL),schema_sha256:schemaSHA};
}
/** Explicit owner-maintainer operation. Secrets are bound and never returned. */
export async function provisionPostgresRuntimeRole({driver,password=null,rotatePassword=false,verifyOnly=false}){
 if(sha(fs.readFileSync(new URL('../postgres/schema.sql',import.meta.url)))!==schemaSHA)throw Error('Reviewed PostgreSQL schema changed');
 if(!driver?.query||!driver.runTransaction)throw Error('An interactive private owner driver is required');
 if(verifyOnly)return verifyPostgresRuntimeRole(driver);
 if(password!=null&&(typeof password!=='string'||password.length<24||password.includes('\0')))throw Error('Strong private application password is required');
 try{return await driver.runTransaction(async tx=>{
  const existed=(await rows(tx,'SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=$1) AS existed',[runtimeRole]))[0].existed;
  await tx.query("SELECT set_config('worldatlas.runtime_password',$1,true),set_config('worldatlas.rotate_password',$2,true)",[password??'',String(rotatePassword)]);await tx.query(roleSQL);
  const proof=await verifyPostgresRuntimeRole(tx);return {...proof,read_only:false,status:'provisioned',existing_role:existed,password_action:existed?(rotatePassword?'explicitly rotated':'preserved'):'created'};
 });}catch(error){const code=/^[A-Z0-9]{5}$/.test(error.code??'')?error.code:null;const safe=new Error(`Private runtime-role provisioning failed${code?` (SQLSTATE ${code})`:''}; do not reopen imports.`);safe.code=code;throw safe;}
}
async function ownerDriver(url){const {Client,neonConfig}=await import('@neondatabase/serverless');neonConfig.webSocketConstructor=globalThis.WebSocket;const client=new Client({connectionString:url});await client.connect();return {query:(sql,params)=>client.query(sql,params),async runTransaction(callback){await client.query('BEGIN');try{const value=await callback({query:(sql,params)=>client.query(sql,params)});await client.query('COMMIT');return value;}catch(error){try{await client.query('ROLLBACK');}catch{}throw error;}},close:()=>client.end()};}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const mode=process.argv[2];let driver;
 try{if(!['--provision','--rotate-password','--verify-only'].includes(mode))throw Error('Invalid mode');if(!process.env.DATABASE_URL)throw Error('Missing private owner credential');driver=await ownerDriver(process.env.DATABASE_URL);const result=await provisionPostgresRuntimeRole({driver,password:process.env.ATLAS_APP_DATABASE_PASSWORD??null,rotatePassword:mode==='--rotate-password',verifyOnly:mode==='--verify-only'});console.log(JSON.stringify(result));}
 catch(error){console.error(error?.code?`Runtime-role maintenance failed (SQLSTATE ${error.code}); keep imports paused.`:'Runtime-role maintenance configuration or permission verification failed; keep imports paused. Usage: node scripts/provision-postgres-runtime-role.mjs --provision | --rotate-password | --verify-only. Supply DATABASE_URL and, for a fresh LOGIN or explicit rotation, ATLAS_APP_DATABASE_PASSWORD through private environment secrets.');process.exitCode=1;}
 finally{await driver?.close().catch(()=>{});}
}
