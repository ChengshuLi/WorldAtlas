import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

test('a failed evidence stream cannot mix live claims with an absent retirement snapshot',async()=>{
 const file=new URL('../src/data-client.js',import.meta.url);
 const source=fs.readFileSync(file,'utf8').replace(/from '(\.\/[^']+)'/g,(_,path)=>`from '${new URL(path,file).href}'`).replace("import.meta.env.VITE_STATIC_ATLAS === 'true'",'true').replace("import.meta.env.VITE_HOSTED_DATABASE === 'true'",'true')+'\nexport {loadHostedMapEvidence};';
 const loader=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64')),previous=global.fetch;
 try{
  for(const failed of ['/api/attributes','/api/names','/api/retirements']){
   global.fetch=async url=>url.startsWith(failed)?Response.json({error:'Temporary database failure'},{status:503}):Response.json({records:[{id:`live:${url.split('?')[0]}`}],next_cursor:null,revision:7});
   const result=await loader.loadHostedMapEvidence(2020,false);
   for(const collection of ['attributes','names','retirements']){
    assert.equal(result[collection].available,false,`${failed} failure must invalidate the whole hosted read`);
    assert.deepEqual(result[collection].records,[],`${failed} failure must not expose partial live ${collection}`);
   }
  }
  let calls=0;
  global.fetch=async url=>{
   const request=calls++;
   if(request<3)return Response.json({records:[],next_cursor:null,revision:request===1?2:1});
   return url.startsWith('/api/retirements')?Response.json({error:'Temporary retirement failure'},{status:503}):Response.json({records:[{id:'after-retry'}],next_cursor:null,revision:3});
  };
  const retried=await loader.loadHostedMapEvidence(2020,false);
  assert.ok(calls>=6,'mixed revisions must retry every stream');
  for(const collection of ['attributes','names','retirements']){assert.equal(retried[collection].available,false);assert.deepEqual(retried[collection].records,[]);}
  global.fetch=async url=>Response.json({records:[{id:`complete:${url.split('?')[0]}`}],next_cursor:null,revision:11});
  const complete=await loader.loadHostedMapEvidence(2020,false);
  for(const collection of ['attributes','names','retirements'])assert.equal(complete[collection].available,true);
  global.fetch=async url=>url.startsWith('/api/retirements')?Response.json({error:'Temporary retirement failure'},{status:503}):Response.json({records:[{id:'partial:new-live-claim'}],next_cursor:null,revision:12});
  const stale=await loader.loadHostedMapEvidence(2020,false);
  for(const collection of ['attributes','names','retirements']){
   assert.equal(stale[collection].available,false);
   assert.deepEqual(stale[collection].records,complete[collection].records,'a cached snapshot keeps prior claims and retirements atomically');
   assert.equal(stale[collection].revision,11,'cached snapshot must not claim the partial live revision');
  }
  for(const [year,examples]of [[2021,false],[2020,true]]){
   const unmatched=await loader.loadHostedMapEvidence(year,examples);
   for(const collection of ['attributes','names','retirements']){assert.equal(unmatched[collection].available,false);assert.deepEqual(unmatched[collection].records,[],'a different date/example setting cannot reuse the cached snapshot');}
  }
 }finally{global.fetch=previous;}
});

test('dated geography shares scalar revision and complete same-year cache authority',async()=>{
 const file=new URL('../src/data-client.js',import.meta.url),pins={release_id:'release',hierarchy_sha256:'a'.repeat(64),footprints_sha256:'b'.repeat(64)};
 const source=fs.readFileSync(file,'utf8').replace(/from '(\.\/[^']+)'/g,(_,path)=>`from '${new URL(path,file).href}'`).replace("import.meta.env.VITE_STATIC_ATLAS === 'true'",'true').replace("import.meta.env.VITE_HOSTED_DATABASE === 'true'",'true')+`\nexport {loadHostedMapEvidence}; datedGeographySupported=true; expectedGeography=${JSON.stringify(pins)};`;
 const loader=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64')),previous=global.fetch;
 const evidence={id:'source',name:'Synthetic test',url:'https://example.test',license:'CC0',vintage:'1000',status:'historical',supported_from:-3000,supported_to:2027,metadata:{test_only:true}};
 let revision=10,fail=false,drift=false,scalarCalls=0;
 global.fetch=async input=>{
  const url=new URL(input,'https://atlas.test'),year=Number(url.searchParams.get('year'));
  if(!url.pathname.includes('/temporal/')){scalarCalls++;return Response.json({records:[],next_cursor:null,revision});}
  if(fail)return Response.json({error:'Unavailable'},{status:503});
  const stream=url.searchParams.get('stream'),claim={id:'parent',entity_id:'location',collection:'memberships',parent_id:'province:b',valid_from:1000,valid_to:1100,source_id:evidence.id,method:'direct',status:'sourced',is_example:0,release_id:pins.release_id,validation_id:'validation',metadata:{},reference_parent_id:'province:a',reference_active:1,entity_kind:'location',entity_valid_from:null,entity_valid_to:null,effective_parent_id:'province:b',parent_context:'historical',membership_status:'dated'};
  return Response.json({year,stream,...pins,revision:revision+Number(drift),records:stream==='records'?[claim]:[],withdrawals:[],sources:stream==='records'?[evidence]:[],next_cursor:null,capability:{datedMembership:1,datedExistence:1,datedFootprints:0}});
 };
 try{
  const complete=await loader.loadHostedMapEvidence(1000,false);assert.equal(complete.temporalGeography.complete,true);assert.equal(complete.temporalGeography.revision,10);
  revision=11;fail=true;const stale=await loader.loadHostedMapEvidence(1000,false);assert.equal(stale.stale,true);assert.equal(stale.cached_revision,10);assert.deepEqual(stale.temporalGeography,complete.temporalGeography);
  const cold=await loader.loadHostedMapEvidence(1001,false);assert.equal(cold.retirementAuthority,false);assert.equal(cold.temporalGeography,null);
  fail=false;drift=true;const before=scalarCalls,changed=await loader.loadHostedMapEvidence(1001,false);assert.equal(changed.unstable,true);assert.equal(changed.temporalGeography,null);assert.equal(scalarCalls-before,9,'Revision drift reloads all three scalar streams for each bounded attempt');
 }finally{global.fetch=previous;}
});
