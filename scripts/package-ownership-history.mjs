import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';

const compare=(a,b)=>a<b?-1:a>b?1:0;
const digest=bytes=>createHash('sha256').update(bytes).digest('hex');
const prior=file=>file.startsWith('prior-archives/');
const manifestName='archive-delivery.json';
async function inventory(root,relative=''){
 const files=[];
 for(const entry of (await fs.readdir(path.join(root,relative),{withFileTypes:true})).sort((a,b)=>compare(a.name,b.name))){
  const file=relative?`${relative}/${entry.name}`:entry.name;
  if(entry.isSymbolicLink())throw Error(`Ownership delivery cannot package a symbolic link: ${file}`);
  if(entry.isDirectory())files.push(...await inventory(root,file));
  else if(entry.isFile()){const bytes=await fs.readFile(path.join(root,file));files.push({path:file,sha256:digest(bytes),bytes:bytes.length});}
  else throw Error(`Unsupported ownership delivery entry: ${file}`);
 }
 return files.sort((a,b)=>compare(a.path,b.path));
}
async function validatePriorPins(source,files){
 const byPath=new Map(files.map(file=>[file.path,file]));
 for(const file of files.filter(file=>prior(file.path)&&path.posix.basename(file.path)==='archive-index.json')){
  const index=JSON.parse(await fs.readFile(path.join(source,file.path),'utf8'));
  if(!Array.isArray(index.parts))throw Error(`Prior archive has no pinned parts: ${file.path}`);
  for(const part of index.parts){
   if(typeof part.path!=='string'||part.path.startsWith('/')||part.path.split('/').some(segment=>segment==='..'||segment==='.')||part.path.includes('\\')||!/^[a-f0-9]{64}$/.test(part.sha256||''))throw Error(`Invalid prior archive pin: ${file.path}`);
   const target=path.posix.join(path.posix.dirname(file.path),part.path),actual=byPath.get(target);
   if(!actual||actual.sha256!==part.sha256)throw Error(`Prior archive hash mismatch: ${target}`);
  }
 }
}

export async function verifyOwnershipDelivery({source,destination,manifest}){
 const sourceFiles=await inventory(source);
 const expected=[...manifest.current_files,...manifest.archives.map(file=>({path:file.path,sha256:file.sha256,bytes:file.bytes}))].sort((a,b)=>compare(a.path,b.path));
 if(JSON.stringify(sourceFiles)!==JSON.stringify(expected))throw Error('Ownership delivery source inventory or hash changed');
 const deployed=(await inventory(destination)).filter(file=>file.path!==manifestName);
 if(JSON.stringify(deployed)!==JSON.stringify(manifest.current_files))throw Error('Ownership delivery deployed inventory or hash changed');
 const emitted=JSON.parse(await fs.readFile(path.join(destination,manifestName),'utf8'));
 if(JSON.stringify(emitted)!==JSON.stringify(manifest))throw Error('Ownership archive delivery manifest changed');
}

export async function packageOwnershipHistory({source,destination,hosted=false,repositoryPath='data/ownership-history'}){
 // The portable export keeps the original archive tree and has no new manifest.
 if(!hosted){await fs.cp(source,destination,{recursive:true});return null;}
 const files=await inventory(source);await validatePriorPins(source,files);
 if(files.some(file=>file.path===manifestName))throw Error('Source ownership tree contains a reserved delivery manifest');
 const current_files=files.filter(file=>!prior(file.path));
 const archives=files.filter(file=>prior(file.path)).map(file=>({...file,repository_path:`${repositoryPath}/${file.path}`,content_addressed_path:`ownership-history/sha256/${file.sha256}`}));
 const manifest={version:1,delivery_status:'repository-retained',note:'Prior lineage archives remain in the source repository. They are omitted only from hosted client assets; this manifest does not assert an object-storage upload.',excluded_directory:'prior-archives',repository_path:repositoryPath,current_files,archives,archived_bytes:archives.reduce((sum,file)=>sum+file.bytes,0)};
 await fs.mkdir(destination,{recursive:true});
 for(const file of current_files){await fs.mkdir(path.dirname(path.join(destination,file.path)),{recursive:true});await fs.copyFile(path.join(source,file.path),path.join(destination,file.path));}
 await fs.writeFile(path.join(destination,manifestName),JSON.stringify(manifest,null,2)+'\n');
 // Account for every excluded file, including dotfiles, and reject changed bytes.
 await verifyOwnershipDelivery({source,destination,manifest});return manifest;
}
