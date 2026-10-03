/** One controlled registration list. Domain modules require reviewed integration;
 * historical registry definitions remain immutable and available by digest. */
import {createObservationRegistry} from './observation-registry.js';
import {assertJSONData} from './json-contract.js';
import baseline from '../data/observation-registry-history/base-v1.json' with {type:'json'};

export const observationModules=Object.freeze([]);
export const registeredObservationRegistry=createObservationRegistry(observationModules);
const freeze=value=>{if(value&&typeof value==='object'){Object.values(value).forEach(freeze);Object.freeze(value);}return value;};
const baselineDigest='cc6aae6c18099d3e776c73ee4144556422ac87b911aa30aa95bef831ca18d2d2';
const retainedRegistries=[{sha256:baselineDigest,registry:freeze(baseline)}];
export const observationDigest=async value=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(value))))].map(n=>n.toString(16).padStart(2,'0')).join('');
let contractPromise;
export function observationContract(){
 return contractPromise??=buildContract();
}
async function buildContract(){
 const registry=registeredObservationRegistry,registries={};
 for(const retained of retainedRegistries){
  assertJSONData(retained.registry,{objectRequired:true,maxBytes:2097152});
  if(await observationDigest(retained.registry)!==retained.sha256)throw Error('Retained registry digest changed');
  // Adding a module cannot reinterpret an older field, type or metric.
  for(const collection of ['types','metrics','fields','relationships'])for(const [id,definition] of Object.entries(retained.registry[collection])){
   if(JSON.stringify(registry[collection][id])!==JSON.stringify(definition))throw Error('Controlled registry changed a retained definition');
  }
  for(const module of retained.registry.modules)if(!registry.modules.some(row=>row.id===module.id&&row.version===module.version))throw Error('Controlled registry removed a retained module');
  registries[retained.sha256]=retained.registry;
 }
 const registry_sha256=await observationDigest(registry);registries[registry_sha256]=registry;
 return freeze({version:1,registry_sha256,registry,registries,supported_registry_sha256:Object.keys(registries).sort()});
}
export async function registryForDigest(hash){
 const contract=await observationContract();
 if(!Object.hasOwn(contract.registries,hash))throw Error('Unrecognized typed registry digest');
 return contract.registries[hash];
}
