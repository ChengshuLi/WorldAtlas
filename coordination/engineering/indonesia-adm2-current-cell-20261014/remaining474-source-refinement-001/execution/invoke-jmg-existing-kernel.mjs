// Separate official-source observation using the unchanged accepted exact kernel.
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {witnessCellEffects,nativePolygonIntervals} from './accepted-native-grid.mjs';
const sha=b=>createHash('sha256').update(b).digest('hex');
const c=JSON.parse(fs.readFileSync(process.argv[2])),read=p=>{const b=fs.readFileSync(p.path);if(b.length!==p.bytes||sha(b)!==p.sha256)throw Error('Changed bound source '+p.path);return b;};
const raw=read(c.geometry),g=JSON.parse(raw),requests=JSON.parse(read(c.requests)).requests.filter(r=>r.country==='MYS'),byRow=new Map();
for(const r of requests){const xs=byRow.get(r.y)??new Set();xs.add(r.x);byRow.set(r.y,xs);}
const requestedRows=[...byRow].sort((a,b)=>a[0]-b[0]).map(([y,x])=>({y,runs:[...x].sort((a,b)=>a-b).map(x=>[x,x+1,1])}));
const b=gunzipSync(read(c.latitudes));if(sha(b)!==c.normative_decoded_sha256)throw Error('Normative table drift');const latitudes=Float64Array.from({length:262166},(_,y)=>b.readDoubleLE(y*8));
const started=performance.now(),effects=witnessCellEffects(g,{size:262166,latitudes,requestedRows,nativePolygonIntervals}),hits=new Map();for(const h of effects.hits){const k=h.y+':'+h.x;const a=hits.get(k)??[];a.push(h.kind);hits.set(k,a);}
const result={kind:'independent-government-source-JMG-Sarawak-native-observation-only',config:c,original_request_count:requests.length,effects,per_original_request:requests.map(r=>({id:r.id,original_package:r.original_package,owner:r.owner??null,y:r.y,x:r.x,jmg_sarawak_contact_kinds:hits.get(r.y+':'+r.x)??[]})),elapsed_seconds:(performance.now()-started)/1000,limits:['Official JMG Sarawak polygon only, not a complete Malaysia source family. Outside Sarawak cannot become outside Malaysia or an IDN winner.','The public government service performed requested outSR4326 transformation from its projected source; exact default datum transformation, positional accuracy and represented boundary date remain unestablished.','Existing source geodetic/vintage/license limits retained. No owner/hold change, legal border, qualification or repair credit.'],authority_or_repair_credit:0};
const out=Buffer.from(JSON.stringify(result)+'\n');fs.writeFileSync(process.argv[3]+'.partial',out,{flag:'wx'});fs.renameSync(process.argv[3]+'.partial',process.argv[3]);console.log(JSON.stringify({bytes:out.length,sha256:sha(out),counts:effects.counts,elapsed_seconds:result.elapsed_seconds}));
