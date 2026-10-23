// Re-encode existing GPU words; never compile, coarsen or change the canonical grid.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';
import {gzipSync,gunzipSync} from 'node:zlib';
import {bindPreparedNativeFeatures as bindPreparedNativeFeaturesPure,additiveBaseReference as additiveBaseReferencePure} from '../src/reference-metadata.js';
import {canonicalValue} from '../src/native-grid.js';
const footprintHash=value=>createHash('sha256').update(JSON.stringify(canonicalValue(value))+'\n').digest('hex');
const bindPreparedNativeFeatures=(...args)=>bindPreparedNativeFeaturesPure(...args,footprintHash,bytes=>createHash('sha256').update(bytes).digest('hex'));
const additiveBaseReference=data=>additiveBaseReferencePure(data,footprintHash);
import {loadOwnershipAssets} from '../src/ownership-assets.js';
import {shuffleOwnershipBytes, unshuffleOwnershipBytes} from '../src/ownership-codec.js';

import {ownershipMetadata} from '../src/ownership-method.js';

const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const validHash = value => /^[a-f0-9]{64}$/.test(value ?? '');
const WORDS_PER_PART = 4194304; // At most16MiB of decoded GPU words per new part.

function encodeWords(words) {
  const encoded = shuffleOwnershipBytes(words);
  if (encoded.length > 32 * 1024 * 1024) throw Error('Ownership transport exceeds decoded byte limit');
  const decoded = unshuffleOwnershipBytes(encoded, words.length);
  const originalBytes = Buffer.from(words.buffer, words.byteOffset, words.byteLength);
  const decodedBytes = Buffer.from(decoded.buffer, decoded.byteOffset, decoded.byteLength);
  if (!originalBytes.equals(decodedBytes)) throw Error('Ownership transport changed canonical GPU words');
  const bytes = gzipSync(encoded, {level: 9});
  if (bytes.length > 8 * 1024 * 1024) throw Error('Ownership transport exceeds compressed byte limit');
  return {encoded, bytes, originalBytes, decodedBytes};
}

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
    const {encoded, bytes, originalBytes, decodedBytes} = encodeWords(words);
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

// Encode the already-admitted final GPU words, not a new scientific grid.
// Content-bound URLs preserve every unchanged compressed/decoded chunk across
// releases instead of renaming the entire bank for one changed ownership word.
export async function packageFinalStartupOwnership({ownership, expectedReference, destination, previousParts=[]}) {
  const metadata=ownershipMetadata(ownership,{requireNative:true,expectedReference});
  const encoded=await encodeFinalOwnershipWords({ownership,destination,previousParts});
  return {...encoded,pixelMap:{...metadata,...encoded.pixelMap}};
}

// Reference-free encoding arithmetic. A new E can bind these actual descriptors
// without a provisional or circular claim that new words belong to old E/N.
export async function encodeFinalOwnershipWords({ownership,destination,previousParts=[]}) {
  const metadata=Object.fromEntries(['version','coordinateBits','size','runWords','method','native_latitudes','reference_owner_sha256'].filter(key=>Object.hasOwn(ownership,key)).map(key=>[key,ownership[key]]));
  if(metadata.version!==2||metadata.method!=='native-linear-evenodd-first-owner-v1'||metadata.size!==262166||metadata.coordinateBits!==19
    ||!(ownership.rows instanceof Uint32Array)||ownership.rows.length!==metadata.size*2
    ||!(ownership.runs instanceof Uint32Array)||ownership.runs.length!==metadata.runWords||metadata.runWords%2!==0)
    throw Error('Complete final ownership words required');
  const parts=[],outputs=[];
  for(const kind of ['rows','runs'])for(let offset=0;offset<ownership[kind].length;offset+=WORDS_PER_PART){
    const words=ownership[kind].subarray(offset,offset+WORDS_PER_PART);
    const {bytes,decodedBytes}=encodeWords(words),sha256=digest(bytes),decoded_sha256=digest(decodedBytes);
    const prior=previousParts.find(p=>p.kind===kind&&p.offset===offset&&p.words===words.length
      &&p.encoding==='byte-shuffle'&&p.sha256===sha256&&p.decoded_sha256===decoded_sha256);
    const relative=prior?.path??`ownership-vintages/${sha256}/native-v1/ownership/${kind==='rows'?'rows':'startup-runs'}-${offset}.bin.gz`;
    if(!/^(?:ownership-vintages\/[a-f0-9]{64}\/)?native-v1\/ownership\/(?:rows|startup-runs)-[0-9]+\.bin\.gz$/.test(relative))
      throw Error('Unsafe final ownership part');
    await fs.mkdir(path.dirname(path.join(destination,relative)),{recursive:true});
    await fs.writeFile(path.join(destination,relative),bytes,{flag:'wx'});
    parts.push({kind,path:relative,offset,words:words.length,encoding:'byte-shuffle',sha256,decoded_sha256});
    outputs.push({path:relative,bytes:bytes.length,sha256});
  }
  return {pixelMap:{...metadata,parts},outputs,
    rows_sha256:digest(Buffer.from(ownership.rows.buffer,ownership.rows.byteOffset,ownership.rows.byteLength)),
    runs_word_stream_sha256:digest(Buffer.from(ownership.runs.buffer,ownership.runs.byteOffset,ownership.runs.byteLength))};
}

// Shared original-N binding for final preparation and ordinary copying.
export function validatePreparedNativeStartup({manifest,manifestSha,nativePixelMap,files}) {
  if(!validHash(manifestSha)||!Array.isArray(files))throw Error('Complete original native startup binding required');
  const metadata=ownershipMetadata(manifest),pins=new Map(files.map(pin=>[pin.path,pin]));
  for(const key of ['version','coordinateBits','size','runWords','method','footprints_sha256','hierarchy_sha256','geographic_release'])
    if(nativePixelMap?.[key]!==metadata[key])throw Error('Prepared startup metadata differs: '+key);
  const parts=nativePixelMap.parts;
  if(!Array.isArray(parts)||parts.length<2||new Set(parts.map(pin=>pin.path)).size!==parts.length)throw Error('Incomplete prepared startup ownership parts');
  const rows=manifest.parts.filter(pin=>pin.kind==='rows'),preparedRows=parts.filter(pin=>pin.kind==='rows');
  const prefix='ownership-vintages/'+manifestSha+'/';
  if(preparedRows.length!==rows.length||preparedRows.some((pin,i)=>
    (pin.path!==rows[i].path&&pin.path!==prefix+rows[i].path)||
    !isDeepStrictEqual({...pin,path:rows[i].path},rows[i])))throw Error('Immutable startup URL would be rebound: prepared startup row identity differs');
  let words=0;
  for(const part of parts){
    const pin=pins.get(part.path);
    if(!pin||pin.sha256!==part.sha256)throw Error('Prepared startup part is missing or rebound');
    if(part.kind==='rows')continue;
    if(part.kind!=='runs'||part.offset!==words||!Number.isSafeInteger(part.words)||part.words<=0||!part.path.startsWith('ownership-vintages/'+manifestSha+'/'))throw Error('Incomplete or foreign prepared startup run stream');
    words+=part.words;
  }
  if(words!==manifest.runWords)throw Error('Prepared startup run stream is incomplete');
  const latitude=nativePixelMap.native_latitudes;
  if(!isDeepStrictEqual(latitude,{...manifest.native_latitudes,transport_path:'native-v1/native-row-latitudes.f64le.gz'})||!pins.has(latitude.transport_path)||pins.get(latitude.transport_path).sha256!==latitude.sha256)throw Error('Prepared startup native latitude differs');
  if(nativePixelMap.canonical_grid_sha256!==undefined&&nativePixelMap.canonical_grid_sha256!==manifestSha)throw Error('Prepared startup canonical grid identity differs');
}

// One metadata admission shared by copying and the actual complete-word reader.
export function validatePreparedStartupIndex({index,indexRaw,manifest,manifestSha,selected,features}) {
  const metadata=ownershipMetadata(manifest);
  const authority=index.version===3,final=index.version===2||authority,proof=index.preparedOwnership;
  if((index.version!==1&&!final)||index.native_manifest_sha256!==manifestSha)
    throw Error('Prepared startup differs from selected native reference; regenerate matching startup products');
  if(final){
    const effective=authority?selected?.reference_release:selected?.envelope?.effective_reference;
    if(authority){
      if(!selected?.finalBank||selected.finalBank.bytes!==indexRaw.length||selected.finalBank.sha256!==digest(indexRaw)
        ||proof?.version!==3||index.additiveRelease!==undefined)throw Error('Prepared final bank differs from the one-way selected index pin');
      additiveBaseReference({preparedOwnership:proof,reference_release:effective,pixelMap:index.pixelMap});
    }
    if(!selected||!Array.isArray(features)||(!authority&&(proof?.version!==2||proof.selection_sha256!==digest(selected.selectionBytes)))
      ||proof.native_manifest_sha256!==manifestSha||(!authority&&!isDeepStrictEqual(index.additiveRelease,selected.envelope))
      ||!isDeepStrictEqual(proof.base_reference,selected.base)||!isDeepStrictEqual(proof.effective_reference,effective)
      ||index.release_id!==effective.id||index.footprints_sha256!==effective.footprints_sha256
      ||index.hierarchy_sha256!==effective.hierarchy_sha256)
      throw Error('Prepared final selection or content/effective reference differs');
    ownershipMetadata(index.pixelMap,{requireNative:true,expectedReference:effective});
    if(index.pixelMap.canonical_grid_sha256!==undefined)throw Error('Final ownership cannot claim original native words');
  }else if(selected||index.release_id!==manifest.geographic_release||index.footprints_sha256!==manifest.footprints_sha256
    ||index.hierarchy_sha256!==manifest.hierarchy_sha256)throw Error('Selected repairs require a corrected prepared bank');
  const nativePixelMap=final?proof.native_pixel_map:index.pixelMap;
  if(!Array.isArray(index.files)||!index.files.length||new Set(index.files.map(pin=>pin.path)).size!==index.files.length)throw Error('Incomplete prepared startup roster');
  for(const pin of index.files)if(typeof pin.path!=='string'||!pin.path.split('/').every(piece=>/^[A-Za-z0-9_.-]+$/.test(piece)&&piece!=='.'&&piece!=='..')||!Number.isSafeInteger(pin.bytes)||pin.bytes<=0||!validHash(pin.sha256))throw Error('Unsafe prepared startup member');
  const pins=new Map(index.files.map(pin=>[pin.path,pin]));
  if(final){
    if(!Array.isArray(index.compatibility_files)||!index.compatibility_files.length
      ||new Set(index.compatibility_files.map(p=>p.path)).size!==index.compatibility_files.length
      ||index.compatibility_files.some(p=>!isDeepStrictEqual(p,pins.get(p.path))))throw Error('Prepared compatibility roster differs');
    const current=new Set([...index.compatibility_files,...nativePixelMap.parts,...index.pixelMap.parts,...proof.context_parts]
      .map(p=>p.path));current.add(nativePixelMap.native_latitudes.transport_path);
    if(index.files.some(p=>!current.has(p.path))||current.size!==index.files.length)throw Error('Inactive final-bank member remains in current deployment');
  }
  validatePreparedNativeStartup({manifest,manifestSha,nativePixelMap,files:index.files});
  if(final){
    if(new Set(index.pixelMap.parts.map(p=>p.path)).size!==index.pixelMap.parts.length
      ||index.pixelMap.size!==nativePixelMap.size||index.pixelMap.coordinateBits!==nativePixelMap.coordinateBits
      ||!isDeepStrictEqual(index.pixelMap.native_latitudes,nativePixelMap.native_latitudes))throw Error('Final ownership part roster or original numerical domain differs');
    for(const kind of ['rows','runs']){
      let offset=0;
      for(const part of index.pixelMap.parts.filter(p=>p.kind===kind)){
        if(part.offset!==offset||!Number.isSafeInteger(part.words)||part.words<=0||part.encoding!=='byte-shuffle'
          ||!validHash(part.decoded_sha256)||pins.get(part.path)?.sha256!==part.sha256)
          throw Error('Incomplete or changed final ownership stream');
        offset+=part.words;
      }
      if(offset!==(kind==='rows'?metadata.size*2:index.pixelMap.runWords))throw Error('Incomplete final ownership word inventory');
    }
    if(index.pixelMap.parts.some(p=>!['rows','runs'].includes(p.kind)))throw Error('Unknown final ownership part kind');
    let offset=0;const contextPaths=new Set();
    if(!Array.isArray(proof.context_parts)||!proof.context_parts.length)throw Error('Missing prepared effective context');
    for(const pin of proof.context_parts){
      if(!/^geography\/effective-context-[a-f0-9]{64}\.json\.gz$/.test(pin.path)||contextPaths.has(pin.path)
        ||pin.offset!==offset||!Number.isSafeInteger(pin.features)||pin.features<1||pin.features>1500
        ||pin.encoding!=='gzip'||!Number.isSafeInteger(pin.decoded_bytes)||pin.decoded_bytes<1||pin.decoded_bytes>32*1024*1024
        ||!validHash(pin.decoded_sha256)||pins.get(pin.path)?.sha256!==pin.sha256||pins.get(pin.path)?.bytes!==pin.bytes)
        throw Error('Incomplete or rebound prepared effective context');
      contextPaths.add(pin.path);offset+=pin.features;
    }
    if(offset!==proof.owners||proof.owners!==features.length)throw Error('Prepared complete context roster differs');
  }
  return {authority,final,proof,pins,nativePixelMap};
}

// Prepared deployment bytes are regenerated only when a reviewed native bank
// changes. Ordinary builds authenticate and copy them without decoding the
// complete GPU stream or recompressing an already accepted transport.
export async function packagePreparedStartupOwnership({manifest,manifestSha,source,destination,selected,features}) {
  if(!validHash(manifestSha))throw Error('Prepared startup requires the selected native manifest hash');
  const root=await fs.realpath(source);
  if(root!==path.resolve(source))throw Error('Prepared startup source must be ordinary');
  const indexFile=path.join(root,'index.json');
  if(await fs.realpath(indexFile)!==indexFile||!(await fs.lstat(indexFile)).isFile())throw Error('Prepared startup index must be ordinary');
  const indexRaw=await fs.readFile(indexFile),index=JSON.parse(indexRaw);
  const inputInventory=[];
  const consumed=async(name,raw)=>{const stat=await fs.lstat(path.join(root,name));
    inputInventory.push({path:name,mode:(stat.mode&0o111)?'100755':'100644',bytes:raw.length,sha256:digest(raw),
      git_blob_oid:createHash('sha1').update('blob '+raw.length+'\0').update(raw).digest('hex'),whole_body_consumed:true});};
  await consumed('index.json',indexRaw);
  const {final,proof,pins}=validatePreparedStartupIndex({index,indexRaw,manifest,manifestSha,selected,features});
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
  // Authenticate every current and retained compatibility URL before writing.
  const bodies=[];
  for(const pin of index.files){
    const file=path.join(root,pin.path);
    if(await fs.realpath(file)!==file||!(await fs.lstat(file)).isFile())throw Error('Prepared startup member must be ordinary');
    const bytes=await fs.readFile(file);
    if(bytes.length!==pin.bytes||digest(bytes)!==pin.sha256)throw Error('Prepared startup bytes changed: '+pin.path);
    await consumed(pin.path,bytes);
    bodies.push({pin,bytes});
  }
  if(final){
    const rawByPath=new Map(bodies.map(({pin,bytes})=>[pin.path,bytes]));
    const context=proof.context_parts.map(pin=>{const raw=gunzipSync(rawByPath.get(pin.path),{maxOutputLength:pin.decoded_bytes});
      if(raw.length!==pin.decoded_bytes||digest(raw)!==pin.decoded_sha256)throw Error('Prepared context decoded bytes differ');
      return JSON.parse(raw);});
    bindPreparedNativeFeatures({preparedOwnership:proof,referenceMetadata:selected.referenceMetadata},features,context);
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
  return {pixelMap:index.pixelMap,files:index.files,input_inventory:inputInventory,...(final?{preparedOwnership:proof}:{})};
}

// Load exactly the selected finished bank for preparation/conservation. This
// authenticates transport and words, not acceptance of a caller's selection.
export async function readPreparedFinalOwnership({indexRaw,manifest,manifestSha,selected,features,ownerCount=features?.length,read}) {
  const index=JSON.parse(indexRaw);
  if(![2,3].includes(index.version))throw Error('A complete prepared final bank is required');
  if(!Number.isSafeInteger(ownerCount)||ownerCount<1)throw Error('Complete final owner denominator required');
  const {proof,pins}=validatePreparedStartupIndex({index,indexRaw,manifest,manifestSha,selected,features:features??new Array(ownerCount)});
  const bodies=new Map();
  async function whole(name){
    const pin=pins.get(name);if(!pin)throw Error('Final ownership input outside the complete prepared roster');
    if(!bodies.has(name)){
      const raw=Buffer.from(await read(pin));
      if(raw.length!==pin.bytes||digest(raw)!==pin.sha256)throw Error('Prepared final input whole identity differs: '+name);
      bodies.set(name,raw);
    }
    return bodies.get(name);
  }
  const ownership=await loadOwnershipAssets(index.pixelMap,async url=>{
    if(typeof url!=='string'||!url.startsWith('./'))throw Error('Unexpected prepared ownership URL');
    return new Response(await whole(url.slice(2)));
  },{requireNative:true,expectedReference:proof.effective_reference});
  if(digest(Buffer.from(ownership.rows.buffer,ownership.rows.byteOffset,ownership.rows.byteLength))!==proof.rows_sha256
    ||digest(Buffer.from(ownership.runs.buffer,ownership.runs.byteOffset,ownership.runs.byteLength))!==proof.runs_word_stream_sha256)
    throw Error('Prepared complete word stream differs from its declared identity');
  const context=[];
  for(const pin of proof.context_parts){
    const raw=gunzipSync(await whole(pin.path),{maxOutputLength:pin.decoded_bytes});
    if(raw.length!==pin.decoded_bytes||digest(raw)!==pin.decoded_sha256)throw Error('Prepared context decoded bytes differ');
    context.push(JSON.parse(raw));
  }
  // A body-only reader can bind the complete supplied denominator and context
  // schema without claiming independent source/acceptance authority. The private
  // checkpoint subsequently joins every value to its accepted certificate/base.
  const prepared=bindPreparedNativeFeatures({preparedOwnership:proof,referenceMetadata:selected.referenceMetadata},features??context.flat(),context);
  return {index,ownership,features:prepared};
}
