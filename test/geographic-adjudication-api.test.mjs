import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {gunzipSync} from 'node:zlib';
import {bindingHash} from '../scripts/geographic-adjudication-api.mjs';

test('source bindings match the actual shared Python canonical protocol', () => {
  const refs = [{source_id: 'native-water-水', path: 'coordination/sources/water.geojson.gz',
    sha256: 'a'.repeat(64), decoded_sha256: 'b'.repeat(64), native_geometry_sha256: 'c'.repeat(64),
    native_identity: {property: 'ne_id', value: 1159112991}, native_role: {property: 'featurecla', value: 'Lake'}}];
  const code = "import sys,json,hashlib;sys.path.insert(0,'scripts');from evidence.immutable import canonical_json;print(hashlib.sha256(canonical_json(json.load(sys.stdin))).hexdigest())";
  const result = spawnSync(process.env.PYTHON ?? 'python3', ['-I', '-B', '-c', code], {
    cwd: new URL('..', import.meta.url), input: JSON.stringify(refs), encoding: 'utf8'});
  assert.equal(result.status, 0, result.stderr);
  assert.equal(bindingHash(refs), result.stdout.trim());
});

// These are synthetic read-only GitHub responses. They exercise the real
// evidence/claim/review validators; physical geometry is checked separately.
import {collectGeographicApproval, METHOD, TARGET} from '../scripts/geographic-adjudication-api.mjs';
import {sha256, subjectsHash} from '../scripts/evidence-quality.mjs';
import {renderClaim} from '../scripts/issue-claim-contract.mjs';
const repo='owner/repo', head='b'.repeat(40), base='a'.repeat(40), branch='engineering/authority-fixture';
const packet='coordination/engineering/authority-fixture/', manifestPath=packet+'evidence-quality.json', dossierPath=packet+'dossier.json';
const sourcePath='coordination/engineering/retained-fixture/water.geojson';
const desc=(path,raw)=>({path,bytes:raw.length,sha256:sha256(raw),hash_kind:'file-bytes'});
function fixture({mutation=()=>{}, secondReview=null, changeClaim=false, changeContract=false, nativeControl=null}={}) {
 const sourceRaw=nativeControl ? Buffer.from(nativeControl.source_base64,'base64') : Buffer.from(JSON.stringify({type:'FeatureCollection',features:[{type:'Feature',properties:{native_id:1,kind:'Lake'},geometry:{type:'Polygon',coordinates:[[[-1,-1],[4,-1],[4,4],[-1,4],[-1,-1]]]}}]}));
 const retainedPath=nativeControl?.dossier.source_refs[0].path??sourcePath;
 const sourceFile={...desc(retainedPath,sourceRaw),...(nativeControl?{uncompressed_sha256:nativeControl.decoded_sha256,uncompressed_bytes:gunzipSync(sourceRaw).length}:{})}, source={id:'synthetic-native-water',url:'https://example.org/synthetic-transport-fixture',role:'physical-surface-water',vintage:'Synthetic fixture only',retrieved_at:'2026-10-05',license:{status:'redistributable',terms:'Synthetic test data'},retention:'retained',verification:'verified',temporal_status:'reference',files:[sourceFile]};
 const refs=nativeControl?.dossier.source_refs??[{source_id:source.id,path:sourcePath,sha256:sourceFile.sha256,decoded_sha256:sourceFile.sha256,native_identity:{property:'native_id',value:1},native_geometry_sha256:'d'.repeat(64),native_role:{property:'kind',value:'Lake'}}];
 const dossier=nativeControl?.dossier??{version:1,method_id:METHOD,target_context:TARGET,context:{},findings:[{sha256:'e'.repeat(64),feature:{type:'Feature',geometry:null,properties:{kind:'lost-previous-coverage'}}}],source_refs:refs,rationale:'Synthetic authority transport; no physical/factual approval.'};
 const decision={dossier_path:dossierPath,target_context:TARGET,target_water:'supported',physical_provenance:'accepted',temporal_suitability:'accepted',resolution_suitability:'accepted',target_uncertainty:'resolved-for-this-target',source_limits:['Synthetic transport fixture; geometry must pass separate validator.'],finding_sha256s:['e'.repeat(64)],source_refs_sha256:bindingHash(refs)};
 if(nativeControl) {source.id=refs[0].source_id;decision.finding_sha256s=dossier.findings.map(row=>row.sha256).sort();}
 const quality={version:1,manifest_path:'coordination/engineering/{job}/evidence-quality.json',subject_ids:[],pins:{},review_kind:'code'};
 const spec={max_prs:3,depends_on:[],mode:'engineering',scope:'Synthetic source-decision transport controls',evidence_quality:quality};
 const issue={number:920,state:'open',created_at:'2026-10-05T00:00:00Z',labels:['type:engineering','kind:work-item','status:ready'],body:`<!-- worldatlas-work:v1\n${JSON.stringify(spec)}\n-->`};
 const pr={number:32,state:'open',draft:false,merged:false,title:'Synthetic source transport',body:'Refs #920',changed_files:2,head:{sha:head,ref:branch,repo:{full_name:repo}},base:{sha:base,ref:'main'}};
 const claim={version:1,active:true,worker_id:'synthetic-author',claim_id:'synthetic-claim',branch,expires_at:'2030-01-01T00:00:00Z',mode:'engineering',max_prs:3};
 const baselineRaw=Buffer.from('Immutable synthetic code baseline\n');
 const manifest={version:1,issue:920,lane:'engineering',worker_id:claim.worker_id,subject_ids:[],subject_ids_sha256:subjectsHash([]),baseline:{commit:base,files:[desc('README.md',baselineRaw),{...sourceFile,role:'original-source'}],pins:{},pin_files:{},subject_files:{}},sources:[source],outputs:[],methods:[{id:'authority-transport',kind:'code',description:'Read-only synthetic authority transport controls',software:'Node24',units:'None; geometry is validated separately'}],metrics:[],summaries:[],conclusions:[],stages:{research:'partial',implementation:'proposed',geographic_approval:'not-requested'},commands:[],change_receipts:[{path:dossierPath,status:'added'},{path:manifestPath,status:'added'}],metric_bindings:[],validation:[],geographic_adjudications:[]};
 const receipt={version:1,pr_number:pr.number,head_sha:head,author_worker_id:claim.worker_id,reviewer_worker_id:'synthetic-reviewer',inspected_files:[dossierPath,manifestPath],outcome:'accepted',limits:[],domains:Object.fromEntries(['implementation','source','geometry'].map(name=>[name,{outcome:'accepted',scope:'Synthetic transport only; no actual source approval',limits:[]}]))};
 mutation({source,manifest,decision,dossier,receipt,issue,claim,pr});
 const dossierRaw=nativeControl?Buffer.from(nativeControl.dossier_base64,'base64'):Buffer.from(JSON.stringify(dossier));decision.dossier_sha256=sha256(dossierRaw);
 manifest.outputs=[desc(dossierPath,dossierRaw)];manifest.geographic_adjudications=[{path:dossierPath,sha256:sha256(dossierRaw)}];
 const manifestRaw=Buffer.from(JSON.stringify(manifest));receipt.manifest_sha256=sha256(manifestRaw);receipt.evidence_hashes=[...new Set([...manifest.baseline.files,...manifest.outputs,...manifest.sources.flatMap(row=>row.files??[])].map(row=>row.sha256))];receipt.geographic_adjudications={version:1,decisions:[decision]};
 const files=[{filename:dossierPath,status:'added'},{filename:manifestPath,status:'added'}];
 const candidate=new Map([['README.md',baselineRaw],[retainedPath,sourceRaw],[dossierPath,dossierRaw],[manifestPath,manifestRaw]]), baseline=new Map([['README.md',baselineRaw],[retainedPath,sourceRaw]]);
 const blobs=new Map(),tree=map=>({truncated:false,tree:[...map].map(([path,raw])=>{const oid=createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');blobs.set(oid,raw);return {path,sha:oid,size:raw.length,type:'blob',mode:'100644'};})});
 const candidateTree=tree(candidate),baseTree=tree(baseline);let reviewReads=0,claimReads=0,issueReads=0;
 const calls=[];
 const api=async(route,method='GET')=>{
  calls.push({route,method});assert.equal(method,'GET','source adapter must be read-only');
  const name=route.split('?')[0];
  if(name===`/repos/${repo}/pulls/32`) return structuredClone(pr);
  if(name===`/repos/${repo}/issues/920`) {const value=structuredClone(issue);if(changeContract&&++issueReads>1)value.body+=' changed';return value;}
  if(name===`/repos/${repo}/issues/920/comments`) {const value=structuredClone(claim);if(changeClaim&&++claimReads>1)value.claim_id='changed-claim';return [{id:1,user:{login:'github-actions[bot]'},body:renderClaim(value)}];}
  if(name===`/repos/${repo}/issues/920/timeline`) return [];
  if(name===`/repos/${repo}/pulls/32/files`) return files;
  if(name===`/repos/${repo}/issues/32/comments`) {let value=structuredClone(receipt);if(++reviewReads>1&&secondReview)secondReview(value);return [{id:600,author_association:'OWNER',body:`<!-- worldatlas-review:v1\n${JSON.stringify(value)}\n-->`}];}
  if(name===`/repos/${repo}/compare/${base}...${base}`) return {status:'identical'};
  if(name===`/repos/${repo}/git/commits/${base}`) return {tree:{sha:'1'.repeat(40)}};
  if(name===`/repos/${repo}/git/commits/${head}`) return {tree:{sha:'2'.repeat(40)}};
  if(name===`/repos/${repo}/git/trees/${'1'.repeat(40)}`) return baseTree;
  if(name===`/repos/${repo}/git/trees/${'2'.repeat(40)}`) return candidateTree;
  const oid=name.split('/git/blobs/')[1];if(oid&&blobs.has(oid))return {sha:oid,size:blobs.get(oid).length,encoding:'base64',content:blobs.get(oid).toString('base64')};
  throw Error(`Unexpected synthetic API route ${route}`);
 };
 return {api,calls,pr,manifest,receipt,dossier,decision,run:()=>collectGeographicApproval({api,repo,number:32,expectedHead:head})};
}

test('actual evidence/claim/review validators produce bounded read-only authority carrier',async()=>{
 const f=fixture(),result=await f.run();assert.equal(result.status,'reviewed');assert.equal(result.dossiers.length,1);
 assert.equal(result.authority_sha256,bindingHash(result.authority));assert.equal(result.review.comment_id,600);
 assert.equal(JSON.parse(Buffer.from(result.dossiers[0].bytes_base64,'base64')).rationale,f.dossier.rationale);
 assert.ok(f.calls.every(row=>row.method==='GET'));
});
for(const [name,options,pattern] of [
 ['self review',{mutation:({receipt,claim})=>receipt.reviewer_worker_id=claim.worker_id},/distinct worker/],
 ['stale reviewed head',{mutation:({receipt})=>receipt.head_sha='c'.repeat(40)},/Missing independent/],
 ['missing explicit source decisions',{secondReview:r=>delete r.geographic_adjudications},/explicit per-dossier/],
 ['target uncertainty',{mutation:({decision})=>decision.target_uncertainty='unknown'},/Unresolved/],
 ['target resolution',{mutation:({decision})=>decision.resolution_suitability='unknown'},/Unresolved/],
 ['political source role',{mutation:({source})=>source.role='political-country-outline'},/physical-water source/],
 ['wrong source reference digest',{mutation:({decision})=>decision.source_refs_sha256='0'.repeat(64)},/bindings differ/],
 ['revoked source decision after byte checks',{secondReview:r=>r.geographic_adjudications.decisions[0].target_water='unknown'},/Unresolved/],
 ['rejected review after byte checks',{secondReview:r=>r.outcome='changes-requested'},/unresolved independent rejection/],
 ['changed canonical claim during byte checks',{changeClaim:true},/reservation changed/],
 ['changed source contract during byte checks',{changeContract:true},/contract changed/],
]) test(`source authority rejects ${name}`,async()=>{await assert.rejects(fixture(options).run,pattern);});


test('actual Git CLI loss passes through real evidence validators and native whole-shape support',async()=>{
 const python=process.env.PYTHON??'python3';
 const prepare=spawnSync(python,['-I','-B','test/geographic-adjudication-pipeline.py','prepare'],{encoding:'utf8',timeout:120000,maxBuffer:8*1024*1024});
 assert.equal(prepare.status,0,prepare.stderr);const control=JSON.parse(prepare.stdout);
 try {
  const f=fixture({nativeControl:control});const envelope=await f.run();
  const validate=spawnSync(python,['-I','-B','test/geographic-adjudication-pipeline.py','validate'],{
   input:JSON.stringify({...control,envelope}),encoding:'utf8',timeout:120000,maxBuffer:8*1024*1024});
  assert.equal(validate.status,0,validate.stderr);const accepted=JSON.parse(validate.stdout);
  assert.equal(accepted.status,'all-findings-supported-and-reviewed');
  assert.equal(accepted.authority_sha256,envelope.authority_sha256);
  assert.equal(control.report.gate_status,'blocked','raw actual CLI lacked real hosted authority');
  assert.equal(control.report.status,'regressions-found');
  const wrapper=spawnSync(python,['-I','-B','test/geographic-adjudication-pipeline.py','wrapper'],{
   input:JSON.stringify({...control,envelope}),encoding:'utf8',timeout:120000,maxBuffer:8*1024*1024,
   env:{...process.env,PATH:path.dirname(process.execPath)+path.delimiter+process.env.PATH}});
  assert.equal(wrapper.status,0,wrapper.stderr);const job=JSON.parse(wrapper.stdout);
  assert.equal(job.gate_status,'passed');assert.equal(job.status,'regressions-found');
  assert.equal(job.adjudication.authority_sha256,envelope.authority_sha256);
  assert.equal(job.source_approval,false);assert.equal(job.candidate_code_executed,false);
  // Replacing the actual combined Git dossier after the API bytes were checked
  // is rejected by whole-file bindings, despite the valid authority carrier.
  const changed={...control,envelope,candidate:control.report.baseline_commit};
  const denied=spawnSync(python,['-I','-B','test/geographic-adjudication-pipeline.py','validate'],{
   input:JSON.stringify(changed),encoding:'utf8',timeout:120000,maxBuffer:8*1024*1024});
  assert.notEqual(denied.status,0);
 } finally {fs.rmSync(control.repo,{recursive:true,force:true});}
});

// Controlled trusted-job report transport isolates the late merge-authority
// boundary. This fixture does not certify its synthetic/null geometry as water.
import {completeIntegration} from '../scripts/merge-integration.mjs';
import {loadEvidencePolicy} from '../scripts/evidence-policy.mjs';
for(const change of ['none','withdraw','replace-limits']) test(`final merge rechecks actual latest source authority: ${change}`,async()=>{
 let changed=false;
 const f=fixture({secondReview:receipt=>{
  if(!changed)return;
  if(change==='withdraw')receipt.geographic_adjudications.decisions[0].target_water='unknown';
  if(change==='replace-limits')receipt.geographic_adjudications.decisions[0].source_limits.push('New limit after combined check');
 }});
 const approved=await f.run();changed=true;
 const candidate='c'.repeat(40),writes=[];
 const api=async(route,method='GET',body)=>{
  const name=route.split('?')[0];
  if(method==='PUT'){writes.push(body);return {merged:true,sha:'f'.repeat(40)};}
  if(name===`/repos/${repo}/git/ref/heads/main`)return {object:{sha:base}};
  if(name===`/repos/${repo}/commits/${head}/status`)return {statuses:[]};
  if(name===`/repos/${repo}/commits/${head}/check-runs`)return {check_runs:['scope','evidence'].map((name,index)=>({id:index+1,name,app:{id:1},status:'completed',conclusion:'success'}))};
  if(name===`/repos/${repo}/git/commits/${candidate}`)return {tree:{sha:'2'.repeat(40)},parents:[{sha:base},{sha:head}]};
  return f.api(route,method,body);
 };
 const report={version:1,method_id:'worldatlas-trusted-geography-check-v1',baseline_commit:base,
  trusted_code_commit:base,candidate_commit:candidate,candidate_code_executed:false,published:false,source_approval:false,
  gate_status:'passed',status:'regressions-found',regressions:1,adjudication:{
   status:'all-findings-supported-and-reviewed',authority_sha256:approved.authority_sha256,
   review:JSON.parse(JSON.stringify(approved.review,Object.keys(approved.review).sort())),
   finding_sha256s:approved.dossiers.flatMap(row=>row.decision.finding_sha256s).sort(),unresolved_findings:0}};
 const run=()=>completeIntegration({api,repo,number:32,expectedHead:head,policy:loadEvidencePolicy(),
  integrationResult:'success',geographyResult:'success',testedBase:base,testedCandidate:candidate,
  geographyReportLoader:async()=>report});
 if(change==='none'){assert.equal((await run()).accepted,true);assert.equal(writes.length,1);}
 else {await assert.rejects(run,change==='withdraw'?/Unresolved/:/source decision changed/);assert.equal(writes.length,0);}
});
