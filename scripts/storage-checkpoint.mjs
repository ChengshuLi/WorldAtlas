import fs from 'node:fs';
import path from 'node:path';
import {createHash,randomUUID} from 'node:crypto';
import {createGzip,createGunzip} from 'node:zlib';
import {Readable,Transform,Writable} from 'node:stream';
import {pipeline} from 'node:stream/promises';
import {fileURLToPath} from 'node:url';
import {storageExportCollections} from '../hosted/storage-export.js';
import {readVerifiedStorageSnapshot} from './restore-postgres-storage.mjs';

const MiB=1024*1024;
export const checkpointLimits=Object.freeze({rawPartBytes:8*MiB,compressedPartBytes:16*MiB,manifestBytes:32*MiB,fileBytes:32*MiB,totalRawBytes:4*1024*MiB,files:100000,parts:100000});
const format='worldatlas-raw-storage-gzip-v1';
const digest=bytes=>createHash('sha256').update(bytes).digest('hex');
const sha=value=>typeof value==='string'&&/^[a-f0-9]{64}$/.test(value);
const integer=(value,min,max)=>Number.isSafeInteger(value)&&value>=min&&value<=max;
const fail=message=>{throw Error(message);};

function regularFile(directory,relative,maxBytes){
 // Paths are also checked against exact canonical export/part names by callers.
 if(typeof relative!=='string'||!relative||path.isAbsolute(relative)||relative.includes('\\')||relative.split('/').some(part=>!part||part==='.'||part==='..'))fail('Unsafe checkpoint file path');
 const root=fs.realpathSync(directory),file=path.join(root,relative);let current=root;
 for(const component of relative.split('/')){current=path.join(current,component);if(fs.lstatSync(current).isSymbolicLink())fail('Checkpoint symlinks are not allowed');}
 const stat=fs.statSync(file);if(!stat.isFile()||!integer(stat.size,1,maxBytes)||!fs.realpathSync(file).startsWith(root+path.sep))fail('Invalid or oversized checkpoint file');
 return {file,bytes:stat.size};
}
function boundedJSON(directory,relative,maxBytes){const entry=regularFile(directory,relative,maxBytes),raw=fs.readFileSync(entry.file);return {raw,value:JSON.parse(raw)};}
async function hashFile(file,expectedBytes){
 const hash=createHash('sha256');let bytes=0;
 for await(const chunk of fs.createReadStream(file,{highWaterMark:64*1024})){bytes+=chunk.length;if(bytes>expectedBytes)fail('Checkpoint file changed size');hash.update(chunk);}
 if(bytes!==expectedBytes)fail('Checkpoint file changed size');return hash.digest('hex');
}
function canonicalSourceFiles(directory){
 const {raw,value:manifest}=boundedJSON(directory,'index.json',checkpointLimits.manifestBytes);
 if(!manifest?.collections||Object.keys(manifest.collections).sort().join(',')!==[...storageExportCollections].sort().join(','))fail('Checkpoint requires all fourteen source collections');
 const files=[{path:'index.json',bytes:raw.length,sha256:digest(raw)}];let total=raw.length;
 for(const collection of storageExportCollections){
  const parts=manifest.collections[collection]?.parts;
  if(!Array.isArray(parts)||!parts.length||parts.length>checkpointLimits.files)fail('Invalid source checkpoint collection');
  for(const [index,part]of parts.entries()){
   const relative=`${collection}/part-${String(index+1).padStart(6,'0')}.json`;
   if(part.path!==relative||!integer(part.bytes,1,checkpointLimits.fileBytes)||!sha(part.sha256))fail('Invalid source checkpoint part');
   const actual=regularFile(directory,relative,checkpointLimits.fileBytes);if(actual.bytes!==part.bytes)fail('Source checkpoint part size changed');
   files.push({path:relative,bytes:part.bytes,sha256:part.sha256});total+=part.bytes;
   if(files.length>checkpointLimits.files||total>checkpointLimits.totalRawBytes)fail('Source checkpoint exceeds bounded file/byte limits');
  }
 }
 // This is the original restore validator, including raw JSON, ordered IDs,
 // source markers, geographic releases and exact ingestion revision. Its
 // existing row-validation stage materializes the snapshot; compression streams.
 const verified=readVerifiedStorageSnapshot(directory);
 if(verified.manifest_sha256!==files[0].sha256)fail('Source index changed during validation');
 return {files,total,revision:verified.revision,fingerprint:verified.manifest.snapshot_marker.fingerprint,source_backend:verified.manifest.source_backend};
}
function readCheckpoint(directory){
 const {value:manifest}=boundedJSON(directory,'checkpoint.json',checkpointLimits.manifestBytes);
 if(manifest?.version!==1||manifest.format!==format||manifest.status!=='complete'||manifest.compression!=='gzip-level-9-mtime-0-os-255'||!sha(manifest.source_manifest_sha256)||!sha(manifest.source_snapshot_fingerprint)||!integer(manifest.source_revision,0,Number.MAX_SAFE_INTEGER)||!['d1','postgres'].includes(manifest.source_backend)||!integer(manifest.raw_part_bytes,64*1024,checkpointLimits.rawPartBytes)||!Array.isArray(manifest.files)||!integer(manifest.files.length,15,checkpointLimits.files)||!Array.isArray(manifest.parts)||!integer(manifest.parts.length,1,checkpointLimits.parts))fail('Invalid storage checkpoint manifest');
 let totalFiles=0,fileIndex=1;
 for(const file of manifest.files){if(!file||!integer(file.bytes,1,checkpointLimits.fileBytes)||!sha(file.sha256))fail('Invalid original checkpoint file');totalFiles+=file.bytes;if(totalFiles>checkpointLimits.totalRawBytes)fail('Checkpoint original byte limit exceeded');}
 if(manifest.files[0].path!=='index.json'||manifest.files[0].sha256!==manifest.source_manifest_sha256)fail('Checkpoint original index hash mismatch');
 for(const collection of storageExportCollections){
  let number=0;
  while(fileIndex<manifest.files.length&&manifest.files[fileIndex].path?.startsWith(collection+'/')){
   if(manifest.files[fileIndex].path!==`${collection}/part-${String(++number).padStart(6,'0')}.json`)fail('Noncanonical original checkpoint file sequence');fileIndex++;
  }
  if(!number)fail('Checkpoint is missing an original collection');
 }
 if(fileIndex!==manifest.files.length)fail('Unsafe or unexpected original checkpoint paths');
 let totalRaw=0,totalCompressed=0;
 for(const [index,part]of manifest.parts.entries()){
  if(!part||part.path!==`parts/part-${String(index+1).padStart(6,'0')}.gz`||!integer(part.bytes,1,checkpointLimits.compressedPartBytes-1)||!integer(part.raw_bytes,1,manifest.raw_part_bytes)||index<manifest.parts.length-1&&part.raw_bytes!==manifest.raw_part_bytes||!sha(part.sha256)||!sha(part.raw_sha256))fail('Invalid compressed checkpoint part');
  totalRaw+=part.raw_bytes;totalCompressed+=part.bytes;
  if(totalRaw>checkpointLimits.totalRawBytes||totalCompressed>checkpointLimits.totalRawBytes*2)fail('Checkpoint aggregate byte limit exceeded');
 }
 if(totalRaw!==totalFiles||manifest.total_raw_bytes!==totalRaw||manifest.total_gzip_bytes!==totalCompressed)fail('Checkpoint file and part byte totals disagree');
 return manifest;
}
function stagingDirectory(output){
 output=path.resolve(output);fs.mkdirSync(path.dirname(output),{recursive:true});
 const staging=path.join(path.dirname(output),`.${path.basename(output)}.staging-${randomUUID()}`);fs.mkdirSync(staging,{mode:0o700});return {output,staging};
}
function durableFile(file,bytes){const fd=fs.openSync(file,'wx',0o600);try{fs.writeFileSync(fd,bytes);fs.fsyncSync(fd);}finally{fs.closeSync(fd);}}
function syncFile(file){const fd=fs.openSync(file,'r');try{fs.fsyncSync(fd);}finally{fs.closeSync(fd);}}
async function* sourceChunks(directory,files,partBytes){
 let chunks=[],size=0;
 for(const file of files){
  const actual=regularFile(directory,file.path,checkpointLimits.fileBytes),hash=createHash('sha256');let count=0;
  for await(const chunk of fs.createReadStream(actual.file,{highWaterMark:64*1024})){
   count+=chunk.length;if(count>file.bytes)fail('Source checkpoint file changed while packing');hash.update(chunk);
   let at=0;
   while(at<chunk.length){const take=Math.min(partBytes-size,chunk.length-at);chunks.push(chunk.subarray(at,at+take));size+=take;at+=take;if(size===partBytes){yield Buffer.concat(chunks,size);chunks=[];size=0;}}
  }
  if(count!==file.bytes||hash.digest('hex')!==file.sha256)fail('Source checkpoint file changed while packing');
 }
 if(size)yield Buffer.concat(chunks,size);
}
async function gzipPart(file,raw){
 const hash=createHash('sha256');let bytes=0,header=Buffer.alloc(0),normalized=false;
 const measure=new Transform({transform(chunk,encoding,callback){
  try{
   if(!normalized){header=Buffer.concat([header,chunk]);if(header.length<10){callback();return;}if(header[0]!==31||header[1]!==139||header[2]!==8||header[3]!==0)fail('Unexpected gzip header');header.fill(0,4,8);header[9]=255;chunk=header;normalized=true;}
   bytes+=chunk.length;if(bytes>=checkpointLimits.compressedPartBytes)fail('Compressed checkpoint part exceeds Git bound');hash.update(chunk);callback(null,chunk);
  }catch(error){callback(error);}
 }});
 await pipeline(Readable.from([raw]),createGzip({level:9}),measure,fs.createWriteStream(file,{flags:'wx',mode:0o600}));syncFile(file);
 return {bytes,sha256:hash.digest('hex'),raw_bytes:raw.length,raw_sha256:digest(raw)};
}

/** Verify every compressed and original byte, optionally rebuilding files in a
 * private staging directory. Gunzip output is bounded independently of headers.
 */
async function decodeCheckpoint(directory,manifest,destination=null){
 let fileIndex=0,fileOffset=0,fileHash=createHash('sha256'),fd=null;
 function openFile(){if(!destination)return;const file=path.join(destination,manifest.files[fileIndex].path);fs.mkdirSync(path.dirname(file),{recursive:true,mode:0o700});fd=fs.openSync(file,'wx',0o600);}
 function consume(chunk){
  let at=0;
  while(at<chunk.length){
   const file=manifest.files[fileIndex];if(!file)fail('Checkpoint decompressed beyond original files');
   if(!fileOffset)openFile();const take=Math.min(file.bytes-fileOffset,chunk.length-at),piece=chunk.subarray(at,at+take);fileHash.update(piece);
   if(fd!==null){let written=0;while(written<piece.length){const count=fs.writeSync(fd,piece,written,piece.length-written);if(count<1)fail('Checkpoint write made no progress');written+=count;}}
   fileOffset+=take;at+=take;
   if(fileOffset===file.bytes){if(fd!==null){fs.fsyncSync(fd);fs.closeSync(fd);fd=null;}if(fileHash.digest('hex')!==file.sha256)fail('Original checkpoint file hash mismatch');fileIndex++;fileOffset=0;fileHash=createHash('sha256');}
  }
 }
 try{
  for(const part of manifest.parts){
   const actual=regularFile(directory,part.path,checkpointLimits.compressedPartBytes-1);
   if(actual.bytes!==part.bytes||await hashFile(actual.file,part.bytes)!==part.sha256)fail('Compressed checkpoint hash or size mismatch');
   const rawHash=createHash('sha256');let rawBytes=0;
   const sink=new Writable({write(chunk,encoding,callback){try{rawBytes+=chunk.length;if(rawBytes>part.raw_bytes||rawBytes>manifest.raw_part_bytes)fail('Checkpoint decompression byte limit exceeded');rawHash.update(chunk);consume(chunk);callback();}catch(error){callback(error);}}});
   await pipeline(fs.createReadStream(actual.file),createGunzip({chunkSize:64*1024}),sink);
   if(rawBytes!==part.raw_bytes||rawHash.digest('hex')!==part.raw_sha256)fail('Decompressed checkpoint hash or size mismatch');
  }
  if(fileIndex!==manifest.files.length||fileOffset)fail('Checkpoint original files are incomplete');
 }finally{if(fd!==null)fs.closeSync(fd);}
}
function summary(manifest,status){return {version:1,status,source_manifest_sha256:manifest.source_manifest_sha256,source_snapshot_fingerprint:manifest.source_snapshot_fingerprint,source_revision:manifest.source_revision,source_backend:manifest.source_backend,files:manifest.files.length,parts:manifest.parts.length,total_raw_bytes:manifest.total_raw_bytes,total_gzip_bytes:manifest.total_gzip_bytes,all_fourteen_tables_preserved:true,json_text_preserved:true,network_requests:0,database_calls:0,media_bytes_included:false};}

export async function packStorageCheckpoint({directory,output,rawPartBytes=checkpointLimits.rawPartBytes}={}){
 if(typeof directory!=='string'||typeof output!=='string'||!directory||!output||!integer(rawPartBytes,64*1024,checkpointLimits.rawPartBytes))fail('Supply source/output directories and a 64 KiB–8 MiB raw part size');
 directory=path.resolve(directory);output=path.resolve(output);
 if(output===directory||output.startsWith(directory+path.sep))fail('Checkpoint output must be outside the source snapshot');
 const source=canonicalSourceFiles(directory);
 if(fs.existsSync(output)){
  const existing=readCheckpoint(output);
  if(existing.source_manifest_sha256!==source.files[0].sha256||existing.source_snapshot_fingerprint!==source.fingerprint||existing.source_revision!==source.revision||existing.source_backend!==source.source_backend||existing.raw_part_bytes!==rawPartBytes||JSON.stringify(existing.files)!==JSON.stringify(source.files))fail('Existing checkpoint differs; never overwrite retained evidence');
  await decodeCheckpoint(output,existing);return summary(existing,'verified-existing');
 }
 const stage=stagingDirectory(output);
 try{
  fs.mkdirSync(path.join(stage.staging,'parts'),{mode:0o700});const parts=[];let compressedBytes=0;
  for await(const raw of sourceChunks(directory,source.files,rawPartBytes)){
   if(parts.length>=checkpointLimits.parts)fail('Checkpoint compressed part count exceeded');
   const relative=`parts/part-${String(parts.length+1).padStart(6,'0')}.gz`,part=await gzipPart(path.join(stage.staging,relative),raw);parts.push({path:relative,...part});compressedBytes+=part.bytes;
  }
  const manifest={version:1,format,status:'complete',compression:'gzip-level-9-mtime-0-os-255',source_manifest_sha256:source.files[0].sha256,source_snapshot_fingerprint:source.fingerprint,source_revision:source.revision,source_backend:source.source_backend,raw_part_bytes:rawPartBytes,files:source.files,parts,total_raw_bytes:source.total,total_gzip_bytes:compressedBytes};
  const bytes=Buffer.from(JSON.stringify(manifest,null,2)+'\n');if(bytes.length>checkpointLimits.manifestBytes)fail('Checkpoint manifest byte limit exceeded');durableFile(path.join(stage.staging,'checkpoint.json'),bytes);
  readCheckpoint(stage.staging);await decodeCheckpoint(stage.staging,manifest);if(fs.existsSync(output))fail('Checkpoint output appeared during packing');fs.renameSync(stage.staging,output);return summary(manifest,'packed');
 }finally{fs.rmSync(stage.staging,{recursive:true,force:true});}
}

export async function unpackStorageCheckpoint({directory,output}={}){
 if(typeof directory!=='string'||typeof output!=='string'||!directory||!output)fail('Supply checkpoint/output directories');
 directory=path.resolve(directory);output=path.resolve(output);
 if(output===directory||output.startsWith(directory+path.sep))fail('Unpack output must be outside the retained checkpoint');
 const manifest=readCheckpoint(directory);
 if(fs.existsSync(output)){
  await decodeCheckpoint(directory,manifest);
  const original=canonicalSourceFiles(output);
  if(original.files[0].sha256!==manifest.source_manifest_sha256||original.fingerprint!==manifest.source_snapshot_fingerprint||original.revision!==manifest.source_revision||original.source_backend!==manifest.source_backend||JSON.stringify(original.files)!==JSON.stringify(manifest.files))fail('Existing unpacked snapshot differs; never overwrite retained evidence');
  return summary(manifest,'verified-existing');
 }
 const stage=stagingDirectory(output);
 try{
  await decodeCheckpoint(directory,manifest,stage.staging);
  const restored=canonicalSourceFiles(stage.staging);
  if(restored.files[0].sha256!==manifest.source_manifest_sha256||restored.fingerprint!==manifest.source_snapshot_fingerprint||restored.revision!==manifest.source_revision||restored.source_backend!==manifest.source_backend||JSON.stringify(restored.files)!==JSON.stringify(manifest.files))fail('Restored original snapshot identity mismatch');
  if(fs.existsSync(output))fail('Unpack output appeared during verification');fs.renameSync(stage.staging,output);return summary(manifest,'unpacked');
 }finally{fs.rmSync(stage.staging,{recursive:true,force:true});}
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{
  const [mode,directory,output,...extra]=process.argv.slice(2);if(!['pack','unpack'].includes(mode)||!directory||!output||extra.length)fail('Usage: node scripts/storage-checkpoint.mjs pack|unpack source-directory output-directory');
  const result=await(mode==='pack'?packStorageCheckpoint({directory,output}):unpackStorageCheckpoint({directory,output}));console.log(JSON.stringify(result));
 }catch{console.error('Storage checkpoint validation failed; retained source bytes were not replaced.');process.exitCode=1;}
}
