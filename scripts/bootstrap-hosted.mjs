import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
process.chdir(path.dirname(path.dirname(fileURLToPath(import.meta.url))));
const origin=process.argv[2];if(!origin||new URL(origin).protocol!=='https:')throw Error('Supply the confirmed owner-private Site origin');
if(!process.stdin.isTTY)throw Error('A hidden credential must be supplied through the terminal');
process.stdin.setRawMode(true);process.stdout.write('Ready for private service credential on hidden stdin.\n');
const token=await new Promise((resolve,reject)=>{let value='';process.stdin.on('data',chunk=>{value+=chunk.toString();if(!value.includes('\n'))return;process.stdin.pause();process.stdin.setRawMode(false);try{resolve(JSON.parse(value.trim()).token);}catch{reject(Error('Invalid credential'));}});});
if(typeof token!=='string'||!token)throw Error('Missing credential');
const headers={'OAI-Sites-Authorization':`Bearer ${token}`,Origin:origin};
async function request(route,options={}){let response;for(let attempt=0;attempt<4;attempt++){response=await fetch(origin+route,{...options,headers:{...headers,...options.headers}});if(![429,502,503,504].includes(response.status))break;await new Promise(resolve=>setTimeout(resolve,Math.min(4000,500*2**attempt)));}if(!response.ok){let error=await response.text();throw Error(`${route}: HTTP ${response.status}: ${error.replaceAll(token,'[redacted]').slice(0,1200)}`);}return response;}
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const manifest=JSON.parse(fs.readFileSync('data/hosted-catalog/index.json'));
let completed=0;let lastUpdate=Date.now();
async function batch(payload){return (await request('/api/records/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)})).json();}
// Taxonomy and sources precede dependent identities. Entities are then split
// into tier-local batches so independent batches can import concurrently.
const ranks=['continent','subcontinent','region','area','province','location','settlement'];
const collections={entity_types:[],sources:[],entities:[],categories:[]};
for(const descriptor of manifest.batches){const bytes=fs.readFileSync('data/hosted-catalog/'+descriptor.path);if(sha(bytes)!==descriptor.sha256)throw Error(`Catalog checksum mismatch: ${descriptor.path}`);const data=JSON.parse(bytes);collections[descriptor.kind].push(...data[descriptor.kind]);}
async function importRows(kind,rows){const inputs=[];for(let at=0;at<rows.length;at+=200){const value={[kind]:rows.slice(at,at+200)};value.ingestion_id=`bootstrap:${sha(JSON.stringify(value))}`;inputs.push(value);}let at=0;await Promise.all(Array.from({length:Math.min(3,inputs.length)},async()=>{while(at<inputs.length){await batch(inputs[at++]);completed++;if(Date.now()-lastUpdate>15000){lastUpdate=Date.now();console.log(`Persistent catalog: ${completed} bounded batches imported; current collection ${kind}.`);}}}));}
await importRows('entity_types',collections.entity_types);await importRows('sources',collections.sources);
for(const rank of ranks)await importRows('entities',collections.entities.filter(r=>r.kind===rank));
const unsupported=collections.entities.filter(r=>!ranks.includes(r.kind));if(unsupported.length)throw Error('Catalog contains an unplanned identity kind');
await importRows('categories',collections.categories);
const archive=fs.readFileSync('data/geographic-migration-archive.json.gz'),digest=sha(archive),sourceId=`source:atlas:immutable-archive:${digest}`;
await batch({ingestion_id:`archive-source:${digest}`,sources:[{id:sourceId,name:'Immutable retained atlas source archive',license:'Mixed original source licenses; retained source notices and provenance govern each record',vintage:'Retained original geographic and historical records',status:'reference',supported_from:2026,supported_to:2027,metadata:{identity_only:true,archive_sha256:digest,scope:'Preservation of original records; no inferred historical memberships'}}]});
const params=new URLSearchParams({id:`media:atlas:archive:${digest}`,source_id:sourceId,name:'Retained geographic identities, original geometry and history',license:'Mixed original source licenses; inspect each archived source',attribution:'Original data providers cited in the retained archive'});
const uploaded=await (await request('/api/media/upload?'+params,{method:'POST',headers:{'Content-Type':'application/gzip'},body:archive})).json();
if(uploaded.sha256!==digest||uploaded.bytes!==archive.length)throw Error('Persistent source archive receipt does not match original');
await batch({ingestion_id:`archive-links:${digest}`,media_links:collections.entities.filter(e=>e.kind==='continent'&&e.active).map(e=>({id:`archive:${digest}:${e.id}`,media_id:uploaded.id,entity_id:e.id,role:'original-source-archive',source_id:sourceId,metadata:{preservation_only:true}}))});
const overview=await (await request('/api/storage')).json();
if(overview.counts.entities!==manifest.counts.entities+manifest.counts.categories)throw Error('Persistent entity count does not match catalog');
console.log(JSON.stringify({persistent_database:overview.counts,media_bytes:overview.media_bytes,archive_sha256:digest,revision:overview.revision}));
