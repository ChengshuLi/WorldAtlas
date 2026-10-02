import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const releasePins=['membership_sha256','footprints_sha256','hierarchy_sha256','location_ids_sha256','changes_sha256'];
export function bootstrapConcurrency(value=process.env.ATLAS_IMPORT_CONCURRENCY??'6'){
 if(!/^[1-8]$/.test(String(value)))throw Error('ATLAS_IMPORT_CONCURRENCY must be an integer from 1 to 8');
 return Number(value);
}
function validatePrior(actual,release){
 for(const key of ['id','source_id','version','reference_date',...releasePins])if(actual[key]!==release[key])throw Error(`Existing reference ${key} mismatch`);
 if(!actual.expected_counts||Object.keys(actual.expected_counts).length!==Object.keys(release.expected_counts).length||Object.keys(release.expected_counts).some(k=>actual.expected_counts[k]!==release.expected_counts[k]))throw Error('Existing reference counts mismatch');
 if(!['staged','published'].includes(actual.status))throw Error('Unexpected existing reference status');
}
export async function publishGeographicReleases({manifest,batch,request,concurrency=bootstrapConcurrency(),mode='publish'}){
 if(!['publish','stage','finalize'].includes(mode))throw Error('Unknown geographic publication mode');
 concurrency=bootstrapConcurrency(concurrency);
 const need=pathname=>{const part=manifest.batches.find(p=>p.path===pathname);if(!part)throw Error(`Missing prepared reference batch: ${pathname}`);return part;};
 async function concurrent(parts){let index=0,failure;await Promise.all(Array.from({length:Math.min(concurrency,parts.length)},async()=>{while(!failure&&index<parts.length){const part=parts[index++];try{await batch(part);}catch(error){failure??=error;}}}));if(failure)throw failure;}
 // Sources and stable identities precede memberships. All retries use the same
 // pinned ingestion IDs; staging service idempotence preserves completed rows.
 const sourcePaths=manifest.sources_batches??manifest.batches.filter(p=>/^sources(?:-\d+)?\.json$/.test(p.path)).map(p=>p.path);
 if(!sourcePaths.length||new Set(sourcePaths).size!==sourcePaths.length)throw Error('Missing or duplicate prepared reference source batches');
 if(mode!=='finalize'){
 await concurrent(sourcePaths.map(need));
 for(const tier of ['continent','subcontinent','region','area','province','location'])await concurrent(manifest.batches.filter(p=>p.path.startsWith(`entities-${tier}-`)));
 }
 const published=[];
 for(const release of manifest.releases){
  const route='/api/geography/release?'+new URLSearchParams({release_id:release.id}),prior=await (await request(route)).json();
  if(prior)validatePrior(prior,release);
  // Public readers may hide staged releases; an absent or explicit staged row
  // both require idempotent replay of every bounded batch before finalization.
  if(!prior||prior.status!=='published'){
   if(mode!=='finalize'){
    await batch(need(`release-${release.version}.json`));
    await concurrent(manifest.batches.filter(p=>p.path.startsWith(`${release.version}-`)));
   }
   if(mode==='stage'){published.push({id:release.id,version:release.version,status:'staged',public_readback_verified:false});continue;}
   await request('/api/geography/finalize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({release_id:release.id})});
  }
  const actual=await (await request(route)).json();if(!actual)throw Error('Published reference release is missing');validatePrior(actual,release);
  if(actual.status!=='published')throw Error('Reference release remains staged after finalization');
  published.push({id:actual.id,version:actual.version,counts:actual.expected_counts,membership_sha256:actual.membership_sha256});
 }
 return published;
}
export async function retainGeographicArchives({archiveFiles,sourceId,request,readArchive=file=>fs.readFileSync(file)}){
 const retained=[],byDigest=new Map();
 // The first sorted path defines immutable media metadata on every retry.
 // Different source paths with identical bytes remain explicit receipt aliases.
 for(const file of [...archiveFiles].sort()){
  const archive=readArchive(file),digest=createHash('sha256').update(archive).digest('hex');
  if(archive.length>20*1024*1024)throw Error('Migration archive exceeds the media-object limit');
  let stored=byDigest.get(digest);
  if(!stored){
   const id=`media:atlas:geographic-evidence:${digest}`,prior=await request('/api/media/'+encodeURIComponent(id)+'?metadata=1',{allowNotFound:true});
   let media;
   if(prior.status===404){
    const parameters=new URLSearchParams({id,source_id:sourceId,name:file.slice(5),license:'Mixed original source licenses; notices retained in the geographic source manifests',attribution:'Cited public geographic providers and WorldAtlas review decisions'});
    media=await (await request('/api/media/upload?'+parameters,{method:'POST',headers:{'Content-Type':file.endsWith('.gz')?'application/gzip':'application/json'},body:archive})).json();
   }else media=await prior.json();
   if(media.sha256!==digest||media.bytes!==archive.length)throw Error('Persistent migration evidence does not match prepared archive');
   stored={id:media.id,sha256:digest,bytes:media.bytes,canonical_path:'data/'+media.name};byDigest.set(digest,stored);
  }
  retained.push({path:file,...stored});
 }
 return retained;
}
async function main(){
process.chdir(path.dirname(path.dirname(fileURLToPath(import.meta.url))));
const origin=process.argv[2],directory=process.argv[3]??'data/geographic-releases',concurrency=bootstrapConcurrency(),mode=process.argv.includes('--stage-only')?'stage':process.argv.includes('--finalize-only')?'finalize':'publish';
if(process.argv.includes('--stage-only')&&process.argv.includes('--finalize-only'))throw Error('Choose staging or finalization');
if(!origin||new URL(origin).protocol!=='https:')throw Error('Supply the confirmed owner-private Site origin');
if(!process.stdin.isTTY)throw Error('A private service credential must be supplied on hidden terminal stdin');
process.stdin.setRawMode(true);process.stdout.write('Ready for private service credential on hidden stdin.\n');
const token=await new Promise((resolve,reject)=>{let value='';process.stdin.on('data',chunk=>{value+=chunk.toString();if(!value.includes('\n'))return;process.stdin.pause();process.stdin.setRawMode(false);try{resolve(JSON.parse(value.trim()).token);}catch{reject(Error('Invalid credential'));}});});
if(typeof token!=='string'||!token)throw Error('Missing private service credential');
const headers={'OAI-Sites-Authorization':`Bearer ${token}`,Origin:origin};
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
async function request(route,options={}){
 const {allowNotFound,...fetchOptions}=options;
 let response;for(let attempt=0;attempt<4;attempt++){
  response=await fetch(origin+route,{...fetchOptions,headers:{...headers,...fetchOptions.headers}});
  if(![429,502,503,504].includes(response.status))break;
  await new Promise(resolve=>setTimeout(resolve,Math.min(4000,500*2**attempt)));
 }
 if(!response.ok&&!(allowNotFound&&response.status===404))throw Error(`${route}: HTTP ${response.status}: ${(await response.text()).replaceAll(token,'[redacted]').slice(0,1200)}`);
 return response;
}
const manifest=JSON.parse(fs.readFileSync(`${directory}/index.json`));
let completed=0,lastUpdate=Date.now();
async function batch(part){
 const bytes=fs.readFileSync(`${directory}/${part.path}`);if(sha(bytes)!==part.sha256)throw Error(`Prepared release hash mismatch: ${part.path}`);
 await request(part.route,{method:'POST',headers:{'Content-Type':'application/json'},body:bytes});completed++;
 if(Date.now()-lastUpdate>15000){lastUpdate=Date.now();console.log(`Reference geography: ${completed} bounded import batches completed.`);}
}
const published=process.argv.includes('--archives-only')?[]:await publishGeographicReleases({manifest,batch,request,concurrency,mode});
// Retain the complete before/after crosswalk independently of deployment assets.
const release=manifest.releases.at(-1),archiveFiles=new Set(['data/geographic-decision-migration.json.gz']);
for(const file of ['data/macro-boundary-migration.json.gz','data/geographic-repair-evidence/index.json','data/reference-migrations/source-territory-repair-v1/index.json'])if(fs.existsSync(file))archiveFiles.add(file);
const repairIndex='data/geographic-repair-evidence/index.json';
if(fs.existsSync(repairIndex)){const index=JSON.parse(fs.readFileSync(repairIndex));for(const pin of Object.values(index.files)){const file='data/geographic-repair-evidence/'+pin.archive_path;if(sha(fs.readFileSync(file))!==pin.sha256)throw Error('Retained geographic evidence changed');archiveFiles.add(file);}}
const references='data/reference-migrations/source-territory-repair-v1';
if(fs.existsSync(references))for(const file of fs.readdirSync(references))archiveFiles.add(references+'/'+file);
for(const directory of ['data/macro-foundation','data/reference-migrations/global-macro-reference-v3'])if(fs.existsSync(directory))for(const file of fs.readdirSync(directory,{recursive:true})){const full=directory+'/'+file;if(fs.statSync(full).isFile())archiveFiles.add(full);}
const retained=mode==='finalize'?[]:await retainGeographicArchives({archiveFiles,sourceId:release.source_id,request});
console.log(JSON.stringify({mode,published,bounded_batches:completed,migration_archives:retained}));

}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))await main();
