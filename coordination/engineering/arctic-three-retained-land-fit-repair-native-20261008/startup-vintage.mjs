// Routing only: stock startup packer and all decoded ownership words unchanged.
import assert from 'node:assert/strict';
import path from 'node:path';
import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {packageStartupOwnership} from '../../../scripts/package-startup-ownership.mjs';
export function startupVintagePrefix(manifestSha){
 assert(/^[a-f0-9]{64}$/.test(manifestSha));return 'ownership-vintages/'+manifestSha;
}
export async function packageVersionedStartupOwnership({manifest,manifestSha,manifestPath,source,destination}){
 const prefix=startupVintagePrefix(manifestSha);
 assert.equal(manifest.version,2);assert.equal(typeof source,'string');assert.equal(typeof destination,'string');
 assert(!destination.split(/[\\/]/).includes('..'));
 assert.equal(typeof manifestPath,'string');assert(!manifestPath.split(/[\\/]/).includes('..'));
 const target=path.resolve(destination,prefix);
 for(let ancestor=target;;ancestor=path.dirname(ancestor)){
  const stat=await fs.lstat(ancestor).catch(error=>{if(error.code==='ENOENT')return null;throw error;});
  if(stat){assert(!stat.isSymbolicLink()&&stat.isDirectory(),'Unsafe startup destination');if(ancestor===target)throw Error('Startup vintage already exists');}
  if(ancestor===path.dirname(ancestor))break;
 }
 const stat=await fs.lstat(manifestPath);assert(stat.isFile()&&!stat.isSymbolicLink()&&stat.size<=32*1024*1024);
 const bytes=await fs.readFile(manifestPath);assert.equal(createHash('sha256').update(bytes).digest('hex'),manifestSha,'Stale manifest binding');
 assert.deepEqual(JSON.parse(bytes),manifest,'Manifest object differs');
 const result=await packageStartupOwnership({manifest,source,destination:path.join(destination,prefix)});
 const rows=manifest.parts.filter(part=>part.kind==='rows');
 const parts=result.pixelMap.parts.map(part=>{
  if(part.kind==='rows'){assert.deepEqual(part,rows.find(row=>row.path===part.path));return part;}
  assert.equal(part.kind,'runs');assert(/^(?:native-v1\/)?ownership\/startup-runs-[0-9]+\.bin\.gz$/.test(part.path));
  return {...part,path:prefix+'/'+part.path};
 });
 const outputs=result.outputs.map(pin=>{assert(/^(?:native-v1\/)?ownership\/startup-runs-[0-9]+\.bin\.gz$/.test(pin.path));return {...pin,path:prefix+'/'+pin.path};});
 return {...result,pixelMap:{...result.pixelMap,parts},outputs,
  immutable_url_binding:{manifest_sha256:manifestSha,prefix,unchanged_row_paths:true,stock_packer_unchanged:true}};
}
