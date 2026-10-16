// Task-only adapter invoking the unchanged accepted exact native kernel.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {fileURLToPath} from 'node:url';
const here=path.dirname(fileURLToPath(import.meta.url));
const sha=b=>createHash('sha256').update(b).digest('hex');
const need=(v,m)=>{if(!v)throw Error(m);};
const configPath=path.resolve(process.argv[2]),dest=path.resolve(process.argv[3]);
need(dest.startsWith(here+path.sep)&&!fs.existsSync(dest),'Fresh owned output required');
const configBody=fs.readFileSync(configPath),config=JSON.parse(configBody);
function read(pin){const b=fs.readFileSync(pin.path);need(b.length===pin.bytes&&sha(b)===pin.sha256,'Changed whole input: '+pin.path);return b;}
const moduleBody=fs.readFileSync(path.join(here,'accepted-native-grid.mjs'));
need(moduleBody.length===config.kernel.bytes&&sha(moduleBody)===config.kernel.sha256,'Accepted kernel drift');
const {witnessCellEffects,nativePolygonIntervals}=await import('./accepted-native-grid.mjs');
const requestBody=read(config.requests),requests=JSON.parse(requestBody).requests;
need(requests.length===501,'Original request scope changed');
const latitudeBody=gunzipSync(read(config.normative_latitudes));need(latitudeBody.length===config.normative_decoded_bytes&&sha(latitudeBody)===config.normative_decoded_sha256,'Normative latitude drift');
const size=config.grid_size,latitudes=Float64Array.from({length:size},(_,y)=>latitudeBody.readDoubleLE(y*8));
fs.mkdirSync(dest);const started=performance.now(),familyProducts=[];
function emit(name,value){const b=Buffer.from(JSON.stringify(value)+'\n');const temp=path.join(dest,name+'.partial');fs.writeFileSync(temp,b,{flag:'wx'});fs.renameSync(temp,path.join(dest,name));return {path:name,bytes:b.length,sha256:sha(b)};}
const requestPin=emit('original-requests.json',{requests,input:config.requests});
for(const family of config.families){
 const selected=requests.filter(r=>family.country==='IDN'||r.country===family.country),byCoordinate=new Map();
 for(const r of selected){const k=r.y+':'+r.x;byCoordinate.set(k,{y:r.y,x:r.x});}
 const rowsMap=new Map();for(const r of byCoordinate.values()){const a=rowsMap.get(r.y)??[];a.push(r.x);rowsMap.set(r.y,a);}
 const requestedRows=[...rowsMap].sort((a,b)=>a[0]-b[0]).map(([y,xs])=>({y,runs:xs.sort((a,b)=>a-b).map(x=>[x,x+1,1])}));
 const familyResult={family:family.key,input:family,requested_original_records:selected.length,distinct_native_query_centres:byCoordinate.size,requestedRows,variants:{},per_original_request:[]};
 const members={original:new Map(),full:new Map()};
 for(const variant of ['original','full']){
  const raw=read(family[variant]),collection=JSON.parse(raw);need(collection.type==='FeatureCollection'&&collection.features.length===family['actual_'+variant+'_features'],'Complete family changed');
  const featureResults=[];
  for(let i=0;i<collection.features.length;i++){
   const f=collection.features[i],id=family.key+':'+f.properties.shapeID;
   const effects=witnessCellEffects(f.geometry,{size,latitudes,requestedRows,nativePolygonIntervals});
   for(const hit of effects.hits){const k=hit.y+':'+hit.x;const arr=members[variant].get(k)??[];arr.push({source_id:id,feature_ordinal:i,shapeName:f.properties.shapeName,kind:hit.kind});members[variant].set(k,arr);}
   featureResults.push({source_id:id,feature_ordinal:i,properties:f.properties,geometry_sha256:sha(JSON.stringify(f.geometry)),effects});
  }
  familyResult.variants[variant]={whole_input:family[variant],crs:collection.crs??null,features:featureResults};
 }
 for(const r of selected){const k=r.y+':'+r.x;familyResult.per_original_request.push({original_request_id:r.id,y:r.y,x:r.x,original_memberships:members.original.get(k)??[],full_memberships:members.full.get(k)??[]});}
 const p=emit(family.key.replaceAll(':','-')+'.json',familyResult);familyProducts.push(p);
 console.log(JSON.stringify({event:'family-complete',family:family.key,product:p,original_requests:selected.length,distinct_centres:byCoordinate.size,elapsed_seconds:(performance.now()-started)/1000}));
}
const result={kind:config.kind,config_pin:{path:configPath,bytes:configBody.length,sha256:sha(configBody)},config,kernel:config.kernel,original_requests:requestPin,family_products:familyProducts,original_record_count:501,elapsed_seconds:(performance.now()-started)/1000,node_max_rss_kib:process.resourceUsage().maxRSS,limits:config.limits,authority_or_repair_credit:0,hold_or_owner_changes:false};
console.log(JSON.stringify({event:'complete',product:emit('result.json',result),elapsed_seconds:result.elapsed_seconds}));
