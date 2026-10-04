/** Database-only proof: unchanged Site24 read functions, actual application
 * login, original owner heap as oracle. This does not contact the deployed Site. */
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {createPostgresDatabase} from '../hosted/postgres-adapter.js';
import {geographicRelease,geographicMembershipPage,geographicChangePage} from '../hosted/geographic-releases.js';
import {entityProfile} from '../hosted/records.js';

const need=(v,code)=>{if(!v)throw Error(code);};
const hash=b=>createHash('sha256').update(b).digest('hex');
export const normalAPISource=Object.freeze({
 commit:'c5fce09842a0af2ae05cf6c611f012b6a71befff',
 files:{'hosted/geographic-releases.js':'9eba2ddeeb267ca09dc396225b8fe27385c1834ab6f9ebf5cb627ae38ebf1701',
 'hosted/records.js':'f5ba42a6059da63dd2db1308b3852422252ffb61cb13f5e3b29d27dbfce4083d',
 'hosted/postgres-adapter.js':'427f48417ea5008146edfb77fd732ba017286a2484f412329452e135073c9ab0',
 'src/model.js':'6cf64270d9c912b09aa93c60a14d058b4482c52e5ffa31d55fdcef026bea3dcc',
 'src/environment-classifications.js':'d589aa3aa91831f0d1d2b5a21e161270ba44e86ef90dea23110a761510074970'}
});
function assertSource(){for(const [file,expected]of Object.entries(normalAPISource.files))
 need(hash(fs.readFileSync(new URL('../'+file,import.meta.url)))===expected,'changed-original-api-function-source');}
function database(query,original=false){return createPostgresDatabase({
 query:(sql,args)=>{need(/^SELECT\b/i.test(sql),'api-proof-write-forbidden');
  return query(original?sql.replaceAll('atlas_geographic_memberships','worldatlas_memberships_original_v1'):sql,args);},
 transaction:()=>{throw Error('api-proof-batch-forbidden');}
},{timeoutMs:60000});}
async function read(db,request){
 const {kind,releaseId,...options}=request;
 if(kind==='release')return geographicRelease(db,releaseId);
 if(kind==='memberships')return geographicMembershipPage(db,{releaseId,...options});
 if(kind==='changes')return geographicChangePage(db,{releaseId,...options});
 if(kind==='profile')return entityProfile(db,options.id,2026,{releaseId});
 throw Error('unknown-normal-api-proof-request');
}
function digest(value){const text=JSON.stringify(value);need(Buffer.byteLength(text)<=4*1024**2,'api-proof-response-bound');return hash(text);}
export async function originalMembershipAPIPlan(ownerQuery){
 assertSource();const db=database(ownerQuery,true),plan=[];
 const releases=(await ownerQuery("SELECT id FROM atlas_geographic_releases WHERE status='published' ORDER BY version")).rows;
 need(releases.length>0&&releases.length<=20,'unbounded-api-proof-releases');
 const add=async request=>{const value=await read(db,request);plan.push({request,sha256:digest(value)});return value;};
 for(const {id:releaseId}of releases){
  await add({kind:'release',releaseId});
  const page=await add({kind:'memberships',releaseId,limit:200});
  need(page.records.length>0,'empty-published-membership-proof');
  if(page.next_cursor)await add({kind:'memberships',releaseId,limit:200,cursor:page.next_cursor});
  const child=page.records.find(row=>row.parent_id!==null);
  need(child,'missing-parent-membership-proof');
  await add({kind:'memberships',releaseId,limit:200,parentId:child.parent_id});
  await add({kind:'memberships',releaseId,limit:200,active:null});
  await add({kind:'profile',releaseId,id:child.entity_id});
  await add({kind:'profile',releaseId,id:'worldatlas-api-proof:absent-entity'});
  await add({kind:'changes',releaseId,limit:200});
 }
 return plan;
}
export async function verifyApplicationMembershipAPI(appQuery,plan){
 assertSource();need(Array.isArray(plan)&&plan.length>0&&plan.length<=160,'unbounded-api-proof-plan');
 const identity=(await appQuery("SELECT current_user role,session_user login,current_setting('transaction_read_only') read_only")).rows[0];
 need(identity?.role==='worldatlas_app'&&identity.login==='worldatlas_app'&&identity.read_only==='on','api-proof-not-readonly-application-login');
 const db=database(appQuery);
 for(const entry of plan)need(digest(await read(db,entry.request))===entry.sha256,'normal-api-function-response-changed');
 return {status:'verified',scope:'live-Neon-original-API-functions',application_login:true,read_only:true,
  probes:plan,source:normalAPISource,served_http_verified:false,writes_restored:false,
  limitations:['No deployed Site HTTP routing or authentication proof.','Old Site24 strict V2 catalog/export endpoints require the later compatible worker deployment.','API parsed JSON parity supplements, and does not replace, full raw TEXT membership parity.']};
}
