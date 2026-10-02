import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {previewImport} from '../src/import-records.js';

export const researchCollections=['sources','entity_types','entities','categories','records','names','relationships','media_links','retirements'];
export const researchHash=bytes=>createHash('sha256').update(bytes).digest('hex');
export const researchJSON=value=>JSON.stringify(Array.isArray(value)?value.map(canonical):canonical(value));
function canonical(value){return value&&typeof value==='object'&&!Array.isArray(value)?Object.fromEntries(Object.keys(value).sort().map(key=>[key,canonical(value[key])])):Array.isArray(value)?value.map(canonical):value;}
const compare=(a,b)=>a.id<b.id?-1:a.id>b.id?1:0;
function text(value,label){if(typeof value!=='string'||!value.trim())throw Error(`${label} must be nonempty text`);}
export function validateResearchGeography(release){
 if(!release||typeof release!=='object'||release.status!=='published')throw Error('Use a published geographic release, saved from /api/geography/release');
 text(release.id,'Geographic release ID');
 for(const key of ['footprints_sha256','hierarchy_sha256'])if(!/^[a-f0-9]{64}$/.test(release[key]))throw Error(`Invalid geographic ${key}`);
 return {id:release.id,status:'published',footprints_sha256:release.footprints_sha256,hierarchy_sha256:release.hierarchy_sha256};
}
function validateRows(input){
 if(!input||typeof input!=='object'||Array.isArray(input))throw Error('Research input must contain JSON collections');
 const collections={};
 for(const [kind,rows]of Object.entries(input)){
  if(kind==='ingestion_id')continue;
  if(!researchCollections.includes(kind)||!Array.isArray(rows))throw Error(`Unsupported research collection: ${kind}`);
  const seen=new Set();collections[kind]=rows.map(row=>{
   previewImport(researchJSON({[kind]:[row]}));
   if(seen.has(row.id))throw Error(`Duplicate ${kind} identity: ${row.id}`);seen.add(row.id);
   if(row.metadata!=null&&(!row.metadata||typeof row.metadata!=='object'||Array.isArray(row.metadata)||JSON.stringify(row.metadata).length>16384))throw Error(`Invalid or oversized metadata: ${row.id}`);
   if(kind==='sources'){
    if(row.url!=null){const url=new URL(row.url);if(!['https:','http:'].includes(url.protocol))throw Error(`Invalid source URL: ${row.id}`);}
   }
   if(kind==='categories'&&!['owner','culture','religion'].includes(row.kind))throw Error(`Invalid category kind: ${row.id}`);
   if(kind==='entities'){
    text(row.kind??row.level,`Entity kind for ${row.id}`);text(row.name,`Entity name for ${row.id}`);
    if(['location','province','area','region','subcontinent','continent'].includes(row.kind??row.level))throw Error('Research imports cannot add or change reference geographic entities; use existing IDs');
   }
   if(kind==='entity_types'){
    text(row.name,`Entity type name for ${row.id}`);
    if(row.geographic_level!=null||['location','province','area','region','subcontinent','continent'].includes(row.id))throw Error('Research imports cannot define geographic tiers');
   }
   if(kind==='names'){
    if(row.role!=null&&!['preferred','alias'].includes(row.role))throw Error(`Invalid name role: ${row.id}`);
   }
   if(kind==='relationships'){text(row.source_entity_id,'Relationship source identity');text(row.target_entity_id,'Relationship target identity');text(row.relationship_type,'Relationship type');}
   if(kind==='media_links'){text(row.entity_id,'Media entity identity');text(row.media_id,'Media identity');text(row.role,'Media role');}
   if(kind==='records'){
    if(row.method!=null&&!['direct','derived','majority-area','reference','estimate'].includes(row.method))throw Error(`Invalid evidence method: ${row.id}`);
    if(row.status!=null&&!['sourced','derived','reference','estimate','unknown','disputed','no-majority','example'].includes(row.status))throw Error(`Invalid evidence status: ${row.id}`);
   }
   return row;
  }).sort(compare);
 }
 const sources=new Map((collections.sources??[]).map(row=>[row.id,row]));
 for(const kind of ['records','names','relationships','media_links'])for(const row of collections[kind]??[]){
  const source=sources.get(row.source_id);if(!source)continue;
  const from=source.supported_from??source.valid_from,to=source.supported_to??source.valid_to;
  if(row.valid_from!=null&&(row.valid_from<from||row.valid_to>to))throw Error(`Claim exceeds source interval: ${row.id}`);
  if(source.status==='example'&&!row.is_example)throw Error(`Example source requires opt-in evidence: ${row.id}`);
  if(kind==='records'&&['reference','estimate'].includes(source.status)&&(row.method??'direct')!==source.status)throw Error(`Source class must match evidence method: ${row.id}`);
 }
 const categories=new Map((collections.categories??[]).map(row=>[row.id,row]));
 for(const row of collections.records??[])if(row.category_id&&categories.has(row.category_id)&&categories.get(row.category_id).kind!==row.attribute)throw Error(`Category kind does not match attribute: ${row.id}`);
 return collections;
}
function orderedEntities(rows){
 const pending=new Map(rows.map(row=>[row.id,row])),result=[];
 while(pending.size){const ready=[...pending.values()].filter(row=>!row.parent_id||!pending.has(row.parent_id)).sort(compare);if(!ready.length)throw Error('Entity parent cycle');for(const row of ready){pending.delete(row.id);result.push(row);}}
 return result;
}
export function compileResearchInput(input,release){
 const geography=validateResearchGeography(release),collections=validateRows(input),counts=Object.fromEntries(researchCollections.map(kind=>[kind,collections[kind]?.length??0]));
 if(!Object.values(counts).some(Boolean))throw Error('Research input contains no rows');
 collections.entities=orderedEntities(collections.entities??[]);
 const replacements=new Map(),correctionGroups=new Map(),claimMaps=new Map(['records','names','relationships','media_links'].map(kind=>[kind,new Map((collections[kind]??[]).map(row=>[row.id,row]))]));
 for(const row of collections.retirements??[]){
  const key=`${row.collection}/${row.replacement_id}`,replacement=row.replacement_id?claimMaps.get(row.collection)?.get(row.replacement_id):null;
  if(replacement)replacements.set(key,true);
  const groupKey=replacement?key:`retirement/${row.id}`;
  if(!correctionGroups.has(groupKey))correctionGroups.set(groupKey,{retirements:[],...(replacement?{[row.collection]:[replacement]}:{})});
  correctionGroups.get(groupKey).retirements.push(row);
 }
 const groups=[];
 for(const kind of researchCollections.filter(kind=>kind!=='retirements'))for(const row of collections[kind]??[])if(!replacements.has(`${kind}/${row.id}`))groups.push({[kind]:[row]});
 const batches=[];let pending={},size=0;
 function payload(rows){return {...rows,ingestion_id:`research:${researchHash(researchJSON(rows))}`};}
 function flush(){if(!size)return;const value=payload(pending),bytes=Buffer.from(researchJSON(value));previewImport(bytes.toString());batches.push({payload:value,bytes,rows:size,sha256:researchHash(bytes)});pending={};size=0;}
 function add(group){
  const added=Object.values(group).reduce((sum,rows)=>sum+rows.length,0);
  // Merge explicitly: a correction and its replacement always stay atomic.
  const candidate={...pending};for(const [kind,rows]of Object.entries(group))candidate[kind]=[...(candidate[kind]??[]),...rows];
  if(size&& (size+added>200||Buffer.byteLength(researchJSON(payload(candidate)))>1048576))flush();
  for(const [kind,rows]of Object.entries(group))pending[kind]=[...(pending[kind]??[]),...rows];size+=added;
  if(size>200||Buffer.byteLength(researchJSON(payload(pending)))>1048576)throw Error('An atomic correction or single row exceeds the import budget');
 }
 for(const group of groups)add(group);
 // The service inserts retirements before replacement claims. A newly imported
 // target must already have committed, rather than sharing its first batch.
 flush();
 // Chained corrections must commit the earlier replacement before retiring it.
 while(correctionGroups.size){
  const remainingReplacements=new Set([...correctionGroups.values()].flatMap(group=>Object.entries(group).filter(([kind])=>kind!=='retirements').flatMap(([kind,rows])=>rows.map(row=>`${kind}/${row.id}`))));
  const ready=[...correctionGroups.entries()].filter(([,group])=>group.retirements.every(row=>!remainingReplacements.has(`${row.collection}/${row.target_id}`))).sort((a,b)=>compare(a[1].retirements[0],b[1].retirements[0]));
  if(!ready.length)throw Error('Correction replacement dependency cycle');
  for(const [key,group]of ready){add(group);flush();correctionGroups.delete(key);}
 }
 flush();return {geography,counts,batches};
}
export function prepareResearchBundle({input,geography,output,sourceFiles=[]}){
 const original=fs.readFileSync(input),release=typeof geography==='string'?JSON.parse(fs.readFileSync(geography)):geography,result=compileResearchInput(JSON.parse(original),release);
 if(fs.existsSync(output))throw Error('Output directory already exists; preserve completed bundles and choose a new directory');
 const staging=`${output}.staging-${process.pid}`;fs.mkdirSync(path.join(staging,'batches'),{recursive:true});
 try{
  fs.writeFileSync(path.join(staging,'input.json'),original);const manifest={version:1,kind:'research-content',geography:result.geography,input:{path:'input.json',sha256:researchHash(original),bytes:original.length},counts:result.counts,source_files:[],batches:[],preflight:'Local syntax, classification, input-source bounds and byte validation; the server remains authoritative for existing identities, conflicts and transactions.'};
  for(const [number,batch]of result.batches.entries()){const name=`batches/batch-${String(number).padStart(6,'0')}.json`;fs.writeFileSync(path.join(staging,name),batch.bytes);manifest.batches.push({path:name,sha256:batch.sha256,bytes:batch.bytes.length,rows:batch.rows,ingestion_id:batch.payload.ingestion_id});}
  for(const file of sourceFiles){
   if(file.redistribution_permitted!==true)throw Error('Source archive requires explicit redistribution_permitted: true');text(file.license,'Source file license');text(file.source_id,'Source file source_id');
   const source=path.resolve(path.dirname(input),file.path),bytes=fs.readFileSync(source),sha256=researchHash(bytes),name=`source-files/${sha256}.bin`;
   fs.mkdirSync(path.join(staging,'source-files'),{recursive:true});fs.writeFileSync(path.join(staging,name),bytes);manifest.source_files.push({path:name,original_name:path.basename(source),sha256,bytes:bytes.length,license:file.license,source_id:file.source_id,redistribution_permitted:true});
  }
  fs.writeFileSync(path.join(staging,'index.json'),JSON.stringify(manifest,null,2)+'\n');fs.mkdirSync(path.dirname(output),{recursive:true});fs.renameSync(staging,output);return manifest;
 }catch(error){fs.rmSync(staging,{recursive:true,force:true});throw error;}
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const [input,geography,output,sourceFileList]=process.argv.slice(2);
 if(!input||!geography||!output)throw Error('Usage: node scripts/prepare-research-bundle.mjs input.json geographic-release.json output-directory [licensed-source-files.json]');
 const manifest=prepareResearchBundle({input,geography,output,sourceFiles:sourceFileList?JSON.parse(fs.readFileSync(sourceFileList)):[]});console.log(JSON.stringify({counts:manifest.counts,batches:manifest.batches.length,input_sha256:manifest.input.sha256,output}));
}
