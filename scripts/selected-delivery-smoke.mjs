// Actual emitted final-bank consumer: complete words, context and occupied controls.
// Historical cumulative reconstruction remains in Git history, not this runtime.

import fs from 'node:fs';
import {fileURLToPath} from 'node:url';

import path from 'node:path';

import assert from 'node:assert/strict';

import {gunzipSync} from 'node:zlib';

import {repositoryReader, sha256} from './evidence-quality.mjs';

import {loadOwnershipAssets} from '../src/ownership-assets.js';

import {additiveBaseReference, loadPreparedNativeContext} from '../src/effective-footprint.js';

import {scientificNativeSelection, originalNativeReference, validateReferenceMetadataHeader} from '../src/reference-metadata.js';

import {readPreparedFinalOwnership} from './package-startup-ownership.mjs';

import {ownershipRun, pickOwnership, samplePackedOwnership} from '../src/pixel-ownership.js';

const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);

const text = value => typeof value === 'string' && value.trim().length > 0;

function exactKeys(value, keys, label) {
  assert(value && typeof value === 'object' && !Array.isArray(value), `${label} must be an object`);
  assert.deepEqual(Object.keys(value).sort(), [...keys].sort(), `${label} has missing/foreign fields`);
}

function uniqueStrings(values, label) {
  assert(Array.isArray(values) && values.length > 0 && values.every(text), `${label} must be nonempty`);
  assert.equal(new Set(values).size, values.length, `Duplicate ${label}`);
}

export function validateDeliveryExpectations(value) {
  assert.equal(value?.version,2,'Current expectations require final-map version 2');
  exactKeys(value,['version','kind','bank','reference'],'Final bank expectations');
  assert.equal(value.kind,'selected-final-bank-consumer-v2');
  assert(value.bank&&hash(value.bank.sha256)&&Number.isSafeInteger(value.bank.bytes)&&value.bank.bytes>0);
  return value;
}

function admitOutput(filename) {
  assert(text(filename) && !filename.includes('\0'), 'Missing output path');
  const output = path.resolve(filename), parent = path.dirname(output);
  assert.equal(fs.realpathSync(parent), parent, 'Output symlink parent refused');
  assert(fs.lstatSync(parent).isDirectory(), 'Output parent must be an existing directory');
  assert(!fs.lstatSync(output, {throwIfNoEntry: false}), 'Output collision');
  return output;
}

export async function checkEmittedSelectedDelivery({root = process.cwd(), emittedDirectory = path.join(root, 'dist/client'),
  expectations} = {}) {
  const inputs = new Map();
  const readRoot = repositoryReader(root), readEmitted = repositoryReader(emittedDirectory);
  const read = (scope, name, pin, {nativePart = false} = {}) => {
    // Authenticate the declaration before passing its exact size to the reader.
    // Dropping it here silently reinstates the legacy unpinned-file ceiling.
    const omittedNativeBytes = pin && nativePart && !Object.hasOwn(pin, 'bytes')
      && hash(pin.decoded_sha256) && Number.isSafeInteger(pin.words) && pin.words > 0;
    if (pin) assert(hash(pin.sha256)
      && ((Number.isSafeInteger(pin.bytes) && pin.bytes >= 0) || omittedNativeBytes),
    'Missing whole-file asset pin');
    const bytes = (scope === 'root' ? readRoot : readEmitted)(name, 'candidate',
      pin && !omittedNativeBytes ? pin : undefined);
    const descriptor = {scope, path: name, bytes: bytes.length, sha256: sha256(bytes)};
    if (pin) {
      // packageStartupOwnership omits encoded bytes on its native run
      // descriptors. The encoded hash remains mandatory; production loading
      // separately authenticates decoded words and their complete coverage.
      if (!omittedNativeBytes) assert.equal(descriptor.bytes, pin.bytes, `Whole asset bytes differ: ${name}`);
      assert.equal(descriptor.sha256, pin.sha256, `Whole asset hash differs: ${name}`);
    }
    const key = `${scope}:${name}`;
    if (inputs.has(key)) assert.deepEqual(inputs.get(key), descriptor, `Consumed asset changed: ${name}`);
    else inputs.set(key, descriptor);
    return bytes;
  };
  const selection = JSON.parse(read('root','data/ownership-selection.json'));
  assert.equal(selection.version,2,'Current emitted delivery requires final-map version 2');
  return checkFinalBankEmitted({selection,expectations,read,inputs});
}

async function checkFinalBankEmitted({selection,expectations,read,inputs}) {
  const native=scientificNativeSelection(selection),manifestRaw=read('root',native.manifest_path);
  assert.equal(sha256(manifestRaw),native.sha256,'Original native manifest differs');
  const manifest=JSON.parse(manifestRaw),indexRaw=read('root',selection.prepared_bank.path,selection.prepared_bank),index=JSON.parse(indexRaw);
  let base=originalNativeReference(manifest),referenceMetadata;
  if(selection.reference_projection){const raw=read('root',selection.reference_projection.path,selection.reference_projection),projection=JSON.parse(raw);
    const references=validateReferenceMetadataHeader(projection,{selection,manifest});base=references.reference;
    referenceMetadata={version:1,asset:{path:'reference-metadata/current.json',bytes:raw.length,sha256:sha256(raw)},native_reference:references.native,reference:base};}
  assert.deepEqual(index.referenceMetadata,referenceMetadata,'Final bank projection identity differs');
  const atlas=JSON.parse(read('emitted','atlas-geography.json'));
  assert.equal(atlas.additiveRelease,undefined,'Final map cannot retain a historical repair envelope');
  assert.deepEqual(atlas.pixelMap,index.pixelMap,'Emitted final words descriptor differs');
  assert.deepEqual(atlas.preparedOwnership,index.preparedOwnership,'Emitted final context descriptor differs');
  assert.deepEqual(atlas.reference_release,selection.reference,'Emitted final identity differs');
  assert.deepEqual(atlas.referenceMetadata?Object.fromEntries(Object.entries(atlas.referenceMetadata).filter(([key])=>key!=='application_reference_revision')):undefined,referenceMetadata);
  assert.deepEqual(additiveBaseReference(atlas),base,'Emitted content reference differs');
  if(expectations!==undefined){validateDeliveryExpectations(expectations);assert.equal(expectations.version,2,'Historical repair expectations cannot admit a final bank');
    assert.deepEqual(expectations.bank,selection.prepared_bank);assert.deepEqual(expectations.reference,selection.reference);}
  uniqueStrings(atlas.parts,'emitted feature parts');
  const features=atlas.parts.flatMap(name=>{const raw=read('emitted',name),rows=JSON.parse(name.endsWith('.gz')?gunzipSync(raw,{maxOutputLength:32*1024*1024}):raw);assert(Array.isArray(rows)&&rows.length);return rows;});
  const prefix='data/canonical-grid/current-startup/',pins=new Map(index.files.map(pin=>[pin.path,pin]));
  // Every fixed compatibility URL and current operand must be the actual committed body.
  for(const pin of index.files){read('root',prefix+pin.path,{...pin,path:prefix+pin.path});read('emitted',pin.path,pin);}
  if(referenceMetadata)read('emitted',referenceMetadata.asset.path,referenceMetadata.asset);
  const expected=await readPreparedFinalOwnership({indexRaw,manifest,manifestSha:native.sha256,
    selected:{finalBank:selection.prepared_bank,reference_release:selection.reference,base,referenceMetadata:atlas.referenceMetadata},features:structuredClone(features),
    read:pin=>read('root',prefix+pin.path,{...pin,path:prefix+pin.path})});
  const fetcher=async name=>{const relative=String(name).replace(/^\.\//,'');const pin=pins.get(relative);assert(pin,'Unlisted emitted final bank operand');return new Response(read('emitted',relative,pin));};
  const words=await loadOwnershipAssets(atlas.pixelMap,fetcher,{requireNative:true,expectedReference:selection.reference});
  const effective=await loadPreparedNativeContext(atlas,features,words,{fetcher});
  assert.deepEqual(effective.rows,expected.ownership.rows,'Every emitted final row word equals its accepted bank');
  assert.deepEqual(effective.runs,expected.ownership.runs,'Every emitted final run word equals its accepted bank');
  assert.deepEqual(features,expected.features,'Complete emitted finished context differs');
  let controls=0;
  for(let y=0;y<effective.size;y++)if(effective.rows[y*2+1]){const run=ownershipRun(expected.ownership,expected.ownership.rows[y*2]);
    assert.equal(pickOwnership(effective,run.start,y),run.id);assert.equal(samplePackedOwnership(effective,{x:run.start,y,width:1,height:1})[0],run.id);controls++;}
  assert(controls>0,'Missing occupied final owner controls');
  return {version:2,kind:'actual-emitted-final-bank-consumer',passed:true,bank:selection.prepared_bank,reference:selection.reference,
    feature_count:features.length,complete_row_words:effective.rows.length,complete_run_words:effective.runs.length,
    occupied_controls_picked_and_sampled:controls,inputs:[...inputs.values()].sort((a,b)=>`${a.scope}:${a.path}`.localeCompare(`${b.scope}:${b.path}`)),
    limitation:'Whole accepted bank/context publication parity plus real picker/sampler controls. No historical repair replay, new science qualification or browser GPU claim.'};
}

export async function runSelectedDeliverySmoke({expectationsPath, outputPath, ...options}) {
  const output = admitOutput(outputPath);
  assert(text(expectationsPath), 'Missing expectations path');
  const expectationsFile = path.resolve(expectationsPath);
  const expectationsBytes = repositoryReader(path.dirname(expectationsFile))(path.basename(expectationsFile), 'candidate');
  const expectations = validateDeliveryExpectations(JSON.parse(expectationsBytes));
  const report = await checkEmittedSelectedDelivery({...options, expectations});
  report.expectations_sha256 = sha256(expectationsBytes);
  // Failures before this point create nothing. Exclusive creation rejects both
  // ordinary collisions and dangling symlinks; parent symlinks are refused too.
  admitOutput(output);
  fs.writeFileSync(output, JSON.stringify(report, null, 2) + '\n',
    {flag: fs.constants.O_WRONLY | fs.constants.O_CREAT | fs.constants.O_EXCL | fs.constants.O_NOFOLLOW});
  return report;
}

export async function main(args = process.argv.slice(2)) {
  if (args.length === 1 && args[0] === '--help') {
    console.log('Usage: node scripts/selected-delivery-smoke.mjs --expectations FILE --output NEW_FILE [--root REPO] [--emitted-directory DIR]');
    return;
  }
  const names = new Map([['--root', 'root'], ['--emitted-directory', 'emittedDirectory'],
    ['--expectations', 'expectationsPath'], ['--output', 'outputPath']]), options = {};
  for (let i = 0; i < args.length; i += 2) {
    const name = names.get(args[i]);
    assert(name && !Object.hasOwn(options, name) && text(args[i + 1]) && !args[i + 1].startsWith('--'),
      `Unknown, duplicate or incomplete option: ${args[i]}`);
    options[name] = args[i + 1];
  }
  const report = await runSelectedDeliverySmoke(options);
  console.log(JSON.stringify(report));
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(error => {console.error(error.message); process.exitCode = 1;});
}
