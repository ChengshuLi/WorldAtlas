// Explicit transport preparation for a reviewed native update. Never run by a build.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';
import {gzipSync,gunzipSync} from 'node:zlib';
import {loadOwnershipAssets} from '../src/ownership-assets.js';
import {additiveBaseReference,loadAdditiveNativePatch} from '../src/effective-footprint.js';
import {originalNativeReference,scientificNativeSelection,validateReferenceMetadataHeader,projectReferenceOwners} from '../src/reference-metadata.js';
import {packageFinalStartupOwnership,validatePreparedNativeStartup} from './package-startup-ownership.mjs';

import {readBuildOwnershipSelection, selectBuildOwnership} from './select-build-ownership.mjs';
import {readGeographicReleaseManifest} from './read-geographic-release-manifest.mjs';
import {packageNativeLatitudes} from './package-native-latitudes.mjs';
import {ownershipMetadata} from '../src/ownership-method.js';
import {packageVersionedStartupOwnership} from '../coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/startup-vintage.mjs';

const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const compare = (a, b) => a < b ? -1 : a > b ? 1 : 0;
const defaultPrevious = 'data/canonical-grid/current-startup';
function need(value, message) { if (!value) throw Error(message); }
function safe(relative) {
  need(typeof relative === 'string' && relative.split('/').every(piece =>
    /^[A-Za-z0-9_.-]+$/.test(piece) && piece !== '.' && piece !== '..'), 'Unsafe startup member path');
  return relative;
}
async function stat(file) {
  return fs.lstat(file).catch(error => { if (error.code === 'ENOENT') return null; throw error; });
}
async function ordinary(file, directory = false) {
  const info = await fs.lstat(file);
  need((directory ? info.isDirectory() : info.isFile()) && await fs.realpath(file) === file,
    'Startup inputs and ancestors must be ordinary');
  return info;
}
async function read(file, pin) {
  const info = await ordinary(file);
  need(info.size <= 32 * 1024 * 1024, 'Startup input exceeds existing file limit');
  const bytes = await fs.readFile(file);
  if (pin) need(bytes.length === pin.bytes && digest(bytes) === pin.sha256, 'Startup bytes changed: ' + pin.path);
  return bytes;
}
async function inventory(root, relative = '') {
  const files = [];
  for (const entry of await fs.readdir(path.join(root, relative), {withFileTypes: true})) {
    const name = safe(relative ? relative + '/' + entry.name : entry.name);
    if (entry.isDirectory()) files.push(...await inventory(root, name));
    else {
      const bytes = await read(path.join(root, name));
      files.push({path: name, bytes: bytes.length, sha256: digest(bytes)});
    }
  }
  return files.sort((a, b) => compare(a.path, b.path));
}
function deploymentPath(name) {
  safe(name);
  need(/^(?:ownership-vintages\/[a-f0-9]{64}\/)?native-v1\/ownership\/(?:rows|startup-runs)-[0-9]+\.bin\.gz$/.test(name) ||
    name === 'native-v1/native-row-latitudes.f64le.gz' || /^geography\/effective-context-[a-f0-9]{64}\.json\.gz$/.test(name), 'Unexpected startup deployment member');
}
async function previousBank(source) {
  await ordinary(source, true);
  const index = JSON.parse(await read(path.join(source, 'index.json')));
  need((index.version === 1 || index.version === 2) && hash(index.native_manifest_sha256) && hash(index.footprints_sha256) &&
    hash(index.hierarchy_sha256) && typeof index.release_id === 'string' &&
    index.pixelMap?.method === 'native-linear-evenodd-first-owner-v1' &&
    Array.isArray(index.files) && index.files.length > 0, 'Invalid previous startup bank');
  ownershipMetadata(index.pixelMap, {requireNative: true, expectedReference: {id: index.release_id,
    footprints_sha256: index.footprints_sha256, hierarchy_sha256: index.hierarchy_sha256}});
  need(index.pixelMap.canonical_grid_sha256 === undefined || index.pixelMap.canonical_grid_sha256 === index.native_manifest_sha256,
    'Previous startup manifest identity differs');
  for (const pin of index.files) {
    deploymentPath(pin.path);
    need(Number.isSafeInteger(pin.bytes) && pin.bytes > 0 && hash(pin.sha256), 'Invalid previous startup pin');
  }
  const actual = (await inventory(source)).filter(pin => pin.path !== 'index.json');
  need(isDeepStrictEqual(actual, index.files), 'Previous startup roster or bytes changed');
  const pins = new Map(actual.map(pin => [pin.path, pin]));
  need(index.pixelMap.parts?.length > 1 && index.pixelMap.parts.every(part => pins.get(part.path)?.sha256 === part.sha256) &&
    pins.get(index.pixelMap.native_latitudes?.transport_path)?.sha256 === index.pixelMap.native_latitudes?.sha256 &&
    actual.some(pin => /^native-v1\/ownership\/startup-runs-/.test(pin.path)), 'Incomplete previous startup compatibility bank');
  if(index.version===2){
    need(index.preparedOwnership?.version===2&&index.preparedOwnership.native_manifest_sha256===index.native_manifest_sha256,
      'Previous final bank lost its original native binding');
    const native=index.preparedOwnership.native_pixel_map;
    ownershipMetadata(native,{requireNative:true,expectedReference:originalNativeReference(native)});
    need(native.canonical_grid_sha256===index.native_manifest_sha256&&native.parts.every(p=>pins.get(p.path)?.sha256===p.sha256),
      'Previous original native stream is incomplete');
  }
  return index;
}
async function addFile(bank, source, pin, targetPath = pin.path) {
  deploymentPath(targetPath);
  const bytes = await read(path.join(source, pin.path), pin);
  const target = path.join(bank, targetPath);
  if (await stat(target)) {
    need((await read(target)).equals(bytes), 'Immutable startup URL would be rebound: ' + targetPath);
    return;
  }
  await fs.mkdir(path.dirname(target), {recursive: true});
  await fs.writeFile(target, bytes, {flag: 'wx'});
}
async function selectedSource(manifest, source, temporary) {
  let missing = false;
  for (const part of manifest.parts) {
    safe(part.path);
    need(/^(?:native-v1\/ownership\/(?:rows|runs)-[0-9]+\.bin\.gz)$/.test(part.path), 'Unexpected selected native member');
    if (await stat(path.join(source, part.path))) await read(path.join(source, part.path), part);
    else missing = true;
  }
  if (!missing) return source;
  const transport = manifest.native_asset_transport, pin = transport?.index;
  need(transport?.version === 1 && transport.kind === 'ordered-exact-original-byte-fragments' && pin,
    'Selected native members are missing and have no exact-byte transport');
  const indexPath = path.resolve(safe(pin.path));
  const index = JSON.parse(await read(indexPath, pin));
  need(index.files?.length === manifest.parts.length && transport.logical_assets === manifest.parts.length &&
    transport.original_compressed_bytes === index.whole_bytes &&
    manifest.parts.every(part => index.files.filter(file => file.path === part.path &&
      file.bytes === part.bytes && file.sha256 === part.sha256).length === 1), 'Native transport roster differs from selected manifest');
  const {restoreWholeImage} = await import('./evidence/restore-whole-image.mjs');
  const restored = path.join(temporary, 'selected-native');
  restoreWholeImage(path.dirname(indexPath), restored, {expectedIndexSha: pin.sha256});
  for (const part of manifest.parts) await read(path.join(restored, part.path), part);
  return restored;
}

// The normal finalization boundary prepares the selected final words once. The
// original native bank and every scientific product keep their own identities.
export async function prepareSelectedStartupOwnership({selectionBytes,manifest,previous,readNative,readPin,destination}) {
  need([1,2].includes(previous?.version)&&Array.isArray(previous.files),'Authenticated previous prepared index required');
  const nativePixelMap=previous.preparedOwnership?.native_pixel_map??previous.pixelMap,nativeFiles=previous.files,previousParts=previous.pixelMap.parts;
  const compatibility=previous.version===1?previous.files:previous.compatibility_files;
  need(Array.isArray(compatibility)&&compatibility.length>0&&new Set(compatibility.map(pin=>pin.path)).size===compatibility.length
    &&compatibility.every(pin=>previous.files.some(old=>isDeepStrictEqual(pin,old))),'Previous compatibility roster differs');
  const selection=JSON.parse(selectionBytes),manifestRaw=Buffer.from(await readPin(selection.additive_release));
  need(manifestRaw.length===selection.additive_release.bytes&&digest(manifestRaw)===selection.additive_release.sha256,
    'Selected additive sidecar whole identity differs');
  const sidecar=JSON.parse(manifestRaw);
  need(sidecar.version===2&&sidecar.kind==='retained-native-additive-selection-v2'&&isDeepStrictEqual(sidecar.base_selection,scientificNativeSelection(selection)),
    'Prepared final native selection differs');
  const whole=async pin=>{
    need(pin&&Number.isSafeInteger(pin.bytes)&&pin.bytes>0&&hash(pin.sha256),'Complete final-map input pin required');
    const raw=Buffer.from(await readPin(pin));
    need(raw.length===pin.bytes&&digest(raw)===pin.sha256,'Final-map input whole identity differs: '+pin.path);
    return raw;
  };
  const wrapped=JSON.parse(await whole(sidecar.runtime_envelope)),release=wrapped.additiveRelease??wrapped;
  const base=additiveBaseReference({additiveRelease:release,reference_release:release.effective_reference});
  const bodies=new Map();
  need(Object.keys(sidecar.logical_asset_map??{}).sort().join(',')==='base_manifest,ledger,owner_roster,patch',
    'Incomplete final-map scientific product roster');
  for(const role of ['base_manifest','ledger','owner_roster','patch']){
    const pin=sidecar.logical_asset_map[role],asset=release[role];
    need(pin.bytes===asset.bytes&&pin.sha256===asset.sha256
      &&(pin.decoded_bytes??pin.bytes)===(asset.decoded_bytes??asset.bytes)
      &&(pin.decoded_sha256??pin.sha256)===(asset.decoded_sha256??asset.sha256),
      'Final-map logical/source identity differs: '+role);
    bodies.set(asset.path,await whole(pin));
  }
  need(selection.sha256===release.base_manifest.sha256
    &&isDeepStrictEqual(JSON.parse(bodies.get(release.base_manifest.path)),manifest),
    'Final-map original native manifest differs');
  validatePreparedNativeStartup({manifest,manifestSha:selection.sha256,nativePixelMap,files:nativeFiles});
  const original=originalNativeReference(manifest);
  need(manifest.original_assets.bounds.sha256===release.owner_roster.sha256,
    'Final-map original owner roster differs');
  const roster=JSON.parse(gunzipSync(bodies.get(release.owner_roster.path),{maxOutputLength:release.owner_roster.decoded_bytes}));
  let projection,referenceMetadata;
  if(selection.reference_projection){
    const raw=await whole(selection.reference_projection);projection=JSON.parse(raw);
    const references=validateReferenceMetadataHeader(projection,{selection,manifest});
    referenceMetadata={version:1,asset:{path:'reference-metadata/current.json',bytes:raw.length,sha256:digest(raw)},
      native_reference:references.native,reference:references.reference};
    bodies.set(referenceMetadata.asset.path,raw);
  }
  const owners=projection?projectReferenceOwners(roster,projection.location_changes,projection.provinces):roster;
  const properties=new Map((projection?.location_changes??[]).map(c=>[c.location_id,c.after_properties]));
  const features=owners.map(owner=>({id:owner.id,pixelIndex:owner.index,geometry:null,
    properties:properties.get(owner.id)??{id:owner.id,parent_id:owner.province_id}}));
  const native=await loadOwnershipAssets(nativePixelMap,async url=>new Response(await readNative(url.slice(2))),
    {requireNative:true,expectedReference:original});
  const data={reference_release:release.effective_reference,additiveRelease:release,
    pixelMap:{...nativePixelMap,canonical_grid_sha256:selection.sha256},...(referenceMetadata?{referenceMetadata}:{})};
  const final=await loadAdditiveNativePatch(data,features,native,{fetcher:async url=>{
    const raw=bodies.get(url.slice(2));need(raw,'Undeclared final-map scientific input');return new Response(raw);
  }});
  const packaged=await packageFinalStartupOwnership({ownership:final,expectedReference:release.effective_reference,
    destination,previousParts});
  const contextParts=[];
  for(let offset=0;offset<features.length;offset+=1500){
    const raw=Buffer.from(JSON.stringify(features.slice(offset,offset+1500))),bytes=gzipSync(raw,{level:9});
    need(raw.length<=32*1024*1024&&bytes.length<=8*1024*1024,'Prepared effective context exceeds existing part limits');
    const sha256=digest(bytes),relative=`geography/effective-context-${sha256}.json.gz`;
    await fs.mkdir(path.join(destination,'geography'),{recursive:true});
    await fs.writeFile(path.join(destination,relative),bytes,{flag:'wx'});
    contextParts.push({path:relative,bytes:bytes.length,sha256,encoding:'gzip',decoded_bytes:raw.length,
      decoded_sha256:digest(raw),offset,features:Math.min(1500,features.length-offset)});
  }
  const preparedOwnership={version:2,selection_sha256:digest(selectionBytes),native_manifest_sha256:selection.sha256,
    native_pixel_map:{...nativePixelMap,canonical_grid_sha256:selection.sha256},base_reference:base,effective_reference:release.effective_reference,
    context_parts:contextParts,owners:features.length,reference_owner_sha256:final.reference_owner_sha256,
    rows_sha256:packaged.rows_sha256,runs_word_stream_sha256:packaged.runs_word_stream_sha256,
    effective_footprint_domain:final.effective_footprint_domain,additive_patch_sha256:final.additive_patch_sha256,
    additive_ledger_sha256:final.additive_ledger_sha256,additive_added_cells:final.additive_added_cells,
    ...(final.additive_authority_registry_sha256?{additive_authority_registry_sha256:final.additive_authority_registry_sha256}:{}),
    ...(final.additive_rule_sha256?{additive_rule_sha256:final.additive_rule_sha256}:{})};
  return {version:2,compatibility_files:compatibility,native_manifest_sha256:selection.sha256,release_id:release.effective_reference.id,
    footprints_sha256:release.effective_reference.footprints_sha256,hierarchy_sha256:release.effective_reference.hierarchy_sha256,
    pixelMap:packaged.pixelMap,preparedOwnership,additiveRelease:release,
    ...(referenceMetadata?{referenceMetadata}:{})};
}

export async function prepareStartupOwnership({output, previous = defaultPrevious, manifest: manifestPath, sha256} = {}) {
  need(typeof output === 'string' && output.length > 0 && !output.includes('\\') &&
    !output.split('/').includes('..'), 'A fresh --output without traversal is required');
  need((manifestPath === undefined) === (sha256 === undefined) && (sha256 === undefined || hash(sha256)),
    'Explicit native selection requires both --manifest and --sha256');
  output = path.resolve(output);
  previous = path.resolve(previous);
  await ordinary(path.dirname(output), true);
  need(!await stat(output), 'Startup output must be fresh');
  const inside = (root, child) => child === root || child.startsWith(root + path.sep);
  need(!inside(previous, output) && !inside(path.resolve(defaultPrevious), output), 'Output cannot be inside an input startup bank');
  const selection = manifestPath === undefined ? await readBuildOwnershipSelection({env: {}}) :
    {manifestPath: safe(manifestPath), expectedSha256: sha256, requireNative: true};
  need(selection.requireNative, 'Startup preparation requires the committed native selection');
  await read(path.resolve(safe(selection.manifestPath)));
  const reference = readGeographicReleaseManifest().releases.at(-1);
  const selected = await selectBuildOwnership({...selection, expectedReference: reference});
  need(!selection.releaseId||selection.releaseId===selected.manifest.geographic_release,'Selected original native release differs');
  const selectionBytes=manifestPath===undefined?await read(path.resolve('data/ownership-selection.json')):null;
  const currentSelection=selectionBytes?JSON.parse(selectionBytes):null;
  need(!inside(path.resolve(selected.source), output), 'Output cannot be inside the selected native source bank');
  const retained = await previousBank(previous);
  const temporary = await fs.mkdtemp(path.join(path.dirname(output), '.prepare-startup-'));
  let ownsOutput = false;
  try {
    const bank = path.join(temporary, 'bank');
    await fs.mkdir(bank);
    const priorNative=retained.preparedOwnership?.native_pixel_map??retained.pixelMap;
    const fixed=retained.version===1?retained.files:retained.compatibility_files;
    need(Array.isArray(fixed)&&fixed.length>0&&fixed.every(pin=>retained.files.some(old=>isDeepStrictEqual(pin,old))), 'Previous compatibility roster differs');
    const kept=new Set([...fixed,...priorNative.parts].map(pin=>pin.path));kept.add(priorNative.native_latitudes.transport_path);
    for (const pin of retained.files.filter(pin=>kept.has(pin.path))) await addFile(bank, previous, pin);
    let pixelMap;
    if(retained.native_manifest_sha256===selected.sha256){
      pixelMap=retained.preparedOwnership?.native_pixel_map??retained.pixelMap;
      validatePreparedNativeStartup({manifest:selected.manifest,manifestSha:selected.sha256,nativePixelMap:pixelMap,files:retained.files});
    }else{
      const source=await selectedSource(selected.manifest,path.resolve(selected.source),temporary);
      const generated=path.join(temporary,'generated');
      const packaged=await packageVersionedStartupOwnership({manifest:selected.manifest,manifestSha:selected.sha256,
        manifestPath:path.resolve(selected.manifestPath),source,destination:generated});
      const latitude=await packageNativeLatitudes({manifest:selected.manifest,expectedReference:originalNativeReference(selected.manifest),destination:generated});
      const prefix='ownership-vintages/'+selected.sha256+'/';
      for(const part of selected.manifest.parts.filter(p=>p.kind==='rows'))await addFile(bank,source,part,prefix+part.path);
      for(const pin of packaged.outputs)await addFile(bank,generated,pin);
      await addFile(bank,generated,latitude.receipt);
      pixelMap={...packaged.pixelMap,parts:packaged.pixelMap.parts.map(p=>p.kind==='rows'?{...p,path:prefix+p.path}:p),
        native_latitudes:latitude.native_latitudes,canonical_grid_sha256:selected.sha256};
    }
    const native=originalNativeReference(selected.manifest);
    let index={version:1,native_manifest_sha256:selected.sha256,release_id:native.id,
      footprints_sha256:native.footprints_sha256,hierarchy_sha256:native.hierarchy_sha256,pixelMap};
    if(currentSelection?.additive_release){
      const generated=path.join(temporary,'final');
      index=await prepareSelectedStartupOwnership({selectionBytes,manifest:selected.manifest,previous:{version:1,pixelMap,files:await inventory(bank)},
        readNative:name=>read(path.join(bank,safe(name))),destination:generated,
        readPin:async pin=>{
          const filename=path.resolve(safe(pin.path)),info=await ordinary(filename);
          need((pin.mode??'100644')==='100644'&&!(info.mode&0o111)&&info.size===pin.bytes,'Final-map input mode or length differs');
          return fs.readFile(filename);
        }});
      for(const pin of await inventory(generated))await addFile(bank,generated,pin);
    }
    index.files=await inventory(bank);
    await fs.mkdir(output); // Exclusive ownership: an existing directory or dangling link is never replaced.
    ownsOutput = true;
    for (const name of await fs.readdir(bank)) await fs.rename(path.join(bank, name), path.join(output, name));
    await fs.writeFile(path.join(output, 'index.json'), JSON.stringify(index) + '\n', {flag: 'wx'});
    return index;
  } catch (error) {
    if (ownsOutput) await fs.rm(output, {recursive: true, force: true});
    throw error;
  } finally {
    await fs.rm(temporary, {recursive: true, force: true});
  }
}

export function parseStartupArguments(args) {
  const options = {};
  for (let i = 0; i < args.length; i += 2) {
    const key = args[i];
    need(['--output', '--previous', '--manifest', '--sha256'].includes(key) && args[i + 1] &&
      !args[i + 1].startsWith('--') && !Object.hasOwn(options, key.slice(2)), 'Expected unique --output, --previous, --manifest or --sha256 options');
    options[key.slice(2)] = args[i + 1];
  }
  return options;
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const index = await prepareStartupOwnership(parseStartupArguments(process.argv.slice(2)));
    console.log(`Prepared ${index.files.length} authenticated startup files for ${index.native_manifest_sha256}`);
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
