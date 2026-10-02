import fs from 'node:fs';
import path from 'node:path';
import {createHash,randomUUID} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {neon} from '@neondatabase/serverless';
import {createNeonDatabase} from '../hosted/postgres-adapter.js';
import {exercisePostgresSmoke,postgresSchemaInventory,postgresSchemaURL,postgresTables} from './verify-postgres-schema.mjs';
import {expectedNeonProjectId,verifyNeonProject} from './verify-neon-project.mjs';

export const productionBranchId='br-summer-butterfly-ar8qikk5';
const databaseName='neondb',roleName='neondb_owner';
const apiOrigin='https://console.neon.tech/api/v2/';
const responseLimit=2*1024*1024,receiptLimit=64*1024;
class VerificationError extends Error{constructor(code){super(code);this.code=code;}}
const fail=code=>{throw new VerificationError(code);};
const object=value=>value!==null&&typeof value==='object'&&!Array.isArray(value);
const validBranchId=value=>typeof value==='string'&&/^br-[a-z0-9-]{1,150}$/.test(value);
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));

/** Split PostgreSQL commands without altering command bytes. Dollar-quoted
 * PL/pgSQL, nested comments, escaped strings and quoted identifiers are opaque.
 * The schema's outer BEGIN/COMMIT is replaced by the HTTP driver's transaction.
 */
export function schemaTransactionStatements(schema){
 if(typeof schema!=='string'||Buffer.byteLength(schema)>1024*1024)fail('invalid-schema-size');
 const statements=[];let start=0,i=0,blockDepth=0,quote=null,dollar=null,lineComment=false;
 while(i<schema.length){
  const ch=schema[i],next=schema[i+1];
  if(lineComment){if(ch==='\n')lineComment=false;i++;continue;}
  if(blockDepth){if(ch==='/'&&next==='*'){blockDepth++;i+=2;}else if(ch==='*'&&next==='/'){blockDepth--;i+=2;}else i++;continue;}
  if(dollar){if(schema.startsWith(dollar,i)){i+=dollar.length;dollar=null;}else i++;continue;}
  if(quote){
   if(ch===quote.character){if(next===quote.character)i+=2;else{quote=null;i++;}}
   else if(ch==='\\'&&quote.escaped)i+=2;else i++;
   continue;
  }
  if(ch==='-'&&next==='-'){lineComment=true;i+=2;continue;}
  if(ch==='/'&&next==='*'){blockDepth=1;i+=2;continue;}
  if(ch==='\''||ch==='"'){
   const prior=schema[i-1],before=schema[i-2];
   quote={character:ch,escaped:ch==='\''&&(prior==='e'||prior==='E')&&(!before||!/[\w$]/.test(before))};i++;continue;
  }
  if(ch==='$'){
   const match=schema.slice(i).match(/^\$(?:[A-Za-z_][A-Za-z_0-9]*)?\$/);
   if(match){dollar=match[0];i+=dollar.length;continue;}
  }
  if(ch===';'){statements.push(schema.slice(start,i+1));start=++i;continue;}
  i++;
 }
 if(quote||dollar||blockDepth)fail('unterminated-schema-token');
 // Only comments/whitespace may follow the schema's final command.
 const stripComments=text=>{
  let offset=0;
  for(;;){
   while(/\s/.test(text[offset]??'')&&offset<text.length)offset++;
   if(text.startsWith('--',offset)){const end=text.indexOf('\n',offset+2);offset=end<0?text.length:end+1;continue;}
   if(text.startsWith('/*',offset)){
    let depth=1;offset+=2;
    while(offset<text.length&&depth){if(text.startsWith('/*',offset)){depth++;offset+=2;}else if(text.startsWith('*/',offset)){depth--;offset+=2;}else offset++;}
    if(depth)fail('unterminated-schema-comment');continue;
   }
   return text.slice(offset).trim();
  }
 };
 if(stripComments(schema.slice(start)))fail('unterminated-schema-command');
 if(stripComments(statements[0]??'').toUpperCase()!=='BEGIN;'||stripComments(statements.at(-1)??'').toUpperCase()!=='COMMIT;')fail('schema-transaction-wrapper-missing');
 const result=statements.slice(1,-1);
 if(!result.length||result.length>1000||result.some(command=>/^(BEGIN|COMMIT|ROLLBACK)\b/i.test(stripComments(command))))fail('unsupported-schema-transaction');
 return result;
}

async function boundedJSON(response){
 const reader=response.body?.getReader();if(!reader)fail('empty-management-response');
 const chunks=[];let size=0;
 try{for(;;){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>responseLimit)fail('management-response-too-large');chunks.push(value);}}
 finally{try{await reader.cancel();}catch{}}
 const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength;}
 let result;try{result=JSON.parse(new TextDecoder().decode(bytes));}catch{fail('invalid-management-json');}
 if(!object(result))fail('invalid-management-object');return result;
}
function writeReceipt(filename,receipt){
 const text=JSON.stringify(receipt,null,2)+'\n';if(Buffer.byteLength(text)>receiptLimit)fail('receipt-too-large');
 fs.mkdirSync(path.dirname(filename),{recursive:true});fs.writeFileSync(filename,text,{mode:0o600});
}
function connectionURI(value,endpointHost){
 if(typeof value!=='string'||value.length>16384)fail('invalid-isolated-connection');
 let uri;try{uri=new URL(value);}catch{fail('invalid-isolated-connection');}
 if(!['postgres:','postgresql:'].includes(uri.protocol)||!uri.hostname.endsWith('.neon.tech')||decodeURIComponent(uri.username)!==roleName||decodeURIComponent(uri.pathname)!=='/'+databaseName||!uri.password||uri.hash)fail('unexpected-isolated-connection');
 const pooledHost=endpointHost.replace(/^([^.]+)\./,'$1-pooler.');
 if(uri.hostname!==endpointHost&&uri.hostname!==pooledHost)fail('connection-endpoint-branch-mismatch');
 if(uri.searchParams.get('sslmode')!=='require')fail('isolated-connection-requires-tls');
 return value;
}
const liveDrivers=uri=>({sql:neon(uri,{fullResults:true,arrayMode:false}),db:createNeonDatabase(uri,{timeoutMs:30000})});

/** All SQL writes target the connection returned for this invocation's newly
 * created branch. Production is queried through management metadata only.
 * No connection string, API response body or raw driver error enters receipts.
 */
export async function verifyNeonSQL({env=process.env,filename='data/validation/neon-sql-verification.json',fetchImpl=fetch,driverFactory=liveDrivers,sleep=pause,uuid=randomUUID}={}){
 const receipt={status:'running',scope:'new disposable Neon validation branch',checked_at_utc:new Date().toISOString(),project_id:expectedNeonProjectId,production_branch_id:productionBranchId,production_sql_writes:false,credentials_logged:false,cleanup_status:'not-required'};
 let createdId=null,requestCount=0,parentRequestCount=0,stage='configuration';
 const checkpoint=()=>writeReceipt(filename,receipt);
 const apiKey=env.NEON_API_KEY,projectId=env.NEON_PROJECT_ID;
 const request=async(method,route,body)=>{
  if(++requestCount>90)fail('management-request-limit');
  let response;try{response=await fetchImpl(new URL(route,apiOrigin),{method,headers:{Authorization:`Bearer ${apiKey.trim()}`,Accept:'application/json',...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{}),redirect:'error',signal:AbortSignal.timeout(15000)});}catch{fail('management-request-unavailable');}
  if(method==='DELETE'&&(response.ok||response.status===404)){try{await response.body?.cancel();}catch{}return null;}
  if(!response.ok){try{await response.body?.cancel();}catch{}fail('management-http-error');}
  return boundedJSON(response);
 };
 const prefix=`projects/${encodeURIComponent(expectedNeonProjectId)}`;
 try{
  if(typeof apiKey!=='string'||!apiKey.trim()||/[\r\n]/.test(apiKey))fail('missing-or-invalid-api-key');
  if(projectId!==expectedNeonProjectId)fail('unexpected-project-id');
  const schema=fs.readFileSync(postgresSchemaURL,'utf8'),commands=schemaTransactionStatements(schema);
  receipt.schema_sha256=createHash('sha256').update(schema).digest('hex');receipt.schema_statements=commands.length;
  stage='parent-verification';
  const parent=await verifyNeonProject({apiKey,projectId,fetchImpl});
  parentRequestCount=parent.api_requests;
  if(parent.branch.id!==productionBranchId||parent.project.configured_postgres_major!==18||!parent.databases.some(database=>database.name===databaseName&&database.owner_name===roleName)||!parent.roles.some(role=>role.name===roleName))fail('verified-parent-contract-mismatch');
  const nonce=uuid();if(typeof nonce!=='string'||!/^[a-f0-9-]{36}$/.test(nonce))fail('invalid-validation-nonce');
  const branchName=`atlas-sql-check-${nonce}`;stage='branch-creation';
  receipt.validation_branch_name=branchName;receipt.cleanup_status='creation-unconfirmed';checkpoint();
  const result=await request('POST',prefix+'/branches',{branch:{name:branchName,parent_id:productionBranchId},endpoints:[{type:'read_write'}]});
  const branch=result.branch;
  // Capture an authenticated create response ID before any subsequent failure,
  // but categorically refuse to delete or connect to the production ID.
  if(object(branch)&&validBranchId(branch.id)&&branch.id!==productionBranchId){createdId=branch.id;receipt.validation_branch_id=createdId;receipt.validation_branch_name=branchName;receipt.cleanup_status='pending';checkpoint();}
  if(!createdId||branch.name!==branchName||branch.parent_id!==productionBranchId||branch.project_id!==undefined&&branch.project_id!==projectId)fail('created-branch-contract-mismatch');
  if(!Array.isArray(result.endpoints)||result.endpoints.length>20)fail('missing-created-endpoint');
  const endpoints=result.endpoints.filter(endpoint=>object(endpoint)&&endpoint.branch_id===createdId&&endpoint.type==='read_write');
  if(endpoints.length!==1||typeof endpoints[0].host!=='string'||!/^ep-[a-z0-9-]+(?:\.[a-z0-9-]+)+\.neon\.tech$/.test(endpoints[0].host))fail('invalid-created-endpoint');
  const endpointHost=endpoints[0].host;
  stage='branch-readiness';let ready=false;
  for(let attempt=0;attempt<30;attempt++){
   const observed=await request('GET',prefix+'/branches/'+encodeURIComponent(createdId));
   if(!object(observed.branch)||observed.branch.id!==createdId||observed.branch.parent_id!==productionBranchId||observed.branch.name!==branchName)fail('isolated-branch-response-mismatch');
   if(observed.branch.current_state==='ready'){ready=true;break;}
   if(['failed','deleting','deleted'].includes(observed.branch.current_state))fail('isolated-branch-unavailable');
   await sleep(2000);
  }
  if(!ready)fail('isolated-branch-readiness-timeout');
  stage='isolated-connection';
  const params=new URLSearchParams({branch_id:createdId,database_name:databaseName,role_name:roleName,pooled:'true'});
  const connection=await request('GET',prefix+'/connection_uri?'+params);
  const drivers=driverFactory(connectionURI(connection.uri,endpointHost));
  let identity;
  for(let attempt=0;attempt<4;attempt++){
   try{identity=await drivers.db.prepare("SELECT current_database() AS database_name,current_user AS role_name,current_schema() AS schema_name,current_setting('server_version_num') AS server_version_num").first();break;}
   catch{if(attempt===3)fail('isolated-sql-connection-unavailable');await sleep(2000);}
  }
  if(identity?.database_name!==databaseName||identity.role_name!==roleName||identity.schema_name!=='public'||!/^18\d{4}$/.test(String(identity.server_version_num)))fail('isolated-database-identity-mismatch');
  receipt.postgres_major=18;receipt.database_name=databaseName;receipt.role_name=roleName;
  stage='empty-schema-verification';
  const existing=await drivers.db.prepare("SELECT count(*) AS count FROM information_schema.tables WHERE table_schema=current_schema() AND table_type='BASE TABLE'").first();
  if(Number(existing?.count)!==0)fail('validation-schema-not-empty');
  stage='schema-transaction';
  const applied=await drivers.sql.transaction(tx=>commands.map(command=>tx.query(command,[])),{isolationLevel:'Serializable',fullResults:true,arrayMode:false,fetchOptions:{signal:AbortSignal.timeout(120000)}});
  if(!Array.isArray(applied)||applied.length!==commands.length)fail('schema-transaction-result-mismatch');
  stage='schema-inventory';const inventory=await postgresSchemaInventory(drivers.db);
  if(!inventory.schema_complete||inventory.tables.length!==postgresTables.length||inventory.tables.some(name=>!postgresTables.includes(name)))fail('schema-inventory-mismatch');
  receipt.schema_tables=[...postgresTables];receipt.schema_complete=true;
  stage='hosted-service-contracts';
  const smoke=await exercisePostgresSmoke(drivers.db);
  if(smoke.retained_original_population!==42||smoke.resolved_population!==43)fail('hosted-service-contract-mismatch');
  receipt.actual_hosted_service_checks=smoke.actual_hosted_service_checks;
  receipt.retained_original_population=42;receipt.resolved_population=43;
  receipt.sql_contracts_passed=true;receipt.status='verified';
 }catch(error){
  receipt.status='failed';receipt.failure_stage=stage;receipt.error_code=error instanceof VerificationError?error.code:`${stage}-failed`;
  const sqlstate=error?.sqlstate??error?.code;if(!(error instanceof VerificationError)&&typeof sqlstate==='string'&&/^[A-Z0-9]{5}$/.test(sqlstate))receipt.sqlstate=sqlstate;
 }
 finally{
  if(createdId){
   try{
    if(!validBranchId(createdId)||createdId===productionBranchId)fail('unsafe-cleanup-target');
    await request('DELETE',prefix+'/branches/'+encodeURIComponent(createdId));receipt.cleanup_status='deleted';
   }catch{receipt.cleanup_status='failed';receipt.status='failed';receipt.cleanup_error_code='validation-branch-cleanup-failed';receipt.retained_validation_branch_id=createdId;}
  }
  receipt.management_requests=requestCount+parentRequestCount;receipt.completed_at_utc=new Date().toISOString();
  receipt.limitations=['No production schema, data import, runtime binding or Neon Auth change.','This small isolated service smoke test does not certify production migration or dataset capacity.'];
  checkpoint();
 }
 return receipt;
}

if(process.argv[1]&&pathToFileURL(path.resolve(process.argv[1])).href===import.meta.url){
 try{const receipt=await verifyNeonSQL({filename:process.argv[2]??undefined});console.log(JSON.stringify(receipt));if(receipt.status!=='verified')process.exitCode=1;}
 catch{console.error(JSON.stringify({status:'failed',error_code:'sanitized-receipt-write-failed',credentials_logged:false}));process.exitCode=1;}
}
