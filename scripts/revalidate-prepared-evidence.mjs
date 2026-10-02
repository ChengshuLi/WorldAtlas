import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {footprintHash} from './check-prepared.mjs';
import {preparedEvidenceJSON} from '../src/prepared-evidence.js';
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const read=file=>JSON.parse(file.endsWith('.gz')?gunzipSync(fs.readFileSync(file)):fs.readFileSync(file));
const defaults=[{id:'dated-reference-names',kind:'names'},{id:'demographic-evidence',kind:'records'}];
function geography(data){
 const hierarchy=read(`${data}/hierarchy.json`),features=read(`${data}/world-index.json`).parts.flatMap(p=>read(`${data}/${p}`).features),units=new Map(hierarchy.map(u=>[u.id,u])),locations=new Map(features.map(f=>[f.id,f])),members=new Map();
 for(const f of features){let id=f.properties.parent_id,seen=new Set();while(id){if(seen.has(id)||!units.has(id))throw Error('Invalid parent chain during evidence revalidation');seen.add(id);if(!members.has(id))members.set(id,[]);members.get(id).push(f.id);id=units.get(id).parent_id;}}
 const footprint=id=>{const ids=locations.has(id)?[id]:members.get(id);if(!ids?.length)throw Error(`Evidence entity lacks a retained footprint: ${id}`);return {kind:locations.has(id)?'location':units.get(id).level,members:ids.length,sha256:sha(preparedEvidenceJSON(ids.sort().map(id=>[id,locations.get(id).geometry])))};};
 return {proof:{footprints_sha256:footprintHash(features),hierarchy_sha256:sha(fs.readFileSync(`${data}/hierarchy.json`)),location_index_sha256:sha(fs.readFileSync(`${data}/world-index.json`))},footprint,entities:new Set([...units.keys(),...locations.keys()])};
}
export function revalidatePreparedEvidence({before='data',after,products=defaults,migrationReceipts=[],write=true}={}){
 if(!after)throw Error('An explicitly staged target geography is required');const old=geography(before),current=geography(after),receipts=[];
 for(const product of products){
  const directory=product.directory??`${before}/${product.id}`,manifest=read(`${directory}/index.json`),proof=fs.existsSync(`${directory}/proof.json`)?read(`${directory}/proof.json`):{};
  for(const input of [manifest,proof])for(const key of ['footprints_sha256','hierarchy_sha256','location_index_sha256'])if(input[key]&&input[key]!==old.proof[key])throw Error(`Original evidence geography is stale: ${product.id}/${key}`);
  const files=['index.json',...['proof.json','sources.json','categories.json','source-receipts.json','location-crosswalk.json','crosswalk.json.gz','unmatched.json.gz'].filter(f=>fs.existsSync(`${directory}/${f}`))],entities=new Set();let rows=0;
  for(const part of manifest.record_parts??manifest.parts){const name=typeof part==='string'?part:part.path;if(!name||path.isAbsolute(name)||name.split('/').includes('..'))throw Error('Unsafe evidence part path');const raw=fs.readFileSync(`${directory}/${name}`);if(part.sha256&&sha(raw)!==part.sha256)throw Error('Original producer part hash mismatch');const pin=proof.parts?.find(p=>p.path===name);if(pin&&(pin.sha256!==sha(raw)||pin.bytes!==raw.length))throw Error('Original producer proof bytes mismatch');files.push(name);for(const row of read(`${directory}/${name}`)){entities.add(product.kind==='names'?row.entity_id:row.location_id);rows++;}}
  if(rows!==manifest.records)throw Error('Original evidence record count mismatch');
  const checked=[...entities].sort().map(id=>{if(!old.entities.has(id)||!current.entities.has(id))throw Error(`Evidence identity removed or replaced: ${id}`);const a=old.footprint(id),b=current.footprint(id);if(a.kind!==b.kind||a.sha256!==b.sha256||a.members!==b.members)throw Error(`Evidence entity footprint changed: ${id}`);return {entity_id:id,kind:a.kind,member_locations:a.members,original_footprint_sha256:a.sha256,revalidated_footprint_sha256:b.sha256,result:'identical-footprint'};});
  receipts.push({product:product.id,directory,receipt:{version:1,revalidation_algorithm_sha256:sha(fs.readFileSync(fileURLToPath(import.meta.url))),scope:'Revalidation of immutable dated evidence against a revised reference geographic release; no historical membership or claim transfer',historical_membership_assigned:false,records:rows,original_geography:old.proof,revalidated_geography:current.proof,source_product_files:[...new Set(files)].sort().map(name=>({path:name,sha256:sha(fs.readFileSync(`${directory}/${name}`))})),migration_receipts:migrationReceipts.map(file=>({path:file,sha256:sha(fs.readFileSync(file))})),entities:checked,validation:['Every original identity retained at the same tier','Exact location geometries and all descendant location identities unchanged for every evidence entity','Original source, record, interval and executed-algorithm bytes preserved','Reference macro-parent changes do not establish dated administrative membership']}});
 }
 if(write)for(const {directory,receipt}of receipts){const file=`${directory}/revalidation.json`,temporary=`${file}.tmp-${process.pid}`;fs.writeFileSync(temporary,JSON.stringify(receipt,null,2)+'\n');fs.renameSync(temporary,file);}
 return receipts.map(({product,receipt})=>({product,records:receipt.records,entities:receipt.entities.length,...receipt.revalidated_geography}));
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))console.log(JSON.stringify(revalidatePreparedEvidence({after:process.argv[2],migrationReceipts:process.argv.slice(3)})));
