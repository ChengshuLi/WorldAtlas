import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
process.chdir(path.dirname(path.dirname(fileURLToPath(import.meta.url))));
const requestedOrigin=process.argv[2],directory=process.argv[3]??'data/prepared-evidence/imports';
const siteURL=requestedOrigin&&new URL(requestedOrigin);
if(!siteURL||siteURL.protocol!=='https:'||siteURL.username||siteURL.password||siteURL.pathname!=='/'||siteURL.search||siteURL.hash)throw Error('Supply the confirmed HTTPS Site origin');
const origin=siteURL.origin;
if(!process.stdin.isTTY)throw Error('A private service credential must be supplied on hidden terminal stdin');
process.stdin.setRawMode(true);process.stdout.write('Ready for private service credential on hidden stdin.\n');
const token=await new Promise((resolve,reject)=>{let value='';process.stdin.on('data',chunk=>{if(chunk.includes(3)){process.stdin.setRawMode(false);reject(Error('Credential entry cancelled'));return;}value+=chunk.toString();if(!/[\r\n]/.test(value))return;process.stdin.pause();process.stdin.setRawMode(false);try{resolve(JSON.parse(value.trim()).token);}catch{reject(Error('Invalid credential'));}});});
if(typeof token!=='string'||!token)throw Error('Missing private service credential');
const manifest=JSON.parse(fs.readFileSync(`${directory}/index.json`));
const sha=raw=>createHash('sha256').update(raw).digest('hex');
if(manifest.version!==1||!Array.isArray(manifest.batches))throw Error('Invalid prepared import manifest');
const publicIndexFile=path.join(path.dirname(directory),'index.json');
if(!fs.existsSync(publicIndexFile))throw Error('Prepared public index is required for import validation');
const publicIndex=JSON.parse(fs.readFileSync(publicIndexFile));
if(publicIndex.imports?.sha256!==sha(fs.readFileSync(`${directory}/index.json`)))throw Error('Prepared import manifest hash mismatch');
for(const part of manifest.batches){
 if(!/^batch-\d+\.json$/.test(part.path)||part.route!=='/api/records/import'||!['sources','categories','names','records'].includes(part.kind)||!Number.isSafeInteger(part.rows)||part.rows<1||part.rows>200)throw Error('Invalid prepared evidence import manifest');
 const raw=fs.readFileSync(`${directory}/${part.path}`),payload=JSON.parse(raw);
 if(sha(raw)!==part.sha256||raw.length>1048576||payload[part.kind]?.length!==part.rows||!payload.ingestion_id)throw Error('Prepared import bytes/count/receipt mismatch');
}
const current=await fetch(origin+'/api/geography/release',{headers:{'OAI-Sites-Authorization':`Bearer ${token}`}});
if(!current.ok)throw Error(`Cannot verify live geography before import: HTTP ${current.status}`);
const release=await current.json();for(const key of ['hierarchy_sha256','footprints_sha256'])if(release?.[key]!==manifest[key]||publicIndex[key]!==manifest[key])throw Error(`Prepared evidence requires matching published geography: ${key}`);
let completed=0,lastUpdate=Date.now();
async function batch(part){
 if(!/^batch-\d+\.json$/.test(part.path)||part.route!=='/api/records/import'||part.rows>200)throw Error('Invalid prepared evidence import manifest');
 const raw=fs.readFileSync(`${directory}/${part.path}`);if(sha(raw)!==part.sha256||raw.length>1048576)throw Error(`Prepared import hash/size mismatch: ${part.path}`);
 let response;for(let attempt=0;attempt<4;attempt++){response=await fetch(origin+part.route,{method:'POST',headers:{'Content-Type':'application/json','OAI-Sites-Authorization':`Bearer ${token}`,Origin:origin},body:raw});if(![429,502,503,504].includes(response.status))break;await new Promise(resolve=>setTimeout(resolve,Math.min(4000,500*2**attempt)));}
 if(!response.ok)throw Error(`Evidence import HTTP ${response.status}: ${(await response.text()).replaceAll(token,'[redacted]').slice(0,1000)}`);
 const receipt=await response.json();if(!receipt.ingestion_id)throw Error('Evidence import has no idempotent receipt');completed++;
 if(Date.now()-lastUpdate>15000){console.log(`Prepared evidence: ${completed}/${manifest.batches.length} bounded batches imported.`);lastUpdate=Date.now();}
}
// Commit source and category identities before dependent rows. Stable, content
// addressed ingestion IDs make interruption/retry safe without date snapshots.
for(const kind of ['sources','categories','names','records']){const parts=manifest.batches.filter(p=>p.kind===kind);let next=0;await Promise.all(Array.from({length:Math.min(3,parts.length)},async()=>{while(next<parts.length)await batch(parts[next++]);}));}
console.log(JSON.stringify({completed_batches:completed,counts:manifest.counts,footprints_sha256:manifest.footprints_sha256,hierarchy_sha256:manifest.hierarchy_sha256}));
