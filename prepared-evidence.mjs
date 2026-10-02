import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {footprintHash} from './scripts/check-prepared.mjs';
import {preparedEvidencePartsAt,selectPreparedEvidence,preparedEvidenceJSON,validatePreparedEvidenceIndex} from './src/prepared-evidence.js';
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const caches=new Map();
export function preparedEvidenceAt(year,{examples=false,directory=new URL('./data/prepared-evidence/',import.meta.url),expected}={}){
 const folder=directory instanceof URL?directory.pathname:path.resolve(directory),file=path.join(folder,'index.json');
 if(!fs.existsSync(file))return {records:[],names:[]};
 const stamp=fs.statSync(file).mtimeMs+':'+fs.statSync(file).size;
 let cache=caches.get(folder);if(cache?.stamp!==stamp){const index=JSON.parse(fs.readFileSync(file));validatePreparedEvidenceIndex(index);cache={stamp,index,parts:new Map(),proof:null};caches.set(folder,cache);}
 if(!expected){const data=path.dirname(folder),hierarchy=path.join(data,'hierarchy.json'),world=path.join(data,'world-index.json');
  const worldIndex=JSON.parse(fs.readFileSync(world)),files=[hierarchy,world,...worldIndex.parts.map(p=>path.join(data,p))],signature=files.map(f=>{const s=fs.statSync(f);return `${s.mtimeMs}:${s.size}`;}).join('|');
  if(cache.proof?.signature!==signature)cache.proof={signature,expected:{hierarchy_sha256:sha(fs.readFileSync(hierarchy)),footprints_sha256:footprintHash(worldIndex.parts.flatMap(p=>JSON.parse(fs.readFileSync(path.join(data,p))).features))}};
  expected=cache.proof.expected;
 }
 validatePreparedEvidenceIndex(cache.index,expected);
 const parts=[];for(const meta of preparedEvidencePartsAt(cache.index,year)){if(!cache.parts.has(meta.path)){const raw=fs.readFileSync(path.join(folder,meta.path));if(sha(raw)!==meta.sha256)throw Error(`Prepared evidence asset hash mismatch: ${meta.path}`);const rows=JSON.parse(gunzipSync(raw));if(sha(preparedEvidenceJSON(rows))!==meta.decoded_sha256)throw Error('Prepared evidence decoded hash mismatch');cache.parts.set(meta.path,rows);}parts.push({path:meta.path,rows:cache.parts.get(meta.path)});}
 // Retain only assets needed at the requested observation interval.
 const active=new Set(parts.map(p=>p.path));for(const key of cache.parts.keys())if(!active.has(key))cache.parts.delete(key);
 return selectPreparedEvidence(cache.index,parts,year,{examples,expected});
}
