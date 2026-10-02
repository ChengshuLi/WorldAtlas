import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {environmentClassifications} from '../src/environment-classifications.js';
const origin=new URL(process.argv[2]??'');
if(origin.protocol!=='https:'||origin.pathname!=='/'||origin.username||origin.password||origin.search||origin.hash)throw Error('Supply the confirmed HTTPS Site origin');
if(!process.stdin.isTTY)throw Error('Use hidden terminal stdin for the private service credential');
process.stdin.setRawMode(true);process.stdout.write('Ready for private read-only service credential on hidden stdin.\n');
const token=await new Promise((resolve,reject)=>{let value='';process.stdin.on('data',chunk=>{if(chunk.includes(3)){process.stdin.setRawMode(false);reject(Error('Cancelled'));return;}value+=chunk.toString();if(!/[\r\n]/.test(value))return;process.stdin.pause();process.stdin.setRawMode(false);try{resolve(JSON.parse(value.trim()).token);}catch{reject(Error('Invalid credential'));}});});
if(typeof token!=='string'||!token)throw Error('Missing credential');
async function get(route){const r=await fetch(new URL(route,origin),{headers:{'OAI-Sites-Authorization':`Bearer ${token}`}});if(!r.ok)throw Error(`Read-only verification HTTP ${r.status}`);return r.json();}
const classifications=await get('/api/classifications'),classificationCatalog={version:1,unknown:null,attributes:environmentClassifications};
if(JSON.stringify(classifications)!==JSON.stringify(classificationCatalog))throw Error('Published environmental classification catalog mismatch');
const classificationCounts=Object.fromEntries(Object.entries(classifications.attributes).map(([attribute,entries])=>[attribute,entries.length]));
const index=JSON.parse(fs.readFileSync('data/geographic-releases/index.json')),releases=[];
for(const expected of index.releases){const actual=await get('/api/geography/release?'+new URLSearchParams({release_id:expected.id}));for(const key of ['id','version','footprints_sha256','hierarchy_sha256','membership_sha256','location_ids_sha256','changes_sha256'])if(actual?.[key]!==expected[key])throw Error(`Published release mismatch: ${key}`);if(actual.status!=='published')throw Error('Unpublished release');for(const [key,value]of Object.entries(expected.expected_counts))if(actual.expected_counts[key]!==value)throw Error('Published counts mismatch');releases.push({id:actual.id,version:actual.version,counts:actual.expected_counts,footprints_sha256:actual.footprints_sha256,hierarchy_sha256:actual.hierarchy_sha256});}
const imports=JSON.parse(fs.readFileSync('data/prepared-evidence/imports/index.json')),expected={names:new Map(),records:new Map()};
for(const batch of imports.batches){const bytes=fs.readFileSync('data/prepared-evidence/imports/'+batch.path);if(createHash('sha256').update(bytes).digest('hex')!==batch.sha256)throw Error('Prepared import hash changed');const p=JSON.parse(bytes);for(const kind of ['names','records'])for(const row of p[kind]??[])expected[kind].set(row.id,row);}
let checked=0;const revisions=new Set();
for(const year of [2020,2021])for(const [collection,endpoint]of [['names','names'],['records','attributes']]){
 const seen=new Map();let cursor;
 do{const q=new URLSearchParams({year:String(year),scope:'map',limit:'500'});if(cursor)q.set('cursor',cursor);const page=await get('/api/'+endpoint+'?'+q);if(page.revision!==undefined)revisions.add(page.revision);for(const row of page.records){if(seen.has(row.id))throw Error('Duplicate paged evidence');seen.set(row.id,row);}cursor=page.next_cursor;}while(cursor);
 for(const row of expected[collection].values()){if(!(row.valid_from<=year&&year<row.valid_to))continue;const actual=seen.get(row.id);if(!actual)throw Error('Missing published prepared claim: '+row.id);for(const key of ['valid_from','valid_to','source_id','is_example'])if((actual[key]??0)!==(row[key]??0))throw Error('Published claim interval/source mismatch');if(collection==='names'){if(actual.entity_id!==row.entity_id||actual.value!==row.name)throw Error('Published dated name mismatch');}else{for(const key of ['location_id','attribute','value','category_id','method','status'])if((actual[key]??null)!==(row[key]??null))throw Error('Published scalar claim mismatch: '+key);}if(!actual.source||!actual.source_license)throw Error('Published evidence lacks provenance');checked++;}
}
if(revisions.size>1)throw Error('Storage changed during read-only verification; retry after imports finish');
const storage=await get('/api/storage');
const archiveReceiptFile='data/validation/geographic-release-bootstrap-2026-10-02.json';
let checkedArchiveObjects=0,checkedArchiveBytes=0;
if(fs.existsSync(archiveReceiptFile)){
 const receipt=JSON.parse(fs.readFileSync(archiveReceiptFile)),objects=new Map(receipt.migration_archives.map(row=>[row.id,row]));
 const catalog=JSON.parse(fs.readFileSync('data/hosted-catalog/index.json'));
 objects.set('media:atlas:archive:'+catalog.archive_sha256,{sha256:catalog.archive_sha256,bytes:fs.statSync('data/geographic-migration-archive.json.gz').size});
 for(const [id,expected]of objects){const response=await fetch(new URL('/api/media/'+encodeURIComponent(id),origin),{headers:{'OAI-Sites-Authorization':`Bearer ${token}`}});if(!response.ok)throw Error('Retained archive read-back failed');const raw=Buffer.from(await response.arrayBuffer());if(raw.length!==expected.bytes||createHash('sha256').update(raw).digest('hex')!==expected.sha256)throw Error('Retained archive bytes differ from preserved source');checkedArchiveObjects++;checkedArchiveBytes+=raw.length;}
}
const verification={read_only:true,verified_at_utc:new Date().toISOString(),url:origin.origin,environment_classifications:classificationCounts,releases,checked_prepared_claims:checked,expected_prepared_counts:imports.counts,checked_archive_objects:checkedArchiveObjects,checked_archive_bytes:checkedArchiveBytes,storage};
if(process.argv[3])fs.writeFileSync(process.argv[3],JSON.stringify(verification,null,2)+"\n");
console.log(JSON.stringify(verification));
