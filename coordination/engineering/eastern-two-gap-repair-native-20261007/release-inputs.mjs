// Complete immutable v7 input ledger for the bounded eastern v8 successor.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {immutableReader,loadSuccessor} from './native-producer.mjs';
import {decodeGeographicReleaseBatch} from '../../../scripts/read-geographic-release-manifest.mjs';
import {validatePredecessor,successorRelease,appendSuccessor} from './release-successor.mjs';
const sha=b=>createHash('sha256').update(b).digest('hex');
export async function releaseInputs(repo,baseline,{storage,nativeStorage}={}){
 const input=immutableReader(repo,baseline,storage),root='data/geographic-releases/';
 const pointer=input.object(root+'current-manifest.json'),original=input.read(root+'index.json');
 assert.equal(sha(original),pointer.predecessor_index_sha256);
 const encoded=input.read(root+pointer.path);assert.equal(sha(encoded),pointer.sha256);
 const registry=input.object(root+pointer.path),base=JSON.parse(original);
 assert.deepEqual(registry.releases.slice(0,base.releases.length),base.releases);
 assert.deepEqual(registry.batches.slice(0,base.batches.length),base.batches);
 const catalog=input.read('data/hosted-catalog/index.json');assert.equal(sha(catalog),registry.original_catalog_sha256);
 const last=registry.releases.at(-1),memberships=[],changes=[],sources=new Map(),payloads=[];
 for(const part of registry.batches){
  if(!part.path.startsWith('7-')&&!registry.sources_batches.includes(part.path))continue;
  const raw=input.read(root+part.path),payload=JSON.parse(decodeGeographicReleaseBatch(raw,part));
  payloads.push({path:root+part.path,sha256:sha(raw),members:payload.memberships?.length??0,changes:payload.changes?.length??0,sources:payload.sources?.length??0});
  if(payload.memberships||payload.changes){assert.equal(payload.release_id,last.id,'Wrong frozen current ledger release');memberships.push(...payload.memberships??[]);changes.push(...payload.changes??[]);}
  for(const s of payload.sources??[]){if(sources.has(s.id))assert.deepEqual(sources.get(s.id),s,'Original source definition rebound');sources.set(s.id,s);}
 }
 assert.equal(memberships.length,84833,'Complete current membership roster required');
 for(const row of [...memberships,...changes])assert(sources.has(row.source_id),'Missing complete original source definition');
 const hierarchy=input.read('data/hierarchy.json');
 await validatePredecessor({registry,memberships,changes,hierarchySha:sha(hierarchy),originalCatalogSha:sha(catalog)});
 const native=loadSuccessor(repo,baseline,{storage:nativeStorage});
 const receiptRaw=input.read('data/reference-migrations/eastern-two-gap-repair-20261006/migration-receipt.json.gz');
 const receipt=input.object('data/reference-migrations/eastern-two-gap-repair-20261006/migration-receipt.json.gz');
 const relationships=receipt.relationships.flatMap(r=>{assert.equal(r.history_transfer,false);assert.equal(r.identity_pairs.length,1);return r.identity_pairs.map(p=>({...p,change_type:'retain',history_transfer:'none'}));});
 const result=await successorRelease({registry,memberships,changes,world:native.features,hierarchySha:sha(hierarchy),originalCatalogSha:sha(catalog),relationships,
  receiptSha:sha(receiptRaw),proposalCommit:'b4b7db357ba92d19df513f188bbd046fe66a35e4',releaseId:native.releaseId,sourceId:native.sourceId});
 return {registry,memberships,changes,sources:[...sources.values()],payloads,result,input_pins:input.pins(),native_pins:native.sourceFiles};
}
export async function buildRelease(repo,baseline,options={}){
 const input=await releaseInputs(repo,baseline,options),next=appendSuccessor(input.registry,input.result,{rowsPerBatch:250});
 assert.equal(next.files.size,343,'Full successor consists of source/header/340 membership/one change payloads');
 return {...input,next};
}
