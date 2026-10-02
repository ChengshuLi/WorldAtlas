import fs from 'node:fs';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {decodeReferences,decodeReferenceContext} from './src/reference-records.js';
import {decodeDerived} from './src/derived-records.js';
import {runtimeOwnershipBucket,runtimeOwnershipData} from './src/runtime-ownership.js';
let cached,referenceCache,runtimeCache;
let boundaryProofCache;
export function preparedBoundariesMatch(rows){
 const file=new URL('./data/ownership-history/index.json',import.meta.url);
 if(!fs.existsSync(file))return false;
 const stamp=fs.statSync(file).mtimeMs,raw=JSON.stringify(rows),signature=createHash('sha256').update(raw).digest('hex');
 if(boundaryProofCache?.stamp===stamp&&boundaryProofCache.signature===signature)return boundaryProofCache.matches;
 const index=JSON.parse(fs.readFileSync(file));
 const actual=rows.length?execFileSync('python3',[new URL('./scripts/boundary-version-hash.py',import.meta.url).pathname,'--stdin'],{input:raw,encoding:'utf8'}).trim():createHash('sha256').update('[]').digest('hex');
 const matches=actual===index.inputs?.boundary_versions;
 boundaryProofCache={stamp,signature,matches};return matches;
}
export function invalidatePreparedFootprints(records,boundaryRows,matches){
 if(matches||!boundaryRows.length)return records;
 const affected=new Set(boundaryRows.map(row=>row[0]));
 return records.map(record=>affected.has(record.location_id)?{...record,value:null,category_id:null,status:'unknown',metadata:{...record.metadata,invalidated_footprint:true,reason:'Location footprint evidence changed; regenerate prepared assignments before using these values'}}:record);
}
function referencesAt(year){
 const root=new URL("./data/reference-attributes/",import.meta.url),file=new URL("index.json",root);if(!fs.existsSync(file))return [];
 const stamp=fs.statSync(file).mtimeMs;if(referenceCache?.stamp!==stamp){const index=JSON.parse(fs.readFileSync(file));referenceCache={stamp,index,parts:index.parts.map(p=>JSON.parse(gunzipSync(fs.readFileSync(new URL(p,root)))))};}
 return decodeReferences(referenceCache.parts,referenceCache.index,year);
}

export function environmentalReferenceContext(){
 referencesAt(2026);
 return referenceCache?(referenceCache.context??=decodeReferenceContext(referenceCache.parts,referenceCache.index)):[];
}

export function derivedRecordsAt(year){
 const runtimeRoot=new URL('./data/ownership-runtime/',import.meta.url),runtimeFile=new URL('index.json',runtimeRoot);
 if(fs.existsSync(runtimeFile)){
  const stamp=fs.statSync(runtimeFile).mtimeMs;
  if(runtimeCache?.stamp!==stamp)runtimeCache={stamp,index:JSON.parse(fs.readFileSync(runtimeFile)),buckets:new Map()};
  const selected=runtimeOwnershipBucket(runtimeCache.index,year);if(!selected)return referencesAt(year);
  if(!runtimeCache.buckets.has(selected.path)){
   runtimeCache.buckets.set(selected.path,runtimeOwnershipData(runtimeCache.index,JSON.parse(gunzipSync(fs.readFileSync(new URL(selected.path,runtimeRoot)))),year));
   while(runtimeCache.buckets.size>2)runtimeCache.buckets.delete(runtimeCache.buckets.keys().next().value);
  }
  const data=runtimeCache.buckets.get(selected.path);
  return [...decodeDerived(data.parts,data.index,year),...referencesAt(year)];
 }
 const root=new URL('./data/ownership-history/',import.meta.url),file=new URL('index.json',root);
 if(!fs.existsSync(file))return referencesAt(year);
 const stamp=fs.statSync(file).mtimeMs;
 if(cached?.stamp!==stamp)cached={stamp,index:JSON.parse(fs.readFileSync(file)),parts:null};
 if(year<cached.index.valid_from||year>=cached.index.valid_to)return referencesAt(year);
 if(!cached.parts){const index=cached.index;if(index.evidence_parts)index.evidence=index.evidence_parts.flatMap(p=>JSON.parse(gunzipSync(fs.readFileSync(new URL(p.path,root)))));cached.parts=index.parts.map(p=>JSON.parse(gunzipSync(fs.readFileSync(new URL(p.path,root)))));}
 return [...decodeDerived(cached.parts,cached.index,year),...referencesAt(year)];
}
