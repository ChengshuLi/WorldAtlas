import {RecordError} from './records.js';
import {storageCatalogV3,exportStorageMarkerV3} from './storage-export-v3.js';
import {storageExportV3Definitions as storage} from './storage-export-v3-contract.js';
import {assertJSONData} from '../src/json-contract.js';
import {observationContract,observationDigest,registryForDigest} from '../src/observation-modules.js';
import {canonicalTypedJSON,decodeTypedRow,normalizeTypedEvidence,normalizeTypedRetirement} from '../src/typed-snapshot.js';
import {assertResearchBundleApproved} from '../src/regional-import-gate.js';
import {derivationInputIds,validateTypedDerivations} from '../src/typed-derivations.js';
import researchGate from '../data/research-geography-gate.json' with {type:'json'};

const definitions={observations:storage.typed_observations,feature_links:storage.typed_feature_links,retirements:storage.typed_retirements};
const fail=(message,status=400)=>{throw new RecordError(message,status);};
const text=(value,label)=>{if(typeof value!=='string'||!value.trim()||value.length>2000)fail(`Invalid ${label}`);return value;};
const rows=async statement=>(await statement.all()).results??[];
const revision=async db=>(await db.prepare('SELECT coalesce(max(rowid),0) revision FROM atlas_ingestions').first()).revision;
const publicCounts=counts=>Object.fromEntries(Object.entries(counts).filter(([key])=>!key.startsWith('_')));
const insert=(db,collection,row)=>{const d=definitions[collection];return db.prepare(`INSERT OR IGNORE INTO ${d.table} (${d.columns.join(',')}) VALUES (${d.columns.map(()=>'?').join(',')})`).bind(...d.columns.map(key=>row[key]??null));};
const stored=(collection,row)=>({...row,contract_version:1,metadata:row.original_json.metadata,...(collection==='observations'?{value:row.original_json.value}:{})});
const cleanCatalog=row=>({...row,metadata:JSON.parse(row.metadata),original_metadata_json:row.metadata});
async function byIds(db,table,ids){
 const unique=[...new Set(ids)].sort(),result=[];if(unique.length>4096)fail('Typed batch references too many identities; split the batch',413);
 for(let i=0;i<unique.length;i+=64){const chunk=unique.slice(i,i+64);chunk.forEach(id=>text(id,'catalog identity'));result.push(...await rows(db.prepare(`SELECT * FROM ${table} WHERE id IN (${chunk.map(()=>'?').join(',')}) ORDER BY id`).bind(...chunk)));}
 return result;
}
function endpointIds(collection,row,registry){
 if(collection==='feature_links')return [row.source_entity_id,row.target_entity_id];
 const ids=[row.subject_id],field=registry.fields[row.field_id];
 if(field?.value_type==='identity'&&row.value!==null)ids.push(row.value);
 if(field?.value_type==='identity-list'&&Array.isArray(row.value))ids.push(...row.value);
 return ids;
}
export async function typedSourcePins(sources){
 return Promise.all(sources.map(async row=>({id:row.id,sha256:await observationDigest(storage.sources.columns.map(key=>row[key]))})));
}
export async function typedCapabilities(db){
 const contract=await observationContract();
 try{await storageCatalogV3(db);return {version:1,typed_observations:1,typed_feature_links:1,storage_export:3,registry_sha256:contract.registry_sha256,supported_registry_sha256:contract.supported_registry_sha256};}
 catch(error){if(error.status!==503&&!/no such table|does not exist|schema|guards/i.test(error.message))throw error;return {version:1,typed_observations:0,typed_feature_links:0,storage_export:0,reason:'typed-schema-uninstalled-or-unverified',registry_sha256:contract.registry_sha256};}
}
export async function typedRegistry(db){await storageCatalogV3(db);const contract=await observationContract();return {version:1,registry_sha256:contract.registry_sha256,registry:contract.registry,supported_registry_sha256:contract.supported_registry_sha256};}

function geographyPins(value){
 if(!value||Object.keys(value).sort().join(',')!=='footprints_sha256,hierarchy_sha256,release_id')fail('Typed imports require exact published geography pins');
 text(value.release_id,'release ID');for(const key of ['hierarchy_sha256','footprints_sha256'])if(!/^[a-f0-9]{64}$/.test(value[key]??''))fail('Invalid published geography hash');return value;
}
function geographyGuard(db,pins,id,fingerprint){
 const condition="EXISTS(SELECT 1 FROM atlas_ingestions WHERE id=? AND fingerprint=?) OR EXISTS(SELECT 1 FROM atlas_geographic_releases g WHERE g.id=? AND g.hierarchy_sha256=? AND g.footprints_sha256=? AND g.status='published' AND NOT EXISTS(SELECT 1 FROM atlas_geographic_releases newer WHERE newer.status='published' AND newer.version>g.version))";
 const value=`CASE WHEN ${condition} THEN 'true' ELSE 'ATLAS_TYPED_GEOGRAPHY_CONFLICT' END`;
 return db.prepare(db.dialect==='postgres'?`SELECT CAST(${value} AS boolean) AS matches`:`SELECT json_extract(${value},'$') AS matches`).bind(id,fingerprint,pins.release_id,pins.hierarchy_sha256,pins.footprints_sha256);
}
async function catalogContext(db,collections,contract){
 const retained={observations:[],feature_links:[]};
 for(const collection of Object.keys(retained)){
  const ids=(collections.retirements??[]).filter(row=>row.collection===collection).flatMap(row=>[row.target_id,...(row.replacement_id?[row.replacement_id]:[])]);
  retained[collection]=(await byIds(db,definitions[collection].table,ids)).map(row=>decodeTypedRow(collection,row));
 }
 const evidence=[...collections.observations.map(row=>['observations',row]),...collections.feature_links.map(row=>['feature_links',row]),...retained.observations.map(row=>['observations',row]),...retained.feature_links.map(row=>['feature_links',row])];
 const entityIds=[],sourceIds=collections.retirements.map(row=>row.source_id);
 const derivations=new Map(),scanned=new Set();
 let pending=evidence.map(([,row])=>row);
 for(let depth=0;pending.length;depth++){
  if(depth>64)fail('Derivation chain exceeds 64 levels',413);
  const requested=[...new Set(pending.flatMap(derivationInputIds))].filter(id=>!scanned.has(id));
  requested.forEach(id=>scanned.add(id));if(scanned.size>4096)fail('Derivation closure exceeds 4096 identities',413);
  const typed=await byIds(db,definitions.observations.table,requested),legacy=await byIds(db,storage.records.table,requested);
  pending=[];
  for(const id of requested){
   const incoming=collections.observations.find(row=>row.id===id),retainedTyped=typed.find(row=>row.id===id),retainedLegacy=legacy.find(row=>row.id===id);
   if((incoming||retainedTyped)&&retainedLegacy||!incoming&&!retainedTyped&&!retainedLegacy)fail('Derivation input is absent or ambiguous',409);
   const row=incoming??(retainedTyped?decodeTypedRow('observations',retainedTyped):{...retainedLegacy,metadata:JSON.parse(retainedLegacy.metadata)});
   derivations.set(id,{row,typed:Boolean(incoming||retainedTyped)});pending.push(row);
  }
 }
 for(const [collection,row] of evidence){const registry=await registryForDigest(row.registry_sha256);entityIds.push(...endpointIds(collection,row,registry));sourceIds.push(row.source_id);}
 for(const {row,typed} of derivations.values()){
  sourceIds.push(row.source_id);entityIds.push(...(typed?endpointIds('observations',row,await registryForDigest(row.registry_sha256)):[row.location_id]));
 }
 const rawSources=await byIds(db,storage.sources.table,sourceIds),entities=await byIds(db,storage.entities.table,entityIds);
 const context={sources:rawSources.map(cleanCatalog),entities:entities.map(cleanCatalog),rawSources,retained,derivations};
 for(const collection of ['observations','feature_links'])for(let i=0;i<retained[collection].length;i++)retained[collection][i]=await normalizeTypedEvidence(collection,retained[collection][i],context);
 for(const [id,input] of derivations)if(input.typed)derivations.set(id,{...input,row:await normalizeTypedEvidence('observations',input.row,context)});
 return context;
}

/** New, bounded typed-only protocol. Existing records/import schemas stay intact.
 * Approval is compiled trusted data, never a certificate supplied by a caller. */
export async function importTypedBatch(db,payload,options={}){
 try{return await importTypedBatchCore(db,payload,options);}
 catch(error){if(error instanceof RecordError||error.status)throw error;throw new RecordError(error.message,400);}
}
async function importTypedBatchCore(db,payload,{gate=researchGate}={}){
 assertJSONData(payload,{objectRequired:true,maxBytes:1048576});
 const allowed=['version','registry_sha256','ingestion_id','expected_geography','region_ids','source_pins','examples','observations','feature_links','retirements'];
 if(Object.keys(payload).some(key=>!allowed.includes(key))||payload.version!==1)fail('Unsupported typed import envelope');
 if(payload.examples!=null&&typeof payload.examples!=='boolean')fail('Invalid example opt-in');
 const contract=await observationContract();await registryForDigest(payload.registry_sha256);await storageCatalogV3(db);
 const fingerprint=await observationDigest(JSON.parse(canonicalTypedJSON(payload))),id=payload.ingestion_id==null?`typed:${fingerprint}`:text(payload.ingestion_id,'ingestion ID');
 const prior=await db.prepare('SELECT * FROM atlas_ingestions WHERE id=?').bind(id).first();
 if(prior){if(prior.fingerprint!==fingerprint)fail('Ingestion ID identifies different typed evidence or context',409);const counts=JSON.parse(prior.counts);return {version:1,ingestion_id:id,duplicate:true,counts:publicCounts(counts),registry_sha256:counts._typed_registry_sha256,expected_geography:counts._expected_geography,revision:await revision(db)};}
 if(payload.registry_sha256!==contract.registry_sha256)fail('New typed imports must pin the current controlled registry',409);
 const pins=geographyPins(payload.expected_geography),collections={};
 for(const key of Object.keys(definitions)){
  const values=payload[key]??[];if(!Array.isArray(values))fail('Typed collections must be arrays');
  for(const row of values){text(row?.id,'typed identity');text(row?.source_id,'source identity');}
  if(new Set(values.map(row=>row.id)).size!==values.length)fail('Duplicate typed import identity');
  if(key!=='retirements'&&values.some(row=>row.registry_sha256!=null&&row.registry_sha256!==payload.registry_sha256))fail('Row and envelope registry pins differ',409);
  collections[key]=key==='retirements'?values:values.map(row=>({...row,registry_sha256:payload.registry_sha256}));
 }
 const count=Object.values(collections).reduce((sum,rows)=>sum+rows.length,0);if(count<1||count>200)fail('Typed imports require 1–200 evidence rows');
 const context=await catalogContext(db,collections,contract),normalized={observations:[],feature_links:[],retirements:[]};
 for(const collection of ['observations','feature_links'])for(const input of collections[collection]){
  const row=await normalizeTypedEvidence(collection,{...input,registry_sha256:payload.registry_sha256},context);
  if(row.is_example&&!payload.examples)fail('Example evidence requires explicit batch opt-in');normalized[collection].push(row);
 }
 const allClaims={sources:context.sources,observations:[...context.retained.observations,...normalized.observations],feature_links:[...context.retained.feature_links,...normalized.feature_links]};
 for(const input of collections.retirements)normalized.retirements.push(normalizeTypedRetirement(input,allClaims));
 const expectedPins=await typedSourcePins(context.rawSources);
 if(!Array.isArray(payload.source_pins)||payload.source_pins.length!==expectedPins.length||new Set(payload.source_pins.map(row=>row?.id)).size!==expectedPins.length||expectedPins.some(expected=>!payload.source_pins.some(row=>row?.id===expected.id&&row.sha256===expected.sha256)))fail('Typed import must pin original source catalog bytes',409);
 const factualSubjects=new Set(validateTypedDerivations([...normalized.observations,...normalized.feature_links,...context.retained.observations,...context.retained.feature_links],new Map([...context.derivations].map(([id,input])=>[id,input.row])),context.sources));
 for(const collection of ['observations','feature_links'])for(const row of normalized[collection])if(!row.is_example){const ids=collection==='observations'?[row.subject_id]:[row.source_entity_id,row.target_entity_id];ids.forEach(id=>factualSubjects.add(id));}
 for(const row of normalized.retirements){const target=allClaims[row.collection].find(target=>target.id===row.target_id);if(target.is_example&&!payload.examples)fail('Example retirement requires explicit batch opt-in');if(!target.is_example){const ids=row.collection==='observations'?[target.subject_id]:[target.source_entity_id,target.target_entity_id];ids.forEach(id=>factualSubjects.add(id));}}
 if(factualSubjects.size){if(gate.version!==2)fail('Typed factual imports require complete regional certificates',409);try{assertResearchBundleApproved(gate,pins,{regionIds:payload.region_ids,subjectIds:[...factualSubjects]});}catch(error){fail(error.message,409);}}
 const statements=[geographyGuard(db,pins,id,fingerprint)],counts={};
 for(const collection of ['retirements','observations','feature_links']){counts[collection]=normalized[collection].length;for(const row of normalized[collection])statements.push(insert(db,collection,stored(collection,row)));}
 statements.push(db.prepare('INSERT OR IGNORE INTO atlas_ingestions(id,fingerprint,counts,created_at) VALUES(?,?,?,?)').bind(id,fingerprint,canonicalTypedJSON({...counts,_typed_registry_sha256:contract.registry_sha256,_expected_geography:pins}),Date.now()));
 try{const result=await db.batch(statements);return {version:1,ingestion_id:id,duplicate:result.at(-1)?.meta?.changes===0,counts,registry_sha256:contract.registry_sha256,expected_geography:pins,revision:await revision(db)};}
 catch(error){if(error.commit_status==='unknown'){const failure=new RecordError('Typed import outcome is unknown; retry the identical ingestion to verify its retained receipt',503);failure.retryable=true;failure.commit_status='unknown';throw failure;}const failure=new RecordError('Typed import rejected; no partial batch may be used',error.retryable?503:409);if(error.retryable||error.sqlstate==='22P02'||/ATLAS_TYPED_GEOGRAPHY_CONFLICT|malformed JSON/i.test(error.message))failure.retryable=true;throw failure;}
}

function encodeCursor(value){let raw='';for(const byte of new TextEncoder().encode(JSON.stringify(value)))raw+=String.fromCharCode(byte);return btoa(raw);}
function decodeCursor(value){try{return JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(value),char=>char.charCodeAt(0))));}catch{fail('Invalid typed snapshot cursor');}}
export async function typedSnapshotPage(db,year,options={}){
 try{return await typedSnapshotPageCore(db,year,options);}
 catch(error){if(error instanceof RecordError||error.status)throw error;throw new RecordError('Retained typed evidence fails its controlled contract',503);}
}
async function typedSnapshotPageCore(db,year,{stream='observations',examples=false,cursor='',limit=100}={}){
 const {validYear}=await import('../src/model.js');
 if(!validYear(year)||!Object.hasOwn(definitions,stream)||!Number.isSafeInteger(limit)||limit<1||limit>200)fail('Invalid typed snapshot request');
 const contract=await observationContract(),marker=await exportStorageMarkerV3(db),enabled=Number(Boolean(examples));let after='';
 if(cursor){const prior=decodeCursor(cursor);if(prior.version!==1||prior.year!==year||prior.stream!==stream||prior.examples!==enabled||typeof prior.after!=='string')fail('Typed cursor identifies another snapshot');if(prior.fingerprint!==marker.fingerprint||prior.registry_sha256!==contract.registry_sha256)fail('Typed snapshot changed; restart all streams',409);after=prior.after;text(after,'snapshot cursor identity');}
 const where=stream==='retirements'?"((c.collection='observations' AND EXISTS(SELECT 1 FROM atlas_typed_observations target WHERE target.id=c.target_id AND target.valid_from<=? AND target.valid_to>? AND target.is_example<=?)) OR (c.collection='feature_links' AND EXISTS(SELECT 1 FROM atlas_typed_feature_links target WHERE target.id=c.target_id AND target.valid_from<=? AND target.valid_to>? AND target.is_example<=?)))":"c.valid_from<=? AND c.valid_to>? AND c.is_example<=?";
 const args=stream==='retirements'?[year,year,enabled,year,year,enabled]:[year,year,enabled],d=definitions[stream];
 const total=(await db.prepare(`SELECT count(*) n FROM ${d.table} c WHERE ${where}`).bind(...args).first()).n;
 const found=await rows(db.prepare(`SELECT c.* FROM ${d.table} c WHERE ${where} AND c.id>? ORDER BY c.id LIMIT ?`).bind(...args,after,limit+1)),selected=found.slice(0,limit).map(row=>decodeTypedRow(stream,row));
 const collections={observations:[],feature_links:[],retirements:[]};collections[stream]=selected;
 const context=await catalogContext(db,collections,contract);
 // Every public claim is normalized using its retained registry vintage; never
 // quietly return malformed evidence or reinterpret an old definition.
 if(stream!=='retirements')for(let i=0;i<selected.length;i++)selected[i]=await normalizeTypedEvidence(stream,selected[i],context);
 else for(let i=0;i<selected.length;i++)selected[i]=normalizeTypedRetirement(selected[i],{sources:context.sources,...context.retained},{requireReplacement:false});
 validateTypedDerivations(stream==='retirements'?[...context.retained.observations,...context.retained.feature_links]:selected,new Map([...context.derivations].map(([id,input])=>[id,input.row])),context.sources);
 const afterMarker=await exportStorageMarkerV3(db);if(marker.fingerprint!==afterMarker.fingerprint)fail('Typed evidence changed during loading; restart all streams',409);
 const result={version:1,year,stream,examples:enabled,registry_sha256:contract.registry_sha256,fingerprint:marker.fingerprint,revision:marker.revision,total,rows:selected,sources:context.sources,entities:context.entities,source_pins:await typedSourcePins(context.rawSources),next_cursor:found.length>limit?encodeCursor({version:1,year,stream,examples:enabled,after:selected.at(-1).id,fingerprint:marker.fingerprint,registry_sha256:contract.registry_sha256}):null};
 if(new TextEncoder().encode(JSON.stringify(result)).length>8*1024*1024){const error=new RecordError('Typed snapshot page exceeds8 MiB; retry a smaller limit',413);error.retryable=true;error.suggested_limit=Math.max(1,Math.floor(limit/2));throw error;}return result;
}
