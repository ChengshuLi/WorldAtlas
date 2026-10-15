// Explicit transport preparation for a reviewed native update. Never run by a build.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';
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
    name === 'native-v1/native-row-latitudes.f64le.gz', 'Unexpected startup deployment member');
}
async function previousBank(source) {
  await ordinary(source, true);
  const index = JSON.parse(await read(path.join(source, 'index.json')));
  need(index.version === 1 && hash(index.native_manifest_sha256) && hash(index.footprints_sha256) &&
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
  need(!selection.releaseId || selection.releaseId === reference?.id, 'Selected ownership belongs to another baseline release');
  const selected = await selectBuildOwnership({...selection, expectedReference: reference});
  need(!inside(path.resolve(selected.source), output), 'Output cannot be inside the selected native source bank');
  const retained = await previousBank(previous);
  const temporary = await fs.mkdtemp(path.join(path.dirname(output), '.prepare-startup-'));
  let ownsOutput = false;
  try {
    const bank = path.join(temporary, 'bank');
    await fs.mkdir(bank);
    for (const pin of retained.files) await addFile(bank, previous, pin);
    const source = await selectedSource(selected.manifest, path.resolve(selected.source), temporary);
    const generated = path.join(temporary, 'generated');
    // The versioned wrapper invokes the existing stock packageStartupOwnership.
    const packaged = await packageVersionedStartupOwnership({manifest: selected.manifest, manifestSha: selected.sha256,
      manifestPath: path.resolve(selected.manifestPath), source, destination: generated});
    const latitude = await packageNativeLatitudes({manifest: selected.manifest, expectedReference: reference, destination: generated});
    const prefix = 'ownership-vintages/' + selected.sha256 + '/';
    for (const part of selected.manifest.parts.filter(part => part.kind === 'rows')) await addFile(bank, source, part, prefix + part.path);
    for (const pin of packaged.outputs) await addFile(bank, generated, pin);
    await addFile(bank, generated, latitude.receipt);
    const pixelMap = {...packaged.pixelMap,
      parts: packaged.pixelMap.parts.map(part => part.kind === 'rows' ? {...part, path: prefix + part.path} : part),
      native_latitudes: latitude.native_latitudes,
      canonical_grid_sha256: selected.sha256};
    const files = await inventory(bank); // Authenticate all retained and new outputs before completion.
    const index = {version: 1, native_manifest_sha256: selected.sha256, release_id: reference.id,
      footprints_sha256: reference.footprints_sha256, hierarchy_sha256: reference.hierarchy_sha256, pixelMap, files};
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
