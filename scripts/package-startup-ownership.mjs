// Re-encode existing GPU words; never compile, coarsen or change the canonical grid.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';
import {gzipSync} from 'node:zlib';
import {loadOwnershipAssets} from '../src/ownership-assets.js';
import {shuffleOwnershipBytes, unshuffleOwnershipBytes} from '../src/ownership-codec.js';

import {ownershipMetadata} from '../src/ownership-method.js';

const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const validHash = value => /^[a-f0-9]{64}$/.test(value ?? '');
const WORDS_PER_PART = 4194304; // At most16MiB of decoded GPU words per new part.

export async function packageStartupOwnership({manifest, source, destination}) {
  const metadata=ownershipMetadata(manifest);
  const native=metadata.method==='native-linear-evenodd-first-owner-v1';
  const assetPattern=native?/^native-v1\/ownership\/(?:rows|runs)-[0-9]+\.bin\.gz$/:/^ownership\/(?:rows|runs)-[0-9]+\.bin\.gz$/;
  if (manifest.version !== 2 || !Array.isArray(manifest.parts) ||
      manifest.parts.some(part => !assetPattern.test(part.path) ||
        !validHash(part.sha256) || !validHash(part.decoded_sha256)) ||
      new Set(manifest.parts.map(part => part.path)).size !== manifest.parts.length) throw Error('Invalid canonical ownership input');
  const inputs = [], byPath = new Map(manifest.parts.map(part => ['./' + part.path, part]));
  const original = await loadOwnershipAssets(manifest, async url => {
    const part = byPath.get(url);
    if (!part) throw Error('Ownership input outside declared roster');
    const bytes = await fs.readFile(path.join(source, part.path));
    if (bytes.length > 32 * 1024 * 1024 || digest(bytes) !== part.sha256) throw Error('Canonical ownership input changed');
    inputs.push({path: part.path, bytes: bytes.length, sha256: digest(bytes), decoded_sha256: part.decoded_sha256});
    return new Response(bytes);
  });
  const parts = manifest.parts.filter(part => part.kind === 'rows'), receipts = [];
  await fs.mkdir(path.join(destination, native?'native-v1/ownership':'ownership'), {recursive: true});
  for (let offset = 0; offset < original.runs.length; offset += WORDS_PER_PART) {
    const words = original.runs.subarray(offset, Math.min(offset + WORDS_PER_PART, original.runs.length));
    const encoded = shuffleOwnershipBytes(words);
    if (encoded.length > 32 * 1024 * 1024) throw Error('Ownership transport exceeds decoded byte limit');
    const decoded = unshuffleOwnershipBytes(encoded, words.length);
    const originalBytes = Buffer.from(words.buffer, words.byteOffset, words.byteLength);
    const decodedBytes = Buffer.from(decoded.buffer, decoded.byteOffset, decoded.byteLength);
    if (!originalBytes.equals(decodedBytes)) throw Error('Ownership transport changed canonical GPU words');
    const bytes = gzipSync(encoded, {level: 9});
    if (bytes.length > 8 * 1024 * 1024) throw Error('Ownership transport exceeds compressed byte limit');
    const relative = `${native?'native-v1/ownership':'ownership'}/startup-runs-${offset}.bin.gz`;
    await fs.writeFile(path.join(destination, relative), bytes, {flag: 'wx'});
    parts.push({kind: 'runs', path: relative, offset, words: words.length, encoding: 'byte-shuffle',
      sha256: digest(bytes), decoded_sha256: digest(decodedBytes)});
    receipts.push({path: relative, bytes: bytes.length, sha256: digest(bytes),
      uncompressed_bytes: encoded.length, uncompressed_sha256: digest(encoded),
      decoded_gpu_word_bytes: decodedBytes.length, decoded_gpu_word_sha256: digest(decodedBytes),
      original_gpu_word_sha256: digest(originalBytes), outcome: 'passed'});
  }
  const pixelMap = metadata;
  pixelMap.parts = parts;
  return {pixelMap, inputs: inputs.sort((a, b) => a.path.localeCompare(b.path)), outputs: receipts,
    rows_sha256: digest(Buffer.from(original.rows.buffer)), runs_word_stream_sha256: digest(Buffer.from(original.runs.buffer)),
    scope: 'Every decoded canonical GPU word preserved; stream digests are not containing-file hashes or geographic approval'};
}

// Prepared deployment bytes are regenerated only when a reviewed native bank
// changes. Ordinary builds authenticate and copy them without decoding the
// complete GPU stream or recompressing an already accepted transport.
export async function packagePreparedStartupOwnership({manifest,manifestSha,source,destination}) {
  if(!validHash(manifestSha))throw Error('Prepared startup requires the selected native manifest hash');
  const root=await fs.realpath(source);
  if(root!==path.resolve(source))throw Error('Prepared startup source must be ordinary');
  const indexFile=path.join(root,'index.json');
  if(await fs.realpath(indexFile)!==indexFile||!(await fs.lstat(indexFile)).isFile())throw Error('Prepared startup index must be ordinary');
  const index=JSON.parse(await fs.readFile(indexFile));
  const metadata=ownershipMetadata(manifest);
  if(index.version!==1||index.native_manifest_sha256!==manifestSha||index.release_id!==manifest.geographic_release||index.footprints_sha256!==manifest.footprints_sha256||index.hierarchy_sha256!==manifest.hierarchy_sha256)throw Error('Prepared startup differs from selected native reference; regenerate matching startup products');
  for(const key of ['version','coordinateBits','size','runWords','method','footprints_sha256','hierarchy_sha256','geographic_release'])if(index.pixelMap?.[key]!==metadata[key])throw Error('Prepared startup metadata differs: '+key);
  if(!Array.isArray(index.files)||!index.files.length||new Set(index.files.map(pin=>pin.path)).size!==index.files.length)throw Error('Incomplete prepared startup roster');
  const pins=new Map(index.files.map(pin=>[pin.path,pin]));
  const actual=[];
  async function inventory(relative=''){
    for(const entry of await fs.readdir(path.join(root,relative),{withFileTypes:true})){
      const name=relative?relative+'/'+entry.name:entry.name;
      if(entry.isDirectory())await inventory(name);
      else if(entry.isFile()){if(name!=='index.json')actual.push(name);}
      else throw Error('Prepared startup contains a nonordinary member');
    }
  }
  await inventory();
  if(JSON.stringify(actual.sort())!==JSON.stringify([...pins.keys()].sort()))throw Error('Prepared startup roster omits or invents a member');
  const parts=index.pixelMap.parts;
  if(!Array.isArray(parts)||parts.length<2||new Set(parts.map(pin=>pin.path)).size!==parts.length)throw Error('Incomplete prepared startup ownership parts');
  const rows=manifest.parts.filter(pin=>pin.kind==='rows'),preparedRows=parts.filter(pin=>pin.kind==='rows');
  const prefix='ownership-vintages/'+manifestSha+'/';
  if(preparedRows.length!==rows.length||preparedRows.some((pin,i)=>
    (pin.path!==rows[i].path&&pin.path!==prefix+rows[i].path)||
    JSON.stringify({...pin,path:rows[i].path})!==JSON.stringify(rows[i])))throw Error('Prepared startup row identity differs');
  let words=0;
  for(const part of parts){
    const pin=pins.get(part.path);
    if(!pin||pin.sha256!==part.sha256)throw Error('Prepared startup part is missing or rebound');
    if(part.kind==='rows')continue;
    if(part.kind!=='runs'||part.offset!==words||!Number.isSafeInteger(part.words)||part.words<=0||!part.path.startsWith('ownership-vintages/'+manifestSha+'/'))throw Error('Incomplete or foreign prepared startup run stream');
    words+=part.words;
  }
  if(words!==manifest.runWords)throw Error('Prepared startup run stream is incomplete');
  const latitude=index.pixelMap.native_latitudes;
  if(!isDeepStrictEqual(latitude,{...manifest.native_latitudes,transport_path:'native-v1/native-row-latitudes.f64le.gz'})||!pins.has(latitude.transport_path)||pins.get(latitude.transport_path).sha256!==latitude.sha256)throw Error('Prepared startup native latitude differs');
  if(index.pixelMap.canonical_grid_sha256!==undefined&&index.pixelMap.canonical_grid_sha256!==manifestSha)throw Error('Prepared startup canonical grid identity differs');
  // Authenticate every current and retained compatibility URL before writing.
  const bodies=[];
  for(const pin of index.files){
    if(typeof pin.path!=='string'||!pin.path.split('/').every(piece=>/^[A-Za-z0-9_.-]+$/.test(piece)&&piece!=='.'&&piece!=='..')||!Number.isSafeInteger(pin.bytes)||pin.bytes<=0||!validHash(pin.sha256))throw Error('Unsafe prepared startup member');
    const file=path.join(root,pin.path);
    if(await fs.realpath(file)!==file||!(await fs.lstat(file)).isFile())throw Error('Prepared startup member must be ordinary');
    const bytes=await fs.readFile(file);
    if(bytes.length!==pin.bytes||digest(bytes)!==pin.sha256)throw Error('Prepared startup bytes changed: '+pin.path);
    bodies.push({pin,bytes});
  }
  for(const {pin,bytes} of bodies){
    const file=path.resolve(destination,pin.path);
    for(let parent=path.dirname(file);;parent=path.dirname(parent)){
      const stat=await fs.lstat(parent).catch(error=>{if(error.code==='ENOENT')return null;throw error;});
      if(stat&&(!stat.isDirectory()||stat.isSymbolicLink()))throw Error('Prepared startup destination must be ordinary');
      if(parent===path.dirname(parent))break;
    }
    await fs.mkdir(path.dirname(file),{recursive:true});
    await fs.writeFile(file,bytes,{flag:'wx'});
  }
  return {pixelMap:index.pixelMap};
}
