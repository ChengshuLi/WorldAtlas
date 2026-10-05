import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';

let loaderSerial=0;
const temporalPins={release_id:'reference:test',hierarchy_sha256:'a'.repeat(64),footprints_sha256:'b'.repeat(64)};
const temporalPage=(stream,year=2020,revision=7)=>({year,stream,...temporalPins,records:[],withdrawals:[],sources:[],next_cursor:null,revision,capability:{datedMembership:1,datedExistence:1,datedFootprints:0}});
async function withLoader(run,{enabled=true,geography=false}={}){
 const file=new URL('../src/data-client.js',import.meta.url);
 const source=fs.readFileSync(file,'utf8').replace(/from '(\.\/[^']+)'/g,(_,path)=>`from '${new URL(path,file).href}'`).replace("import.meta.env.VITE_STATIC_ATLAS === 'true'",'true').replace("import.meta.env.VITE_HOSTED_DATABASE === 'true'",'true')+`\n${enabled?'compactMapSupported=true;':''}\n${geography?`datedGeographySupported=true;expectedGeography=${JSON.stringify(temporalPins)};`:''}\nexport {loadHostedMapEvidence,loadReferenceAttributes,loadSelectedHostedMap,loadPreparedEvidence,loadHistory,loadOwnershipHistory};\n// isolated client fixture ${++loaderSerial}`;
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
function request(url){const parsed=new URL(url,'https://atlas.example');assert.equal(parsed.pathname,'/api/map/snapshot','compact reads must not download independent claim streams');assert.equal(parsed.searchParams.get('evidence_only'),'1');return parsed.searchParams;}
function unavailable(result,{stale=false,authority=false}={}){
 assert.equal(result.stale,stale);assert.equal(result.retirementAuthority,authority);
 for(const key of ['attributes','names','retirements']){assert.equal(result[key].available,false);if(!stale)assert.deepEqual(result[key].records,[]);}
}

test('reference presentation context is reused within one loaded generation and rebuilt on reload',async()=>withLoader(async loader=>{
 let generation=1,reads=0;
 global.fetch=async url=>{
  if(url==='./atlas-geography.json')return Response.json({units:[],features:[],preparedEvidence:{index_sha256:String(generation)},contentCapabilities:{}});
  if(url==='./reference-attributes/index.json'){reads++;return Response.json({version:2,parts:['part.json'],values:[generation===1?'Cfb':'Af'],types:[{attribute:'climate',valid_from:2026,valid_to:2027,method:'reference',status:'reference',source:'Immutable reference',metadata:{generation}}]});}
  assert.equal(url,'./reference-attributes/part.json');return Response.json([['location:A',[[0,0,1,1]]]]);
 };
 const first=await loader.loadReferenceAttributes(2020),next=await loader.loadReferenceAttributes(2021);
 assert.equal(first.referenceContexts,next.referenceContexts);assert.equal(reads,1);
 assert.equal(first.referenceContexts.get('location:A').climate.provenance.metadata.generation,1);
 generation=2;await loader.loadGeography();
 const changed=await loader.loadReferenceAttributes(2020);
 assert.notEqual(changed.referenceContexts,first.referenceContexts);assert.equal(reads,2);
 assert.equal(changed.referenceContexts.get('location:A').climate.provenance.metadata.generation,2);
 assert.equal(first.referenceContexts.get('location:A').climate.provenance.metadata.generation,1);
 const controller=new AbortController();controller.abort();
 await assert.rejects(loader.loadReferenceAttributes(2020,controller.signal),{name:'AbortError'});
}));

test('a pinned reference bundle preloads once and preserves legacy dated/reference separation',async()=>withLoader(async loader=>{
 const digest=bytes=>createHash('sha256').update(bytes).digest('hex');
 const index={version:2,footprints_sha256:temporalPins.footprints_sha256,parts:['original.json.gz'],values:['Cfb'],types:[{attribute:'climate',valid_from:2026,valid_to:2027,method:'reference',status:'reference',source:'Original reference',metadata:{normal_period:'1991-2020'}}]};
 const indexHash=digest(Buffer.from(JSON.stringify(index)));
 const raw=Buffer.from(JSON.stringify({version:1,index_sha256:indexHash,index,parts:[[['location:A',[[0,0,1,1]]]]]})),bytes=gzipSync(raw);
 const proof={version:1,path:'reference-attributes/startup-bundle.json.gz',bytes:bytes.length,sha256:digest(bytes),decoded_bytes:raw.length,decoded_sha256:digest(raw),index_sha256:indexHash,footprints_sha256:temporalPins.footprints_sha256,part_count:1};
 const calls=[];global.fetch=async url=>{
  calls.push(url);
  if(url==='./atlas-geography.json')return Response.json({units:[],features:[],reference_release:{id:temporalPins.release_id,...temporalPins},referenceAttributes:proof});
  assert.equal(url,'./reference-attributes/startup-bundle.json.gz');return new Response(bytes);
 };
 await loader.loadGeography();
 const historical=await loader.loadReferenceAttributes(2020),current=await loader.loadReferenceAttributes(2026);
 assert.deepEqual(historical.records,[]);assert.equal(historical.referenceContexts.get('location:A').climate.provenance.metadata.normal_period,'1991-2020');
 assert.equal(current.records[0].value,'Cfb');assert.equal(current.referenceContexts,historical.referenceContexts);
 assert.deepEqual(calls,['./atlas-geography.json','./reference-attributes/startup-bundle.json.gz']);
}));

test('a rejected old reference generation cannot clear a newer successful generation',async()=>withLoader(async loader=>{
 let rejectOld,reads=0;
 global.fetch=async url=>{
  if(url==='./atlas-geography.json')return Response.json({units:[],features:[]});
  if(url==='./reference-attributes/index.json'){
   reads++;if(reads===1)return new Promise((resolve,reject)=>{rejectOld=reject;});
   return Response.json({version:1,parts:['current.json']});
  }
  assert.equal(url,'./reference-attributes/current.json');return Response.json([]);
 };
 const failed=assert.rejects(loader.loadReferenceAttributes(2020),/old-generation-unavailable/);
 await loader.loadGeography();const current=await loader.loadReferenceAttributes(2020);
 rejectOld(Error('old-generation-unavailable'));await failed;
 const repeated=await loader.loadReferenceAttributes(2021);
 assert.equal(reads,2);assert.equal(repeated.referenceContexts,current.referenceContexts);
}));

test('complete entity and history reads start before the catalog finishes',async()=>withLoader(async loader=>{
 let finishCatalog;const calls=[];
 global.fetch=async url=>{
  calls.push(url);
  if(url==='./atlas-geography.json')return Response.json({units:[],parts:['catalog.json'],entityParts:['entities.json'],temporalHistoryParts:['history.json'],temporal:{}});
  if(url==='./catalog.json')return new Promise(resolve=>{finishCatalog=()=>resolve(Response.json([]));});
  assert.ok(['./entities.json','./history.json'].includes(url));return Response.json([]);
 };
 const pending=loader.loadGeography();await new Promise(setImmediate);
 assert.deepEqual(new Set(calls),new Set(['./atlas-geography.json','./catalog.json','./entities.json','./history.json']));
 finishCatalog();const result=await pending;
 assert.deepEqual(result.features,[]);assert.deepEqual(result.temporal,{entities:[],history:[]});
}));

test('ownership transport starts before catalog fan-out and geography waits for every stream',async()=>withLoader(async loader=>{
 const rows=Uint32Array.of(0,1,1,0),runs=Uint32Array.of(0,2,7,0);
 const pixelMap={version:1,size:2,runWords:4,parts:[{kind:'rows',path:'rows',offset:0,words:4},{kind:'runs',path:'runs',offset:0,words:4}]};
 const calls=[],release=new Map();let complete=false;
 global.fetch=async url=>{
  calls.push(url);
  if(url==='./atlas-geography.json')return Response.json({units:[],parts:['catalog'],pixelMap,entityParts:['entities'],temporalHistoryParts:['history'],temporal:{}});
  if(url==='./rows')return new Response(Buffer.from(rows.buffer));
  return new Promise(resolve=>release.set(url,()=>resolve(url==='./runs'?new Response(Buffer.from(runs.buffer)):Response.json([]))));
 };
 const pending=loader.loadGeography().then(value=>{complete=true;return value;});
 await new Promise(setImmediate);
 assert.ok(calls.indexOf('./rows')<calls.indexOf('./catalog'));
 assert.ok(calls.includes('./runs'));assert.equal(complete,false);
 for(const url of ['./entities','./history','./catalog'])release.get(url)();
 await new Promise(setImmediate);assert.equal(complete,false,'complete metadata cannot expose a map before ownership');
 release.get('./runs')();const result=await pending;
 assert.deepEqual(result.ownership.rows,rows);assert.deepEqual(result.ownership.runs,runs);
 assert.deepEqual(result.features,[]);assert.deepEqual(result.temporal,{entities:[],history:[]});
}));

test('unavailable bootstrap streams reject instead of returning a partial geography',async()=>{
 for(const missing of ['catalog','entities','history','rows','runs'])await withLoader(async loader=>{
  const rows=Uint32Array.of(0,1,1,0),runs=Uint32Array.of(0,2,7,0);
  global.fetch=async url=>{
   if(url==='./atlas-geography.json')return Response.json({units:[],parts:['catalog'],entityParts:['entities'],temporalHistoryParts:['history'],temporal:{},pixelMap:{version:1,size:2,runWords:4,parts:[{kind:'rows',path:'rows',offset:0,words:4},{kind:'runs',path:'runs',offset:0,words:4}]}});
   if(url===`./${missing}`)return new Response('',{status:503});
   if(url==='./rows'||url==='./runs')return new Response(Buffer.from((url==='./rows'?rows:runs).buffer));
   return Response.json([]);
  };
  await assert.rejects(loader.loadGeography(),/could not load|unavailable/i);
 });
});

test('older Workers negotiate the sparse limit without masking unrelated bad requests',async()=>withLoader(async loader=>{
 const limits=[];global.fetch=async url=>{const p=request(url),limit=Number(p.get('limit'));limits.push(limit);return limit>1000?Response.json({error:'Map entity page limit must be between 1 and 1000'},{status:400}):Response.json(validPage());};
 const result=await loader.loadHostedMapEvidence(2020,false);assert.deepEqual(limits,[4096,1000]);assert.equal(result.retirementAuthority,true);
 global.fetch=async()=>Response.json({error:'Invalid selected year'},{status:400});unavailable(await loader.loadHostedMapEvidence(2021,false));
}));

test('initial hosted evidence starts during geography and is consumed only once for its selection',async()=>withLoader(async loader=>{
 let completeEvidence;const calls=[];
 global.fetch=async url=>{
  if(url==='./atlas-history.json.gz')return Response.json({states:[],boundaries:[],attributes:[]});
  if(url==='./atlas-geography.json')return Response.json({units:[],features:[],contentCapabilities:{mapSnapshots:1}});
  const params=request(url);calls.push([params.get('year'),params.get('examples')]);
  if(calls.length===1)return new Promise(resolve=>{completeEvidence=()=>resolve(Response.json(validPage()));});
  return Response.json(validPage());
 };
 await loader.loadGeography({year:2020,examples:false});assert.deepEqual(calls,[['2020','0']]);
 let complete=false;const pending=loader.loadSelectedHostedMap(2020,false).then(value=>{complete=true;return value;});
 await new Promise(setImmediate);assert.equal(complete,false);assert.equal(calls.length,1);
 completeEvidence();const first=await pending;assert.equal(first.retirementAuthority,true);
 await loader.loadSelectedHostedMap(2020,false);assert.equal(calls.length,2,'later visits fetch fresh evidence');
}));

test('changing the initial year or examples cancels speculation and fetches the requested pair',async()=>{
 for(const next of [{year:2021,examples:false},{year:2020,examples:true}])await withLoader(async loader=>{
  let reads=0,aborted=false;
  global.fetch=async(url,{signal}={})=>{
   if(url==='./atlas-history.json.gz')return Response.json({states:[],boundaries:[],attributes:[]});
  if(url==='./atlas-geography.json')return Response.json({units:[],features:[],contentCapabilities:{mapSnapshots:1}});
   const params=request(url);reads++;
   if(reads===1)return new Promise((resolve,reject)=>signal.addEventListener('abort',()=>{aborted=true;reject(new DOMException('Canceled','AbortError'));},{once:true}));
   assert.equal(params.get('year'),String(next.year));assert.equal(params.get('examples'),String(Number(next.examples)));
   return Response.json(validPage({year:next.year}));
  };
  await loader.loadGeography({year:2020,examples:false});const result=await loader.loadSelectedHostedMap(next.year,next.examples);
  assert.equal(aborted,true);assert.equal(reads,2);assert.equal(result.retirementAuthority,true);
 });
});

test('a canceled initial selection does not poison a later retry',async()=>withLoader(async loader=>{
 let reads=0;
 global.fetch=async(url,{signal}={})=>{
  if(url==='./atlas-history.json.gz')return Response.json({states:[],boundaries:[],attributes:[]});
  if(url==='./atlas-geography.json')return Response.json({units:[],features:[],contentCapabilities:{mapSnapshots:1}});
  request(url);reads++;
  if(reads===1)return new Promise((resolve,reject)=>signal.addEventListener('abort',()=>reject(new DOMException('Canceled','AbortError')),{once:true}));
  return Response.json(validPage());
 };
 await loader.loadGeography({year:2020,examples:false});const controller=new AbortController();
 const canceled=loader.loadSelectedHostedMap(2020,false,controller.signal);controller.abort();
 await assert.rejects(canceled,{name:'AbortError'});
 assert.equal((await loader.loadSelectedHostedMap(2020,false)).retirementAuthority,true);assert.equal(reads,2);
}));

test('reloading geography discards old speculative evidence even when transport ignores cancellation',async()=>withLoader(async loader=>{
 let reads=0,finishOld;
 global.fetch=async url=>{
  if(url==='./atlas-history.json.gz')return Response.json({states:[],boundaries:[],attributes:[]});
  if(url==='./atlas-geography.json')return Response.json({units:[],features:[],contentCapabilities:{mapSnapshots:1}});
  request(url);reads++;
  if(reads===1)return new Promise(resolve=>{finishOld=()=>resolve(Response.json(validPage()));});
  return new Response('',{status:503});
 };
 await loader.loadGeography({year:2020,examples:false});await loader.loadGeography();finishOld();
 await new Promise(setImmediate);unavailable(await loader.loadSelectedHostedMap(2020,false));
}));

test('preloaded prepared evidence remains hash-pinned and a failed index can be retried',async()=>withLoader(async loader=>{
 const index={version:1,parts:[],sources:[],hierarchy_sha256:'a'.repeat(64),footprints_sha256:'b'.repeat(64)};
 const raw=Buffer.from(JSON.stringify(index)),proof={...index,index_sha256:createHash('sha256').update(raw).digest('hex')};
 let correct=false,reads=0;
 global.fetch=async url=>{
  if(url==='./atlas-geography.json')return Response.json({units:[],features:[],preparedEvidence:proof,contentCapabilities:{mapSnapshots:1}});
  if(url==='./prepared-evidence/index.json'){reads++;return new Response(correct?raw:Buffer.from(JSON.stringify({...index,hierarchy_sha256:'c'.repeat(64)})));}
  if(url==='./atlas-history.json.gz')return Response.json({states:[],boundaries:[],attributes:[]});
  request(url);return Response.json(validPage());
 };
 await loader.loadGeography({year:2020,examples:false});await new Promise(setImmediate);
 await assert.rejects(loader.loadPreparedEvidence(2020,false),/hash mismatch/);
 correct=true;assert.deepEqual(await loader.loadPreparedEvidence(2020,false),{records:[],names:[]});
 assert.ok(reads>=2);
}));

test('late failure of the old prepared index cannot clear the current loaded generation',async()=>withLoader(async loader=>{
 const index={version:1,parts:[],sources:[],hierarchy_sha256:'a'.repeat(64),footprints_sha256:'b'.repeat(64)},raw=Buffer.from(JSON.stringify(index));
 const proof={...index,index_sha256:createHash('sha256').update(raw).digest('hex')};let reads=0,finishOld;
 global.fetch=async url=>{
  if(url==='./atlas-geography.json')return Response.json({units:[],features:[],preparedEvidence:proof,contentCapabilities:{mapSnapshots:1}});
  if(url==='./prepared-evidence/index.json'){reads++;if(reads===1)return new Promise(resolve=>{finishOld=()=>resolve(new Response('',{status:503}));});return new Response(raw);}
  if(url==='./atlas-history.json.gz')return Response.json({states:[],boundaries:[],attributes:[]});
  request(url);return Response.json(validPage());
 };
 await loader.loadGeography({year:2020,examples:false});await loader.loadGeography({year:2020,examples:false});
 assert.deepEqual(await loader.loadPreparedEvidence(2020,false),{records:[],names:[]});
 finishOld();await new Promise(setImmediate);
 assert.deepEqual(await loader.loadPreparedEvidence(2020,false),{records:[],names:[]});assert.equal(reads,2);
}));

test('a superseded geography root cannot restart the previous initial selection',async()=>withLoader(async loader=>{
 let roots=0,finishOld,reads=0;
 const root={units:[],features:[],contentCapabilities:{mapSnapshots:1}};
 global.fetch=async url=>{
  if(url==='./atlas-geography.json'){roots++;if(roots===1)return new Promise(resolve=>{finishOld=()=>resolve(Response.json(root));});return Response.json(root);}
  if(url==='./atlas-history.json.gz')return Response.json({states:[],boundaries:[],attributes:[]});
  const params=request(url);assert.equal(params.get('year'),'2021');reads++;return Response.json(validPage({year:2021}));
 };
 const old=loader.loadGeography({year:2020,examples:false});await new Promise(setImmediate);
 await loader.loadGeography({year:2021,examples:false});finishOld();await assert.rejects(old,{name:'AbortError'});
 assert.equal((await loader.loadSelectedHostedMap(2021,false)).retirementAuthority,true);assert.equal(reads,1);
}));

test('history reloads with geography and an old failure cannot clear the current immutable read',async()=>withLoader(async loader=>{
 let reads=0,failOld;
 const current={states:[],boundaries:[],attributes:[]};
 global.fetch=async url=>{
  if(url==='./atlas-geography.json')return Response.json({units:[],features:[]});
  assert.equal(url,'./atlas-history.json.gz');reads++;
  if(reads===1)return new Promise(resolve=>{failOld=()=>resolve(new Response('',{status:503}));});
  return Response.json(current);
 };
 await loader.loadGeography();const old=loader.loadHistory();
 await loader.loadGeography();assert.deepEqual(await loader.loadHistory(),current);
 failOld();await assert.rejects(old,/unavailable/);
 assert.deepEqual(await loader.loadHistory(),current);assert.equal(reads,2);
}));

test('a pending complete snapshot cannot return across a geography reload',async()=>withLoader(async loader=>{
 let finishHistory;
 const index={version:1,parts:[],sources:[],hierarchy_sha256:'a'.repeat(64),footprints_sha256:'b'.repeat(64)};
 global.fetch=async url=>{
  if(url==='./atlas-geography.json')return Response.json({units:[],features:[],preparedEvidence:index,contentCapabilities:{mapSnapshots:1}});
  if(url==='./prepared-evidence/index.json')return Response.json(index);
  if(url==='./reference-attributes/index.json')return Response.json({version:2,parts:[],types:[],values:[]});
  if(url==='./ownership-runtime/index.json')return Response.json({version:1,encoding:'ownership-v2-century',shared:{version:2},buckets:[]});
  if(url==='./atlas-history.json.gz')return new Promise(resolve=>{finishHistory=()=>resolve(Response.json({states:[],boundaries:[],attributes:[]}));});
  request(url);return Response.json(validPage());
 };
 await loader.loadGeography();const pending=loader.loadSnapshot(2020,false);await new Promise(setImmediate);
 await loader.loadGeography();finishHistory();await assert.rejects(pending,{name:'AbortError'});
}));

test('ordinary pending hosted evidence cannot repopulate the cache after a geography reload',async()=>withLoader(async loader=>{
 let reads=0,finishOld;
 global.fetch=async url=>{
  if(url==='./atlas-geography.json')return Response.json({units:[],features:[],contentCapabilities:{mapSnapshots:1}});
  request(url);reads++;
  if(reads===1)return new Promise(resolve=>{finishOld=()=>resolve(Response.json(validPage()));});
  return new Response('',{status:503});
 };
 await loader.loadGeography();const old=loader.loadHostedMapEvidence(2020,false);
 await loader.loadGeography();finishOld();await assert.rejects(old,{name:'AbortError'});
 unavailable(await loader.loadHostedMapEvidence(2020,false));
}));

test('complete inline temporal streams use the existing pin and revision validator without extra HTTP reads',async()=>withLoader(async loader=>{
 let calls=0;global.fetch=async url=>{const p=request(url);assert.equal(p.get('include_temporal'),'1');calls++;return Response.json({...validPage(),temporal_geography:{records:temporalPage('records'),withdrawals:temporalPage('withdrawals')}});};
 const result=await loader.loadHostedMapEvidence(2020,false);assert.equal(calls,1);assert.equal(result.temporalGeography.complete,true);assert.equal(result.temporalGeography.revision,7);assert.equal(result.retirementAuthority,true);
},{geography:true}));

test('inline temporal revision or release drift restarts the scalar snapshot rather than repinning it',async()=>withLoader(async loader=>{
 let calls=0;global.fetch=async url=>{request(url);calls++;const records=temporalPage('records');if(calls===1)records.revision++;if(calls===2)records.hierarchy_sha256='c'.repeat(64);return Response.json({...validPage({stamp:':'+calls}),temporal_geography:{records,withdrawals:temporalPage('withdrawals')}});};
 const result=await loader.loadHostedMapEvidence(2020,false);assert.equal(calls,3);assert.equal(result.temporalGeography.revision,7);assert.ok(result.attributes.records.every(r=>r.id.endsWith(':3')));
},{geography:true}));

test('absent inline temporal pages retain bounded ordinary geography paging',async()=>withLoader(async loader=>{
 const calls=[];global.fetch=async url=>{const p=new URL(url,'https://atlas.invalid');calls.push(p.pathname);if(p.pathname==='/api/map/snapshot')return Response.json(validPage());assert.equal(p.pathname,'/api/geography/temporal/snapshot');return Response.json(temporalPage(p.searchParams.get('stream')));};
 const result=await loader.loadHostedMapEvidence(2020,false);assert.equal(calls.length,3);assert.equal(result.temporalGeography.complete,true);
},{geography:true}));

test('partial inline temporal pages cannot become authoritative or trigger unbounded reads',async()=>withLoader(async loader=>{
 let calls=0;global.fetch=async()=>{calls++;return Response.json({...validPage(),temporal_geography:{records:temporalPage('records'),withdrawals:{...temporalPage('withdrawals'),next_cursor:'unfinished'}}});};
 unavailable(await loader.loadHostedMapEvidence(2020,false));assert.equal(calls,1);
},{geography:true}));

test('compact client hydrates two atomic entity pages and retains shared source provenance',async()=>withLoader(async loader=>{
 const calls=[];global.fetch=async(url,options)=>{const params=request(url);calls.push(params);assert.equal(params.get('year'),'2020');assert.equal(params.get('examples'),'0');assert.equal(params.get('limit'),'4096');assert.equal(options.signal,undefined);return Response.json(params.has('cursor')?validPage({id:'location:B'}):validPage({next_cursor:'location:A'}));};
 const result=await loader.loadHostedMapEvidence(2020,false);assert.equal(calls.length,2);assert.equal(calls[1].get('cursor'),'location:A');assert.equal(result.retirementAuthority,true);
 for(const key of ['attributes','names','retirements']){assert.equal(result[key].available,true);assert.equal(result[key].revision,7);assert.equal(result[key].records.length,2);assert.equal(result[key].records[0].source,'Published historical source');assert.equal(result[key].records[0].source_metadata.sha256,'f'.repeat(64));}
 assert.deepEqual(result.attributes.records.map(r=>r.location_id),['location:A','location:B']);assert.equal(result.names.records[0].value,'Historical location:A');assert.equal(result.retirements.records[0].target_id,'prepared:location:A');
}));

test('oversized second page reduces its limit and retries its cursor without duplicating completed pages',async()=>withLoader(async loader=>{
 const calls=[];global.fetch=async url=>{const params=request(url);calls.push({cursor:params.get('cursor'),limit:Number(params.get('limit'))});if(!params.has('cursor'))return Response.json(validPage({next_cursor:'location:A'}));if(Number(params.get('limit'))>400)return Response.json({error:'Page too large',retryable:true,suggested_limit:400},{status:413});return Response.json(validPage({id:'location:B'}));};
 const result=await loader.loadHostedMapEvidence(2020,false);assert.deepEqual(calls,[{cursor:null,limit:4096},{cursor:'location:A',limit:4096},{cursor:'location:A',limit:400}]);assert.equal(result.attributes.available,true);assert.equal(result.attributes.records.length,2);assert.equal(new Set(result.attributes.records.map(r=>r.id)).size,2);
 global.fetch=async url=>{const params=request(url);return Number(params.get('limit'))>1?Response.json({error:'Too large',retryable:true,suggested_limit:1},{status:413}):Response.json({error:'Still too large',retryable:true,suggested_limit:1},{status:413});};
 unavailable(await loader.loadHostedMapEvidence(2021,false));
}));

test('a first-page size retry reaches the reduced request and preserves retirement authority',async()=>withLoader(async loader=>{
 const limits=[];global.fetch=async url=>{const params=request(url),limit=Number(params.get('limit'));limits.push(limit);assert.equal(params.has('cursor'),false);return limit>500?Response.json({error:'Too large',retryable:true},{status:413}):Response.json(validPage());};
 const result=await loader.loadHostedMapEvidence(2020,false);assert.deepEqual(limits,[4096,2048,1024,512,256]);assert.equal(result.attributes.records.length,1);assert.equal(result.attributes.revision,7);assert.equal(result.retirements.records[0].target_id,'prepared:location:A');assert.equal(result.retirementAuthority,true);
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

function ownershipFixture(generation){
 const index={version:1,encoding:'ownership-v2-century',source_index_sha256:`source-${generation}`,shared:{version:2,owner_ids:['owner:stable'],labels:[`Label ${generation}`],source_ids:[`source:${generation}`],statuses_order:['derived'],entities:{'owner:stable':{name:'Stable owner'}},source:`Source ${generation}`,source_url:'https://example.org/original'},buckets:[{path:'same-path.json',valid_from:1901,valid_to:2001}]};
 const bucket={version:1,source_index_sha256:index.source_index_sha256,valid_from:1901,valid_to:2001,parts:[[['location:A',[[1901,2001,0,0,0]]]]],evidence:[[0,1,1,[[0,1]],[0],0]]};
 return {index,bucket};
}

test('ownership index and same-path buckets reload with geography while nearby years reuse them',async()=>withLoader(async loader=>{
 let generation=1,indexReads=0,bucketReads=0;
 global.fetch=async url=>{
  if(url==='./atlas-geography.json')return Response.json({units:[],features:[]});
  const fixture=ownershipFixture(generation);
  if(url==='./ownership-runtime/index.json'){indexReads++;return Response.json(fixture.index);}
  assert.equal(url,'./ownership-runtime/same-path.json');bucketReads++;return Response.json(fixture.bucket);
 };
 await loader.loadGeography();
 const first=await loader.loadOwnershipHistory(1950);await loader.loadOwnershipHistory(1951);
 assert.equal(indexReads,1);assert.equal(bucketReads,1);assert.equal(first[0].value,'Label 1');
 generation=2;await loader.loadGeography();
 const next=await loader.loadOwnershipHistory(1950);await loader.loadOwnershipHistory(1951);
 assert.equal(indexReads,2);assert.equal(bucketReads,2);assert.equal(next[0].value,'Label 2');
 assert.equal(next[0].id,first[0].id);assert.equal(next[0].category_id,first[0].category_id);
 assert.deepEqual([next[0].valid_from,next[0].valid_to],[1901,2001]);
 assert.deepEqual(next[0].metadata.source_record_ids,['source:2']);assert.equal(first[0].value,'Label 1');
}));

for(const failingAsset of ['index','bucket'])test(`late old ownership ${failingAsset} failure cannot evict current generation`,async()=>withLoader(async loader=>{
 let generation=1,rejectOld,indexReads=0,bucketReads=0;
 global.fetch=async url=>{
  if(url==='./atlas-geography.json')return Response.json({units:[],features:[]});
  const fixture=ownershipFixture(generation);
  if(url==='./ownership-runtime/index.json'){
   indexReads++;if(generation===1&&failingAsset==='index')return new Promise((resolve,reject)=>{rejectOld=reject;});
   return Response.json(fixture.index);
  }
  assert.equal(url,'./ownership-runtime/same-path.json');bucketReads++;
  if(generation===1&&failingAsset==='bucket')return new Promise((resolve,reject)=>{rejectOld=reject;});
  return Response.json(fixture.bucket);
 };
 await loader.loadGeography();const old=assert.rejects(loader.loadOwnershipHistory(1950),/old-generation-unavailable/);await new Promise(setImmediate);
 generation=2;await loader.loadGeography();const current=await loader.loadOwnershipHistory(1950);
 const reads=[indexReads,bucketReads];rejectOld(Error('old-generation-unavailable'));await old;
 const repeated=await loader.loadOwnershipHistory(1951);
 assert.deepEqual([indexReads,bucketReads],reads);assert.equal(current[0].value,'Label 2');assert.equal(repeated[0].value,'Label 2');
}));
