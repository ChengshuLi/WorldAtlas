import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

export const expectedNeonProjectId='weathered-lab-37571695';
const apiOrigin='https://console.neon.tech/api/v2/';
const responseByteLimit=2*1024*1024,receiptByteLimit=64*1024;
class VerificationError extends Error{
 constructor(code,httpStatus=null){super(code);this.code=code;this.httpStatus=httpStatus;}
}
const fail=(code,status)=>{throw new VerificationError(code,status);};
const object=value=>value!==null&&typeof value==='object'&&!Array.isArray(value);
const label=(value,code)=>{
 if(typeof value!=='string'||!value.trim()||value.length>200||/[\u0000-\u001f\u007f]/.test(value)||/\w+:\/\//.test(value))fail(code);
 return value;
};
async function boundedJSON(response){
 const chunks=[];let length=0;const reader=response.body?.getReader();if(!reader)fail('empty-api-response');
 try{for(;;){const {done,value}=await reader.read();if(done)break;length+=value.byteLength;if(length>responseByteLimit)fail('api-response-too-large');chunks.push(value);}}
 finally{try{await reader.cancel();}catch{}}
 const bytes=new Uint8Array(length);let offset=0;for(const part of chunks){bytes.set(part,offset);offset+=part.byteLength;}
 let body;try{body=JSON.parse(new TextDecoder().decode(bytes));}catch{fail('invalid-api-json');}if(!object(body))fail('invalid-api-object');return body;
}

/** Project-scoped management metadata only. No connection URI, SQL endpoint,
 * password, role creation, branch creation or write request is ever used.
 */
export async function verifyNeonProject({apiKey,projectId,fetchImpl=fetch}={}){
 if(typeof apiKey!=='string'||!apiKey.trim()||/[\r\n]/.test(apiKey))fail('missing-or-invalid-api-key');
 if(projectId!==expectedNeonProjectId)fail('unexpected-project-id');
 let requests=0;
 const get=async route=>{
  requests++;if(requests>20)fail('api-request-limit');
  let response;try{response=await fetchImpl(new URL(route,apiOrigin),{method:'GET',headers:{Authorization:`Bearer ${apiKey.trim()}`,Accept:'application/json'},redirect:'error',signal:AbortSignal.timeout(15000)});}catch{fail('api-request-unavailable');}
  if(!response.ok){try{await response.body?.cancel();}catch{}fail('neon-api-http-error',response.status);}
  return boundedJSON(response);
 };
 const prefix=`projects/${encodeURIComponent(projectId)}`;
 const projectResponse=await get(prefix),project=projectResponse.project;
 if(!object(project)||project.id!==expectedNeonProjectId)fail('project-response-mismatch');
 const version=typeof project.pg_version==='number'?project.pg_version:typeof project.pg_version==='string'&&/^\d+$/.test(project.pg_version)?Number(project.pg_version):NaN;
 if(!Number.isInteger(version)||version<14||version>99)fail('postgres-major-unavailable');
 const allBranches=[],cursors=new Set();let cursor='';
 do{
  const params=new URLSearchParams({limit:'100'});if(cursor)params.set('cursor',cursor);
  const result=await get(prefix+'/branches?'+params);
  if(!Array.isArray(result.branches)||result.branches.length>100)fail('invalid-branch-list');allBranches.push(...result.branches);
  if(allBranches.length>1000)fail('branch-inventory-too-large');
  cursor=result.pagination?.cursor??result.next_cursor??'';
  if(cursor){label(cursor,'invalid-branch-cursor');if(cursors.has(cursor))fail('repeated-branch-cursor');cursors.add(cursor);}
 }while(cursor);
 const production=allBranches.filter(branch=>object(branch)&&branch.name==='production');
 if(production.length!==1)fail('production-branch-not-unique');
 const branch=production[0],branchId=label(branch.id,'invalid-production-branch-id');
 if(branch.project_id!==undefined&&branch.project_id!==projectId)fail('production-project-mismatch');
 const [databaseResponse,roleResponse]=await Promise.all([get(prefix+'/branches/'+encodeURIComponent(branchId)+'/databases'),get(prefix+'/branches/'+encodeURIComponent(branchId)+'/roles')]);
 if(!Array.isArray(databaseResponse.databases)||!databaseResponse.databases.length||databaseResponse.databases.length>200)fail('invalid-database-inventory');
 if(!Array.isArray(roleResponse.roles)||!roleResponse.roles.length||roleResponse.roles.length>200)fail('invalid-role-inventory');
 const roles=roleResponse.roles.map(role=>{if(!object(role)||role.branch_id!==undefined&&role.branch_id!==branchId)fail('role-branch-mismatch');return {name:label(role.name,'invalid-role-name')};}).sort((a,b)=>a.name<b.name?-1:a.name>b.name?1:0);
 const roleNames=new Set(roles.map(role=>role.name));if(roleNames.size!==roles.length)fail('duplicate-role-name');
 const databases=databaseResponse.databases.map(database=>{
  if(!object(database)||database.branch_id!==undefined&&database.branch_id!==branchId)fail('database-branch-mismatch');
  const name=label(database.name,'invalid-database-name'),owner=label(database.owner_name,'invalid-database-owner');if(!roleNames.has(owner))fail('database-owner-role-unavailable');return {name,owner_name:owner};
 }).sort((a,b)=>a.name<b.name?-1:a.name>b.name?1:0);
 if(new Set(databases.map(database=>database.name)).size!==databases.length)fail('duplicate-database-name');
 const receipt={status:'verified',read_only:true,checked_at_utc:new Date().toISOString(),project:{id:projectId,configured_postgres_major:version},branch:{id:branchId,name:'production',is_default:typeof branch.default==='boolean'?branch.default:typeof project.default_branch_id==='string'?project.default_branch_id===branchId:null},databases,roles,api_requests:requests,checks:{expected_project:true,production_branch:true,postgres_major_observed:true,database_owners_present:true},limitations:['Management API metadata only; no SQL connection or schema verification.','No migration, data import, Neon Auth configuration or runtime binding change.','A repository Actions secret does not configure the private Site runtime.']};
 const serialized=JSON.stringify(receipt);
 if(Buffer.byteLength(serialized)>receiptByteLimit||serialized.includes(apiKey.trim()))fail('unsafe-or-oversized-receipt');
 return receipt;
}

function writeReceipt(filename,receipt){const json=JSON.stringify(receipt,null,2)+'\n';if(Buffer.byteLength(json)>receiptByteLimit)fail('receipt-too-large');fs.mkdirSync(path.dirname(filename),{recursive:true});fs.writeFileSync(filename,json,{mode:0o600});}
export async function runNeonVerification({env=process.env,filename='data/validation/neon-project-verification.json',fetchImpl=fetch}={}){
 let receipt;
 try{receipt=await verifyNeonProject({apiKey:env.NEON_API_KEY,projectId:env.NEON_PROJECT_ID,fetchImpl});}
 catch(error){receipt={status:'failed',read_only:true,checked_at_utc:new Date().toISOString(),expected_project_id:expectedNeonProjectId,error_code:error instanceof VerificationError?error.code:'verification-unavailable',...(error instanceof VerificationError&&Number.isInteger(error.httpStatus)?{http_status:error.httpStatus}:{}),credentials_logged:false};}
 writeReceipt(filename,receipt);return receipt;
}
if(process.argv[1]&&pathToFileURL(path.resolve(process.argv[1])).href===import.meta.url){
 try{const receipt=await runNeonVerification({filename:process.argv[2]??undefined});console.log(JSON.stringify(receipt));if(receipt.status!=='verified')process.exitCode=1;}
 catch{console.error(JSON.stringify({status:'failed',read_only:true,error_code:'receipt-write-unavailable',credentials_logged:false}));process.exitCode=1;}
}
