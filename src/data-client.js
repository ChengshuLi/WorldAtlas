import {hydrateMapSnapshotPage} from './map-snapshot-format.js';
import {loadHostedTemporalGeography} from './hosted-temporal-client.js';
import {mergeHostedTemporalHistory} from './hosted-temporal-geography.js';
import {decodeReferences,decodeReferenceContext} from './reference-records.js';
import {referenceContextByLocation} from './reference-context.js';
import {loadReferenceBundle} from './reference-bundle.js';
import {preparedEvidencePartsAt,selectPreparedEvidence,verifyPreparedEvidencePart,verifyPreparedEvidenceIndexBytes,mergePreparedEvidence} from './prepared-evidence.js';
import {decodeDerived} from './derived-records.js';
import {runtimeOwnershipBucket,runtimeOwnershipData} from './runtime-ownership.js';
import {loadOwnershipAssets} from './ownership-assets.js';
import { validYear } from './model.js';
import { validateHierarchy } from './hierarchy.js';

const staticAtlas = import.meta.env.VITE_STATIC_ATLAS === 'true';
const hostedDatabase = import.meta.env.VITE_HOSTED_DATABASE === 'true';
let historyRequest;
let compactMapSupported=false;
let datedGeographySupported=false,expectedGeography,referenceTemporalHistory=[];
let ownershipRequests=new Map();
let ownershipIndexRequest;
let referenceAttributeRequest;
let referenceAttributeBundle,referenceAttributeFootprints;
let initialHostedMapRequest;
let geographyGeneration=0;
let preparedEvidenceIndexRequest,preparedEvidenceProof;
let preparedEvidenceRequests=new Map();
function loadPreparedEvidenceIndex(){
 if(!preparedEvidenceIndexRequest){
  const proof=preparedEvidenceProof;
  const request=fetch('./prepared-evidence/index.json').then(async response=>{if(!response.ok)throw Error(`Atlas evidence unavailable (${response.status})`);return verifyPreparedEvidenceIndexBytes(await response.arrayBuffer(),proof);}).catch(error=>{if(preparedEvidenceIndexRequest===request)preparedEvidenceIndexRequest=null;throw error;});
  preparedEvidenceIndexRequest=request;
 }
 return preparedEvidenceIndexRequest;
}
async function loadPreparedEvidence(year,examples,signal){
 const requests=preparedEvidenceRequests,proof=preparedEvidenceProof,index=await loadPreparedEvidenceIndex();signal?.throwIfAborted();const selected=preparedEvidencePartsAt(index,year);
 const parts=await Promise.all(selected.map(async part=>{if(!requests.has(part.path))requests.set(part.path,readJSON(`./prepared-evidence/${part.path}`).then(async rows=>{await verifyPreparedEvidencePart(part,rows);return rows;}).catch(error=>{requests.delete(part.path);throw error;}));return {path:part.path,rows:await requests.get(part.path)};}));
 const active=new Set(selected.map(p=>p.path));for(const key of requests.keys())if(!active.has(key))requests.delete(key);signal?.throwIfAborted();
 return selectPreparedEvidence(index,parts,year,{examples,expected:proof});
}
function loadHistory(){
 if(!historyRequest){
  const request=readJSON('./atlas-history.json.gz').catch(error=>{if(historyRequest===request)historyRequest=null;throw error;});
  historyRequest=request;
 }
 return historyRequest;
}
function loadReferenceGeneration(){
 if(!referenceAttributeRequest){
  const proof=referenceAttributeBundle,footprints=referenceAttributeFootprints;
  const request=(proof?loadReferenceBundle(proof,footprints):readJSON('./reference-attributes/index.json').then(async index=>({index,parts:await Promise.all(index.parts.map(p=>readJSON(`./reference-attributes/${p}`)))})))
   .then(({index,parts})=>{const referenceBaselines=decodeReferenceContext(parts,index);return {index,parts,referenceBaselines,referenceContexts:referenceContextByLocation(referenceBaselines)};})
   .catch(error=>{if(referenceAttributeRequest===request)referenceAttributeRequest=null;throw error;});
  referenceAttributeRequest=request;
 }
 return referenceAttributeRequest;
}
async function loadReferenceAttributes(year,signal){
 const {index,parts,referenceBaselines,referenceContexts}=await loadReferenceGeneration();signal?.throwIfAborted();return {records:decodeReferences(parts,index,year),referenceBaselines,referenceContexts};
}

async function loadOwnershipHistory(year,signal){
 // Capture this generation before awaiting its index; later loads get a new map.
 const requests=ownershipRequests;
 if(!ownershipIndexRequest){
  const request=readJSON('./ownership-runtime/index.json').catch(error=>{if(ownershipIndexRequest===request)ownershipIndexRequest=null;throw error;});
  ownershipIndexRequest=request;
 }
 const index=await ownershipIndexRequest;signal?.throwIfAborted();
 const selected=runtimeOwnershipBucket(index,year);if(!selected)return [];
 if(!requests.has(selected.path)){
  const request=readJSON(`./ownership-runtime/${selected.path}`).then(bucket=>runtimeOwnershipData(index,bucket,year)).catch(error=>{if(requests.get(selected.path)===request)requests.delete(selected.path);throw error;});
  requests.set(selected.path,request);
  // Keep navigation between nearby dates cheap without retaining the entire history.
  while(requests.size>2)requests.delete(requests.keys().next().value);
 }
 const data=await requests.get(selected.path);signal?.throwIfAborted();
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
async function loadHostedSnapshotPages(year,examples,signal){
 const attributes=[],names=[],retirements=[];let cursor='',revision=null,limit=4096,temporalPages;const cursors=new Set();
 try{
 while(true){
  const params=new URLSearchParams({year:String(year),examples:String(Number(examples)),limit:String(limit),evidence_only:'1',include_temporal:String(Number(datedGeographySupported))});if(cursor)params.set('cursor',cursor);
  const response=await fetch('/api/map/snapshot?'+params,{signal});
  if(!response.ok){const error=await response.json().catch(()=>({}));if(response.status===400&&limit>1000&&error.error==='Map entity page limit must be between 1 and 1000'){limit=1000;continue;}if(response.status===409&&error.retryable)throw new ContentRevisionError();if(response.status===413&&error.retryable&&limit>1){limit=Math.max(1,Math.min(limit-1,Number.isInteger(error.suggested_limit)?error.suggested_limit:Math.floor(limit/2)));continue;}throw Error(`Atlas data unavailable (${response.status})`);}
  const raw=await response.json(),page=hydrateMapSnapshotPage(raw);
  if(page.year!==year)throw Error('Historical database returned an incorrect year');
  if(revision!=null&&revision!==page.revision)throw new ContentRevisionError();revision=page.revision;
  attributes.push(...page.records);names.push(...page.names);retirements.push(...page.retirements);
  if(page.next_cursor===null)temporalPages=raw.temporal_geography;
  cursor=page.next_cursor||'';if(cursor&&cursors.has(cursor))throw Error('Historical database returned a repeated cursor');if(cursor)cursors.add(cursor);else break;
 }
 const result=[attributes,names,retirements].map(records=>({records,available:true,revision}));result.temporalPages=temporalPages;return result;
 }catch(error){if(error.name==='AbortError'||signal?.aborted||error.retryable)throw error;return [0,1,2].map(()=>({records:[],available:false,revision:null}));}
}
let lastCompleteHostedMap;
function unavailableHostedMap(year,examples,{unstable=false}={}){
 const key=`${year}:${Number(examples)}`,cached=lastCompleteHostedMap?.key===key?lastCompleteHostedMap.value:null,empty={records:[],available:false,revision:null};
 return {attributes:cached?{...cached.attributes,available:false}:empty,names:cached?{...cached.names,available:false}:empty,retirements:cached?{...cached.retirements,available:false}:empty,temporalGeography:cached?.temporalGeography??null,stale:Boolean(cached),retirementAuthority:Boolean(cached),cached_revision:cached?.attributes.revision??null,...(unstable?{unstable:true}:{})};
}
async function temporalAPIGet(url,{signal}={}){
 const response=await fetch(url,{signal}),payload=await response.json();
 if(!response.ok){const error=Object.assign(new Error('Dated geography unavailable'),{status:response.status,retryable:response.status===409||Boolean(payload.retryable),suggested_limit:payload.suggested_limit});throw error;}
 return payload;
}
async function loadHostedMapEvidence(year,examples,signal){
 const generation=geographyGeneration;
 for(let attempt=0;attempt<3;attempt++){
  if(generation!==geographyGeneration)throw new DOMException('Evidence geography superseded','AbortError');
  signal?.throwIfAborted();
  try{
   const pages=hostedDatabase&&compactMapSupported?await loadHostedSnapshotPages(year,examples,signal):await Promise.all(['/api/attributes','/api/names','/api/retirements'].map(endpoint=>loadHostedRecords(endpoint,year,examples,signal)));
   signal?.throwIfAborted();
   if(generation!==geographyGeneration)throw new DOMException('Evidence geography superseded','AbortError');
   if(pages.some(p=>!p.available))return unavailableHostedMap(year,examples);
   const versions=new Set(pages.filter(p=>p.revision!=null).map(p=>p.revision));
   if(versions.size>1)throw new ContentRevisionError();
   let temporalGeography=null;
   if(hostedDatabase&&datedGeographySupported){
    const bundled=pages.temporalPages;
    const apiGet=bundled?async url=>{const stream=new URL(url,'https://atlas.invalid').searchParams.get('stream');const page=bundled[stream];if(!page||page.next_cursor!==null)throw Error('Incomplete inline temporal geography');return page;}:temporalAPIGet;
    try{temporalGeography=await loadHostedTemporalGeography({apiGet,year,examples,expectedGeography,expectedRevision:pages[0].revision,signal});}
    catch(error){if(error.name==='AbortError'||signal?.aborted||error.retryable)throw error;return unavailableHostedMap(year,examples);}
   }
   const value={attributes:pages[0],names:pages[1],retirements:pages[2],temporalGeography,retirementAuthority:true};
   signal?.throwIfAborted();
   if(generation!==geographyGeneration)throw new DOMException('Evidence geography superseded','AbortError');
   if(hostedDatabase)lastCompleteHostedMap={key:`${year}:${Number(examples)}`,value};
   return value;
  }catch(error){
   if(error.name==='AbortError'||signal?.aborted||!error.retryable)throw error;
   if(attempt===2)return unavailableHostedMap(year,examples,{unstable:true});
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

export async function loadGeography(initialSelection) {
  const generation=++geographyGeneration;
  initialHostedMapRequest?.controller.abort();initialHostedMapRequest=null;
  lastCompleteHostedMap=null;
  // Reference presentation context belongs to this loaded asset generation.
  referenceAttributeRequest=null;
  ownershipIndexRequest=null;ownershipRequests=new Map();
  historyRequest=null;
  preparedEvidenceIndexRequest=null;preparedEvidenceRequests=new Map();
  const data=await readJSON(staticAtlas ? './atlas-geography.json' : '/api/geography');
  if(generation!==geographyGeneration)throw new DOMException('Geography superseded','AbortError');
  referenceAttributeBundle=data.referenceAttributes??null;
  referenceAttributeFootprints=data.reference_release?.footprints_sha256??data.preparedEvidence?.footprints_sha256;
  preparedEvidenceProof=data.preparedEvidence;
  compactMapSupported=data.contentCapabilities?.mapSnapshots===1;
  datedGeographySupported=data.contentCapabilities?.datedGeography===1;
  expectedGeography=data.reference_release?{release_id:data.reference_release.id,hierarchy_sha256:data.reference_release.hierarchy_sha256,footprints_sha256:data.reference_release.footprints_sha256}:null;
  if(datedGeographySupported&&!expectedGeography)throw Error('Dated geography requires a pinned reference release');
  // Preload one complete pinned bundle; legacy deployments keep their old reads.
  if(staticAtlas&&referenceAttributeBundle)loadReferenceGeneration().catch(()=>{});
  // Queue ownership rows before the catalog fan-out so decoding can overlap it.
  // Every required stream still completes before this generation is exposed.
  const ownershipInput=data.parts&&data.pixelMap?loadOwnershipAssets(data.pixelMap):null;
  // Fetch one pinned initial evidence selection while complete geography loads.
  // It is consumed only for that same year/examples pair, never another visit.
  let speculative;
  if(staticAtlas&&hostedDatabase&&validYear(initialSelection?.year)&&typeof initialSelection.examples==='boolean'){
   const {year,examples}=initialSelection,controller=new AbortController();
   const request=loadHostedMapEvidence(year,examples,controller.signal);
   request.catch(()=>{});
   speculative={year,examples,controller,request};initialHostedMapRequest=speculative;
   loadHistory().catch(()=>{});
   if(preparedEvidenceProof)loadPreparedEvidenceIndex().catch(()=>{});
  }
  const inputs=Promise.all([
   ownershipInput,
   data.temporalHistoryParts?Promise.all(data.temporalHistoryParts.map(p=>readJSON(`./${p}`))).then(parts=>parts.flat()):null,
   data.entityParts?Promise.all(data.entityParts.map(p=>readJSON(`./${p}`))).then(parts=>parts.flat()):null,
   data.parts?Promise.all(data.parts.map(part=>readJSON(`./${part}`))).then(parts=>parts.flat()):null
  ]);
  let ownership,history,entities,features;
  try{
   [ownership,history,entities,features]=await inputs;
   if(generation!==geographyGeneration)throw new DOMException('Geography superseded','AbortError');
   if(features){data.features=features;data.ownership=ownership;}
   if(entities)data.temporal.entities=entities;
   if(history)data.temporal.history=history;
   validateHierarchy(data.units,data.features.map(f=>f.properties));
  }catch(error){speculative?.controller.abort();if(initialHostedMapRequest===speculative)initialHostedMapRequest=null;throw error;}
  referenceTemporalHistory=data.temporal?.history??[];
  return data;
}

async function loadSelectedHostedMap(year,examples,signal){
 const pending=initialHostedMapRequest;initialHostedMapRequest=null;
 if(!pending)return loadHostedMapEvidence(year,examples,signal);
 if(pending.year!==year||pending.examples!==examples){pending.controller.abort();return loadHostedMapEvidence(year,examples,signal);}
 const cancel=()=>pending.controller.abort();
 if(signal?.aborted)cancel();else signal?.addEventListener('abort',cancel,{once:true});
 try{const value=await pending.request;signal?.throwIfAborted();return value;}
 finally{signal?.removeEventListener('abort',cancel);}
}

export async function loadSnapshot(year, examples, signal) {
  if (!validYear(year)) throw new Error('Invalid year');
  if (!staticAtlas) return readJSON(`/api/snapshot?year=${year}&examples=${Number(examples)}`, signal);
  const generation=geographyGeneration;
  // The immutable export is shared across requests; cancel the selection, not its download.
  const [history,derived,references,hostedMap,evidence] = await Promise.all([loadHistory(),loadOwnershipHistory(year,signal),loadReferenceAttributes(year,signal),loadSelectedHostedMap(year,examples,signal),loadPreparedEvidence(year,examples,signal)]);
  signal?.throwIfAborted();
  if(generation!==geographyGeneration)throw new DOMException('Snapshot geography superseded','AbortError');
  const {attributes:hosted,names:temporal_history,retirements}=hostedMap;
  const evidenceUnavailable=hostedDatabase&&!hostedMap.retirementAuthority;
  const merged=evidenceUnavailable?{records:[],names:[]}:mergePreparedEvidence(hosted.records,temporal_history.records,evidence,{retirements:retirements.records});
  const temporalHistory=hostedMap.temporalGeography?mergeHostedTemporalHistory([...referenceTemporalHistory,...merged.names],hostedMap.temporalGeography.combinedSnapshot,{complete:true,year,examples,expectedGeography}):merged.names;
  return { year,evidenceUnavailable,referenceBaselines:references.referenceBaselines, referenceContexts:references.referenceContexts, temporal_history:temporalHistory, temporalHistoryComplete:Boolean(hostedMap.temporalGeography), storage:hostedDatabase?{available:hosted.available&&temporal_history.available&&retirements.available,stale:Boolean(hostedMap.stale),cached_revision:hostedMap.cached_revision??null,...(!hosted.available?{reason:hostedMap.stale?'Historical database unavailable. Showing the last complete cached content snapshot for this year; it may be outdated. Select the year again to retry.':hostedMap.unstable?'Historical content changed during loading. Dated values are unavailable until a consistent snapshot can be read. Select the year again to retry.':'Historical database unavailable. Dated values are unavailable because withdrawals could not be verified. Geography remains browsable. Select the year again to retry.'}:{})}:null, states:evidenceUnavailable?[]:selectRecords(history.states, year, examples), boundaries: selectRecords(history.boundaries, year, examples), attributes:evidenceUnavailable?[]:mergePreparedEvidence([...merged.records,...(history.attributes||[]).filter(r=>r.valid_from<=year&&r.valid_to>year&&(!r.is_example||examples))],[],{records:[...derived,...references.records],names:[]},{retirements:retirements.records}).records,polities:[] };
}

export async function ensureGeometry(data,signal){
  if(!data.geometryParts)return;
  data.geometryRequest ||= Promise.all(data.geometryParts.map(p=>readJSON(`./${p}`))).then(parts=>new Map(parts.flat().map(f=>[f.id,f.geometry]))).catch(error=>{data.geometryRequest=null;throw error;});
  const geometries=await data.geometryRequest;signal?.throwIfAborted();
  for(const f of data.features)f.geometry=geometries.get(f.id);
}
