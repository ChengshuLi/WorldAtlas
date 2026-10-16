import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {nativeRuntimeIndex,nativePolygonIntervals} from '../../src/native-grid.js';
const sha=b=>createHash('sha256').update(b).digest('hex');
const root=new URL('./',import.meta.url),pins=[];
function file(name,expected){const b=fs.readFileSync(new URL(name,root));if(sha(b)!==expected)throw Error(name+' hash mismatch');pins.push({path:name,bytes:b.length,sha256:sha(b)});return JSON.parse(b);}
function blob(oid,expected){const b=execFileSync('git',['cat-file','blob',oid],{maxBuffer:20*1024**2,env:{...process.env,GIT_NO_LAZY_FETCH:'1'}});if(sha(b)!==expected)throw Error(oid+' hash mismatch');pins.push({git_blob_oid:oid,bytes:b.length,sha256:sha(b)});return b;}
const started=performance.now();
const exact=file('exact365-new-source-identity-inputs.json','53b6a1400802e8f73d25a2dcad6f14606e07add90ed54542f94b0895e4e1748b');
const stage=file('whole-new-source-stage-inputs.json','620c3aab733389f4511491ba5c1f916f22c9235188b6e00d6a20053ef1020988');
const countryDecoded=gunzipSync(blob('235bf73f0890fa97c82d1471f840296f17cfcfca','7b631cc2986f597d3378b72d86c11d42b0ef843e130f9194ffdd2e52797da075'));
if(sha(countryDecoded)!=='239eec57ac17f100a11e2536cffc56752c318b50ae765b0918ff7aab4ce8f255')throw Error('Country decoded hash');
const countries=JSON.parse(countryDecoded).features;
const latitudeDecoded=gunzipSync(blob('de6905e162dc031b1b93248fae91190c39c4ad53','ab0becdda100da3473d7bb5d34ccda6510aa1c0490c407082072c7201ad1e147'));
if(sha(latitudeDecoded)!=='66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23')throw Error('Latitude decoded hash');
const size=262166,latitudes=Float64Array.from({length:size},(_,i)=>latitudeDecoded.readDoubleLE(i*8));
if(exact.records.length!==365||new Set(exact.records.map(r=>JSON.stringify(r.original_key))).size!==365)throw Error('Exact key scope');
const rows=exact.records.map(r=>({...r,latitude_from_normative_table:latitudes[r.original_key.y]}));
const rowStart=Math.min(...rows.map(r=>r.original_key.y)),rowEnd=Math.max(...rows.map(r=>r.original_key.y))+1;
const allCountries=countries.map((f,i)=>({id:'retained-country-ordinal:'+i,pixelIndex:i+1,geometry:f.geometry}));
const allSources=stage.map((r,i)=>({id:r.target,pixelIndex:i+1,geometry:r.consumed.geometry}));
function observe(features,kind){
 const scan=nativePolygonIntervals(nativeRuntimeIndex(features),{size,rowStart,rowEnd,latitudes});
 for(const r of rows){const {y,x}=r.original_key;r[kind+'_hits']=[...new Set((scan.rows.get(y)??[]).filter(s=>s.start<=x&&x<s.end).map(s=>s.owner-1))];r[kind+'_ties']=scan.ties.filter(t=>t.y===y&&(t.start??t.x)<=x&&x<(t.end??t.x+1)).map(t=>({...t,feature_ordinal:t.owner-1}));}
 return {input_features:features.length,complete_row_window:[rowStart,rowEnd],evaluated_rows:rowEnd-rowStart,output_rows:scan.rows.size,all_window_ties:scan.ties.length,method:scan.method};
}
const countryExecution=observe(allCountries,'country'),sourceExecution=observe(allSources,'new_source');
for(const r of rows){r.country_hits=r.country_hits.map(i=>({ordinal:i,ADM0_A3:countries[i].properties.ADM0_A3,ADMIN:countries[i].properties.ADMIN,ISO_A3_EH:countries[i].properties.ISO_A3_EH}));r.new_source_hits=r.new_source_hits.map(i=>stage[i].target);r.exclusive_CHN_reference=r.country_hits.length===1&&r.country_hits[0].ADM0_A3==='CHN'&&!r.country_ties.length;r.unique_proposed_source=r.new_source_hits.length===1&&r.new_source_hits[0]===r.new_source_identity&&!r.new_source_ties.length;}
const groups={};for(const r of rows){const key=r.country_hits.map(h=>h.ADM0_A3).sort().join('+')||'neither';groups[key]=(groups[key]??0)+1;}
const out={kind:'independent-full-retained-country-and-twelve-new-source-exact-native365-observation',accepted_code_commit:'cd68e89523901acf477d0365470410b8b970bb48',pins,country_source:{commit:'f7c358326d776398bc1cffe84df81eac7033091c',path:'data/retained-geographic-sources/namibia/natural-earth-reference-countries.geojson.gz',decoded_bytes:countryDecoded.length,decoded_sha256:sha(countryDecoded)},native_latitudes:{decoded_bytes:latitudeDecoded.length,decoded_sha256:sha(latitudeDecoded)},country_feature_inventory:countries.map((f,i)=>({ordinal:i,ADM0_A3:f.properties.ADM0_A3,ADMIN:f.properties.ADMIN,ISO_A3_EH:f.properties.ISO_A3_EH,geometry_type:f.geometry.type})),country_execution:countryExecution,new_source_execution:sourceExecution,groups,exact_keys:rows.length,exclusive_CHN_keys:rows.filter(r=>r.exclusive_CHN_reference).length,unique_proposed_source_keys:rows.filter(r=>r.unique_proposed_source).length,country_tie_keys:rows.filter(r=>r.country_ties.length).length,source_tie_keys:rows.filter(r=>r.new_source_ties.length).length,records:rows,elapsed_seconds:(performance.now()-started)/1000,limits:['All retained country features, not a selected CHN/VNM subset, are tested.','This is exact membership under nativePolygonIntervals, not current owner-zero, complete competing fine-source qualification, adoption, or sovereign jurisdiction.','The original competing source-census operands and contradictory fine-source hits remain unchanged.','No geometry editing, country clipping, recency priority, finer-polygon fallback, or source-bank replay.']};
fs.writeFileSync(new URL('full-country365-exact-native-observation.json',root),JSON.stringify(out,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({country_features:countries.length,groups,exclusive_CHN:out.exclusive_CHN_keys,unique_proposed:out.unique_proposed_source_keys,country_ties:out.country_tie_keys,source_ties:out.source_tie_keys,elapsed_seconds:out.elapsed_seconds,rss:process.memoryUsage().rss}));
