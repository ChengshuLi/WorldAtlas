import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {nativeRuntimeIndex,nativePolygonIntervals,NATIVE_GRID_METHOD} from './inputs/accepted89ff/src/native-grid.js';
// Separate necessary source comparison; no historical allocation/deadline policy.
const base='bulk-completion/vn-lao-khm178/',start=performance.now();
const sha=b=>createHash('sha256').update(b).digest('hex');
const pins=JSON.parse(fs.readFileSync(base+'vnm-current-map-input-pins.json'));
const read=p=>{const pin=pins.find(x=>x.path===p),raw=fs.readFileSync(p);if(!pin||raw.length!==pin.bytes||sha(raw)!==pin.sha256)throw Error('Input custody differs '+p);return raw;};
const scope=JSON.parse(read(base+'exact178-original-scope.json'));
const identity=JSON.parse(read(base+'inputs/existing345-native-locations.json'));
const locs=new Map(identity.locations.map(x=>[x.id,x]));
const latPath='vietnam-next/repair-package/reference1588/cell-hold-audit/tanbien26-readiness/inputs/native-latitudes.f64le.gz';
const raw=gunzipSync(read(latPath));
if(sha(raw)!=='66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23')throw Error('Original latitudes differ');
const size=262166,latitudes=Float64Array.from({length:size},(_,i)=>raw.readDoubleLE(i*8));
const ys=[...new Set(scope.records.map(p=>p.original_key.y))].sort((a,b)=>a-b),runs=[];
for(const y of ys){const last=runs.at(-1);if(last&&last[1]===y)last[1]++;else runs.push([y,y+1]);}
const summaries=[];
for(const [kind,file] of [['new-vnm-cod-adm0','vnm_admin0.geojson'],['current89ff-foreign8-map','current89ff-foreign8-geography-subset.json']]){
 const family=JSON.parse(read(base+'inputs/'+file));
 const entries=family.features.map((f,i)=>{
  const id=kind==='new-vnm-cod-adm0'?'cod:VNM:ADM0:VN':f.properties.id,loc=locs.get(id);
  if(kind!=='new-vnm-cod-adm0'&&!loc)throw Error('No exact existing current map ID');
  return {id,pixelIndex:loc?.index??i+1,geometry:f.geometry,properties:f.properties};
 });
 const idx=nativeRuntimeIndex(entries),lookup=new Map(entries.map(e=>[e.pixelIndex,e]));
 const contacts=[],rows=[];
 for(const [rowStart,rowEnd] of runs){
  const got=nativePolygonIntervals(idx,{size,rowStart,rowEnd,latitudes});
  for(let y=rowStart;y<rowEnd;y++){
   const spans=got.rows.get(y)??[],ties=got.ties.filter(t=>t.y===y);
   rows.push({y,spans,ties});
   for(const p of scope.records.filter(p=>p.original_key.y===y)){
    const x=p.original_key.x,hits=[...new Set(spans.filter(s=>s.start<=x&&x<s.end).map(s=>s.owner))],boundary=ties.filter(t=>t.x===x||(t.start<=x&&x<t.end));
    const fact=i=>{const e=lookup.get(i);return {id:e.id,index:i,index_namespace:kind==='new-vnm-cod-adm0'?'country-source-feature-ordinal':'existing-Atlas-native-index',properties:e.properties};};
    contacts.push({original_key:p.original_key,longitude:(x+.5)/size*360-180,latitude:latitudes[y],positive_contacts:hits.map(fact),boundary_tie_contacts:boundary.map(t=>({kind:t.kind,...fact(t.owner)}))});
   }
  }
 }
 const result={kind,source:base+'inputs/'+file,native_rule:NATIVE_GRID_METHOD,records:contacts.length,contacts,requested_complete_rows:rows,source_approval:false,ownership_mutation:false,current_native_owner_zero_checked:false,limit:kind==='new-vnm-cod-adm0'?'NewGSO2025country body, not original2020district/parent identity':'Eight applicable accepted89ffmap features only. This is not a complete global/currentnative authority query; original345foreignsource-family comparisons remain separate.'};
 fs.writeFileSync(base+kind+'-contacts.json',JSON.stringify(result,null,2)+'\n');
 const summary={kind,features:entries.length,keys:contacts.length,positive_keys:contacts.filter(p=>p.positive_contacts.length).length,tie_keys:contacts.filter(p=>p.boundary_tie_contacts.length).length};
 summaries.push(summary);console.log(JSON.stringify(summary));
}
fs.writeFileSync(base+'vnm-current-map-execution-receipt.json',JSON.stringify({status:'completed',elapsed_ms:performance.now()-start,finished_utc:new Date().toISOString(),internal_lifetime_max_rss_bytes:process.resourceUsage().maxRSS*1024,final_rss_bytes:process.memoryUsage().rss,policy_guards_added:false,source_predicate:NATIVE_GRID_METHOD,kernel_sha256:sha(fs.readFileSync(base+'inputs/accepted89ff/src/native-grid.js')),inputs:pins,summaries,ownership_mutation:false,repair_credit:0},null,2)+'\n');
