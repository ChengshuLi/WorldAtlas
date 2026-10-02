import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
process.chdir(path.dirname(path.dirname(fileURLToPath(import.meta.url))));
const origin=process.argv[2],directory=process.argv[3]??'data/geographic-releases';
if(!origin||new URL(origin).protocol!=='https:')throw Error('Supply the confirmed owner-private Site origin');
if(!process.stdin.isTTY)throw Error('A private service credential must be supplied on hidden terminal stdin');
process.stdin.setRawMode(true);process.stdout.write('Ready for private service credential on hidden stdin.\n');
const token=await new Promise((resolve,reject)=>{let value='';process.stdin.on('data',chunk=>{value+=chunk.toString();if(!value.includes('\n'))return;process.stdin.pause();process.stdin.setRawMode(false);try{resolve(JSON.parse(value.trim()).token);}catch{reject(Error('Invalid credential'));}});});
if(typeof token!=='string'||!token)throw Error('Missing private service credential');
const headers={'OAI-Sites-Authorization':`Bearer ${token}`,Origin:origin};
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
async function request(route,options={}){
 let response;for(let attempt=0;attempt<4;attempt++){
  response=await fetch(origin+route,{...options,headers:{...headers,...options.headers}});
  if(![429,502,503,504].includes(response.status))break;
  await new Promise(resolve=>setTimeout(resolve,Math.min(4000,500*2**attempt)));
 }
 if(!response.ok)throw Error(`${route}: HTTP ${response.status}: ${(await response.text()).replaceAll(token,'[redacted]').slice(0,1200)}`);
 return response;
}
const manifest=JSON.parse(fs.readFileSync(`${directory}/index.json`));
let completed=0,lastUpdate=Date.now();
async function batch(part){
 const bytes=fs.readFileSync(`${directory}/${part.path}`);if(sha(bytes)!==part.sha256)throw Error(`Prepared release hash mismatch: ${part.path}`);
 await request(part.route,{method:'POST',headers:{'Content-Type':'application/json'},body:bytes});completed++;
 if(Date.now()-lastUpdate>15000){lastUpdate=Date.now();console.log(`Reference geography: ${completed} bounded import batches completed.`);}
}
async function concurrent(parts){let index=0;await Promise.all(Array.from({length:Math.min(3,parts.length)},async()=>{while(index<parts.length)await batch(parts[index++]);}));}
// Sources and new stable identities precede memberships. Existing registry rows
// are never resubmitted with different names or parents.
await batch(manifest.batches.find(p=>p.path==='sources.json'));
for(const tier of ['continent','subcontinent','region','area','province','location'])await concurrent(manifest.batches.filter(p=>p.path.startsWith(`entities-${tier}-`)));
const published=[];
for(const release of manifest.releases){
 const prior=await (await request('/api/geography/release?'+new URLSearchParams({release_id:release.id}))).json();
 if(!prior){
  await batch(manifest.batches.find(p=>p.path===`release-${release.version}.json`));
  await concurrent(manifest.batches.filter(p=>p.path.startsWith(`${release.version}-`)));
  await request('/api/geography/finalize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({release_id:release.id})});
 }
 const actual=await (await request('/api/geography/release?'+new URLSearchParams({release_id:release.id}))).json();
 for(const key of ['membership_sha256','footprints_sha256','hierarchy_sha256','location_ids_sha256','changes_sha256'])if(actual?.[key]!==release[key])throw Error(`Published reference ${key} mismatch`);
 // Counts are compared by value because the server canonicalizes object keys.
 if(actual.status!=='published'||Object.keys(release.expected_counts).some(k=>actual.expected_counts[k]!==release.expected_counts[k]))throw Error('Published reference counts mismatch');
 published.push({id:actual.id,version:actual.version,counts:actual.expected_counts,membership_sha256:actual.membership_sha256});
}
// Retain the complete before/after crosswalk independently of deployment assets.
const archive=fs.readFileSync('data/geographic-decision-migration.json.gz'),digest=sha(archive),release=manifest.releases.at(-1);
const parameters=new URLSearchParams({id:`media:atlas:geographic-migration:${digest}`,source_id:release.source_id,name:'Worldwide reference hierarchy before-and-after crosswalk',license:'Original source licenses retained in cited continent decisions',attribution:'Cited public geographic providers and WorldAtlas review decisions'});
const media=await (await request('/api/media/upload?'+parameters,{method:'POST',headers:{'Content-Type':'application/gzip'},body:archive})).json();
if(media.sha256!==digest||media.bytes!==archive.length)throw Error('Persistent migration evidence does not match prepared archive');
console.log(JSON.stringify({published,bounded_batches:completed,migration_archive:{id:media.id,sha256:digest,bytes:media.bytes}}));
