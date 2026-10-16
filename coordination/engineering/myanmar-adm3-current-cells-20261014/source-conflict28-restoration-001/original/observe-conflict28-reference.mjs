import fs from 'node:fs';import {createHash} from 'node:crypto';import {gunzipSync} from 'node:zlib';
import {nativeRuntimeIndex,nativePolygonIntervals} from '../mmr7479-native-preparation-001/accepted-9f40/src/native-grid.js';
const sha=b=>createHash('sha256').update(b).digest('hex');
const rows=JSON.parse(fs.readFileSync('.cache/worker6-mmr-original-scope-0400-001/source-conflict28.json'));
if(rows.records.length!==28||new Set(rows.records.map(r=>r.y+','+r.x)).size!==28)throw Error('Original28 coordinate roster');
const raw=fs.readFileSync('.cache/mmr7479-native-preparation-001/reference-countries.geojson.gz');if(sha(raw)!=='7b631cc2986f597d3378b72d86c11d42b0ef843e130f9194ffdd2e52797da075')throw Error('Original country body');
const countries=JSON.parse(gunzipSync(raw)).features;
const selected=['MMR','THA'].map((code,i)=>{const matches=countries.filter(f=>f.properties.ADM0_A3===code);if(matches.length!==1)throw Error('Country identity');return {id:code,pixelIndex:i+1,geometry:matches[0].geometry};});
const latEncoded=fs.readFileSync('.cache/mmr7479-native-preparation-001/native_latitudes.gz');if(sha(latEncoded)!=='ab0becdda100da3473d7bb5d34ccda6510aa1c0490c407082072c7201ad1e147')throw Error('Latitude bytes');const lat=gunzipSync(latEncoded),latitudes=Float64Array.from({length:262166},(_,i)=>lat.readDoubleLE(i*8));
if(sha(lat)!=='66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23')throw Error('Latitude identity');
const index=nativeRuntimeIndex(selected),out=rows.records.map(r=>({...r,reference_hits:[],reference_ties:[]}));
for(const block of [...new Set(out.map(r=>Math.floor(r.y/4096)))]){
 const points=out.filter(r=>Math.floor(r.y/4096)===block);const scan=nativePolygonIntervals(index,{size:262166,latitudes,rowStart:Math.min(...points.map(r=>r.y)),rowEnd:Math.max(...points.map(r=>r.y))+1});
 for(const p of points){p.reference_hits=[...new Set((scan.rows.get(p.y)??[]).filter(r=>r.start<=p.x&&p.x<r.end).map(r=>selected[r.owner-1].id))];p.reference_ties=scan.ties.filter(t=>t.y===p.y&&(t.start??t.x)<=p.x&&p.x<(t.end??t.x+1)).map(t=>({country:selected[t.owner-1].id,kind:t.kind}));p.longitude=(p.x+.5)/262166*360-180;p.latitude=latitudes[p.y];}
}
const result={kind:'original28-conflict-two-original-reference-operands-observation',source:'f7c358326d776398bc1cffe84df81eac7033091c:data/retained-geographic-sources/namibia/natural-earth-reference-countries.geojson.gz',country_body_sha256:sha(raw),operator:'Original exact nativePolygonIntervals; no geometry clipping or source priority introduced',records:out,limits:['Reference membership is a source fact, not an adopted winner or source-priority decision.','All competing source SIDs/candidate owners retained. No native qualification or selection mutation.']};
fs.writeFileSync('.cache/worker3-mmr3483-opportunity-001/conflict28-reference-observation.json',JSON.stringify(result)+'\n',{flag:'wx'});
console.log(JSON.stringify({coordinates:out.length,groups:Object.fromEntries([...new Set(out.map(p=>p.reference_hits.join('+')||'neither'))].map(k=>[k,out.filter(p=>(p.reference_hits.join('+')||'neither')===k).length])),ties:out.filter(p=>p.reference_ties.length).length,rss_bytes:process.memoryUsage().rss}));
