import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
export function footprintHash(features){return createHash('sha256').update(JSON.stringify(features.map(f=>[f.id,f.geometry]).sort((a,b)=>a[0].localeCompare(b[0])))).digest('hex');}
export function checkPrepared(features){
 const expected=footprintHash(features),owner=JSON.parse(fs.readFileSync('data/ownership-history/index.json')),reference=JSON.parse(fs.readFileSync('data/reference-attributes/index.json'));
 for(const [name,index] of [['ownership',owner],['references',reference]])if(index.footprints_sha256!==expected||index.locations!==features.length)throw Error(`Prepared ${name} do not match location footprints`);
 const pixels=JSON.parse(fs.readFileSync('data/pixel-audit.json'));if(pixels.footprints_sha256!==expected||pixels.locations!==features.length)throw Error('Pixel representation audit is stale');
 const runtimeFile='data/ownership-runtime/index.json';
 if(!fs.existsSync(runtimeFile))throw Error('Bounded temporal ownership assets are missing');
 const runtime=JSON.parse(fs.readFileSync(runtimeFile));
 if(runtime.source_index_sha256!==createHash('sha256').update(fs.readFileSync('data/ownership-history/index.json')).digest('hex'))throw Error('Temporal ownership assets are stale');
 if(runtime.shared.footprints_sha256!==expected)throw Error('Temporal ownership footprints are stale');
 for(const part of runtime.buckets){if(createHash('sha256').update(fs.readFileSync('data/ownership-runtime/'+part.path)).digest('hex')!==part.sha256)throw Error(`Temporal ownership hash mismatch: ${part.path}`);}
 const validateAlgorithms=(algorithms,expected)=>{
  const hashes=algorithms.map(part=>{
   const actual=createHash('sha256').update(fs.readFileSync('data/ownership-history/'+part.path)).digest('hex');
   if(actual!==part.sha256)throw Error(`Executed ownership algorithm hash mismatch: ${part.path}`);
   return actual;
  }).join('');
  if(hashes!==expected)throw Error('Executed ownership algorithms do not match their provenance');
 };
 validateAlgorithms(owner.execution_algorithms,owner.inputs.algorithm_sha256);
 validateAlgorithms(owner.initial_execution.algorithms,owner.initial_execution.inputs.algorithm_sha256);
 const boundaryVersions=execFileSync('python3',[fileURLToPath(new URL('./boundary-version-hash.py',import.meta.url))],{encoding:'utf8'}).trim();
 if(boundaryVersions!==owner.inputs.boundary_versions)throw Error('Prepared ownership is stale: dated non-example location footprints changed; reprepare ownership and runtime assets');
 for(const part of [...owner.parts,...(owner.evidence_parts||[])]){const raw=fs.readFileSync('data/ownership-history/'+part.path);if(createHash('sha256').update(raw).digest('hex')!==part.sha256)throw Error(`Ownership part hash mismatch: ${part.path}`);}
 for(const [part,hash] of Object.entries(reference.parts_sha256||{}))if(createHash('sha256').update(fs.readFileSync('data/reference-attributes/'+part)).digest('hex')!==hash)throw Error(`Reference part hash mismatch: ${part}`);
 return expected;
}
