import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
const code=process.env.CODE_ROOT ?? process.cwd(), gitRoot=process.env.REGRESSION_GIT_ROOT ?? '/workspace/scratch/127991fc8b8e/worldatlas-primary';
const output=process.env.ROUTE_OUTPUT ?? '/workspace/shared/worldatlas-recovery/checkpoint-prepared-route/before.json';
const {prepareIntegration}=await import(pathToFileURL(path.join(code,'scripts/merge-integration.mjs')));
const {selectedDataSelection}=await import(pathToFileURL(path.join(code,'scripts/integration-profile.mjs')));
const {renderClaim}=await import(pathToFileURL(path.join(code,'scripts/issue-claim-contract.mjs')));
const repo='ChengshuLi/WorldAtlas', base='2d1fc6f430e756498908bf2c4e267356a13f5cc7', head='4a99d16449e8901eb8ae1992b5cab33d4b9da128', candidate='c'.repeat(40);
const git=(...args)=>execFileSync('git',['--no-lazy-fetch','-C',gitRoot,...args],{env:{...process.env,GIT_NO_LAZY_FETCH:'1'},maxBuffer:128e6});
const tree=c=>{
 const local=git('ls-tree','-rz',c).toString().split('\0').filter(Boolean).map(line=>{const [meta,name]=line.split('\t'),[mode,type,sha]=meta.split(' ');return{path:name,mode,type,sha}});
 const api=JSON.parse(fs.readFileSync(path.join(path.dirname(output),'tree-'+c+'.json')));
 assert.equal(api.truncated,false);assert.equal(api.sha,git('rev-parse',c+'^{tree}').toString().trim());
 const entries=api.tree.filter(x=>x.type!=='tree'),byPath=new Map(entries.map(x=>[x.path,x]));assert.equal(local.length,entries.length);
 for(const row of local){const actual=byPath.get(row.path);for(const key of ['mode','type','sha'])assert.equal(actual?.[key],row[key],row.path+':'+key);assert(Number.isSafeInteger(actual.size),row.path);}
 return entries;
};
const baseline=tree(base), authored=tree(head), old=new Map(baseline.map(x=>[x.path,x]));
const overrides=new Map(), scenario=process.env.ROUTE_CASE??'unchanged';
const replace=(rows,name,bytes)=>{const row=rows.find(x=>x.path===name);assert(row,name);const sha=createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex');row.sha=sha;row.size=bytes.length;overrides.set(sha,bytes);};
const policyPath='.github/package-inputs.json';
if(['remove-unrelated','remove-shared','reorder','change-policy'].includes(scenario)){const row=authored.find(x=>x.path===policyPath),policy=JSON.parse(git('cat-file','blob',row.sha));
if(scenario==='remove-unrelated')policy.inputs=policy.inputs.filter(x=>x!=='data/administrative-sources.json');
if(scenario==='remove-shared')policy.inputs=policy.inputs.filter(x=>!x.endsWith('/owners.json.gz'));
if(scenario==='reorder')[policy.inputs[0],policy.inputs[1]]=[policy.inputs[1],policy.inputs[0]];
if(scenario==='change-policy')policy.verification_paths.push('package.json');
replace(authored,policyPath,Buffer.from(JSON.stringify(policy)+'\n'));}
if(scenario==='change-code'){const row=authored.find(x=>x.path==='src/native-grid.js');replace(authored,row.path,Buffer.concat([git('cat-file','blob',row.sha),Buffer.from('\n// Changed candidate execution code\n')]));}
if(scenario==='tamper-prior-sidecar'){const selection=JSON.parse(git('show',base+':data/ownership-selection.json'));replace(baseline,selection.additive_release.path,Buffer.from('{}\n'));}
if(scenario==='wrong-acceptance'){const row=authored.find(x=>x.path==='data/selected-checkpoint.json'),locator=JSON.parse(git('cat-file','blob',row.sha));locator.acceptance.head='0'.repeat(40);replace(authored,row.path,Buffer.from(JSON.stringify(locator)+'\n'));}
const files=authored.filter(x=>old.get(x.path)?.sha!==x.sha||old.get(x.path)?.mode!==x.mode).map(x=>({filename:x.path,status:old.has(x.path)?'modified':'added'}));
const branch='engineering/slovakia-selected-delivery-20261017', refs=new Map(), calls=[];
const raw=oid=>overrides.get(oid)??git('cat-file','blob',oid);
const cacheDir=path.join(path.dirname(output),'accepted-api');fs.mkdirSync(cacheDir,{recursive:true});
const api=async(route,method='GET',body)=>{
  const p=route.split('?')[0].replace('/repos/'+repo,'');calls.push({route,method});
  if(p==='/git/refs'&&method==='POST'){refs.set(body.ref.replace('refs/heads/',''),body.sha);return{ref:body.ref};}
  if(p==='/merges'&&method==='POST'){if(body.base==='main')throw Error('No external write allowed');refs.set(body.base,candidate);return{sha:candidate};}
  if(/\/git\/refs?\/heads\/worldatlas-integration\//.test(p)){const ref=p.split(/\/git\/refs?\/heads\//)[1];if(method==='DELETE'){refs.delete(ref);return null;}return{object:{sha:refs.get(ref)}};}
  if(method!=='GET')throw Error('Unrecognized mutation refused: '+method+' '+route);
  if(p==='/pulls/999999')return{number:999999,state:'open',draft:false,body:'Closes #999998',title:'Exact retained Slovakia delivery fixture',changed_files:files.length,head:{sha:head,ref:branch,repo:{full_name:repo}},base:{ref:'main',sha:base},mergeable:true};
  if(p==='/issues/999998')return{number:999998,state:'open',created_at:'2026-10-03T00:00:00Z',labels:['type:engineering','kind:work-item','status:ready'],body:'<!-- worldatlas-work:v1\n'+JSON.stringify({mode:'engineering',max_prs:3,depends_on:[],scope:'code'})+'\n-->'};
  if(p==='/issues/999998/comments')return[{id:1,user:{login:'github-actions[bot]'},body:renderClaim({version:1,active:true,worker_id:'regression',claim_id:'nonce',branch,expires_at:'2030-01-01T00:00:00Z'})}];
  if(p==='/issues/999998/timeline')return[];
  if(p==='/pulls/999999/files'){const page=Number(new URL('https://fixture.invalid'+route).searchParams.get('page')||1);return files.slice((page-1)*100,page*100);}
  if(p==='/commits/'+head+'/check-runs')return{check_runs:[{id:1,name:'scope',app:{id:1},status:'completed',conclusion:'success'}]};
  if(p==='/commits/'+head+'/status')return{statuses:[]};
  if(p==='/git/ref/heads/main')return{object:{sha:base}};
  if(p==='/git/commits/'+base)return{sha:base,tree:{sha:'baseline'}};
  if(p==='/git/commits/'+head)return{sha:head,tree:{sha:'authored'}};
  if(p==='/git/commits/'+candidate)return{sha:candidate,tree:{sha:'integrated'},parents:[{sha:base},{sha:head}]};
  if(p==='/git/trees/baseline')return{truncated:false,tree:baseline};
  if(p==='/git/trees/authored'||p==='/git/trees/integrated')return{truncated:false,tree:authored};
  if(p.startsWith('/git/blobs/')){const sha=p.split('/').at(-1),bytes=raw(sha);return{sha,size:bytes.length,encoding:'base64',content:bytes.toString('base64')};}
  if(p==='/contents/.github/package-inputs.json'){assert.equal(new URL('https://fixture.invalid'+route).searchParams.get('ref'),candidate);const entry=authored.find(x=>x.path==='.github/package-inputs.json'),bytes=raw(entry.sha);return{type:'file',path:entry.path,sha:entry.sha,size:bytes.length,encoding:'base64',content:bytes.toString('base64')};}
  // Only authentic accepted-checkpoint read routes may reach GitHub. All queue
  // writes above are in-memory fixture operations, never public mutations.
  if(!/^\/repos\/ChengshuLi\/WorldAtlas\/(issues\/2431\/comments|pulls\/2431(?:\?|$)|git\/commits\/[a-f0-9]{40}(?:\?|$))/.test(route))throw Error('Unexpected read route '+route);
  const filename=path.join(cacheDir,Buffer.from(route).toString('hex')+'.json');
  if(!fs.existsSync(filename))fs.writeFileSync(filename,execFileSync('gh',['api',route],{maxBuffer:16e6}));
  return JSON.parse(fs.readFileSync(filename));
};
const metadataDiagnostics={};
const selected=await selectedDataSelection({api,repo,branch,files,baseline:{entries:new Map(baseline.map(x=>[x.path,x]))},authored:{entries:new Map(authored.map(x=>[x.path,x]))},metadataDiagnostics});
const options={api,repo,number:999999,expectedHead:head,policy:{version:1,mode:'enforce-new',activation_time:'2100-01-01T00:00:00Z'},integrationRequestId:'exact-slovakia-retirement-regression',evidenceCheck:async()=>{throw Error('Removed evidence traversal reached')}};
const prepared=await prepareIntegration(options);
if(process.env.EXPECT_SELECTED==='1'){assert.equal(selected?.test_selection,'selected-data',JSON.stringify(metadataDiagnostics));assert.equal(prepared.test_selection,'selected-data');assert.equal(prepared.geography_software,false);const repeated=await prepareIntegration(options);assert.equal(repeated.test_selection,prepared.test_selection);assert.equal(repeated.geography_software,false);}
if(process.env.EXPECT_SELECTED==='0'){assert.equal(selected,null);assert.notEqual(prepared.test_selection,'selected-data');assert.equal(prepared.geography_software,true);}
const executing_code=Object.fromEntries(['scripts/package-inputs.mjs','scripts/integration-profile.mjs','scripts/merge-integration.mjs'].map(name=>[name,createHash('sha256').update(fs.readFileSync(path.join(code,name))).digest('hex')]));
const result={scenario,executing_code,base,head,synthetic_candidate:candidate,files:files.length,selected,metadataDiagnostics,prepared:{profile:prepared.profile,test_selection:prepared.test_selection??null,geography_software:prepared.geography_software,geography_required:prepared.geography_required,shards:prepared.shards??null},read_calls:calls.filter(x=>x.method==='GET').length,fixture_mutations:calls.filter(x=>x.method!=='GET')};
fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
