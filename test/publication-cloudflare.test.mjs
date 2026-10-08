import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {readPublicationState,publicationPlan,validateDelivery} from '../scripts/publication-plan.mjs';
import {validateCloudflareOperation} from '../scripts/publication-cloudflare.mjs';
import {cloudflareFixture} from './fixtures/cloudflare-publication.mjs';
const root='/repos/ChengshuLi/WorldAtlas';
function fixture(){
 const cf=cloudflareFixture();
 const routes=new Map([[root+'/deployments?per_page=100&page=1',[cf.deployment]],
  [root+'/deployments/100/statuses?per_page=100&page=1',[cf.status]],
  [root+'/issues/comments/99',cf.receipt()]]);
 const api=async route=>{assert.ok(routes.has(route),'Unexpected '+route);return structuredClone(routes.get(route));};
 return {...cf,routes,api,refresh(){routes.set(root+'/issues/comments/99',this.receipt());}};
}
test('actual Cloudflare primary/provider/package delivery without Site identity',async()=>{
 const f=fixture(),state=await readPublicationState(f.api);
 assert.equal(state.delivery.provider,'cloudflare');assert.equal(state.delivery.cloudflare.deployment_id,'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee');
 assert.equal(state.site_delivery,null);assert.equal(state.cloudflare_delivery.primary_commit,'a'.repeat(40));
});
for(const [label,mutate] of [
 ['invented mirror',f=>f.delivery.source_commit='a'.repeat(40)],['invented Site',f=>f.delivery.site={version:24}],
 ['wrong provider deployment',f=>f.delivery.cloudflare.deployment_id='not-a-uuid'],['wrong registry identity',f=>f.delivery.cloudflare.registry_deployment_id=101],
 ['mismatched runtime package',f=>f.delivery.package_inventory_sha256='f'.repeat(64)],['missing lookup',f=>delete f.delivery.lookup_sha256],
 ['missing catalog',f=>delete f.op.catalog_sha256],['duplicate issue',f=>f.op.issues.push(849)],['missing issue',f=>f.op.issues=[]],
 ['incoherent singular issue',f=>f.op.issue=51],['wrong protocol',f=>delete f.op.protocol_version],['unbounded operation',f=>f.op.expires_at='2030-10-04T01:00:00Z'],
 ['missing rollback',f=>delete f.op.rollback_url],['unreviewed runtime',f=>delete f.op.runtime_review_url],
 ['anonymous result author',f=>{const c=f.receipt();c.author_association='NONE';f.receipt=()=>c;}],
 ['unconfirmed cleanup',f=>f.result.cleanup_confirmed=false],['missing acceptance row',f=>f.result.issue_checks=[]],
 ['writes enabled',f=>f.delivery.database_writes=true],['other task',f=>f.deployment.task='other'],
 ['unknown Cloudflare environment',f=>{f.deployment.environment='worldatlas-cloudflare-unknown';f.deployment.task=f.deployment.environment;}],
 ['unsettled receipt asserting delivery',f=>{f.result.state='unsettled';f.result.cleanup_confirmed=false;f.status.state='error';}],
])test('rejects '+label,async()=>{const f=fixture();mutate(f);f.refresh();await assert.rejects(()=>readPublicationState(f.api));});
test('failed CF operation is settled without advancing any boundary',async()=>{
 const f=fixture();f.result.state='failed-settled';f.result.delivery=null;f.status.state='failure';f.refresh();const state=await readPublicationState(f.api);assert.equal(state.delivery,null);assert.equal(state.unsettled.length,0);
});
test('unsettled cleanup blocks even with terminal error status',async()=>{
 const f=fixture();f.result.state='unsettled';f.result.cleanup_confirmed=false;f.result.delivery=null;f.status.state='error';f.refresh();const state=await readPublicationState(f.api);assert.equal(state.delivery,null);assert.equal(state.unsettled.length,1);
});
test('staging or native activity cannot hide behind a newer public success',async()=>{
 for(const environment of ['worldatlas-cloudflare-staging','worldatlas-production']){
  const f=fixture(),older=structuredClone(f.deployment);older.id=50;older.environment=environment;
  if(environment==='worldatlas-production'){older.task='worldatlas-publication';older.payload={worldatlas_publication:{version:1,operation_id:'recovery',publisher_worker_id:'publisher',kind:'recovery',primary_commit:older.sha,issues:[51],started_at:f.op.started_at,expires_at:f.op.expires_at,rollback_url:f.url}};}
  else{older.task=environment;older.payload.worldatlas_cloudflare.operation_id='22222222-3333-4444-5555-666666666666';older.payload.worldatlas_cloudflare.kind='staging';older.payload.worldatlas_cloudflare.public_reads=false;}
  f.routes.set(root+'/deployments?per_page=100&page=1',[f.deployment,older]);f.routes.set(root+'/deployments/50/statuses?per_page=100&page=1',[]);
  const state=await readPublicationState(f.api);assert.equal(state.delivery.primary_commit,f.deployment.sha);assert.equal(state.unsettled[0].deployment_id,50);
 }
});
test('Cloudflare history never substitutes current main and residuals survive missing labels',async()=>{
 const f=fixture();f.result.issue_checks[0].outcome='deferred';f.refresh();const target='b'.repeat(40);let reads=0;
 f.routes.set(root+'/commits/main',{sha:target});f.routes.set(root+'/issues?state=open&labels=publisher-needed&per_page=100&page=1',[]);
 f.routes.set(root+'/compare/'+f.op.primary_commit+'...'+target+'?per_page=100&page=1',{status:'identical',merge_base_commit:{sha:f.op.primary_commit},total_commits:0,commits:[]});
 f.routes.set(root+'/issues/849',{number:849,title:'Residual fixture',state:'closed',labels:[],html_url:f.url});
 const plan=await publicationPlan(async route=>{if(route===root+'/commits/main')reads++;return f.api(route);});
 assert.equal(reads,1);assert.equal(plan.target_commit,target);assert.equal(plan.last_delivery.primary_commit,'a'.repeat(40));assert.deepEqual(plan.issues[0].discovery,['outstanding-acceptance']);assert.equal(plan.issues[0].state,'closed');
});
test('a newer Site-only delivery cannot skip the undelivered Cloudflare application delta',async()=>{
 const f=fixture(),target='b'.repeat(40),url='https://github.com/ChengshuLi/WorldAtlas/issues/6#issuecomment-199';
 const site={id:200,sha:target,environment:'worldatlas-production',task:'worldatlas-publication',payload:{worldatlas_publication:{version:1,operation_id:'site-only',publisher_worker_id:'site-publisher',kind:'site',primary_commit:target,issues:[6],started_at:f.op.started_at,expires_at:f.op.expires_at,rollback_url:url}}};
 const delivery={version:1,primary_commit:target,source_commit:'c'.repeat(40),site:{project_id:'appgprj_6abdf87277c08191bce4a22b8dfb25db',version:25,deployment_id:'appgdep_fixture'},release_id:'site-release',hierarchy_sha256:'1'.repeat(64),footprint_sha256:'2'.repeat(64),assets_sha256:'3'.repeat(64),evidence_urls:[url]};
 const result={version:1,deployment_id:200,operation_id:'site-only',publisher_worker_id:'site-publisher',primary_commit:target,state:'verified',cleanup_confirmed:true,delivery,issue_checks:[{issue:6,outcome:'verified',evidence_urls:[url]}]};
 f.routes.set(root+'/deployments?per_page=100&page=1',[site,f.deployment]);f.routes.set(root+'/deployments/200/statuses?per_page=100&page=1',[{id:1001,state:'success',log_url:url}]);
 f.routes.set(root+'/issues/comments/199',{id:199,user:{type:'User'},author_association:'OWNER',html_url:url,body:'<!-- worldatlas-publication-result:v1\n'+JSON.stringify(result)+'\n-->'});
 f.routes.set(root+'/commits/main',{sha:target});f.routes.set(root+'/issues?state=open&labels=publisher-needed&per_page=100&page=1',[]);
 f.routes.set(root+'/compare/'+f.op.primary_commit+'...'+target+'?per_page=100&page=1',{status:'ahead',merge_base_commit:{sha:f.op.primary_commit},total_commits:1,commits:[{sha:target,commit:{message:'Not yet delivered to Cloudflare'}}]});
 f.routes.set(root+'/commits/'+target+'/pulls?per_page=100&page=1',[]);
 const state=await readPublicationState(f.api),plan=await publicationPlan(f.api);assert.equal(state.site_delivery.primary_commit,target);assert.equal(state.cloudflare_delivery.primary_commit,f.op.primary_commit);assert.equal(plan.last_delivery.provider,'cloudflare');assert.deepEqual(plan.commits.map(c=>c.sha),[target]);
});
test('distinct registry IDs cannot reuse the same operation UUID',async()=>{
 const f=fixture(),other=structuredClone(f.deployment);other.id=50;f.routes.set(root+'/deployments?per_page=100&page=1',[f.deployment,other]);f.routes.set(root+'/deployments/50/statuses?per_page=100&page=1',[]);
 await assert.rejects(()=>readPublicationState(f.api),/Duplicate operation identity/);
});
// Expectations come from the independently retained real registry, including the
// singular #822 registration, its supplemental #6 residual and both private stages.
const historical=JSON.parse(fs.readFileSync(new URL('../coordination/engineering/cloudflare-publication-846-20261007/registry-source.json',import.meta.url)));
function replay(snapshot){
 const routes=new Map([[root+'/deployments?per_page=100&page=1',snapshot.deployments.map(r=>r.deployment)]]);
 for(const row of snapshot.deployments){routes.set(root+'/deployments/'+row.deployment.id+'/statuses?per_page=100&page=1',row.statuses);if(row.receipt)routes.set(root+'/issues/comments/'+row.receipt.id,row.receipt);}
 return async route=>{assert.ok(routes.has(route),'Unknown replay '+route);return structuredClone(routes.get(route));};
}
test('replays complete real Site/native/CF history, without fabricating absent historical release pins',async()=>{
 const state=await readPublicationState(replay(historical));assert.equal(state.delivery.primary_commit,'4a1fc6777fe766dca2c0698362a06f06a44f9344');assert.equal(state.delivery.cloudflare.worker_version,'f46f5cdd-58f5-41cd-abee-cb5b41c2106d');assert.equal(state.unsettled.length,0);assert.equal(state.delivery.release_id,undefined);assert.equal(state.delivery.historical,true);assert.equal(state.site_delivery,null);assert.ok(state.checks.some(row=>row.issue===51));
 assert.ok(state.checks.some(r=>r.issue===6&&r.outcome==='deferred'));assert.ok(state.checks.some(r=>r.issue===845&&r.outcome==='verified'));
 assert.throws(()=>validateDelivery(state.delivery),'Historical normalization is not a new delivery/bootstrap certificate');
});
for(const kind of ['payload','result','new-id'])test('historical compatibility refuses '+kind+' drift',async()=>{
 const snapshot=structuredClone(historical),row=snapshot.deployments.find(r=>r.deployment.id===6850090217);
 if(kind==='payload')row.deployment.payload.worldatlas_cloudflare.issue=6;
 if(kind==='result')row.receipt.body+='\nChanged';
 if(kind==='new-id')row.deployment.id=12345;
 await assert.rejects(()=>readPublicationState(replay(snapshot)));
});
test('new operation cannot opt into a singular-issue legacy exception',()=>{
 const f=cloudflareFixture();delete f.op.issues;f.op.issue=849;assert.throws(()=>validateCloudflareOperation(f.deployment));
});
test('duplicate raw registry identities cannot be hidden by normalization',async()=>{
 const f=fixture();f.routes.set(root+'/deployments?per_page=100&page=1',[f.deployment,structuredClone(f.deployment)]);await assert.rejects(()=>readPublicationState(f.api),/duplicate complete operation inventory/);
});
test('altering the actually consumed historical inventory rejects at import with unchanged code pin',()=>{
 const tmp=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'atlas-history-drift-')));
 const original=new URL('../coordination/publication/cloudflare-history.json',import.meta.url),originalBytes=fs.readFileSync(original),originalHash=createHash('sha256').update(originalBytes).digest('hex');
 try{
  fs.mkdirSync(path.join(tmp,'scripts'));fs.mkdirSync(path.join(tmp,'coordination','publication'),{recursive:true});
  fs.writeFileSync(path.join(tmp,'scripts','publication-cloudflare.mjs'),fs.readFileSync(new URL('../scripts/publication-cloudflare.mjs',import.meta.url)),{flag:'wx'});
  const target=path.join(tmp,'coordination','publication','cloudflare-history.json');fs.writeFileSync(target,originalBytes,{flag:'wx'});
  const command=['--input-type=module','-e','await import(process.argv[1]);',path.join(tmp,'scripts','publication-cloudflare.mjs')];
  assert.equal(spawnSync(process.execPath,command,{encoding:'utf8'}).status,0);
  const changed=JSON.parse(originalBytes);changed.records[0].originating_issues=[51];fs.writeFileSync(target,JSON.stringify(changed));
  const result=spawnSync(process.execPath,command,{encoding:'utf8'});assert.equal(result.status,1);assert.match(result.stderr,/compatibility inventory changed/);
  assert.equal(createHash('sha256').update(fs.readFileSync(original)).digest('hex'),originalHash);
 }finally{fs.rmSync(tmp,{recursive:true});}
});
