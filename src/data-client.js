import {decodeReferences} from './reference-records.js';
import {preparedEvidencePartsAt,selectPreparedEvidence,verifyPreparedEvidencePart,verifyPreparedEvidenceIndexBytes,mergePreparedEvidence} from './prepared-evidence.js';
import {decodeDerived} from './derived-records.js';
import {runtimeOwnershipBucket,runtimeOwnershipData} from './runtime-ownership.js';
import {loadOwnershipAssets} from './ownership-assets.js';
import { validYear } from './model.js';
import { validateHierarchy } from './hierarchy.js';

const staticAtlas = import.meta.env.VITE_STATIC_ATLAS === 'true';
const hostedDatabase = import.meta.env.VITE_HOSTED_DATABASE === 'true';
let historyRequest;
const ownershipRequests=new Map();
let ownershipIndexRequest;
let referenceAttributeRequest;
let preparedEvidenceIndexRequest,preparedEvidenceProof;
const preparedEvidenceRequests=new Map();
async function loadPreparedEvidence(year,examples,signal){
 preparedEvidenceIndexRequest ||= fetch('./prepared-evidence/index.json').then(async response=>{if(!response.ok)throw Error(`Atlas evidence unavailable (${response.status})`);return verifyPreparedEvidenceIndexBytes(await response.arrayBuffer(),preparedEvidenceProof);}).catch(error=>{preparedEvidenceIndexRequest=null;throw error;});
 const index=await preparedEvidenceIndexRequest;signal?.throwIfAborted();const selected=preparedEvidencePartsAt(index,year);
 const parts=await Promise.all(selected.map(async part=>{if(!preparedEvidenceRequests.has(part.path))preparedEvidenceRequests.set(part.path,readJSON(`./prepared-evidence/${part.path}`).then(async rows=>{await verifyPreparedEvidencePart(part,rows);return rows;}).catch(error=>{preparedEvidenceRequests.delete(part.path);throw error;}));return {path:part.path,rows:await preparedEvidenceRequests.get(part.path)};}));
 const active=new Set(selected.map(p=>p.path));for(const key of preparedEvidenceRequests.keys())if(!active.has(key))preparedEvidenceRequests.delete(key);signal?.throwIfAborted();
 return selectPreparedEvidence(index,parts,year,{examples,expected:preparedEvidenceProof});
}
async function loadReferenceAttributes(year,signal){
 referenceAttributeRequest ||= readJSON("./reference-attributes/index.json").then(async index=>({index,parts:await Promise.all(index.parts.map(p=>readJSON(`./reference-attributes/${p}`)))})).catch(error=>{referenceAttributeRequest=null;throw error;});
 const {index,parts}=await referenceAttributeRequest;signal?.throwIfAborted();return decodeReferences(parts,index,year);
}

async function loadOwnershipHistory(year,signal){
 ownershipIndexRequest ||= readJSON('./ownership-runtime/index.json').catch(error=>{ownershipIndexRequest=null;throw error;});
 const index=await ownershipIndexRequest;signal?.throwIfAborted();
 const selected=runtimeOwnershipBucket(index,year);if(!selected)return [];
 if(!ownershipRequests.has(selected.path)){
  ownershipRequests.set(selected.path,readJSON(`./ownership-runtime/${selected.path}`).then(bucket=>runtimeOwnershipData(index,bucket,year)).catch(error=>{ownershipRequests.delete(selected.path);throw error;}));
  // Keep navigation between nearby dates cheap without retaining the entire history.
  while(ownershipRequests.size>2)ownershipRequests.delete(ownershipRequests.keys().next().value);
 }
 const data=await ownershipRequests.get(selected.path);signal?.throwIfAborted();
 return decodeDerived(data.parts,data.index,year);
}

class ContentRevisionError extends Error{constructor(){super('Historical content changed while reading');this.retryable=true;}}
async function loadHostedRecords(endpoint,year,examples,signal){
 if(!hostedDatabase)return {records:[],available:true,revision:null};
 try{
 const records=[];let cursor='',revision=null;const cursors=new Set();
 do{
  const params=new URLSearchParams({year:String(year),examples:String(Number(examples)),limit:'250',scope:'map'});if(cursor)params.set('cursor',cursor);
  const response=await fetch(endpoint+'?'+params,{signal});
  if(!response.ok){if(response.status===409&&(await response.json()).retryable)throw new ContentRevisionError();throw Error(`Atlas data unavailable (${response.status})`);}
  const page=await response.json();
  if(!Array.isArray(page.records)||!Number.isSafeInteger(page.revision))throw Error('Historical database returned an invalid page');
  if(revision!=null&&revision!==page.revision)throw new ContentRevisionError();revision=page.revision;
  records.push(...page.records);cursor=page.next_cursor||'';
  if(cursor&&cursors.has(cursor))throw Error('Historical database returned a repeated cursor');cursors.add(cursor);
 }while(cursor);
 return {records,available:true,revision};
 }catch(error){if(error.name==='AbortError'||signal?.aborted||error.retryable)throw error;return {records:[],available:false,revision:null};}
}
async function loadHostedMapEvidence(year,examples,signal){
 for(let attempt=0;attempt<3;attempt++){
  signal?.throwIfAborted();
  try{
   const pages=await Promise.all(['/api/attributes','/api/names','/api/retirements'].map(endpoint=>loadHostedRecords(endpoint,year,examples,signal)));
   const versions=new Set(pages.filter(p=>p.available&&p.revision!=null).map(p=>p.revision));
   if(versions.size>1)throw new ContentRevisionError();
   return {attributes:pages[0],names:pages[1],retirements:pages[2]};
  }catch(error){
   if(error.name==='AbortError'||signal?.aborted||!error.retryable)throw error;
   if(attempt===2)return {attributes:{records:[],available:false},names:{records:[],available:false},retirements:{records:[],available:false},unstable:true};
  }
 }
}

export async function readJSON(url, signal) {
  const response = await fetch(url, { signal });
  if (!response.ok) throw new Error(`Atlas data unavailable (${response.status})`);
  if(url.endsWith('.gz')){
    const bytes=new Uint8Array(await response.arrayBuffer());
    const raw=bytes[0]===31&&bytes[1]===139?await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).text():new TextDecoder().decode(bytes);
    return JSON.parse(raw);
  }
  return response.json();
}

export function selectRecords(records, year, examples) {
  const selected = new Map();
  for (const record of records) {
    if (record.valid_from > year || record.valid_to <= year || (record.is_example && !examples)) continue;
    const previous = selected.get(record.location_id);
    if (!previous || previous.is_example > record.is_example) selected.set(record.location_id, record);
  }
  return [...selected.values()];
}

export async function loadGeography() {
  const data=await readJSON(staticAtlas ? './atlas-geography.json' : '/api/geography');
  if(data.parts){const [features,ownership]=await Promise.all([Promise.all(data.parts.map(part=>readJSON(`./${part}`))).then(parts=>parts.flat()),data.pixelMap?loadOwnershipAssets(data.pixelMap):null]);data.features=features;data.ownership=ownership;}
  if(data.entityParts)data.temporal.entities=(await Promise.all(data.entityParts.map(p=>readJSON(`./${p}`)))).flat();
  if(data.temporalHistoryParts)data.temporal.history=(await Promise.all(data.temporalHistoryParts.map(p=>readJSON(`./${p}`)))).flat();
  validateHierarchy(data.units,data.features.map(f=>f.properties));
  preparedEvidenceProof=data.preparedEvidence;
  return data;
}

export async function loadSnapshot(year, examples, signal) {
  if (!validYear(year)) throw new Error('Invalid year');
  if (!staticAtlas) return readJSON(`/api/snapshot?year=${year}&examples=${Number(examples)}`, signal);
  // The immutable export is shared across requests; cancel the selection, not its download.
  historyRequest ||= readJSON('./atlas-history.json.gz').catch(error => { historyRequest = null; throw error; });
  const [history,derived,references,hostedMap,evidence] = await Promise.all([historyRequest,loadOwnershipHistory(year,signal),loadReferenceAttributes(year,signal),loadHostedMapEvidence(year,examples,signal),loadPreparedEvidence(year,examples,signal)]);
  signal?.throwIfAborted();
  const {attributes:hosted,names:temporal_history,retirements}=hostedMap;
  const merged=mergePreparedEvidence(hosted.records,temporal_history.records,evidence,{retirements:retirements.records});
  return { year, temporal_history:merged.names, storage:hostedDatabase?{available:hosted.available&&temporal_history.available&&retirements.available,...(hostedMap.unstable?{reason:'Historical content changed during loading; retry to load a consistent database snapshot'}:{})}:null, states: selectRecords(history.states, year, examples), boundaries: selectRecords(history.boundaries, year, examples), attributes:mergePreparedEvidence([...merged.records,...(history.attributes||[]).filter(r=>r.valid_from<=year&&r.valid_to>year&&(!r.is_example||examples))],[],{records:[...derived,...references],names:[]},{retirements:retirements.records}).records,polities:[] };
}

export async function ensureGeometry(data,signal){
  if(!data.geometryParts)return;
  data.geometryRequest ||= Promise.all(data.geometryParts.map(p=>readJSON(`./${p}`))).then(parts=>new Map(parts.flat().map(f=>[f.id,f.geometry]))).catch(error=>{data.geometryRequest=null;throw error;});
  const geometries=await data.geometryRequest;signal?.throwIfAborted();
  for(const f of data.features)f.geometry=geometries.get(f.id);
}
