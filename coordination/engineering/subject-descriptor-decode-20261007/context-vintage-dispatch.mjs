// Preserve the mandatory original code realm, then mint a current-realm proof.
// Original data, source hashes and scientific execution metadata are unchanged.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {gunzipSync} from 'node:zlib';
import {repositoryReader,safeEvidencePath,sha256} from '../../../scripts/evidence-quality.mjs';
import {validateContextMigration} from '../../../scripts/native-ownership/validate-context-migration.mjs';
import {validateBuildContextStage as currentStage,BUILD_CONTEXT_STAGE_PATH} from '../../../scripts/native-ownership/validate-build-context-stage.mjs';

const captureRoot=fileURLToPath(new URL('./legacy-context-v1/',import.meta.url));
const indexSha='51d3be21c7c95f9672acbd437348d5536880f6245b845ae78d9e1ae24e6c3c41';
const limit=32*1024*1024;
function ordinary(root,name){
 safeEvidencePath(name);
 let target=root;
 for(const component of name.split('/')){
  target=path.join(target,component);const stat=fs.lstatSync(target);
  if(stat.isSymbolicLink())throw Error('Captured context code cannot use symlinks');
 }
 const stat=fs.lstatSync(target);
 if(!stat.isFile()||stat.size>limit)throw Error('Captured context code must be bounded ordinary files');
 return fs.readFileSync(target);
}
export async function authenticateOriginalValidator({snapshotRoot=captureRoot}={}){
 let ancestor=path.parse(path.resolve(snapshotRoot)).root;
 for(const component of path.resolve(snapshotRoot).slice(ancestor.length).split(path.sep)){
  ancestor=path.join(ancestor,component);const stat=fs.lstatSync(ancestor);
  if(!stat.isDirectory()||stat.isSymbolicLink())throw Error('Captured context root cannot use symlink ancestors');
 }
 const raw=ordinary(snapshotRoot,'index.json');
 if(sha256(raw)!==indexSha)throw Error('Captured context inventory bytes differ');
 const index=JSON.parse(raw),names=new Set(index.files.map(p=>p.path));
 if(names.size!==17||index.files.length!==17)throw Error('Incomplete captured context closure');
 for(const pin of index.files){
  const body=ordinary(snapshotRoot,pin.path);
  if((fs.lstatSync(path.join(snapshotRoot,pin.path)).mode&0o777)!==0o644||body.length!==pin.bytes||sha256(body)!==pin.sha256)
   throw Error('Captured context code bytes or mode differ: '+pin.path);
  // Every literal project import must resolve to an authenticated body. The
  // exact original bytes contain no computed/dynamic imports or package imports.
  if(pin.path!=='package.json'){
   for(const match of body.toString().matchAll(/^\s*import\s+(?:[^\n;]*?\sfrom\s+)?['"]([^'"]+)['"]/gm)){
    const specifier=match[1];if(specifier.startsWith('node:'))continue;
    if(!specifier.startsWith('.'))throw Error('Unsupported captured project import');
    const resolved=path.posix.normalize(path.posix.join(path.posix.dirname(pin.path),specifier));
    if(!names.has(resolved))throw Error('Captured context import outside inventory');
   }
  }
 }
 if(process.execArgv.some(v=>/loader|--import|--require|^-r$/.test(v))||process.env.NODE_OPTIONS)
  throw Error('Captured context validation requires an ordinary Node invocation');
 const module=await import(pathToFileURL(path.join(snapshotRoot,index.entry)).href);
 return {index,validate:module.validateBuildContextStage};
}
export async function validateBuildContextVintage({root=process.cwd(),expectedReference,readFile}={}){
 const read=readFile??repositoryReader(root);
 if(!readFile&&!fs.existsSync(path.join(root,BUILD_CONTEXT_STAGE_PATH)))
  return currentStage({root,expectedReference}); // Existing original-only fallback.
 const {index,validate}=await authenticateOriginalValidator();
 const stageRaw=read(BUILD_CONTEXT_STAGE_PATH,'candidate');
 if(stageRaw.length!==index.stage_bytes||sha256(stageRaw)!==index.stage_sha256)
  throw Error('Original context stage bytes differ');
 const stage=JSON.parse(stageRaw),pins=new Map(index.files.map(p=>[p.path,p]));
 const originalRead=(name,vintage)=>pins.has(name)&&vintage==='candidate'
  ?ordinary(captureRoot,name):read(name,vintage);
 // This executes the old implementation and ALL its original input guards.
 const originalResult=await validate({root,expectedReference,readFile:originalRead});
 const checked=pin=>{
  safeEvidencePath(pin.path);
  if(!Number.isSafeInteger(pin.bytes)||pin.bytes<0||pin.bytes>limit)throw Error('Context byte pin exceeds bound');
  const raw=read(pin.path,'candidate');
  if(raw.length!==pin.bytes||sha256(raw)!==pin.sha256)throw Error('Current context bytes differ: '+pin.path);
  return raw;
 };
 const registry=JSON.parse(gunzipSync(checked(stage.releases),{maxOutputLength:limit}));
 const predecessor=registry.releases.at(-2),release=registry.releases.at(-1);
 assert.deepEqual(release,expectedReference);assert.deepEqual(predecessor,originalResult.predecessorRelease);
 const decode=(pin,before)=>{
  const inputs=JSON.parse(checked(pin)),features=[];
  for(const part of inputs.parts){
   safeEvidencePath(part.path);if(!/^part-[0-9]+\.json\.gz$/.test(part.path))throw Error('Unsafe compact context part');
   let base=path.posix.dirname(pin.path);
   if(part.reused_from!==undefined){
    assert.equal(part.reused_from,stage.before_context.path);assert(before);
    const {reused_from,...descriptor}=part;
    assert.deepEqual(descriptor,before.inputs.parts.find(p=>p.path===part.path));base=path.posix.dirname(stage.before_context.path);
   }
   const raw=checked({path:base+'/'+part.path,bytes:part.bytes,sha256:part.sha256});
   const decoded=gunzipSync(raw,{maxOutputLength:limit});
   if(decoded.length!==part.uncompressed_bytes||sha256(decoded)!==part.uncompressed_sha256)throw Error('Compact context decoded bytes differ');
   features.push(...JSON.parse(decoded));
  }
  return {inputs,features};
 };
 const before=decode(stage.before_context),after=decode(stage.after_context,before);
 const migration=validateContextMigration({original:before.features,migrated:after.features,
  candidates:JSON.parse(checked(stage.native_proposal)),predecessorRelease:predecessor,release,
  migrationManifestFile:path.join(root,stage.geometry_manifest.path)});
 const {geometryValidation,...receipt}=migration;
 assert.deepEqual(receipt,originalResult.receipt.migration);
 return {...originalResult,geometryValidation}; // Never return the old realm token.
}
