import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {neon} from '@neondatabase/serverless';

export const storageTarget=Object.freeze({project:'weathered-lab-37571695',branch:'br-summer-butterfly-ar8qikk5',database:'neondb',role:'neondb_owner'});
const apiOrigin='https://console.neon.tech/api/v2/';
const responseLimit=2*1024*1024,receiptLimit=512*1024;
class StorageError extends Error {constructor(code){super(code);this.code=code;}}
const need=(ok,code)=>{if(!ok)throw new StorageError(code);};
const number=value=>{const n=typeof value==='string'&&/^\d+$/.test(value)?Number(value):value;need(Number.isSafeInteger(n)&&n>=0,'invalid-storage-number');return n;};
const identifier=value=>{need(typeof value==='string'&&/^[a-zA-Z_][a-zA-Z_0-9]{0,62}$/.test(value),'invalid-catalog-identifier');return value;};
const rows=result=>{need(Array.isArray(result?.rows),'invalid-query-result');return result.rows;};

// A fixed catalog-only transaction. No caller supplies SQL or table names.
// Limits include one overflow sentinel, so oversized inventories fail closed.
export const storageQueries=Object.freeze([
  "SELECT set_config('statement_timeout','5000',true) AS statement_timeout,set_config('lock_timeout','1000',true) AS lock_timeout",
  `SELECT current_database() AS database_name,current_user AS role_name,
    current_setting('transaction_read_only') AS read_only,
    current_setting('statement_timeout') AS statement_timeout,current_setting('lock_timeout') AS lock_timeout,
    current_setting('neon.endpoint_id',true) AS endpoint_id,
    pg_database_size(current_database())::text AS database_bytes,clock_timestamp()::text AS observed_at`,
  `SELECT c.relname AS table_name,c.relkind AS relation_kind,
    pg_relation_size(c.oid)::text AS heap_main_bytes,
    CASE WHEN c.reltoastrelid=0 THEN '0' ELSE pg_total_relation_size(c.reltoastrelid)::text END AS toast_total_bytes,
    pg_table_size(c.oid)::text AS table_bytes,pg_indexes_size(c.oid)::text AS index_bytes,
    pg_total_relation_size(c.oid)::text AS total_bytes,
    s.n_live_tup::text AS estimated_live_rows,s.n_dead_tup::text AS estimated_dead_rows,
    s.last_analyze::text AS last_analyze,s.last_autoanalyze::text AS last_autoanalyze
    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
    LEFT JOIN pg_stat_all_tables s ON s.relid=c.oid
    WHERE n.nspname='public' AND c.relname LIKE 'atlas\\_%' ESCAPE '\\' AND c.relkind IN ('r','p','m')
    ORDER BY c.relname LIMIT 513`,
  `SELECT t.relname AS table_name,i.relname AS index_name,pg_relation_size(i.oid)::text AS index_bytes,
    pg_get_indexdef(i.oid) AS definition,x.indisvalid AS valid,x.indisready AS ready
    FROM pg_index x JOIN pg_class i ON i.oid=x.indexrelid JOIN pg_class t ON t.oid=x.indrelid
    JOIN pg_namespace n ON n.oid=t.relnamespace
    WHERE n.nspname='public' AND t.relname LIKE 'atlas\\_%' ESCAPE '\\' AND t.relkind IN ('r','p','m')
    ORDER BY t.relname,i.relname LIMIT 4097`
]);

export function validateStorageResults(results,{endpointId}={}) {
  need(Array.isArray(results)&&results.length===storageQueries.length,'transaction-result-mismatch');
  const settings=rows(results[0]),identity=rows(results[1]);
  need(settings.length===1&&settings[0].statement_timeout==='5s'&&settings[0].lock_timeout==='1s','timeout-configuration-mismatch');
  need(identity.length===1,'identity-result-mismatch');const id=identity[0];
  need(id.database_name===storageTarget.database&&id.role_name===storageTarget.role&&id.read_only==='on','read-only-identity-mismatch');
  need(id.statement_timeout==='5s'&&id.lock_timeout==='1s','transaction-timeouts-mismatch');
  need(id.endpoint_id==null||id.endpoint_id===''||id.endpoint_id===endpointId,'sql-endpoint-mismatch');
  need(typeof id.observed_at==='string'&&id.observed_at.length<100&&Number.isFinite(Date.parse(id.observed_at)),'invalid-observation-time');
  const tableRows=rows(results[2]),indexRows=rows(results[3]);
  need(tableRows.length>0&&tableRows.length<=512&&indexRows.length<=4096,'catalog-inventory-limit');
  const names=new Set();
  const tables=tableRows.map(row=>{
    const name=identifier(row.table_name);need(name.startsWith('atlas_')&&!names.has(name)&&['r','p','m'].includes(row.relation_kind),'table-inventory-mismatch');names.add(name);
    const sizes=Object.fromEntries(['heap_main_bytes','toast_total_bytes','table_bytes','index_bytes','total_bytes'].map(k=>[k,number(row[k])]));
    for(const k of ['estimated_live_rows','estimated_dead_rows'])sizes[k]=row[k]==null?null:number(row[k]);
    need(sizes.total_bytes===sizes.table_bytes+sizes.index_bytes&&sizes.table_bytes>=sizes.heap_main_bytes+sizes.toast_total_bytes,'table-accounting-mismatch');
    const timestamps={};for(const k of ['last_analyze','last_autoanalyze']){need(row[k]==null||typeof row[k]==='string'&&row[k].length<100&&Number.isFinite(Date.parse(row[k])),'invalid-statistics-time');timestamps[k]=row[k]??null;}
    return {table_name:name,relation_kind:row.relation_kind,...sizes,heap_auxiliary_bytes:sizes.table_bytes-sizes.heap_main_bytes-sizes.toast_total_bytes,...timestamps};
  });
  const indexNames=new Set();
  const indexes=indexRows.map(row=>{
    const table=identifier(row.table_name),name=identifier(row.index_name);need(names.has(table)&&!indexNames.has(name),'index-inventory-mismatch');indexNames.add(name);
    need(typeof row.definition==='string'&&Buffer.byteLength(row.definition)<=8192&&!/[\u0000-\u001f\u007f]/.test(row.definition)&&/^CREATE (UNIQUE )?INDEX /.test(row.definition),'unsafe-index-definition');
    need(typeof row.valid==='boolean'&&typeof row.ready==='boolean','invalid-index-state');
    return {table_name:table,index_name:name,index_bytes:number(row.index_bytes),definition:row.definition,valid:row.valid,ready:row.ready};
  });
  const databaseBytes=number(id.database_bytes),applicationBytes=tables.reduce((n,t)=>n+t.total_bytes,0);
  need(Number.isSafeInteger(applicationBytes)&&applicationBytes<=databaseBytes,'database-accounting-mismatch');
  return {observed_at_utc:new Date(id.observed_at).toISOString(),database_bytes:databaseBytes,application_relation_bytes:applicationBytes,
    other_database_bytes:databaseBytes-applicationBytes,tables,indexes,checks:{transaction_read_only:true,expected_sql_identity:true,
      sql_endpoint_setting_present:!!id.endpoint_id,timeouts_verified:true,table_accounting_verified:true},
    limitations:['Catalog live/dead tuple counts are estimates, not COUNT(*) or reclaimable bytes; missing statistics are null.',
      'pg_database_size is physical database allocation, distinct from Neon logical usage, plan allowance and billing.',
      'Other database bytes include non-application relations, catalogs and allocation overhead; this is not a free-space measurement.',
      'Sizes/statistics may change during concurrent activity; catalog/size functions are not a frozen physical snapshot.',
      'Index main-fork sizes omit auxiliary forks; table index_bytes includes complete attached index storage. TOAST total includes its index.',
      'No raw facts, wide table scans, ANALYZE, VACUUM, DDL, deletion, provisioning, imports or paid changes.']};
}

export const liveStorageDriver=(uri,sqlFactory=neon)=>{
  const sql=sqlFactory(uri,{fullResults:true,arrayMode:false});
  return ()=>sql.transaction(tx=>storageQueries.map(query=>tx.query(query,[])),{
    readOnly:true,isolationLevel:'RepeatableRead',fullResults:true,arrayMode:false,
    fetchOptions:{signal:AbortSignal.timeout(30000),redirect:'error'}
  });
};

export async function measureNeonStorage({env=process.env,fetchImpl=fetch,driverFactory=liveStorageDriver}={}) {
  const apiKey=env.NEON_API_KEY,projectId=env.NEON_PROJECT_ID;
  need(typeof apiKey==='string'&&apiKey.trim()&&!/[\r\n]/.test(apiKey),'missing-api-key');
  need(projectId===storageTarget.project,'unexpected-project');
  let requestCount=0;const secrets=[apiKey.trim()];
  const get=async route=>{
    need(++requestCount<=5,'management-request-limit');let response;
    try{response=await fetchImpl(new URL(route,apiOrigin),{method:'GET',headers:{Authorization:'Bearer '+apiKey.trim(),Accept:'application/json'},redirect:'error',signal:AbortSignal.timeout(15000)});}catch{throw new StorageError('management-unavailable');}
    if(!response.ok){try{await response.body?.cancel();}catch{}throw new StorageError('management-http-error');}
    const chunks=[];let size=0;try{for await(const chunk of response.body){size+=chunk.length;need(size<=responseLimit,'management-response-limit');chunks.push(chunk);}}finally{try{await response.body?.cancel();}catch{}}
    let json;try{json=JSON.parse(Buffer.concat(chunks));}catch{throw new StorageError('invalid-management-json');}need(json&&typeof json==='object'&&!Array.isArray(json),'invalid-management-object');return json;
  };
  const prefix='projects/'+storageTarget.project;
  const {project}=await get(prefix);need(project?.id===storageTarget.project,'project-mismatch');
  const {branch}=await get(prefix+'/branches/'+storageTarget.branch);
  need(branch?.id===storageTarget.branch&&branch.name==='production'&&(branch.project_id==null||branch.project_id===storageTarget.project),'production-branch-mismatch');
  const {endpoints}=await get(prefix+'/endpoints');need(Array.isArray(endpoints)&&endpoints.length<=100,'endpoint-inventory-limit');
  const selected=endpoints.filter(e=>e.branch_id===storageTarget.branch&&e.type==='read_write');
  need(selected.length===1,'production-endpoint-not-unique');const endpoint=selected[0];
  need(/^ep-[a-z0-9-]{1,150}$/.test(endpoint.id??'')&&/^ep-[a-z0-9-]+(?:\.[a-z0-9-]+)+\.neon\.tech$/.test(endpoint.host??'')&&endpoint.host.startsWith(endpoint.id+'.')&&(endpoint.project_id==null||endpoint.project_id===storageTarget.project),'production-endpoint-mismatch');
  const {uri}=await get(prefix+'/connection_uri?'+new URLSearchParams({branch_id:storageTarget.branch,database_name:storageTarget.database,role_name:storageTarget.role,pooled:'false'}));
  let parsed;try{parsed=new URL(uri);}catch{throw new StorageError('invalid-connection');}
  need(['postgres:','postgresql:'].includes(parsed.protocol)&&parsed.hostname===endpoint.host&&!parsed.port&&!parsed.hash&&decodeURIComponent(parsed.username)===storageTarget.role&&decodeURIComponent(parsed.pathname)==='/'+storageTarget.database&&parsed.password&&parsed.searchParams.get('sslmode')==='require'&&[...parsed.searchParams.keys()].every(k=>k==='sslmode'||k==='channel_binding'),'production-connection-mismatch');
  secrets.push(uri,parsed.password,decodeURIComponent(parsed.password));
  let results;try{results=await driverFactory(uri)();}catch{throw new StorageError('catalog-transaction-unavailable');}
  const observation=validateStorageResults(results,{endpointId:endpoint.id});
  const optionalNumber=value=>value==null?null:number(value);
  need(env.GITHUB_SHA==null||/^[0-9a-f]{40}$/.test(env.GITHUB_SHA),'invalid-source-commit');
  const receipt={version:1,status:'measured',read_only:true,source_commit:env.GITHUB_SHA??null,project_id:storageTarget.project,production_branch_id:storageTarget.branch,
    endpoint_id:endpoint.id,credentials_logged:false,management_requests:requestCount,...observation,
    provider:{branch_logical_size_bytes:optionalNumber(branch.logical_size),branch_logical_size_limit_mib:optionalNumber(project.branch_logical_size_limit),
      logical_usage_source:branch.logical_size==null?'unavailable':'Neon GET branch logical_size',
      billing_usage:{status:'unavailable',reason:'Fixed project/branch responses do not establish billing-metered usage or actual charges.'}}};
  const serialized=JSON.stringify(receipt);need(Buffer.byteLength(serialized)<=receiptLimit&&!secrets.some(s=>s&&serialized.includes(s))&&!/postgres(?:ql)?:\/\//i.test(serialized),'unsafe-or-oversized-receipt');
  return receipt;
}

export async function runStorageMeasurement({filename='data/validation/neon-table-storage.json',...options}={}) {
  let receipt;try{receipt=await measureNeonStorage(options);}catch(error){receipt={version:1,status:'failed',read_only:true,observed_at_utc:new Date().toISOString(),credentials_logged:false,error_code:error instanceof StorageError?error.code:'measurement-unavailable'};}
  fs.mkdirSync(path.dirname(filename),{recursive:true});fs.writeFileSync(filename,JSON.stringify(receipt,null,2)+'\n',{mode:0o600});return receipt;
}
if(process.argv[1]&&pathToFileURL(path.resolve(process.argv[1])).href===import.meta.url){
  try{const receipt=await runStorageMeasurement({filename:process.argv[2]??undefined});console.log(JSON.stringify(receipt));if(receipt.status!=='measured')process.exitCode=1;}
  catch{console.error('{"status":"failed","error_code":"receipt-write-unavailable","credentials_logged":false}');process.exitCode=1;}
}
