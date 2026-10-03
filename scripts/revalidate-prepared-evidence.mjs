import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {gunzipSync,gzipSync} from 'node:zlib';
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
export function revalidatePreparedEvidence({before='data',after,products=defaults,migrationReceipts=[],archiveDirectory,write=true}={}){
 if(!after)throw Error('An explicitly staged target geography is required');const old=geography(before),current=geography(after),receipts=[],archives=[];
 for(const product of products){
  const directory=product.directory??`${before}/${product.id}`,manifest=read(`${directory}/index.json`),proof=fs.existsSync(`${directory}/proof.json`)?read(`${directory}/proof.json`):{};
  const keys=Object.keys(old.proof),stale=[manifest,proof].some(input=>keys.some(key=>input[key]&&input[key]!==old.proof[key])),priorFile=`${directory}/revalidation.json`,prior=stale&&fs.existsSync(priorFile)?read(priorFile):null;
  if(prior&&(prior.version!==1||prior.historical_membership_assigned!==false||prior.records!==manifest.records||!Array.isArray(prior.entities)||!Array.isArray(prior.source_product_files)||keys.some(key=>! /^[a-f0-9]{64}$/.test(prior.original_geography?.[key]??'')||prior.revalidated_geography?.[key]!==old.proof[key])))throw Error('Previous evidence revalidation geography or contract is stale');
  for(const input of [manifest,proof])for(const key of keys)if(input[key]&&input[key]!== (prior?.original_geography??old.proof)[key])throw Error(`Original evidence geography is stale: ${product.id}/${key}`);
  const files=['index.json',...['proof.json','sources.json','categories.json','source-receipts.json','location-crosswalk.json','crosswalk.json.gz','unmatched.json.gz'].filter(f=>fs.existsSync(`${directory}/${f}`))],entities=new Set();let rows=0;
  for(const part of manifest.record_parts??manifest.parts){const name=typeof part==='string'?part:part.path;if(!name||path.isAbsolute(name)||name.split('/').includes('..'))throw Error('Unsafe evidence part path');const raw=fs.readFileSync(`${directory}/${name}`);if(part.sha256&&sha(raw)!==part.sha256)throw Error('Original producer part hash mismatch');const pin=proof.parts?.find(p=>p.path===name);if(pin&&(pin.sha256!==sha(raw)||pin.bytes!==raw.length))throw Error('Original producer proof bytes mismatch');files.push(name);for(const row of read(`${directory}/${name}`)){entities.add(product.kind==='names'?row.entity_id:row.location_id);rows++;}}
  if(rows!==manifest.records)throw Error('Original evidence record count mismatch');
  const sourceFiles=[...new Set(files)].sort().map(name=>({path:name,sha256:sha(fs.readFileSync(`${directory}/${name}`))}));
  const previousEntities=new Map(prior?.entities.map(row=>[row.entity_id,row])??[]);
  if(prior){
   if(previousEntities.size!==prior.entities.length||previousEntities.size!==entities.size||[...entities].some(id=>!previousEntities.has(id)))throw Error('Previous evidence entity inventory changed');
   if(prior.source_product_files.length!==sourceFiles.length||new Set(prior.source_product_files.map(file=>file.path)).size!==sourceFiles.length||sourceFiles.some(file=>!prior.source_product_files.some(oldFile=>oldFile.path===file.path&&oldFile.sha256===file.sha256)))throw Error('Previous evidence source bytes changed');
  }
  const checked=[...entities].sort().map(id=>{if(!old.entities.has(id)||!current.entities.has(id))throw Error(`Evidence identity removed or replaced: ${id}`);const a=old.footprint(id),b=current.footprint(id);if(a.kind!==b.kind||a.sha256!==b.sha256||a.members!==b.members)throw Error(`Evidence entity footprint changed: ${id}`);const previous=previousEntities.get(id);if(prior&&(previous.result!=='identical-footprint'||previous.kind!==a.kind||previous.member_locations!==a.members||previous.original_footprint_sha256!==a.sha256||previous.revalidated_footprint_sha256!==a.sha256))throw Error(`Previous evidence footprint proof differs: ${id}`);return {entity_id:id,kind:a.kind,member_locations:a.members,original_footprint_sha256:a.sha256,revalidated_footprint_sha256:b.sha256,result:'identical-footprint'};});
  let chained={};if(prior){
   if(!archiveDirectory||!product.id||/[\\/]/.test(product.id))throw Error('Chained evidence revalidation requires an explicit safe prior archive directory');
   const raw=fs.readFileSync(priorFile),packed=gzipSync(raw,{mtime:0}),file=path.resolve(archiveDirectory,`${product.id}-revalidation.json.archive.gz`);if(fs.existsSync(file)&&!fs.readFileSync(file).equals(packed))throw Error('Previous evidence archive would be overwritten');archives.push({file,packed});
   chained={prior_revalidation:{sha256:sha(raw),archive_path:path.relative(process.cwd(),file),archive_sha256:sha(packed),compression:'gzip',revalidated_geography:prior.revalidated_geography}};
  }
  receipts.push({product:product.id,directory,receipt:{...prior,version:1,revalidation_algorithm_sha256:sha(fs.readFileSync(fileURLToPath(import.meta.url))),scope:'Revalidation of immutable dated evidence against a revised reference geographic release; no historical membership or claim transfer',historical_membership_assigned:false,records:rows,original_geography:prior?.original_geography??old.proof,revalidated_geography:current.proof,source_product_files:prior?.source_product_files??sourceFiles,migration_receipts:[...(prior?.migration_receipts??[]),...migrationReceipts.map(file=>({path:file,sha256:sha(fs.readFileSync(file))}))],entities:checked,validation:['Every original identity retained at the same tier','Exact location geometries and all descendant location identities unchanged for every evidence entity','Original source, record, interval and executed-algorithm bytes preserved','Reference macro-parent changes do not establish dated administrative membership'],...chained}});
 }
 if(write){for(const {file,packed}of archives){fs.mkdirSync(path.dirname(file),{recursive:true});if(!fs.existsSync(file))fs.writeFileSync(file,packed,{flag:'wx'});}for(const {directory,receipt}of receipts){const file=`${directory}/revalidation.json`,temporary=`${file}.tmp-${process.pid}`;fs.writeFileSync(temporary,JSON.stringify(receipt,null,2)+'\n');fs.renameSync(temporary,file);}}
 return receipts.map(({product,receipt})=>({product,records:receipt.records,entities:receipt.entities.length,...receipt.revalidated_geography}));
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))console.log(JSON.stringify(revalidatePreparedEvidence({after:process.argv[2],migrationReceipts:process.argv.slice(3)})));
