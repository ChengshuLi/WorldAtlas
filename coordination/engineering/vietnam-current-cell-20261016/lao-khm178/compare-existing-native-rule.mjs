import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {nativeRuntimeIndex,nativePolygonIntervals,NATIVE_GRID_METHOD} from './inputs/accepted89ff/src/native-grid.js';

// Task-only invocation of the unchanged accepted native rule. Numerical indices
// below identify source features; they never create or assign Atlas owners.
const base='bulk-completion/vn-lao-khm178/';
const started=performance.now(), deadline=started+55000;
const availableBytes=process.availableMemory(), entryRss=process.memoryUsage().rss;
const resourceObservation={availableBytes,entryRss,task_complete_phase_bound_bytes:512*1024*1024};
// Current accepted code removed the old processingAllowance policy. Observe
// current OS capacity directly; do not import or recreate historical controls.
const prospectiveCompletePhaseBytes=resourceObservation.task_complete_phase_bound_bytes;
const sha=b=>createHash('sha256').update(b).digest('hex');
const require=(x,m)=>{if(!x)throw Error(m);};
require(prospectiveCompletePhaseBytes<=availableBytes,'Task complete phase does not fit current OS available memory');
const pins=JSON.parse(fs.readFileSync(base+'comparison-input-bindings.json'));
const codePins=JSON.parse(fs.readFileSync(base+'accepted-code-bindings.json'));
for(const p of codePins){const b=fs.readFileSync(p.path);require(b.length===p.bytes&&sha(b)===p.sha256,'Accepted code pin mismatch: '+p.path);}
const read=p=>{const pin=pins.find(x=>x.path===p);require(pin,'Unpinned scientific input '+p);const b=fs.readFileSync(p);require(b.length===pin.bytes&&sha(b)===pin.sha256,'Scientific input identity mismatch '+p);return b;};
const json=p=>JSON.parse(read(p));
fs.writeFileSync(base+'actual-admission.json',JSON.stringify({started_utc:new Date().toISOString(),resourceObservation,entry_rss:process.memoryUsage().rss,rule:NATIVE_GRID_METHOD,codePins,inputPins:pins,scope:'178 unchanged original keys; no current-owner-zero or owner mutation',source_index_namespace:'Per-family source feature ordinal for COD; original global SID for retained geoBoundaries. Neither is a new Atlas owner.'},null,2)+'\n');
const scope=json(base+'exact178-original-scope.json');
const identities=json(base+'inputs/existing345-native-locations.json');
const latPin=pins.find(x=>x.path.endsWith('native-latitudes.f64le.gz'));
const latRaw=gunzipSync(read(latPin.path));
require(latRaw.length===2097328&&sha(latRaw)==='66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23','Latitude original decoded identity');
const size=262166,latitudes=Float64Array.from({length:size},(_,i)=>latRaw.readDoubleLE(i*8));
const roster=new Map(identities.roster.map(x=>[x.source_id,x]));
const results=[];
const families=[['LAO','cod-adm0','lao_admin0.geojson'],['LAO','cod-adm2','lao_admin2.geojson'],['LAO','original-adm2','original-gb-LAO-ADM2.json'],['KHM','cod-adm0','khm_admin0.geojson'],['KHM','cod-adm2','khm_admin2.geojson'],['KHM','original-adm2','original-gb-KHM-ADM2.json']];
for(const [country,kind,file] of families){
 require(performance.now()<deadline,'Comparison deadline before '+country+kind);
 const family=json(base+'inputs/'+file), original=kind==='original-adm2';
 const entries=family.features.map((f,ordinal)=>{
  const sourceId=original?`gb:${country}:ADM2:${f.properties.shapeID}`:`cod:${country}:${kind}:${f.properties.adm2_pcode??f.properties.adm0_pcode}`;
  const old=original?roster.get(sourceId):null;
  require(!original||old,'Original source identity missing');
  return {id:sourceId,pixelIndex:original?old.source_index:ordinal+1,geometry:f.geometry,ordinal,properties:f.properties,existing_atlas_owners:old?.owners??[],original_sid:old?.source_index??null};
 });
 const lookup=new Map(entries.map(e=>[e.pixelIndex,e]));
 const index=nativeRuntimeIndex(entries);
 const points=scope.records.filter(r=>r.country_comparison===country&&!(original&&country==='KHM'&&r.original_key.owner===48516&&r.original_key.x===208401&&r.original_key.y===122965));
 const ys=[...new Set(points.map(p=>p.original_key.y))].sort((a,b)=>a-b),runs=[];
 for(const y of ys){const last=runs.at(-1);if(last&&last[1]===y)last[1]++;else runs.push([y,y+1]);}
 const rowResults=[],contacts=[];
 for(const [rowStart,rowEnd] of runs){
  require(performance.now()<deadline,'Comparison deadline during '+country+kind);
  const got=nativePolygonIntervals(index,{size,rowStart,rowEnd,latitudes});
  for(let y=rowStart;y<rowEnd;y++){
   const spans=got.rows.get(y)??[],ties=got.ties.filter(t=>t.y===y);
   rowResults.push({y,spans:spans.map(s=>({start:s.start,end:s.end,source_feature_index:s.owner})),ties:ties.map(t=>({...t,source_feature_index:t.owner,owner:undefined}))});
   for(const p of points.filter(p=>p.original_key.y===y)){
    const x=p.original_key.x;
    const hits=[...new Set(spans.filter(s=>s.start<=x&&x<s.end).map(s=>s.owner))];
    const tieHits=ties.filter(t=>t.x===x||(t.start<=x&&x<t.end));
    const fact=i=>{const e=lookup.get(i);return {source_feature_index:i,source_id:e.id,ordinal:e.ordinal,properties:e.properties,original_sid:e.original_sid,existing_atlas_owners:e.existing_atlas_owners};};
    contacts.push({original_key:p.original_key,longitude:(x+.5)/size*360-180,latitude:latitudes[y],positive_source_contacts:hits.map(fact),boundary_tie_contacts:tieHits.map(t=>({kind:t.kind,...fact(t.owner)}))});
   }
  }
  require(process.memoryUsage().rss<=prospectiveCompletePhaseBytes,'Task complete phase bound exceeded');
 }
 if(original&&country==='KHM'){
  const priorPath='vietnam-next/repair-package/cambodia-resolution/bencau-membership-admission-20261015/execution-001/one-row-result.json';
  // Actual independently reviewed no-member/no-tie result is reused, never rerun.
  const prior=json(priorPath);
  contacts.push({original_key:{owner:48516,y:122965,x:208401},positive_source_contacts:[],boundary_tie_contacts:[],reused_actual_negative:{path:priorPath,sha256:pins.find(p=>p.path===priorPath).sha256,review:'vietnam-next/repair-package/cambodia-resolution/bencau-membership-admission-20261015/independent-actual-review/review.md'},prior_result_keys:Object.keys(prior)});
 }
 require(contacts.length===(country==='LAO'?129:49),'Complete family exact-key contact coverage');
 const result={country,kind,source_path:base+'inputs/'+file,features:entries.length,source_feature_index_is_not_atlas_owner:true,native_rule:NATIVE_GRID_METHOD,contacts,all_requested_rows:rowResults,scientific_approval:false,native_topology_verified:false,ownership_mutation:false};
 fs.writeFileSync(base+country.toLowerCase()+'-'+kind+'-contacts.json',JSON.stringify(result,null,2)+'\n');
 results.push({country,kind,features:entries.length,keys:contacts.length,positive_keys:contacts.filter(c=>c.positive_source_contacts.length).length,tie_keys:contacts.filter(c=>c.boundary_tie_contacts.length).length,runs:runs.length,elapsed_ms:performance.now()-started});
 console.log(JSON.stringify(results.at(-1)));
}
fs.writeFileSync(base+'actual-comparison-receipt.json',JSON.stringify({status:'completed',started_utc:new Date(Date.now()-(performance.now()-started)).toISOString(),finished_utc:new Date().toISOString(),elapsed_ms:performance.now()-started,internal_lifetime_max_rss_bytes:process.resourceUsage().maxRSS*1024,final_rss_bytes:process.memoryUsage().rss,resourceObservation,results,no_new_kernel:true,no_source_geometry_edits:true,no_current_owner_zero_claim:true,proposed_owner_assignment_only:true,ownership_mutation:false,repair_credit:0},null,2)+'\n');
