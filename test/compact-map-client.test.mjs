import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

let loaderSerial=0;
async function withLoader(run,{enabled=true}={}){
 const file=new URL('../src/data-client.js',import.meta.url);
 const source=fs.readFileSync(file,'utf8').replace(/from '(\.\/[^']+)'/g,(_,path)=>`from '${new URL(path,file).href}'`).replace("import.meta.env.VITE_STATIC_ATLAS === 'true'",'true').replace("import.meta.env.VITE_HOSTED_DATABASE === 'true'",'true')+`\n${enabled?'compactMapSupported=true;':''}\nexport {loadHostedMapEvidence};\n// isolated client fixture ${++loaderSerial}`;
 const loader=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64')),previous=global.fetch;
 try{return await run(loader);}finally{global.fetch=previous;}
}
function validPage({id='location:A',year=2020,revision=7,next_cursor=null,stamp=''}={}){
 const source={id:'source:test',name:'Published historical source',url:'https://example.org/census',license:'CC0',vintage:'2020',supported_from:-3000,supported_to:2027,status:'historical',metadata:{sha256:'f'.repeat(64),precision:'census observation'}};
 return {year,revision,next_cursor,entities:[{id,kind:'location'}],sources:{[source.id]:source},aliases_truncated:[],
  records:[{id:`claim:${id}${stamp}`,location_id:id,attribute:'population',value:42,category_id:null,valid_from:year,valid_to:year+1,source_id:source.id,method:'direct',status:'sourced',is_example:0,metadata:{observation:'original census'}}],
  names:[{id:`name:${id}${stamp}`,entity_id:id,name:`Historical ${id}`,language:'en',role:'preferred',field:'name',value:`Historical ${id}`,name_role:'preferred',valid_from:year,valid_to:year+1,source_id:source.id,is_example:0,metadata:{attested:true}}],
  retirements:[{id:`retirement:${id}${stamp}`,collection:'records',target_id:`prepared:${id}`,source_id:source.id,reason:'Source correction',replacement_id:null,metadata:{review:'retained'}}]};
}
function request(url){const parsed=new URL(url,'https://atlas.example');assert.equal(parsed.pathname,'/api/map/snapshot','compact reads must not download independent claim streams');return parsed.searchParams;}
function unavailable(result,{stale=false,authority=false}={}){
 assert.equal(result.stale,stale);assert.equal(result.retirementAuthority,authority);
 for(const key of ['attributes','names','retirements']){assert.equal(result[key].available,false);if(!stale)assert.deepEqual(result[key].records,[]);}
}

test('compact client hydrates two atomic entity pages and retains shared source provenance',async()=>withLoader(async loader=>{
 const calls=[];global.fetch=async(url,options)=>{const params=request(url);calls.push(params);assert.equal(params.get('year'),'2020');assert.equal(params.get('examples'),'0');assert.equal(params.get('limit'),'1000');assert.equal(options.signal,undefined);return Response.json(params.has('cursor')?validPage({id:'location:B'}):validPage({next_cursor:'location:A'}));};
 const result=await loader.loadHostedMapEvidence(2020,false);assert.equal(calls.length,2);assert.equal(calls[1].get('cursor'),'location:A');assert.equal(result.retirementAuthority,true);
 for(const key of ['attributes','names','retirements']){assert.equal(result[key].available,true);assert.equal(result[key].revision,7);assert.equal(result[key].records.length,2);assert.equal(result[key].records[0].source,'Published historical source');assert.equal(result[key].records[0].source_metadata.sha256,'f'.repeat(64));}
 assert.deepEqual(result.attributes.records.map(r=>r.location_id),['location:A','location:B']);assert.equal(result.names.records[0].value,'Historical location:A');assert.equal(result.retirements.records[0].target_id,'prepared:location:A');
}));

test('oversized second page reduces its limit and retries its cursor without duplicating completed pages',async()=>withLoader(async loader=>{
 const calls=[];global.fetch=async url=>{const params=request(url);calls.push({cursor:params.get('cursor'),limit:Number(params.get('limit'))});if(!params.has('cursor'))return Response.json(validPage({next_cursor:'location:A'}));if(Number(params.get('limit'))>400)return Response.json({error:'Page too large',retryable:true,suggested_limit:400},{status:413});return Response.json(validPage({id:'location:B'}));};
 const result=await loader.loadHostedMapEvidence(2020,false);assert.deepEqual(calls,[{cursor:null,limit:1000},{cursor:'location:A',limit:1000},{cursor:'location:A',limit:400}]);assert.equal(result.attributes.available,true);assert.equal(result.attributes.records.length,2);assert.equal(new Set(result.attributes.records.map(r=>r.id)).size,2);
 global.fetch=async url=>{const params=request(url);return Number(params.get('limit'))>1?Response.json({error:'Too large',retryable:true,suggested_limit:1},{status:413}):Response.json({error:'Still too large',retryable:true,suggested_limit:1},{status:413});};
 unavailable(await loader.loadHostedMapEvidence(2021,false));
}));

test('a first-page size retry reaches the reduced request and preserves retirement authority',async()=>withLoader(async loader=>{
 const limits=[];global.fetch=async url=>{const params=request(url),limit=Number(params.get('limit'));limits.push(limit);assert.equal(params.has('cursor'),false);return limit>500?Response.json({error:'Too large',retryable:true},{status:413}):Response.json(validPage());};
 const result=await loader.loadHostedMapEvidence(2020,false);assert.deepEqual(limits,[1000,500]);assert.equal(result.attributes.records.length,1);assert.equal(result.attributes.revision,7);assert.equal(result.retirements.records[0].target_id,'prepared:location:A');assert.equal(result.retirementAuthority,true);
}));

test('retryable conflicts and cross-page revision changes restart the complete compact snapshot',async()=>withLoader(async loader=>{
 let attempt=0;const calls=[];
 global.fetch=async url=>{const params=request(url),cursor=params.get('cursor');calls.push(cursor);if(!cursor){attempt++;return Response.json(validPage({revision:attempt,next_cursor:'location:A',stamp:`:${attempt}`}));}if(attempt===1)return Response.json({error:'Concurrent import',retryable:true},{status:409});if(attempt===2)return Response.json(validPage({id:'location:B',revision:99,stamp:':invalid'}));return Response.json(validPage({id:'location:B',revision:attempt,stamp:`:${attempt}`}));};
 const result=await loader.loadHostedMapEvidence(2020,false);assert.deepEqual(calls,[null,'location:A',null,'location:A',null,'location:A']);assert.equal(result.retirementAuthority,true);
 for(const key of ['attributes','names','retirements']){assert.equal(result[key].revision,3);assert.equal(result[key].records.length,2);assert.ok(result[key].records.every(r=>r.id.endsWith(':3')),'claims from rejected revisions never leak into the completed read');}
}));

test('three persistently inconsistent attempts produce unavailable evidence without cold-cache authority',async()=>withLoader(async loader=>{
 let calls=0;global.fetch=async url=>{const params=request(url);calls++;return Response.json(validPage({id:params.has('cursor')?'location:B':'location:A',revision:params.has('cursor')?2:1,next_cursor:params.has('cursor')?null:'location:A'}));};
 const result=await loader.loadHostedMapEvidence(2020,false);assert.equal(calls,6);assert.equal(result.unstable,true);unavailable(result);
}));

test('warm failures retain claims and withdrawals atomically only for the same year and example setting',async()=>withLoader(async loader=>{
 global.fetch=async url=>{request(url);return Response.json(validPage());};const complete=await loader.loadHostedMapEvidence(2020,false);
 let calls=0;global.fetch=async url=>{const params=request(url);calls++;return params.has('cursor')?Response.json({error:'Database unavailable'},{status:503}):Response.json(validPage({revision:8,next_cursor:'location:A',stamp:':partial',year:Number(params.get('year'))}));};
 const stale=await loader.loadHostedMapEvidence(2020,false);unavailable(stale,{stale:true,authority:true});assert.equal(stale.cached_revision,7);
 for(const key of ['attributes','names','retirements']){assert.deepEqual(stale[key].records,complete[key].records);assert.equal(stale[key].revision,7);}
 assert.equal(calls,2);for(const [year,examples]of [[2021,false],[2020,true]])unavailable(await loader.loadHostedMapEvidence(year,examples));
 global.fetch=async url=>{request(url);return Response.json(validPage({revision:9,stamp:':recovered'}));};const recovered=await loader.loadHostedMapEvidence(2020,false);assert.equal(recovered.attributes.available,true);assert.equal(recovered.attributes.revision,9);assert.equal(recovered.retirements.records[0].id,'retirement:location:A:recovered');
}));

test('malformed compact pages, incorrect years and cursor cycles fail atomically',async()=>{
 for(const mutate of [p=>({...p,year:2021}),p=>({...p,sources:{}}),p=>({...p,records:[...p.records,p.records[0]]}),p=>({...p,aliases_truncated:null}),p=>({...p,next_cursor:12})])await withLoader(async loader=>{global.fetch=async url=>{request(url);return Response.json(mutate(validPage()));};unavailable(await loader.loadHostedMapEvidence(2020,false));});
 await withLoader(async loader=>{let calls=0;global.fetch=async url=>{const params=request(url);calls++;return Response.json(validPage({id:params.has('cursor')?'location:B':'location:A',next_cursor:'location:A'}));};unavailable(await loader.loadHostedMapEvidence(2020,false));assert.equal(calls,2,'a repeated cursor cannot loop or publish partial data');});
});

test('compact client propagates aborts and passes the signal to its network request',async()=>withLoader(async loader=>{
 const early=new AbortController();early.abort();global.fetch=()=>{throw Error('Already-aborted reads must not reach the network');};await assert.rejects(loader.loadHostedMapEvidence(2020,false,early.signal),error=>error.name==='AbortError');
 const during=new AbortController();global.fetch=async(url,options)=>{request(url);assert.equal(options.signal,during.signal);during.abort();throw during.signal.reason;};await assert.rejects(loader.loadHostedMapEvidence(2020,false,during.signal),error=>error.name==='AbortError');
}));

test('clients without a compact capability keep the original three-stream protocol',async()=>withLoader(async loader=>{
 const calls=[];global.fetch=async url=>{calls.push(new URL(url,'https://atlas.example').pathname);return Response.json({records:[],next_cursor:null,revision:4});};const result=await loader.loadHostedMapEvidence(2020,false);assert.deepEqual(calls.sort(),['/api/attributes','/api/names','/api/retirements']);assert.equal(result.attributes.available,true);assert.equal(result.retirementAuthority,true);
},{enabled:false}));

test('the geography capability enables compact reads through the actual manifest loader',async()=>withLoader(async loader=>{
 const calls=[];global.fetch=async url=>{calls.push(url);if(url==='./atlas-geography.json')return Response.json({units:[],features:[],contentCapabilities:{mapSnapshots:1}});request(url);return Response.json(validPage());};
 await loader.loadGeography();const result=await loader.loadHostedMapEvidence(2020,false);assert.equal(calls[0],'./atlas-geography.json');assert.equal(calls.length,2);assert.match(calls[1],/^\/api\/map\/snapshot\?/);assert.equal(result.attributes.available,true);
},{enabled:false}));
