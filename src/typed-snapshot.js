/** Shared prepared/static/hosted semantics. Raw JSON remains separately retained;
 * decoding evidence never rewrites its source storage or creates inferred facts. */
import {assertJSONData} from './json-contract.js';
import {normalizeTypedObservation,normalizeTypedRelationship,resolveTypedObservations,supportedInterval} from './typed-observations.js';
import {observationContract,registryForDigest} from './observation-modules.js';
import {validateTypedDerivations,validateTypedGeography} from './typed-derivations.js';

export const canonicalTypedJSON=value=>JSON.stringify(canonical(value));
function canonical(value){return Array.isArray(value)?value.map(canonical):value&&typeof value==='object'?Object.fromEntries(Object.keys(value).sort().map(key=>[key,canonical(value[key])])):value;}
export function retainedTypedJSON(value,raw,label,{objectRequired=false}={}){
 assertJSONData(value,{objectRequired,maxBytes:1048576});
 if(raw===undefined)return JSON.stringify(value);
 if(typeof raw!=='string'||new TextEncoder().encode(raw).length>1048576)throw Error(`Invalid original ${label} JSON`);
 const parsed=JSON.parse(raw);assertJSONData(parsed,{objectRequired,maxBytes:1048576});
 if(canonicalTypedJSON(parsed)!==canonicalTypedJSON(value))throw Error(`Original ${label} JSON identifies different evidence`);
 return raw;
}
export function decodeTypedRow(collection,row){
 const metadata=typeof row.metadata==='string'?JSON.parse(row.metadata):row.metadata??{};
 const original_json={metadata:typeof row.metadata==='string'?row.metadata:retainedTypedJSON(metadata,row.original_json?.metadata,'metadata',{objectRequired:true})};
 const result={...row,metadata,original_json};
 if(collection==='observations'){
  result.value=typeof row.value==='string'?JSON.parse(row.value):row.value;
  // This helper decodes storage rows; public/pure inputs should already carry
  // original_json to distinguish a quoted identity string from JSON TEXT.
  original_json.value=typeof row.value==='string'?row.value:retainedTypedJSON(result.value,row.original_json?.value,'value');
 }
 if(collection!=='retirements')result.version=row.contract_version??row.version??1;
 return result;
}
export async function normalizeTypedEvidence(collection,row,context){
 if(!['observations','feature_links'].includes(collection)||row.contract_version!=null&&row.contract_version!==1)throw Error('Unsupported typed evidence contract');
 const registry=await registryForDigest(row.registry_sha256),metadata=row.metadata??{};
 const original_json={metadata:retainedTypedJSON(metadata,row.original_json?.metadata,'metadata',{objectRequired:true})};
 if(collection==='observations')original_json.value=retainedTypedJSON(row.value,row.original_json?.value,'value');
 const input={...row,metadata,original_json};
 return collection==='observations'?normalizeTypedObservation(input,context,registry):normalizeTypedRelationship(input,context,registry);
}
export function normalizeTypedRetirement(row,{sources,observations,feature_links},{requireReplacement=true}={}){
 assertJSONData(row,{objectRequired:true,maxBytes:1048576});
 const texts=['id','target_id','source_id','reason'];
 for(const key of texts)if(typeof row[key]!=='string'||!row[key].trim()||row[key].length>2000)throw Error('Invalid typed retirement identity/reason');
 if(!['observations','feature_links'].includes(row.collection))throw Error('Invalid typed retirement collection');
 const source=sources.find(source=>source.id===row.source_id),claims=row.collection==='observations'?observations:feature_links;
 const target=claims.find(claim=>claim.id===row.target_id);
 if(!source||!target||source.status==='example'&&!target.is_example)throw Error('Typed retirement lacks an allowed source/target');
 const replacement_id=row.replacement_id??null;
 if(replacement_id!==null){
  if(typeof replacement_id!=='string'||!replacement_id.trim()||replacement_id.length>2000||replacement_id===row.target_id)throw Error('Invalid typed replacement identity');
  const replacement=claims.find(claim=>claim.id===replacement_id);
  if(!replacement&&requireReplacement)throw Error('Typed replacement must exist in the atomic import');
  const identity=row.collection==='observations'?['subject_id','subject_kind','field_id']:['source_entity_id','target_entity_id','relationship_type'];
  if(replacement&&identity.some(key=>replacement[key]!==target[key]))throw Error('Typed correction cannot transfer evidence between subjects or fields');
 }
 const metadata=row.metadata??{},raw=retainedTypedJSON(metadata,row.original_json?.metadata,'retirement metadata',{objectRequired:true});
 return {...row,replacement_id,metadata,original_json:{metadata:raw}};
}
export async function resolveTypedSnapshot(input,year,{examples=false}={}){
 supportedInterval(year,year===-1?1:year+1);
 assertJSONData(input,{objectRequired:true,maxBytes:64*1024*1024});
 if(input.version!==1)throw Error('Unsupported typed snapshot version');
 const contract=await observationContract();
 if(input.registry_sha256!==contract.registry_sha256)throw Error('Typed snapshot has a different current registry');
 const collections=['sources','entities','observations','feature_links','retirements'];
 for(const key of collections)if(!Array.isArray(input[key])||input[key].length>100000)throw Error('Invalid typed snapshot collection');
 const context={sources:input.sources,entities:input.entities};
 const observations=[],links=[],retirements=[];
 for(const row of input.observations)observations.push(await normalizeTypedEvidence('observations',row,context));
 for(const row of input.feature_links)links.push(await normalizeTypedEvidence('feature_links',row,context));
 const derivations=new Map(observations.map(row=>[row.id,row]));
 for(const entry of input.derivation_inputs??[]){
  if(!['typed','legacy'].includes(entry.kind))throw Error('Unknown derivation input namespace');
  const row=entry.kind==='typed'?await normalizeTypedEvidence('observations',entry.row,context):entry.row;
  const existing=derivations.get(row.id);
  if(existing&&(entry.kind==='legacy'||canonicalTypedJSON(existing)!==canonicalTypedJSON(row)))throw Error('Ambiguous derivation input identity');
  derivations.set(row.id,row);
 }
 validateTypedDerivations([...observations,...links],derivations,input.sources);
 validateTypedGeography([...observations,...links,...derivations.values()],input.geography_pins);
 const seen=new Set(),targets=new Set(),retired={observations:[],feature_links:[]};
 for(const inputRow of input.retirements){
  const row=normalizeTypedRetirement(inputRow,{sources:input.sources,observations,feature_links:links},{requireReplacement:false});
  const target=JSON.stringify([row.collection,row.target_id]);
  if(seen.has(row.id)||targets.has(target))throw Error('Duplicate typed retirement identity or target');
  seen.add(row.id);targets.add(target);retired[row.collection].push(row.target_id);retirements.push(row);
 }
 const retiredLinks=new Set(retired.feature_links),linkIds=new Set();
 for(const row of links){if(linkIds.has(row.id))throw Error('Duplicate typed snapshot link identity');linkIds.add(row.id);}
 return {version:1,year,registry_sha256:contract.registry_sha256,
  observations:resolveTypedObservations(observations,year,{...context,retired_ids:retired.observations,examples,registry:contract.registry}),
  feature_links:links.filter(row=>!retiredLinks.has(row.id)&&row.valid_from<=year&&row.valid_to>year&&(!row.is_example||examples)).sort((a,b)=>a.id<b.id?-1:a.id>b.id?1:0),
  retirements,sources:input.sources,entities:input.entities};
}
