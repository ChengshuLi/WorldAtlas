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
