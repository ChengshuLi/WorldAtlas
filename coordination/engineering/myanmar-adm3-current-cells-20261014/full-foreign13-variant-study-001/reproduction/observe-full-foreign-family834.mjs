import fs from 'node:fs';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {pinReader} from '../../scripts/prepare-delivery-handoff.mjs';
import {nativeRuntimeIndex,nativePolygonIntervals} from '../../src/native-grid.js';
import {valueSha} from '../../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const code=process.argv[2],family='gb:'+code+':ADM2',directory='.takeover/full-foreign-variants834/';
const need=(v,m)=>{if(!v)throw Error(m);},sha=b=>createHash('sha256').update(b).digest('hex');
need(['BGD','CHN','IND','LAO','THA'].includes(code),'One exact original foreign family');
const started=performance.now(),reader=pinReader(process.cwd());
const load=p=>JSON.parse(fs.readFileSync(p));
const acquisition=load(directory+'acquisition.json').records.find(r=>r.family===family);
const prior=load('.takeover/remaining1295/complete-original-foreign-fine-observation834.json');
const country=load('.takeover/remaining1295/complete-country-reference-observation1295.json');
const evidence=load('.takeover/remaining1295/diagnostic383/original7479-source-evidence.json');
const scope=country.records.filter(r=>r.reference_disposition==='foreign-only-interior');
need(scope.length===834&&new Set(scope.map(r=>[r.owner,r.y,r.x].join(':'))).size===834,'Literal unfinished 834 questions');
const rosterRaw=gunzipSync(reader.read(evidence.owner_roster));
need(rosterRaw.length===evidence.owner_roster.decoded_bytes&&sha(rosterRaw)===evidence.owner_roster.decoded_sha256,'Whole stable owner roster');
const owners=JSON.parse(rosterRaw),ownerMap=new Map(owners.map(r=>[r.id,r]));
need(owners.length===49625&&owners.every((r,i)=>r.index===i+1),'Complete original stable owner roster');
const latRaw=gunzipSync(reader.read(country.whole_native_latitudes));
need(latRaw.length===2097328&&sha(latRaw)===country.whole_native_latitudes.decoded_sha256,'Whole normative native latitudes');
const latitudes=Float64Array.from({length:262166},(_,i)=>latRaw.readDoubleLE(i*8));
const originalFamily=prior.whole_original_families.find(r=>r.family===family);
const originalRaw=Buffer.concat(originalFamily.parts.map(pin=>{const raw=gunzipSync(reader.read(pin));need(raw.length===(pin.decoded_bytes??pin.uncompressed_bytes)&&sha(raw)===(pin.decoded_sha256??pin.uncompressed_sha256),'Whole retained simplified part');return raw;}));
need(originalRaw.length===originalFamily.whole_bytes&&sha(originalRaw)===originalFamily.whole_sha256,'Complete original simplified family');
const originalCollection=JSON.parse(originalRaw),retainedByShape=new Map();
for(const [ordinal,f]of originalCollection.features.entries()){
  const id=f.properties.shapeID,rows=retainedByShape.get(id)??[];rows.push({ordinal,properties:f.properties});retainedByShape.set(id,rows);
}
const encoded=fs.readFileSync(acquisition.file);need(encoded.length===acquisition.bytes&&sha(encoded)===acquisition.sha256,'Whole acquired full encoded body');
let raw=gunzipSync(encoded,{maxOutputLength:acquisition.decoded_bytes});
need(raw.length===acquisition.decoded_bytes&&sha(raw)===acquisition.decoded_sha256,'Whole acquired full decoded body');
const full=JSON.parse(raw);raw=null;
need(full.type==='FeatureCollection'&&Array.isArray(full.features)&&full.features.length>0,'Complete full FeatureCollection');
const fullByShape=new Map();
for(const [ordinal,f]of full.features.entries()){
  need(f.type==='Feature'&&f.properties&&typeof f.properties.shapeID==='string'&&['Polygon','MultiPolygon'].includes(f.geometry?.type),'No omitted full original member');
  const rows=fullByShape.get(f.properties.shapeID)??[];rows.push(ordinal);fullByShape.set(f.properties.shapeID,rows);
}
function bounds(g){let west=Infinity,south=Infinity,east=-Infinity,north=-Infinity;const walk=a=>{if(typeof a[0]==='number'){west=Math.min(west,a[0]);east=Math.max(east,a[0]);south=Math.min(south,a[1]);north=Math.max(north,a[1]);}else for(const c of a)walk(c);};walk(g.coordinates);return [west,south,east,north];}
const pointBounds=[Math.min(...scope.map(r=>(r.x+.5)/262166*360-180)),Math.min(...scope.map(r=>latitudes[r.y])),Math.max(...scope.map(r=>(r.x+.5)/262166*360-180)),Math.max(...scope.map(r=>latitudes[r.y]))];
const crosswalk=[],features=[],details=new Map(),featureByScanIndex=new Map();
for(const [ordinal,f]of full.features.entries()){
  const id=family+':'+f.properties.shapeID,old=retainedByShape.get(f.properties.shapeID)??[],existing=ownerMap.get(id)??null;
  const valid=fullByShape.get(f.properties.shapeID).length===1&&old.length===1&&!!existing
    &&f.properties.shapeGroup===code&&f.properties.shapeType==='ADM2'
    &&old[0].properties.shapeGroup===code&&old[0].properties.shapeType==='ADM2'
    &&old[0].properties.shapeName===f.properties.shapeName;
  const row={full_feature_ordinal:ordinal,full_feature_pointer:'/features/'+ordinal,full_shapeID:f.properties.shapeID,full_properties:f.properties,
    retained_original_members:old,stable_existing_location:existing,exact_same_build_member_crosswalk:valid};crosswalk.push(row);
  const b=bounds(f.geometry);if(b[0]>pointBounds[2]||pointBounds[0]>b[2]||b[1]>pointBounds[3]||pointBounds[1]>b[3])continue;
  const temporary=features.length+1;features.push({id:'full-original-'+ordinal,pixelIndex:temporary,geometry:f.geometry});
  details.set(temporary,{family,country:code,source_id:id,full_feature_ordinal:ordinal,geometry_pointer:'/features/'+ordinal+'/geometry',
    full_shapeID:f.properties.shapeID,full_name:f.properties.shapeName,existing_location:existing,exact_same_build_member_crosswalk:valid,
    retained_original_member_pointers:old.map(o=>'/features/'+o.ordinal),bounds:b});featureByScanIndex.set(temporary,f);
}
const index=nativeRuntimeIndex(features),records=[],ys=[...new Set(scope.map(r=>r.y))].sort((a,b)=>a-b),contactIndices=new Set();
let calls=0,whole_feature_row_admissions=0;
for(const y of ys){
  const latitude=latitudes[y],wholeIndex=index.filter(item=>{const b=details.get(item.index).bounds;return b[1]<=latitude&&latitude<=b[3];});
  const scan=wholeIndex.length?nativePolygonIntervals(wholeIndex,{size:262166,latitudes,rowStart:y,rowEnd:y+1}):{rows:new Map(),ties:[]};
  if(wholeIndex.length)calls++;whole_feature_row_admissions+=wholeIndex.length;
  for(const p of scope.filter(r=>r.y===y)){
    const hits=(scan.rows.get(y)??[]).filter(r=>r.start<=p.x&&p.x<r.end).map(r=>{contactIndices.add(r.owner);return r.owner;});
    const ties=scan.ties.filter(r=>(r.start??r.x)<=p.x&&p.x<(r.end??r.x+1)).map(r=>{contactIndices.add(r.owner);return {index:r.owner,kind:r.kind};});
    records.push({owner:p.owner,y,x:p.x,full_interiors:hits,full_boundaries:ties});
  }
}
for(const i of contactIndices)details.get(i).geometry_sha256=valueSha(featureByScanIndex.get(i).geometry);
for(const r of records){r.full_interiors=r.full_interiors.map(i=>details.get(i));r.full_boundaries=r.full_boundaries.map(t=>({...details.get(t.index),kind:t.kind}));}
const originalMissing=[...retainedByShape].filter(([id])=>!fullByShape.has(id)).flatMap(([id,rows])=>rows.map(r=>({shapeID:id,...r})));
const counts={points_with_interior:records.filter(r=>r.full_interiors.length).length,points_with_boundary:records.filter(r=>r.full_boundaries.length).length,
  unique_crosswalked_interior:records.filter(r=>r.full_interiors.length===1&&r.full_interiors[0].exact_same_build_member_crosswalk&&!r.full_boundaries.length).length,
  full_features:full.features.length,original_retained_features:originalCollection.features.length,
  crosswalked_full_features:crosswalk.filter(r=>r.exact_same_build_member_crosswalk).length,
  full_unmatched_or_ambiguous_members:crosswalk.filter(r=>!r.exact_same_build_member_crosswalk).length,
  retained_members_missing_from_full:originalMissing.length};
const result={kind:'bounded-complete-same-build-full-foreign-family-observation-original834',family,actual_executing_tree:reader.git('rev-parse','HEAD').toString().trim(),
  actual_native_operator:reader.pin(reader.git('rev-parse','HEAD').toString().trim(),'src/native-grid.js'),
  whole_full_source:acquisition,whole_retained_simplified_family:originalFamily,whole_native_latitudes:country.whole_native_latitudes,
  complete_stable_owner_roster:evidence.owner_roster,exact_original_questions:834,full_feature_roster_crosswalk:crosswalk,
  original_retained_members_missing_from_full:originalMissing,plausible_whole_features:features.length,affected_native_rows:ys.length,native_calls:calls,
  whole_feature_row_admissions,counts,elapsed_seconds:(performance.now()-started)/1000,rss_bytes:process.memoryUsage().rss,records,
  limits:['This is a new full-variant numerical observation, not a source adoption, qualification or delivery.',
    'Every full family feature and retained simplified member was joined by literal same-build shapeID, group, tier and name to the original stable existing owner.',
    'Bounds only omit whole geometries that cannot contact any requested centre or row; no geometry is clipped or rewritten.',
    'All full interiors, overlapping members, exact boundaries, unmatched IDs and contrary original Myanmar fine/country/current-source facts remain available.',
    'The original simplified family remains a distinct operand. Full variant source/shape identity does not itself assign any cell.']};
fs.writeFileSync(directory+'full-'+code+'-observation834.json',JSON.stringify(result,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({...result,records:undefined,full_feature_roster_crosswalk:undefined,whole_full_source:undefined,whole_retained_simplified_family:undefined,whole_native_latitudes:undefined,complete_stable_owner_roster:undefined},null,2));
